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
     2009 and 2010 Volume 1s, 1,137 pages, $11.37. The only way to reach the last
     two missing citywide totals, 2007 and 2009, plus confirmation of 2010's
     derived one.

  2  ACQUISITION, born-digital -- 24 pages, $0.24, and the best value here.
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

Nothing is sent without --yes.

What is deliberately left out
-----------------------------
Six volumes are scans, 1,651 pages, but only three are in tier 1. The other
three are the 2005, 2007 and 2009 VOLUME 2s -- 514 pages, $5.14 -- and in the
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

How pages are sent: in batches, and why
---------------------------------------
Each book's wanted pages go to Datalab in batches of up to 100 (--batch-pages).
A batch is a PDF sliced from the book with pypdf and converted with
paginate=true, so the markdown comes back with a numbered break before every
page and is cut apart into one cache file per page, exactly as before. Datalab
bills per page, so a batch costs what its pages would cost one at a time. What
batching changes is the number of requests, and requests are the bottleneck:

    Datalab's ceilings    200 MB and 7,000 pages per request; 10 requests a
                          minute and 5 at once on the free and pay-as-you-go
                          plans (documentation.datalab.to/docs/common/limits)
    one page per request  the 1,137 scanned tier 1 pages are 1,137 uploads, each
                          followed by status polls, which this script counts
                          against the same 10 a minute: close to four hours
                          of requests before any processing time
    batches of 100        13 uploads; the rest of the wait is Datalab's
                          processing

Every request used to carry one page. That suited the first OCR runs -- a few
hundred scattered pages, where one page per request made page numbers
unambiguous and the cache per page for free -- and it was not revisited when
tier 1 added whole volumes, which then went page by page at a pace sized for
two hundred.

Batching has costs of its own. Each has a guardrail:

  A batch fails as a unit    A failed batch caches nothing and is never
                             re-sent automatically, since whether a failed
                             request was billed is not knowable from here; the
                             run ends by printing a one-page-at-a-time retry
                             command for it. Pages Datalab lists in
                             metadata.failed_pages are left uncached and the
                             rest of the batch is kept.
  Page numbers must be       The breaks must rise strictly within 0..k-1 of the
  recovered                  pages sent. A gap is allowed and cached as a blank
                             page, as a one-page request for an empty page would
                             be. Anything else and the batch is not split: its
                             raw markdown is kept as _unsplit-pNNN-pNNN.md beside
                             the pages, so paid-for output is never discarded.
  Long waits                 A batch can take many minutes. Its check URL goes
                             into _pending.json before the first poll and comes
                             out once its pages are cached, so a run that is
                             killed, sleeps or times out is collected by the
                             next run -- Datalab keeps results about a day --
                             instead of being paid for twice.
  Cross-page processing      The engine behind Datalab's convert endpoint looks
                             across pages -- text repeated at the top or bottom
                             of several pages can be dropped as a running header
                             -- so a page converted in a batch can differ from
                             the same page converted alone, and the extractor
                             was validated on single-page output. README.md has
                             a one-minute check that sends a few already-cached
                             pages as a batch into a scratch cache for
                             comparison; run it before trusting a new kind of
                             batch, and use --verify after any run.
  Upload size                Only the wanted pages travel, and a slice larger
                             than --batch-mb is cut in half again before it is
                             sent; nothing over 190 MB is ever uploaded. The
                             2024 book, whole, is 247 MB -- over the ceiling.

--batch-pages 1 still sends one page per request, which is only worth it to
isolate a page that keeps failing inside a batch; --estimate warns when that
would mean hundreds of requests. The same command re-run is always safe.

Resumable, cached and audited
-----------------------------
Each page's markdown is written to `<out stem>-cache/<book>/p<NNN>.md` -- so
`budget-books-ocr.jsonl` caches into `budget-books-ocr-cache/` -- and a page
whose file already exists is never re-sent, whichever batch size wrote it. An
interrupted run continues where it stopped, re-running is free, and the JSONL
can be rebuilt from cache alone with `--rebuild`. Two bookkeeping files sit in
the cache: _pending.json, the batches submitted but not yet collected, and
_requests.jsonl, one line per request with its pages, cost in cents and time
taken. The latter is the spend record, and what --estimate reads to predict how
long the next run will take instead of guessing. A key's own 30-day spend cap,
set in Datalab's billing settings, is the backstop outside this script: a
request over it is refused with HTTP 402, and the run stops sending at once.

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
import concurrent.futures
import datetime
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf is required:  pip install pypdf")

# Overridable so the batching can be tested against a local stand-in.
CONVERT = os.environ.get("DATALAB_CONVERT_URL", "https://www.datalab.to/api/v1/convert")
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
# Datalab's published rate for accurate conversion, $10 per 1,000 pages
# (datalab.to/pricing, 2026-09-23). The estimate uses it; the bill itself is
# each request's cost_breakdown, logged in _requests.jsonl.
CENTS_PER_PAGE = 1.0

# How pages travel -- see "How pages are sent" in the module docstring for why
# batches, and what each of these guards against. Datalab's own ceilings
# (documentation.datalab.to/docs/common/limits): 200 MB and 7,000 pages per
# request, 10 requests a minute and 5 at once on the free and pay-as-you-go
# plans.
BATCH_PAGES = 100            # --batch-pages: pages per request; 1 = one page per request
BATCH_MB = 90                # --batch-mb: a batch PDF bigger than this is split again
HARD_MB = 190                # never upload more than this, whatever --batch-mb says
REQUESTS_PER_MINUTE = 10     # --rpm: one budget for uploads AND status polls together
CONCURRENT = 3               # --concurrency: batches in flight at once (the plan allows 5)
RESULT_RETENTION_HOURS = 20  # Datalab deletes results about a day after they complete
PER_PAGE_WARN = 50           # --estimate warns above this many one-page requests


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


def compact(pages) -> str:
    """[1, 2, 3, 7, 9, 10] -> '1-3,7,9-10'."""
    runs = []
    for p in sorted(pages):
        if runs and p == runs[-1][1] + 1:
            runs[-1][1] = p
        else:
            runs.append([p, p])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


def pages_pdf(reader: PdfReader, pages: list[int]) -> bytes:
    """The given pages (1-indexed, in order) as one standalone PDF.

    Sending a slice of the PDF rather than an extracted image is deliberate.
    These scans are not all JPEG -- pulling the page image out means knowing
    which of DCTDecode, CCITTFaxDecode, JBIG2Decode or FlateDecode this
    particular scanner used, and getting it wrong on one book is a silent
    failure. pypdf already knows how to copy a page, and Datalab takes a PDF.

    Slicing, rather than uploading the whole book with Datalab's page_range, is
    deliberate too: only the pages being paid for travel, and a slice fits under
    Datalab's 200 MB ceiling when the book does not (the 2024 book is 247 MB).
    """
    w = PdfWriter()
    for p in pages:
        w.add_page(reader.pages[p - 1])
    # add_page copies the page tree, not the document catalogue, so the source's
    # /Info is dropped and each upload would otherwise arrive anonymous. Carry it
    # over and add which pages these are, so the file identifies itself on the
    # far side instead of relying on the filename alone. Page-level metadata --
    # /MediaBox and /Rotate -- is copied by add_page already, which matters:
    # several of these scans have rotated pages, and a rotated page sent as a
    # bare image comes back sideways.
    src = dict(reader.metadata or {})
    w.add_metadata({k: str(v) for k, v in src.items() if k != "/Producer"}
                   | {"/Subject": f"pages {compact(pages)} of {len(reader.pages)}"})
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def plan_batches(pages: list[int], n_pages: int, file_bytes: int,
                 max_pages: int, max_mb: float) -> list[list[int]]:
    """Cut a book's pages into batches of at most max_pages and roughly max_mb.

    Size is estimated from the book's average page, which is close for scans
    (every page is one image of about the same size); a batch that still comes
    out too big when built is halved in send_batch before anything is sent.
    """
    per_page = file_bytes / max(n_pages, 1)
    fit = max(1, int(max_mb * 1e6 // max(per_page, 1)))
    size = max(1, min(max_pages, fit))
    return [pages[i:i + size] for i in range(0, len(pages), size)]


# --------------------------------------------------------------------------
# Datalab
# --------------------------------------------------------------------------

class Fatal(Exception):
    """An error no other batch can succeed past: bad key, spend cap, no access."""


class BatchFailed(Exception):
    """This batch failed; others may still succeed."""


class RateLimiter:
    """At most `per_minute` requests a minute across every thread, evenly spaced.

    Uploads and status polls draw on the same budget. Counting only uploads is
    how a one-page-per-request run spent most of its allowance polling.
    """

    def __init__(self, per_minute: float):
        self.interval = 60.0 / per_minute
        self.lock = threading.Lock()
        self.next_slot = 0.0

    def wait(self) -> None:
        with self.lock:
            slot = max(time.monotonic(), self.next_slot)
            self.next_slot = slot + self.interval
        delay = slot - time.monotonic()
        if delay > 0:
            time.sleep(delay)


def _http_json(req: urllib.request.Request, timeout: float) -> dict:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def submit(blob: bytes, name: str, key: str, limiter: RateLimiter) -> tuple[str, str]:
    """Upload one PDF; return (request_check_url, request_id). Nothing is billed
    until this succeeds, so every failure here is safe to retry or to skip."""
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
    #
    # paginate=true is what makes a batch safe to cut back into pages: each page
    # opens with a "{N}------" line. It is the only setting batching adds; mode
    # and output_format are exactly what the validated single-page runs used.
    for field, value in (("output_format", "markdown"), ("mode", "accurate"),
                         ("paginate", "true")):
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
    # A slow uplink needs time: allow for about 2 Mbit/s, never under a minute.
    timeout = 60 + len(blob) / 250_000
    for attempt in range(6):
        limiter.wait()
        try:
            answer = _http_json(req, timeout)
            if not answer.get("success"):
                raise BatchFailed(f"upload refused: {answer.get('error')}")
            return answer["request_check_url"], str(answer.get("request_id") or "")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 402, 403):
                # 402 is the key's spend cap: a limit the owner set on purpose.
                raise Fatal(f"HTTP {exc.code} from Datalab: {exc.read()[:300]!r}")
            if exc.code == 413:
                raise BatchFailed("413: over Datalab's size limit")
            if exc.code in (429, 500, 502, 503, 529) and attempt < 5:
                time.sleep(60 if exc.code == 429 else 10 * (attempt + 1))
                continue
            raise BatchFailed(f"upload failed: HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == 5:
                raise BatchFailed(f"upload failed: {exc}")
            time.sleep(10 * (attempt + 1))
    raise BatchFailed("upload failed after retries")


def wait_for(check_url: str, key: str, limiter: RateLimiter, n_pages: int,
             timeout: float) -> dict:
    """Poll until the request is complete; return the finished response.

    Polls are spaced by the batch's size -- a 100-page batch is not going to be
    ready in five seconds -- and draw on the same request budget as uploads.
    Raises TimeoutError while the request is still running, which leaves it in
    the pending ledger for the next run to collect rather than pay for again.
    """
    req = urllib.request.Request(check_url, headers={"X-API-Key": key, "User-Agent": USER_AGENT})
    interval = min(60.0, max(5.0, 0.5 * n_pages))
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(interval)
        limiter.wait()
        try:
            answer = _http_json(req, 120)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise BatchFailed("result not found: expired or never existed")
            if exc.code in (401, 403):
                raise Fatal(f"HTTP {exc.code} while polling")
            if exc.code == 429:
                time.sleep(60)
            continue
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        if answer.get("status") != "complete":
            continue
        # Requests processed in Datalab's EU region return a signed result_url
        # instead of the content itself. Fetch it without the API key, and keep
        # the polling response's non-null fields, which carry the billing.
        if answer.get("result_url"):
            with urllib.request.urlopen(answer["result_url"], timeout=300) as resp:
                answer = {**json.loads(resp.read()),
                          **{k: v for k, v in answer.items() if v is not None}}
        if answer.get("success") is False:
            raise BatchFailed(f"conversion failed: {answer.get('error')}")
        return answer
    raise TimeoutError(check_url)


PAGE_BREAK = re.compile(r"^\{(\d+)\}-{8,}[ \t]*$", re.M)


def split_pages(markdown: str, pages: list[int]) -> dict[int, str]:
    """A batch's paginated markdown, cut back into one text per page sent.

    With paginate=true each page opens with a line of "{N}" and dashes, N
    counting from 0 within the uploaded PDF. The page numbers written to the
    cache come from our own list of what was sent, and N is only allowed to
    confirm it: the marks must rise strictly and stay inside 0..k-1. A page
    with no content can come back with no mark, which is a gap; it is returned
    as empty text, exactly as a blank page from a one-page request would be.
    Anything else -- marks out of order, repeated or out of range, or text
    before the first one -- raises, and the batch is not split at all.
    """
    marks = list(PAGE_BREAK.finditer(markdown))
    ids = [int(m.group(1)) for m in marks]
    k = len(pages)
    if not marks:
        if k == 1:
            return {pages[0]: markdown}
        raise ValueError(f"no page marks in a {k}-page batch")
    if any(b <= a for a, b in zip(ids, ids[1:])) or ids[0] < 0 or ids[-1] >= k:
        raise ValueError(f"page marks {ids[:12]}{'...' if len(ids) > 12 else ''} "
                         f"do not fit {k} pages")
    if markdown[:marks[0].start()].strip():
        raise ValueError("text before the first page mark")
    texts = {p: "" for p in pages}
    for j, m in enumerate(marks):
        stop = marks[j + 1].start() if j + 1 < len(marks) else len(markdown)
        body = markdown[m.end():stop].strip("\n")
        texts[pages[ids[j]]] = body + "\n" if body.strip() else ""
    return texts


class Ledger:
    """Requests submitted -- and so billed -- whose pages are not cached yet.

    An entry is written before the first poll and removed once its pages are in
    the cache. If a run is killed, the machine sleeps or a poll times out, the
    next run collects these results first (Datalab keeps them about a day)
    rather than paying to send the same pages again.
    """

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        try:
            self.entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.entries = {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.entries, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, check_url: str, file: str, pages: list[int]) -> None:
        with self.lock:
            self.entries[check_url] = {
                "file": file, "pages": pages,
                "submitted": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
            self._save()

    def remove(self, check_url: str) -> None:
        with self.lock:
            if self.entries.pop(check_url, None) is not None:
                self._save()

    def pending_pages(self) -> set[tuple[str, int]]:
        with self.lock:
            return {(e["file"], p) for e in self.entries.values() for p in e["pages"]}

    def age_hours(self, check_url: str) -> float:
        ts = datetime.datetime.fromisoformat(self.entries[check_url]["submitted"])
        return (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 3600


class RequestLog:
    """One JSON line per request: what was sent, what came back, what it cost.

    The audit trail for spend, and the history --estimate reads to say how long
    the next run will take instead of guessing.
    """

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def write(self, **row) -> None:
        row = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               **row}
        with self.lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def seconds_per_page(self) -> float | None:
        """Median wall-clock seconds per page over past successful batches."""
        try:
            rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
        except (OSError, ValueError):
            return None
        rates = sorted(r["elapsed"] / r["n"] for r in rows
                       if r.get("status") == "cached" and r.get("n") and r.get("elapsed"))
        return rates[len(rates) // 2] if rates else None


class Sender:
    """Everything the batch workers share: key, limits, cache, ledger, log."""

    def __init__(self, key, limiter, cache, ledger, log, max_bytes):
        self.key, self.limiter, self.cache = key, limiter, cache
        self.ledger, self.log, self.max_bytes = ledger, log, max_bytes
        self.pdf_lock = threading.Lock()      # pypdf readers are not thread-safe
        self.print_lock = threading.Lock()
        self.stop = threading.Event()         # set by a Fatal error: send nothing more
        self.failed = []                      # (file, pages, reason), for the retry hint
        self.cents = 0.0
        self.cached = 0
        self.poll_timeout = None              # seconds; None = scale with batch size

    def say(self, msg: str) -> None:
        with self.print_lock:
            print(msg)

    def send(self, pdf: Path, reader: PdfReader, pages: list[int]) -> None:
        """Build, upload, wait for and cache one batch. Never raises except Fatal."""
        if self.stop.is_set():
            return
        with self.pdf_lock:
            blob = pages_pdf(reader, pages)
        if len(blob) > self.max_bytes and len(pages) > 1:
            half = len(pages) // 2
            self.send(pdf, reader, pages[:half])
            self.send(pdf, reader, pages[half:])
            return
        label = f"{pdf.stem[:34]} p{compact(pages)}"
        try:
            check_url, request_id = submit(blob, f"{pdf.stem}-p{pages[0]}-{pages[-1]}.pdf",
                                           self.key, self.limiter)
        except BatchFailed as exc:
            if "413" in str(exc) and len(pages) > 1:     # refused unbilled: try halves
                half = len(pages) // 2
                self.send(pdf, reader, pages[:half])
                self.send(pdf, reader, pages[half:])
                return
            self._fail(pdf, pages, str(exc), label)
            return
        self.ledger.add(check_url, pdf.name, pages)
        self.say(f"    sent  {label}  ({len(pages)}p, {len(blob) / 1e6:.1f} MB)")
        self.collect(check_url, pdf.name, pages, started=time.time(), request_id=request_id)

    def collect(self, check_url: str, file: str, pages: list[int], started: float | None,
                request_id: str = "") -> None:
        """Wait for a submitted batch and cache its pages. A timeout leaves it in
        the ledger for the next run; nothing here re-sends anything."""
        label = f"{Path(file).stem[:34]} p{compact(pages)}"
        try:
            answer = wait_for(check_url, self.key, self.limiter, len(pages),
                              timeout=self.poll_timeout or max(900, 30 * len(pages)))
        except TimeoutError:
            self.say(f"    still running after the wait: {label}. Left in the ledger; "
                     f"the next run collects it without paying again.")
            return
        except BatchFailed as exc:
            self.ledger.remove(check_url)
            self._fail(Path(file), pages, str(exc), label, request_id=request_id)
            return
        cents = (answer.get("cost_breakdown") or {}).get("final_cost_cents")
        with self.print_lock:
            self.cents += cents or 0
        book_dir = self.cache / Path(file).stem
        book_dir.mkdir(parents=True, exist_ok=True)
        try:
            texts = split_pages(answer.get("markdown") or "", pages)
        except ValueError as exc:
            # Paid for and unusable as pages: keep the raw output so it is never
            # thrown away, cache nothing, and send nothing again.
            raw = book_dir / f"_unsplit-p{pages[0]:03d}-p{pages[-1]:03d}.md"
            raw.write_text(answer.get("markdown") or "", encoding="utf-8")
            self.ledger.remove(check_url)
            self._fail(Path(file), pages, f"could not split: {exc}; raw output in {raw.name}",
                       label, request_id=request_id, cents=cents)
            return
        failed_idx = set((answer.get("metadata") or {}).get("failed_pages") or [])
        failed = [pages[i] for i in sorted(failed_idx) if 0 <= i < len(pages)]
        for pg, text in texts.items():
            if pg not in failed:
                (book_dir / f"p{pg:03d}.md").write_text(text, encoding="utf-8")
        self.ledger.remove(check_url)
        kept = len(pages) - len(failed)
        with self.print_lock:
            self.cached += kept
        self.log.write(file=file, pages=compact(pages), n=len(pages), request_id=request_id,
                       status="cached", failed_pages=compact(failed) if failed else "",
                       # A batch collected from the ledger was not timed from its
                       # upload, so it says nothing about how long batches take.
                       elapsed=round(time.time() - started, 1) if started else None,
                       runtime=answer.get("runtime"), cents=cents)
        self.say(f"    done  {label}  {kept} cached"
                 + (f", {len(failed)} failed: p{compact(failed)}" if failed else "")
                 + (f"  {cents}c" if cents is not None else ""))
        if failed:
            self.failed.append((file, failed, "Datalab reported these pages as failed"))

    def _fail(self, pdf: Path, pages: list[int], reason: str, label: str,
              request_id: str = "", cents=None) -> None:
        self.failed.append((pdf.name, pages, reason))
        self.log.write(file=pdf.name, pages=compact(pages), n=len(pages), request_id=request_id,
                       status="failed", error=reason, cents=cents)
        self.say(f"    FAILED {label}: {reason}")


# --------------------------------------------------------------------------

def select(root: Path, wanted: list[str]) -> list[Path]:
    """Files for --book. A full filename matches only itself: as a substring,
    "2007 Annual Budget, Volume 1.pdf" also matches "2006-2007 Annual Budget,
    Volume 1.pdf", and manual mode would send pages of the wrong book."""
    pdfs = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    hits = []
    for w in wanted:
        exact = [p for p in pdfs if p.name.lower() == w.lower()]
        found = exact or [p for p in pdfs if w.lower() in p.name.lower()]
        if not found:
            print(f"  ! no file matching {w!r}")
        hits += [p for p in found if p not in hits]
    return hits


def parse_pages(spec: str) -> list[int]:
    """'58,60-62' -> [58, 60, 61, 62]."""
    out = []
    for part in re.findall(r"\d+(?:\s*-\s*\d+)?", spec):
        lo, _, hi = part.replace(" ", "").partition("-")
        out += range(int(lo), int(hi or lo) + 1)
    return sorted(set(out))


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
    ap.add_argument("--book", action="append", default=[], metavar="NAME",
                    help="a PDF's filename (which then matches only itself) or a "
                         "substring of one; repeatable. Defaults to the three Volume 1 "
                         "scans the born-digital books cannot cover.")
    ap.add_argument("--window", default="{}-{}".format(*DEFAULT_WINDOW), metavar="LO-HI",
                    help="with --book: page range to send (default %(default)s)")
    ap.add_argument("--pages", default="", metavar="N,N-M,...",
                    help="exact pages to send, overriding --window; ranges allowed")
    ap.add_argument("--batch-pages", type=int, default=BATCH_PAGES, metavar="N",
                    help="pages per request (default %(default)s). Datalab bills per page "
                         "either way; 1 sends one page per request, which is only worth "
                         "it to isolate a page that fails inside a batch")
    ap.add_argument("--batch-mb", type=float, default=BATCH_MB, metavar="MB",
                    help="target upload size per request (default %(default)s; Datalab's "
                         "ceiling is 200)")
    ap.add_argument("--rpm", type=float, default=REQUESTS_PER_MINUTE, metavar="N",
                    help="requests per minute, uploads and status polls together "
                         "(default %(default)s, Datalab's free and pay-as-you-go limit; "
                         "the Team plan allows 200)")
    ap.add_argument("--concurrency", type=int, default=CONCURRENT, metavar="N",
                    help="requests in flight at once (default %(default)s; the free plan "
                         "allows 5)")
    ap.add_argument("--pace", type=float, default=None, metavar="SECONDS",
                    help="older spelling of --rpm: seconds between requests")
    ap.add_argument("--poll-timeout", type=float, default=None, metavar="SECONDS",
                    help="how long to wait for one batch before leaving it in the "
                         "ledger for the next run (default 15 min, or 30s per page "
                         "for big batches)")
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
    explicit = parse_pages(args.pages)
    if args.pace:
        args.rpm = 60.0 / args.pace
    args.batch_pages = max(1, args.batch_pages)
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

    # Batches submitted by an earlier run and not collected yet. They are paid
    # for, so their pages are not sent again; results older than Datalab keeps
    # them are dropped here, before pricing, so those pages are counted to send.
    ledger = Ledger(cache / "_pending.json")
    for url in list(ledger.entries):
        if ledger.age_hours(url) > RESULT_RETENTION_HOURS:
            e = ledger.entries[url]
            print(f"  ! a batch submitted {ledger.age_hours(url):.0f}h ago "
                  f"({e['file']} p{compact(e['pages'])}) is past Datalab's retention; "
                  f"its pages will be sent again")
            ledger.remove(url)
    pending = ledger.pending_pages()

    plan, by_tier = [], collections.Counter()
    n_requests = 0
    for pdf in sorted(want):
        pages = sorted(want[pdf])
        reader = PdfReader(str(pdf))
        to_send = [pg for pg in pages
                   if not (cache / pdf.stem / f"p{pg:03d}.md").exists()
                   and (pdf.name, pg) not in pending]
        batches = plan_batches(to_send, len(reader.pages), pdf.stat().st_size,
                               args.batch_pages, args.batch_mb)
        plan.append((pdf, reader, pages, batches))
        n_requests += len(batches)
        for pg in pages:
            by_tier[want[pdf][pg]] += 1
        tset = "".join(str(t) for t in sorted({want[pdf][pg] for pg in pages}))
        print(f"  [t{tset}] {pdf.name[:46]:<46} {len(pages):>4} of {len(reader.pages):>4}p, "
              f"{len(pages) - len(to_send):>4} cached or pending, "
              f"{len(batches):>3} request{'s' if len(batches) != 1 else ''}")
    print()
    for t in sorted(by_tier):
        label = {1: "acquisition, scanned", 2: "acquisition, born-digital",
                 3: "validation, published figures", 4: "validation, all pies & tables",
                 0: "manual selection"}[t]
        print(f"  tier {t}  {label:<26} {by_tier[t]:>5}p = "
              f"${by_tier[t] * CENTS_PER_PAGE / 100:>6,.2f}")

    todo = sum(len(b) for *_, batches in plan for b in batches)
    print(f"\n  {todo} pages to send x {CENTS_PER_PAGE}c = ${todo * CENTS_PER_PAGE / 100:.2f}")
    if pending:
        print(f"  {len(ledger.entries)} batch(es), {len(pending)} pages, were submitted "
              f"by an earlier run and not collected; they are collected first, at no cost")
    # Time, honestly. Every request needs at least one poll after its upload, so
    # the request budget alone sets a floor; Datalab's processing comes on top,
    # and the request log's history is the only fair guess at it.
    if todo:
        floor = 2 * n_requests / args.rpm
        print(f"  {n_requests} request{'s' if n_requests != 1 else ''} of up to "
              f"{args.batch_pages} page{'s' if args.batch_pages != 1 else ''}, "
              f"{args.concurrency} in flight, within {args.rpm:g} requests/minute: "
              f"at least {floor:.0f} min for the requests themselves")
        spp = RequestLog(cache / "_requests.jsonl").seconds_per_page()
        if spp:
            print(f"  past batches took a median {spp:.1f}s per page, so roughly "
                  f"{spp * todo / args.concurrency / 60 + floor:.0f} min in all")
        else:
            print("  Datalab's processing time comes on top; the first run records it "
                  "in _requests.jsonl for the next estimate")
        if args.batch_pages == 1 and todo > PER_PAGE_WARN:
            print(f"\n  ! --batch-pages 1 means one request per page: {todo} uploads, each "
                  f"with its polls, at least {floor / 60:.1f} hours before any processing "
                  f"time. Datalab bills per page, so batches cost the same. Use single "
                  f"pages only to isolate a page that keeps failing inside a batch.")

    if args.estimate:
        print("\n  --estimate: nothing sent. Add --yes to spend it.")
        return
    if todo and not (args.yes or args.rebuild):
        sys.exit("\n  refusing to spend money without --yes")

    if not args.rebuild and (todo or ledger.entries):
        key = api_key()
        cache.mkdir(parents=True, exist_ok=True)
        sender = Sender(key, RateLimiter(args.rpm), cache, ledger,
                        RequestLog(cache / "_requests.jsonl"),
                        int(min(1.5 * args.batch_mb, HARD_MB) * 1e6))
        sender.poll_timeout = args.poll_timeout
        print()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency))
        futures = [pool.submit(sender.collect, url, e["file"], e["pages"], None)
                   for url, e in list(ledger.entries.items())]
        futures += [pool.submit(sender.send, pdf, reader, batch)
                    for pdf, reader, _pages, batches in plan for batch in batches]
        try:
            for fut in concurrent.futures.as_completed(futures):
                try:
                    fut.result()
                except Fatal as exc:
                    if not sender.stop.is_set():
                        sender.stop.set()
                        sender.say(f"\n  STOPPING: {exc}. Nothing more will be sent; "
                                   f"batches already submitted are still collected.")
        except KeyboardInterrupt:
            sender.stop.set()
            print(f"\n  interrupted. Batches already submitted stay in {ledger.path.name} "
                  f"and are collected by the next run, at no cost.", flush=True)
            os._exit(130)
        pool.shutdown(wait=True)
        print(f"\n  cached {sender.cached} pages; Datalab reports "
              f"${sender.cents / 100:.2f} billed for this run's collected batches")
        if ledger.entries:
            print(f"  {len(ledger.entries)} batch(es) still running on Datalab's side, "
                  f"recorded in {ledger.path}. Run the same command again later to "
                  f"collect them; they are not sent or paid for again.")
        if sender.failed:
            print(f"  {len(sender.failed)} set(s) of pages not cached. None is re-sent "
                  f"automatically: a request that failed may still have been billed.")
            for file, pages, reason in sender.failed:
                print(f"    {file} p{compact(pages)}: {reason}")
            print("  To retry them one page at a time, after checking the reason:")
            for file, pages, _reason in sender.failed:
                print(f'    python3 {Path(sys.argv[0]).name} {args.root} --book "{file}" '
                      f'--pages {compact(pages)} --batch-pages 1 --yes')

    # --- JSONL, in the same shape as --dump-text -------------------------
    n = blank = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for pdf, _reader, pages, _batches in plan:
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
