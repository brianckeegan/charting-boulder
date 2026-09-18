"""Harmonize every source onto one schema and write data/processed/.

Phases C, S and V of TASK.md. This is where the four source shapes stop being
four things:

  - CDE school spreadsheets      2003-2025, school x grade
  - NCES CCD                     1986-2023, school x grade + teacher FTE
  - CDE staff spreadsheets       teacher FTE by school
  - re-OCR'd yearbooks           1986-1999 district x grade, and district
                                 trends reaching back to 1977-78

Joins:
  school   CDE school_code <-> CCD seasch, both normalized to a zero-padded
           four-digit string. The registry keys on the NCES id, which is
           stable across renames and code changes; CDE codes are not unique
           statewide in every year.
  district yearbook district names <-> CDE district codes, by normalized name
           within county. Names are the only key the yearbooks print.

Run:  python3 -m pipeline.normalize
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from .extract import (
    ccd_records,
    parse_cde_school_sheet,
    parse_cde_teacher_sheet,
    parse_yearbook_district_grade,
    parse_yearbook_district_summary,
    parse_yearbook_trends,
)
from .schema import normalize_code

HERE = Path(__file__).resolve().parent.parent
RAW_CDE = HERE / "data" / "raw" / "cde"
CCD_CACHE = HERE / "data" / "raw" / "ccd"
YEARBOOKS = HERE / "data" / "interim" / "yearbooks"
PROCESSED = HERE / "data" / "processed"
LOOKUPS = HERE / "data" / "lookups"
AUDIT = HERE / "audit"

CCD_YEARS = range(1986, 2025)  # 2024 was released since the audit


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path.relative_to(HERE)}: {len(rows):,} rows")


# --------------------------------------------------------------------------
# district name matching
# --------------------------------------------------------------------------

DISTRICT_SUFFIX = re.compile(
    r"\b(RE|R|J|JT|RJ|RD|C|UD)?[-\s]?\d+\s*(J|JT|J1|A)?$", re.I)


def split_district_name(name: str) -> tuple[str, str]:
    """Split a district name into its base and its organisational suffix.

    The suffix is printed inconsistently across volumes - the same district is
    "AGATE" in one book and "AGATE 300" in the next, "CALHAN" and "CALHAN
    RJ-1", "AULT-HIGHLAND RE-9" and "AULT-HIGHLAND" - and some names carry a
    footnote asterisk. So it cannot simply be kept, or the same district fails
    to match itself across two books.

    Nor can it simply be dropped: Garfield RE-2 (Rifle, about 1,560 pupils)
    and Garfield 16 (Parachute, about 165) are different districts in the same
    county, distinguishable only by that suffix. `district_key` therefore
    keeps it only where it does real work.
    """
    text = re.sub(r"[*†‡]", " ", str(name).upper())
    text = re.sub(r"[^A-Z0-9 -]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"\s((?:RE|R|J|JT|RJ|RD|C|UD)?[- ]?\d+[A-Z]*)$", text)
    if match:
        return text[:match.start()].strip(), re.sub(r"[^A-Z0-9]", "", match.group(1))
    return text, ""


def base_key(name: str, county: str = "") -> str:
    base, _ = split_district_name(name)
    base = re.sub(r"[^A-Z0-9]", "", base)
    county_key = re.sub(r"[^A-Z]", "", str(county).upper())
    return f"{county_key}|{base}" if county_key else base


# A Board of Cooperative Educational Services is a shared agency several
# districts run together, not a district. The yearbooks list them alongside
# districts, which is why a volume reports 180-183 reporting units where
# Colorado had 176 districts.
#
# They are flagged, never removed. Their pupils are real and NCES counts them
# too: dropping the 185 BOCES pupils from 1992 turns an exact match with NCES
# into a 185-pupil shortfall, and the same in 1993, 1996 and 1999. The count
# of districts is what was misleading, not the totals.
BOCES = re.compile(r"\bBOCE?S\b|BOARD OF COOPERATIVE", re.I)


def unit_type(name: str) -> str:
    return "boces" if BOCES.search(str(name)) else "district"


# Base keys that need their suffix to stay, because two real districts share
# the base. Filled by index_district_names() before any key is built.
_AMBIGUOUS: set[str] = set()


def index_district_names(rows: list[dict]) -> None:
    """Find the base names that more than one district actually uses."""
    suffixes: dict[str, set] = defaultdict(set)
    for row in rows:
        key = base_key(row.get("district_name", ""), row.get("county_name", ""))
        _, suffix = split_district_name(row.get("district_name", ""))
        if suffix:
            suffixes[key].add(suffix)
    _AMBIGUOUS.clear()
    _AMBIGUOUS.update(k for k, found in suffixes.items() if len(found) > 1)


def district_key(name: str, county: str = "") -> str:
    """A comparable key for a district name.

    County plus base name, with the organisational suffix appended only where
    two real districts share that base (see `index_district_names`).
    """
    key = base_key(name, county)
    if key in _AMBIGUOUS:
        _, suffix = split_district_name(name)
        return f"{key}#{suffix}" if suffix else key
    return key


def build_district_crosswalk(cde_school_records: list[dict]) -> dict[str, dict]:
    """Map a district name key to a CDE district code.

    Built from the CDE school files themselves, which carry both the code and
    the name, so it needs no hand-maintained list. Later years win where a
    name is reused, because the modern code is the one the archive keys on.
    """
    by_key: dict[str, dict] = {}
    for record in sorted(cde_school_records, key=lambda r: r["year"]):
        code, name = record["district_code"], record["district_name"]
        if not code or not name:
            continue
        for key in {district_key(name), district_key(name, record.get("county_name", ""))}:
            if not key or key.endswith("|"):
                continue
            by_key[key] = {"district_code": code, "district_name": name}
    return by_key


# --------------------------------------------------------------------------

def load_cde_school() -> tuple[list[dict], dict]:
    """Every CDE school-by-grade spreadsheet the fetch step landed."""
    records, meta = [], {}
    for path in sorted(RAW_CDE.glob("enrollment-school-*.xls*")):
        year = int(re.search(r"(\d{4})", path.name).group(1))
        rows, info = parse_cde_school_sheet(path, year, path.name)
        records.extend(rows)
        meta[year] = info
        note = info.get("error") or f"{info['schools']:,} schools, totals {info['row_total_pass']}/{info['row_total_pass'] + info['row_total_fail']}"
        print(f"  CDE enrollment {year}: {note}")
    return records, meta


def load_cde_teacher() -> tuple[list[dict], dict]:
    """Teacher FTE by school, preferring the eleven-year table.

    pipeline/teacher_fte.py reads every staff report CDE publishes in either
    serial and writes data/processed/school-teacher-fte.csv. That table is a
    superset of the three spreadsheet years this module used to read on its
    own, so it is the source when it exists. The glob is kept as the fallback
    for a checkout where the staff step has not been run.
    """
    table = PROCESSED / "school-teacher-fte.csv"
    if table.exists():
        records, by_year = [], defaultdict(lambda: {"schools_with_fte": 0, "total_fte": 0.0})
        with table.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                year = int(row["year"])
                fte = float(row["teacher_fte"]) if row["teacher_fte"] else None
                records.append({
                    "year": year,
                    "school_code": normalize_code(row["school_code"], 4),
                    "district_code": normalize_code(row["district_code"], 4),
                    "teacher_fte": row["teacher_fte"],
                    "enrollment_reported": row["enrollment_reported"],
                    "source": row["source"],
                })
                if fte is not None:
                    by_year[year]["schools_with_fte"] += 1
                    by_year[year]["total_fte"] += fte
        meta = dict(sorted(by_year.items()))
        for year, info in meta.items():
            print(f"  CDE teacher FTE {year}: {info['schools_with_fte']:,} schools, "
                  f"{info['total_fte']:,.1f} FTE")
        return records, meta

    print("  CDE teacher FTE: school-teacher-fte.csv absent; "
          "reading the spreadsheet years only (run pipeline.teacher_fte first)")
    records, meta = [], {}
    for path in sorted(RAW_CDE.glob("teacher_fte-school-*.xls*")):
        year = int(re.search(r"(\d{4})", path.name).group(1))
        rows, info = parse_cde_teacher_sheet(path, year, path.name)
        records.extend(rows)
        meta[year] = info
        note = info.get("error") or f"{info['schools_with_fte']:,} schools, {info['total_fte']:,.1f} FTE"
        print(f"  CDE teacher FTE {year}: {note}")
    return records, meta


def load_ccd() -> tuple[list[dict], list[dict], dict]:
    enrollment, school_years, meta = [], [], {}
    for year in CCD_YEARS:
        try:
            rows, schools, info = ccd_records(year, CCD_CACHE)
        except Exception as exc:  # noqa: BLE001
            print(f"  CCD {year}: unavailable ({exc})")
            continue
        enrollment.extend(rows)
        school_years.extend(schools)
        meta[year] = info
        print(f"  CCD {year}: {info['directory_rows']:,} schools, "
              f"{info['schools_with_teacher_fte']:,} with FTE, "
              f"{info['schools_with_usable_coordinates']:,} located")
    return enrollment, school_years, meta


def load_yearbooks() -> tuple[list[dict], list[dict], list[dict], dict]:
    grade_records, trend_records, summary_records, meta = [], [], [], {}
    for volume in sorted(YEARBOOKS.iterdir()):
        if not volume.is_dir() or not volume.name.isdigit():
            continue
        year = int(volume.name)
        grades, ginfo = parse_yearbook_district_grade(volume, year)
        trends, tinfo = parse_yearbook_trends(volume, year)
        summary, sinfo = parse_yearbook_district_summary(volume, year)
        grade_records.extend(grades)
        trend_records.extend(trends)
        summary_records.extend(summary)
        meta[year] = {"district_by_grade": ginfo, "trends": tinfo, "summary": sinfo}
        if "error" in ginfo:
            print(f"  yearbook {year}: {ginfo['error']}")
        else:
            staff = ("" if sinfo.get("error") else
                     f"; summary {sinfo['districts']} districts, "
                     f"{sinfo['total_teacher_fte']:,.0f} FTE"
                     + (f" (staff {sinfo['staff_year']})"
                        if sinfo.get("staff_year") != year else ""))
            print(f"  yearbook {year}: {ginfo['districts']} districts, "
                  f"totals {ginfo['row_total_pass']}/{ginfo['row_total_pass'] + ginfo['row_total_fail']}; "
                  f"trends {tinfo.get('districts', 0)} districts{staff}")
    return grade_records, trend_records, summary_records, meta


# --------------------------------------------------------------------------

def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    print("Reading CDE school spreadsheets")
    cde_school, cde_school_meta = load_cde_school()
    print("Reading CDE staff spreadsheets")
    cde_teacher, cde_teacher_meta = load_cde_teacher()
    print("Reading NCES CCD")
    ccd_enrollment, ccd_schools, ccd_meta = load_ccd()
    print("Reading re-OCR'd yearbooks")
    yb_grades, yb_trends, yb_summary, yb_meta = load_yearbooks()

    # ---- school identity -------------------------------------------------
    # CCD carries the NCES id and the CDE school code together, so it is the
    # bridge. Build (year, school_code) -> ncessch, then fall back to any year
    # for a school CDE reports but CCD does not cover.
    ncessch_by_year_code: dict[tuple[int, str], str] = {}
    ncessch_by_code: dict[str, str] = {}
    for row in ccd_schools:
        if row["school_code"]:
            ncessch_by_year_code[(row["year"], row["school_code"])] = row["ncessch"]
            ncessch_by_code.setdefault(row["school_code"], row["ncessch"])

    matched = 0
    for row in cde_school:
        key = (row["year"], row["school_code"])
        ncessch = ncessch_by_year_code.get(key) or ncessch_by_code.get(row["school_code"], "")
        row["ncessch"] = ncessch
        if ncessch:
            matched += 1
    report["cde_rows_matched_to_nces_id"] = {
        "matched": matched, "total": len(cde_school),
        "rate": round(matched / len(cde_school), 4) if cde_school else None,
    }

    # ---- school enrollment panel ----------------------------------------
    print("\nBuilding the school panel")
    cde_index = {(r["year"], r["school_code"], r["grade"]): r for r in cde_school}
    ccd_index = {(r["year"], r["school_code"], r["grade"]): r for r in ccd_enrollment if r["school_code"]}

    # Deliberately narrow. Names, districts and coordinates live in
    # school-year.csv, one row per school-year rather than repeated on each of
    # a school's fourteen grade rows. Carrying them here, plus a source
    # filename per row, made this file 65 MB; the attributes are identical
    # within a school-year, so repeating them is storage without information.
    # `source` collapses to a one-letter flag for the same reason.
    panel = []
    for key in sorted(set(cde_index) | set(ccd_index)):
        year, code, grade = key
        c, n = cde_index.get(key), ccd_index.get(key)
        panel.append({
            "year": year,
            "ncessch": (c or {}).get("ncessch") or (n or {}).get("ncessch", ""),
            "school_code": code,
            "district_code": (c or {}).get("district_code", ""),
            "grade": grade,
            "enrollment_cde": c["enrollment"] if c else "",
            "enrollment_ccd": n["enrollment"] if n else "",
            "source": ("both" if c and n else "cde" if c else "ccd"),
        })
    write_csv(PROCESSED / "school-enrollment-by-grade.csv", panel, [
        "year", "ncessch", "school_code", "district_code",
        "grade", "enrollment_cde", "enrollment_ccd", "source"])

    # ---- school-year table ----------------------------------------------
    cde_totals: dict[tuple[int, str], int] = defaultdict(int)
    for row in cde_school:
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED"):
            cde_totals[(row["year"], row["school_code"])] += row["enrollment"]
    fte_index = {(r["year"], r["school_code"]): r for r in cde_teacher}
    ccd_school_index = {(r["year"], r["school_code"]): r for r in ccd_schools if r["school_code"]}
    # Coordinates come from the most recent year that has a real one, carried
    # backward by school id (finding A12).
    coords: dict[str, tuple] = {}
    for row in sorted(ccd_schools, key=lambda r: r["year"]):
        if row["latitude"] is not None:
            coords[row["ncessch"]] = (row["latitude"], row["longitude"])

    names = {(r["year"], r["school_code"]): r for r in cde_school}
    school_year_rows = []
    for key in sorted(set(cde_totals) | set(ccd_school_index)):
        year, code = key
        c = names.get(key, {})
        n = ccd_school_index.get(key, {})
        fte = fte_index.get(key, {})
        ncessch = c.get("ncessch") or n.get("ncessch", "")
        latitude, longitude = coords.get(ncessch, (None, None))
        school_year_rows.append({
            "year": year,
            "ncessch": ncessch,
            "school_code": code,
            "district_code": c.get("district_code", ""),
            "school_name": c.get("school_name") or n.get("school_name", ""),
            "district_name": c.get("district_name") or n.get("district_name", ""),
            "enrollment_total_cde": cde_totals.get(key, ""),
            "enrollment_total_ccd": n.get("enrollment_total_ccd") or "",
            "teacher_fte_cde": fte.get("teacher_fte", ""),
            "teacher_fte_ccd": n.get("teacher_fte_ccd") or "",
            "enrollment_reported_in_fte_file": fte.get("enrollment_reported", ""),
            "latitude": latitude if latitude is not None else "",
            "longitude": longitude if longitude is not None else "",
            "is_charter": n.get("is_charter", ""),
            "status": n.get("status", ""),
        })
    write_csv(PROCESSED / "school-year.csv", school_year_rows, [
        "year", "ncessch", "school_code", "district_code", "school_name", "district_name",
        "enrollment_total_cde", "enrollment_total_ccd", "teacher_fte_cde", "teacher_fte_ccd",
        "enrollment_reported_in_fte_file", "latitude", "longitude", "is_charter", "status"])

    # ---- registry and closures ------------------------------------------
    print("\nBuilding the school registry")
    seen: dict[str, dict] = {}
    for row in sorted(school_year_rows, key=lambda r: r["year"]):
        key = row["ncessch"] or f"CDE:{row['school_code']}"
        entry = seen.setdefault(key, {
            "ncessch": row["ncessch"], "school_codes": set(), "names": [],
            "district_codes": set(), "first_year": row["year"], "last_year": row["year"],
            "last_status": "", "latitude": row["latitude"], "longitude": row["longitude"],
        })
        entry["school_codes"].add(row["school_code"])
        if row["school_name"] and row["school_name"] not in entry["names"]:
            entry["names"].append(row["school_name"])
        if row["district_code"]:
            entry["district_codes"].add(row["district_code"])
        entry["last_year"] = max(entry["last_year"], row["year"])
        entry["first_year"] = min(entry["first_year"], row["year"])
        if row["status"]:
            entry["last_status"] = row["status"]

    last_panel_year = max((r["year"] for r in school_year_rows), default=0)
    code_owners: dict[str, set] = defaultdict(set)
    for key, entry in seen.items():
        for code in entry["school_codes"]:
            code_owners[code].add(key)
    name_index: dict[str, set] = defaultdict(set)
    for key, entry in seen.items():
        for name in entry["names"]:
            name_index[re.sub(r"[^A-Z]", "", name.upper())].add(key)

    registry = []
    for key, entry in sorted(seen.items()):
        still_open = entry["last_year"] >= last_panel_year
        reused = any(len(code_owners[c]) > 1 for c in entry["school_codes"])
        name_twin = any(len(name_index[re.sub(r"[^A-Z]", "", n.upper())]) > 1 for n in entry["names"])

        if still_open:
            label, confidence, evidence = "still_open", "high", f"reported in {last_panel_year}"
        elif str(entry["last_status"]) in ("2", "6"):
            label, confidence, evidence = "closed", "high", f"CCD school_status={entry['last_status']}"
        elif name_twin:
            label, confidence, evidence = "renamed", "low", "another school carries the same name"
        elif reused:
            label, confidence, evidence = "code_changed", "low", "school code later used by another school"
        else:
            label, confidence, evidence = "closed", "medium", "stopped reporting; no status field"

        registry.append({
            "ncessch": entry["ncessch"],
            "school_codes": ";".join(sorted(entry["school_codes"])),
            "names": ";".join(entry["names"]),
            "district_codes": ";".join(sorted(entry["district_codes"])),
            "first_year": entry["first_year"],
            "last_year": entry["last_year"],
            "closure_label": label,
            "closure_confidence": confidence,
            "closure_evidence": evidence,
            "latitude": entry["latitude"],
            "longitude": entry["longitude"],
        })
    write_csv(PROCESSED / "schools.csv", registry, [
        "ncessch", "school_codes", "names", "district_codes", "first_year", "last_year",
        "closure_label", "closure_confidence", "closure_evidence", "latitude", "longitude"])

    # ---- district tier ---------------------------------------------------
    print("\nBuilding the district tier")
    crosswalk = build_district_crosswalk(cde_school)
    (LOOKUPS / "district-crosswalk.json").write_text(
        json.dumps(crosswalk, indent=2, sort_keys=True) + "\n")

    matched_districts = 0
    for row in yb_grades:
        hit = (crosswalk.get(district_key(row["district_name"], row["county_name"]))
               or crosswalk.get(district_key(row["district_name"])))
        if hit:
            row["district_code"] = hit["district_code"]
            matched_districts += 1
    report["yearbook_rows_matched_to_district_code"] = {
        "matched": matched_districts, "total": len(yb_grades),
        "rate": round(matched_districts / len(yb_grades), 4) if yb_grades else None,
    }

    district_grade = [{
        "year": r["year"], "district_code": r["district_code"], "district_name": r["district_name"],
        "county_name": r["county_name"], "unit_type": unit_type(r["district_name"]),
        "grade": r["grade"], "enrollment": r["enrollment"], "source": r["source"],
    } for r in yb_grades]

    # The modern era's district tier is the school panel summed by district.
    modern: dict[tuple, int] = defaultdict(int)
    modern_names: dict[tuple, str] = {}
    for row in cde_school:
        key = (row["year"], row["district_code"], row["grade"])
        modern[key] += row["enrollment"]
        modern_names[(row["year"], row["district_code"])] = row["district_name"]
    for (year, code, grade), value in sorted(modern.items()):
        district_grade.append({
            "year": year, "district_code": code,
            "district_name": modern_names.get((year, code), ""), "county_name": "",
            "unit_type": unit_type(modern_names.get((year, code), "")),
            "grade": grade, "enrollment": value, "source": "cde-school-sum",
        })
    write_csv(PROCESSED / "district-enrollment-by-grade.csv", district_grade, [
        "year", "district_code", "district_name", "county_name", "unit_type",
        "grade", "enrollment", "source"])

    # District-year: one continuous fall-membership series, 1977 to the
    # present.
    #
    # Each volume reprints the previous nine years, so most district-years are
    # read from two or more books, and summing them all gave 700,000 pupils
    # for 1978 against Colorado's actual 560,000.
    #
    # One volume supplies each year outright, rather than merging readings
    # district by district across books.
    #
    # Merging looked reasonable and was not. The same district is "AGATE" in
    # one volume and "AGATE 300" in the next, "CALHAN" and "CALHAN RJ-1",
    # "DOLORES COUNTY RE NO" and "DOLORES RE-2" - real renames as well as
    # inconsistent printing. Matching by name reached 82%, and the residue
    # double-counted, inflating 1978 to 700,000 pupils against Colorado's
    # actual 560,000. A name-matching rule good enough for a total would have
    # to be perfect, and this one cannot be.
    #
    # Taking every row for a year from a single volume removes the problem
    # instead of mitigating it. Name matching is still used for the overlap
    # comparison below, where failing to match two readings costs a
    # comparison rather than corrupting a sum.
    volumes_by_year: dict[int, set] = defaultdict(set)
    for row in yb_trends:
        volumes_by_year[row["year"]].add(int(re.search(r"yearbook-(\d{4})", row["source"]).group(1)))
    chosen_volume = {
        year: (year if year in found else min(found))
        for year, found in volumes_by_year.items()
    }

    # The series: every row from the year's chosen volume, keyed on the name
    # exactly as that volume prints it. No cross-volume matching is involved,
    # so a rename cannot double-count.
    index_district_names(yb_trends + yb_grades + cde_school)
    trend_index: dict[tuple, dict] = {}
    for row in yb_trends:
        volume = int(re.search(r"yearbook-(\d{4})", row["source"]).group(1))
        if volume != chosen_volume.get(row["year"]):
            continue
        key = (row["year"], row["district_name"], row["county_name"])
        hit = (crosswalk.get(district_key(row["district_name"], row["county_name"]))
               or crosswalk.get(district_key(row["district_name"])))
        record = trend_index.setdefault(key, {
            "year": row["year"], "school_year": row["school_year"],
            "district_code": hit["district_code"] if hit else "",
            "district_name": row["district_name"], "county_name": row["county_name"],
            "source": f"yearbook-{volume}-table4",
        })
        record.setdefault(row["measure"], row["value"])

    # The overlap comparison is separate, and only here does name matching
    # matter: failing to match two readings costs a comparison, not a sum.
    readings: dict[tuple, list[dict]] = defaultdict(list)
    for row in yb_trends:
        if row["measure"] != "fall_membership":
            continue
        volume = int(re.search(r"yearbook-(\d{4})", row["source"]).group(1))
        readings[(row["year"], district_key(row["district_name"], row["county_name"]))].append(
            {**row, "volume": volume})

    overlap_rows = []
    for key, entries in readings.items():
        year, _ = key
        by_measure = {"fall_membership": entries}
        chosen = min(entries, key=lambda e: abs(e["volume"] - year))
        # Two volumes reading the same printed figure is two independent OCR
        # passes over one source. Where they disagree, one of them is wrong,
        # and the size of the disagreement measures the OCR directly - against
        # the book itself rather than against NCES.
        fall = by_measure.get("fall_membership", [])
        if len(fall) > 1:
            values = {e["volume"]: e["value"] for e in fall}
            distinct = set(values.values())
            overlap_rows.append({
                "year": year,
                "district_name": chosen["district_name"],
                "county_name": chosen["county_name"],
                "volumes": ";".join(str(v) for v in sorted(values)),
                "readings": ";".join(f"{v}:{int(values[v])}" for v in sorted(values)),
                "agree": len(distinct) == 1,
                "spread": int(max(distinct) - min(distinct)),
                "chosen_volume": chosen["volume"],
                "chosen_value": int(chosen["value"]),
            })

    district_year = sorted(trend_index.values(), key=lambda r: (r["year"], r["district_name"]))

    # 1986-1999 comes from each volume's own grade table rather than its
    # trends table. The ten-year, four-measure Table 4 only exists in the
    # early volumes; from about 1992 the books print a shorter five-year
    # trend instead, and 1988 and 1999 print none at all. The grade table is
    # in every volume and is the better source anyway - summed and compared
    # against NCES it lands within 0.00% in several years.
    covered = {row["year"] for row in district_year}
    grade_totals: dict[tuple, dict] = {}
    for row in yb_grades:
        if row["year"] in covered or row["grade"] in ("SPECIAL_EDUCATION", "UNGRADED"):
            continue
        key = (row["year"], row["district_name"], row["county_name"])
        entry = grade_totals.setdefault(key, {
            "year": row["year"], "school_year": f"{row['year']}-{str(row['year'] + 1)[2:]}",
            "district_code": row.get("district_code", ""),
            "district_name": row["district_name"], "county_name": row["county_name"],
            "fall_membership": 0, "source": f"{row['source']}-grades",
        })
        entry["fall_membership"] += row["enrollment"]
    district_year.extend(grade_totals.values())

    # Extend the same series through the modern era by summing the school
    # panel, so one column carries fall membership from 1977 to the present.
    modern_totals: dict[tuple, int] = defaultdict(int)
    for row in cde_school:
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED"):
            modern_totals[(row["year"], row["district_code"])] += row["enrollment"]
    for (year, code), value in sorted(modern_totals.items()):
        if not code:
            continue
        district_year.append({
            "year": year, "school_year": f"{year}-{str(year + 1)[2:]}",
            "district_code": code,
            "district_name": modern_names.get((year, code), ""),
            "county_name": "", "fall_membership": value,
            "source": "cde-school-sum",
        })

    for row in district_year:
        row["unit_type"] = unit_type(row.get("district_name", ""))
    write_csv(PROCESSED / "district-year.csv", district_year, [
        "year", "school_year", "district_code", "district_name", "county_name", "unit_type",
        "fall_membership", "closing_day_membership", "average_daily_membership", "adae", "source"])
    if overlap_rows:
        agree = sum(1 for r in overlap_rows if r["agree"])
        print(f"  overlapping district-years: {len(overlap_rows):,}, "
              f"{agree:,} agree exactly ({agree / len(overlap_rows):.1%})")
        write_csv(PROCESSED / "district-year-overlap.csv",
                  sorted(overlap_rows, key=lambda r: (-r["spread"], r["year"])),
                  list(overlap_rows[0].keys()))

    # ---- the yearbook era of the district staffing table ------------------
    #
    # district-teacher-fte-cde.csv is written by pipeline.teacher_fte and
    # covers 2000 onward. The yearbooks carry the same measures for the
    # fourteen years before that, in a table CDE printed as Table 1 in some
    # volumes and Table 2 in others, so they are merged in here - where the
    # district name crosswalk already exists - rather than in a module that
    # knows nothing about yearbooks.
    #
    # One parsed row can land in two different years. The 1999 volume prints
    # Fall 1999 membership beside Fall 1998 teachers, so its school counts
    # belong to 1999 and its staff to 1998; the 1998 volume prints no staff
    # column at all. Each row is therefore split into what it says about its
    # own year and what it says about the staff year, and the two are merged
    # by district.
    index_district_names(yb_trends + yb_grades + yb_summary + cde_school)
    staffing: dict[tuple, dict] = {}

    def staffing_row(year: int, row: dict) -> dict:
        hit = (crosswalk.get(district_key(row["district_name"], row["county_name"]))
               or crosswalk.get(district_key(row["district_name"])))
        code = hit["district_code"] if hit else ""
        key = (year, code or f"name:{district_key(row['district_name'])}")
        return staffing.setdefault(key, {
            "year": year,
            "district_code": code,
            "district_name": row["district_name"],
            "county_name": row["county_name"],
            "unit_type": unit_type(row["district_name"]),
            "source": row["source"],
        })

    for row in yb_summary:
        own = staffing_row(row["year"], row)
        for key in ("schools_elementary", "schools_middle", "schools_senior",
                    "schools_other", "graduation_rate", "dropout_rate"):
            if row.get(key) is not None:
                own[key] = row[key]
        if row.get("schools_total") is not None:
            own["schools_published"] = row["schools_total"]
        if row.get("enrollment") is not None:
            own["enrollment_published"] = row["enrollment"]

        staff = staffing_row(row["staff_year"], row) if row["staff_year"] != row["year"] else own
        if row.get("teacher_fte") is not None:
            staff["teacher_fte_published"] = row["teacher_fte"]
        for key in ("staff_certificated_fte", "staff_noncertificated_fte",
                    "pupil_teacher_ratio"):
            value = row.get({"staff_certificated_fte": "staff_certificated_fte",
                             "staff_noncertificated_fte": "staff_noncertificated_fte",
                             "pupil_teacher_ratio": "pupil_teacher_ratio"}[key])
            if value is not None:
                staff[key] = value

    matched = sum(1 for r in staffing.values() if r["district_code"])
    print(f"\nDistrict staffing, the yearbook era")
    print(f"  {len(staffing):,} district-years 1986-1999; "
          f"{matched:,} matched to a CDE district code ({matched / len(staffing):.1%})")

    existing_path = PROCESSED / "district-teacher-fte-cde.csv"
    existing = []
    if existing_path.exists():
        with existing_path.open(encoding="utf-8") as handle:
            existing = [dict(r) for r in csv.DictReader(handle)]
            for row in existing:
                row["unit_type"] = unit_type(row.get("district_name", ""))
    columns = ["year", "district_code", "district_name", "county_name", "unit_type",
               "teacher_fte_published", "teacher_fte_school_sum", "teacher_fte_difference",
               "staff_certificated_fte", "staff_noncertificated_fte",
               "pupil_teacher_ratio",
               "schools_published", "schools_elementary", "schools_middle",
               "schools_senior", "schools_other", "schools_in_sum",
               "enrollment_published", "enrollment_school_sum",
               "graduation_rate", "dropout_rate", "source"]
    for row in existing:
        row["schools_in_sum"] = row.pop("schools", "")
    combined = sorted(list(staffing.values()) + existing,
                      key=lambda r: (int(r["year"]), str(r["district_code"]),
                                     str(r["district_name"])))
    write_csv(existing_path, combined, columns)
    years = sorted({int(r["year"]) for r in combined})
    print(f"  the table now spans {years[0]}-{years[-1]}")

    # ---- reconciliation --------------------------------------------------
    print("\nReconciling CDE against CCD")
    recon = []
    for year in sorted({r["year"] for r in cde_school}):
        cde_year = {k[1]: v for k, v in cde_totals.items() if k[0] == year}
        ccd_year: dict[str, int] = defaultdict(int)
        ccd_prek = 0
        for row in ccd_enrollment:
            if row["year"] != year or not row["school_code"]:
                continue
            if row["grade"] == "PK":
                ccd_prek += row["enrollment"]
                continue
            ccd_year[row["school_code"]] += row["enrollment"]
        if not ccd_year:
            continue
        cde_prek = sum(r["enrollment"] for r in cde_school
                       if r["year"] == year and r["grade"] == "PK")
        overlap = set(cde_year) & set(ccd_year)
        exact = sum(1 for c in overlap if cde_year[c] == ccd_year[c])
        diffs = sorted(abs(cde_year[c] - ccd_year[c]) for c in overlap)
        recon.append({
            "year": year,
            "cde_schools": len(cde_year),
            "ccd_schools": len(ccd_year),
            "matched": len(overlap),
            "exact_agreement": exact,
            "median_abs_diff": diffs[len(diffs) // 2] if diffs else "",
            "cde_total": sum(cde_year.values()),
            "ccd_total": sum(ccd_year.values()),
            "cde_prek": cde_prek,
            "ccd_prek": ccd_prek,
            "gap_excluding_prek": sum(cde_year.values()) - cde_prek - sum(ccd_year.values()),
        })
        print(f"  {year}: {len(overlap):,}/{len(cde_year):,} matched, "
              f"{exact:,} exact, gap ex-PK {recon[-1]['gap_excluding_prek']:+,}")
    write_csv(PROCESSED / "source-reconciliation.csv", recon, list(recon[0].keys()) if recon else ["year"])

    # ---- district reconciliation, the yearbook tier's real check ----------
    # The row-total checksum can only speak for rows it was given, and it
    # passes on an aggregate row that sums correctly against itself - which is
    # exactly how a "** STATE TOTALS:" row doubled three volumes while every
    # checksum reported clean. Summing each volume's numbered grades and
    # comparing against NCES for the same year is the check that caught it,
    # because NCES is collected independently of the scanned book.
    print("\nReconciling the yearbook tier against NCES")
    district_recon = []
    ccd_by_year: dict[int, int] = defaultdict(int)
    for row in ccd_enrollment:
        if row["grade"] != "UNGRADED":
            ccd_by_year[row["year"]] += row["enrollment"]
    yb_by_year: dict[int, int] = defaultdict(int)
    yb_districts: dict[int, set] = defaultdict(set)
    for row in yb_grades:
        yb_districts[row["year"]].add(row["district_name"])
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED", "PK"):
            yb_by_year[row["year"]] += row["enrollment"]
    for year in sorted(yb_by_year):
        ccd_total = ccd_by_year.get(year)
        if not ccd_total:
            continue
        diff = yb_by_year[year] - ccd_total
        district_recon.append({
            "year": year,
            "districts": len(yb_districts[year]),
            "yearbook_k12": yb_by_year[year],
            "ccd_k12": ccd_total,
            "difference": diff,
            "pct_difference": round(diff / ccd_total, 6),
        })
        print(f"  {year}: yearbook {yb_by_year[year]:,} vs NCES {ccd_total:,}  {diff:+,} ({diff / ccd_total:+.2%})")
    if district_recon:
        write_csv(PROCESSED / "district-reconciliation.csv", district_recon,
                  list(district_recon[0].keys()))

    report["counts"] = {
        "school_enrollment_rows": len(panel),
        "school_year_rows": len(school_year_rows),
        "schools_in_registry": len(registry),
        "district_grade_rows": len(district_grade),
        "district_year_rows": len(district_year),
        "reconciliation_years": len(recon),
        "years_covered_school": sorted({r["year"] for r in panel})[:1] + sorted({r["year"] for r in panel})[-1:],
        "years_covered_district": sorted({r["year"] for r in district_year})[:1] + sorted({r["year"] for r in district_year})[-1:],
    }
    report["parse_meta"] = {
        "cde_school": cde_school_meta, "cde_teacher": cde_teacher_meta,
        "ccd": ccd_meta, "yearbooks": yb_meta,
    }
    (AUDIT / "normalize-report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\nWrote {AUDIT / 'normalize-report.json'}")


if __name__ == "__main__":
    main()
