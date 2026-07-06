# Boulder Budget Widget — WordPress / Newspack plugin

Embeds the **Balance Boulder's Budget** interactive in any WordPress (Newspack)
article via a `[boulder_budget]` shortcode **and** a native Gutenberg block.

The widget is a self-contained React app (`boulder-budget-widget.html`, ~200 KB,
React/icons all inlined) that writes reader submissions directly to Supabase with
a browser-safe, RLS-protected publishable key. This plugin renders it inside an
**isolated, auto-resizing same-origin iframe** — the professional way to drop a
standalone app into a themed site:

- **Isolation** — the widget ships its own CSS reset (`html,body{…}`) and generic
  utility classes (`.flex`, `.grid`, `.p-4`, …). Inlined into a post they would
  collide with the theme; an iframe keeps the widget's styles in and the theme's
  styles out.
- **Auto-height** — because the iframe is served from *this plugin's folder*
  (same origin as your site), the page can measure the inner document and size the
  iframe to it — no scrollbars, no fixed-height guessing, and **no changes to the
  widget build**. A `ResizeObserver` keeps it correct as readers expand the survey
  or open the sources panel.

## Install

1. Copy this folder into `wp-content/plugins/` (rename it to `boulder-budget-widget`
   if you like), **or** zip it and use **Plugins → Add New → Upload Plugin**.
2. Activate **Boulder Budget Widget** on the Plugins screen.

The current production build is already bundled in `assets/`, so it works
immediately after activation.

## Use it

**Shortcode** (works everywhere — Gutenberg, Classic, widgets):

```
[boulder_budget]
```

**Block** — in the editor, insert **“Boulder Budget Widget”** (Embed category).
It renders a live preview and exposes the same settings in the sidebar.

### Attributes

| Shortcode attr | Block field | Default | Notes |
|---|---|---|---|
| `height` | Height | *(blank)* | Blank = auto-fit to content. Set a value (e.g. `900px`) to force a fixed height with internal scrolling. |
| `max_width` | Max width | `720px` | The interactive is ~680 px wide; `720px` frames it cleanly. Use `none` (or a wide/full block) for the full column. |
| `caption` | Caption | *(none)* | Optional line beneath the widget. |
| `title` | — | *Balance Boulder's Budget — interactive* | Accessible iframe title. |
| `src` | Source URL override | *(bundled build)* | Point at a different copy. **Must be same-origin** for auto-fit; a cross-origin URL falls back to the min height. |

Example:

```
[boulder_budget max_width="none" caption="Source: City of Boulder 2026 budget."]
```

## Update the widget

The interactive itself lives in the main repo (`2026-06-budget-tool/`). To ship a
new version:

```bash
# in 2026-06-budget-tool/
BBW_PREVIEW=0 ./build-standalone.sh                     # must be the production build
cp boulder-budget-widget.html newspack-plugin/assets/   # drop it into the plugin
```

That's it — the plugin cache-busts automatically (it versions the iframe URL by
the file's modification time), so readers get the new build on next load. Always
use the `BBW_PREVIEW=0` (production) build; the preview build adds a "local copy"
banner and does not write to the live database.

## Backend (Supabase)

The Supabase project URL and publishable key are compiled **into the widget
build**, not into this plugin. The publishable key is safe to ship publicly —
Row-Level Security allows inserts only, never reads. To point submissions at
**your own** Supabase project, change the URL/key in the widget source and
rebuild (see `../ARCHITECTURE.md` and `../pipeline/supabase/schema.sql`); no
plugin change is needed.

## Host / security notes

- **Static `.html` from a plugin folder** is served by default on standard
  WordPress hosting. If your host (some managed/VIP setups) blocks direct access
  to `.html` in `wp-content/plugins/`, either move `boulder-budget-widget.html`
  into an allowed static path and set the `src` attribute to it, or upload it to
  the Media Library and point `src` there. (Cross-origin `src` disables auto-fit —
  set a `height` instead.)
- **Content Security Policy:** if your site sets one, allow the iframe and the
  Supabase calls it makes:
  `frame-src 'self';` and `connect-src 'self' https://*.supabase.co;`.
- The iframe is intentionally **not** `sandbox`ed — it runs first-party code and
  needs same-origin access for auto-fit. Don't add `sandbox` without
  `allow-same-origin allow-scripts` or auto-fit and the app will break.

## Files

```
boulder-budget-widget.php   Main plugin: shortcode + block registration + renderer
block.json                  Block metadata & attributes
block.js                    Editor UI (plain JS, no build step)
assets/embed.js             Front-end auto-resize helper
assets/embed.css            Wrapper styling (minimal)
assets/boulder-budget-widget.html   The compiled production build (replace to update)
```

No build tooling, package manager, or npm install is required to run the plugin.
MIT licensed, same as the rest of the project.
