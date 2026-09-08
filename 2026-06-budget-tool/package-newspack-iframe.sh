#!/usr/bin/env bash
# package-newspack-iframe.sh — build the ZIP for Newspack's built-in Iframe Block.
#
# Newspack ships an "Iframe" block that accepts a ZIP archive of a self-contained
# HTML app and serves it from the site's own uploads folder. That is the lightest
# way to publish this interactive: no custom plugin, nothing for the publisher to
# maintain, and the upload lands in the media library (never in wp-content/plugins/,
# so it can't collide with or overwrite an installed plugin).
#
# The archive contains exactly one file — index.html — which is the canonical
# production build renamed to the entry point the block looks for.
#
# Usage:  ./package-newspack-iframe.sh            # package the existing build
#         REBUILD=1 ./package-newspack-iframe.sh  # production-build first, then package
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WIDGET="$HERE/boulder-budget-widget.html"
OUT="$HERE/boulder-budget-interactive.zip"

command -v zip >/dev/null || { echo "zip is required" >&2; exit 1; }

if [ "${REBUILD:-0}" = "1" ]; then
  BBW_PREVIEW=0 bash "$HERE/build-standalone.sh"
fi

[ -f "$WIDGET" ] || {
  echo "Missing $WIDGET — run: BBW_PREVIEW=0 ./build-standalone.sh" >&2; exit 1;
}

# Never ship a preview build: it shows a "local copy" banner and does not write
# reader submissions to the live database.
if grep -q '__BBW_PREVIEW__=!0' "$WIDGET"; then
  echo "That widget is a PREVIEW build. Rebuild with: BBW_PREVIEW=0 ./build-standalone.sh" >&2
  exit 1
fi

# Stage index.html at the archive root — the entry point the Iframe Block expects.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$WIDGET" "$STAGE/index.html"

rm -f "$OUT"
# -X omits extra file attributes so no macOS/Linux metadata rides along.
( cd "$STAGE" && zip -qX "$OUT" index.html )

echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo
echo "Contents:"
unzip -l "$OUT" | sed -n '3,$p' | head -5
echo
echo "Send this file plus NEWSPACK-EMBED-GUIDE.md to the publisher."
echo "They upload it via the Newspack Iframe Block (Add block -> Iframe -> upload ZIP)."
