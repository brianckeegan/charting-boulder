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


def district_key(name: str, county: str = "") -> str:
    """A comparable key for a district name.

    The yearbooks print "MAPLETON 1" and "SANGRE DE CRISTO RE-22J"; the modern
    CDE files print "Mapleton 1" and "Sangre De Cristo Re-22j". The trailing
    organisational suffix is the least stable part across forty years, so it
    is stripped and the county is used to disambiguate the remainder.
    """
    text = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper())
    text = re.sub(r"\s+", " ", text).strip()
    text = DISTRICT_SUFFIX.sub("", text).strip()
    text = re.sub(r"\b(SCHOOL DISTRICT|SCHOOLS|DISTRICT|COUNTY)\b", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    county_key = re.sub(r"[^A-Z]", "", str(county).upper())
    return f"{county_key}|{text}" if county_key else text


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


def load_yearbooks() -> tuple[list[dict], list[dict], dict]:
    grade_records, trend_records, meta = [], [], {}
    for volume in sorted(YEARBOOKS.iterdir()):
        if not volume.is_dir() or not volume.name.isdigit():
            continue
        year = int(volume.name)
        grades, ginfo = parse_yearbook_district_grade(volume, year)
        trends, tinfo = parse_yearbook_trends(volume, year)
        grade_records.extend(grades)
        trend_records.extend(trends)
        meta[year] = {"district_by_grade": ginfo, "trends": tinfo}
        if "error" in ginfo:
            print(f"  yearbook {year}: {ginfo['error']}")
        else:
            print(f"  yearbook {year}: {ginfo['districts']} districts, "
                  f"totals {ginfo['row_total_pass']}/{ginfo['row_total_pass'] + ginfo['row_total_fail']}; "
                  f"trends {tinfo.get('districts', 0)} districts")
    return grade_records, trend_records, meta


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
    yb_grades, yb_trends, yb_meta = load_yearbooks()

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
        "county_name": r["county_name"], "grade": r["grade"], "enrollment": r["enrollment"],
        "source": r["source"],
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
            "grade": grade, "enrollment": value, "source": "cde-school-sum",
        })
    write_csv(PROCESSED / "district-enrollment-by-grade.csv", district_grade, [
        "year", "district_code", "district_name", "county_name", "grade", "enrollment", "source"])

    # District-year: the yearbook trends table, which is the only source
    # reaching before 1986.
    trend_index: dict[tuple, dict] = {}
    for row in yb_trends:
        hit = (crosswalk.get(district_key(row["district_name"], row["county_name"]))
               or crosswalk.get(district_key(row["district_name"])))
        key = (row["year"], row["district_name"])
        entry = trend_index.setdefault(key, {
            "year": row["year"], "school_year": row["school_year"],
            "district_code": hit["district_code"] if hit else "",
            "district_name": row["district_name"], "county_name": row["county_name"],
            "source": row["source"],
        })
        entry[row["measure"]] = row["value"]
    district_year = sorted(trend_index.values(), key=lambda r: (r["year"], r["district_name"]))
    write_csv(PROCESSED / "district-year.csv", district_year, [
        "year", "school_year", "district_code", "district_name", "county_name",
        "fall_membership", "closing_day_membership", "average_daily_membership", "adae", "source"])

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
