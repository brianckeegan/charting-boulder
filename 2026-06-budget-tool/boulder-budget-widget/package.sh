#!/usr/bin/env bash
# package.sh — produce an installable zip of the Boulder Budget Widget plugin.
#
# The bundled widget (assets/boulder-budget-widget.html) is GENERATED, never
# committed: the repo tracks exactly one built widget (../boulder-budget-widget.html)
# so the plugin copy can't drift from what the site deploys. This script refreshes
# the copy from the canonical build and zips the plugin for upload via
# WordPress → Plugins → Add New → Upload Plugin.
#
# Usage:  ./package.sh              # package using the existing canonical build
#         REBUILD=1 ./package.sh    # run the production build first, then package
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WIDGET="$HERE/../boulder-budget-widget.html"
OUT="$HERE/boulder-budget-widget-plugin.zip"

command -v zip >/dev/null || { echo "zip is required" >&2; exit 1; }

# Guard against the one mistake that matters: this plugin must NEVER install as
# wp-content/plugins/newspack-plugin/ — that slug belongs to the real Newspack
# platform plugin (Automattic), and WordPress will offer to overwrite it.
# (This script always stages under boulder-budget-widget/ below regardless of
# $HERE's name, so it's already safe — this just catches a renamed source dir
# early with a clear message instead of silently producing a differently-named
# zip than expected.)
if [ "$(basename "$HERE")" = "newspack-plugin" ]; then
  echo "This source folder is named 'newspack-plugin' — that collides with the" >&2
  echo "real Newspack platform plugin's slug. Rename this directory (e.g. to" >&2
  echo "boulder-budget-widget/) before packaging." >&2
  exit 1
fi

if [ "${REBUILD:-0}" = "1" ]; then
  BBW_PREVIEW=0 bash "$HERE/../build-standalone.sh"
fi
[ -f "$WIDGET" ] || { echo "Missing $WIDGET — run: BBW_PREVIEW=0 ../build-standalone.sh" >&2; exit 1; }

# Refuse to ship a preview build (it shows a review banner and skips the database).
if grep -q '__BBW_PREVIEW__=!0' "$WIDGET"; then
  echo "That widget is a PREVIEW build. Rebuild with: BBW_PREVIEW=0 ../build-standalone.sh" >&2
  exit 1
fi

cp "$WIDGET" "$HERE/assets/boulder-budget-widget.html"

# Stage under the proper plugin folder name so the zip installs as
# wp-content/plugins/boulder-budget-widget/.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/boulder-budget-widget/assets"
cp "$HERE/boulder-budget-widget.php" "$HERE/block.json" "$HERE/block.js" "$HERE/README.md" \
   "$STAGE/boulder-budget-widget/"
cp "$HERE/assets/embed.js" "$HERE/assets/embed.css" "$HERE/assets/boulder-budget-widget.html" \
   "$STAGE/boulder-budget-widget/assets/"

rm -f "$OUT"
( cd "$STAGE" && zip -rq "$OUT" boulder-budget-widget )
echo "Wrote $OUT ($(du -h "$OUT" | cut -f1)) — upload via Plugins → Add New → Upload Plugin."
