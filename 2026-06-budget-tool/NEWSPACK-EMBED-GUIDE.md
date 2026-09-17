# Publishing the “Balance Boulder’s Budget” interactive

Two ways to put the interactive in a Newspack article. **Method A (inline)** is
the primary one and gives the best reading experience. **Method B (iframe ZIP)**
is the fallback if Method A is blocked on your site.

Neither method installs a plugin.

> **⚠️ This is never a plugin.**
> If you ever land on a WordPress screen saying *“This plugin is already
> installed”* or offering to **“Replace current with uploaded,”** you are in the
> wrong place — click **Cancel and go back**. Confirming that prompt can delete
> the real Newspack plugin your site runs on.

---

# Method A — Inline (recommended)

The interactive renders as ordinary article content: no iframe, no fixed height,
no scroll-box. It inherits your site’s fonts, and the running score bar follows
the reader down the page, parking just below your site header.

### What this method needs

Two things — worth checking before you start:

1. **SFTP (or file manager) access** to place one JavaScript file. WordPress
   blocks `.js` uploads through the Media Library by default, so this file has to
   be placed directly on the server.
2. **An Administrator account** to paste the snippet. WordPress strips `<script>`
   tags from post content for non-Administrators, so an Editor account will
   silently lose the embed on save.

If either is a problem, use **Method B** instead — it needs neither.

### Step 1 — Place the script

Upload `boulder-budget-embed.js` (~200 KB) to a stable path on the server. A good
choice:

```
/wp-content/uploads/interactives/boulder-budget-embed.js
```

which is served at:

```
https://YOURSITE.org/wp-content/uploads/interactives/boulder-budget-embed.js
```

Open that URL in a browser to confirm it loads before continuing.

### Step 2 — Add the snippet to the article

Place the cursor where the interactive should appear, add a **Custom HTML**
block, and paste:

```html
<script src="https://YOURSITE.org/wp-content/uploads/interactives/boulder-budget-embed.js" defer></script>
<boulder-budget></boulder-budget>
```

Update the domain to match your site. Preview the post — the interactive should
appear inline, running the full width of the article column.

### Step 3 — Check the score bar

As you scroll, the running score bar should pin itself **just below your site
header**, not underneath it.

It measures your header automatically, so usually there is nothing to do. If it
sits too high or too low, set the offset by hand — the number is your header’s
height in pixels:

```html
<boulder-budget sticky-offset="72"></boulder-budget>
```

### Step 4 — Check before publishing

- [ ] The interactive appears inline and fills the article column.
- [ ] Dragging a **department slider** changes the numbers in the score bar.
- [ ] The score bar pins below the header while scrolling, not behind it.
- [ ] Scrolling reaches the survey and the **Submit** button.
- [ ] It looks right **on a phone**.
- [ ] Saving and reloading the post keeps the embed (if it vanishes, the account
      lacks Administrator rights — see “What this method needs”).

### Updating later

Replace `boulder-budget-embed.js` on the server with the new version. Every
article using it updates at once — no post edits needed. Readers may need a hard
refresh, or you can add `?v=2` to the end of the `src` URL to bust caches.

---

# Method B — Newspack Iframe Block (fallback)

Use this if you can’t place a file via SFTP, or don’t have an Administrator
account. It uses Newspack’s own built-in block and needs no special permissions.

### Steps

1. Open the article and place the cursor where the interactive should go.
2. Click **+** (Add block), search for **“Iframe,”** and select the **Iframe** block.
3. Choose the option to **upload an archive / ZIP file**, and upload
   `boulder-budget-interactive.zip` (~64 KB). The block accepts `.zip` only.
4. In the block’s sidebar settings, set:

   | Setting | Value |
   |---|---|
   | **Height** | **800 px** |
   | **Width** | **100 %** |

5. Preview and confirm the interactive loads and the sliders respond.

**Why it scrolls inside a box:** the interactive is about **4,550 px tall** in an
article column (**6,020 px** on a phone), so no frame height shows all of it.
Readers scroll within the frame, and the score bar stays pinned to the top of the
frame. If 800 px feels wrong, try 700 px (less dominant) or 900–1000 px (more
visible at once). The block also has a **full screen** toggle, which lets the
interactive take over the viewport but hides the surrounding article.

### Updating later

Select the existing Iframe block and upload the new ZIP, then update the post.

---

## Troubleshooting

**(A) The embed disappears when I save the post.**
WordPress stripped the `<script>` tag — the account isn’t an Administrator. Ask an
Administrator to paste it, or switch to Method B.

**(A) Nothing appears where the tag is.**
Open the script URL directly in a browser. If it 404s, the file isn’t where the
snippet points. If it downloads instead of displaying, that’s fine — it just
means the path is right.

**(A) The score bar hides behind the site header.**
Set `sticky-offset` by hand (Step 3) to your header’s height in pixels.

**(B) No “Iframe” block appears when I search.**
It’s part of Newspack Blocks and may be disabled — check **Newspack → Settings**
or ask Newspack support to enable it. Use Method A instead.

**(B) The upload is rejected.**
The block accepts `.zip` only. Make sure your Mac didn’t auto-expand the download.
At ~64 KB, a size limit is an unlikely cause.

**(B) The frame is blank or shows a file listing.**
The archive’s entry point is `index.html` at the top level. If your Newspack
version expects something else, tell us what you see — it’s a one-line repackage.

**Fonts look different between the two methods.**
Expected. Method A deliberately inherits your site’s typography so it reads as
native article content; Method B renders in the interactive’s own typeface
(Public Sans) inside its frame.

**Reader submissions don’t seem to save.**
If your site enforces a Content Security Policy, it must allow
`https://*.supabase.co` — see below.

---

## Technical notes (for your web or IT person)

Most sites need none of this.

**Outbound connections**

| Host | Purpose | Method A | Method B |
|---|---|---|---|
| `https://*.supabase.co` | Saving reader submissions | Required | Required |
| `https://fonts.googleapis.com` / `fonts.gstatic.com` | Public Sans typeface | **Not used** | Optional (falls back to system fonts) |

**Content Security Policy**, if you enforce one:

```
script-src  'self';
connect-src 'self' https://*.supabase.co;
frame-src   'self';                                        # Method B only
style-src   'self' 'unsafe-inline' https://fonts.googleapis.com;   # Method B only
font-src    'self' https://fonts.gstatic.com;                      # Method B only
```

**Isolation.** Method A seals the interactive’s CSS in a Shadow DOM, so its
styles and your theme’s styles cannot affect each other. Note that Shadow DOM is
style encapsulation, not a security boundary: inline, the interactive shares the
page’s origin with other scripts on the article. Method B’s iframe is a stronger
boundary, which is one reason to keep it available.

**Privacy and storage.** No cookies, no analytics, no third-party trackers. One
browser `localStorage` flag (`bb_submitted_v4`) marks repeat submissions from the
same browser. Survey responses are anonymous, optional, and stored in the
project’s own database — not shared with any third party.

---

## Questions

Contact **Brian Keegan** — [brianckeegan.com](http://www.brianckeegan.com) — who
built the interactive and can repackage or adjust it as needed.

Source: [github.com/brianckeegan/charting-boulder](https://github.com/brianckeegan/charting-boulder)
