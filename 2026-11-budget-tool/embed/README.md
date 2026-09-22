# Iframe embed — publishable artifacts

Two built files. This is what gets published; nothing in here is edited by hand.

| File | What it is | Use |
|---|---|---|
| `index.html` | The whole interactive in one self-contained file (200 KB). No external requests except the survey POST. | Zip it and upload to the Newspack Iframe Block |
| `boulder-budget-embed.js` | The same interactive as a `<boulder-budget>` Web Component, styles scoped in a shadow root (201 KB) | For a page that wants the widget inline rather than in an iframe |

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

## These are build outputs, and the build is no longer in this repo

Both files were compiled from a React source (`boulder-budget-widget.jsx`) by
`build-standalone.sh`, with esbuild inlining React, ReactDOM and the icons. Those
inputs were removed from this repository deliberately; the last working copy of
all six of them is in git history at commit `665be7c`, under
`2026-06-budget-tool/`:

```
git show 665be7c:2026-06-budget-tool/boulder-budget-widget.jsx > boulder-budget-widget.jsx
git show 665be7c:2026-06-budget-tool/build-standalone.sh       > build-standalone.sh
```

**Practical consequence:** these two files cannot be regenerated from a fresh
clone. Changing the interactive means restoring the build chain from that commit
or from wherever the source is maintained now, rebuilding, and replacing both
files here. Editing the 200 KB minified bundles directly is not a realistic
option.

One live cross-reference survives the removal and is worth knowing about:
`pipeline/supabase/migrations/2026-08-29-security-hardening.sql` constrains the
department names the widget may submit, and its comment says to keep that
allowlist in lockstep with `GF_DEPTS` in the JSX. With the JSX out of the repo,
that check is now a manual one — if the widget's department list changes, the
migration has to change with it or valid submissions start being rejected.
