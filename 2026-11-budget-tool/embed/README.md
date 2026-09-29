# Iframe embed — publishable artifacts

Everything needed to publish the interactive. The two built files are what gets
published, and neither is edited by hand: both are rebuilt from the source in
[`src/`](./src/).

| File | What it is | Use |
|---|---|---|
| `index.html` | The whole interactive in one self-contained file (207 KB). No external requests except the survey POST. | Zip it and upload to the Newspack Iframe Block. GitHub Pages also serves it at [`/boulder-budget-2026/`](https://brianckeegan.github.io/charting-boulder/boulder-budget-2026/) |
| `boulder-budget-embed.js` | The same interactive as a `<boulder-budget>` Web Component, styles scoped in a shadow root (208 KB) | For a page that wants the widget inline rather than in an iframe |
| `src/` | The React source (`boulder-budget-widget.jsx`), the build script, and the pinned build dependencies | Edit the JSX, then rebuild both files (below) |
| `NEWSPACK-EMBED-GUIDE.md` | Step-by-step publishing instructions for Newspack: inline (Method A) or iframe ZIP (Method B) | Read before publishing |
| `pages-redirect.html` | Sends the repository's root GitHub Pages URL, which was shared before the widget moved, on to `/boulder-budget-2026/` | Deployed with `index.html` by `.github/workflows/deploy-widget.yml` whenever either file changes |

## Publishing

The overriding deliverable is a ZIP of the HTML for an iframe embed:

```
cd 2026-11-budget-tool/embed
zip boulder-budget-interactive.zip index.html
```

Upload that to the Newspack Iframe Block. It accepts `application/zip` only, and
the archive must contain an `index.html` at its root — which is why the file is
named `index.html` here rather than after the widget.

For the Web Component instead:

```html
<script src="/path/to/boulder-budget-embed.js" defer></script>
<boulder-budget></boulder-budget>
```

Shadow DOM scopes the styling so the host theme cannot leak in. It is *not* a
security boundary — it isolates CSS, nothing else.

## Rebuilding

Both files are compiled from `src/boulder-budget-widget.jsx` by
`src/build-standalone.sh`, with esbuild inlining React, ReactDOM and the icons.
The source was out of this repository for a while and was restored from commit
`665be7c` for the 2027 revision. Before any change, rebuilding the restored
copy reproduced both published files byte for byte.

```
cd 2026-11-budget-tool/embed/src
BBW_PREVIEW=0 ./build-standalone.sh                    # ../index.html
BBW_PREVIEW=0 BBW_TARGET=embed ./build-standalone.sh   # ../boulder-budget-embed.js
```

It needs Node 18+ and npm, and installs the pinned versions in `build-deps/`
with `npm ci`. Without `BBW_PREVIEW=0` the page is a review copy that keeps
submissions in memory and never touches the database. It writes the same
`../index.html`, so rebuild with `BBW_PREVIEW=0` before committing.

**The widget and the database change together.** The table has one column per
field the widget sends, and
`pipeline/supabase/migrations/2026-08-29-security-hardening.sql` limits
`top_cut` to the General Fund department names in `bbw_gf_departments()`,
which must match `GF_DEPTS` in the JSX. GitHub Pages publishes `index.html` as
soon as it reaches `main`, so a widget change that sends a new field or
renames a department needs its migration run on the live table **before** the
merge. [`RUNBOOK-2027-sliders.md`](../pipeline/supabase/migrations/RUNBOOK-2027-sliders.md)
walks through the most recent one.
