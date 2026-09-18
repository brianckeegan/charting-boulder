"""Non-public school membership, from CDE's own count of it.

Every enrollment figure elsewhere in this archive is a public-school figure,
which makes "where did the pupils go" a question the archive cannot answer
about its own closures. CDE counts the non-public schools too, by district and
by grade, and publishes it in the same serial as the public count.

The layout is an indented panel: the codes sit at the left margin, the county,
district and school names step rightwards, and each district is followed by a
printed total. That total is the check.
"""
from __future__ import annotations
import re
from pathlib import Path

from .schema import GRADES, normalize_code, parse_count

DISTRICT_TOTAL = re.compile(r"DISTRICT\s+TOTALS?", re.I)
STATE_TOTAL = re.compile(r"STATE\s+TOTALS?|GRAND\s+TOTALS?", re.I)


def parse_nonpublic_sheet(path: Path, year: int, source: str) -> tuple[list[dict], dict]:
    """One year of non-public membership, by school and grade."""
    from .extract import read_sheet
    rows = read_sheet(path)

    header_idx = grade_at = None
    for index, row in enumerate(rows[:40]):
        cells = [str(v).strip().upper() for v in row]
        if "TOTAL" in cells and "PK" in cells:
            header_idx = index
            grade_at = {}
            for position, cell in enumerate(cells):
                label = cell[:-2] if cell.endswith(".0") else cell
                if label in GRADES or label == "TOTAL":
                    grade_at[label] = position
            break
    if header_idx is None or "TOTAL" not in (grade_at or {}):
        return [], {"error": "no header row carrying PK and TOTAL"}
    first_grade = min(grade_at.values())

    records, county, district = [], "", ("", "")
    checks = {"pass": 0, "fail": 0}
    subtotals, aggregate, skipped = [], 0, 0
    for row in rows[header_idx + 1:]:
        cells = [("" if v is None or str(v) == "nan" else str(v).strip()) for v in row]
        if not any(cells):
            continue
        names = [(i, c) for i, c in enumerate(cells[:first_grade]) if c]
        counts = {}
        for grade in GRADES:
            if grade in grade_at and grade_at[grade] < len(cells):
                value = parse_count(cells[grade_at[grade]])
                if value is not None:
                    counts[grade] = counts.get(grade, 0) + value
        printed = (parse_count(cells[grade_at["TOTAL"]])
                   if grade_at["TOTAL"] < len(cells) else None)
        if printed is None and not counts:
            # A heading. Which one it is comes from how far in it sits.
            if not names:
                continue
            column, label = names[-1]
            if STATE_TOTAL.search(label):
                continue
            if column == first_grade - 1:
                district = (district[0], label)
            elif column == first_grade - 2:
                district = (district[0], label)
            else:
                county = label
            continue
        label = names[-1][1] if names else ""
        if DISTRICT_TOTAL.search(label) or STATE_TOTAL.search(label):
            if DISTRICT_TOTAL.search(label):
                subtotals.append((district[1], printed))
            aggregate += 1
            continue
        # A school row carries its codes at the left margin and its name last.
        codes = [c for c in cells[:first_grade] if re.fullmatch(r"[A-Za-z]?\d{3,4}", c)]
        if not label or not codes:
            skipped += 1
            continue
        if printed is None or sum(counts.values()) != printed:
            checks["fail"] += 1
            continue
        checks["pass"] += 1
        base = {"year": year, "county_name": county,
                "district_code": normalize_code(codes[0]), "district_name": district[1],
                "school_code": codes[-1], "school_name": label, "source": source}
        records.extend({**base, "grade": grade, "enrollment": value}
                       for grade, value in counts.items())

    summed: dict[str, int] = {}
    for row in records:
        summed[row["district_name"]] = summed.get(row["district_name"], 0) + row["enrollment"]
    agree = sum(1 for name, total in subtotals
                if total is not None and summed.get(name) == total)
    return records, {
        "schools": len({(r["district_name"], r["school_name"]) for r in records}),
        "records": len(records), "rows_aggregate_excluded": aggregate,
        "rows_skipped": skipped,
        "row_total_pass": checks["pass"], "row_total_fail": checks["fail"],
        "district_total_pass": agree,
        "district_total_fail": len([s for s in subtotals if s[1] is not None]) - agree,
    }


# --------------------------------------------------------------------------
# Fetch and build
# --------------------------------------------------------------------------

import csv
import hashlib
import json
from datetime import datetime, timezone

from .fetch import fetch

HERE = Path(__file__).resolve().parent.parent
LOOKUPS = HERE / "data" / "lookups"
RAW = HERE / "data" / "raw" / "nonpublic"
PROCESSED = HERE / "data" / "processed"

NONPUBLIC_FILE = re.compile(r"non-?public", re.I)
BY_GRADE = re.compile(r"by\s+grade", re.I)


def fetch_all() -> list[dict]:
    """Every non-public membership file the inventory names, by grade."""
    with (LOOKUPS / "inventory.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    wanted = [r for r in rows
              if NONPUBLIC_FILE.search(r["label"]) and BY_GRADE.search(r["label"])
              and r["fmt"] in ("xls", "xlsx")]

    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    landed = []
    for row in wanted:
        name = re.sub(r"[^A-Za-z0-9._-]", "_",
                      f"nonpublic-{row['year']}-{row['filename']}")
        dest = RAW / name
        already = dest.exists() and dest.stat().st_size > 0
        try:
            data = fetch(row["url"], dest)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {name}: {exc}")
            continue
        retrieved = manifest.get(name, {}).get("fetched_at") if already else None
        manifest[name] = {
            "url": row["url"], "label": row["label"], "year": int(row["year"]),
            "format": row["fmt"], "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": retrieved or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        landed.append({**row, "path": dest})
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return landed


def main() -> None:
    print("Fetching every non-public membership file the inventory names by grade")
    landed = fetch_all()
    print(f"  {len(landed)} files on disk\n")

    records, report = [], {}
    for item in sorted(landed, key=lambda r: int(r["year"])):
        year = int(item["year"])
        rows, meta = parse_nonpublic_sheet(item["path"], year, item["path"].name)
        report[item["path"].name] = meta
        if meta.get("error") or not rows:
            print(f"  {year}: {meta.get('error', 'no rows')}")
            continue
        records.extend(rows)
        print(f"  {year}: {meta['schools']:,} schools, "
              f"rows {meta['row_total_pass']}/{meta['row_total_pass'] + meta['row_total_fail']}, "
              f"districts {meta['district_total_pass']}/"
              f"{meta['district_total_pass'] + meta['district_total_fail']}")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    fields = ["year", "county_name", "district_code", "district_name",
              "school_code", "school_name", "grade", "enrollment", "source"]
    with (PROCESSED / "nonpublic-enrollment-by-grade.csv").open("w", newline="",
                                                                encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in sorted(
            records, key=lambda r: (r["year"], r["district_code"], r["school_code"], r["grade"])))
    print(f"\nwrote data/processed/nonpublic-enrollment-by-grade.csv: {len(records):,} rows")

    by_year: dict[int, dict] = {}
    for row in records:
        entry = by_year.setdefault(row["year"], {"enrollment": 0, "schools": set(),
                                                 "districts": set()})
        entry["enrollment"] += row["enrollment"]
        entry["schools"].add((row["district_name"], row["school_name"]))
        entry["districts"].add(row["district_code"])
    with (PROCESSED / "nonpublic-year.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["year", "schools", "districts", "enrollment"])
        for year in sorted(by_year):
            entry = by_year[year]
            writer.writerow([year, len(entry["schools"]), len(entry["districts"]),
                             entry["enrollment"]])
    print(f"wrote data/processed/nonpublic-year.csv: {len(by_year)} years")
    (HERE / "audit" / "nonpublic-parse.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
