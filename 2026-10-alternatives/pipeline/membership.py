"""The three CDE membership files the spreadsheet reader cannot take.

2001 and 2002 are PDFs and 2003 is a spreadsheet laid out as an indented
panel, so neither shape has the header the ordinary reader looks for. Both are
read here, and both are checked the same way the rest of the archive is: every
row prints its own total, and a row is kept only where the grades add to it.
"""
from __future__ import annotations
import re
from pathlib import Path

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTTextContainer

from .schema import GRADES, normalize_code, parse_count

# PK, K, 1 to 12, then the printed total: sixteen figures on a school's line.
COLUMNS = GRADES + ["TOTAL"]
# Only a genuine subtotal row. "COUNTY" cannot be part of this: Colorado has
# districts called Denver County 1, Jefferson County R-1 and Douglas County
# Re 1, and excluding them drops three of the largest districts in the state.
AGGREGATE = re.compile(r"\bTOTALS?\b|\bSTATE\s+TOTAL\b", re.I)
# A subtotal says which level it is for, and only the district one can be
# checked against the schools above it: a county total spans several districts
# and the state total spans them all, and attributing either to the last
# district seen puts 741,829 pupils into Expeditionary BOCES.
DISTRICT_TOTAL = re.compile(r"\bDISTRICT\s+TOTALS?\b", re.I)
# CDE's residual: pupils a district reports without attaching them to a
# building. They are real and they are inside the district's printed total,
# but they are not a school, so they are held back from the school records and
# added in again when the district total is checked.
NOT_IN_A_SCHOOL = re.compile(r"\bNOT\s+IN\s+A\s+SCHOOL\b", re.I)


# --------------------------------------------------------------------------
# 2003: county, district and school indented down one column each
# --------------------------------------------------------------------------

def parse_indented_sheet(path: Path, year: int, source: str) -> tuple[list[dict], dict]:
    """The 2003 workbook, where the hierarchy is indentation rather than columns.

    A county row carries a number and a name and nothing else; a district row
    carries its code and name two columns further right; a school row carries
    its own code and name two further right again, and the grades after that.
    So the identity of a school row is not on it - it is whatever county and
    district were last seen above it.
    """
    from .extract import read_sheet
    rows = read_sheet(path)

    header_idx = grade_at = None
    for index, row in enumerate(rows[:40]):
        cells = [str(v).strip().upper() for v in row]
        if "TOTAL" in cells and "PK" in cells:
            header_idx = index
            grade_at = {}
            for position, cell in enumerate(cells):
                label = {"PK": "PK", "K": "K", "TOTAL": "TOTAL"}.get(
                    cell, cell[:-2] if cell.endswith(".0") else cell)
                if label in COLUMNS:
                    grade_at[label] = position
            break
    if header_idx is None or not grade_at or "TOTAL" not in grade_at:
        return [], {"error": "no header row carrying PK and TOTAL"}
    first_grade = min(grade_at.values())

    # The panel is three levels of two columns each - code then name for the
    # county, the district and the school - sitting immediately left of the
    # grades. Reading a row's level from which of those six columns it fills
    # is the whole of the layout, and it does not depend on guessing.
    school_at = (first_grade - 2, first_grade - 1)
    district_at = (first_grade - 4, first_grade - 3)
    county_at = (first_grade - 6, first_grade - 5)
    if county_at[0] < 0:
        return [], {"error": f"grades start at column {first_grade}, too few to indent"}

    def pair(cells, at):
        code = cells[at[0]] if at[0] < len(cells) else ""
        name = cells[at[1]] if at[1] < len(cells) else ""
        return normalize_code(code.replace(".0", "")), name

    records, county, district = [], "", ("", "")
    checks = {"pass": 0, "fail": 0}
    subtotals: list[tuple[str, int | None]] = []
    residual: dict[str, int] = {}
    aggregate = skipped = 0
    for row in rows[header_idx + 1:]:
        cells = [("" if v is None or str(v) == "nan" else str(v).strip())
                 for v in row]
        if not any(cells):
            continue
        filled = [i for i, c in enumerate(cells[:first_grade]) if c]
        has_grades = any(cells[i] for i in grade_at.values() if i < len(cells))
        if not has_grades:
            if not filled:
                continue
            deepest = max(filled)
            if deepest in county_at:
                county = pair(cells, county_at)[1] or cells[filled[-1]]
            elif deepest in district_at:
                code, name = pair(cells, district_at)
                if not AGGREGATE.search(name):
                    district = (code, name)
            continue
        code, name = pair(cells, school_at)
        label = cells[filled[-1]] if filled else ""
        if AGGREGATE.search(name) or AGGREGATE.search(label):
            # "MAPLETON 1 Total" sits in the district's own name column and
            # carries the grades, so it looks like a school with no code.
            if not name and max(filled) in district_at:
                subtotals.append((district[1],
                                  parse_count(cells[grade_at["TOTAL"]])))
            aggregate += 1
            continue
        if not code.isdigit():
            skipped += 1
            continue
        if code == "0000" or NOT_IN_A_SCHOOL.search(name):
            residual[district[1]] = (residual.get(district[1], 0)
                                     + (parse_count(cells[grade_at["TOTAL"]]) or 0))
            skipped += 1
            continue
        counts = {}
        for grade in GRADES:
            if grade in grade_at:
                value = parse_count(cells[grade_at[grade]])
                if value is not None:
                    counts[grade] = counts.get(grade, 0) + value
        printed = parse_count(cells[grade_at["TOTAL"]])
        if printed is None or sum(counts.values()) != printed:
            checks["fail"] += 1
            continue
        checks["pass"] += 1
        base = {"year": year, "ncessch": "", "school_code": code,
                "district_code": district[0], "district_name": district[1],
                "school_name": name, "county_name": county, "source": source}
        records.extend({**base, "grade": grade, "enrollment": value}
                       for grade, value in counts.items())
    meta = {
        "schools": len({r["school_code"] for r in records}),
        "records": len(records), "rows_aggregate_excluded": aggregate,
        "rows_dropped_no_school_code": skipped,
        "row_total_pass": checks["pass"], "row_total_fail": checks["fail"],
    }
    meta.update(check_subtotals(records, subtotals, residual))
    return records, meta


# --------------------------------------------------------------------------
# 2001 and 2002: PDFs whose grade columns run together as text
# --------------------------------------------------------------------------

def _characters(element):
    if isinstance(element, LTChar):
        yield element
    elif hasattr(element, "__iter__"):
        for child in element:
            yield from _characters(child)


def _runs(chars, gap: float):
    """Characters in runs, broken wherever the horizontal step exceeds `gap`."""
    groups = []
    for char in sorted(chars, key=lambda c: c.x0):
        if groups and char.x0 - max(c.x1 for c in groups[-1]) <= gap:
            groups[-1].append(char)
        else:
            groups.append([char])
    return groups


def _lines(path: Path, gap: float):
    """Every line of the file as runs of text, keyed by page and baseline."""
    found: dict[tuple[int, float], list] = {}
    for page_number, page in enumerate(extract_pages(str(path))):
        for element in page:
            if not isinstance(element, LTTextContainer):
                continue
            for char in _characters(element):
                found.setdefault((page_number, round(char.y0, 0)), []).append(char)
    for key in sorted(found, key=lambda k: (k[0], -k[1])):
        groups = _runs(found[key], gap)
        yield key, [(g[0].x0, "".join(c.get_text() for c in g).strip())
                    for g in groups if "".join(c.get_text() for c in g).strip()]


def _layout(lines) -> int:
    """How many identifying fields a data line carries.

    2001 heads a single column, "COUNTY/DISTRICT/SCHOOL NAME", and indents the
    three levels under it, so a school's line holds one name. 2002 repeats all
    three on every line. The header cannot be used to tell them apart - its
    labels are set to the right of the columns they head, so in 2002 "COUNTY"
    is printed at x=38 above data that starts at x=10. The lines themselves
    can: count the names on the lines that carry a full row of figures, and
    take the count that most of them agree on.
    """
    counts: dict[int, int] = {}
    for _key, runs in lines:
        figures = [t for _x, t in runs if re.fullmatch(r"[\d,]+", t)]
        if len(figures) == len(COLUMNS):
            names = sum(1 for _x, t in runs if not re.fullmatch(r"[\d,]+", t))
            counts[names] = counts.get(names, 0) + 1
    return max(counts, key=counts.get) if counts else 0


def parse_membership_pdf(path: Path, year: int, source: str,
                         gap: float = 2.5) -> tuple[list[dict], dict]:
    """The 2001 and 2002 membership PDFs, read from character positions.

    Taken as text these files give "ALTERNATIVE SCHOOL000000000051655938213" -
    sixteen figures with nothing between them, because every grade column is
    narrow and most of them are zero. The characters know better: a column is
    about twenty-eight points wide and a digit about five, so the gaps between
    columns are an order of magnitude larger than the gaps inside a number.

    Nothing here trusts that reading on its own. A line is kept only where it
    splits into exactly sixteen figures and the fifteen grades add to the
    sixteenth.
    """
    lines = list(_lines(path, gap))
    fields_per_line = _layout(lines)
    if not fields_per_line:
        return [], {"error": "no line carries a full row of figures"}
    flat = fields_per_line >= 3

    def is_figure(text):
        return bool(re.fullmatch(r"[\d,]+", text))

    # In the indented file the level of a heading is its left edge, and the
    # levels are whatever the file actually uses rather than a fixed margin.
    # A school's line marks the deepest of them, so anything starting to the
    # right of that is page furniture - the title, the "GRADE LEVEL" banner -
    # and not a heading at all. Reading the banner as a district name puts
    # every school at the top of a page into a district called GRADE LEVEL.
    school_indents: dict[int, int] = {}
    for _key, runs in lines:
        if sum(1 for _x, t in runs if is_figure(t)) == len(COLUMNS):
            names = [x for x, t in runs if not is_figure(t)]
            if names:
                school_indents[round(min(names))] = school_indents.get(round(min(names)), 0) + 1
    school_indent = max(school_indents, key=school_indents.get) if school_indents else 10 ** 6
    indents = sorted({round(runs[0][0])
                      for _key, runs in lines
                      if runs and not any(is_figure(t) for _x, t in runs)
                      and round(runs[0][0]) <= school_indent})
    county_indent = indents[0] if indents else 0

    records, county, district = [], "", ""
    checks = {"pass": 0, "fail": 0}
    subtotals: list[tuple[str, int | None]] = []
    residual: dict[str, int] = {}
    aggregate = skipped = 0
    for _key, runs in lines:
        figures = [t for _x, t in runs if is_figure(t)]
        words = [(x, t) for x, t in runs if not is_figure(t)]
        if not figures:
            if not words or flat or round(words[0][0]) > school_indent:
                continue
            label = " ".join(t for _x, t in words).strip()
            if round(words[0][0]) <= county_indent + 4:
                county = re.sub(r"\s*COUNTY$", "", label, flags=re.I).strip()
            else:
                district = label
            continue
        if len(figures) != len(COLUMNS) or not words:
            skipped += 1
            continue
        if flat:
            if len(words) == 2 and AGGREGATE.search(words[1][1]):
                # "ADAMS | DISTRICT TOTAL" - the subtotal for whatever district
                # the lines above it belong to.
                if DISTRICT_TOTAL.search(words[1][1]):
                    subtotals.append((district, parse_count(figures[-1])))
                aggregate += 1
                continue
            if len(words) != fields_per_line:
                skipped += 1
                continue
            county, district, name = (t for _x, t in words[:3])
            county = re.sub(r"\s*COUNTY$", "", county, flags=re.I).strip()
        else:
            name = " ".join(t for _x, t in words).strip()
        if not name:
            skipped += 1
            continue
        if AGGREGATE.search(name):
            if DISTRICT_TOTAL.search(name):
                subtotals.append((district, parse_count(figures[-1])))
            aggregate += 1
            continue
        if NOT_IN_A_SCHOOL.search(name):
            residual[district] = residual.get(district, 0) + (parse_count(figures[-1]) or 0)
            skipped += 1
            continue
        counts = {}
        for grade, value in zip(GRADES, figures):
            parsed = parse_count(value)
            if parsed is None:
                counts = {}
                break
            counts[grade] = counts.get(grade, 0) + parsed
        printed = parse_count(figures[-1])
        if not counts or printed is None or sum(counts.values()) != printed:
            checks["fail"] += 1
            continue
        checks["pass"] += 1
        base = {"year": year, "ncessch": "", "school_code": "",
                "district_code": "", "district_name": district,
                "school_name": name, "county_name": county, "source": source}
        records.extend({**base, "grade": grade, "enrollment": value}
                       for grade, value in counts.items())
    meta = {
        "layout": "flat" if flat else "indented",
        "name_columns": fields_per_line,
        "schools": len({(r["district_name"], r["school_name"]) for r in records}),
        "records": len(records), "rows_aggregate_excluded": aggregate,
        "rows_dropped_no_school_code": skipped,
        "row_total_pass": checks["pass"], "row_total_fail": checks["fail"],
    }
    meta.update(check_subtotals(records, subtotals, residual))
    return records, meta


def check_subtotals(records, subtotals, residual=None) -> dict:
    """A district's schools must add to the district total the file prints.

    The row totals check each line against itself, which an aggregate row
    passes just as easily as a school does. This is the check that catches a
    row read at the wrong level, or a school attributed to the wrong district.
    """
    summed: dict[str, int] = dict(residual or {})
    for row in records:
        summed[row["district_name"]] = summed.get(row["district_name"], 0) + row["enrollment"]
    agree = disagree = 0
    worst = None
    for district, printed in subtotals:
        if printed is None or district not in summed:
            continue
        gap = summed[district] - printed
        if gap == 0:
            agree += 1
        else:
            disagree += 1
            if worst is None or abs(gap) > abs(worst[1]):
                worst = (district, gap)
    return {"district_total_pass": agree, "district_total_fail": disagree,
            "district_total_worst": worst}
