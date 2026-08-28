# Publishing the “Balance Boulder’s Budget” interactive

A step-by-step guide for embedding the interactive in a Newspack article using
Newspack’s **built-in Iframe Block**. No plugin to install, nothing to maintain.

**Time needed:** about 5 minutes.
**Who can do this:** any editor who can add a block to a post. No developer required.

---

## What you received

| File | What it is |
|---|---|
| `boulder-budget-interactive.zip` | The interactive, ~64 KB. Contains one file, `index.html`. |
| `NEWSPACK-EMBED-GUIDE.md` | This guide. |

The interactive is fully self-contained — all of its code is inside that one
HTML file. Once uploaded it is served from **your own site’s media library**, so
it runs on your domain, not a third party’s.

> **⚠️ This is not a plugin — do not install it under Plugins.**
> If you ever see a WordPress screen saying *“This plugin is already installed”*
> or offering to **“Replace current with uploaded,”** you are in the wrong place.
> Click **Cancel and go back**. Confirming that prompt can delete the real
> Newspack plugin your site runs on. This ZIP goes through the **Iframe Block
> inside the post editor**, described below.

---

## Part 1 — Add the interactive to an article

1. **Open the article** you want to publish it in (or create a new draft).

2. **Place your cursor** where the interactive should appear — usually after the
   first few paragraphs, where a reader has enough context to want to try it.

3. **Add the block.** Click the **+** (Add block) button and search for
   **“Iframe.”** Select the **Iframe** block.
   *If no Iframe block appears, see [Troubleshooting](#troubleshooting).*

4. **Choose the upload option.** The block offers a few ways to provide content
   (a URL, a file upload, or the media library). Choose the option to **upload an
   archive / ZIP file**.

5. **Upload `boulder-budget-interactive.zip`.** The block accepts `.zip` files
   only. It will unpack the archive and load `index.html` automatically.

6. **Confirm the preview.** You should see the interactive appear in the editor,
   starting with the headline **“Balance Boulder’s 2026 budget.”** If you see a
   blank frame, see [Troubleshooting](#troubleshooting).

---

## Part 2 — Set the height

This is the one setting that matters. In the block’s sidebar settings you’ll find
**Height** and **Width**.

**Recommended settings:**

| Setting | Value |
|---|---|
| **Height** | **800 px** |
| **Width** | **100 %** |

**Why the interactive scrolls inside the frame:** it is genuinely long — about
**4,550 px tall** in a typical article column, and **6,020 px on a phone**. No
sensible frame height shows all of it at once, so readers scroll within the
frame. This is expected and works well, because the running **score bar stays
pinned to the top of the frame** as they scroll — readers always see how much of
the gap they’ve closed.

**If 800 px doesn’t feel right,** adjust to taste:

- **700 px** — if the interactive feels too dominant in the article.
- **900–1000 px** — if your audience skews desktop and you want more visible at once.
- **Full-screen toggle** — the block also has a **full screen** option, which lets
  the interactive take over the whole viewport on that post. It’s an option worth
  previewing, but it hides the surrounding article content, so we suggest starting
  with a fixed height.

---

## Part 3 — Check it works before publishing

Preview the post and confirm all five:

- [ ] The interactive loads and shows **“Balance Boulder’s 2026 budget.”**
- [ ] Dragging a **department slider** changes the numbers in the score bar.
- [ ] The **two gap bars** (2026 and 2027) respond as you move sliders.
- [ ] Scrolling **inside** the frame reaches the survey and the **Submit** button
      at the bottom.
- [ ] It looks right **on a phone** — use your browser’s responsive preview or an
      actual phone.

Then publish as normal.

> **Optional but useful:** submit one test response yourself. It confirms the
> whole path works end to end, and one extra row in the data is harmless.

---

## Updating to a new version later

When you receive an updated `boulder-budget-interactive.zip`:

1. Open the article and select the existing **Iframe block**.
2. Upload the new ZIP the same way (or remove the block and add a fresh one).
3. Re-check the height setting, then update the post.

Readers get the new version immediately — there is no cache to clear on your end.

---

## Troubleshooting

**No “Iframe” block appears when I search.**
The Iframe block is part of Newspack Blocks. If it’s missing, it may be disabled
on your site — check **Newspack → Blocks/Settings**, or ask Newspack support to
enable the Iframe block. As a fallback, we can supply a plain embed URL instead
(see “Alternative” below).

**The upload is rejected.**
The block accepts **`.zip` only**. Make sure you’re uploading the `.zip` file
itself, not an unzipped folder — and that your Mac didn’t auto-expand it on
download. If your site caps upload size, note this file is only ~64 KB, so a size
limit is an unlikely cause.

**The frame is blank or shows a file listing.**
The archive’s entry point is `index.html` at the top level of the ZIP. If your
Newspack version expects a different structure, tell us what you see and we’ll
repackage it — it’s a one-line change on our end.

**Fonts look wrong.**
The interactive uses the Public Sans typeface loaded from Google Fonts. If your
site or a reader’s browser blocks Google Fonts, it falls back to system fonts and
still works correctly — only the typography changes.

**Reader submissions don’t seem to save.**
The interactive sends submissions to the project’s database. If your site enforces
a Content Security Policy, it must allow `https://*.supabase.co` — see the
technical notes below.

**Something else.**
Send a screenshot and the article URL to the contact below.

---

## Technical notes (for your web or IT person)

Most sites need none of this — it’s here in case your setup is locked down.

**Outbound connections the page makes**

| Host | Purpose | Required? |
|---|---|---|
| `https://*.supabase.co` | Saving reader submissions | Yes, for the survey to work |
| `https://fonts.googleapis.com` | Font stylesheet | No — degrades to system fonts |
| `https://fonts.gstatic.com` | Font files | No — degrades to system fonts |

**Content Security Policy**, if you enforce one:

```
frame-src   'self';
connect-src 'self' https://*.supabase.co;
style-src   'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src    'self' https://fonts.gstatic.com;
```

**Privacy and storage.** The interactive sets no cookies and runs no analytics or
third-party trackers. It writes a single browser `localStorage` flag
(`bb_submitted_v4`) so repeat submissions from the same browser can be identified
in analysis. Survey responses are anonymous, optional, and stored in the
project’s own database — not shared with any third party.

**Sandboxing.** Don’t add a restrictive `sandbox` attribute to the frame; the
interactive needs scripts to run. Newspack’s block handles this correctly by
default.

---

## Alternative if the Iframe Block isn’t available

The interactive is also live at a public URL and can be embedded with a plain
iframe in a **Custom HTML** block:

```html
<iframe
  src="https://brianckeegan.github.io/charting-boulder/boulder-budget-2026/"
  title="Balance Boulder's Budget — interactive"
  style="width:100%;height:800px;border:0;display:block"
  loading="lazy"></iframe>
```

This works immediately with no upload, but serves the interactive from a
third-party domain rather than yours. Prefer the ZIP method when you can.

---

## Questions

Contact **Brian Keegan** — [brianckeegan.com](http://www.brianckeegan.com) —
who built the interactive and can repackage or adjust it as needed.

Source and documentation: [github.com/brianckeegan/charting-boulder](https://github.com/brianckeegan/charting-boulder)
