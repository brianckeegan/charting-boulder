"""Parsers. One function per source shape, each returning tidy long records.

Four shapes, because the sources really are four different things:

  parse_cde_school_sheet   CDE spreadsheets, 2003-2025. School x grade.
  parse_cde_teacher_sheet  CDE staff spreadsheets. Teacher FTE by school.
  parse_yearbook_tables    Datalab markdown from the scanned 1986-1999
                           volumes. District x grade, and the district
                           trends table that reaches back to 1977-78.
  ccd_records              NCES CCD through the Urban Institute API.

Every parser funnels through pipeline.schema, so the grade vocabulary, the
code padding and the missing-value rules are decided once.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

from .schema import (
    CCD_GRADE,
    normalize_ccd_state_code,
    normalize_code,
    normalize_grade,
    parse_count,
    parse_decimal,
    usable_coordinate,
)

HERE = Path(__file__).resolve().parent.parent
CCD_API = "https://educationdata.urban.org/api/v1/schools/ccd"
USER_AGENT = "charting-boulder/pipeline (+https://github.com/brianckeegan/charting-boulder)"

# Aggregate rows that sit inside a detail table and must never be read as a
# school: state totals, county totals, district subtotals.
AGGREGATE_ROW = re.compile(r"\b(STATE|COUNTY|DISTRICT|GRAND)\s+TOTALS?\b|\bTOTALS?\s+FOR\b", re.I)


def read_sheet(path: Path) -> list[list]:
    """First worksheet as rows. pandas covers both the modern .xlsx
    (openpyxl) and the legacy BIFF .xls (xlrd); CDE publishes both."""
    import pandas as pd  # noqa: PLC0415

    frame = pd.read_excel(path, header=None, dtype=object)
    return [["" if v is None or (isinstance(v, float) and v != v) else v for v in row]
            for row in frame.values.tolist()]


def _find_header(rows: list[list], minimum_grades: int = 8) -> tuple[int, dict[int, str]] | None:
    """The header is the first row carrying enough recognizable grade columns.

    CDE puts one or two title rows above it, and the title text moves between
    vintages, so counting grade columns is more robust than matching a title.
    """
    for i, row in enumerate(rows[:40]):
        mapped = {j: normalize_grade(v) for j, v in enumerate(row) if normalize_grade(v)}
        numeric = {j: g for j, g in mapped.items() if g not in ("SPECIAL_EDUCATION", "UNGRADED")}
        if len(numeric) >= minimum_grades:
            return i, mapped
    return None


def _column_finder(header: list[str], sample: list | None = None, code_width: int = 4):
    """Find a column by header pattern, checking the values when it matters.

    Header names are not unique. The 2006 file has TWO columns headed
    "District Code": the first holds the school year (20062007) and the second
    the real code (0010). Taking the first match gave every school in the
    state the same district, and the year collapsed to a single district in
    the output - visible only because a district count of 1 is absurd.

    So when several columns match and a sample row is available, prefer one
    whose value is the right width for a code.
    """
    def find(*patterns: str, as_code: bool = False) -> int | None:
        matches = [j for j, name in enumerate(header)
                   if any(re.search(p, name, re.I) for p in patterns)]
        if not matches:
            return None
        if as_code and sample and len(matches) > 1:
            for j in matches:
                if j >= len(sample):
                    continue
                text = str(sample[j]).strip()
                if text.endswith(".0"):
                    text = text[:-2]
                if text.isdigit() and len(text) <= code_width:
                    return j
        return matches[0]
    return find


def parse_cde_school_sheet(path: Path, year: int, source: str) -> tuple[list[dict], dict]:
    """CDE school-by-grade spreadsheet -> long records, plus parse metadata.

    The identifier columns drift between eras (finding A6): 2013 heads them
    COUNTY/DISTRICT/SCHOOL, 2024 drops county and renames the district pair
    to "Organization". Both map onto one schema here.
    """
    rows = read_sheet(path)
    found = _find_header(rows)
    if found is None:
        return [], {"error": "no header row with enough grade columns"}
    header_idx, grade_cols = found
    header = [str(v).strip() for v in rows[header_idx]]
    first_data = rows[header_idx + 1] if header_idx + 1 < len(rows) else None
    find = _column_finder(header, first_data)

    # Header wording drifts hard across 24 vintages: "School Code" becomes
    # "Sch Code", "District Code" becomes "Distr Code", and from about 2019
    # the district pair is renamed "Organization". Matching only the long
    # spellings silently lost nine of the twenty-four years.
    cols = {
        "school_code": find(r"^(school|sch)\s*(code|number|no)\b", r"(school|sch).*code", as_code=True),
        "school_name": find(r"^(school|sch)\s*name", r"^school$"),
        "district_code": find(r"(district|distr|lea|organization).*(code|number|no)", as_code=True),
        "district_name": find(r"(district|distr|lea|organization).*name", r"^district$"),
        "county_name": find(r"county.*name"),
        "total": find(r"^total$", r"pk-?12\s*(count|total)", r"^count$"),
    }
    if cols["school_code"] is None:
        return [], {"error": "no school code column", "header": header}

    def cell(row, idx):
        if idx is None or idx >= len(row):
            return ""
        text = str(row[idx]).strip()
        return text[:-2] if text.endswith(".0") and text[:-2].isdigit() else text

    records, dropped, not_in_school, aggregate, total_checks = [], 0, 0, 0, {"pass": 0, "fail": 0}
    for row in rows[header_idx + 1:]:
        if not any(str(v).strip() for v in row):
            continue
        code = normalize_code(cell(row, cols["school_code"]))
        if not code or not code.isdigit():
            dropped += 1
            continue
        # School code 0000 is CDE's "Not in a school" residual: pupils a
        # district reports without attaching them to a building. They are real
        # and they belong in the district tier, but they are not a school and
        # CCD has no counterpart, so they would show up as a phantom school
        # closing and reopening every year.
        if code == "0000":
            not_in_school += 1
            continue
        # Aggregate rows hide inside the detail table. The 2010 file ends with
        # a STATE TOTALS row coded 9999/9999 carrying all 843,316 pupils; read
        # as a school it doubles the state exactly. Row-total checksums cannot
        # catch this, because an aggregate row sums correctly against itself -
        # only comparing school sums to the district rows exposes it.
        name = f"{cell(row, cols['school_name'])} {cell(row, cols['district_name'])}".upper()
        if code == "9999" or AGGREGATE_ROW.search(name):
            aggregate += 1
            continue
        base = {
            "year": year,
            "ncessch": "",
            "school_code": code,
            "district_code": normalize_code(cell(row, cols["district_code"])),
            "district_name": cell(row, cols["district_name"]),
            "school_name": cell(row, cols["school_name"]),
            "source": source,
        }
        # Sum rather than append, so Half-Day K and Full-Day K collapse to one
        # K (finding A5).
        totals: dict[str, int] = {}
        for j, grade in grade_cols.items():
            if j >= len(row):
                continue
            value = parse_count(row[j])
            if value is not None:
                totals[grade] = totals.get(grade, 0) + value
        for grade, value in totals.items():
            records.append({**base, "grade": grade, "enrollment": value})

        # The file prints its own row total; compare (cleaning rule 10).
        printed = parse_count(row[cols["total"]]) if cols["total"] is not None and cols["total"] < len(row) else None
        if printed is not None:
            summed = sum(v for g, v in totals.items() if g != "UNGRADED" or True)
            total_checks["pass" if summed == printed else "fail"] += 1

    k_columns = [header[j] for j, g in sorted(grade_cols.items()) if g == "K"]
    meta = {
        "header_row": header_idx,
        "grade_columns": {str(k): v for k, v in sorted(grade_cols.items())},
        "kindergarten_columns_summed": k_columns,
        "id_columns": {k: (header[v] if v is not None else None) for k, v in cols.items()},
        "schools": len({r["school_code"] for r in records}),
        "records": len(records),
        "rows_dropped_no_school_code": dropped,
        "rows_not_in_a_school": not_in_school,
        "rows_aggregate_excluded": aggregate,
        "row_total_pass": total_checks["pass"],
        "row_total_fail": total_checks["fail"],
    }
    return records, meta


def parse_cde_teacher_sheet(path: Path, year: int, source: str) -> tuple[list[dict], dict]:
    """CDE staff spreadsheet -> teacher FTE by school.

    The current file also carries its own Enrollment Count, which validates
    the join against the membership file rather than merely joining to it
    (finding A11).
    """
    rows = read_sheet(path)
    header_idx = next(
        (i for i, r in enumerate(rows[:25])
         if any(re.search(r"teacher\s*fte", str(v), re.I) for v in r)), None)
    if header_idx is None:
        return [], {"error": "no Teacher FTE column found"}

    header = [str(v).strip() for v in rows[header_idx]]
    find = _column_finder(header)
    cols = {
        "school_code": find(r"school\s*code"),
        "school_name": find(r"school\s*name"),
        "district_code": find(r"(lea|district|organization)\s*code"),
        "teacher_fte": find(r"teacher\s*fte"),
        "enrollment": find(r"enrollment"),
        "ratio": find(r"ratio"),
    }
    if cols["school_code"] is None or cols["teacher_fte"] is None:
        return [], {"error": "missing school code or teacher FTE column", "header": header}

    records = []
    for row in rows[header_idx + 1:]:
        if cols["school_code"] >= len(row):
            continue
        code = normalize_code(row[cols["school_code"]])
        if not code.isdigit():
            continue
        fte = parse_decimal(row[cols["teacher_fte"]]) if cols["teacher_fte"] < len(row) else None
        if fte is None:
            continue
        records.append({
            "year": year,
            "school_code": code,
            "district_code": (normalize_code(row[cols["district_code"]])
                              if cols["district_code"] is not None and cols["district_code"] < len(row) else ""),
            "school_name": (str(row[cols["school_name"]]).strip()
                            if cols["school_name"] is not None and cols["school_name"] < len(row) else ""),
            "teacher_fte": fte,
            "enrollment_reported": (parse_count(row[cols["enrollment"]])
                                    if cols["enrollment"] is not None and cols["enrollment"] < len(row) else None),
            "source": source,
        })

    return records, {
        "header_row": header_idx,
        "columns": header,
        "schools_with_fte": len(records),
        "total_fte": round(sum(r["teacher_fte"] for r in records), 1),
        "carries_own_enrollment": cols["enrollment"] is not None,
    }


# --------------------------------------------------------------------------
# the re-OCR'd yearbooks
# --------------------------------------------------------------------------

def _markdown_rows(text: str) -> list[list[str]]:
    out = []
    for line in text.splitlines():
        if "|" not in line or re.match(r"^\s*\|?\s*[-:| ]+\s*\|?\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if any(cells):
            out.append(cells)
    return out


def parse_yearbook_district_grade(volume_dir: Path, year: int) -> tuple[list[dict], dict]:
    """Table 2 of a yearbook: district x grade, from Datalab markdown.

    Shape, as the re-OCR returns it:
        |                 |      | PREK | K  | 1 | ... | SPEC EDUC | UNGR | TOTAL |
        | COUNTY: EL PASO |      |      |    |   |     |           |      |       |
        | CALHAN          | RJ-1 | 0    | 26 |33 | ... | 0         | 0    | 370   |

    Column 0 is the district name, column 1 its number within the county, and
    a "COUNTY:" row carries the county forward until the next one.
    """
    index_path = volume_dir / "index.json"
    if not index_path.exists():
        return [], {"error": "volume not finished - no index.json"}
    index = json.loads(index_path.read_text())

    records, checks, aggregates = [], {"pass": 0, "fail": 0}, 0
    for page, record in sorted(index["pages"].items(), key=lambda kv: int(kv[0])):
        if "BY SCHOOL DISTRICT AND GRADE" not in (record.get("heading") or "").upper():
            continue
        page_file = volume_dir / f"p{int(page):03d}.md"
        if not page_file.exists():
            continue

        rows = _markdown_rows(page_file.read_text())

        # Find the header ONCE per page, then never re-detect.
        #
        # Re-detecting per row silently destroyed about half the districts. A
        # small rural district whose grade counts happen to be values in 1-12
        # ("5 | 12 | 3 | 8 | 11 | 9 | 7 | 6") satisfies any "looks like eight
        # grade labels" test, so it was read as a new header and reset the
        # column map for every row after it. The loss fell entirely on the
        # smallest districts, which is exactly where it would be least visible.
        grade_cols: dict[int, str] = {}
        start = 0
        for i, cells in enumerate(rows[:6]):
            mapped = {j: normalize_grade(c) for j, c in enumerate(cells) if normalize_grade(c)}
            numeric = [g for g in mapped.values() if g not in ("SPECIAL_EDUCATION", "UNGRADED")]
            if len(numeric) >= 8:
                grade_cols, start = mapped, i + 1
                break
        if not grade_cols:
            continue
        total_idx = max(grade_cols) + 1

        # On some pages Datalab drops the ungraded column outright - not just
        # its header, the whole column - so the row is one value short and its
        # grade cells sum to slightly less than the printed total. St. Vrain
        # summed 15,938 against a printed 16,099, which reads like an OCR
        # error but is a missing column, and it accounted for most of the
        # "failures" from 1990 on.
        #
        # This is recorded rather than repaired, because the values are not in
        # the markdown to recover. It costs nothing the archive needs: summing
        # the 1992 yearbook's numbered grades and subtracting pre-K gives
        # 602,791, and NCES independently reports 602,791 for the same 180
        # districts - exact to the pupil. The numbered grades are intact; only
        # the ungraded count is lost on those pages.
        has_ungraded = "UNGRADED" in grade_cols.values()

        county = ""
        for cells in rows[start:]:
            joined = " ".join(cells)
            county_match = re.search(r"COUNTY:\s*([A-Z][A-Z .'-]+)", joined, re.I)
            if county_match:
                county = county_match.group(1).strip().title()
                # A county header row can also carry the first district.
            if not grade_cols or not cells[0]:
                continue
            name = cells[0].strip()
            if not re.search(r"[A-Za-z]", name) or name.upper().startswith("COUNTY"):
                continue
            # The same aggregate-row trap as the 2010 CDE file, and it was
            # missed here because the guard was only wired into the other
            # parser. These volumes end with a "** STATE TOTALS:" row, and
            # read as a district it doubles the state exactly: 1989 came to
            # 1,108,896 against the 554,296 NCES reports. 1989, 1991 and 1994
            # were all doubled, all at 100.00%, and every row-total checksum
            # passed throughout - an aggregate row sums correctly against
            # itself. Only the independent NCES comparison exposed it.
            #
            # "DENVER COUNTY" and "JEFFERSON COUNTY" are real districts, so
            # the pattern requires the word TOTALS rather than COUNTY alone.
            if AGGREGATE_ROW.search(name.upper()):
                aggregates += 1
                continue

            totals: dict[str, int] = {}
            for j, grade in grade_cols.items():
                if j >= len(cells):
                    continue
                value = parse_count(cells[j])
                if value is not None:
                    totals[grade] = totals.get(grade, 0) + value
            if len(totals) < 8:
                continue

            district_number = cells[1].strip() if len(cells) > 1 else ""
            for grade, value in totals.items():
                records.append({
                    "year": year,
                    "district_code": "",
                    "district_name": name,
                    "district_number": district_number,
                    "county_name": county,
                    "grade": grade,
                    "enrollment": value,
                    "source": f"yearbook-{year}",
                })

            # Every row prints its total; this is the only mechanical proof an
            # OCR'd row was read correctly (finding A14).
            #
            # Only rows carrying the full grade set are checked. Counting a
            # partial row as a failure made this disagree with
            # audit/check-row-totals.py on the same volume - 135/181 here
            # against 137/142 there - which is worse than having one check,
            # because two numbers for one fact means neither can be quoted.
            # The total sits in the column after the last grade column, and
            # its position is taken from the header rather than from the end
            # of the row. Reading "the last numeric cell" instead looked right
            # until a page came back with one column fewer than its header:
            # the ungraded count then posed as the total, and 41 sound rows
            # were reported as failures on the 1990 volume alone. A check that
            # cries wolf is worse than no check, because the real failures
            # stop being visible among them.
            if total_idx is not None and total_idx < len(cells):
                printed = parse_count(cells[total_idx])
                if printed is None:
                    checks["not_checkable"] = checks.get("not_checkable", 0) + 1
                elif sum(totals.values()) == printed:
                    checks["pass"] += 1
                elif not has_ungraded and sum(totals.values()) < printed:
                    # Short by exactly the column the page is missing.
                    checks["ungraded_column_missing"] = checks.get("ungraded_column_missing", 0) + 1
                else:
                    checks["fail"] += 1
            else:
                checks["not_checkable"] = checks.get("not_checkable", 0) + 1

    return records, {
        "districts": len({r["district_name"] for r in records}),
        "records": len(records),
        "row_total_pass": checks["pass"],
        "row_total_fail": checks["fail"],
        "row_total_ungraded_column_missing": checks.get("ungraded_column_missing", 0),
        "row_total_not_checkable": checks.get("not_checkable", 0),
        "aggregate_rows_excluded": aggregates,
    }


# 1999 drops "SELECTED" from the title. Requiring it lost that volume whole.
SUMMARY_HEADING = re.compile(r"SUMMARY OF (SELECTED )?SCHOOL DISTRICT DATA", re.I)

# The summary table's columns, matched against the whole stack of header rows
# joined together. Order is load-bearing twice over: a column is claimed by the
# first pattern that matches it and then taken out of the running, so the
# specific names have to come before the general ones. "TOTAL CERTIFICATED" and
# "TOTAL NONCERTIFICATED" both contain TOTAL, and "PUPIL/SELECTED TEACHER
# RATIO" contains "TEACHER RATIO"; putting the school total and the plain ratio
# last is what stops them taking the wrong column.
SUMMARY_COLUMNS = [
    ("staff_noncertificated_fte", r"NONCERTIFICATED"),
    ("staff_certificated_fte", r"TOTAL CERTIFICATED"),
    ("teacher_fte", r"CLASSROOM TEACHER"),
    ("pupil_selected_teacher_ratio", r"SELECTED"),
    ("pupil_teacher_ratio", r"PUPIL/ ?TEACHER\s*RATIO"),
    ("enrollment", r"\bSTUDENTS\b|PUPIL\s*MEMBERSHIP"),
    ("schools_elementary", r"\bELEMENTARY\b"),
    ("schools_middle", r"\bMIDDLE\b"),
    ("schools_senior", r"\bSENIOR\b"),
    ("schools_other", r"\bOTHER\b"),
    ("schools_total", r"\bTOTAL\b"),
    ("dropout_rate", r"DROPOUT"),
    ("graduation_rate", r"GRADUATION"),
]
SCHOOL_COUNTS = ("schools_elementary", "schools_middle", "schools_senior", "schools_other")
SUMMARY_REQUIRED = {"enrollment", "schools_total", "schools_elementary"}
FALL_YEAR = re.compile(r"FALL\s*(\d{4})")


def _summary_header(text: str) -> str:
    """One header cell, with the print layout taken back out of it.

    The column names are set over two or three lines and hyphenated across
    them, so the OCR returns "ELEMEN-<br>TARY" and "TOTAL NONCER-<br>TIFICATED".
    Undoing the break first means the patterns can match the word rather than
    the typesetting.
    """
    flat = re.sub(r"<br\s*/?>", " ", text or "")
    flat = re.sub(r"<[^>]+>", " ", flat)
    flat = re.sub(r"-\s+", "", flat)
    return re.sub(r"\s+", " ", flat).strip().upper()


def _summary_map(rows: list[list[str]]) -> tuple[dict[str, int], int, int | None, str]:
    """Find the column map, reading the header rows as one stacked block.

    The heading is set over two, three or four lines, and which line carries
    which word moves between volumes: 1992 puts every column name on one row,
    1998 splits "ELEMEN-" and "TARY" across two, and both hang those under a
    group name ("NUMBER OF SCHOOLS") on the row above. Joining the rows down
    each column and matching against the join reads all three layouts without
    knowing which one it is looking at.
    """
    best: tuple[dict[str, int], int, int | None, str] = ({}, 0, None, "")
    width = max((len(r) for r in rows[:6]), default=0)
    for last in range(min(6, len(rows))):
        # Stop before the first row of figures, so a district never joins the
        # header.
        numeric = sum(1 for c in rows[last]
                      if re.fullmatch(r"[\d,]+(\.\d+)?%?", (c or "").strip()))
        if numeric >= 3:
            break
        joined = []
        for j in range(width):
            parts = [rows[i][j] for i in range(last + 1) if j < len(rows[i])]
            joined.append(_summary_header(" ".join(parts)))
        merge = next((j for j, name in enumerate(joined)
                      if re.search(r"\bOTHER TOTAL\b", name)), None)
        if merge is not None:
            joined = joined[:merge] + ["OTHER", "TOTAL"] + joined[merge + 1:]
        found: dict[str, int] = {}
        for key, pattern in SUMMARY_COLUMNS:
            for j, name in enumerate(joined):
                if j in found.values() or key in found or not name:
                    continue
                if re.search(pattern, name):
                    found[key] = j
                    break
        # Take the fullest reading, not the first adequate one. The 1999
        # volume sets "FALL 1998" on the first header row and "CLASSROOM
        # TEACHER F.T.E." two rows below it, so a map built from the first
        # three rows satisfies every requirement and still has no teacher
        # column - which is how 49 districts came back with school counts and
        # no staff at all.
        if SUMMARY_REQUIRED <= set(found) and len(found) > len(best[0]):
            staff_header = joined[found["teacher_fte"]] if "teacher_fte" in found else ""
            best = (found, last + 1, merge, staff_header)
    return best


def _summary_unmerge(cells: list[str], index: int | None) -> list[str]:
    """Undo one cell that holds two columns' worth of a row.

    Where the OCR ran the OTHER and TOTAL headings together it sometimes did
    the same to the figures beneath them, so a row reads "0 2" in one cell.
    Where it did not, the row already has them apart and nothing needs doing.
    """
    if index is None or index >= len(cells):
        return cells
    parts = cells[index].split()
    if len(parts) != 2:
        return cells
    return cells[:index] + parts + cells[index + 1:]


def _summary_row_holds(cells, columns, offset) -> tuple[bool, bool]:
    """Does this reading of the row satisfy the row's own two checks?"""
    def value(key, caster):
        j = columns.get(key)
        if j is None or j == offset:
            return None
        if j > offset:
            j -= 1
        return caster(cells[j]) if j < len(cells) else None

    parts = [value(k, parse_count) for k in SCHOOL_COUNTS]
    total = value("schools_total", parse_count)
    schools_ok = (total is not None and all(p is not None for p in parts)
                  and sum(parts) == total)

    teachers = value("teacher_fte", parse_decimal)
    students = value("enrollment", parse_count)
    ratio = value("pupil_teacher_ratio", parse_decimal)
    ratio_ok = bool(students is not None and teachers and ratio
                    and abs(students / teachers - ratio) <= max(0.06, ratio * 0.02))
    return schools_ok, ratio_ok


def _summary_offset(cells, columns) -> tuple[int, int]:
    """Where, if anywhere, this row lost a cell - and so where it shifted.

    A row that drops one cell in the middle pulls everything after it one
    place left, and the result is not obviously wrong: Denver's 1994 row lost
    its school total and came back with 62,773 teachers and 17 pupils, while
    Colorado Springs lost its non-certificated staff in 1996 and came back
    with 33,175 teachers. Both are the state's largest districts, so dropping
    them would be visible, and both are recoverable - because the row prints
    the ratio between two of its own columns, and the shift only divides
    correctly in one position.

    Every possible loss point is tried and one is accepted only if the row
    then satisfies both of its checks, having satisfied neither or only one
    before. Returns the column index that was lost (or a sentinel past the
    end, meaning the row is whole) and 1 when a shift was applied.
    """
    whole = len(cells) + 1
    if _summary_row_holds(cells, columns, whole)[1]:
        return whole, 0
    first = min(columns.values())
    for offset in range(first, max(columns.values()) + 1):
        schools_ok, ratio_ok = _summary_row_holds(cells, columns, offset)
        if ratio_ok and (schools_ok or columns.get("schools_total", -1) == offset):
            return offset, 1
    return whole, 0


def parse_yearbook_district_summary(volume_dir: Path, year: int) -> tuple[list[dict], dict]:
    """The yearbook's summary table: district staff and school counts.

    Printed as Table 1 in some volumes and Table 2 in others, under a heading
    that does not change: "SUMMARY OF SELECTED SCHOOL DISTRICT DATA". Thirteen
    columns, of which the archive takes the schools, the staff and the two
    figures that check them:

        |            |     | ELEM | MID | SEN | OTH | TOT | NONCERT | CERT |
        |            |     | CLASSROOM TEACHERS | STUDENTS | RATIO | ... |
        | COUNTY: ADAMS    |                                                |
        | MAPLETON   | 1   | 6 | 2 | 1 | 1 | 10 | 181.5 | 274.8 | 226.8 |
        |            |     | 4,941 | 21.8 | 29.4 | 3.3 |

    Two checks come from the row itself, and both are recorded rather than
    used to silently drop rows: the four school counts must add to the printed
    total, and students divided by classroom teachers must be the printed
    ratio. A row failing either is kept and flagged, because unlike the modern
    ratio reports there is no second file to fall back on for these years.
    """
    index_path = volume_dir / "index.json"
    if not index_path.exists():
        return [], {"error": "volume not finished - no index.json"}
    index = json.loads(index_path.read_text())

    records: list[dict] = []
    checks = {"schools_pass": 0, "schools_fail": 0, "ratio_pass": 0, "ratio_fail": 0}
    aggregates = repaired = 0

    # The table's span, not only the pages whose running head the OCR could
    # read. Two pages - 1996's p025 and 1997's p031 - came back with an empty
    # heading, and taking only the flagged pages dropped both, with each
    # volume quietly losing about thirty districts. This is the same fault the
    # page selection in datalab-ocr.py had, one layer further down: a page
    # that is never read cannot fail a check. A page inside the span that
    # holds something else has no header to find and is skipped anyway.
    flagged = [int(page) for page, record in index["pages"].items()
               if SUMMARY_HEADING.search(record.get("heading") or "")]
    if not flagged:
        return [], {"error": "no summary pages in this volume"}
    span = range(min(flagged), max(flagged) + 1)

    for page in span:
        page_file = volume_dir / f"p{page:03d}.md"
        if not page_file.exists():
            continue
        rows = _markdown_rows(page_file.read_text())

        columns, start, merged_at, staff_header = _summary_map(rows)
        if not columns:
            continue
        # 1999 prints Fall 1999 membership beside Fall 1998 teachers, in one
        # row, under two different "FALL" headings. Filing those teachers
        # under 1999 would put a year's staffing one year out - and the row's
        # own ratio is the 1998 one, so the arithmetic check fails on every
        # row rather than passing quietly. The heading says which year the
        # staff belong to, so the heading is what decides.
        stated = FALL_YEAR.search(staff_header)
        staff_year = int(stated.group(1)) if stated else year

        # Everything left of the first measure is the district's name and its
        # number within the county, which some pages split and some do not.
        first = min(columns.values())
        county = ""
        for cells in rows[start:]:
            cells = _summary_unmerge(cells, merged_at)
            label = re.sub(r"<[^>]+>", "", cells[0]).strip() if cells else ""
            # A county heading is written "COUNTY: ADAMS" in the earlier
            # volumes and "ADAMS COUNTY" on its own row, underlined, from 1998.
            if label.upper().startswith("COUNTY:"):
                county = label.split(":", 1)[1].strip()
                continue
            if (label.upper().endswith(" COUNTY")
                    and not any(c.strip() for c in cells[1:])):
                county = label[: -len(" COUNTY")].strip()
                continue
            name = " ".join(re.sub(r"<[^>]+>", "", c).strip()
                            for c in cells[:first] if c.strip())
            name = name.strip()
            if not name:
                continue
            if AGGREGATE_ROW.search(name) or name.upper().startswith("TOTAL"):
                aggregates += 1
                continue

            offset, shifted = _summary_offset(cells, columns)

            def cell(key: str, offset=offset):
                j = columns.get(key)
                if j is None:
                    return ""
                if j == offset:
                    return ""          # the cell the row lost
                if j > offset:
                    j -= 1
                return cells[j] if j < len(cells) else ""

            teacher_fte = parse_decimal(cell("teacher_fte"))
            enrollment = parse_count(cell("enrollment"))
            if teacher_fte is None and enrollment is None:
                continue
            repaired += shifted

            row = {
                "year": year,
                "staff_year": staff_year,
                "county_name": county,
                "district_name": name,
                "source": f"yearbook-{year}-summary",
            }
            for key in ("schools_elementary", "schools_middle", "schools_senior",
                        "schools_other", "schools_total"):
                row[key] = parse_count(cell(key))
            for key in ("staff_noncertificated_fte", "staff_certificated_fte"):
                row[key] = parse_decimal(cell(key))
            row["teacher_fte"] = teacher_fte
            row["enrollment"] = enrollment
            row["pupil_teacher_ratio"] = parse_decimal(cell("pupil_teacher_ratio"))
            row["dropout_rate"] = parse_decimal(cell("dropout_rate"))
            row["graduation_rate"] = parse_decimal(cell("graduation_rate"))

            parts = [row[k] for k in SCHOOL_COUNTS]
            if row["schools_total"] is not None and all(p is not None for p in parts):
                ok = sum(parts) == row["schools_total"]
                checks["schools_pass" if ok else "schools_fail"] += 1
                row["schools_check"] = "pass" if ok else "fail"
            else:
                row["schools_check"] = ""

            ratio = row["pupil_teacher_ratio"]
            # The check only means anything where the two figures are from the
            # same autumn. In the 1999 volume they are not, and its ratio is
            # the one the file prints for 1998 - so there is nothing here to
            # check the 1998 staffing against except NCES.
            if staff_year != year:
                ratio = None
            if enrollment is not None and teacher_fte and ratio:
                # The ratio is printed to one decimal, so a correct row can be
                # out by half of that plus the rounding of the figures it came
                # from. Anything past 2% is a misread column, not rounding.
                ok = abs(enrollment / teacher_fte - ratio) <= max(0.06, ratio * 0.02)
                checks["ratio_pass" if ok else "ratio_fail"] += 1
                row["ratio_check"] = "pass" if ok else "fail"
            else:
                row["ratio_check"] = ""
            records.append(row)

    info = {
        "districts": len(records),
        "aggregate_rows_skipped": aggregates,
        "rows_realigned": repaired,
        **checks,
        "staff_year": records[0]["staff_year"] if records else year,
        "total_teacher_fte": round(sum(r["teacher_fte"] or 0 for r in records), 1),
        "total_schools": sum(r["schools_total"] or 0 for r in records),
    }
    return records, info


def parse_yearbook_trends(volume_dir: Path, year: int) -> tuple[list[dict], dict]:
    """Table 4: ten years of district membership on four measures.

    The 1986 volume runs 1977-78 to 1986-87, and each later volume carries its
    own rolling window, so the volumes overlap and read the same district-years
    independently (finding A2).

        | MAPLETON 1               | COUNTY: ADAMS |       |...
        | FALL MEMBERSHIP          | 5,770         | 5,436 |...
        | CLOSING DAY MEMBERSHIP   | 5,548         | 5,112 |...
    """
    index_path = volume_dir / "index.json"
    if not index_path.exists():
        return [], {"error": "volume not finished - no index.json"}
    index = json.loads(index_path.read_text())

    measures = {
        "FALL MEMBERSHIP": "fall_membership",
        "CLOSING DAY MEMBERSHIP": "closing_day_membership",
        "AVERAGE DAILY MEMBERSHIP": "average_daily_membership",
        "ADAE": "adae",
    }

    records = []
    for page, record in sorted(index["pages"].items(), key=lambda kv: int(kv[0])):
        if "TRENDS IN ENROLLMENT" not in (record.get("heading") or "").upper():
            continue
        page_file = volume_dir / f"p{int(page):03d}.md"
        if not page_file.exists():
            continue

        school_years: list[str] = []
        district = county = ""
        for cells in _markdown_rows(page_file.read_text()):
            years_in_row = [c for c in cells if re.fullmatch(r"(19|20)\d{2}-\d{2}", c.strip())]
            if len(years_in_row) >= 5:
                school_years = years_in_row
                continue
            if not cells[0]:
                continue
            label = cells[0].strip().upper()
            measure = measures.get(label)
            if measure is None:
                joined = " ".join(cells)
                county_match = re.search(r"COUNTY:\s*([A-Z][A-Z .'-]+)", joined, re.I)
                if county_match and re.search(r"[A-Za-z]", cells[0]):
                    district = cells[0].strip()
                    county = county_match.group(1).strip().title()
                continue
            if not district or not school_years:
                continue
            values = [c for c in cells[1:] if c.strip()]
            for school_year, raw in zip(school_years, values):
                value = parse_decimal(raw)
                if value is None:
                    continue
                records.append({
                    "year": int(school_year[:4]),
                    "school_year": school_year,
                    "district_name": district,
                    "county_name": county,
                    "measure": measure,
                    "value": value,
                    "source": f"yearbook-{year}-table4",
                })

    return records, {
        "districts": len({r["district_name"] for r in records}),
        "records": len(records),
        "years": sorted({r["year"] for r in records})[:3] + ["..."] if records else [],
    }


# --------------------------------------------------------------------------
# NCES CCD
# --------------------------------------------------------------------------

def _fetch_json(url: str, tries: int = 4) -> dict:
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_ccd_year(year: int, cache_dir: Path) -> tuple[list[dict], list[dict]]:
    """CCD directory and enrollment for Colorado, cached to disk."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    directory_path = cache_dir / f"ccd-directory-{year}.json"
    if not directory_path.exists():
        rows, url = [], f"{CCD_API}/directory/{year}/?fips=8"
        while url:
            page = _fetch_json(url)
            rows.extend(page["results"])
            url = page.get("next")
        directory_path.write_text(json.dumps(rows))

    enrollment_path = cache_dir / f"ccd-enrollment-{year}.json"
    if not enrollment_path.exists():
        rows = []
        for grade in list(range(-1, 15)) + [99]:
            url = f"{CCD_API}/enrollment/{year}/grade-{grade}/?fips=8"
            try:
                while url:
                    page = _fetch_json(url)
                    rows.extend(page["results"])
                    url = page.get("next")
            except Exception:  # noqa: BLE001
                continue
        enrollment_path.write_text(json.dumps(rows))

    return (json.loads(directory_path.read_text()),
            json.loads(enrollment_path.read_text()))


def ccd_records(year: int, cache_dir: Path) -> tuple[list[dict], list[dict], dict]:
    """CCD -> (enrollment long records, school-year records, metadata)."""
    directory, enrollment = fetch_ccd_year(year, cache_dir)

    info = {}
    for row in directory:
        info[row["ncessch"]] = {
            "school_name": row.get("school_name") or "",
            "district_name": (row.get("lea_name") or "").strip(),
            "school_code": normalize_ccd_state_code(row.get("seasch")),
            "leaid": row.get("leaid") or "",
            "teachers_fte": parse_decimal(row.get("teachers_fte")),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "charter": row.get("charter"),
            "status": row.get("school_status"),
            "lowest_grade": row.get("lowest_grade_offered"),
            "highest_grade": row.get("highest_grade_offered"),
        }

    long_records, totals = [], {}
    for row in enrollment:
        grade = CCD_GRADE.get(row.get("grade"))
        value = parse_count(row.get("enrollment"))
        if value is None:
            continue
        if row.get("grade") == 99:
            totals[row["ncessch"]] = value
            continue
        if grade is None:
            continue
        meta = info.get(row["ncessch"], {})
        long_records.append({
            "year": year,
            "ncessch": row["ncessch"],
            "school_code": meta.get("school_code", ""),
            "district_code": "",
            "district_name": meta.get("district_name", ""),
            "school_name": meta.get("school_name", ""),
            "grade": grade,
            "enrollment": value,
            "source": f"ccd-{year}",
        })

    school_years = []
    for ncessch, meta in info.items():
        has_coords = usable_coordinate(meta["latitude"], meta["longitude"])
        school_years.append({
            "year": year,
            "ncessch": ncessch,
            "school_code": meta["school_code"],
            "leaid": meta["leaid"],
            "school_name": meta["school_name"],
            "district_name": meta["district_name"],
            "teacher_fte_ccd": meta["teachers_fte"],
            "enrollment_total_ccd": totals.get(ncessch),
            "latitude": meta["latitude"] if has_coords else None,
            "longitude": meta["longitude"] if has_coords else None,
            "is_charter": meta["charter"],
            "status": meta["status"],
            "lowest_grade": meta["lowest_grade"],
            "highest_grade": meta["highest_grade"],
            "source": f"ccd-{year}",
        })

    raw_ids = [r.get("seasch") for r in directory if r.get("seasch")]
    meta = {
        "directory_rows": len(directory),
        "enrollment_rows": len(enrollment),
        "schools_with_grade_rows": len({r["ncessch"] for r in long_records}),
        "schools_with_teacher_fte": sum(1 for s in school_years if s["teacher_fte_ccd"]),
        "schools_with_usable_coordinates": sum(1 for s in school_years if s["latitude"] is not None),
        "state_id_format": ("district-school" if raw_ids and "-" in str(raw_ids[0]) else "bare school code"),
        "prek_rows": sum(1 for r in enrollment if r.get("grade") == -1),
    }
    return long_records, school_years, meta
