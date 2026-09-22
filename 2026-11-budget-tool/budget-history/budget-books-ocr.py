"""
Boulder budget books -- OCR the pages pypdf cannot read, through Datalab
=======================================================================
Second of the four stages, and the only one that costs money. README.md has the
whole pipeline:

    budget-books-inventory.py   what is in the corpus, which books are scans,
                                and the text of every matched page
    budget-books-ocr.py         <- this: turn scans and mangled pages into text
    budget-books-extract.py     pull candidate figures out of either kind of text
    budget-history.py           the dataset, typed in from checked figures

Run it on your local copy of the books, with a Datalab key in the environment:

    export DATALAB_API_KEY=...
    python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --estimate       # the bill; nothing sent
    python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --yes            # spend it
    python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --tier 2 --yes   # one tier only

Tiers 3 and 4 take their page lists from budget-books-extracted.csv and
budget-books-pages-of-interest.csv, looked for beside this script and then in
the working directory, so copy those two along if you copy the script.

The output is JSONL in exactly the shape `budget-books-inventory.py --dump-text`
writes, so `budget-books-extract.py` reads OCR'd and born-digital pages through
the same code path:

    python3 budget-books-extract.py dump.jsonl budget-books-ocr.jsonl -o budget-books-extracted.csv

Four tiers, four reasons to spend
---------------------------------
`--tier 1,2,3,4` (the default) prices each separately, because a page bought for
one reason is worth very different amounts. A page two tiers both want is sent,
and paid for, once; `--estimate` prints each tier's share of the pages and how
many are not cached yet.

  1  ACQUISITION, scanned -- whole volumes with no text layer at all: the 2007,
     2009 and 2010 Volume 1s, 1,137 pages, $8.53. The only way to reach the last
     two missing citywide totals, 2007 and 2009, plus confirmation of 2010's
     derived one.

  2  ACQUISITION, born-digital -- 24 pages, $0.18, and the best value here.
     These pages HAVE text; it is mangled past what any regex reaches. The 2012
     pie extracts as "Pol ice 29, 593 Comm Planning Parks and Rec 12% and SUSt
     24, 229 S/, 644 10%", where the 32% belongs to Public Works. Datalab rebuilds
     layout instead of streaming text by position, so it reads what pypdf
     cannot. This tier recovered five departmental pie years (2011, 2012, 2013,
     2018 and 2019), 2012's summary-block halves and 2013's whole block.

  3  VALIDATION -- every page a published figure came from, plus two either side
     for a table continuing overleaf. Read from budget-books-extracted.csv rather
     than hard-coded, so it tracks the dataset.

  4  VALIDATION -- every page holding a pie, a multi-year table or a summary
     block, whether or not the extractor could read it. Read from
     budget-books-pages-of-interest.csv. A second, independent reading of the
     same printed figures, and the tier that found 2011's summary block and
     2017's staffing level on pages the born-digital dump never held.

Nothing is sent without --yes, and at the free tier's pacing (see --pace) a
thousand pages take about two hours.

What is deliberately left out
-----------------------------
Six volumes are scans, 1,651 pages, but only three are in tier 1. The other
three are the 2005, 2007 and 2009 VOLUME 2s -- 514 pages, $3.85 -- and in the
books we can read, Volume 2 is the Capital Improvement Program and carries
essentially no citywide summaries: the 2006-2007 Volume 2 matched one summary
keyword in 149 pages, the 2008 Volume 2 matched none in 207. 2005 Volume 2 is
redundant outright, since that year's Volume 1 is born-digital and already
yielded the year in full. Add any of them with --book if the capital detail is
ever wanted.

Tier 1 matches filenames from the START, not anywhere in them. "2007 Annual
Budget, Volume 1" is a substring of "2006-2007 Annual Budget, Volume 1.pdf", and
an unanchored match pulled that born-digital biennial book into a tier meant for
scans. The scan test caught it, but only because that test exists.

Resumable and cached
--------------------
Each page's markdown is written to `<out stem>-cache/<book>/p<NNN>.md` — so
`budget-books-ocr.jsonl` caches into `budget-books-ocr-cache/` — and a page
whose file already exists is never re-sent. An interrupted run continues where
it stopped, re-running is free, and the JSONL can be rebuilt from cache alone
with `--rebuild`.

One thing to watch
------------------
Datalab's markdown is *cleaner* than pypdf's output, and cleaner input is not
automatically parsed input. Markdown renders a table as pipe-delimited rows with
every cell wrapped in HTML and every dollar sign escaped, and a pie as a table
rather than as a run of labels and numbers. `budget-books-extract.py` reads those
shapes now, but a heading or row type it has only seen from pypdf will quietly
return nothing from OCR text, which looks exactly like a year with no data.
`--verify` runs the extractor over the new JSONL and prints which measures came
out, so a run that produced text but no figures is visible immediately.
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf is required:  pip install pypdf")

CONVERT = "https://www.datalab.to/api/v1/convert"
USER_AGENT = "charting-boulder/budget-books-ocr (+https://github.com/brianckeegan/charting-boulder)"

# Volume 1 of the three years the born-digital books cannot cover. Matched as
# substrings of the filename, so the exact Laserfiche naming does not matter.
DEFAULT_BOOKS = ["2007 Annual Budget, Volume 1",
                 "2009 Annual Budget, Volume 1",
                 "2010 Annual Budget, Volume 1"]

# --------------------------------------------------------------------------
# Tiers
# --------------------------------------------------------------------------
# Four different reasons to spend money, in descending order of how much each
# page buys. `--tier 1,2,3,4` runs all four; each is priced separately so the
# bill can be seen before any of it is committed.
#
#   1  ACQUISITION, scanned. Whole volumes with no text layer at all. The only
#      way to reach the last two missing citywide totals, 2007 and 2009.
#   2  ACQUISITION, born-digital. Pages that DO have text, mangled past what any
#      regex reaches -- interleaved pie labels, dropped commas, values that live
#      in an image. Datalab rebuilds layout instead of streaming text by
#      position, so it can read what pypdf cannot. Twenty-odd pages, and the
#      best value in the corpus.
#   3  VALIDATION. Every page a published figure came from, plus a margin for a
#      table continuing overleaf. Computed from budget-books-extracted.csv, not
#      typed, so it tracks the dataset rather than drifting from it.
#   4  VALIDATION. Every page holding a pie, a multi-year table or a summary
#      block, read or not. Computed from budget-books-pages-of-interest.csv,
#      which the extractor writes.
#
# Volume 2 of the scanned years is deliberately NOT in tier 1. In the books we
# can read it is the Capital Improvement Program and carries essentially no
# citywide summaries: the 2006-2007 Volume 2 matched one summary keyword in 149
# pages and the 2008 Volume 2 matched none in 207. Add it with --book if the
# capital detail is ever wanted.
TIER1_BOOKS = DEFAULT_BOOKS          # all pages of each

# Page numbers, as printed by budget-books-extract.py when it skips something.
TIER2_PAGES = {
    "2011 Annual Budget": [67],                       # pie interleaved beyond repair
    "2012 Annual Budget, Volume 1": [39, 93, 112],    # pie, and the one hand-typed block
    "2013 Annual Budget, Volume 1": [97, 115],        # block illegible; no operating/capital
    "2018 Annual Budget - Volume 1": [66],            # pie double-counts its own subtotals
    "2019 Approved Operating Budget": [57],           # pie values are an image
}
TIER2_MARGIN = 1
TIER3_MARGIN = 2
EXTRACTED_CSV = "budget-books-extracted.csv"
# Written by budget-books-extract.py: every page holding a pie, a multi-year table
# or a summary block, whether or not it could be read. Tier 4's target list.
INTEREST_CSV = "budget-books-pages-of-interest.csv"
# Manual mode's default page range (--book without --pages): the citywide
# summary pages sit between 58 and 102 in every book pypdf can read.
DEFAULT_WINDOW = (50, 115)
CENTS_PER_PAGE = 0.75

# The free tier allows 10 requests a minute and 5 at once; one page per request
# means a lot of requests, so pace them. Sequential and slow is fine here: the
# whole job is a few hundred pages and it only ever runs once per book.
PACE_SECONDS = 6.5


def api_key() -> str:
    key = os.environ.get("DATALAB_API_KEY", "").strip()
    if not key:
        sys.exit("DATALAB_API_KEY is not set. export it and run again.")
    return key


def tier3_pages(here: Path):
    """{filename: [pages]} for every page a published figure came from.

    Read from the extractor's own output rather than hard-coded, so this tracks
    the dataset. If the CSV is missing, tier 3 is skipped with a warning instead
    of silently validating nothing.
    """
    import csv as _csv
    # Beside the script, then the working directory: this file gets copied into
    # the corpus directory and run from there, where its siblings are absent.
    path = next((c for c in (here / EXTRACTED_CSV, Path.cwd() / EXTRACTED_CSV)
                 if c.exists()), None)
    if path is None:
        print(f"  ! {EXTRACTED_CSV} not found in {here} or {Path.cwd()};"
              f" skipping tier 3. Copy it from the repo beside this script.")
        return {}
    out = {}
    with path.open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if "excerpt" in row["file"].lower():
                continue
            out.setdefault(row["file"], set()).add(int(row["page"]))
    return {k: sorted(v) for k, v in out.items()}


def looks_scanned(pdf: Path) -> bool:
    """No extractable text worth the name. Same test as budget-books-inventory.py:
    a genuinely scanned page yields zero characters, while even a sparse
    born-digital table page yields a few dozen."""
    reader = PdfReader(str(pdf))
    n = len(reader.pages)
    idx = sorted(set(range(0, n, max(1, n // 12)))) or [0]
    with_text = 0
    for i in idx:
        try:
            if len((reader.pages[i].extract_text() or "").strip()) >= 25:
                with_text += 1
        except Exception:  # noqa: BLE001
            pass
    return (with_text / len(idx)) < 0.4


def infer_year(name: str):
    years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", name)]
    years = [y for y in years if 1970 <= y <= 2035]
    return max(years) if years else ""


def one_page_pdf(reader: PdfReader, page: int) -> bytes:
    """Page `page` (1-indexed) as a standalone PDF.

    Sending a slice of the PDF rather than an extracted image is deliberate.
    These scans are not all JPEG — pulling the page image out means knowing
    which of DCTDecode, CCITTFaxDecode, JBIG2Decode or FlateDecode this
    particular scanner used, and getting it wrong on one book is a silent
    failure. pypdf already knows how to copy a page, and Datalab takes a PDF.
    """
    w = PdfWriter()
    w.add_page(reader.pages[page - 1])
    # add_page copies the page tree, not the document catalogue, so the source's
    # /Info is dropped and each upload would otherwise arrive anonymous. Carry it
    # over and add which page this was, so the file identifies itself on the
    # far side instead of relying on the filename alone. Page-level metadata --
    # /MediaBox and /Rotate -- is copied by add_page already, which matters:
    # several of these scans have rotated pages, and a rotated page sent as a
    # bare image comes back sideways.
    src = dict(reader.metadata or {})
    w.add_metadata({k: str(v) for k, v in src.items() if k != "/Producer"}
                   | {"/Subject": f"page {page} of {len(reader.pages)}"})
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Datalab
# --------------------------------------------------------------------------

def post_pdf(blob: bytes, name: str, key: str) -> str:
    boundary = "----charting-boulder-" + os.urandom(8).hex()
    parts = []
    # output_format=markdown is load-bearing, not a preference. It is what makes
    # Datalab render a pie chart's data as a markdown table:
    #
    #     | Police | \$29,105 | 13% |
    #
    # and that shape is why tier 2 recovered 2011, 2012 and 2013 -- three years
    # whose pies pypdf returns as interleaved nonsense. budget-books-extract.py
    # parses these as tables, keying on the cell containing a "%", so column order
    # does not matter. Changing this to json or html breaks that reader.
    for field, value in (("output_format", "markdown"), ("mode", "accurate")):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n".encode()
    )
    parts.append(blob)
    parts.append(f"\r\n--{boundary}--\r\n".encode())

    # Datalab sits behind Cloudflare, which rejects the default
    # "Python-urllib/3.x" agent with error 1010. Any ordinary agent passes.
    req = urllib.request.Request(
        CONVERT, data=b"".join(parts),
        headers={"X-API-Key": key,
                 "Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": USER_AGENT},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                answer = json.loads(resp.read())
            if not answer.get("success"):
                raise RuntimeError(answer.get("error"))
            return answer["request_check_url"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                time.sleep(60)
                continue
            raise
        except Exception:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def poll(check_url: str, key: str, timeout: int = 600) -> dict:
    req = urllib.request.Request(check_url, headers={"X-API-Key": key, "User-Agent": USER_AGENT})
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                answer = json.loads(resp.read())
            if answer.get("status") == "complete":
                return answer
        except Exception:  # noqa: BLE001
            pass
        time.sleep(4)
    raise TimeoutError(check_url)


# --------------------------------------------------------------------------

def select(root: Path, wanted: list[str]) -> list[Path]:
    pdfs = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    hits = [p for p in pdfs if any(w.lower() in p.name.lower() for w in wanted)]
    missing = [w for w in wanted
               if not any(w.lower() in p.name.lower() for p in pdfs)]
    for w in missing:
        print(f"  ! no file matching {w!r}")
    return hits


def page_list(n_pages: int, window, every: int, explicit) -> list[int]:
    if explicit:
        return [p for p in explicit if 1 <= p <= n_pages]
    lo, hi = window
    pages = list(range(max(1, lo), min(n_pages, hi) + 1))
    return pages[::every] if every > 1 else pages


def main():
    ap = argparse.ArgumentParser(description="OCR the budget-book pages pypdf cannot read, through Datalab.")
    ap.add_argument("root", help="directory holding the PDFs (searched recursively)")
    ap.add_argument("-o", "--out", default="budget-books-ocr.jsonl",
                    help="JSONL to write (default %(default)s)")
    ap.add_argument("--cache", default="", help="markdown cache dir (default: <out>-cache)")
    ap.add_argument("--tier", default="1,2,3,4", metavar="1,2,3,4",
                    help="which tiers to run (default %(default)s). 1 = whole scanned "
                         "volumes, 2 = born-digital pages pypdf mangles, 3 = validate "
                         "every page a published figure came from, 4 = every page "
                         "holding a pie, table or summary block, read or not. "
                         "--book or --pages switches to manual selection instead.")
    ap.add_argument("--book", action="append", default=[], metavar="SUBSTRING",
                    help="filename substring to include; repeatable. Defaults to the "
                         "three Volume 1 scans the born-digital books cannot cover.")
    ap.add_argument("--window", default="{}-{}".format(*DEFAULT_WINDOW), metavar="LO-HI",
                    help="with --book: page range to send (default %(default)s)")
    ap.add_argument("--pages", default="", metavar="N,N,...",
                    help="exact pages to send, overriding --window")
    ap.add_argument("--pace", type=float, default=PACE_SECONDS, metavar="SECONDS",
                    help="seconds between requests (default %(default)s, sized for the "
                         "free tier's 10/minute). Lower it on a paid plan to shorten a "
                         "long run; a 429 is retried after a minute either way.")
    ap.add_argument("--every", type=int, default=1, metavar="N",
                    help="thin the window to every Nth page — the cheap way to "
                         "find which pages carry the summaries")
    ap.add_argument("--estimate", action="store_true",
                    help="print the page count and cost, send nothing")
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the JSONL from cached markdown, send nothing")
    ap.add_argument("--yes", action="store_true", help="required before anything is sent")
    ap.add_argument("--verify", action="store_true",
                    help="after writing, run budget-books-extract.py over the result")
    args = ap.parse_args()

    # Line-buffer stdout. Redirected to a file -- `nohup ... > run.log &`, which is
    # how a multi-hour run gets started -- Python block-buffers output in ~8KB, so
    # the log stays EMPTY until roughly 130 pages have finished, about 14 minutes
    # in, while the requests are visibly going through on the Datalab dashboard.
    # It looks like a hung process. This was invisible in testing because the
    # environment used there set PYTHONUNBUFFERED=1; a default Python reproduces it
    # exactly (0 of 3 progress lines visible mid-run, 3 of 3 with this line).
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:        # Python < 3.7
        pass

    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"no such directory: {root}")
    lo, _, hi = args.window.partition("-")
    window = (int(lo), int(hi))
    explicit = [int(x) for x in re.findall(r"\d+", args.pages)]
    out_path = Path(args.out)
    cache = Path(args.cache) if args.cache else out_path.with_name(out_path.stem + "-cache")

    here = Path(__file__).resolve().parent
    tiers = [int(t) for t in re.findall(r'\d', args.tier)] if args.tier else []
    pdfs = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    # budget-books-inventory.py --extract writes "<year>-excerpt.pdf" beside the
    # originals, holding pages that are already in them. Those are duplicates, and
    # OCR is charged per page, so paying for one is pure waste. The extractor
    # drops them from its dumps for the same reason.
    pdfs = [q for q in pdfs if "excerpt" not in q.name.lower()]
    if not pdfs:
        sys.exit(f"no PDFs under {root} — unzip the archive first?")

    # {resolved pdf: {page: tier}} -- a page wanted by two tiers is paid for once,
    # and attributed to the cheaper-to-justify tier for the printout.
    want = {}

    def claim(pdf, pages, tier):
        d = want.setdefault(pdf, {})
        for pg in pages:
            d.setdefault(pg, tier)

    def match(substr, anchored=False):
        """Filename substring match.

        `anchored` requires the name to START with the pattern, which tier 1
        needs: "2007 Annual Budget, Volume 1" is a substring of "2006-2007
        Annual Budget, Volume 1.pdf", so an unanchored match pulled the
        born-digital biennial book into a tier meant for scans. The scan test
        caught it -- but only because that test exists, and had the biennial
        book been a scan it would have quietly added 321 pages to the bill.
        """
        lo = substr.lower()
        return [q for q in pdfs
                if (q.name.lower().startswith(lo) if anchored else lo in q.name.lower())]

    if args.book or args.pages or not tiers:
        # Manual mode, unchanged: explicit books and an explicit window.
        for pdf in select(root, args.book or DEFAULT_BOOKS):
            claim(pdf, page_list(len(PdfReader(str(pdf)).pages), window,
                                 args.every, explicit), 0)
    else:
        if 1 in tiers:
            for substr in TIER1_BOOKS:
                for pdf in match(substr, anchored=True):
                    n = len(PdfReader(str(pdf)).pages)
                    if not looks_scanned(pdf):
                        print(f"  ! {pdf.name} has a text layer; tier 1 is for scans. Skipping.")
                        continue
                    claim(pdf, range(1, n + 1), 1)
                if not match(substr, anchored=True):
                    print(f"  ! no file starting with {substr!r}")
        if 2 in tiers:
            for substr, pages in TIER2_PAGES.items():
                for pdf in match(substr):
                    n = len(PdfReader(str(pdf)).pages)
                    claim(pdf, [q for pg in pages
                                for q in range(max(1, pg - TIER2_MARGIN),
                                               min(n, pg + TIER2_MARGIN) + 1)], 2)
        if 4 in tiers:
            import csv as _csv
            ipath = next((c for c in (here / INTEREST_CSV, Path.cwd() / INTEREST_CSV)
                          if c.exists()), None)
            if ipath is None:
                print(f"  ! {INTEREST_CSV} not found in {here} or {Path.cwd()};"
                      f" skipping tier 4. It is written by budget-books-extract.py.")
            else:
                per = {}
                with ipath.open(encoding="utf-8") as fh:
                    for row in _csv.DictReader(fh):
                        if "excerpt" in row["file"].lower():
                            continue
                        per.setdefault(row["file"], []).append(int(row["page"]))
                for fname, pages in per.items():
                    for pdf in match(fname):
                        n = len(PdfReader(str(pdf)).pages)
                        claim(pdf, [q for q in pages if 1 <= q <= n], 4)
        if 3 in tiers:
            for fname, pages in tier3_pages(here).items():
                for pdf in match(fname):
                    n = len(PdfReader(str(pdf)).pages)
                    claim(pdf, [q for pg in pages
                                for q in range(max(1, pg - TIER3_MARGIN),
                                               min(n, pg + TIER3_MARGIN) + 1)], 3)

    if not want:
        sys.exit("nothing selected — check --tier / --book against the real filenames")

    plan, by_tier = [], collections.Counter()
    for pdf in sorted(want):
        pages = sorted(want[pdf])
        plan.append((pdf, PdfReader(str(pdf)), pages))
        for pg in pages:
            by_tier[want[pdf][pg]] += 1
        cached = sum(1 for pg in pages if (cache / pdf.stem / f"p{pg:03d}.md").exists())
        tset = "".join(str(t) for t in sorted({want[pdf][pg] for pg in pages}))
        print(f"  [t{tset}] {pdf.name[:46]:<46} {len(pages):>4} of "
              f"{len(PdfReader(str(pdf)).pages):>4}p, {cached:>4} cached")
    print()
    for t in sorted(by_tier):
        label = {1: "acquisition, scanned", 2: "acquisition, born-digital",
                 3: "validation, published figures", 4: "validation, all pies & tables",
                 0: "manual selection"}[t]
        print(f"  tier {t}  {label:<26} {by_tier[t]:>5}p = "
              f"${by_tier[t] * CENTS_PER_PAGE / 100:>6,.2f}")

    todo = sum(1 for pdf, _, pages in plan
               for p in pages if not (cache / pdf.stem / f"p{p:03d}.md").exists())
    print(f"\n  {todo} pages to send x {CENTS_PER_PAGE}c = "
          f"${todo * CENTS_PER_PAGE / 100:.2f}"
          f"   (~{todo * args.pace / 60:.0f} min at {args.pace}s/page)")

    if args.estimate:
        print("\n  --estimate: nothing sent. Add --yes to spend it.")
        return
    if todo and not (args.yes or args.rebuild):
        sys.exit("\n  refusing to spend money without --yes")

    if not args.rebuild and todo:
        key = api_key()
        sent = 0
        for pdf, reader, pages in plan:
            (cache / pdf.stem).mkdir(parents=True, exist_ok=True)
            for p in pages:
                dest = cache / pdf.stem / f"p{p:03d}.md"
                if dest.exists():
                    continue
                try:
                    url = post_pdf(one_page_pdf(reader, p), f"{pdf.stem}-p{p}.pdf", key)
                    answer = poll(url, key)
                except Exception as exc:  # noqa: BLE001
                    # One bad page must not lose the pages already paid for.
                    print(f"    {pdf.stem} p{p}: FAILED {type(exc).__name__}: {exc}")
                    continue
                dest.write_text(answer.get("markdown") or "", encoding="utf-8")
                sent += 1
                cents = (answer.get("cost_breakdown") or {}).get("final_cost_cents")
                print(f"    {pdf.stem[:34]:<34} p{p:>3}  {len(dest.read_text(encoding='utf-8')):>5} chars"
                      f"  {cents if cents is not None else '?'}c")
                time.sleep(args.pace)
        print(f"\n  sent {sent} pages")

    # --- JSONL, in the same shape as --dump-text -------------------------
    n = blank = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for pdf, _reader, pages in plan:
            for p in pages:
                src = cache / pdf.stem / f"p{p:03d}.md"
                if not src.exists():
                    continue
                text = src.read_text(encoding="utf-8")
                if not text.strip():
                    # Paid for and empty. Either a genuinely blank page or a
                    # conversion that returned nothing, and the difference
                    # matters, so count them instead of dropping them quietly.
                    blank += 1
                    continue
                fh.write(json.dumps({
                    "file": pdf.name,
                    "year": infer_year(pdf.name),
                    "page": p,
                    # The born-digital path records which keyword matched; there
                    # is no keyword scan here, so say where the page came from
                    # instead of inventing a match.
                    "targets": ["ocr"],
                    "text": text,
                }) + "\n")
                n += 1
    mb = out_path.stat().st_size / 1e6
    print(f"  wrote {out_path}: {n} pages, {mb:.1f} MB")
    if blank:
        print(f"  {blank} cached page(s) came back with no text and were left out. "
              f"Delete them from the cache to retry:  "
              f"find {cache} -size 0 -name '*.md' -delete")

    if args.verify:
        import subprocess
        # Look beside this script, then in the working directory. Copying just
        # this file into the corpus directory and running it there is a
        # reasonable thing to do -- it is where the PDFs are -- and doing so used
        # to end a successful paid run with a bare "No such file" traceback,
        # which reads like the OCR failed when the JSONL was already written.
        here = Path(__file__).resolve().parent
        cand = [here / "budget-books-extract.py", Path.cwd() / "budget-books-extract.py"]
        extractor = next((c for c in cand if c.exists()), None)
        print()
        if extractor is None:
            print(f"  {out_path} is written; --verify needs budget-books-extract.py.")
            print(f"  Looked in {here} and {Path.cwd()}. Run it yourself with:")
            print(f"    python3 /path/to/budget-books-extract.py {out_path} -o facts.csv")
            return
        subprocess.run([sys.executable, str(extractor),
                        str(out_path), "-o", str(out_path.with_suffix(".csv"))])


if __name__ == "__main__":
    main()
