#!/bin/bash
# ============================================================================
# download_qcew.sh
# ----------------------------------------------------------------------------
# Retrieve quarterly QCEW "by area" slices for the Boulder, CO MSA (area C1450)
# from the BLS QCEW Open Data Access *single-file API*, then clean + concatenate
# them into one combined CSV.
#
#   API pattern (one file per area, per quarter):
#     https://data.bls.gov/cew/data/api/<YEAR>/<QTR>/area/C1450.csv
#
# The single-file API serves 2014-present. Earlier years are only available via
# the multi-hundred-MB bulk "by area" zips, which this script deliberately does
# NOT use — set START_YEAR no earlier than 2014.
#
# Requirements: bash, curl, python3 + pandas (for the clean/concatenate step).
# Usage:        bash download_qcew.sh
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/qcew_boulder_raw"
COMBINED="$HERE/qcew_boulder_combined.csv"

AREA="C1450"                 # Boulder, CO MSA (CBSA 14500 -> QCEW area C1450)
BASE="https://data.bls.gov/cew/data/api"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
START_YEAR=2014              # API floor; do not lower (older years need bulk files)
END_YEAR=2025                # bump as new vintages publish

mkdir -p "$DEST"
echo "QCEW Boulder MSA ($AREA) — single-file API, $START_YEAR-$END_YEAR"
echo "Dest: $DEST"
echo "------------------------------------------------------------"

ok=0; skip=0; miss=0
for year in $(seq "$START_YEAR" "$END_YEAR"); do
  for q in 1 2 3 4; do
    out="$DEST/qcew_${AREA}_${year}_q${q}.csv"

    # Idempotent: keep an already-valid slice (header sanity check).
    if [ -f "$out" ] && head -1 "$out" 2>/dev/null | grep -q "area_fips"; then
      skip=$((skip+1)); continue
    fi

    url="$BASE/$year/$q/area/$AREA.csv"
    code=$(curl -sS -A "$UA" --retry 3 --retry-delay 2 \
                -w "%{http_code}" -o "$out" "$url")

    # A valid slice is HTTP 200 whose first line is the QCEW header.
    if [ "$code" = "200" ] && head -1 "$out" 2>/dev/null | grep -q "area_fips"; then
      echo "  [ok]   $year Q$q  ($(($(wc -l <"$out")-1)) rows)"
      ok=$((ok+1))
    else
      # Future/unpublished quarter, or a transient error — don't keep a stub.
      rm -f "$out"
      echo "  [miss] $year Q$q  (HTTP $code)"
      miss=$((miss+1))
    fi
    sleep 0.3   # be polite to the BLS endpoint
  done
done

echo "------------------------------------------------------------"
echo "Downloaded=$ok  already-had=$skip  missing=$miss"
echo ""

# Clean + concatenate with pandas: robust CSV quoting, values kept verbatim
# (preserves leading zeros and BLS disclosure codes), deduped and ordered.
python3 - "$DEST" "$COMBINED" "$AREA" <<'PY'
import sys, glob, os
import pandas as pd

dest, combined, area = sys.argv[1], sys.argv[2], sys.argv[3]
files = sorted(glob.glob(os.path.join(dest, f"qcew_{area}_*_q*.csv")))
if not files:
    sys.exit("No QCEW slices found to concatenate — nothing downloaded?")

df = pd.concat((pd.read_csv(f, dtype=str) for f in files),
               ignore_index=True, sort=False)

# --- clean ---
df = df.drop_duplicates()                          # slices shouldn't overlap; defensive
for c in df.columns:                               # trim stray whitespace
    if pd.api.types.is_string_dtype(df[c]):
        df[c] = df[c].str.strip()

order = ["own_code", "industry_code", "agglvl_code", "size_code"]
df["_y"] = pd.to_numeric(df["year"], errors="coerce")
df["_q"] = pd.to_numeric(df["qtr"], errors="coerce")
df = (df.sort_values(["_y", "_q"] + [c for c in order if c in df.columns])
        .drop(columns=["_y", "_q"]))

df.to_csv(combined, index=False)

yrs = sorted(df["year"].dropna().unique(), key=int)
print(f"Combined: {len(df):,} rows  x  {df.shape[1]} cols  ->  {os.path.basename(combined)}")
print(f"  Years: {yrs[0]}-{yrs[-1]} ({len(yrs)} years)")
for y, g in df.groupby("year"):
    print(f"    {y}: quarters {sorted(g['qtr'].unique(), key=int)}  ({len(g):,} rows)")
PY
