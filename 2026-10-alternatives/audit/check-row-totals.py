"""Check re-OCR'd yearbook tables against their own printed row totals.

Every table in the CDE yearbooks prints a total at the end of each row. Summing
the cells and comparing is the only mechanical proof that a scanned row was read
correctly - an OCR error that changes a digit will almost always break the sum.
This is cleaning rule 10 in TASK.md and finding A14 in proof-run.md.

Run from the folder root, after datalab-ocr.py has produced some volumes:

    python3 audit/check-row-totals.py           # every volume present
    python3 audit/check-row-totals.py 1986 1987 # named volumes

Prints a pass rate per volume and names the failing rows, and writes
audit/row-totals.json. A failure is not necessarily an OCR fault: a row can
legitimately fail where the source itself does not add up, which is worth
knowing either way.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
YEARBOOKS = HERE.parent / "data" / "interim" / "yearbooks"

# Tables whose rows carry a printed total, and how many leading cells to skip
# before the numeric grid starts. The district-by-grade table leads with a
# district name and a district code; the trends table leads with a measure name.
CHECKABLE = {
    "BY SCHOOL DISTRICT AND GRADE": 2,
    "SUMMARY OF SELECTED SCHOOL DISTRICT DATA": 2,
}

SKIP = re.compile(r"COUNTY:|PREK|^\s*\|?\s*-{3,}|TOTAL\s*\|", re.I)


def check_page(path: Path, skip_cells: int) -> tuple[int, int, list]:
    passed = failed = 0
    failures = []
    for line in path.read_text().splitlines():
        if "|" not in line or SKIP.search(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < skip_cells + 16 or not cells[0]:
            continue
        nums = [c.replace(",", "") for c in cells[skip_cells:] if re.fullmatch(r"[\d,]+", c or "")]
        if len(nums) < 16:
            continue
        values = [int(n) for n in nums]
        if sum(values[:-1]) == values[-1]:
            passed += 1
        else:
            failed += 1
            failures.append({
                "page": path.name,
                "row": cells[0],
                "summed": sum(values[:-1]),
                "printed": values[-1],
            })
    return passed, failed, failures


def check_volume(year: int) -> dict:
    out_dir = YEARBOOKS / str(year)
    index_path = out_dir / "index.json"
    if not index_path.exists():
        return {"year": year, "status": "incomplete - no index.json"}
    index = json.loads(index_path.read_text())

    passed = failed = 0
    failures: list = []
    for page, record in index["pages"].items():
        heading = (record.get("heading") or "").upper()
        skip_cells = next((n for k, n in CHECKABLE.items() if k in heading), None)
        if skip_cells is None:
            continue
        page_path = out_dir / f"p{int(page):03d}.md"
        if not page_path.exists():
            continue
        p, f, rows = check_page(page_path, skip_cells)
        passed += p
        failed += f
        failures.extend(rows)

    return {
        "year": year,
        "status": "checked",
        "rows_checked": passed + failed,
        "passed": passed,
        "failed": failed,
        "pass_rate": (round(passed / (passed + failed), 4) if passed + failed else None),
        "failures": failures[:50],
    }


def main() -> None:
    years = [int(a) for a in sys.argv[1:]] or sorted(
        int(p.name) for p in YEARBOOKS.iterdir() if p.is_dir() and p.name.isdigit()
    )
    report = {}
    for year in years:
        result = check_volume(year)
        report[str(year)] = result
        if result["status"] != "checked":
            print(f"{year}: {result['status']}")
            continue
        rate = result["pass_rate"]
        print(f"{year}: {result['passed']}/{result['rows_checked']} rows sum to their printed total"
              f" ({rate:.1%})" if rate is not None else f"{year}: no checkable rows")
        for failure in result["failures"][:5]:
            print(f"    {failure['page']} {failure['row']}: "
                  f"summed {failure['summed']}, printed {failure['printed']}")

    (HERE / "row-totals.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote {HERE / 'row-totals.json'}")


if __name__ == "__main__":
    main()
