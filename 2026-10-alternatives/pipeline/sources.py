"""Discover every published CDE file, across both eras and both series.

Phase A of TASK.md. Nothing is parsed here; the job is to know what exists
before a parser assumes anything. The output is data/lookups/inventory.csv,
one row per published file.

Two site shapes, and each has a trap the audit caught:

  Artemis (spl.cde.state.co.us) puts the <a> element BEFORE the text that
  names the report. A scraper reading the nearest preceding text fetches the
  wrong file - proof-run.py did exactly that and pulled "count of teachers by
  district" as the 2013 pupil-teacher ratio. Labels are read forward.

  The current CDE site (ed.cde.state.co.us) is Finalsite, which hides the real
  filename in a data-file-name attribute and serves it from a UUID path. The
  filename is the only place the year and grain are reliably stated.

Run:  python3 -m pipeline.sources
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LOOKUPS = HERE / "data" / "lookups"

ARTEMIS = "https://spl.cde.state.co.us/artemis/edserials"
MEMBERSHIP_SERIAL = f"{ARTEMIS}/ed59017internet"
YEARBOOK_SERIAL = f"{ARTEMIS}/ed27919internet"
STAFF_SERIAL = f"{ARTEMIS}/ed288internet"
CDE_HOST = "https://ed.cde.state.co.us"
MEMBERSHIP_ARCHIVE = f"{CDE_HOST}/cdereval/pupilmembership-statistics/data-insights-resources-archives"
STAFF_ARCHIVE = f"{CDE_HOST}/cdereval/staffstatistics/data-insights-resources-archives"

USER_AGENT = "charting-boulder/pipeline (+https://github.com/brianckeegan/charting-boulder)"

# What each row is classified as. The column that matters downstream is
# `measure` plus `grain`; everything else is kept so the inventory can answer
# questions the pipeline has not thought to ask yet.
MEMBERSHIP_BY_SCHOOL = re.compile(
    r"membership.*grade.*by school|by school and grade|grade level by school", re.I)
MEMBERSHIP_BY_DISTRICT = re.compile(
    r"membership.*grade.*(by (lea|district)|district and grade)|grade level membership by lea", re.I)
TEACHER_BY_SCHOOL = re.compile(r"(pupil|student)[-/ ]?teacher.*(ratio|fte).*school|ratio by school", re.I)
TEACHER_BY_DISTRICT = re.compile(r"(pupil|student)[-/ ]?teacher.*(ratio|fte)|average teacher salary", re.I)
EXCLUDE = re.compile(r"non-?public|home[- ]based|home study|data request|release memo|ranking", re.I)


@dataclass
class Item:
    series: str        # membership | staff | yearbook
    year: int
    label: str
    url: str
    fmt: str           # xlsx | xls | pdf
    measure: str       # enrollment | teacher_fte | other
    grain: str         # school | district | unknown
    filename: str


INDEX_CACHE = HERE / "data" / "raw" / "indexes"


def get(url: str, tries: int = 4) -> str:
    """Fetch an index page, cached to disk.

    The Artemis host is slow and drops connections under load - the proxy
    logged eight mid-exchange closes during one discovery run. Caching makes a
    re-run free, which matters because discovery touches 46 index pages and a
    single failure should not cost the whole sweep.
    """
    INDEX_CACHE.mkdir(parents=True, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url.replace("https://", ""))[:150] + ".html"
    cached = INDEX_CACHE / key
    if cached.exists() and cached.stat().st_size > 200:
        return cached.read_text(encoding="utf-8", errors="replace")

    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode("utf-8", "replace")
            cached.write_text(body, encoding="utf-8")
            return body
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def classify(label: str, filename: str) -> tuple[str, str]:
    text = f"{label} {filename}"
    if EXCLUDE.search(text):
        return "other", "unknown"
    if MEMBERSHIP_BY_SCHOOL.search(text):
        return "enrollment", "school"
    if MEMBERSHIP_BY_DISTRICT.search(text):
        return "enrollment", "district"
    if TEACHER_BY_SCHOOL.search(text):
        return "teacher_fte", "school"
    if TEACHER_BY_DISTRICT.search(text):
        return "teacher_fte", "district"
    return "other", "unknown"


# An anchor whose own text is just a format word is a download link, not a
# label; the report's name is then the nearest text before it.
FORMAT_WORD = re.compile(r"^\s*\(?\s*(ms\s*)?(excel|word|pdf|xlsx?|csv|html?)\s*\)?\s*$", re.I)
FURNITURE = re.compile(r"Questions\?|Broken Links|Accessibility|Contact us|stateinfo", re.I)


def artemis_year(series_url: str, year: int, series: str) -> list[Item]:
    """Read one Artemis year index.

    The two series disagree about where a report's name sits relative to its
    link, and assuming either one alone mislabels half the archive:

      staff pages       <a href="...pdf">Pupil-teacher ratios by school</a>
      membership pages  Pupil Membership by School and Grade Level
                        <a href="...pdf">PDF</a> <a href="...xls">MS Excel</a>

    So the label is whichever side is not a format word. Getting this wrong is
    not a cosmetic problem: proof-run.py fetched "count of teachers by
    district" believing it was the 2013 pupil-teacher ratio, and a classifier
    reading only anchor text leaves every membership year unlabelled.
    """
    page = None
    for suffix in ("index.html", "index.htm"):
        try:
            page = get(f"{series_url}/{year}/{suffix}")
            break
        except Exception:  # noqa: BLE001
            continue
    if page is None:
        return []

    flat = re.sub(r"\s+", " ", page)
    # Walk the document as an ordered stream of text and anchors.
    tokens = re.split(r'(<a\s[^>]*href="[^"]+"[^>]*>.*?</a>)', flat, flags=re.I | re.S)

    items: list[Item] = []
    last_text = ""
    for token in tokens:
        anchor = re.match(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', token or "", re.I | re.S)
        if not anchor:
            text = html.unescape(re.sub(r"<[^>]+>", " ", token or ""))
            text = re.sub(r"\s+", " ", text).strip()
            if text and not FURNITURE.search(text) and len(text) > 3:
                last_text = text
            continue

        href, inner_raw = anchor.groups()
        if not re.search(r"\.(xlsx|xls|pdf)$", href, re.I):
            continue
        inner = html.unescape(re.sub(r"<[^>]+>", " ", inner_raw))
        inner = re.sub(r"\s+", " ", inner).strip()

        if inner and not FORMAT_WORD.match(inner):
            label = inner              # staff layout: the anchor names the report
        else:
            label = last_text          # membership layout: the text before it does

        url = href if href.startswith("http") else f"{series_url}/{year}/{href}"
        filename = url.rsplit("/", 1)[-1]
        measure, grain = classify(label, filename)
        items.append(Item(series, year, label[:160], url,
                          filename.rsplit(".", 1)[-1].lower(), measure, grain, filename))
    return items


def finalsite(archive_url: str, series: str) -> list[Item]:
    """Read a Finalsite archive page. The real filename lives in
    data-file-name; the href is a UUID."""
    page = get(archive_url)
    items: list[Item] = []
    pattern = r'<a data-file-name="([^"]+)" data-resource-uuid="[^"]+" href="([^"]+)">(.*?)</a>'
    for match in re.finditer(pattern, page, re.S):
        filename, href, raw_label = match.groups()
        label = html.unescape(re.sub(r"<[^>]+>", "", raw_label)).replace("\xa0", " ").strip()
        # The school year is stated in the filename far more reliably than in
        # the label: "2024-25_Membership_Grade_bySchool.xlsx".
        year_match = re.search(r"(19|20)(\d{2})[-_]?(\d{2})?", filename)
        if not year_match:
            continue
        year = int(year_match.group(0)[:4])
        measure, grain = classify(label, filename)
        items.append(Item(series, year, label[:160], f"{CDE_HOST}{href}",
                          filename.rsplit(".", 1)[-1].lower(), measure, grain, filename))
    return items


def yearbooks() -> list[Item]:
    """The scanned 1986-1999 volumes. One PDF per year, district grain only."""
    page = get(f"{YEARBOOK_SERIAL}/")
    items = []
    for match in re.finditer(r'href="(ed27919(\d{4})internet\.pdf)"', page, re.I):
        filename, year = match.group(1), int(match.group(2))
        items.append(Item("yearbook", year, f"Pupil membership and related information, Fall {year}",
                          f"{YEARBOOK_SERIAL}/{filename}", "pdf", "enrollment", "district", filename))
    return items


def discover() -> list[Item]:
    items: list[Item] = []

    print("Artemis membership series (ED5/90.17), 2000-2024")
    for year in range(2000, 2025):
        found = artemis_year(MEMBERSHIP_SERIAL, year, "membership")
        print(f"  {year}: {len(found)} files")
        items.extend(found)

    print("Artemis staff series (ED2.88), 1999-2019")
    for year in range(1999, 2020):
        found = artemis_year(STAFF_SERIAL, year, "staff")
        print(f"  {year}: {len(found)} files")
        items.extend(found)

    print("Current CDE archive pages")
    for url, series in ((MEMBERSHIP_ARCHIVE, "membership"), (STAFF_ARCHIVE, "staff")):
        found = finalsite(url, series)
        print(f"  {series}: {len(found)} files")
        items.extend(found)

    print("Yearbooks (ED2/79.19), 1986-1999")
    found = yearbooks()
    print(f"  {len(found)} volumes")
    items.extend(found)

    return items


def main() -> None:
    LOOKUPS.mkdir(parents=True, exist_ok=True)
    items = discover()

    out = LOOKUPS / "inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(items[0]).keys()))
        writer.writeheader()
        for item in sorted(items, key=lambda i: (i.series, i.year, i.filename)):
            writer.writerow(asdict(item))
    print(f"\nWrote {out}: {len(items)} files")

    # Coverage: which years have a school-grain file for each measure.
    coverage: dict[int, dict[str, str]] = {}
    for item in items:
        if item.measure == "other":
            continue
        cell = coverage.setdefault(item.year, {})
        key = f"{item.measure}_{item.grain}"
        # Prefer a spreadsheet over a PDF when both exist.
        if key not in cell or (item.fmt in ("xlsx", "xls") and cell[key] == "pdf"):
            cell[key] = item.fmt
    (LOOKUPS / "coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n")

    print("\nyear  enrol/school  enrol/district  fte/school  fte/district")
    for year in sorted(coverage):
        c = coverage[year]
        print(f"{year}  {c.get('enrollment_school','-'):>12}  {c.get('enrollment_district','-'):>14}"
              f"  {c.get('teacher_fte_school','-'):>10}  {c.get('teacher_fte_district','-'):>12}")


if __name__ == "__main__":
    main()
