#!/usr/bin/env python3
"""
Boulder's annual financial reports (ACFRs) -- find five tables, then read them twice
====================================================================================
The city's Annual Comprehensive Financial Reports are audited, and the budget
books are not. Five of their tables fill gaps in, or check, this dataset:

    fundbal    Changes in Fund Balances - Governmental Funds, ten years: sales
               and use tax and property tax collections, the `salesuse_total`
               and `property_tax_revenue` actuals
    fte        Full-Time Equivalent City Employees by Functions/Programs, ten
               years: staffing by function
    taxsales   Taxable Sales by Market Sector, ten years: the sales tax base
    legal      Legal Debt Margin Information: that year's assessed value
    gf         the General Fund's Budget and Actual statement: original budget,
               final budget and actual, one year per report

Three stages, the middle one paid:

    python3 acfr-extract.py --locate
    python3 budget-books-ocr.py raw-acfr --pages-from acfr-pages.csv \\
        -o raw-acfr/acfr-ocr.jsonl --yes
    python3 acfr-extract.py

`--locate` finds each table's pages in the PDFs' own text and writes
acfr-pages.csv. The page numbers move from report to report (the tax table is
on page 250 of the 2016 report and 263 of the 2025 one), so they are found,
not typed.

The last stage reads every table twice, from the PDF's text layer (pypdf) and
from Datalab's OCR of the same page, and writes acfr-extracted.csv with both
readings side by side and how each figure is confirmed: by the two readings
agreeing, by another report printing it identically, by its own page's sums,
or by the page's text layer containing it (see confirm()). budget-history.py
loads only confirmed figures.

Two reports need help finding their pages:

  2021  The statistical section was scanned and run through OCR by the city
        before publication, so its text layer reads "Cha1Jges In Fund
        Balances - Govcmmcnial Funds". The title search misses that table,
        so its page is given below. The numbers have the same trouble
        ("110,01 I", "154.694"), which makes Datalab's reading the stronger
        one for this report.
  2023  The text layer is font glyph codes, not characters ("/0/1/2/3/i255"),
        in pypdf and PyMuPDF alike. Nothing on it can be searched or read. Its
        pages were found by rendering them, and it has the same 316 pages and
        the same layout as the 2022 report. Its figures rest on OCR alone,
        checked against its own totals and against the 2024 and 2025 reports,
        which print the same years.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf is required:  pip install pypdf")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw-acfr"
PAGES_CSV = HERE / "acfr-pages.csv"

def loose(phrase):
    """A title pattern that tolerates a stray space inside any word. Text
    layers split words apart: the 2024 report reads "CIT Y OF BOULDER" and
    "Decem ber", and the 2021 one "Lega l Debt Margin"."""
    return "".join(r"\s*" if c == " " else re.escape(c) + r"\s*" for c in phrase)


# Title patterns. Each must appear on the table's first page. A title alone is
# not enough: the table of contents and the statistical section's introduction
# name every table, and "Changes in Fund Balances" also heads each fund's
# budget schedule. So a ten-year table's page must also say "Last Ten" and
# carry year headings. The 2024 report prints only two years on the first page
# of its debt table, so two are enough.
TABLES = {
    "fundbal": loose("Changes In Fund Balances"),
    "taxsales": loose("Taxable Sales by Market Sector"),
    "legal": loose("Legal Debt Margin Information"),
    "fte": loose("Full-Time Equivalent City Employees"),
    "gf": loose("Budget and Actual"),
}
LAST_TEN = loose("Last Ten")
CONTENTS = loose("Table of Contents")
# Every table here runs to at most two pages: the ten-year tables print half
# their years on each page of a spread, and the General Fund statement puts its
# other financing sources on the second page.
MAX_PAGES = 2
OTHER_TITLE = re.compile(
    r"Statistical\s*Data|Budget\s*and\s*Actual\s*\(continued\)|Pledged\s*Revenue|"
    r"Direct\s*and\s*Overlapping|Demographic|Operating\s*Indicators|Principal\s*Employers",
    re.I)

# First pages the title search cannot find; see the module docstring.
OVERRIDES = {
    "2021.pdf": {"fundbal": 281},
    "2023.pdf": {"fundbal": 279, "taxsales": 281, "legal": 291, "fte": 297, "gf": 47},
}
NO_TEXT_LAYER = {"2023.pdf"}
# Reports whose text layer is not read for figures. 2023's is font codes. 2021's
# is the city's own OCR of a scan: its figures ("110,01 I", "154.694") are too
# garbled to place, and it is not an independent reading of a born-digital
# page anyway. Both rest on Datalab's reading, checked against their own
# printed totals and against the other reports that print the same years.
NO_TEXT_FIGURES = {"2021.pdf", "2023.pdf"}


class Pages:
    """A report's page texts, each extracted once: the title search looks at
    every page for each of five tables, and pypdf takes a second or more per
    page on the scanned 2021 report."""

    def __init__(self, pdf):
        self.reader = PdfReader(str(pdf))
        self.n = len(self.reader.pages)
        self._text = {}

    def text(self, pg):
        if pg not in self._text:
            raw = self.reader.pages[pg - 1].extract_text() or ""
            self._text[pg] = re.sub(r"\s+", " ", raw)
        return self._text[pg]


def years_on(text):
    # "20 14" and "20 15" in the 2021 report's text layer are years too.
    return {int(re.sub(r"\s", "", y))
            for y in re.findall(r"\b(2\s?0\s?[0-3]\s?\d)\b", text)}


def find_start(pages, key):
    n = pages.n
    for pg in range(1, n + 1):
        t = pages.text(pg)
        if not re.search(TABLES[key], t, re.I):
            continue
        if key == "gf":
            # The basic statements' General Fund statement, not the required
            # supplementary copy near the back or a fund-level schedule.
            if pg > 0.6 * n or not re.search(r"General\s*Fund", t) or "Original" not in t:
                continue
            return pg
        if (re.search(LAST_TEN, t, re.I) and len(years_on(t)) >= 2
                and not re.search(CONTENTS, t, re.I)
                and "statistical section of the City" not in t):
            return pg
    return None


def span(pages, fname, key, start):
    """The table's pages: the first, and the next unless it is blank or begins
    another table. A report with no text layer takes the two-page span its
    neighbours have."""
    got = [start]
    if fname in NO_TEXT_LAYER:
        return [start, start + 1]
    nxt = start + 1
    if nxt <= pages.n:
        t = pages.text(nxt)
        blank = "intentionally left blank" in t.lower() or len(t.strip()) < 40
        # The General Fund statement repeats its heading on page two with
        # "(continued)", and that page is wanted.
        continued = key == "gf" and re.search(r"\(continued\)", t, re.I)
        starts_other = bool(OTHER_TITLE.search(t)) and not continued
        if (not blank and not starts_other) or continued:
            got.append(nxt)
    return got[:MAX_PAGES]


def locate():
    rows = []
    for pdf in sorted(RAW.glob("*.pdf")):
        pages = Pages(pdf)
        got = []
        for key in TABLES:
            start = OVERRIDES.get(pdf.name, {}).get(key) or (
                None if pdf.name in NO_TEXT_LAYER else find_start(pages, key))
            if start is None:
                sys.exit(f"{pdf.name}: no {key} table found; add it to OVERRIDES")
            for pg in span(pages, pdf.name, key, start):
                rows.append({"file": pdf.name, "page": pg, "table": key})
            got.append(f"{key} {start}")
        print(f"  {pdf.name}: {', '.join(got)}")
    with PAGES_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["file", "page", "table"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {PAGES_CSV.name}: {len(rows)} pages in {len({r['file'] for r in rows})} reports")


# ---------------------------------------------------------------------------
# Reading every table twice
# ---------------------------------------------------------------------------
OCR_JSONL = RAW / "acfr-ocr.jsonl"
OUT_CSV = HERE / "acfr-extracted.csv"

# A cell holds a number, a dash (nothing that year), a footnote mark standing
# in for a number, or nothing. Numbers arrive as "$ 88,403", "136,269$",
# "(1,294)", "21.13" and "3.86%".
TOKEN = re.compile(
    r"\([a-z]\)|\*"
    r"|\(?\$?\s?\d{1,3}(?:,\s?\d{3})+(?:\.\d+)?\s?%?\s?\$?\)?"
    r"|\(?\$?\s?\d+(?:\.\d+)?\s?%?\s?\$?\)?"
    r"|(?<![\w.])-(?![\w.])")
YEAR_CELL = re.compile(r"(20[0-3]\d)(?:\s*\([a-z]\))?")


def cell(tok):
    """('num', value), ('dash', None) or ('mark', '(a)')."""
    t = re.sub(r"[\s$]", "", tok)
    if t == "-":
        return ("dash", None)
    if re.fullmatch(r"\([a-z]\)|\*", t):
        return ("mark", t)
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "").rstrip("%")
    v = float(t)
    return ("num", -v if neg else v)


def split_row(text):
    """A text-layer row as (label, [cells]): the label is whatever precedes the
    first cell, and anything between cells that is not a cell is dropped (the
    2021 report's own OCR turns "$" into "s")."""
    toks = list(TOKEN.finditer(text))
    # A label can end in digits ("2021" as a row of its own); cells begin where
    # the run of tokens reaching the end of the row begins.
    start = len(toks)
    for i in range(len(toks) - 1, -1, -1):
        gap = text[toks[i].end(): toks[i + 1].start()] if i + 1 < len(toks) else text[toks[i].end():]
        if re.search(r"[A-Za-z]{2,}", gap):
            break
        start = i
    label = text[: toks[start].start()] if start < len(toks) else text
    return label.strip(" .:$").strip(), [cell(t.group()) for t in toks[start:]]


# --- the text layer, by position -----------------------------------------
def text_rows(page):
    """The page's rows, top to bottom, each {y, text, segs}: text segments whose
    baselines sit within two points of each other form one row."""
    segs = []

    def visit(text, cm, tm, _font, _size):
        t = text.strip()
        if t:
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            segs.append((y, x, t))

    page.extract_text(visitor_text=visit)
    segs.sort(key=lambda s: (-s[0], s[1]))
    rows = []
    for y, x, t in segs:
        if rows and abs(rows[-1]["y"] - y) <= 2.0:
            rows[-1]["segs"].append((x, t))
        else:
            rows.append({"y": y, "segs": [(x, t)]})
    for r in rows:
        r["segs"].sort()
        r["text"] = " ".join(t for _x, t in r["segs"])
    return rows


def text_years(rows):
    """The header row's years and where each sits across the page."""
    for r in rows:
        hits = [(x, int(m.group(1))) for x, t in r["segs"]
                for m in re.finditer(r"\b(20[0-3]\d)\b", t)]
        years = [y for _x, y in hits]
        if len(years) >= 2 and all(b == a + 1 for a, b in zip(years, years[1:])):
            return r, hits
    return None, []


def year_row(r):
    years = [int(m.group(1)) for _x, t in r["segs"] for m in re.finditer(r"\b(20[0-3]\d)\b", t)]
    ok = len(years) >= 2 and all(b == a + 1 for a, b in zip(years, years[1:]))
    return years if ok else None


def text_grid(page):
    """{y: (label, {year: cell})} for one page of a ten-year table. A page can
    stack two blocks of years, each under its own heading row (the 2025
    report's taxable sales: 2016-2020 above, 2021-2025 below), so every heading
    row starts a new block."""
    rows = text_rows(page)
    head, hits = text_years(rows)
    if not head:
        return {}, []
    years, seen = None, []
    grid = {}
    for r in rows:
        if r["y"] > head["y"] + 1:
            continue
        ys = year_row(r)
        if ys:
            years = ys
            seen += [y for y in ys if y not in seen]
            continue
        label, cells = split_row(r["text"])
        if not cells:
            if label:
                grid[round(r["y"], 1)] = (label, {})
            continue
        if len(cells) == len(years):
            grid[round(r["y"], 1)] = (label, dict(zip(years, cells)))
        # A row with fewer cells than years cannot be placed by count, and
        # its cells' positions are not reliable enough to place them singly.
    return grid, seen


def text_spread(reader, pages):
    """A ten-year table across its two pages, rows matched by height: each row
    of the right-hand page sits level with its label on the left."""
    left, ly = text_grid(reader.pages[pages[0] - 1])
    rows = [(label, dict(cells), y) for y, (label, cells) in sorted(left.items(), reverse=True)]
    years = list(ly)
    if len(pages) > 1:
        right, ry = text_grid(reader.pages[pages[1] - 1])
        years += [y for y in ry if y not in years]
        for y, (_label, cells) in right.items():
            match = min(rows, key=lambda r: abs(r[2] - y), default=None)
            if match and abs(match[2] - y) <= 2.5:
                match[1].update(cells)
    return [(label, cells) for label, cells, _y in rows], years


# --- Datalab's markdown ----------------------------------------------------
def md_rows(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells):
            continue
        out.append([re.sub(r"</?(?:u|b|i|strong|em)>|\\", "", c).replace("<br>", " ").strip()
                    for c in cells])
    return out


def md_header(rows):
    """(row index, {column: year}) for the first row naming two or more
    consecutive years."""
    for i, r in enumerate(rows):
        cols = {j: int(m.group(1)) for j, c in enumerate(r)
                if (m := YEAR_CELL.fullmatch(c))}
        ys = sorted(cols.values())
        if len(ys) >= 2 and all(b == a + 1 for a, b in zip(ys, ys[1:])):
            return i, cols
    return None, {}


def md_cells(c):
    """A markdown cell's tokens (usually one; empty for a blank cell)."""
    return [cell(t.group()) for t in TOKEN.finditer(c)] if c else []


def value_columns(body, cols):
    """Where each year's figures actually are. Datalab sometimes gives the "$"
    its own column, with the year heading over the "$" and every figure one
    column to the right (the 2025 report's tax table): then the figures are
    read from that neighbouring, unheaded column."""
    out = {}
    for j, yr in cols.items():
        here = sum(1 for r in body if j < len(r) and md_cells(r[j]))
        nxt = sum(1 for r in body if j + 1 < len(r) and md_cells(r[j + 1]))
        out[j + 1 if (j + 1 not in cols and nxt > here) else j] = yr
    return out


def md_spread(texts):
    """A ten-year table across its two pages of markdown. The right page's
    rows are matched to the left page's by ORDER WITHIN EACH COLUMN, not by
    row: Datalab sometimes slides a column's cells up or down a row (the 2021
    report's 2021 column in its staffing table), but it keeps each column's
    cells in order, and the left page says which rows carry cells at all."""
    rows = md_rows(texts[0])
    hi, cols = md_header(rows)
    if hi is None:
        return [], []
    # Every heading row starts a new block of years; see text_grid.
    heads = [i for i in range(hi, len(rows)) if md_header([rows[i]])[0] is not None]
    table, years = [], []
    for n, h in enumerate(heads):
        body = rows[h + 1: heads[n + 1] if n + 1 < len(heads) else len(rows)]
        cols = value_columns(body, md_header([rows[h]])[1])
        years += [y for y in sorted(cols.values()) if y not in years]
        for r in body:
            label = r[0] if r and not md_cells(r[0]) else ""
            cells = {cols[j]: md_cells(r[j])[0] for j in cols if j < len(r) and md_cells(r[j])}
            if label or cells:
                table.append((label, cells))
    if len(texts) > 1:
        rrows = md_rows(texts[1])
        rhi, rcols = md_header(rrows)
        if rhi is not None:
            body = rrows[rhi + 1:]
            rcols = value_columns(body, rcols)
            # A row whose last left-hand cell is blank has ended, and has no
            # cells on the right-hand page either: the 2024 report's "Planning &
            # Development Services:" heading row stops after 2017.
            last = max(years)
            carriers = [i for i, (label, cells) in enumerate(table) if last in cells]
            for j, yr in rcols.items():
                column = [md_cells(r[j])[0] for r in body if j < len(r) and md_cells(r[j])]
                if len(column) == len(carriers):
                    for i, c in zip(carriers, column):
                        table[i][1][yr] = c
            years += [y for y in sorted(rcols.values()) if y not in years]
    return table, years


# --- the General Fund statement and the assessed value --------------------
GF_COLUMNS = ("adopted", "final", "actual", "variance")   # Original, Final, Actual, Variance


def md_statement(texts):
    """[(label, [cells])] from the General Fund statement's markdown: each
    labelled row's figures in column order, blank and "$" cells skipped."""
    out = []
    for text in texts:
        for r in md_rows(text):
            if not r or md_cells(r[0]):
                continue
            cells = [c for x in r[1:] for c in md_cells(x)]
            out.append((r[0], cells))
    return out


def text_statement(reader, pages):
    out = []
    for pg in pages:
        for r in text_rows(reader.pages[pg - 1]):
            out.append(split_row(r["text"]))
    return out


DEBT_LIMIT = re.compile(r"Debt\s*limit\s*-\s*3%", re.I)


def md_assessed(texts):
    """(assessed value, the debt limit printed under it, 3% of it)."""
    got = {}
    for text in texts:
        for r in md_rows(text):
            if not r:
                continue
            for key, pat in (("av", r"Assessed\s*value"), ("limit", DEBT_LIMIT.pattern)):
                if key not in got and re.match(pat, r[0], re.I):
                    cells = [c for x in r[1:] for c in md_cells(x) if c[0] == "num"]
                    if cells:
                        got[key] = cells[0]
    return got.get("av"), got.get("limit")


def text_assessed(reader, pages):
    got = {}
    for pg in pages:
        for r in text_rows(reader.pages[pg - 1]):
            label, cells = split_row(r["text"])
            nums = [c for c in cells if c[0] == "num"]
            for key, pat in (("av", r"Assessed\s*value"), ("limit", DEBT_LIMIT.pattern)):
                if key not in got and nums and re.match(pat, label, re.I):
                    got[key] = nums[0]
    return got.get("av"), got.get("limit")


# --- comparing the two readings --------------------------------------------
def norm(label):
    return re.sub(r"[^a-z0-9]", "", label.lower())


def shown(c):
    """A cell as the CSV shows it: the figure, "-" or the footnote mark."""
    if c is None:
        return ""
    kind, v = c
    if kind == "num":
        return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0")
    return "-" if kind == "dash" else v


def compare(md, tx):
    """Both readings of one cell -> (value, status). A dash and a footnote mark
    agree with each other: neither is a figure."""
    if md is None and tx is None:
        return None, ""
    if tx is None:
        return md, "ocr only"
    if md is None:
        return tx, "text only"
    if md == tx or (md[0] != "num" and tx[0] != "num"):
        return md, "agree"
    return md, "DISAGREE"


def read_all():
    import json
    pages = {}
    with PAGES_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            pages.setdefault((r["file"], r["table"]), []).append(int(r["page"]))
    ocr = {}
    with OCR_JSONL.open(encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            ocr[(d["file"], d["page"])] = d["text"]
    out = []
    for fname in sorted({f for f, _t in pages}):
        report = int(Path(fname).stem)
        reader = None if fname in NO_TEXT_FIGURES else PdfReader(str(RAW / fname))

        def emit(table, line, year, basis, unit, md, tx, pgs):
            value, status = compare(md, tx)
            if value is None:
                return
            out.append({"report": report, "table": table, "line": line, "year": year,
                        "basis": basis, "unit": unit, "value": shown(value),
                        "ocr": shown(md), "text": shown(tx), "status": status,
                        "pages": "-".join(str(p) for p in pgs)})

        for table, unit in (("fundbal", "thousands"), ("taxsales", "thousands"), ("fte", "fte")):
            pgs = pages[(fname, table)]
            md, _ = md_spread([ocr[(fname, p)] for p in pgs])
            merged, labels = {}, {}
            for label, cells in md:
                merged.setdefault(norm(label), {}).update(cells)
                labels.setdefault(norm(label), label)
            tx = {}
            for label, cells in (text_spread(reader, pgs)[0] if reader else []):
                tx.setdefault(norm(label), {}).update(cells)
            if table == "fundbal":
                keep = {norm("Sales and use taxes"), norm("General property taxes")}
                merged = {k: v for k, v in merged.items() if k in keep}
            for key, cells in merged.items():
                label = labels[key]
                tcells = tx.get(key, {})
                for year in sorted(set(cells) | set(tcells)):
                    # The rows under the taxable sales total are tax rates, in percent.
                    pct = table == "taxsales" and re.search(
                        r"direct city sales tax( rate)?$|food service sales tax$", label, re.I)
                    u = "pct" if pct else unit
                    emit(table, label.rstrip(": "), year, "actual" if table != "fte" else "adopted",
                         u, cells.get(year), tcells.get(year), pgs)
        pgs = pages[(fname, "gf")]
        md = md_statement([ocr[(fname, p)] for p in pgs])
        tx = dict((norm(l), c) for l, c in text_statement(reader, pgs)) if reader else {}
        seen = set()
        for label, cells in md:
            key = norm(label)
            if len(cells) != 4 or key in seen:
                continue
            seen.add(key)
            tcells = tx.get(key) if len(tx.get(key) or []) == 4 else [None] * 4
            for basis, c, t in zip(GF_COLUMNS, cells, tcells):
                emit("gf", label.rstrip(": "), report, basis, "thousands", c, t, pgs)
        pgs = pages[(fname, "legal")]
        md_av, md_limit = md_assessed([ocr[(fname, p)] for p in pgs])
        tx_av, tx_limit = text_assessed(reader, pgs) if reader else (None, None)
        emit("legal", "Assessed value", report, "actual", "thousands", md_av, tx_av, pgs)
        emit("legal", "Debt limit - 3% of assessed value", report, "actual", "thousands",
             md_limit, tx_limit, pgs)
    return out


# --- which figures are confirmed -------------------------------------------
# Line labels that differ between reports only by a misprint.
ALIASES = {
    "climateinitatives": "climateinitiatives",
    "accomodationstaxes": "accommodationstaxes",
    "overunderexpenditures": "excessdeficiencyofrevenuesoverunderexpenditures",
}


def line_key(r):
    k = norm(r["line"])
    return ALIASES.get(k, k)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def confirm(rows):
    """Say how each figure is known to be right, in a `confirmed` column, and
    settle the disagreements.

      both readings    the text layer and Datalab read the same figure
      another report   one reading, or two that disagree, and another report
                       prints the same figure for the same line and year: every
                       ten-year table repeats nine of its years in the next
                       report, and each report is a separate reading
      own arithmetic   the page's own sums pin the figure down: a ten-year
                       column whose lines add up to its printed total, with
                       this the only figure in it confirmed no other way (a
                       report's own figures for a year the next report
                       revises, like 2017's taxable sales); or a single-year
                       table read only by OCR, the 2021 and 2023 reports, whose
                       debt limit is 3% of its assessed value and whose General
                       Fund lines add up to its printed totals
      text layer       read only by OCR, but the same figure is in the page's
                       text layer where no row could be placed by position; for
                       figures of five digits or more, which do not recur by
                       chance (2017's own taxable sales, which later reports
                       revise)
      (blank)          unconfirmed, and not used

    Where the two readings disagree, the one another report prints wins. That
    is how the 2022 report's staffing table is read: Datalab slides one of its
    columns down a row from "Development" on, and the text layer, which places
    each row by its height on the page, matches the other reports."""
    from collections import defaultdict
    by = defaultdict(list)
    for r in rows:
        by[(r["table"], line_key(r), r["year"], r["basis"])].append(r)
    for r in rows:
        others = {v for o in by[(r["table"], line_key(r), r["year"], r["basis"])]
                  if o["report"] != r["report"] for v in (o["ocr"], o["text"]) if v != ""}
        if r["status"] == "agree":
            r["confirmed"] = "both readings"
        elif r["status"] == "DISAGREE":
            pick = [v for v in (r["text"], r["ocr"]) if v in others]
            if len(set(pick)) == 1:
                r["value"], r["confirmed"] = pick[0], "another report"
            else:
                r["confirmed"] = ""
        else:
            r["confirmed"] = "another report" if r["value"] in others else ""
    own_arithmetic(rows)
    in_text_layer(rows)
    return rows


def in_text_layer(rows):
    """Confirm the remaining OCR-only figures of five digits or more that the
    page's text layer contains, whatever their position; see confirm()."""
    texts = {}
    for r in rows:
        if r["confirmed"] or r["status"] != "ocr only" or abs(num(r["value"])) < 10000:
            continue
        fname = f"{r['report']}.pdf"
        if fname in NO_TEXT_FIGURES:
            continue
        if fname not in texts:
            texts[fname] = PdfReader(str(RAW / fname))
        pages = [int(p) for p in r["pages"].split("-")]
        blob = "".join(re.sub(r"\s", "", texts[fname].pages[p - 1].extract_text() or "")
                       for p in pages)
        if f"{abs(int(num(r['value']))):,}" in blob:
            r["confirmed"] = "text layer"


TOTALS = {"fte": ("Total", 0.011), "taxsales": ("Total Sales and Use Tax", 1.01)}


def own_arithmetic(rows):
    """Confirm figures their own page's sums pin down; see confirm()."""
    by_report = {}
    for r in rows:
        by_report.setdefault((r["report"], r["table"]), []).append(r)
    for (report, table), rs in by_report.items():
        if table in TOTALS:
            total_label, tol = TOTALS[table]
            for year in {r["year"] for r in rs}:
                col = [r for r in rs if r["year"] == year and r["unit"] != "pct"]
                tot = [r for r in col if r["line"] == total_label]
                if len(tot) != 1:
                    continue
                lines = sum(num(r["value"]) for r in col if r is not tot[0])
                unsettled = [r for r in col if not r["confirmed"]]
                if abs(lines - num(tot[0]["value"])) <= tol and len(unsettled) == 1:
                    unsettled[0]["confirmed"] = "own arithmetic"
        if table == "legal":
            av = next((r for r in rs if r["line"] == "Assessed value"), None)
            lim = next((r for r in rs if r["line"].startswith("Debt limit")), None)
            if av and lim and abs(round(num(av["value"]) * 0.03) - num(lim["value"])) <= 1:
                for r in (av, lim):
                    r["confirmed"] = r["confirmed"] or "own arithmetic"
        if table == "gf":
            for basis in GF_COLUMNS:
                col = [r for r in rs if r["basis"] == basis]
                ok = gf_sums_hold(col)
                for r in col:
                    if ok:
                        r["confirmed"] = r["confirmed"] or "own arithmetic"


def gf_sums_hold(col):
    """Revenue lines sum to Total revenues and expenditure lines to Total
    expenditures, to within the $1 thousand the city's rounding allows per
    line."""
    names = [r["line"] for r in col]
    try:
        tr, te = names.index("Total revenues"), names.index("Total expenditures")
    except ValueError:
        return False
    rev = sum(num(r["value"]) for r in col[:tr])
    exp = sum(num(r["value"]) for r in col[tr + 1: te])
    slack_r, slack_e = max(2, tr // 2), max(2, (te - tr) // 2)
    return (abs(rev - num(col[tr]["value"])) <= slack_r and
            abs(exp - num(col[te]["value"])) <= slack_e)


def write_extracted(rows):
    cols = ["report", "table", "line", "year", "basis", "unit", "value", "ocr", "text",
            "status", "confirmed", "pages"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    tally = Counter(r["status"] for r in rows)
    print(f"wrote {OUT_CSV.name}: {len(rows)} cells, " +
          ", ".join(f"{n} {k}" for k, n in tally.most_common()))
    conf = Counter(r["confirmed"] or "unconfirmed" for r in rows)
    print("  confirmed by: " + ", ".join(f"{n} {k}" for k, n in conf.most_common()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--locate", action="store_true",
                    help="find the five tables' pages and write acfr-pages.csv")
    args = ap.parse_args()
    if args.locate:
        locate()
        return
    write_extracted(confirm(read_all()))


if __name__ == "__main__":
    main()
