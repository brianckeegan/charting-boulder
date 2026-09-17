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


def _column_finder(header: list[str]):
    def find(*patterns: str) -> int | None:
        for j, name in enumerate(header):
            for pattern in patterns:
                if re.search(pattern, name, re.I):
                    return j
        return None
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
    find = _column_finder(header)

    # Header wording drifts hard across 24 vintages: "School Code" becomes
    # "Sch Code", "District Code" becomes "Distr Code", and from about 2019
    # the district pair is renamed "Organization". Matching only the long
    # spellings silently lost nine of the twenty-four years.
    cols = {
        "school_code": find(r"^(school|sch)\s*(code|number|no)\b", r"(school|sch).*code"),
        "school_name": find(r"^(school|sch)\s*name", r"^school$"),
        "district_code": find(r"(district|distr|lea|organization).*(code|number|no)"),
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

    records, checks = [], {"pass": 0, "fail": 0}
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
            printed = None
            for cell in reversed(cells):
                printed = parse_count(cell)
                if printed is not None:
                    break
            summed = sum(totals.values())
            if printed is not None:
                checks["pass" if summed == printed else "fail"] += 1

    return records, {
        "districts": len({r["district_name"] for r in records}),
        "records": len(records),
        "row_total_pass": checks["pass"],
        "row_total_fail": checks["fail"],
    }


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
