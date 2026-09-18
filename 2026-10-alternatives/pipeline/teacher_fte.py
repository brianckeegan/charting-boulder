"""Build the teacher-FTE panel, school and district grain, from every source.

Teacher FTE is the archive's thinnest measure and the one whose coverage was
most badly misread. The inventory classified these files by their published
label, and the labels lie: CDE calls the same report "Student-teacher ratios"
whether it is by school or by district, publishes it in two different serials
in the same year, and in several years the two disagree about which grain
they carry. Reading the labels gave three usable school-grain years. Reading
the files gives far more.

So this module fetches every ratio and salary file the inventory names, from
both serials, and decides the grain from the parsed header rather than the
title.

Two decoding wrinkles, both in the PDFs:

  - Several vintages embed a subset font whose character codes sit a fixed
    distance from ASCII - 29, as it happens - so the text extracts as
    "3XSLO7HDFKHU" until it is shifted back to "PupilTeacher". The offset is
    detected per file by trying shifts until known column names appear.
  - The text is kerning-split, so "1,234.5" arrives as "1 , 2 3 4 . 5" and
    every field has to be reassembled from character positions rather than
    split on whitespace.

Run:  python3 -m pipeline.teacher_fte
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import time
import urllib.request
import zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .schema import normalize_code, parse_decimal, parse_count

HERE = Path(__file__).resolve().parent.parent
LOOKUPS = HERE / "data" / "lookups"
RAW = HERE / "data" / "raw" / "fte"
PROCESSED = HERE / "data" / "processed"
AUDIT = HERE / "audit"

USER_AGENT = "charting-boulder/pipeline (+https://github.com/brianckeegan/charting-boulder)"
RATIO_FILE = re.compile(r"pupil.?teacher|student.?teacher|teacher.*fte", re.I)

# Column names that mark a successfully decoded header.
HEADER_WORDS = re.compile(
    r"COUNTY|DISTRICT|SCHOOL|TEACHER|PUPIL|ORGANIZATION|MEMBERSHIP", re.I)


# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------

def fetch(url: str, dest: Path, tries: int = 4) -> bytes:
    if dest.exists() and dest.stat().st_size > 0:
        return dest.read_bytes()
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return data
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_all() -> list[dict]:
    """Every ratio/salary file in the inventory, from both serials."""
    with (LOOKUPS / "inventory.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    wanted = [r for r in rows
              if RATIO_FILE.search(r["label"]) or RATIO_FILE.search(r["filename"])]

    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    landed = []
    for row in wanted:
        name = f"{row['series']}-{row['year']}-{row['filename']}"
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        dest = RAW / name
        already = dest.exists() and dest.stat().st_size > 0
        try:
            data = fetch(row["url"], dest)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {name}: {exc}")
            continue
        # A file already on disk was not fetched again, so it keeps the date it
        # was actually retrieved. Stamping today's date on every rerun would
        # make the manifest claim a retrieval that never happened, and quietly
        # destroy the one thing it exists to record.
        retrieved = (manifest.get(name, {}).get("fetched_at") if already else None)
        manifest[name] = {
            "url": row["url"], "label": row["label"], "series": row["series"],
            "year": int(row["year"]), "format": row["fmt"],
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": retrieved or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        landed.append({**row, "path": dest, "sha256": manifest[name]["sha256"]})
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    # CDE publishes the same file at more than one year's URL. The 2016 and
    # 2017 "Pupil-teacher ratio by school" PDFs are byte-identical - same
    # SHA-256, same 583,100 bytes - so parsing both produced two years with
    # exactly the same 1,784 schools and 49,277.5 FTE. That is one year of
    # data wearing two labels, and publishing it as two would invent a year.
    #
    # The earliest year that carries a given file keeps it. Later duplicates
    # are dropped and named, because this is the source's error and a reader
    # should be told rather than shown a gap.
    by_hash: dict[str, dict] = {}
    duplicates = []
    for item in sorted(landed, key=lambda r: (int(r["year"]), r["series"])):
        seen = by_hash.get(item["sha256"])
        if seen and int(seen["year"]) != int(item["year"]):
            duplicates.append((int(item["year"]), int(seen["year"]), item["path"].name))
            continue
        by_hash.setdefault(item["sha256"], item)
    if duplicates:
        print("  duplicate files, dropped:")
        for year, original, name in duplicates:
            print(f"    {year} is byte-identical to {original}: {name}")
    kept = [i for i in landed if not any(i["path"].name == d[2] for d in duplicates)]
    return kept


# --------------------------------------------------------------------------
# PDF text, with positions
# --------------------------------------------------------------------------

def shift_text(text: str, offset: int) -> str:
    """Shift every character code by a fixed offset.

    The range matters. Guarding on `32 < code` looks safe and silently skips
    the digits: in these subset fonts the numerals sit below 32, so letters
    decoded and every number in the file came out as control characters. The
    guard is on the RESULT being printable, not on the input.
    """
    out = []
    for ch in text:
        shifted = ord(ch) + offset
        out.append(chr(shifted) if 32 <= shifted < 127 else ch)
    return "".join(out)


def _decode_string(part: str) -> str:
    """One PDF string literal or hex string, as text."""
    if part.startswith("("):
        return re.sub(r"\\([nrtbf()\\])",
                      lambda m: {"n": "\n", "r": "\r", "t": "\t",
                                 "b": "\b", "f": "\f"}.get(m.group(1), m.group(1)),
                      part[1:-1])
    hexed = re.sub(r"\s", "", part[1:-1])
    if len(hexed) % 2:
        hexed += "0"
    raw = bytes.fromhex(hexed)
    # A two-byte CID font's codes arrive as 00xx; a single-byte font's do not.
    if raw and len(raw) % 2 == 0 and raw[0::2].count(0) > len(raw) // 4:
        return raw.decode("utf-16-be", errors="replace")
    return raw.decode("latin-1")


_NUM = r"-?\d*\.?\d+"
_TOKEN = re.compile(
    rf"BT\b"
    rf"|({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+Tm\b"
    rf"|({_NUM})\s+({_NUM})\s+(TD|Td)\b"
    rf"|({_NUM})\s+TL\b"
    rf"|T\*"
    rf"|/[^\s/]+\s+({_NUM})\s+Tf\b"
    rf"|\[(.*?)\]\s*TJ"
    rf"|\(((?:[^()\\]|\\.)*)\)\s*Tj"
    rf"|<([0-9A-Fa-f\s]*)>\s*Tj", re.S)

_PIECE = re.compile(r"\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>|-?\d*\.?\d+")


def _page_runs(body: str, state: dict | None = None) -> list[tuple]:
    """Every show operation on one page, with its text matrix and segments.

    A show operation is returned as (a, b, c, d, e, f, size, segments), where
    segments splits the text at the array's own kerning adjustments:
    [[kern_before, text], ...]. Those adjustments are what separate the columns
    in the 2003-2012 vintages, and they are exact - unlike a position estimate,
    which needs the font's glyph widths to be right.
    """
    if state is None:
        state = {}
    la, lb, lc, ld, le, lf = state.get("line", (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    a, b, c, d, e, f = state.get("text", (la, lb, lc, ld, le, lf))
    leading = state.get("leading", 0.0)
    size = state.get("size", 1.0)
    runs: list[tuple] = []

    def move(tx: float, ty: float) -> None:
        nonlocal le, lf, a, b, c, d, e, f
        le, lf = tx * la + ty * lc + le, tx * lb + ty * ld + lf
        a, b, c, d, e, f = la, lb, lc, ld, le, lf

    for token in _TOKEN.finditer(body):
        text = token.group(0)
        if text.startswith("BT"):
            la, lb, lc, ld, le, lf = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
            a, b, c, d, e, f = la, lb, lc, ld, le, lf
        elif token.group(1) is not None:
            la, lb, lc, ld, le, lf = (float(token.group(i)) for i in range(1, 7))
            a, b, c, d, e, f = la, lb, lc, ld, le, lf
        elif token.group(7) is not None:
            tx, ty = float(token.group(7)), float(token.group(8))
            if token.group(9) == "TD":
                leading = -ty
            move(tx, ty)
        elif token.group(10) is not None:
            leading = float(token.group(10))
        elif text.startswith("T*"):
            move(0.0, -leading)
        elif token.group(11) is not None:
            size = float(token.group(11))
        elif token.group(12) is not None:
            segments, kern = [], 0.0
            for piece in _PIECE.finditer(token.group(12)):
                raw = piece.group(0)
                if raw[0] in "(<":
                    segments.append([kern, _decode_string(raw)])
                    kern = 0.0
                else:
                    kern -= float(raw)
            if segments:
                runs.append((a, b, c, d, e, f, size, segments))
        elif token.group(13) is not None:
            runs.append((a, b, c, d, e, f, size,
                         [[0.0, _decode_string("(" + token.group(13) + ")")]]))
        elif token.group(14) is not None:
            runs.append((a, b, c, d, e, f, size,
                         [[0.0, _decode_string("<" + token.group(14) + ">")]]))
    state["line"] = (la, lb, lc, ld, le, lf)
    state["text"] = (a, b, c, d, e, f)
    state["leading"], state["size"] = leading, size
    return runs


CONTINUATION = re.compile(r"\bBT\b|\bTJ\b|\bTj\b")


def _document_runs(bodies: list[str]) -> list[tuple]:
    """Every show operation in the document, in one coordinate space, by page.

    Returns (page, line, along, unit, segments) per operation. `line` is the
    axis rows advance along and `along` the axis text advances along, which
    swap when the text matrix is a quarter turn - as it is in every ratio
    report from 2006 on, where reading the matrix translation as (x, y) groups
    the table by column instead of by row.

    A page's content is often several stream objects, and a later one begins
    inside a text object with no BT and no Tm, only the moves that continue the
    previous stream. So the text state carries across streams, and a stream
    counts as a new page only when it opens a text object before it draws
    anything: whether the first of BT, Tj and TJ to appear is BT.

    Counting every stream as a page loses the continuations. Counting none of
    them merges pages, and because each page's table starts at the same
    coordinate, that puts a hundred unrelated rows on one line - which is how
    the 2009 file came out with Ortega Middle School twice, once with 29.7
    teachers and once with 2.
    """
    state: dict = {}
    runs, page_no = [], 0
    for body in bodies:
        opening = CONTINUATION.search(body)
        if opening is None or opening.group(0) == "BT":
            page_no += 1
        for a, b, c, d, e, f, size, segments in _page_runs(body, state):
            rotated = abs(b) > abs(a)
            unit = math.hypot(a, b) * size or 1.0
            line, along = (e, f) if rotated else (f, e)
            runs.append((page_no, line, along, unit, segments))
    return runs


def pdf_rows(path: Path) -> tuple[list[list[str]], int | None]:
    """Extract a PDF's text as rows of fields, from the text matrices.

    Three things about these files defeated a simpler reading, and each one
    failed silently rather than raising:

      - **The page is rotated.** From 2006 the ratio reports set a text matrix
        of `0 s -s 0 x y`, which turns the page ninety degrees: the along-line
        axis is the page's y and the line axis is its x. Reading the matrix's
        translation as (x, y) therefore groups by *column* instead of by row,
        and every row of the table comes out interleaved with every other.
      - **The line operator is `TD`, not `Td`.** Matching only `Td` left the
        position frozen wherever the last `Tm` put it, so a whole page of text
        landed on one line. That is why 2005-2012 extracted 78 to 1,348 "rows"
        of run-together text and parsed to nothing at all.
      - **A cell that overflows is drawn in two pieces**, the overflow inside a
        clip region at its own matrix, so "SKYVIEW ACADEMY HIGH SCHOOL" arrives
        as "SKYVIEW ACADEMY HIGH SCHOO" and "L", and "265" as "2" and "65".
        Those have to be joined back, which means knowing where one show
        operation ends - and that needs a glyph width.

    So the fields come from two signals. Inside a show operation the kerning
    adjustments are exact and large where a column ends. Between operations the
    file decides which regime it is in: measure the implied glyph width of
    every adjacent pair, and if the low end of that distribution sits at a
    plausible width (about 0.6 em) the operations abut and are joined; if it
    sits well above one (1.0 em and up) each operation is its own cell and
    stands alone.
    """
    data = path.read_bytes()
    bodies = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        try:
            body = zlib.decompress(data[start:end]).decode("latin-1")
        except Exception:  # noqa: BLE001
            continue
        if "Tj" in body or "TJ" in body:
            bodies.append(body)
    if not bodies:
        return [], None

    # One page's content is often several stream objects, and the later ones
    # begin in the middle of a text object - no BT, no Tm, only the moves that
    # continue the previous stream. Resetting per stream put those runs in an
    # identity matrix while the rest of the page was rotated, which scattered
    # about a tenth of the rows of every 2006-2012 volume into fragments with
    # no numbers on them. The state carries across streams for that reason.
    placed = [(page, round(line, 1), along, unit, segments)
              for page, line, along, unit, segments in _document_runs(bodies)]
    if not placed:
        return [], None

    sample = "".join(t for row in placed[:400] for _, t in row[4])
    offset = 0
    if not HEADER_WORDS.search(re.sub(r"\s+", "", sample)):
        for candidate in range(-40, 41):
            if candidate and HEADER_WORDS.search(
                    re.sub(r"\s+", "", shift_text(sample, candidate))):
                offset = candidate
                break

    by_line: dict[tuple[int, float], list[tuple]] = defaultdict(list)
    order: dict[tuple[int, float], int] = {}
    for index, (page, line, along, unit, segments) in enumerate(placed):
        key = (page, line)
        by_line[key].append((along, unit, segments))
        order.setdefault(key, index)

    # Which regime? For each adjacent pair on a line, the implied glyph width
    # is the distance between them, less the kerning already accounted for,
    # divided by the characters drawn. Where operations abut this is a real
    # glyph width and the low percentile is tight; where each is its own cell
    # the gaps inflate it past any width a font actually has.
    implied, long_runs = [], []
    for ops in by_line.values():
        ops = sorted(ops)
        for (x0, unit0, segs0), (x1, *_rest) in zip(ops, ops[1:]):
            chars = sum(len(t) for _, t in segs0)
            kerns = sum(k for k, _ in segs0) / 1000.0 * unit0
            if chars and unit0:
                width = (x1 - x0 - kerns) / chars / unit0
                if 0.05 < width < 40:
                    implied.append(width)
                    if chars >= 20:
                        long_runs.append(width)
    implied.sort()
    long_runs.sort()
    floor = implied[len(implied) // 10] if implied else 1.0
    flowing = floor < 0.8 and bool(long_runs)
    em = long_runs[len(long_runs) // 2] if flowing else 0.0

    rows: list[list[str]] = []
    # Rows come back in the order the file draws them, which needs no guess
    # about which way the page runs.
    for key in sorted(by_line, key=lambda k: order[k]):
        fields, current, cursor, drift_chars = [], "", None, 0
        for along, unit, segments in sorted(by_line[key]):
            if not flowing:
                # Each operation is a cell. Its own kerning may still split it.
                for index, (kern, text) in enumerate(segments):
                    text = shift_text(text, offset) if offset else text
                    if current and (index == 0 or kern / 1000.0 * unit > 0.55 * unit):
                        if current.strip():
                            fields.append(current.strip())
                        current = ""
                    current += text
                continue
            position = along
            for index, (kern, text) in enumerate(segments):
                gap = kern / 1000.0 * unit
                position += gap
                if index == 0 and cursor is not None:
                    # Between operations the estimate has drifted by whatever
                    # the average glyph width missed, so allow for it in
                    # proportion to the characters it was applied to.
                    gap = position - cursor
                    allowance = 0.55 * unit + 0.05 * unit * drift_chars
                else:
                    allowance = 0.55 * unit
                text = shift_text(text, offset) if offset else text
                if current and gap > allowance:
                    if current.strip():
                        fields.append(current.strip())
                    current = ""
                current += text
                position += em * unit * len(text)
            cursor = position
            drift_chars = sum(len(t) for _, t in segments)
        if current.strip():
            fields.append(current.strip())
        if fields:
            rows.append(fields)
    return rows, offset


def read_sheet_rows(path: Path) -> list[list[str]]:
    import pandas as pd  # noqa: PLC0415

    frame = pd.read_excel(path, header=None, dtype=object)
    return [["" if v is None or (isinstance(v, float) and v != v) else str(v).strip()
             for v in row] for row in frame.values.tolist()]


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

CODE = re.compile(r"^\d{2,4}$")
NUMBER = re.compile(r"^-?[\d,]+(?:\.\d+)?$")
# The trailing measures are scanned with a looser pattern than NUMBER, because
# two columns printed too close together arrive as one field with two decimal
# points in it - "34.517.2173913". Telling those apart is three_numbers's job;
# this only has to recognise that the field is made of printed figures.
FIGURES = re.compile(r"^\d[\d,. ]*$")
# A ratio is sometimes written "17:1" rather than 17.0.
RATIO_TEXT = re.compile(r"^(\d+(?:\.\d+)?)\s*:\s*1$")
# Aggregate rows again. This is the third distinct place one has turned up -
# the 2010 CDE enrollment file, the yearbooks, and now the teacher files, where
# 2019 carries an unnamed row of 53,458 FTE against 53,456 for every real
# school combined. It is always the same shape: no name, and a value equal to
# the sum of everything above it.
AGGREGATE_NAME = re.compile(
    r"\b(STATE|COUNTY|DISTRICT|GRAND|SCHOOL)\s+(TOTALS?|OVERALL|SUMMARY|WIDE)\b"
    r"|^(TOTALS?|STATEWIDE|ALL\s+DISTRICTS?|ALL\s+SCHOOLS?)$", re.I)
# The 2010 report prints a subtotal after each district's schools, named for
# the district with TOTALS* appended - "MAPLETON 1 TOTALS*". It is the only
# district-grain teacher FTE CDE published in the PDF era, so it is kept rather
# than discarded with the other aggregates, and the suffix is what identifies
# it: the row is a district's own total, stated by the file.
DISTRICT_SUBTOTAL = re.compile(r"^(?P<name>.+?)\s+TOTALS?\s*\*?$", re.I)
# "STATE TOTALS" also ends in TOTALS, and reading it as a district called
# "STATE" put the whole state into the 2018 file a second time - 105,460 FTE
# against 52,730 for every school in it. A subtotal's name has to be a name.
NOT_A_DISTRICT = re.compile(r"^(STATE|COUNTY|GRAND|SCHOOL|DISTRICT|ALL)$", re.I)


def _as_number(text: str) -> float | None:
    """A printed figure, or None if this is not one.

    Leading zeros are rejected on purpose. None of these tables print 034.5,
    so allowing it would only manufacture extra ways to cut a run of digits
    apart - and the whole point of the search below is that exactly one way
    should survive.
    """
    if not text or text.count(".") > 1:
        return None
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    whole = text.split(".")[0]
    if len(whole) > 1 and whole[0] == "0":
        return None
    return float(text)


def three_numbers(tokens: list[str]) -> tuple[float, float, float] | None:
    """Membership, teacher FTE and their ratio, out of the row's trailing text.

    These tables print three numbers whose relationship is fixed: membership
    divided by teacher FTE is the ratio in the last column. That is what makes
    them recoverable when the columns run together, which they do constantly -
    the space between two right-aligned figures is often narrower than a
    character, so "34.5" and "17.2173913" arrive as "34.517.2173913" and every
    row of the 2002 report came out unreadable.

    So every way of cutting the trailing text into three printed figures is
    tried, and a cut is accepted only if the first divided by the second equals
    the third to the precision the third is printed at. Where more than one cut
    survives, the one that keeps the most of the row's own field boundaries
    wins. Where none does, the row is dropped: this reconstructs what the file
    states about itself, and never guesses past it.
    """
    text = "".join(tokens)
    if not text or len(text) > 30:
        return None
    edges, position = set(), 0
    for token in tokens[:-1]:
        position += len(token)
        edges.add(position)

    best = None
    for i in range(1, len(text) - 1):
        left = _as_number(text[:i])
        if left is None or left <= 0:
            continue
        for j in range(i + 1, len(text)):
            middle = _as_number(text[i:j])
            right = _as_number(text[j:])
            if middle is None or right is None or middle <= 0 or right <= 0:
                continue
            if right > 200 or middle > 20000 or left > 200000:
                continue
            printed = text[j:]
            decimals = len(printed.split(".")[1]) if "." in printed else 0
            # CDE truncates the printed ratio rather than rounding it - 616
            # over 31.15 is 19.7753 and the file says 19.77 - so the window has
            # to be a whole unit of the last printed place, not half of one.
            # Two bounds, and the tighter one wins. CDE truncates the printed
            # ratio rather than rounding it - 616 over 31.15 is 19.7753 and
            # the file says 19.77 - so a whole unit of the last printed place
            # has to be allowed. But a ratio printed as "1" would then accept
            # almost any pair of numbers, which is how Hagen Early Education
            # Center came out of a clean row with 8,435 teachers. A relative
            # bound closes that.
            tolerance = min(1.05 * 10 ** -decimals, max(0.02, 0.05 * right))
            error = abs(left / middle - right)
            if error > tolerance:
                continue
            kept = len(edges & {i, j})
            candidate = (-kept, error, -left)
            if best is None or candidate < best[0]:
                best = (candidate, (left, middle, right))
    return best[1] if best else None


def parse_row(fields: list[str]) -> dict | None:
    """Read one row of a pupil/teacher-ratio table from its shape.

    Header mapping does not survive these vintages: the column titles are
    stacked across two or three lines that do not align with each other or
    with the data, so "COUNTY / DISTRICT / SCHOOL / TEACHER" sits above
    "CODE / NAME / CODE / CODE / FTE / RATIO" and neither row has one entry
    per column. The data rows, by contrast, have the same shape in every
    vintage:

        [county code] county name [district code] district name
        [school code] school name  enrollment  teacher FTE  ratio

    So the row is read from its own structure. The trailing numbers are the
    measures, and the number of four-digit codes before them says whether the
    row is a school or a district: two codes means district plus school, one
    means district alone.
    """
    if len(fields) < 4:
        return None

    fields = list(fields)
    # A trailing "17:1" is the ratio written as a ratio.
    if fields:
        ratio_match = RATIO_TEXT.match(fields[-1].replace(" ", ""))
        if ratio_match:
            fields[-1] = ratio_match.group(1)

    trailing: list[str] = []
    while (len(fields) > 1 and FIGURES.match(fields[-1].strip())
           and len(trailing) < 5):
        trailing.insert(0, fields.pop().replace(",", "").replace(" ", ""))
    if len(trailing) < 2:
        return None
    # A row whose own fields already read as three figures is taken at its
    # word, subject to the same 5% arithmetic check the archive has always
    # applied. Only when that fails is the row treated as run together and the
    # split searched for, and then on much tighter terms - so a clean row can
    # never be silently re-cut into a different set of numbers.
    measures = None
    if len(trailing) == 3:
        plain = [_as_number(value) for value in trailing]
        if all(v is not None for v in plain) and plain[1] and plain[2]:
            if abs(plain[0] / plain[1] - plain[2]) <= max(0.5, plain[2] * 0.05):
                measures = tuple(plain)
    if measures is None:
        measures = three_numbers(trailing)
    if measures is None:
        return None
    enrollment_value, teacher_fte, ratio = measures

    codes = [f.strip() for f in fields if CODE.match(f.strip())]
    # A leading two-digit code is the county, not a district. Counting it as
    # one turned every district row into a school row: 2013 came back with 185
    # "schools" carrying 2,977 FTE, which is the district table wearing the
    # wrong label. Colorado has 64 counties, so a two-digit first code that is
    # followed by a name is a county and is set aside before the grain is
    # decided.
    county_code = ""
    if codes and len(codes[0]) <= 2 and fields and fields[0].strip() == codes[0]:
        county_code = codes.pop(0)
    names = [f.strip() for f in fields
             if not CODE.match(f.strip()) and f.strip()
             and not re.fullmatch(r"\d{4}-\d{2,4}", f.strip())]
    subtotal = DISTRICT_SUBTOTAL.match(names[-1]) if names else None
    if subtotal and NOT_A_DISTRICT.match(subtotal.group("name").strip()):
        subtotal = None
    # An unnamed row in one of these tables is the state total, not a school.
    if not names or (any(AGGREGATE_NAME.search(n) for n in names) and not subtotal):
        return None

    enrollment = int(round(enrollment_value))

    # 2006 prints no codes at all - county name, district name, school name,
    # then the three measures - so the grain cannot come from counting codes.
    # Three names and no code is a school row whose identity has to be
    # recovered from the name; see resolve_by_name.
    if not codes and len(names) >= 3:
        return {
            "grain": "school",
            "county_code": "", "district_code": "", "school_code": "",
            "county_name": names[0],
            "district_name": names[-2],
            "school_name": names[-1],
            "enrollment_reported": enrollment,
            "teacher_fte": teacher_fte,
            "pupil_teacher_ratio": ratio,
        }

    grain = "school" if len(codes) >= 2 and not subtotal else "district"
    if grain == "school":
        district_name = names[-2] if len(names) >= 2 else ""
        school_name = names[-1]
    else:
        district_name = subtotal.group("name") if subtotal else names[-1]
        school_name = ""
    return {
        "grain": grain,
        "county_code": county_code,
        "district_code": normalize_code(codes[0]) if codes else "",
        "school_code": normalize_code(codes[1]) if len(codes) >= 2 else "",
        "county_name": names[0] if len(names) > (2 if grain == "school" else 1) else "",
        "district_name": district_name,
        "school_name": school_name,
        "enrollment_reported": enrollment,
        "teacher_fte": teacher_fte,
        "pupil_teacher_ratio": ratio,
    }


HEADER_MAP = [
    ("school_code", r"^(school|sch)\s*code"),
    # "LEA" on its own is the district code column in the 2023 and 2024
    # by-district spreadsheets. Requiring the word "code" left it unmatched, so
    # every district row in those files carried an empty code, collapsed onto
    # one key, and the whole of both years came out as a single row holding the
    # state total.
    ("district_code", r"^(lea|district|distr|organization|org)(\s*(code|id))?$"),
    ("district_code", r"^(lea|district|distr|organization|org)\s*code"),
    ("county_code", r"^county\s*code"),
    ("school_name", r"^(school|sch)\s*name"),
    ("district_name", r"^(lea|district|distr|organization|org)\s*name"),
    ("county_name", r"^county\s*name"),
    ("teacher_fte", r"teacher\s*fte"),
    ("enrollment_reported", r"enrollment|membership|pk-?12"),
    ("pupil_teacher_ratio", r"ratio"),
]


def parse_sheet(rows: list[list[str]], year: int, source: str) -> list[dict]:
    """Spreadsheets carry a clean single-row header, so use it.

    The shape rule that PDFs need is guesswork here, and guessing wrongly is
    what made 2024's unpadded codes ("10", "187") look like a county."""
    header_idx = next((i for i, r in enumerate(rows[:25])
                       if any(re.search(r"teacher\s*fte", str(c), re.I) for c in r)), None)
    if header_idx is None:
        return []
    header = [str(c).strip() for c in rows[header_idx]]
    columns: dict[str, int] = {}
    for key, pattern in HEADER_MAP:
        for j, name in enumerate(header):
            if key not in columns and re.search(pattern, name, re.I):
                columns[key] = j
    if "teacher_fte" not in columns:
        return []

    def cell(row, key):
        j = columns.get(key)
        return str(row[j]).strip() if j is not None and j < len(row) else ""

    out = []
    for row in rows[header_idx + 1:]:
        fte = parse_decimal(cell(row, "teacher_fte").replace(",", ""))
        if fte is None:
            continue
        names = [cell(row, k) for k in ("school_name", "district_name")]
        # The 2023 and 2024 by-district files end with an unnamed row carrying
        # the state total - 52,969.4 FTE in 2023, which is every district over
        # again. It has no name to match an aggregate pattern against, so the
        # absence of a name is what identifies it.
        if not any(n for n in names) or any(AGGREGATE_NAME.search(n) for n in names if n):
            continue
        school_code = normalize_code(cell(row, "school_code"))
        ratio = cell(row, "pupil_teacher_ratio").replace(" ", "")
        match = RATIO_TEXT.match(ratio)
        out.append({
            "year": year, "source": source,
            "grain": "school" if school_code.isdigit() else "district",
            "county_code": cell(row, "county_code"),
            "county_name": cell(row, "county_name"),
            "district_code": normalize_code(cell(row, "district_code")),
            "district_name": cell(row, "district_name"),
            "school_code": school_code,
            "school_name": cell(row, "school_name"),
            "teacher_fte": fte,
            "enrollment_reported": parse_count(cell(row, "enrollment_reported").replace(",", "")),
            "pupil_teacher_ratio": parse_decimal(match.group(1) if match else ratio),
        })
    return out


def parse_file(path: Path, year: int, label: str) -> tuple[list[dict], dict]:
    if path.suffix.lower() in (".xls", ".xlsx"):
        rows = read_sheet_rows(path)
        offset = 0
        records = parse_sheet(rows, year, path.name)
        if records:
            grains = {r["grain"] for r in records}
            return records, {
                "grain": "school" if grains == {"school"} else "district" if grains == {"district"} else "mixed",
                "font_offset": 0, "label": label, "records": len(records), "rows_skipped": 0,
                "school_rows": sum(1 for r in records if r["grain"] == "school"),
                "district_rows": sum(1 for r in records if r["grain"] == "district"),
                "total_fte": round(sum(r["teacher_fte"] for r in records), 1),
            }
    else:
        rows, offset = pdf_rows(path)
    if not rows:
        return [], {"error": "no text extracted"}

    records, skipped = [], 0
    for fields in rows:
        parsed = parse_row([str(f) for f in fields if str(f).strip()])
        if parsed is None:
            skipped += 1
            continue
        records.append({"year": year, "source": path.name, **parsed})

    grains = {r["grain"] for r in records}
    grain = ("school" if grains == {"school"} else
             "district" if grains == {"district"} else
             "mixed" if grains else "unknown")
    return records, {
        "grain": grain, "font_offset": offset, "label": label,
        "records": len(records), "rows_skipped": skipped,
        "school_rows": sum(1 for r in records if r["grain"] == "school"),
        "district_rows": sum(1 for r in records if r["grain"] == "district"),
        "total_fte": round(sum(r["teacher_fte"] for r in records), 1),
    }


# --------------------------------------------------------------------------
# NCES, both grains
# --------------------------------------------------------------------------

CCD_API = "https://educationdata.urban.org/api/v1"


def _fetch_json(url: str, tries: int = 4) -> dict:
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def ccd_district_fte(year: int, cache: Path) -> list[dict]:
    """District (LEA) teacher FTE from NCES, with its staff breakdown.

    This is the only source that covers every year at district grain, and it
    carries the split by level as well as the total, which CDE never publishes.
    """
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"ccd-lea-{year}.json"
    if not path.exists():
        rows, url = [], f"{CCD_API}/school-districts/ccd/directory/{year}/?fips=8"
        while url:
            page = _fetch_json(url)
            rows.extend(page["results"])
            url = page.get("next")
        path.write_text(json.dumps(rows))

    out = []
    for row in json.loads(path.read_text()):
        total = parse_decimal(row.get("teachers_total_fte"))
        if total is None:
            continue
        out.append({
            "year": year,
            "leaid": row.get("leaid") or "",
            "district_code": normalize_code(row.get("state_leaid") or ""),
            "district_name": (row.get("lea_name") or "").strip(),
            "teacher_fte": total,
            "teacher_fte_prek": parse_decimal(row.get("teachers_prek_fte")),
            "teacher_fte_kindergarten": parse_decimal(row.get("teachers_kindergarten_fte")),
            "teacher_fte_elementary": parse_decimal(row.get("teachers_elementary_fte")),
            "teacher_fte_secondary": parse_decimal(row.get("teachers_secondary_fte")),
            "staff_total_fte": parse_decimal(row.get("staff_total_fte")),
            "enrollment_reported": parse_count(row.get("enrollment")),
            "source": f"ccd-lea-{year}",
        })
    return out


NAME_NOISE = re.compile(r"[^A-Z0-9]+")


def name_key(text: str) -> str:
    return NAME_NOISE.sub(" ", (text or "").upper()).strip()


def keep_district_rows(records: list[dict]) -> tuple[list[dict], int]:
    """Drop rows that look like districts only because a code went missing.

    A school row whose school code merged into the name leaves one code behind,
    and one code is what marks a district row - so "HULSTROM OPTIONS K-8
    SCHOOL" arrived in the district table as a district. Every such row in the
    2016, 2018, 2019 and 2022 files was a school, and together with the state
    total they were the whole of CDE's district-grain teacher FTE: seventeen
    rows across nine years.

    A file that really does publish a district table - 2010 does, and the
    by-district spreadsheets from 2023 do - names the same district code and
    name in its school rows. That is the test, and it is the file's own
    evidence rather than a list maintained here.
    """
    districts: dict[str, set[str]] = defaultdict(set)
    for row in records:
        if row["grain"] == "school" and row["district_code"]:
            districts[row["district_code"]].add(name_key(row["district_name"]))
    # A file that publishes districts and nothing else has no school rows to
    # check against, and needs none: there is no school row for a missing code
    # to have come from.
    if not districts:
        return list(records), 0
    kept, dropped = [], 0
    for row in records:
        if row["grain"] != "district":
            kept.append(row)
            continue
        known = districts.get(row["district_code"])
        if known and name_key(row["district_name"]) in known:
            kept.append(row)
        else:
            dropped += 1
    return kept, dropped


def resolve_by_name(records: list[dict]) -> int:
    """Give the code-less 2006 rows their district and school codes back.

    2006 is the one year whose ratio report prints names and no codes at all.
    The names are the same ones the surrounding years print beside the codes,
    so the pairing is taken from the nearest year that has both. A name that
    matches more than one code pair, or none, is left unresolved rather than
    guessed at, and the count of each is reported.
    """
    index: dict[tuple[str, str], dict[int, set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set))
    for row in records:
        if row["grain"] == "school" and row["school_code"]:
            key = (name_key(row["district_name"]), name_key(row["school_name"]))
            index[key][row["year"]].add((row["district_code"], row["school_code"]))

    resolved = 0
    for row in records:
        if row["grain"] != "school" or row["school_code"]:
            continue
        key = (name_key(row["district_name"]), name_key(row["school_name"]))
        years = index.get(key)
        if not years:
            continue
        nearest = min(years, key=lambda y: (abs(y - row["year"]), y))
        codes = years[nearest]
        if len(codes) != 1:
            continue
        row["district_code"], row["school_code"] = next(iter(codes))
        resolved += 1
    return resolved


def main() -> None:
    print("Fetching every ratio and salary file the inventory names")
    landed = fetch_all()
    print(f"  {len(landed)} files on disk\n")

    school_records: dict[tuple, dict] = {}
    district_records: dict[tuple, dict] = {}
    report = {}

    parsed: list[dict] = []
    for item in sorted(landed, key=lambda r: (int(r["year"]), r["series"])):
        year = int(item["year"])
        records, meta = parse_file(item["path"], year, item["label"])
        records, dropped = keep_district_rows(records)
        meta["district_rows_dropped"] = dropped
        meta["district_rows"] = sum(1 for r in records if r["grain"] == "district")
        report[item["path"].name] = meta
        note = meta.get("error") or (
            f"{meta['grain']:8s} {meta['records']:>5,} rows  {meta['total_fte']:>10,.1f} FTE"
            + (f"  font{meta['font_offset']:+d}" if meta["font_offset"] else "")
            + (f"  -{dropped} false district" if dropped else ""))
        print(f"  {year} {item['series']:10s} {note}")
        parsed.extend(records)

    duplicates: dict[int, int] = defaultdict(int)
    resolved = resolve_by_name(parsed)
    if resolved:
        print(f"\n  {resolved:,} code-less rows matched to a school by name (2006)")

    # A year can be published in both serials, and the two files are not always
    # the same length. Rather than take whichever row was read last - which
    # mixes two files inside one year - the fuller file is the year's source,
    # and the other only fills in schools it does not carry.
    by_source: dict[tuple[int, str], dict[str, dict]] = defaultdict(dict)
    for record in parsed:
        if record["grain"] != "school" or not record["school_code"]:
            continue
        seen = by_source[(record["year"], record["source"])]
        previous = seen.get(record["school_code"])
        # Within one file a school can still be listed twice with different
        # staff - 2009 does it 84 times, and both readings satisfy the file's
        # own arithmetic, so the arithmetic cannot choose between them. Ortega
        # Middle School is printed with 459 pupils against 29.7 teachers and
        # again against 2, and 459 over 2 really is the 229.5 that row prints.
        # The fuller staffing is kept and the rest counted: taking the last
        # instead cost 2009 about 1,800 FTE, moving it from 2% below NCES to 5%.
        if previous is None or record["teacher_fte"] > previous["teacher_fte"]:
            seen[record["school_code"]] = record
            if previous is not None:
                duplicates[record["year"]] += 1
        else:
            duplicates[record["year"]] += 1

    filled = 0
    for year in sorted({key[0] for key in by_source}):
        files = sorted((key for key in by_source if key[0] == year),
                       key=lambda key: -len(by_source[key]))
        for rank, key in enumerate(files):
            for code, record in by_source[key].items():
                if (year, code) in school_records:
                    continue
                school_records[(year, code)] = record
                if rank:
                    filled += 1
    if filled:
        print(f"  {filled:,} schools taken from a year's second published file")

    # A district-grain publication covers the state, not one district. Where a
    # year leaves only a handful of district rows standing, they are not a
    # district table - they are school rows that lost a code and happened to
    # match a real district's name. 2006 kept exactly one, carrying 9 FTE, and
    # 2022 one carrying 13.4; both would have read as a district's whole
    # teaching staff.
    by_year: dict[int, list[dict]] = defaultdict(list)
    for record in parsed:
        if record["grain"] == "district":
            by_year[record["year"]].append(record)
    districts_in_year = {year: len({r["district_code"] for r in rows
                                    if r["grain"] == "school" and r["district_code"]})
                         for year, rows in
                         [(y, [r for r in parsed if r["year"] == y]) for y in by_year]}
    for year, rows in sorted(by_year.items()):
        expected = districts_in_year.get(year) or 0
        if expected and len(rows) < expected / 2:
            print(f"  {year}: {len(rows)} district rows against {expected} districts "
                  f"- not a district table, dropped")
            continue
        for record in rows:
            key = (record["year"], record["district_code"])
            if key not in district_records or record["enrollment_reported"]:
                district_records[key] = record

    PROCESSED.mkdir(parents=True, exist_ok=True)
    school_rows = sorted(school_records.values(),
                         key=lambda r: (r["year"], r["district_code"], r["school_code"]))
    columns = ["year", "district_code", "district_name", "school_code", "school_name",
               "county_name", "teacher_fte", "enrollment_reported",
               "pupil_teacher_ratio", "source"]
    with (PROCESSED / "school-teacher-fte.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(school_rows)
    years = sorted({r["year"] for r in school_rows})
    print(f"\nwrote data/processed/school-teacher-fte.csv: {len(school_rows):,} rows, "
          f"{years[0]}-{years[-1]}")

    # ---- CDE district tier ----------------------------------------------
    #
    # CDE publishes district-grain teacher FTE in three places only: the 2010
    # report's per-district subtotals, and the by-district spreadsheets for
    # 2023 and 2024. Everywhere else the district total is the sum of the
    # schools, which is how this archive already builds district enrollment.
    #
    # Both are carried, in their own columns, and neither is substituted for
    # the other - the same rule the school panel follows with CDE and NCES. In
    # 2010, 2023 and 2024 the two can be compared, and `teacher_fte_difference`
    # is that comparison rather than a claim.
    summed: dict[tuple, dict] = {}
    for row in school_rows:
        if not row["district_code"]:
            continue
        key = (row["year"], row["district_code"])
        entry = summed.setdefault(key, {
            "year": row["year"], "district_code": row["district_code"],
            "district_name": row["district_name"], "county_name": row["county_name"],
            "schools": 0, "teacher_fte_school_sum": 0.0, "enrollment_school_sum": 0,
        })
        entry["schools"] += 1
        entry["teacher_fte_school_sum"] += row["teacher_fte"]
        entry["enrollment_school_sum"] += row["enrollment_reported"] or 0

    district_rows = []
    for key in sorted(set(summed) | set(district_records)):
        total = summed.get(key, {})
        published = district_records.get(key, {})
        school_sum = round(total["teacher_fte_school_sum"], 4) if total else None
        stated = published.get("teacher_fte")
        sources = []
        if stated is not None:
            sources.append(published["source"])
        if school_sum is not None:
            sources.append("cde-school-sum")
        district_rows.append({
            "year": key[0],
            "district_code": key[1],
            "district_name": published.get("district_name") or total.get("district_name", ""),
            "county_name": total.get("county_name") or published.get("county_name", ""),
            "teacher_fte_published": stated if stated is not None else "",
            "teacher_fte_school_sum": school_sum if school_sum is not None else "",
            "teacher_fte_difference": (round(stated - school_sum, 4)
                                       if stated is not None and school_sum is not None else ""),
            "schools": total.get("schools", ""),
            "enrollment_published": published.get("enrollment_reported") or "",
            "enrollment_school_sum": total.get("enrollment_school_sum", ""),
            "source": "+".join(sources),
        })
    columns = ["year", "district_code", "district_name", "county_name",
               "teacher_fte_published", "teacher_fte_school_sum", "teacher_fte_difference",
               "schools", "enrollment_published", "enrollment_school_sum", "source"]
    with (PROCESSED / "district-teacher-fte-cde.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(district_rows)
    years = sorted({r["year"] for r in district_rows})
    both = [r for r in district_rows if r["teacher_fte_difference"] != ""]
    agree = sum(1 for r in both if abs(r["teacher_fte_difference"]) < 0.005)
    print(f"wrote data/processed/district-teacher-fte-cde.csv: {len(district_rows):,} rows, "
          f"{years[0]}-{years[-1]}")
    if both:
        print(f"  {len(both):,} district-years carry both a published total and a school sum; "
              f"{agree:,} agree exactly ({agree / len(both):.1%})")
    if duplicates:
        print("  second readings of a school in the same year, not used: "
              + ", ".join(f"{year} ({count})" for year, count in sorted(duplicates.items())))
    report["_second_readings"] = dict(sorted(duplicates.items()))
    report["_district_comparison"] = {
        "district_years_with_both": len(both),
        "exact_agreement": agree,
        "published_years": sorted({r["year"] for r in both}),
    }

    # ---- NCES district tier ---------------------------------------------
    print("\nNCES district teacher FTE")
    ccd_cache = HERE / "data" / "raw" / "ccd"
    lea_rows = []
    for year in range(1986, 2025):
        try:
            rows = ccd_district_fte(year, ccd_cache)
        except Exception as exc:  # noqa: BLE001
            print(f"  {year}: unavailable ({exc})")
            continue
        lea_rows.extend(rows)
        if year % 5 == 0 or year > 2021:
            print(f"  {year}: {len(rows):,} districts, {sum(r['teacher_fte'] for r in rows):,.0f} FTE")

    columns = ["year", "leaid", "district_code", "district_name", "teacher_fte",
               "teacher_fte_prek", "teacher_fte_kindergarten", "teacher_fte_elementary",
               "teacher_fte_secondary", "staff_total_fte", "enrollment_reported", "source"]
    with (PROCESSED / "district-teacher-fte-ccd.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(lea_rows, key=lambda r: (r["year"], r["district_name"])))
    years = sorted({r["year"] for r in lea_rows})
    print(f"\nwrote data/processed/district-teacher-fte-ccd.csv: {len(lea_rows):,} rows, "
          f"{years[0]}-{years[-1]}")

    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT / "teacher-fte-parse.json").write_text(json.dumps(report, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
