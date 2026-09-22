"""
Boulder budget books -- inventory, triage and page-text dump
============================================================
First of the four stages; README.md has the whole pipeline. Run it on your
LOCAL copy of the historical budget books before converting anything. It
answers the three questions that decide the cheapest route:

    1. What is actually in the corpus?   (year, pages, size)
    2. Which books are born-digital and which are scanned?
       Born-digital parses locally for free. Scanned needs OCR, which costs money
       and time, so you want to know exactly how many pages that is.
    3. Which PAGES carry the numbers?
       A budget book runs 250-500 pages, and the series needs a few dozen
       numbers per year off a handful of summary pages, pies and tables.
       Converting the whole book to reach them is the expensive mistake.

Usage
-----
    pip install pypdf
    python3 budget-books-inventory.py ~/Downloads/ExportedContents/

    # the text of every matched page in the born-digital books, as JSONL --
    # what budget-books-extract.py reads:
    python3 budget-books-inventory.py ~/Downloads/ExportedContents/ --dump-text dump.jsonl

    # or just the matched pages, as one small PDF per year:
    python3 budget-books-inventory.py ~/Downloads/ExportedContents/ --extract out/

A page matches when it carries a keyword from one of four TARGETS groups:
citywide totals, staffing, the General Fund, and the revenue and spending
categories (the pies).

Outputs
-------
    budget-books-inventory.csv   one row per PDF: year, pages, size, born-digital
                                 or scanned, and the page numbers matching each
                                 target group
    FILE.jsonl                   (--dump-text) one line per matched page:
                                 file, year, page, targets, text
    out/<year>-excerpt.pdf       (--extract) just the matched pages

What to do with the result
--------------------------
  * Born-digital matched pages  -> dump them and run the extractor: no upload,
                                   no OCR bill.
  * Scanned pages, and pages whose text comes out mangled
                                -> budget-books-ocr.py sends just those to
                                   Datalab.
"""

import argparse
import csv
import json
import pathlib
import re
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf is required:  pip install pypdf")

# Pages worth finding, grouped by what they feed in the series. Matching is
# case-insensitive and deliberately loose — a false positive costs one extra
# page in the excerpt, a false negative costs a whole year of data.
TARGETS = {
    "totals": [
        "budget summary", "budget at a glance", "all funds", "citywide budget",
        "total budget", "sources and uses", "summary of revenues",
        "revenues and expenditures", "fund financial", "fund summary",
    ],
    "staffing": [
        "authorized position", "position summary", "staffing summary",
        "full-time equivalent", "standard fte", "personnel summary",
        "approved positions", " fte ",
    ],
    "general_fund": [
        "general fund summary", "general fund revenue", "general fund expenditure",
    ],
    # Where the revenue and expense CATEGORY breakdowns live. These are pie
    # figures, not tables, and none of the keywords above reaches them: the
    # 2012-2017 books head them "Figure 4-2: Citywide Revenues (Sources) for
    # 2012" and "Figure 5-06: Citywide Expenditures for 2013", while the 2005
    # and 2006 books use the bare "2005 Uses of Funds". Without these, the
    # citywide revenue mix and the departmental spending split are invisible for
    # every middle year.
    "categories": [
        "uses of funds", "sources of funds", "citywide revenues", "citywide expenditures",
        "revenues (sources)", "expenditures (uses)", "overview of", "composition of",
        "revenues by fund", "expenditures by fund", "budget by department",
        "expenditures by department", "revenue by source",
    ],
}

# A page with fewer than this many extractable characters is treated as an image.
#
# Calibrated against real output, not guessed. A genuinely scanned page yields
# exactly 0 characters; a born-digital page yields something even when it is
# sparse. Summary and financial-table pages — precisely the ones this script
# exists to find — are far sparser than prose: measured at 42-134 characters,
# because a table is mostly numbers and whitespace. An earlier threshold of 120
# sat ABOVE most real table pages and classified whole born-digital books as
# scanned, which would mean paying to OCR books that never needed it.
TEXT_CHARS_MIN = 25
# A book is called scanned if fewer than this share of sampled pages have text.
BORN_DIGITAL_MIN_SHARE = 0.4
# How many pages to sample when classifying. Enough that a run of blank
# dividers in a 500-page book cannot flip the verdict.
SAMPLE_PAGES = 12


def infer_year(name: str):
    """Pull a plausible budget year out of a filename. Prefers 19xx/20xx."""
    years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", name)]
    years = [y for y in years if 1970 <= y <= 2035]
    return max(years) if years else None


def page_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def inspect(path: pathlib.Path, deep: bool):
    reader = PdfReader(str(path))
    n = len(reader.pages)

    # Sample evenly across the book to classify born-digital vs scanned without
    # reading every page.
    step = max(1, n // SAMPLE_PAGES)
    sample_idx = sorted(set(range(0, n, step)) | {n - 1})
    lengths = [len(page_text(reader.pages[i]).strip()) for i in sample_idx]
    with_text = sum(1 for L in lengths if L >= TEXT_CHARS_MIN)
    share = with_text / len(lengths) if lengths else 0.0
    kind = "born_digital" if share >= BORN_DIGITAL_MIN_SHARE else "scanned"

    hits = {k: [] for k in TARGETS}
    # Only keyword-scan books we can actually read. A scanned book needs OCR
    # before any of this works, which is the point of reporting it separately.
    if kind == "born_digital" and deep:
        for i in range(n):
            low = page_text(reader.pages[i]).lower()
            if not low:
                continue
            for target, keys in TARGETS.items():
                if any(k in low for k in keys):
                    hits[target].append(i + 1)   # 1-indexed, as a human reads it

    return {
        "file": path.name,
        "year": infer_year(path.name) or "",
        "pages": n,
        "size_mb": round(path.stat().st_size / 1e6, 1),
        "kind": kind,
        "text_share_sampled": round(share, 2),
        # Keep the raw evidence so a borderline verdict can be eyeballed rather
        # than trusted. max_chars near zero is a genuinely scanned book.
        "max_chars_sampled": max(lengths) if lengths else 0,
        **{f"pages_{k}": " ".join(str(p) for p in v[:40]) for k, v in hits.items()},
        **{f"n_{k}": len(v) for k, v in hits.items()},
    }


def main():
    ap = argparse.ArgumentParser(description="Inventory and triage Boulder budget books.")
    ap.add_argument("root", help="directory containing the PDFs (searched recursively)")
    ap.add_argument("--extract", metavar="OUTDIR",
                    help="also write one small PDF per book containing only the matched pages")
    ap.add_argument("--shallow", action="store_true",
                    help="skip the per-page keyword scan (much faster, no page numbers)")
    ap.add_argument("--dump-text", metavar="FILE.jsonl",
                    help="write the text of every matched page as JSONL. A couple of MB for "
                         "the whole corpus, and the fastest way to hand the real table "
                         "structure to whoever writes the parser without shipping any PDFs.")
    ap.add_argument("--max-pages-per-book", type=int, default=0,
                    help="with --dump-text, keep only the first N matched pages per book "
                         "(the citywide summary tables sit near the front)")
    ap.add_argument("--out", default="budget-books-inventory.csv",
                    help="CSV to write (default %(default)s)")
    args = ap.parse_args()

    # Line-buffer stdout. Redirected to a file -- `nohup ... > run.log &`, which is
    # how a long run gets started -- Python block-buffers output in ~8KB, so
    # the log stays EMPTY until enough books have been scanned to fill it.
    # It looks like a hung process. This was invisible in testing because the
    # environment used there set PYTHONUNBUFFERED=1; a default Python reproduces it
    # exactly (0 of 3 progress lines visible mid-run, 3 of 3 with this line).
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:        # Python < 3.7
        pass

    root = pathlib.Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"no such directory: {root}")

    pdfs = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    if not pdfs:
        sys.exit(f"no PDFs under {root} — unzip the archive first?")

    print(f"{len(pdfs)} PDFs under {root}\n")
    if args.dump_text:
        # Opened per book in append mode below, so start clean or a re-run
        # silently doubles every page.
        pathlib.Path(args.dump_text).write_text("", encoding="utf-8")
    rows = []
    for i, p in enumerate(pdfs, 1):
        print(f"  [{i}/{len(pdfs)}] {p.name[:70]}", end="", flush=True)
        try:
            row = inspect(p, deep=not args.shallow)
        except Exception as exc:
            print(f"  -> FAILED: {type(exc).__name__}: {exc}")
            rows.append({"file": p.name, "year": infer_year(p.name) or "",
                         "pages": "", "size_mb": round(p.stat().st_size / 1e6, 1),
                         "kind": "unreadable", "text_share_sampled": ""})
            continue
        matched = sum(row.get(f"n_{k}", 0) for k in TARGETS)
        print(f"  -> {row['pages']}p {row['kind']}, {matched} matched pages")
        rows.append(row)

        if args.dump_text and row["kind"] == "born_digital":
            by_page = {}
            for target in TARGETS:
                for x in (row.get(f"pages_{target}") or "").split():
                    by_page.setdefault(int(x), []).append(target)
            dump_pages = sorted(by_page)
            if args.max_pages_per_book:
                dump_pages = dump_pages[: args.max_pages_per_book]
            if dump_pages:
                reader = PdfReader(str(p))
                with open(args.dump_text, "a", encoding="utf-8") as fh:
                    for pg in dump_pages:
                        fh.write(json.dumps({
                            "file": p.name,
                            "year": row["year"],
                            "page": pg,
                            "targets": by_page[pg],
                            "text": page_text(reader.pages[pg - 1]),
                        }) + "\n")

        if args.extract and row["kind"] == "born_digital":
            pages = sorted({int(x) for k in TARGETS
                            for x in (row.get(f"pages_{k}") or "").split() if x})
            if pages:
                outdir = pathlib.Path(args.extract).expanduser()
                outdir.mkdir(parents=True, exist_ok=True)
                w = PdfWriter()
                reader = PdfReader(str(p))
                for pg in pages:
                    w.add_page(reader.pages[pg - 1])
                stem = row["year"] or p.stem
                with (outdir / f"{stem}-excerpt.pdf").open("wb") as fh:
                    w.write(fh)

    cols = ["file", "year", "pages", "size_mb", "kind", "text_share_sampled", "max_chars_sampled"]
    for k in TARGETS:
        cols += [f"n_{k}", f"pages_{k}"]
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # Summary — this is the number that decides the route.
    digital = [r for r in rows if r.get("kind") == "born_digital"]
    scanned = [r for r in rows if r.get("kind") == "scanned"]
    bad = [r for r in rows if r.get("kind") == "unreadable"]
    tot_pages = sum(r["pages"] for r in rows if isinstance(r.get("pages"), int))
    scan_pages = sum(r["pages"] for r in scanned if isinstance(r.get("pages"), int))
    matched_pages = sum(r.get(f"n_{k}", 0) for r in rows for k in TARGETS)
    years = sorted({r["year"] for r in rows if r.get("year")})

    print(f"\nwrote {args.out}")
    print(f"  books            {len(rows)}  ({len(digital)} born-digital, "
          f"{len(scanned)} scanned, {len(bad)} unreadable)")
    if years:
        print(f"  years            {years[0]}-{years[-1]}  ({len(years)} distinct)")
    print(f"  total pages      {tot_pages:,}")
    print(f"  pages needing OCR{scan_pages:>8,}   <- the only pages worth paying to convert")
    if not args.shallow:
        print(f"  matched pages    {matched_pages:,}   <- what actually carries the numbers")
        if tot_pages:
            print(f"                   {matched_pages / tot_pages:.1%} of the corpus")
    if args.dump_text:
        mb = pathlib.Path(args.dump_text).stat().st_size / 1e6
        print(f"  text dump        {args.dump_text}  ({mb:.1f} MB)  <- send this, not the PDFs")


if __name__ == "__main__":
    main()
