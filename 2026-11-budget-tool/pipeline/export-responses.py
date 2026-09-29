#!/usr/bin/env python3
"""Export budget contributions from Supabase to responses.csv for the notebook.

This is the "live export" the analysis notebook expects when STUB_MODE = False
(it reads RESPONSES_CSV = 'responses.csv'). Columns and order match the
notebook's GF_SLIDERS / FUND_SLIDERS / REV_COLS / DEMO_COLS exactly, plus `ts`
and `scenario`. `ts` is `created_at`, the insert time a server-side trigger
sets; the widget's own `client_ts` comes from the reader's clock and is not
exported.

Reading individual rows requires the SECRET key (the publishable key is
insert-only under Row Level Security), so run this from a trusted machine — never
ship the secret key to a browser.

Usage:
    export SUPABASE_URL=https://iplcjxbazezpjdzdpjxx.supabase.co
    export SUPABASE_SECRET_KEY=sb_secret_...        # or SUPABASE_SERVICE_ROLE_KEY
    python3 export-responses.py [outfile.csv]

No third-party packages required (urllib + csv from the standard library).
"""

import csv
import json
import os
import sys
import urllib.parse
import urllib.request

# The same lists, in the same order, as the notebook's canonical columns and
# public.contributions in supabase/schema.sql. PostgREST rejects the whole
# request if any name here is not a column of the table, so a list that drifts
# from the schema stops the export rather than exporting the wrong thing.
GF_SLIDERS = ["gf_police", "gf_genadmin", "gf_fire", "gf_hhs", "gf_manager", "gf_it",
              "gf_facilities", "gf_finance", "gf_parksrec", "gf_attorney", "gf_other"]
# The 2027 widget's locked section: each department's spending outside the
# General Fund. (Before 2027 these were seventeen funds; see
# supabase/migrations/RUNBOOK-2027-sliders.md.)
FUND_SLIDERS = ["fund_utilities", "fund_transpo", "fund_openspace", "fund_hhs",
                "fund_parksrec", "fund_facilities", "fund_pds", "fund_manager",
                "fund_climate", "fund_fire", "fund_other"]
# rev_fees/rev_property/rev_sales are % changes (-25..25); rev_marijuana is a
# tax rate (0..10, 3.5 today); rev_shift is $M moved onto dedicated funds (0..5).
REV_COLS = ["rev_fees", "rev_property", "rev_sales", "rev_marijuana", "rev_shift"]
DEMO_COLS = ["demo_years", "demo_area", "demo_employment", "demo_commute", "demo_student",
             "demo_education", "demo_building", "demo_tenure", "demo_income",
             "demo_age", "demo_race", "demo_gender", "demo_lgbtq", "demo_disability"]

OUT_COLS = ["ts", "scenario"] + GF_SLIDERS + FUND_SLIDERS + REV_COLS + DEMO_COLS

# `ts` is created_at, not client_ts: schema.sql forces created_at on the server
# precisely so the response timeline cannot be spoofed through the public insert
# path, while client_ts is whatever the reader's device clock said.
SELECT_COLS = ["created_at", "scenario"] + GF_SLIDERS + FUND_SLIDERS + REV_COLS + DEMO_COLS

PAGE = 1000


def main() -> int:
    base = os.environ.get("SUPABASE_URL", "https://iplcjxbazezpjdzdpjxx.supabase.co").rstrip("/")
    key = (os.environ.get("SUPABASE_SECRET_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY"))
    if not key:
        sys.exit("Set SUPABASE_SECRET_KEY (the sb_secret_… key) before running.")

    out_name = sys.argv[1] if len(sys.argv) > 1 else "responses.csv"
    select = ",".join(SELECT_COLS)
    rows = []
    offset = 0
    while True:
        qs = urllib.parse.urlencode({
            "select": select,
            "order": "created_at.asc",
            "limit": PAGE,
            "offset": offset,
        })
        req = urllib.request.Request(
            f"{base}/rest/v1/contributions?{qs}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            sys.exit(f"Supabase returned {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE

    with open(out_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            r["ts"] = r.get("created_at")
            writer.writerow({c: r.get(c) for c in OUT_COLS})

    print(f"Wrote {out_name}: {len(rows):,} rows x {len(OUT_COLS)} cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
