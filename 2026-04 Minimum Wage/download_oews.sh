#!/bin/bash
# ============================================================
# download_oews.sh
# Downloads all BLS OEWS metropolitan-area zip files (1997-2025)
# into ./oews_boulder_raw/ for the oews_boulder.py extractor.
#
# Usage:
#   bash download_oews.sh
# ============================================================

set -u

DEST="oews_boulder_raw"
BASE="https://www.bls.gov/oes/special.requests"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
REFERER="https://www.bls.gov/oes/tables.htm"

mkdir -p "$DEST"
echo "Downloading OEWS metro files into ./$DEST/"
echo "------------------------------------------------------------"

ok=0; skip=0; fail=0

for yy in 97 98 99 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25; do
  # BLS names the metro "all data" zip oesmNNma.zip ("ma" = metropolitan area),
  # which is what oews_boulder.py globs (oes*ma.zip).  NOT oesmNNmet.zip.
  file="oesm${yy}ma.zip"
  out="$DEST/$file"
  url="$BASE/$file"

  # Skip if we already have a valid zip
  if [ -f "$out" ] && unzip -tq "$out" >/dev/null 2>&1; then
    echo "  [have]  $file"
    skip=$((skip+1))
    continue
  fi

  # Download with browser-like headers
  curl -sSL -A "$UA" -e "$REFERER" -o "$out" "$url"

  # Verify it's actually a zip, not an HTML error page
  if [ -f "$out" ] && unzip -tq "$out" >/dev/null 2>&1; then
    size=$(du -h "$out" | cut -f1)
    echo "  [ok]    $file  ($size)"
    ok=$((ok+1))
  else
    echo "  [miss]  $file  (no file for this year, or blocked)"
    rm -f "$out"
    fail=$((fail+1))
  fi

  sleep 2   # be polite to the BLS server
done

echo "------------------------------------------------------------"
echo "Done.  downloaded=$ok  already-had=$skip  missing=$fail"
echo "Files are in ./$DEST/"
ls -lh "$DEST" 2>/dev/null | grep -i "oesm" || echo "  (none yet)"
