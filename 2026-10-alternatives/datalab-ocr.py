"""Re-OCR the 1986-1999 CDE yearbooks through the Datalab convert API.

Why this exists: the scanned yearbooks ship an embedded OCR text layer that
keeps headings and district names but loses the numbers. Measured on the 1986
volume, the district-by-grade table recovers 3.9% of its cells and the staff
table recovers none (see audit/proof-run.md, finding A3). Datalab's accurate
mode reads the same page images cleanly, including thousands separators and
decimals, at 0.75 cents a page.

The script is deliberately frugal. It does not send whole volumes. It uses the
cheap embedded text layer for the one thing that layer is good at - telling you
which page a table starts on - then sends only those page images for real OCR.

For each volume it:

  1. downloads the yearbook PDF to data/raw/yearbooks/ (about 110 MB each),
  2. decodes the embedded text layer to locate the wanted tables,
  3. pulls those pages out as JPEGs (one scanned image per page),
  4. sends each to Datalab in accurate mode and saves the markdown,
  5. deletes the PDF, keeping the page images and the markdown.

It is resumable: a page whose markdown already exists is skipped, so an
interrupted run continues where it stopped. Every request is recorded in
data/interim/yearbooks/<year>/index.json with its cost and Datalab request id.

Needs an API key in the environment. The key is never written to disk by this
script and must not be committed:

    export DATALAB_API_KEY=...
    python3 datalab-ocr.py            # all volumes, 1986-1999
    python3 datalab-ocr.py 1986 1987  # named volumes only
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
YEARBOOKS = HERE / "data" / "raw" / "yearbooks"
OUT = HERE / "data" / "interim" / "yearbooks"

SERIAL = "https://spl.cde.state.co.us/artemis/edserials/ed27919internet"
CONVERT = "https://www.datalab.to/api/v1/convert"
USER_AGENT = "charting-boulder/datalab-ocr (+https://github.com/brianckeegan/charting-boulder)"
YEARS = list(range(1986, 2000))

# Free tier allows 10 requests a minute and 5 at once. Stay under both.
WORKERS = 4
PACE_SECONDS = 6.5

# Page-span settings. MAX_GAP is how many unflagged pages may sit inside one
# run of a table before it is treated as two tables; MARGIN extends each run
# at both ends to catch a continuation page past the last repeated heading.
MAX_GAP = 10
MARGIN = 4

# The tables worth paying to read, matched against the embedded text layer.
# Headings drift across fourteen volumes, so each pattern is loose and the
# page's real identity is taken from what Datalab returns, not from this match.
WANTED = {
    "district_by_grade": r"MEMBERSHIP BY SCHOOL DISTRICT AND GRADE",
    "district_summary": r"SUMMARY OF SELECTED SCHOOL DISTRICT DATA",
    "district_trends": r"TRENDS? IN ENROLLMENT|STATE TRENDS IN COLORADO PUBLIC SCHOOL",
}


def api_key() -> str:
    key = os.environ.get("DATALAB_API_KEY", "").strip()
    if not key:
        sys.exit("DATALAB_API_KEY is not set. export it and run again.")
    return key


# --------------------------------------------------------------------------
# the PDF: embedded text to find pages, embedded JPEGs to send
# --------------------------------------------------------------------------

def download_volume(year: int) -> Path:
    YEARBOOKS.mkdir(parents=True, exist_ok=True)
    dest = YEARBOOKS / f"{year}.pdf"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    url = f"{SERIAL}/ed27919{year}internet.pdf"
    print(f"  downloading {url}")
    delay = 2
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "charting-boulder/datalab-ocr"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                dest.write_bytes(resp.read())
            return dest
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"    retry after {exc}")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def page_texts(pdf: bytes) -> list[str]:
    """Decode the invisible OCR layer. Good enough to locate a heading; not
    good enough to read a number, which is the whole reason for this script."""
    pages = []
    for match in re.finditer(rb"stream\r?\n", pdf):
        start = match.end()
        end = pdf.find(b"endstream", start)
        if end < 0:
            continue
        try:
            body = zlib.decompress(pdf[start:end])
        except Exception:  # noqa: BLE001
            continue
        if b"TJ" not in body and b"Tj" not in body:
            continue
        hexes = re.findall(rb"<([0-9A-Fa-f]{4,})>", body)
        if hexes:
            text = "".join(
                bytes.fromhex(h.decode()).decode("utf-16-be", errors="replace") for h in hexes
            )
        else:
            text = " ".join(
                s[1:-1].decode("latin-1") for s in re.findall(rb"\((?:[^()\\]|\\.)*\)", body)
            )
        pages.append(re.sub(r"\s+", " ", text).strip())
    return pages


def page_images(pdf: bytes) -> list[bytes]:
    """One scanned JPEG per page, in stream order."""
    jpegs = []
    for match in re.finditer(rb"/DCTDecode", pdf):
        start = pdf.find(b"stream", match.end())
        if start < 0:
            continue
        start = pdf.find(b"\n", start) + 1
        end = pdf.find(b"endstream", start)
        blob = pdf[start:end].strip(b"\r\n")
        if blob[:2] == b"\xff\xd8":
            jpegs.append(blob)
    return jpegs


def wanted_pages(texts: list[str]) -> dict[int, str]:
    """Page index -> which table it looks like.

    A long table repeats its heading on most pages but not all, and the
    embedded OCR layer misses some of the ones it does repeat. Taking only
    the flagged pages therefore under-covers the table: in the 1986 volume
    that lost roughly half the districts, because the pages in the gaps were
    never sent for OCR at all and so were invisible to every later stage.

    So a table is treated as a contiguous SPAN. Each run of flagged pages
    claims every page from its first to its last, gaps included, plus a
    margin on each end to catch a continuation page that trails past the last
    heading. Over-sending costs 0.75 cents a page; under-sending silently
    loses districts.
    """
    hits: dict[int, str] = {}
    for i, text in enumerate(texts):
        for label, pattern in WANTED.items():
            if re.search(pattern, text or "", re.I):
                hits[i] = label
                break
    if not hits:
        return {}

    spread: dict[int, str] = {}
    flagged = sorted(hits)
    # Group flagged pages into runs of the same table, allowing a gap of a few
    # unflagged pages inside one run.
    run_start = previous = flagged[0]
    label = hits[run_start]

    def claim(start: int, end: int, table: str) -> None:
        for j in range(max(0, start - MARGIN), min(len(texts), end + MARGIN + 1)):
            spread.setdefault(j, table)

    for page in flagged[1:]:
        same_table = hits[page] == label
        if same_table and page - previous <= MAX_GAP:
            previous = page
            continue
        claim(run_start, previous, label)
        run_start = previous = page
        label = hits[page]
    claim(run_start, previous, label)
    return spread


# --------------------------------------------------------------------------
# Datalab
# --------------------------------------------------------------------------

def post_image(jpeg: bytes, name: str, key: str) -> str:
    boundary = "----charting-boulder-" + os.urandom(8).hex()
    parts = []
    for field, value in (("output_format", "markdown"), ("mode", "accurate")):
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
        f"Content-Type: image/jpeg\r\n\r\n".encode()
    )
    parts.append(jpeg)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    # Datalab sits behind Cloudflare, which rejects the default
    # "Python-urllib/3.x" agent with error 1010. Any ordinary agent passes.
    req = urllib.request.Request(
        CONVERT, data=body,
        headers={
            "X-API-Key": key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT,
        },
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

def process_volume(year: int, key: str) -> dict:
    out_dir = OUT / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {"year": year, "pages": {}}

    pdf_path = download_volume(year)
    pdf = pdf_path.read_bytes()
    texts, images = page_texts(pdf), page_images(pdf)
    targets = wanted_pages(texts)
    print(f"  {year}: {len(texts)} text pages, {len(images)} page images, {len(targets)} pages to read")

    todo = [i for i in sorted(targets) if not (out_dir / f"p{i:03d}.md").exists() and i < len(images)]
    print(f"  {year}: {len(todo)} still to send ({len(targets) - len(todo)} already done)")

    def one(i: int) -> tuple[int, dict]:
        url = post_image(images[i], f"{year}_p{i:03d}.jpg", key)
        answer = poll(url, key)
        markdown = answer.get("markdown") or ""
        (out_dir / f"p{i:03d}.md").write_text(markdown)
        return i, {
            "guessed_table": targets[i],
            "request_id": url.rsplit("/", 1)[-1],
            "cost_cents": (answer.get("cost_breakdown") or {}).get("final_cost_cents"),
            "quality": answer.get("parse_quality_score"),
            "heading": next((ln.strip("# ").strip() for ln in markdown.splitlines()
                             if ln.startswith("#")), "")[:120],
            "chars": len(markdown),
        }

    if todo:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = []
            for i in todo:
                futures.append(pool.submit(one, i))
                time.sleep(PACE_SECONDS)
            for future in futures:
                try:
                    i, record = future.result()
                    index["pages"][str(i)] = record
                    print(f"    p{i:03d} {record['cost_cents']}c {record['heading'][:60]}")
                except Exception as exc:  # noqa: BLE001
                    print(f"    FAILED: {exc}", file=sys.stderr)

    # Record every page on disk, not just the ones this run sent. index.json is
    # only written when a volume finishes, so a volume interrupted part-way and
    # resumed later would otherwise list only the second run's pages - and
    # check-row-totals.py reads this index to know which table each page holds.
    for page_file in sorted(out_dir.glob("p*.md")):
        i = int(page_file.stem[1:])
        if str(i) in index["pages"]:
            continue
        markdown = page_file.read_text()
        index["pages"][str(i)] = {
            "guessed_table": targets.get(i),
            "request_id": None,
            "cost_cents": None,
            "quality": None,
            "heading": next((ln.strip("# ").strip() for ln in markdown.splitlines()
                             if ln.startswith("#")), "")[:120],
            "chars": len(markdown),
            "recovered_from_disk": True,
        }

    index["total_cost_cents"] = round(
        sum((p.get("cost_cents") or 0) for p in index["pages"].values()), 2
    )
    index["pages_on_disk"] = len(list(out_dir.glob("p*.md")))
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    # The PDF is 110 MB and re-downloadable; the page images and markdown are
    # what the cleaning step needs.
    pdf_path.unlink(missing_ok=True)
    return index


def main() -> None:
    key = api_key()
    years = [int(a) for a in sys.argv[1:]] or YEARS
    OUT.mkdir(parents=True, exist_ok=True)
    grand_total = 0.0
    for year in years:
        print(f"Volume {year}")
        try:
            index = process_volume(year, key)
        except Exception as exc:  # noqa: BLE001
            print(f"  volume {year} failed: {exc}", file=sys.stderr)
            continue
        grand_total += index.get("total_cost_cents") or 0
        print(f"  {year} done: {len(index['pages'])} pages, {index['total_cost_cents']} cents")
    print(f"\nTotal so far: {grand_total:.2f} cents")


if __name__ == "__main__":
    main()
