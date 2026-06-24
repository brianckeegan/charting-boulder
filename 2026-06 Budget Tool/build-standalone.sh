#!/usr/bin/env bash
# build-standalone.sh — produce a FULLY SELF-CONTAINED boulder-budget-widget.html
# with NO external network requests. Unlike build-preview.sh (which loads React,
# Babel, Tailwind and icons from CDNs at view-time and therefore breaks when a CDN
# is unreachable or the viewer is offline), this build inlines everything: React +
# ReactDOM (production), only the lucide icons actually used, the compiled JSX, and
# a small static stylesheet. The result opens from a double-click and renders the
# same way days later, offline, on any machine.
#
# Requirements: Node 18+ and npm, run from a directory that supports symlinks
# (a normal local disk does; some network/cloud mounts do not — if npm errors with
# ENOSYS/symlink, set BUILD_DIR to a local path).
#
# Usage:  ./build-standalone.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
JSX="$HERE/boulder-budget-widget.jsx"
OUT="$HERE/boulder-budget-widget.html"
BUILD_DIR="${BUILD_DIR:-$(mktemp -d)}"

REACT_V=18.2.0
REACTDOM_V=18.2.0
LUCIDE_V=0.383.0
ESBUILD_V=0.21.5

echo "Build dir: $BUILD_DIR"
cd "$BUILD_DIR"
[ -f package.json ] || npm init -y >/dev/null 2>&1
echo "Installing pinned build-time deps…"
npm install --no-audit --no-fund --save-exact \
  "react@$REACT_V" "react-dom@$REACTDOM_V" "lucide-react@$LUCIDE_V" "esbuild@$ESBUILD_V" >/dev/null 2>&1

cp "$JSX" ./widget.jsx

# Preview builds keep submissions in this browser session and never touch the
# live database — safe for a double-click review copy. Build a PRODUCTION HTML
# that writes to the configured backend with:  BBW_PREVIEW=0 ./build-standalone.sh
BBW_PREVIEW="${BBW_PREVIEW:-1}"
PREVIEW_JS=true; [ "$BBW_PREVIEW" = "0" ] && PREVIEW_JS=false
# Optional production wiring: route writes through a Vercel pipeline. Example:
#   BBW_PREVIEW=0 BBW_ENDPOINT=https://your-pipeline.vercel.app/api ./build-standalone.sh
ENDPOINT_JS=""; [ -n "${BBW_ENDPOINT:-}" ] && ENDPOINT_JS="window.__BBW_ENDPOINT__ = \"${BBW_ENDPOINT}\";"

# Entry: bare imports (no CDNs) + config flags + in-memory storage shim + mount.
cat > entry.jsx << EOF
import React from "react";
import { createRoot } from "react-dom/client";
import BoulderBudgetWidget from "./widget.jsx";
(function () {
  if (typeof window !== "undefined") {
    window.__BBW_PREVIEW__ = ${PREVIEW_JS};
    ${ENDPOINT_JS}
    if (!window.storage) {
      var mem = {};
      window.storage = {
        get: function (k) { return Promise.resolve(k in mem ? { key: k, value: mem[k], shared: true } : null); },
        set: function (k, v) { mem[k] = v; return Promise.resolve({ key: k, value: v, shared: true }); },
      };
    }
  }
})();
createRoot(document.getElementById("root")).render(<BoulderBudgetWidget />);
EOF

echo "Bundling (JSX compiled; React/ReactDOM/icons inlined; production; minified)…"
node_modules/.bin/esbuild entry.jsx \
  --bundle --minify --format=iife \
  --jsx=automatic \
  --define:process.env.NODE_ENV='"production"' \
  --loader:.jsx=jsx \
  --target=es2018 \
  --outfile=bundle.js

# Static CSS for the exact Tailwind utility classes the widget uses (the rest of
# the styling is inline styles and the component's own scoped <style> block).
cat > static.css << 'EOF'
*,*::before,*::after{box-sizing:border-box}
.flex{display:flex}.inline-flex{display:inline-flex}.grid{display:grid}
.flex-wrap{flex-wrap:wrap}
.items-center{align-items:center}.items-start{align-items:flex-start}
.justify-between{justify-content:space-between}.justify-center{justify-content:center}
.text-right{text-align:right}
.relative{position:relative}
.overflow-hidden{overflow:hidden}
.w-full{width:100%}
.mx-auto{margin-left:auto;margin-right:auto}
.rounded-md{border-radius:6px}.rounded-lg{border-radius:10px}.rounded-full{border-radius:9999px}
.gap-1{gap:4px}.gap-1\.5{gap:6px}.gap-2{gap:8px}.gap-2\.5{gap:10px}.gap-3{gap:12px}
.mt-1{margin-top:4px}.mt-2{margin-top:8px}.mt-3{margin-top:12px}.mt-4{margin-top:16px}
.mt-5{margin-top:20px}.mt-6{margin-top:24px}.mt-7{margin-top:28px}.mt-8{margin-top:32px}
.pt-3{padding-top:12px}.pt-6{padding-top:24px}.pb-5{padding-bottom:20px}
.p-3{padding:12px}.p-4{padding:16px}
EOF

echo "Assembling self-contained HTML…"
{
  cat << 'HEAD'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Balance Boulder's Budget</title>
  <meta name="description" content="An interactive budget-balancing tool for the City of Boulder, from Boulder Reporting Lab." />
  <style>
    html,body{margin:0;background:#fff;font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;color:#1A1A1A}
    #note{font:600 12px/1.45 system-ui,sans-serif;color:#5A5A5A;text-align:center;padding:9px 14px;background:#FAFAE1;border-bottom:1px solid #E1E1E1}
HEAD
  cat static.css
  cat << 'HEAD2'
  </style>
</head>
<body>
HEAD2
  if [ "$BBW_PREVIEW" != "0" ]; then
    echo '  <div id="note">Local copy, for review. The interaction is fully live; the &ldquo;Add my budget&rdquo; tally works during this session but is not saved to the database. The published embed stores responses in Boulder Reporting Lab&rsquo;s database.</div>'
  fi
  cat << 'HEAD3'
  <div id="root"></div>
  <script>
HEAD3
  cat bundle.js
  cat << 'TAIL'
  </script>
</body>
</html>
TAIL
} > "$OUT"

SIZE=$(wc -c < "$OUT")
echo "Wrote $OUT ($((SIZE/1024)) KB, self-contained — no network needed to view)."
