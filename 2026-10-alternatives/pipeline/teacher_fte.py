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
        try:
            data = fetch(row["url"], dest)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {name}: {exc}")
            continue
        manifest[name] = {
            "url": row["url"], "label": row["label"], "series": row["series"],
            "year": int(row["year"]), "format": row["fmt"],
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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


def pdf_rows(path: Path) -> tuple[list[list[str]], int | None]:
    """Extract a PDF's text as rows of fields, using text positions.

    Each Tm/Td operator places a run of text at an (x, y). Runs sharing a y
    are one row; a gap in x starts a new field. This is what makes the
    kerning-split text readable: "1 , 2 3 4 . 5" is one field because its
    characters are adjacent, while the next column is separated by a gap.
    """
    data = path.read_bytes()
    # (page, y, x, text). Page must be part of the key: every page repeats the
    # column header at the same y, so grouping on y alone across the whole
    # document concatenates all 52 copies of it into one unusable row.
    placed: list[tuple[int, float, float, str]] = []
    page_no = 0

    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        try:
            body = zlib.decompress(data[start:end]).decode("latin-1")
        except Exception:  # noqa: BLE001
            continue
        if "Tj" not in body and "TJ" not in body:
            continue
        page_no += 1

        # Text position comes from Td (relative move) and Tm (absolute matrix,
        # whose last two numbers are x and y). Everything drawn at the same y
        # is one row of the table.
        num = r"-?\d*\.?\d+"
        pattern = re.compile(
            rf"(?P<td>{num})\s+({num})\s+Td|"
            rf"(?P<tm>{num})\s+{num}\s+{num}\s+{num}\s+({num})\s+({num})\s+Tm|"
            r"\[(?P<tj>.*?)\]\s*TJ|"
            r"\((?P<s>(?:[^()\\]|\\.)*)\)\s*Tj", re.S)

        x = y = 0.0
        for token in pattern.finditer(body):
            if token.group("td") is not None:
                x += float(token.group("td")); y += float(token.group(2))
            elif token.group("tm") is not None:
                x, y = float(token.group(4)), float(token.group(5))
            elif token.group("tj") is not None:
                parts = re.findall(r"\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f]+>", token.group("tj"))
                text = "".join(
                    p[1:-1] if p.startswith("(") else
                    bytes.fromhex(p[1:-1]).decode("utf-16-be", errors="replace")
                    for p in parts)
                if text.strip():
                    placed.append((page_no, round(y, 1), x, text))
            elif token.group("s") is not None and token.group("s").strip():
                placed.append((page_no, round(y, 1), x, token.group("s")))

    if not placed:
        return [], None

    # Work out the font offset once, from all the text on the first page.
    sample = "".join(t for _, _, _, t in placed[:400])
    offset = 0
    if not HEADER_WORDS.search(re.sub(r"\s+", "", sample)):
        for candidate in range(-40, 41):
            if candidate and HEADER_WORDS.search(
                    re.sub(r"\s+", "", shift_text(sample, candidate))):
                offset = candidate
                break

    rows: list[list[str]] = []
    by_line: dict[tuple[int, float], list[tuple[float, str]]] = defaultdict(list)
    for page, y, x, text in placed:
        by_line[(page, y)].append((x, shift_text(text, offset) if offset else text))

    # Down each page in turn: page ascending, y descending.
    #
    # How a line splits into fields depends on how the PDF was written, and
    # these vintages differ. The 2016-2019 files place each cell as one run,
    # so a run is a field and nothing needs joining. The 2005-2012 files place
    # each CHARACTER as its own run, so "Mapleton" arrives as eight runs and
    # the field has to be rebuilt from the gaps between them.
    #
    # Guessing wrong in either direction is silent: merge a whole-run line and
    # "01 | ADAMS | 0010 | Mapleton 1" becomes one field; split a
    # character-run line and every word shatters. So each line is measured
    # first - if its runs are mostly one or two characters long, it is
    # character-placed and gets joined on gaps; otherwise each run stands.
    for page, y in sorted(by_line, key=lambda k: (k[0], -k[1])):
        runs = sorted(by_line[(page, y)])
        if not runs:
            continue

        lengths = sorted(len(t) for _, t in runs)
        character_placed = lengths[len(lengths) // 2] <= 2

        if not character_placed:
            fields = [t.strip() for _, t in runs if t.strip()]
        else:
            steps = [b[0] - a[0] for a, b in zip(runs, runs[1:]) if b[0] - a[0] > 0]
            ordered = sorted(steps)
            median = ordered[len(ordered) // 2] if ordered else 2.0
            threshold = max(median * 2.5, 3.0)
            fields, current, previous_x = [], "", None
            for x, text in runs:
                if previous_x is not None and x - previous_x > threshold:
                    if current.strip():
                        fields.append(current.strip())
                    current = ""
                current += text
                previous_x = x
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
    while fields and NUMBER.match(fields[-1].replace(" ", "")) and len(trailing) < 3:
        trailing.insert(0, fields.pop().replace(",", "").replace(" ", ""))
    if len(trailing) < 2:
        return None

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
    # An unnamed row in one of these tables is the state total, not a school.
    if not names or any(AGGREGATE_NAME.search(n) for n in names):
        return None

    ratio = parse_decimal(trailing[-1])
    teacher_fte = parse_decimal(trailing[-2])
    enrollment = parse_count(trailing[-3]) if len(trailing) == 3 else None
    if teacher_fte is None:
        return None

    # These tables print enrollment, FTE and the ratio between them, so the row
    # can check itself: enrollment / FTE should equal the printed ratio.
    #
    # This matters because a long school name wraps onto a second line and
    # splits the row, leaving only two trailing numbers - and then enrollment
    # is read as the FTE. Douglas County High School came out with 1,893
    # teachers, and three years inflated by about 31% while every individual
    # row still looked like a plausible number.
    if enrollment is not None and ratio and teacher_fte > 0:
        implied = enrollment / teacher_fte
        if abs(implied - ratio) > max(0.5, ratio * 0.05):
            return None
    elif enrollment is None and ratio and teacher_fte > 0:
        # Two numbers only: cannot tell FTE from enrollment. Reject rather
        # than guess, and let the year's coverage show the loss.
        return None

    grain = "school" if len(codes) >= 2 else "district"
    if grain == "school":
        district_name = names[-2] if len(names) >= 2 else ""
        school_name = names[-1]
    else:
        district_name = names[-1]
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
        if any(AGGREGATE_NAME.search(n) for n in names if n):
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


def main() -> None:
    print("Fetching every ratio and salary file the inventory names")
    landed = fetch_all()
    print(f"  {len(landed)} files on disk\n")

    school_records: dict[tuple, dict] = {}
    district_records: dict[tuple, dict] = {}
    report = {}

    for item in sorted(landed, key=lambda r: (int(r["year"]), r["series"])):
        year = int(item["year"])
        records, meta = parse_file(item["path"], year, item["label"])
        report[item["path"].name] = meta
        note = meta.get("error") or (
            f"{meta['grain']:8s} {meta['records']:>5,} rows  {meta['total_fte']:>10,.1f} FTE"
            + (f"  font{meta['font_offset']:+d}" if meta["font_offset"] else ""))
        print(f"  {year} {item['series']:10s} {note}")

        for record in records:
            if record["grain"] == "school":
                key = (record["year"], record["school_code"])
                # A year published in both serials: keep the fuller reading.
                if key not in school_records or record["enrollment_reported"]:
                    school_records[key] = record
            else:
                key = (record["year"], record["district_code"])
                if key not in district_records or record["enrollment_reported"]:
                    district_records[key] = record

    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, store, extra in (
        ("school-teacher-fte.csv", school_records,
         ["year", "district_code", "district_name", "school_code", "school_name",
          "county_name", "teacher_fte", "enrollment_reported", "pupil_teacher_ratio", "source"]),
        ("district-teacher-fte-cde.csv", district_records,
         ["year", "district_code", "district_name", "county_name",
          "teacher_fte", "enrollment_reported", "pupil_teacher_ratio", "source"]),
    ):
        rows = sorted(store.values(), key=lambda r: (r["year"], r["district_code"], r["school_code"]))
        with (PROCESSED / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=extra, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        years = sorted({r["year"] for r in rows})
        print(f"\nwrote data/processed/{name}: {len(rows):,} rows, "
              f"{years[0] if years else '-'}-{years[-1] if years else '-'}")

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
