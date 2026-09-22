"""
Boulder budget books — OCR the scanned volumes through Datalab
==============================================================
Third stage of the budget-book pipeline, and the only one that costs money:

    budget-books-inventory.py   what is in the corpus, and which books are scans
    budget-books-ocr.py         <- this: turn the scans into readable text
    budget-books-extract.py     pull the figures out of either kind of text

Run it on your local copy of the books, with a Datalab key in the environment:

    export DATALAB_API_KEY=...
    python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --estimate   # what it will cost
    python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --yes        # actually spend it

The output is JSONL in exactly the shape `budget-books-inventory.py --dump-text`
writes, so `budget-books-extract.py` reads OCR'd and born-digital pages through
the same code path:

    python3 budget-books-extract.py dump.jsonl budget-books-ocr.jsonl -o facts.csv

Why this sends 200 pages and not 1,651
--------------------------------------
Six of the twenty-odd volumes are scans with no text layer at all — the
inventory measures 0 extractable characters on every sampled page:

    2005 Annual Budget, Volume 2.pdf   151p    2009 Annual Budget, Volume 1.pdf   411p
    2007 Annual Budget, Volume 1.pdf   377p    2009 Annual Budget, Volume 2.pdf   211p
    2007 Annual Budget, Volume 2.pdf   152p    2010 Annual Budget, Volume 1.pdf   349p

That is 1,651 pages, and sending all of them would be a waste of about $11 and
several hours. Two cuts bring it to roughly 200, and both are measured off the
born-digital books rather than guessed.

**Skip every Volume 2.** In the books we CAN read, Volume 2 is the capital
program and departmental detail and carries essentially no citywide summary
pages: the 2006‑2007 Volume 2 matched one summary keyword in 149 pages, and the
2008 Volume 2 matched none in 207. Volume 1 is where the citywide figures live.
That also drops 2005 Volume 2 entirely, since 2005 Volume 1 is born-digital and
already yielded that year in full.

**Send a window, not the whole volume.** Across every book in the corpus whose
text we can read, the citywide summary block sits between page 58 and page 102:

    2006-2007 Vol 1   block p58, narrative p59, sources p64, uses p70, FTE p83
    2008 Vol 1        block p71, uses p87, FTE p100
    2011              total p67, sources p76, uses p84, FTE p96
    2012 / 2013       overview p93 / p97
    2014 / 2015 / 2016 / 2017   p96 / p100 / p100 / p102

DEFAULT_WINDOW spans that range with room on both sides. It is a default, not a
fact about the 2009 book — if a run comes back with nothing, widen it rather
than concluding the figures are absent. `--every 8` is the cheap way to look:
it thins the window to every eighth page, so you can find the section for about
six cents and then re-run tightly around it.

What it costs
-------------
Datalab bills per page (0.75 cents in accurate mode at the time of writing), so
the three Volume 1 windows come to around $1.50. `--estimate` prints the page
count and the arithmetic and exits without spending anything; nothing is sent
until `--yes`.

Resumable and cached
--------------------
Each page's markdown is written to `<out stem>-cache/<book>/p<NNN>.md` — so
`budget-books-ocr.jsonl` caches into `budget-books-ocr-cache/` — and a page
whose file already exists is never re-sent. An interrupted run continues where
it stopped, re-running is free, and the JSONL can be rebuilt from cache alone
with `--rebuild`.

One thing to watch
------------------
Datalab's markdown is *cleaner* than pypdf's output, and `budget-books-extract.py`
was written against pypdf's mangling — fused labels, commas turned into periods,
numbers run together. Cleaner input is not automatically parsed input: markdown
renders a table as pipe-delimited rows, which is a shape the extractor has never
seen. `--verify` runs the extractor over the new JSONL and reports which
measures came out, so a run that produced text but no figures is visible
immediately instead of looking like a year with no data.
"""

from __future__ import annotations

import argparse
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
# Pages 58-102 in every readable book, plus margin. See the module docstring.
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
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Datalab
# --------------------------------------------------------------------------

def post_pdf(blob: bytes, name: str, key: str) -> str:
    boundary = "----charting-boulder-" + os.urandom(8).hex()
    parts = []
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
    ap = argparse.ArgumentParser(description="OCR the scanned budget books through Datalab.")
    ap.add_argument("root", help="directory holding the PDFs (searched recursively)")
    ap.add_argument("-o", "--out", default="budget-books-ocr.jsonl")
    ap.add_argument("--cache", default="", help="markdown cache dir (default: <out>-cache)")
    ap.add_argument("--book", action="append", default=[], metavar="SUBSTRING",
                    help="filename substring to include; repeatable. Defaults to the "
                         "three Volume 1 scans the born-digital books cannot cover.")
    ap.add_argument("--window", default="{}-{}".format(*DEFAULT_WINDOW), metavar="LO-HI",
                    help="page range to send (default %(default)s)")
    ap.add_argument("--pages", default="", metavar="N,N,...",
                    help="exact pages to send, overriding --window")
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

    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"no such directory: {root}")
    lo, _, hi = args.window.partition("-")
    window = (int(lo), int(hi))
    explicit = [int(x) for x in re.findall(r"\d+", args.pages)]
    out_path = Path(args.out)
    cache = Path(args.cache) if args.cache else out_path.with_name(out_path.stem + "-cache")

    books = select(root, args.book or DEFAULT_BOOKS)
    if not books:
        sys.exit("nothing matched — check --book against the real filenames")

    plan = []
    for pdf in books:
        reader = PdfReader(str(pdf))
        pages = page_list(len(reader.pages), window, args.every, explicit)
        plan.append((pdf, reader, pages))
        cached = sum(1 for p in pages if (cache / pdf.stem / f"p{p:03d}.md").exists())
        print(f"  {pdf.name[:52]:<52} {len(reader.pages):>4}p total, "
              f"{len(pages):>3} selected, {cached:>3} already cached")

    todo = sum(1 for pdf, _, pages in plan
               for p in pages if not (cache / pdf.stem / f"p{p:03d}.md").exists())
    print(f"\n  {todo} pages to send x {CENTS_PER_PAGE}c = "
          f"${todo * CENTS_PER_PAGE / 100:.2f}"
          f"   (~{todo * PACE_SECONDS / 60:.0f} min at {PACE_SECONDS}s/page)")

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
                dest.write_text(answer.get("markdown") or "")
                sent += 1
                cents = (answer.get("cost_breakdown") or {}).get("final_cost_cents")
                print(f"    {pdf.stem[:34]:<34} p{p:>3}  {len(dest.read_text()):>5} chars"
                      f"  {cents if cents is not None else '?'}c")
                time.sleep(PACE_SECONDS)
        print(f"\n  sent {sent} pages")

    # --- JSONL, in the same shape as --dump-text -------------------------
    n = 0
    with out_path.open("w") as fh:
        for pdf, _reader, pages in plan:
            for p in pages:
                src = cache / pdf.stem / f"p{p:03d}.md"
                if not src.exists():
                    continue
                text = src.read_text()
                if not text.strip():
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

    if args.verify:
        import subprocess
        here = Path(__file__).resolve().parent
        print()
        subprocess.run([sys.executable, str(here / "budget-books-extract.py"),
                        str(out_path), "-o", str(out_path.with_suffix(".csv"))])


if __name__ == "__main__":
    main()
