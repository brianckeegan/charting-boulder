#!/usr/bin/env python3
"""Build the public, de-identified survey file from a private response export.

Reads either private export (pipeline/export-responses.py's responses.csv, or the
Supabase dashboard's contributions_rows.csv) and writes
../data/budget-survey-public.csv: one row per budget the notebook analyzes, with
every slider, the widget's stored dollar totals and five survey answers.

What it leaves out, and why (data/README.md has the full account):
- times, the row id, the reader's own clock, the widget version and the raw
  payload, which could link a row to a person or a moment;
- the nine survey items the column did not analyze (years in Boulder, area,
  employment, commute, student, race, gender, LGBTQ and disability);
- test submissions and second budgets from the same browser, which the
  notebook sets aside anyway.

Rows keep the database's order by row id, a random (version 4) UUID that says
nothing about when a budget arrived, and are numbered B001, B002, ... in that
order; the ids themselves are dropped. The notebook reads every file in this
order, so the public file reproduces its results exactly.

Usage:
    python3 make-public-data.py <private export.csv> [out.csv]
"""

import csv
import sys
from pathlib import Path

GF_SLIDERS = ["gf_police", "gf_genadmin", "gf_fire", "gf_hhs", "gf_manager", "gf_it",
              "gf_facilities", "gf_finance", "gf_parksrec", "gf_attorney", "gf_other"]
FUND_SLIDERS = ["fund_utilities", "fund_transpo", "fund_openspace", "fund_hhs",
                "fund_parksrec", "fund_facilities", "fund_pds", "fund_manager",
                "fund_climate", "fund_fire", "fund_other"]
REV_COLS = ["rev_fees", "rev_property", "rev_sales", "rev_marijuana", "rev_shift"]
STORED_COLS = ["spend_change", "revenue_only"]
# The five survey items the column analyzed, as readers answered them.
PUBLIC_DEMO_COLS = ["demo_tenure", "demo_age", "demo_education", "demo_income", "demo_building"]

NUMERIC = GF_SLIDERS + FUND_SLIDERS + REV_COLS + STORED_COLS
OUT_COLS = ["budget_id"] + NUMERIC + PUBLIC_DEMO_COLS
TRUE = {"true", "t", "1"}


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "budget-survey-public.csv"

    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    missing = set(NUMERIC + PUBLIC_DEMO_COLS + ["scenario"]) - set(rows[0])
    if missing:
        sys.exit(f"{src} is missing columns: {sorted(missing)}")

    # The budgets the notebook analyzes: written by the 2027 widget (payload v5),
    # not a repeat from the same browser.
    kept = [r for r in rows
            if r["scenario"] == "2027"
            and r.get("client_version", "5") == "5"
            and r.get("repeat_client", "false").strip().lower() not in TRUE]

    # The dashboard export carries the id; pipeline/export-responses.py's export is
    # already in id order. A time-ordered id (UUID version 7) would leak arrival order.
    if "id" in rows[0]:
        if any(len(r["id"]) != 36 or r["id"][14] != "4" for r in kept):
            sys.exit("Row ids are not random (version 4) UUIDs; their order could reveal submission times.")
        kept.sort(key=lambda r: r["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, lineterminator="\n")
        w.writeheader()
        for i, r in enumerate(kept, start=1):
            w.writerow({"budget_id": f"B{i:03d}", **{c: r[c] for c in NUMERIC + PUBLIC_DEMO_COLS}})

    print(f"Read {len(rows):,} rows from {src}; wrote {len(kept):,} budgets x {len(OUT_COLS)} columns to {out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
