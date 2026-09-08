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
# Two build targets:
#   BBW_TARGET=html   (default) -> boulder-budget-widget.html, the standalone page
#                                  used by GitHub Pages and the Newspack Iframe ZIP.
#   BBW_TARGET=embed            -> boulder-budget-embed.js, a Web Component
#                                  (<boulder-budget>) that renders INLINE in an
#                                  article with its styles sealed in a Shadow DOM.
#                                  No iframe, so no fixed height to guess.
#
# Usage:  ./build-standalone.sh                    # standalone HTML (preview)
#         BBW_PREVIEW=0 ./build-standalone.sh      # standalone HTML (production)
#         BBW_PREVIEW=0 BBW_TARGET=embed ./build-standalone.sh   # embed bundle
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
JSX="$HERE/boulder-budget-widget.jsx"
OUT="$HERE/boulder-budget-widget.html"
OUT_EMBED="$HERE/boulder-budget-embed.js"
BBW_TARGET="${BBW_TARGET:-html}"
BUILD_DIR="${BUILD_DIR:-$(mktemp -d)}"

case "$BBW_TARGET" in
  html|embed) ;;
  *) echo "BBW_TARGET must be 'html' or 'embed' (got '$BBW_TARGET')" >&2; exit 1 ;;
esac

REACT_V=18.2.0
REACTDOM_V=18.2.0
LUCIDE_V=0.383.0
ESBUILD_V=0.21.5

echo "Build dir: $BUILD_DIR"
cd "$BUILD_DIR"
# Reproducible install. `npm ci` installs exactly the tree recorded in the
# committed lockfile — transitive dependencies included, each with an integrity
# hash — and fails if the manifest and lockfile disagree. This matters more than
# usual here: the result is inlined into a single bundle served to readers, so
# Subresource Integrity cannot protect it after the fact. Without the lockfile,
# transitive deps would silently re-resolve on every build.
if [ -f "$HERE/build-deps/package-lock.json" ]; then
  cp "$HERE/build-deps/package.json" "$HERE/build-deps/package-lock.json" ./
  echo "Installing pinned build-time deps (npm ci, locked tree)…"
  npm ci --no-audit --no-fund >/dev/null 2>&1
else
  echo "WARNING: build-deps/package-lock.json missing — falling back to an" >&2
  echo "unpinned npm install. The build will work but is not reproducible." >&2
  [ -f package.json ] || npm init -y >/dev/null 2>&1
  npm install --no-audit --no-fund --save-exact \
    "react@$REACT_V" "react-dom@$REACTDOM_V" "lucide-react@$LUCIDE_V" "esbuild@$ESBUILD_V" >/dev/null 2>&1
fi

cp "$JSX" ./widget.jsx

# Static CSS for the exact Tailwind utility classes the widget uses (the rest of
# the styling is inline styles and the component's own scoped <style> block).
# Generated before bundling so the embed target can inline it into the Shadow DOM.
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

# Shadow-DOM stylesheet for the embed target: the same utilities, plus a :host
# block that normalises spacing WITHOUT importing a typeface — inline builds
# inherit the host page's font so the interactive reads as native article text.
if [ "$BBW_TARGET" = "embed" ]; then
  {
    cat << 'EOF'
:host{display:block;font-family:inherit;font-size:16px;line-height:1.45;color:#1A1A1A;--bbw-sticky-top:0px}
:host([hidden]){display:none}
EOF
    cat static.css
  } > shadow.css
fi

# Preview builds keep submissions in this browser session and never touch the
# live database — safe for a double-click review copy. Build a PRODUCTION HTML
# that writes to the configured backend with:  BBW_PREVIEW=0 ./build-standalone.sh
BBW_PREVIEW="${BBW_PREVIEW:-1}"
PREVIEW_JS=true; [ "$BBW_PREVIEW" = "0" ] && PREVIEW_JS=false

# Entry: bare imports (no CDNs) + config flags + in-memory storage shim + mount.
if [ "$BBW_TARGET" = "html" ]; then
cat > entry.jsx << EOF
import React from "react";
import { createRoot } from "react-dom/client";
import BoulderBudgetWidget from "./widget.jsx";
(function () {
  if (typeof window !== "undefined") {
    window.__BBW_PREVIEW__ = ${PREVIEW_JS};
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
else
# Embed entry: define <boulder-budget> as a Web Component. Styles live in a
# Shadow DOM so the article's CSS and the widget's CSS cannot reach each other,
# and there is no iframe — the interactive is ordinary article content, so its
# full height just flows down the page.
cat > entry.jsx << EOF
import React from "react";
import { createRoot } from "react-dom/client";
import BoulderBudgetWidget from "./widget.jsx";
import shadowCss from "./shadow.css";

(function () {
  if (typeof window === "undefined" || !window.customElements) return;
  window.__BBW_PREVIEW__ = ${PREVIEW_JS};
  window.__BBW_INHERIT_FONTS__ = true;   // use the host page's typeface
  if (!window.storage) {
    var mem = {};
    window.storage = {
      get: function (k) { return Promise.resolve(k in mem ? { key: k, value: mem[k], shared: true } : null); },
      set: function (k, v) { mem[k] = v; return Promise.resolve({ key: k, value: v, shared: true }); },
    };
  }

  var TAG = "boulder-budget";
  if (customElements.get(TAG)) return;   // never define twice

  // Measure the host site's own sticky/fixed header so our score bar parks just
  // below it instead of underneath it. querySelectorAll does not pierce shadow
  // roots, so the widget's own sticky bar is never counted. Re-measured on
  // resize and after layout settles, and overridable per-embed with the
  // sticky-offset attribute.
  function detectStickyOffset() {
    if (!document.body) return 0;
    var bottom = 0;
    var vw = window.innerWidth || 0;
    var els = document.body.querySelectorAll("*");
    for (var i = 0; i < els.length; i++) {
      var el = els[i], cs;
      try { cs = getComputedStyle(el); } catch (e) { continue; }
      if (cs.position !== "fixed" && cs.position !== "sticky") continue;
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      var r = el.getBoundingClientRect();
      if (r.width < vw * 0.5) continue;             // a full-width bar, not a badge
      if (r.height < 8 || r.height > 200) continue; // plausible header height
      if (r.top > 4 || r.bottom <= 0) continue;     // actually pinned at the top
      if (r.bottom > bottom) bottom = r.bottom;
    }
    return Math.round(bottom);
  }

  class BoulderBudgetElement extends HTMLElement {
    constructor() {
      super();
      var self = this, t = null;
      this._onResize = function () {
        clearTimeout(t);
        t = setTimeout(function () { self._sync(); }, 150);
      };
      this._onFirstScroll = function () {
        window.removeEventListener("scroll", self._onFirstScroll);
        self._sync();                                // catch reveal-on-scroll headers
      };
    }
    connectedCallback() {
      if (!this.shadowRoot) {
        var shadow = this.attachShadow({ mode: "open" });
        var style = document.createElement("style");
        style.textContent = shadowCss;
        var mount = document.createElement("div");
        shadow.appendChild(style);
        shadow.appendChild(mount);
        this._root = createRoot(mount);
        this._root.render(<BoulderBudgetWidget />);
      }
      this._sync();
      var self = this;
      setTimeout(function () { self._sync(); }, 300);   // after layout settles
      setTimeout(function () { self._sync(); }, 1500);  // after webfonts/images
      window.addEventListener("resize", this._onResize);
      window.addEventListener("scroll", this._onFirstScroll, { passive: true });
    }
    disconnectedCallback() {
      window.removeEventListener("resize", this._onResize);
      window.removeEventListener("scroll", this._onFirstScroll);
    }
    _sync() {
      var attr = this.getAttribute("sticky-offset");
      var manual = attr !== null && attr !== "" && !isNaN(parseInt(attr, 10));
      var px = manual ? parseInt(attr, 10) : detectStickyOffset();
      this.style.setProperty("--bbw-sticky-top", Math.max(0, px) + "px");
    }
  }
  customElements.define(TAG, BoulderBudgetElement);
})();
EOF
fi

echo "Bundling (JSX compiled; React/ReactDOM/icons inlined; production; minified)…"
node_modules/.bin/esbuild entry.jsx \
  --bundle --minify --format=iife \
  --jsx=automatic \
  --define:process.env.NODE_ENV='"production"' \
  --loader:.jsx=jsx \
  --loader:.css=text \
  --target=es2018 \
  --outfile=bundle.js

# The embed target emits JavaScript, not a page: stop here.
if [ "$BBW_TARGET" = "embed" ]; then
  {
    cat << 'BANNER'
/*! Balance Boulder's Budget — inline embed (Web Component <boulder-budget>).
 *  Self-contained: React, icons and styles are bundled, with styles sealed in a
 *  Shadow DOM so the article's CSS and the widget's CSS cannot collide. There is
 *  no iframe, so the interactive flows at its natural height.
 *
 *  Usage:  <script src="/path/to/boulder-budget-embed.js" defer></script>
 *          <boulder-budget></boulder-budget>
 *
 *  The running score bar auto-detects a fixed site header and parks just below
 *  it; override with <boulder-budget sticky-offset="72"></boulder-budget>.
 *  Source: https://github.com/brianckeegan/charting-boulder
 */
BANNER
    cat bundle.js
  } > "$OUT_EMBED"
  SIZE=$(wc -c < "$OUT_EMBED")
  echo "Wrote $OUT_EMBED ($((SIZE/1024)) KB) — inline Web Component build."
  exit 0
fi

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
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💰</text></svg>" />
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
