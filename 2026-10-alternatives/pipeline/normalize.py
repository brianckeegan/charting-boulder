"""Harmonize every source onto one schema and write data/processed/.

Phases C, S and V of TASK.md. This is where the four source shapes stop being
four things:

  - CDE school spreadsheets      2003-2025, school x grade
  - NCES CCD                     1986-2023, school x grade + teacher FTE
  - CDE staff spreadsheets       teacher FTE by school
  - re-OCR'd yearbooks           1986-1999 district x grade, and district
                                 trends reaching back to 1977-78

Joins:
  school   CDE school_code <-> CCD seasch, both normalized to a zero-padded
           four-digit string. The registry keys on the NCES id, which is
           stable across renames and code changes; CDE codes are not unique
           statewide in every year.
  district yearbook district names <-> CDE district codes, by normalized name
           within county. Names are the only key the yearbooks print.

Run:  python3 -m pipeline.normalize
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .extract import (
    ccd_records,
    parse_cde_school_sheet,
    parse_cde_teacher_sheet,
    parse_yearbook_district_grade,
    parse_yearbook_district_summary,
    parse_yearbook_trends,
)
from .membership import (
    parse_indented_sheet,
    parse_membership_pdf,
)
from .schema import normalize_code

HERE = Path(__file__).resolve().parent.parent
RAW_CDE = HERE / "data" / "raw" / "cde"
CCD_CACHE = HERE / "data" / "raw" / "ccd"
YEARBOOKS = HERE / "data" / "interim" / "yearbooks"
PROCESSED = HERE / "data" / "processed"
LOOKUPS = HERE / "data" / "lookups"
DISTRICT_ALIASES = LOOKUPS / "district-aliases.csv"
AUDIT = HERE / "audit"

CCD_YEARS = range(1986, 2025)  # 2024 was released since the audit


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path.relative_to(HERE)}: {len(rows):,} rows")


# --------------------------------------------------------------------------
# district name matching
# --------------------------------------------------------------------------

DISTRICT_SUFFIX = re.compile(
    r"\b(RE|R|J|JT|RJ|RD|C|UD)?[-\s]?\d+\s*(J|JT|J1|A)?$", re.I)


def split_district_name(name: str) -> tuple[str, str]:
    """Split a district name into its base and its organisational suffix.

    The suffix is printed inconsistently across volumes - the same district is
    "AGATE" in one book and "AGATE 300" in the next, "CALHAN" and "CALHAN
    RJ-1", "AULT-HIGHLAND RE-9" and "AULT-HIGHLAND" - and some names carry a
    footnote asterisk. So it cannot simply be kept, or the same district fails
    to match itself across two books.

    Nor can it simply be dropped: Garfield RE-2 (Rifle, about 1,560 pupils)
    and Garfield 16 (Parachute, about 165) are different districts in the same
    county, distinguishable only by that suffix. `district_key` therefore
    keeps it only where it does real work.
    """
    text = re.sub(r"[*†‡]", " ", str(name).upper())
    # A parenthetical names the town - "WELD RE-1 (GILCREST)", "PARK (ESTES
    # PARK) R-3" - and is not part of the district's name. It is not always
    # last, so it cannot be matched only at the end. The joint marker "(J)"
    # is part of the name, so only a parenthetical of three letters or more
    # is dropped.
    # Read the other way round where the parenthetical is the district and
    # what precedes it is the county: "WELD RE-1 (GILCREST)" is Gilcrest RE-1,
    # and dropping the bracket would leave Gilcrest and Keenesburg both
    # called Weld.
    inverted = re.match(r"^\s*[A-Z][A-Z .'-]*?\s+"
                        r"((?:RE|R|J|JT|RJ|RD|C|UD)?[- ]?\d+[A-Z]{0,2})\s*"
                        r"\(\s*([A-Z][A-Z ]{2,})\)\s*$", text)
    if inverted:
        text = f"{inverted.group(2).strip()} {inverted.group(1)}"
    text = re.sub(r"\(\s*[A-Z][A-Z ]{2,}\)", " ", text)
    text = re.sub(r"[^A-Z0-9 -]", " ", text)
    printed = re.sub(r"\s+", " ", text).strip()
    # NCES prints the legal name - "SCHOOL DISTRICT NO. 1 IN THE COUNTY OF
    # DENVER AND STATE OF COLORADO" - where CDE prints "DENVER COUNTY 1". The
    # clause is not dropped but turned around, because it is the only part of
    # the legal name that says which district this is: struck out, Denver's
    # name and Arapahoe's both reduce to "1".
    legal = re.search(r"\s+IN\s+THE\s+COUNTY\s+OF\s+([A-Z][A-Z ]*?)"
                      r"(?:\s+(?:AND\s+)?ST[A-Z]*\b.*)?$", text)
    county_said = re.sub(r"\s+(?:AND\s+)?ST[A-Z]*$", "", legal.group(1).strip()) if legal else ""
    if len(county_said) > 3:
        text = f"{county_said} COUNTY {text[:legal.start()].strip()}"
    else:
        # A truncated or multi-county clause names nothing usable. Drop it,
        # unless dropping it would leave a bare number for a name.
        shortened = re.sub(r"\s+(?:IN|OF)\s+THE\s+COUNT.*$", " ", text)
        shortened = re.sub(r"\s+AND\s+STATE\s+OF\b.*$", " ", shortened)
        # A word, not a letter: the J of "28J" is a letter, and passing on it
        # reduced "SCHOOL DISTRICT NO. 28J IN THE COUNTIES OF ADAMS AND
        # ARAPAHOE" to a bare "28J".
        if re.search(r"[A-Z]{3,}", re.sub(r"\bNO\b|\bSCH(?:OOL)? DIST(?:RICT)?\b", " ", shortened)):
            text = shortened
    text = re.sub(r"\bNO\b(?=\s*-?\s*\d)", " ", text)
    text = re.sub(r"\s+SCHOOLS?\s*$", " ", text)
    # "School district" is boilerplate, and dropping it is not cosmetic. CDE
    # writes Fort Lupton as "WELD COUNTY S/D RE-8" and Gilcrest as "WELD
    # COUNTY RE-1"; with the boilerplate kept they have different base names,
    # so nothing noticed that both are called Weld County, and the yearbooks'
    # unsuffixed "WELD COUNTY" was handed to whichever the crosswalk saw
    # last - 3080, Gilcrest - taking four years of Fort Lupton's pupils with
    # it. Stripped, the two collide on one base and the suffix decides, which
    # is what `index_district_names` exists for.
    text = re.sub(r"\bS D\b|\bSCH(?:OOL)? DIST(?:RICT)?\b", " ", text)
    text = re.sub(r"\bCO\b(?= )", "COUNTY", text)
    text = re.sub(r"\s+", " ", text).strip()
    # The joint-district marker is printed "RE 2(J)" in one book and "RE-2J" in
    # the next, and stripping the brackets above leaves the J standing alone.
    # It has to be pulled back into the suffix, or "BOULDER VALLEY RE 2(J)"
    # keeps "RE 2 J" in its base name and never matches "BOULDER VALLEY".
    # The designator is printed every way a typewriter allows: "9-R", "26 JT",
    # "RE-1-J", "R2-J", "27J". Read too narrowly, Durango 9-R keeps its number
    # in its base name and never matches the volume that prints plain
    # "DURANGO". The trailing letter groups are capped at two characters so
    # that a place name appended after the designator - "12 FIVE STAR" - is
    # not swallowed as part of it.
    match = re.search(
        r"\s((?:RE|R|J|JT|RJ|RD|C|UD)?[- ]?\d+[A-Z]{0,2}(?:[- ][A-Z]{1,2})*)$", text)
    if match:
        suffix = re.sub(r"[^A-Z0-9]", "", match.group(1))
        # And it has to be dropped from the suffix as well. It says the
        # district crosses a county line, not which district it is: no two
        # districts are told apart by it, but a book that prints it where
        # another does not would otherwise look like two districts. The books
        # spell it "J" and "JT" both - "WILEY RE-13J" and "WILEY RE-13 JT" -
        # so both come off.
        suffix = re.sub(r"(?<=\d)JT?$", "", suffix)
        base = text[:match.start()].strip()
    else:
        base, suffix = text, ""
    # A base with no word in it names nothing. "SCHOOL DIST NO 27J" loses its
    # boilerplate and would be left as "27J", which matches no CDE name and
    # says nothing about which district it is; the name as printed is kept
    # instead.
    if not re.search(r"[A-Z]{3,}", base):
        return printed, ""
    return base, suffix


def base_key(name: str, county: str = "") -> str:
    base, _ = split_district_name(name)
    base = re.sub(r"[^A-Z0-9]", "", base)
    county_key = re.sub(r"[^A-Z]", "", str(county).upper())
    return f"{county_key}|{base}" if county_key else base


# A Board of Cooperative Educational Services is a shared agency several
# districts run together, not a district. The yearbooks list them alongside
# districts, which is why a volume reports 180-183 reporting units where
# Colorado had 176 districts.
#
# They are flagged, never removed. Their pupils are real and NCES counts them
# too: dropping the 185 BOCES pupils from 1992 turns an exact match with NCES
# into a 185-pupil shortfall, and the same in 1993, 1996 and 1999. The count
# of districts is what was misleading, not the totals.
BOCES = re.compile(r"\bBOCE?S\b|BOARD OF COOPERATIVE", re.I)


def unit_type(name: str) -> str:
    return "boces" if BOCES.search(str(name)) else "district"


# Base keys that need their suffix to stay, because two real districts share
# the base. Filled by index_district_names() before any key is built.
_AMBIGUOUS: set[str] = set()


def index_district_names(rows: list[dict]) -> None:
    """Find the base names that more than one district actually uses.

    Read off the district codes, not the printed suffixes. Counting suffixes
    asks whether a name was ever written two ways, which is a different and
    much commoner thing: Durango is "DURANGO 9-R" in one volume and "DURANGO
    9R" in another, and no second Durango exists. Counting codes asks whether
    two districts answer to the base, which is the question the suffix is
    being kept to settle.
    """
    codes: dict[str, set] = defaultdict(set)
    for row in rows:
        code = row.get("district_code") or ""
        if not code:
            continue
        for key in {base_key(row.get("district_name", "")),
                    base_key(row.get("district_name", ""), row.get("county_name", ""))}:
            if key and not key.endswith("|"):
                codes[key].add(code)
    _AMBIGUOUS.clear()
    _AMBIGUOUS.update(k for k, found in codes.items() if len(found) > 1)


# Colorado's 64 counties. The data cannot supply this list: CDE's county
# column alone carries 69 values, among them "FEMONT" and "PHILLIPS COUNTY\\".
COLORADO_COUNTIES = frozenset(name.replace("_", " ") for name in """
    ADAMS ALAMOSA ARAPAHOE ARCHULETA BACA BENT BOULDER BROOMFIELD CHAFFEE
    CHEYENNE CLEAR_CREEK CONEJOS COSTILLA CROWLEY CUSTER DELTA DENVER DOLORES
    DOUGLAS EAGLE EL_PASO ELBERT FREMONT GARFIELD GILPIN GRAND GUNNISON
    HINSDALE HUERFANO JACKSON JEFFERSON KIOWA KIT_CARSON LA_PLATA LAKE LARIMER
    LAS_ANIMAS LINCOLN LOGAN MESA MINERAL MOFFAT MONTEZUMA MONTROSE MORGAN
    OTERO OURAY PARK PHILLIPS PITKIN PROWERS PUEBLO RIO_BLANCO RIO_GRANDE
    ROUTT SAGUACHE SAN_JUAN SAN_MIGUEL SEDGWICK SUMMIT TELLER WASHINGTON WELD
    YUMA""".split())
assert len(COLORADO_COUNTIES) == 64, len(COLORADO_COUNTIES)

# The counties CDE states for each district code. Filled by
# index_district_counties() before any lookup is made.
_COUNTIES_OF_CODE: dict[str, set] = defaultdict(set)


def official_county(name: str) -> str:
    """A county name in the official form, or "" if it is not one."""
    text = re.sub(r"\s+", " ", re.sub(r"[^A-Z ]", " ", str(name or "").upper())).strip()
    text = re.sub(r" COUNTY$", "", text)
    return text if text in COLORADO_COUNTIES else ""


def index_district_counties(rows: list[dict]) -> None:
    _COUNTIES_OF_CODE.clear()
    for row in rows:
        county = official_county(row.get("county_name", ""))
        if row.get("district_code") and county:
            _COUNTIES_OF_CODE[row["district_code"]].add(county)


def lookup_district(crosswalk: dict, name: str, county: str = "") -> dict | None:
    """A district code for a printed name and county, or None.

    The county-keyed lookup comes first. Without a hit there, the name alone
    is tried - but a match from another county is refused where the row
    names a real county and CDE places the district in a different one.
    Without that check, stripping a town's name in brackets gave Estes Park
    the bare key "PARK", and a row reading "PARK RE-2" in Park County would
    have been filed under Estes Park in Larimer. A county the OCR misread
    ("Montrase") names no real county, so it cannot refuse a match.
    """
    hit = crosswalk.get(district_key(name, county))
    if hit:
        return hit
    hit = crosswalk.get(district_key(name))
    if not hit:
        return None
    stated = official_county(county)
    known = _COUNTIES_OF_CODE.get(hit["district_code"])
    if stated and known and stated not in known:
        return None
    return hit


def district_key(name: str, county: str = "") -> str:
    """A comparable key for a district name.

    County plus base name, with the organisational suffix appended only where
    two real districts share that base (see `index_district_names`).
    """
    key = base_key(name, county)
    if key in _AMBIGUOUS:
        _, suffix = split_district_name(name)
        return f"{key}#{suffix}" if suffix else key
    return key


def build_district_crosswalk(cde_school_records: list[dict]) -> dict[str, dict]:
    """Map a district name key to a CDE district code.

    Built from the CDE school files themselves, which carry both the code and
    the name, so it needs no hand-maintained list. Later years win where a
    name is reused, because the modern code is the one the archive keys on.

    Six districts are beyond any rule, because the name in the yearbook and
    the name in the modern file have nothing in common: Fort Lupton RE-8 is
    now Weld County S/D RE-8, Gilcrest RE-1 is now Weld County RE-1, Custer
    County's only district was called Consolidated C-1 for twenty-three years.
    Those are read from data/lookups/district-aliases.csv, which records for
    each one the membership either side of the change that identifies it.
    """
    by_key: dict[str, dict] = {}
    for record in sorted(cde_school_records, key=lambda r: r["year"]):
        code, name = record["district_code"], record["district_name"]
        if not code or not name:
            continue
        for key in {district_key(name), district_key(name, record.get("county_name", ""))}:
            if not key or key.endswith("|"):
                continue
            # A base name two districts share cannot be coded by that base.
            # Garfield County has Garfield RE-2 in Rifle and Garfield 16 in
            # Parachute; a file that prints either as plain "GARFIELD" was
            # being handed whichever code was seen last, which put nine years
            # of Rifle's pupils - 2,193 rising to 3,787 - under Parachute's
            # code, a district of about 700 at the time. The suffix is what
            # tells them apart, so without one the name resolves to nothing
            # and the row is left uncoded rather than coded wrongly.
            if key in _AMBIGUOUS and "#" not in key:
                continue
            by_key[key] = {"district_code": code, "district_name": name}

    for alias in load_district_aliases():
        key = district_key(alias["district_name"], alias["county_name"])
        by_key[key] = {"district_code": normalize_code(alias["district_code"], 4),
                       "district_name": alias["district_name"],
                       "via": f"alias ({alias['reason']})"}
    return by_key


def load_district_aliases() -> list[dict]:
    """Districts the automatic crosswalk cannot reach, and why."""
    if not DISTRICT_ALIASES.exists():
        return []
    with DISTRICT_ALIASES.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("district_code")]


# --------------------------------------------------------------------------

def load_cde_school() -> tuple[list[dict], dict]:
    """Every CDE school-by-grade file the fetch step landed.

    Three of them are not the ordinary shape. 2003 is a spreadsheet laid out
    as an indented panel with no header a column finder can use; 2001 and 2002
    are PDFs whose grade columns run together as text. Each is tried with the
    ordinary reader first and falls through to the one that fits, so a file
    that changes shape again is picked up rather than dropped.
    """
    records, meta = [], {}
    paths = (sorted(RAW_CDE.glob("enrollment-school-*.xls*"))
             + sorted(RAW_CDE.glob("enrollment-school-*.pdf")))
    for path in sorted(paths, key=lambda p: (int(re.search(r"(\d{4})", p.name).group(1)), p.suffix)):
        year = int(re.search(r"(\d{4})", path.name).group(1))
        if path.suffix.lower() == ".pdf":
            rows, info = parse_membership_pdf(path, year, path.name)
        else:
            rows, info = parse_cde_school_sheet(path, year, path.name)
            if info.get("error"):
                rows, info = parse_indented_sheet(path, year, path.name)
        if info.get("error") or not rows:
            meta[year] = info
            print(f"  CDE enrollment {year}: {info.get('error', 'no rows')}")
            continue
        records.extend(rows)
        meta[year] = info
        totals = info["row_total_pass"] + info["row_total_fail"]
        note = (f"{info['schools']:,} schools, "
                f"row totals {info['row_total_pass']}/{totals}")
        if info.get("district_total_pass") is not None:
            districts = info["district_total_pass"] + info["district_total_fail"]
            note += f", district totals {info['district_total_pass']}/{districts}"
        print(f"  CDE enrollment {year}: {note}")
    filled = resolve_school_codes(records)
    if filled:
        print(f"  {filled['districts']:,} rows given a district code by name, "
              f"{filled['schools']:,} a school code, from the years that print them")
    return records, meta


def resolve_school_codes(records: list[dict]) -> dict:
    """Give the code-less years the codes the coded years use.

    The 2001 and 2002 PDFs print no codes at all - the county, district and
    school are named and nothing else. Without a code those rows cannot reach
    the district tier or the school registry, so the 1,630 schools they carry
    would sit in the archive attached to nothing.

    The years either side do print codes, and the names are the same names.
    A name is only used where it maps to exactly one code across the coded
    years, so a district that was renamed or a school name that two buildings
    shared resolves to nothing rather than to a guess.
    """
    district_of: dict[str, set] = defaultdict(set)
    school_of: dict[tuple, set] = defaultdict(set)
    for row in records:
        name = (row["district_name"] or "").strip().upper()
        if name and row["district_code"]:
            district_of[name].add(row["district_code"])
        if name and row.get("school_code") and row["school_name"]:
            school_of[(name, row["school_name"].strip().upper())].add(row["school_code"])

    districts = schools = 0
    for row in records:
        name = (row["district_name"] or "").strip().upper()
        if not row["district_code"]:
            codes = district_of.get(name, set())
            if len(codes) == 1:
                row["district_code"] = next(iter(codes))
                districts += 1
        if not row.get("school_code"):
            codes = school_of.get((name, (row["school_name"] or "").strip().upper()), set())
            if len(codes) == 1:
                row["school_code"] = next(iter(codes))
                schools += 1
    return {"districts": districts, "schools": schools}


# The 2001 and 2002 PDFs abbreviate names the later files spell out, so a
# name is compared on its words, with the common abbreviations expanded and
# the words every school shares removed.
_SCHOOL_WORDS = {"ELEM": "ELEMENTARY", "EL": "ELEMENTARY", "SCH": "SCHOOL",
                 "SCHL": "SCHOOL", "JR": "JUNIOR", "SR": "SENIOR", "MT": "MOUNT",
                 "ST": "SAINT", "CTR": "CENTER", "ACAD": "ACADEMY",
                 "INTERMED": "INTERMEDIATE"}


def school_name_key(name: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]", " ", str(name or "").upper()).split()
    words = [_SCHOOL_WORDS.get(w, w) for w in words]
    return " ".join(w for w in words if w not in ("SCHOOL", "THE"))


def bridge_school_codes(records: list[dict], ccd_schools: list[dict]) -> dict:
    """Give a code-less CDE school the code NCES holds for it that year.

    resolve_school_codes matches a 2001 name against the names of 2003 and
    later, and the names changed form in between - "MESA ELEMENTARY" in the
    PDF, "MESA ELEMENTARY SCHOOL" after - so it left 371 schools in 2001 and
    335 in 2002 with no code. NCES's directory for the same year carries
    CDE's district code, CDE's school code and a name from the same period.

    A match must be unique within the district, and the code must not be one
    a coded school already holds that year. The test of the result is
    independent: NCES built these years from CDE's own submission, so a
    right match counts the same pupils. Every name match agrees to the pupil.
    """
    index: dict[tuple, list[dict]] = defaultdict(list)
    for school in ccd_schools:
        if school.get("school_code") and school.get("district_code"):
            index[(school["year"], school["district_code"],
                   school_name_key(school["school_name"]))].append(school)
    taken = {(r["year"], r["school_code"]) for r in records if r.get("school_code")}

    found: dict[tuple, str] = {}
    for row in records:
        if row.get("school_code") or not row.get("district_code"):
            continue
        key = (row["year"], row["district_code"], school_name_key(row["school_name"]))
        if key in found:
            continue
        hits = index.get(key, [])
        code = hits[0]["school_code"] if len(hits) == 1 else ""
        found[key] = code if code and (row["year"], code) not in taken else ""

    bridged = set()
    for row in records:
        if row.get("school_code") or not row.get("district_code"):
            continue
        code = found.get((row["year"], row["district_code"],
                          school_name_key(row["school_name"])), "")
        if code:
            row["school_code"] = code
            bridged.add((row["year"], code))
    by_name = set(bridged)

    # A second pass for the names the first cannot reach - "SINGING HILLS
    # ELEMENTARY SCHOO", cut off by the PDF's column; "GOVERNOR'S" against
    # "GOVERNORS"; a district the PDF names in a form that resolved to no
    # code. Left alone, each of these is listed twice: once under its
    # placeholder with CDE's count, and again as an NCES-only school with the
    # same count. The pass accepts an NCES school only where no CDE school
    # holds its code, its total equals the CDE total to the pupil, it is the
    # only such school in the district (or, where the district is unknown,
    # carries the same name), and the two names share a distinctive word.
    held = {(r["year"], r["school_code"]) for r in records if r.get("school_code")}
    pending: dict[tuple, dict] = {}
    for row in records:
        if row.get("school_code") or row["grade"] in ("SPECIAL_EDUCATION", "UNGRADED"):
            continue
        key = (row["year"], row.get("district_code") or "",
               (row.get("district_name") or "").strip().upper(), row["school_name"])
        entry = pending.setdefault(key, {"total": 0})
        entry["total"] += row["enrollment"]
    free = defaultdict(list)
    for school in ccd_schools:
        code, total = school.get("school_code"), school.get("enrollment_total_ccd")
        if code and total and (school["year"], code) not in held:
            free[school["year"]].append(school)

    def distinctive(name: str) -> set:
        generic = {"ELEMENTARY", "MIDDLE", "HIGH", "JUNIOR", "SENIOR", "CENTER",
                   "ACADEMY", "CHARTER", "PROGRAM", "EDUCATION", "LEARNING", "PRIMARY",
                   "INTERMEDIATE", "PREPARATORY", "COMMUNITY", "COUNTY", "DISTRICT"}
        return {w for w in school_name_key(name).split() if len(w) >= 4 and w not in generic}

    # Keyed on the whole identity - year, district code, district name and
    # school name - so two code-less schools of one name in two districts
    # the PDF did not resolve are never one school here.
    second: dict[tuple, str] = {}
    for (year, district, district_name, name), entry in pending.items():
        if entry["total"] <= 0:
            continue
        if district:
            candidates = [s for s in free[year] if s.get("district_code") == district]
        else:
            candidates = [s for s in free[year]
                          if school_name_key(s["school_name"]) == school_name_key(name)]
        same = [s for s in candidates if s["enrollment_total_ccd"] == entry["total"]
                and distinctive(s["school_name"]) & distinctive(name)]
        if len(same) == 1:
            second[(year, district, district_name, name)] = same[0]["school_code"]
    claimed = defaultdict(int)
    for (year, _, _, _), code in second.items():
        claimed[(year, code)] += 1
    for row in records:
        if row.get("school_code"):
            continue
        code = second.get((row["year"], row.get("district_code") or "",
                           (row.get("district_name") or "").strip().upper(),
                           row["school_name"]))
        # Two CDE schools settling on one NCES school means the evidence
        # does not decide between them, so neither takes it.
        if code and claimed[(row["year"], code)] == 1:
            row["school_code"] = code
            bridged.add((row["year"], code))

    # The check, on the first pass only: the second pass makes an equal
    # total its condition, so it cannot also be the test of it.
    cde_total: dict[tuple, int] = defaultdict(int)
    for row in records:
        if (row["year"], row.get("school_code")) in by_name \
                and row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED"):
            cde_total[(row["year"], row["school_code"])] += row["enrollment"]
    ccd_total = {(s["year"], s["school_code"]): s.get("enrollment_total_ccd")
                 for s in ccd_schools if s.get("school_code")}
    compared = [(k, v) for k, v in cde_total.items() if ccd_total.get(k) is not None]
    agree = sum(1 for k, v in compared if v == ccd_total[k])
    return {"schools": len(bridged), "by_name": len(by_name),
            "by_equal_total": len(bridged) - len(by_name),
            "by_name_compared_with_nces": len(compared),
            "by_name_agree_to_the_pupil": agree}


def separate_shared_school_codes(records: list[dict]) -> dict:
    """Prefix a school code with its district where two districts share it.

    A CDE school code is unique inside its district, not across the state,
    and CDE reuses a few for facilities rather than schools: in 2011 "0006"
    is the county jail programme in Brighton, Denver and Greeley, and in 2012
    "0001" is "facilities with district run education" in two districts. The
    school tables are keyed on the code, so each of those collapsed to one
    row per grade and 51 pupils were lost. A code shared in any year is
    changed to "<district>-<code>" in every year it appears, not only in the
    shared year: "0001" is one district's alone from 2013 to 2024, and a
    prefix in 2012 only would break that facility into two, the first of
    which appears to close.
    """
    owners: dict[tuple, set] = defaultdict(set)
    for row in records:
        if row.get("school_code"):
            owners[(row["year"], row["school_code"])].add(row.get("district_code") or "")
    shared_years = sorted(f"{y}:{c}" for (y, c), districts in owners.items() if len(districts) > 1)
    shared = {c for (y, c), districts in owners.items() if len(districts) > 1}
    for row in records:
        if row.get("school_code") in shared:
            row["school_code"] = f"{row.get('district_code') or ''}-{row['school_code']}"
    return {"codes": shared_years, "prefixed_in_every_year": sorted(shared)}


def assign_placeholder_codes(records: list[dict]) -> dict:
    """A code for each school the sources print without one.

    The school tables are keyed on the school code, so every code-less row
    shared one key, and each grade kept only the last row written: 2001 lost
    124,863 pupils from the school tables, and one "school" was left holding
    the combined 124,924 of 371. A placeholder is made from the district and
    the printed name, so it is the same in both years for the same school,
    and it starts with X, which no CDE code does.
    """
    made = set()
    for row in records:
        if row.get("school_code"):
            continue
        owner = row.get("district_code") or (row.get("district_name") or "").strip().upper()
        digest = hashlib.sha1(f"{owner}|{school_name_key(row['school_name'])}"
                              .encode("utf-8")).hexdigest()[:5].upper()
        row["school_code"] = f"X{digest}"
        made.add((row["year"], row["school_code"]))
    return {"school_years": len(made)}


def load_cde_teacher() -> tuple[list[dict], dict]:
    """Teacher FTE by school, preferring the eleven-year table.

    pipeline/teacher_fte.py reads every staff report CDE publishes in either
    serial and writes data/processed/school-teacher-fte.csv. That table is a
    superset of the three spreadsheet years this module used to read on its
    own, so it is the source when it exists. The glob is kept as the fallback
    for a checkout where the staff step has not been run.
    """
    table = PROCESSED / "school-teacher-fte.csv"
    if table.exists():
        records, by_year = [], defaultdict(lambda: {"schools_with_fte": 0, "total_fte": 0.0})
        with table.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                year = int(row["year"])
                fte = float(row["teacher_fte"]) if row["teacher_fte"] else None
                records.append({
                    "year": year,
                    "school_code": normalize_code(row["school_code"], 4),
                    "district_code": normalize_code(row["district_code"], 4),
                    "teacher_fte": row["teacher_fte"],
                    "enrollment_reported": row["enrollment_reported"],
                    "source": row["source"],
                })
                if fte is not None:
                    by_year[year]["schools_with_fte"] += 1
                    by_year[year]["total_fte"] += fte
        meta = dict(sorted(by_year.items()))
        for year, info in meta.items():
            print(f"  CDE teacher FTE {year}: {info['schools_with_fte']:,} schools, "
                  f"{info['total_fte']:,.1f} FTE")
        return records, meta

    print("  CDE teacher FTE: school-teacher-fte.csv absent; "
          "reading the spreadsheet years only (run pipeline.teacher_fte first)")
    records, meta = [], {}
    for path in sorted(RAW_CDE.glob("teacher_fte-school-*.xls*")):
        year = int(re.search(r"(\d{4})", path.name).group(1))
        rows, info = parse_cde_teacher_sheet(path, year, path.name)
        records.extend(rows)
        meta[year] = info
        note = info.get("error") or f"{info['schools_with_fte']:,} schools, {info['total_fte']:,.1f} FTE"
        print(f"  CDE teacher FTE {year}: {note}")
    return records, meta


def load_ccd() -> tuple[list[dict], list[dict], dict]:
    enrollment, school_years, meta = [], [], {}
    for year in CCD_YEARS:
        try:
            rows, schools, info = ccd_records(year, CCD_CACHE)
        except Exception as exc:  # noqa: BLE001
            print(f"  CCD {year}: unavailable ({exc})")
            continue
        enrollment.extend(rows)
        school_years.extend(schools)
        meta[year] = info
        print(f"  CCD {year}: {info['directory_rows']:,} schools, "
              f"{info['schools_with_teacher_fte']:,} with FTE, "
              f"{info['schools_with_usable_coordinates']:,} located")
    return enrollment, school_years, meta


def _name_distance(a: str, b: str, ceiling: int = 2) -> int:
    """Levenshtein distance, given up on once it cannot matter."""
    if abs(len(a) - len(b)) > ceiling:
        return ceiling + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[-1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def repair_trend_names(trends: list[dict], roster: dict[str, dict]) -> list[dict]:
    """Repair district names the OCR damaged on the trend pages.

    Page 63 of the 1986 volume lost the first character of every district
    name - "SUMMIT RE-1" came back as "UMMIT RE-1", "TELLURIDE" as
    "ELLURIDE" - while the figures beside them and the county in the next
    cell read cleanly. It is a left-edge crop on one page, not a bad scan.
    Page 58 misread Montrose as MONTRASE in both the district and the county.

    Neither is guessed at. The same volume prints the same districts in its
    grade and summary tables, which that crop did not touch, so the repair is
    a lookup inside one document: a damaged name is accepted only where
    exactly one name in the volume's own roster fits it, either by having lost
    up to three leading characters or by differing in at most two characters
    at the same length and the same organisational suffix. Anything matching
    two roster names, or none, is left as the OCR read it.
    """
    known = {k: v for k, v in roster.items()}
    repairs: list[dict] = []
    fixes: dict[str, dict] = {}
    for row in trends:
        raw = row["district_name"]
        key = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", raw.upper())).strip()
        if key in known or key in fixes:
            continue
        suffix = split_district_name(key)[1]
        head = [k for k in known if k.endswith(key) and 0 < len(k) - len(key) <= 3]
        near = [k for k in known
                if len(k) == len(key) and split_district_name(k)[1] == suffix
                and _name_distance(k, key) <= 2]
        match = head[0] if len(head) == 1 else (near[0] if len(near) == 1 else "")
        if not match:
            continue
        fixes[key] = known[match]
        repairs.append({"read_as": raw, "repaired_to": known[match]["district_name"],
                        "rule": "truncated" if len(head) == 1 else "misread"})

    for row in trends:
        key = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", row["district_name"].upper())).strip()
        fix = fixes.get(key)
        if fix:
            row["district_name"] = fix["district_name"]
            # The roster prints counties in capitals and Table 4 in title
            # case; the repaired rows take the Table 4 form.
            row["county_name"] = (fix["county_name"] or row["county_name"]).strip().title()
    return repairs


def load_yearbooks() -> tuple[list[dict], list[dict], list[dict], dict]:
    grade_records, trend_records, summary_records, meta = [], [], [], {}
    for volume in sorted(YEARBOOKS.iterdir()):
        if not volume.is_dir() or not volume.name.isdigit():
            continue
        year = int(volume.name)
        grades, ginfo = parse_yearbook_district_grade(volume, year)
        trends, tinfo = parse_yearbook_trends(volume, year)
        summary, sinfo = parse_yearbook_district_summary(volume, year)

        # The volume's own roster, from the two tables the crop missed.
        roster: dict[str, dict] = {}
        for record in grades + summary:
            key = re.sub(r"\s+", " ",
                         re.sub(r"[^A-Z0-9 ]", " ", record["district_name"].upper())).strip()
            roster.setdefault(key, record)
        repairs = repair_trend_names(trends, roster)
        tinfo["name_repairs"] = repairs
        for repair in repairs:
            print(f"    {year} trends: read \"{repair['read_as']}\", "
                  f"filed as \"{repair['repaired_to']}\" ({repair['rule']})")

        grade_records.extend(grades)
        trend_records.extend(trends)
        summary_records.extend(summary)
        meta[year] = {"district_by_grade": ginfo, "trends": tinfo, "summary": sinfo}
        if "error" in ginfo:
            print(f"  yearbook {year}: {ginfo['error']}")
        else:
            staff = ("" if sinfo.get("error") else
                     f"; summary {sinfo['districts']} districts, "
                     f"{sinfo['total_teacher_fte']:,.0f} FTE"
                     + (f" (staff {sinfo['staff_year']})"
                        if sinfo.get("staff_year") != year else ""))
            print(f"  yearbook {year}: {ginfo['districts']} districts, "
                  f"totals {ginfo['row_total_pass']}/{ginfo['row_total_pass'] + ginfo['row_total_fail']}; "
                  f"trends {tinfo.get('districts', 0)} districts{staff}")
    return grade_records, trend_records, summary_records, meta


# --------------------------------------------------------------------------

def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    print("Reading CDE school spreadsheets")
    cde_school, cde_school_meta = load_cde_school()
    print("Reading CDE staff spreadsheets")
    cde_teacher, cde_teacher_meta = load_cde_teacher()
    print("Reading NCES CCD")
    ccd_enrollment, ccd_schools, ccd_meta = load_ccd()
    print("Reading re-OCR'd yearbooks")
    yb_grades, yb_trends, yb_summary, yb_meta = load_yearbooks()

    bridge = bridge_school_codes(cde_school, ccd_schools)
    placeholders = assign_placeholder_codes(cde_school)
    shared_codes = separate_shared_school_codes(cde_school)
    if shared_codes["codes"]:
        print(f"  school codes two districts share, given a district prefix: "
              f"{', '.join(shared_codes['codes'])}")
    report["school_codes_shared_across_districts"] = shared_codes
    print(f"  {bridge['schools']:,} code-less school-years given NCES's code for them: "
          f"{bridge['by_name']:,} by name, of which {bridge['by_name_agree_to_the_pupil']:,} "
          f"of {bridge['by_name_compared_with_nces']:,} compared agree with NCES to the "
          f"pupil; {bridge['by_equal_total']:,} more by an equal total")
    print(f"  {placeholders['school_years']:,} school-years given a placeholder code (X...)")
    report["school_codes_bridged_from_nces"] = bridge
    report["school_placeholder_codes"] = placeholders

    # ---- school identity -------------------------------------------------
    # CCD carries the NCES id and the CDE school code together, so it is the
    # bridge. Build (year, school_code) -> ncessch, then fall back to any year
    # for a school CDE reports but CCD does not cover.
    ncessch_by_year_code: dict[tuple[int, str], str] = {}
    ncessch_by_code: dict[str, str] = {}
    for row in ccd_schools:
        if row["school_code"]:
            ncessch_by_year_code[(row["year"], row["school_code"])] = row["ncessch"]
            ncessch_by_code.setdefault(row["school_code"], row["ncessch"])

    matched = 0
    for row in cde_school:
        key = (row["year"], row["school_code"])
        ncessch = ncessch_by_year_code.get(key) or ncessch_by_code.get(row["school_code"], "")
        row["ncessch"] = ncessch
        if ncessch:
            matched += 1
    report["cde_rows_matched_to_nces_id"] = {
        "matched": matched, "total": len(cde_school),
        "rate": round(matched / len(cde_school), 4) if cde_school else None,
    }

    # ---- school enrollment panel ----------------------------------------
    print("\nBuilding the school panel")
    cde_index = {(r["year"], r["school_code"], r["grade"]): r for r in cde_school}
    ccd_index = {(r["year"], r["school_code"], r["grade"]): r for r in ccd_enrollment if r["school_code"]}

    # Deliberately narrow. Names, districts and coordinates live in
    # school-year.csv, one row per school-year rather than repeated on each of
    # a school's fourteen grade rows. Carrying them here, plus a source
    # filename per row, made this file 65 MB; the attributes are identical
    # within a school-year, so repeating them is storage without information.
    # `source` collapses to a one-letter flag for the same reason.
    panel = []
    for key in sorted(set(cde_index) | set(ccd_index)):
        year, code, grade = key
        c, n = cde_index.get(key), ccd_index.get(key)
        panel.append({
            "year": year,
            "ncessch": (c or {}).get("ncessch") or (n or {}).get("ncessch", ""),
            "school_code": code,
            "district_code": (c or {}).get("district_code", ""),
            "grade": grade,
            "enrollment_cde": c["enrollment"] if c else "",
            "enrollment_ccd": n["enrollment"] if n else "",
            "source": ("both" if c and n else "cde" if c else "ccd"),
        })
    # Every CDE pupil read has to reach the panel. Checked by year, because a
    # collapsed key loses rows silently and every total checked elsewhere is
    # summed before the panel is built.
    read_by_year: dict[int, int] = defaultdict(int)
    for row in cde_school:
        read_by_year[row["year"]] += row["enrollment"]
    kept_by_year: dict[int, int] = defaultdict(int)
    for row in panel:
        if row["enrollment_cde"] != "":
            kept_by_year[row["year"]] += row["enrollment_cde"]
    lost = {y: read_by_year[y] - kept_by_year.get(y, 0) for y in read_by_year
            if read_by_year[y] != kept_by_year.get(y, 0)}
    if lost:
        raise AssertionError(f"the school panel dropped CDE pupils: {lost}")
    print(f"  every CDE pupil read reaches the panel, in all {len(read_by_year)} years")
    write_csv(PROCESSED / "school-enrollment-by-grade.csv", panel, [
        "year", "ncessch", "school_code", "district_code",
        "grade", "enrollment_cde", "enrollment_ccd", "source"])

    # ---- school-year table ----------------------------------------------
    cde_totals: dict[tuple[int, str], int] = defaultdict(int)
    for row in cde_school:
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED"):
            cde_totals[(row["year"], row["school_code"])] += row["enrollment"]
    fte_index = {(r["year"], r["school_code"]): r for r in cde_teacher}
    ccd_school_index = {(r["year"], r["school_code"]): r for r in ccd_schools if r["school_code"]}
    # Coordinates come from the most recent year that has a real one, carried
    # backward by school id (finding A12).
    coords: dict[str, tuple] = {}
    for row in sorted(ccd_schools, key=lambda r: r["year"]):
        if row["latitude"] is not None:
            coords[row["ncessch"]] = (row["latitude"], row["longitude"])

    names = {(r["year"], r["school_code"]): r for r in cde_school}
    school_year_rows = []
    for key in sorted(set(cde_totals) | set(ccd_school_index)):
        year, code = key
        c = names.get(key, {})
        n = ccd_school_index.get(key, {})
        fte = fte_index.get(key, {})
        ncessch = c.get("ncessch") or n.get("ncessch", "")
        latitude, longitude = coords.get(ncessch, (None, None))
        school_year_rows.append({
            "year": year,
            "ncessch": ncessch,
            "school_code": code,
            "district_code": c.get("district_code", ""),
            "school_name": c.get("school_name") or n.get("school_name", ""),
            "district_name": c.get("district_name") or n.get("district_name", ""),
            "enrollment_total_cde": cde_totals.get(key, ""),
            "enrollment_total_ccd": n.get("enrollment_total_ccd") or "",
            "teacher_fte_cde": fte.get("teacher_fte", ""),
            "teacher_fte_ccd": n.get("teacher_fte_ccd") or "",
            "enrollment_reported_in_fte_file": fte.get("enrollment_reported", ""),
            "latitude": latitude if latitude is not None else "",
            "longitude": longitude if longitude is not None else "",
            "is_charter": n.get("is_charter", ""),
            "status": n.get("status", ""),
        })
    write_csv(PROCESSED / "school-year.csv", school_year_rows, [
        "year", "ncessch", "school_code", "district_code", "school_name", "district_name",
        "enrollment_total_cde", "enrollment_total_ccd", "teacher_fte_cde", "teacher_fte_ccd",
        "enrollment_reported_in_fte_file", "latitude", "longitude", "is_charter", "status"])

    # ---- registry and closures ------------------------------------------
    print("\nBuilding the school registry")
    seen: dict[str, dict] = {}
    for row in sorted(school_year_rows, key=lambda r: r["year"]):
        key = row["ncessch"] or f"CDE:{row['school_code']}"
        entry = seen.setdefault(key, {
            "ncessch": row["ncessch"], "school_codes": set(), "names": [],
            "district_codes": set(), "first_year": row["year"], "last_year": row["year"],
            "last_status": "", "latitude": row["latitude"], "longitude": row["longitude"],
        })
        entry["school_codes"].add(row["school_code"])
        if row["school_name"] and row["school_name"] not in entry["names"]:
            entry["names"].append(row["school_name"])
        if row["district_code"]:
            entry["district_codes"].add(row["district_code"])
        entry["last_year"] = max(entry["last_year"], row["year"])
        entry["first_year"] = min(entry["first_year"], row["year"])
        if row["status"]:
            entry["last_status"] = row["status"]

    last_panel_year = max((r["year"] for r in school_year_rows), default=0)
    code_owners: dict[str, set] = defaultdict(set)
    for key, entry in seen.items():
        for code in entry["school_codes"]:
            code_owners[code].add(key)
    name_index: dict[str, set] = defaultdict(set)
    for key, entry in seen.items():
        for name in entry["names"]:
            name_index[re.sub(r"[^A-Z]", "", name.upper())].add(key)

    registry = []
    for key, entry in sorted(seen.items()):
        still_open = entry["last_year"] >= last_panel_year
        reused = any(len(code_owners[c]) > 1 for c in entry["school_codes"])
        name_twin = any(len(name_index[re.sub(r"[^A-Z]", "", n.upper())]) > 1 for n in entry["names"])

        untracked = (not entry["ncessch"]
                     and all(c.startswith("X") for c in entry["school_codes"]))
        if still_open:
            label, confidence, evidence = "still_open", "high", f"reported in {last_panel_year}"
        elif untracked:
            # A placeholder is made from the printed name, and the PDFs print
            # the same school differently from year to year. The code cannot
            # be followed, so its disappearance says nothing about a closure.
            label, confidence, evidence = ("untracked", "none",
                                           "placeholder code; the source printed no code")
        elif str(entry["last_status"]) in ("2", "6"):
            label, confidence, evidence = "closed", "high", f"CCD school_status={entry['last_status']}"
        elif name_twin:
            label, confidence, evidence = "renamed", "low", "another school carries the same name"
        elif reused:
            label, confidence, evidence = "code_changed", "low", "school code later used by another school"
        else:
            label, confidence, evidence = "closed", "medium", "stopped reporting; no status field"

        registry.append({
            "ncessch": entry["ncessch"],
            "school_codes": ";".join(sorted(entry["school_codes"])),
            "names": ";".join(entry["names"]),
            "district_codes": ";".join(sorted(entry["district_codes"])),
            "first_year": entry["first_year"],
            "last_year": entry["last_year"],
            "closure_label": label,
            "closure_confidence": confidence,
            "closure_evidence": evidence,
            "latitude": entry["latitude"],
            "longitude": entry["longitude"],
        })
    write_csv(PROCESSED / "schools.csv", registry, [
        "ncessch", "school_codes", "names", "district_codes", "first_year", "last_year",
        "closure_label", "closure_confidence", "closure_evidence", "latitude", "longitude"])

    # ---- district tier ---------------------------------------------------
    print("\nBuilding the district tier")
    # Which base names two districts share has to be settled before the
    # crosswalk is built, not after: the crosswalk is what consults it.
    index_district_names(yb_trends + yb_grades + yb_summary + cde_school)
    index_district_counties(cde_school)
    crosswalk = build_district_crosswalk(cde_school)
    (LOOKUPS / "district-crosswalk.json").write_text(
        json.dumps(crosswalk, indent=2, sort_keys=True) + "\n")

    matched_districts = 0
    for row in yb_grades:
        hit = lookup_district(crosswalk, row["district_name"], row["county_name"])
        if hit:
            row["district_code"] = hit["district_code"]
            matched_districts += 1
    report["yearbook_rows_matched_to_district_code"] = {
        "matched": matched_districts, "total": len(yb_grades),
        "rate": round(matched_districts / len(yb_grades), 4) if yb_grades else None,
    }

    district_grade = [{
        "year": r["year"], "district_code": r["district_code"], "district_name": r["district_name"],
        "county_name": r["county_name"], "unit_type": unit_type(r["district_name"]),
        "grade": r["grade"], "enrollment": r["enrollment"], "source": r["source"],
    } for r in yb_grades]

    # The modern era's district tier is the school panel summed by district.
    modern: dict[tuple, int] = defaultdict(int)
    modern_names: dict[tuple, str] = {}
    for row in cde_school:
        key = (row["year"], row["district_code"], row["grade"])
        modern[key] += row["enrollment"]
        modern_names[(row["year"], row["district_code"])] = row["district_name"]
    for (year, code, grade), value in sorted(modern.items()):
        district_grade.append({
            "year": year, "district_code": code,
            "district_name": modern_names.get((year, code), ""), "county_name": "",
            "unit_type": unit_type(modern_names.get((year, code), "")),
            "grade": grade, "enrollment": value, "source": "cde-school-sum",
        })
    write_csv(PROCESSED / "district-enrollment-by-grade.csv", district_grade, [
        "year", "district_code", "district_name", "county_name", "unit_type",
        "grade", "enrollment", "source"])

    # District-year: one continuous fall-membership series, 1977 to the
    # present.
    #
    # Each volume reprints the previous nine years, so most district-years are
    # read from two or more books, and summing them all gave 700,000 pupils
    # for 1978 against Colorado's actual 560,000.
    #
    # One volume supplies each year outright, rather than merging readings
    # district by district across books.
    #
    # Merging looked reasonable and was not. The same district is "AGATE" in
    # one volume and "AGATE 300" in the next, "CALHAN" and "CALHAN RJ-1",
    # "DOLORES COUNTY RE NO" and "DOLORES RE-2" - real renames as well as
    # inconsistent printing. Matching by name reached 82%, and the residue
    # double-counted, inflating 1978 to 700,000 pupils against Colorado's
    # actual 560,000. A name-matching rule good enough for a total would have
    # to be perfect, and this one cannot be.
    #
    # Taking every row for a year from a single volume removes the problem
    # instead of mitigating it. Name matching is still used for the overlap
    # comparison below, where failing to match two readings costs a
    # comparison rather than corrupting a sum.
    volumes_by_year: dict[int, set] = defaultdict(set)
    for row in yb_trends:
        volumes_by_year[row["year"]].add(int(re.search(r"yearbook-(\d{4})", row["source"]).group(1)))
    chosen_volume = {
        year: (year if year in found else min(found))
        for year, found in volumes_by_year.items()
    }

    # The series: every row from the year's chosen volume, keyed on the name
    # exactly as that volume prints it. No cross-volume matching is involved,
    # so a rename cannot double-count. The ambiguity index is the one built
    # before the crosswalk: indexing again here, after grade rows have taken
    # codes from that crosswalk, could key lookups by rules the crosswalk was
    # not keyed by.
    trend_index: dict[tuple, dict] = {}
    for row in yb_trends:
        volume = int(re.search(r"yearbook-(\d{4})", row["source"]).group(1))
        if volume != chosen_volume.get(row["year"]):
            continue
        key = (row["year"], row["district_name"], row["county_name"])
        hit = lookup_district(crosswalk, row["district_name"], row["county_name"])
        record = trend_index.setdefault(key, {
            "year": row["year"], "school_year": row["school_year"],
            "district_code": hit["district_code"] if hit else "",
            "district_name": row["district_name"], "county_name": row["county_name"],
            "source": f"yearbook-{volume}-table4",
            "membership_definition": "printed_total",
        })
        record.setdefault(row["measure"], row["value"])

    # The overlap comparison is separate, and only here does name matching
    # matter: failing to match two readings costs a comparison, not a sum.
    readings: dict[tuple, list[dict]] = defaultdict(list)
    for row in yb_trends:
        if row["measure"] != "fall_membership":
            continue
        volume = int(re.search(r"yearbook-(\d{4})", row["source"]).group(1))
        readings[(row["year"], district_key(row["district_name"], row["county_name"]))].append(
            {**row, "volume": volume})

    overlap_rows = []
    for key, entries in readings.items():
        year, _ = key
        by_measure = {"fall_membership": entries}
        chosen = min(entries, key=lambda e: abs(e["volume"] - year))
        # Two volumes reading the same printed figure is two independent OCR
        # passes over one source. Where they disagree, one of them is wrong,
        # and the size of the disagreement measures the OCR directly - against
        # the book itself rather than against NCES.
        fall = by_measure.get("fall_membership", [])
        if len(fall) > 1:
            # Every reading is kept. A dict keyed on the volume let a second
            # reading from the same volume overwrite the first, and two
            # districts sharing a key - Garfield RE-2 and Garfield 16 in the
            # 1987 volume - were then reported as one district whose readings
            # agreed, with a chosen value of 1,724 beside a reading of 173.
            # Agreement means two different volumes reading the same figure;
            # one volume reading two figures under one key is a key collision
            # and is never counted as agreement.
            pairs = sorted((e["volume"], int(e["value"])) for e in fall)
            volumes = [v for v, _ in pairs]
            distinct = {value for _, value in pairs}
            overlap_rows.append({
                "year": year,
                "district_name": chosen["district_name"],
                "county_name": chosen["county_name"],
                "volumes": ";".join(str(v) for v in sorted(set(volumes))),
                "readings": ";".join(f"{v}:{value}" for v, value in pairs),
                "agree": len(distinct) == 1 and len(set(volumes)) == len(volumes),
                "spread": int(max(distinct) - min(distinct)),
                "chosen_volume": chosen["volume"],
                "chosen_value": int(chosen["value"]),
            })

    district_year = sorted(trend_index.values(), key=lambda r: (r["year"], r["district_name"]))

    # 1986-1999 comes from each volume's own grade table rather than its
    # trends table. The ten-year, four-measure Table 4 only exists in the
    # early volumes; from about 1992 the books print a shorter five-year
    # trend instead, and 1988 and 1999 print none at all. The grade table is
    # in every volume and is the better source anyway - summed and compared
    # against NCES it lands within 0.00% in several years.
    #
    # The two sources do not count the same thing, and the column says so.
    # Table 4 prints a district's total fall membership. The grade sums take
    # pre-kindergarten through twelfth grade and leave out special education
    # and ungraded pupils, which Table 4 includes. In 1986 and 1987, where one
    # volume prints both, the grade rule counts 0.7% and 0.8% fewer pupils
    # statewide - and the gap is not even: Denver's is 2.6%, Adams 12's 2.2%,
    # St. Vrain's 2.1%, Boulder Valley's 0.6%. So `membership_definition`
    # names the rule on every row, and `fall_membership_k12` carries
    # kindergarten to twelfth grade alone wherever grades are printed, which
    # includes 1986 and 1987, so the seam can be measured and not only noted.
    covered = {row["year"] for row in district_year}
    grade_totals: dict[tuple, dict] = {}
    k12_by_code: dict[tuple, int] = defaultdict(int)
    for row in yb_grades:
        if row["grade"] in ("SPECIAL_EDUCATION", "UNGRADED"):
            continue
        if row["grade"] != "PK" and row.get("district_code"):
            k12_by_code[(row["year"], row["district_code"])] += row["enrollment"]
        if row["year"] in covered:
            continue
        key = (row["year"], row["district_name"], row["county_name"])
        entry = grade_totals.setdefault(key, {
            "year": row["year"], "school_year": f"{row['year']}-{str(row['year'] + 1)[2:]}",
            "district_code": row.get("district_code", ""),
            "district_name": row["district_name"], "county_name": row["county_name"],
            "fall_membership": 0, "fall_membership_k12": 0,
            "membership_definition": "grades_pk_12",
            "source": f"{row['source']}-grades",
        })
        entry["fall_membership"] += row["enrollment"]
        if row["grade"] != "PK":
            entry["fall_membership_k12"] += row["enrollment"]
    # Table 4 rows in a year that also prints grades get their K-12 count from
    # the same volume's grade table.
    for row in district_year:
        found = k12_by_code.get((row["year"], row.get("district_code") or ""))
        if found is not None and row.get("district_code"):
            row["fall_membership_k12"] = found
    district_year.extend(grade_totals.values())

    # Extend the same series through the modern era by summing the school
    # panel, so one column carries fall membership from 1977 to the present.
    modern_totals: dict[tuple, int] = defaultdict(int)
    modern_k12: dict[tuple, int] = defaultdict(int)
    for row in cde_school:
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED"):
            modern_totals[(row["year"], row["district_code"])] += row["enrollment"]
            if row["grade"] != "PK":
                modern_k12[(row["year"], row["district_code"])] += row["enrollment"]
    for (year, code), value in sorted(modern_totals.items()):
        if not code:
            continue
        district_year.append({
            "year": year, "school_year": f"{year}-{str(year + 1)[2:]}",
            "district_code": code,
            "district_name": modern_names.get((year, code), ""),
            "county_name": "", "fall_membership": value,
            "fall_membership_k12": modern_k12.get((year, code), 0),
            "membership_definition": "grades_pk_12",
            "source": "cde-school-sum",
        })

    # ---- district to county -----------------------------------------------
    #
    # Every analysis that joins a district to a population has to get from a
    # district code to a county, and no single source states it in every year:
    # the yearbooks print a county heading over each block of districts, CDE's
    # school files carry a county column in some years and not others, and the
    # by-district spreadsheets carry none at all. The statements are gathered
    # from wherever they appear and written out once, so the join is made in
    # one place and can be checked.
    #
    # A district can genuinely sit in more than one county. The crosswalk keeps
    # the county stated most often and records the rest rather than choosing
    # silently.
    county_claims: dict[str, Counter] = defaultdict(Counter)
    for row in cde_school + yb_summary:
        code = row.get("district_code") or ""
        county = (row.get("county_name") or "").strip()
        if code and county and not county.upper().startswith("COLORADO BOC"):
            county_claims[code][county.upper()] += 1
    for row in yb_summary:
        # The yearbook rows carry a county but no code; match by name.
        if row.get("county_name") and not row.get("county_name", "").upper().startswith("COLORADO BOC"):
            hit = lookup_district(crosswalk, row["district_name"], row["county_name"])
            if hit:
                county_claims[hit["district_code"]][row["county_name"].strip().upper()] += 1

    district_county = {}
    for code, claims in county_claims.items():
        (best, count), = claims.most_common(1)
        district_county[code] = {
            "district_code": code,
            "county_name": best.title(),
            "statements": sum(claims.values()),
            "agreement": round(count / sum(claims.values()), 4),
            "also_stated": ";".join(sorted(n.title() for n in claims if n != best)),
        }
    write_csv(LOOKUPS / "district-county.csv", sorted(district_county.values(),
              key=lambda r: r["district_code"]),
              ["district_code", "county_name", "statements", "agreement", "also_stated"])
    split = sum(1 for r in district_county.values() if r["also_stated"])
    print(f"\nDistrict to county")
    print(f"  {len(district_county):,} districts placed in a county; "
          f"{split} are stated in more than one")

    # The district tier's county is the crosswalk's wherever the code is
    # known. As printed it was the OCR's: "Kidwa" for Kiowa, "Guray" for
    # Ouray, "Montrase" and "Montr" for Montrose, and six counties spelled in
    # capitals on some rows and title case on others, so a join or a group on
    # county put districts in counties that do not exist or split one county
    # in two. Where no code is known the printed county stays, in title case.
    for row in district_year:
        row["unit_type"] = unit_type(row.get("district_name", ""))
        known = district_county.get(row.get("district_code") or "")
        if known:
            row["county_name"] = known["county_name"]
        elif row.get("county_name"):
            row["county_name"] = row["county_name"].strip().title()
    write_csv(PROCESSED / "district-year.csv", district_year, [
        "year", "school_year", "district_code", "district_name", "county_name", "unit_type",
        "fall_membership", "membership_definition", "fall_membership_k12",
        "closing_day_membership", "average_daily_membership", "adae", "source"])
    if overlap_rows:
        agree = sum(1 for r in overlap_rows if r["agree"])
        print(f"  overlapping district-years: {len(overlap_rows):,}, "
              f"{agree:,} agree exactly ({agree / len(overlap_rows):.1%})")
        write_csv(PROCESSED / "district-year-overlap.csv",
                  sorted(overlap_rows, key=lambda r: (-r["spread"], r["year"])),
                  list(overlap_rows[0].keys()))

    # ---- the yearbook era of the district staffing table ------------------
    #
    # district-teacher-fte-cde.csv is written by pipeline.teacher_fte and
    # covers 2000 onward. The yearbooks carry the same measures for the
    # fourteen years before that, in a table CDE printed as Table 1 in some
    # volumes and Table 2 in others, so they are merged in here - where the
    # district name crosswalk already exists - rather than in a module that
    # knows nothing about yearbooks.
    #
    # One parsed row can land in two different years. The 1999 volume prints
    # Fall 1999 membership beside Fall 1998 teachers, so its school counts
    # belong to 1999 and its staff to 1998; the 1998 volume prints no staff
    # column at all. Each row is therefore split into what it says about its
    # own year and what it says about the staff year, and the two are merged
    # by district.
    staffing: dict[tuple, dict] = {}

    def staffing_row(year: int, row: dict) -> dict:
        hit = lookup_district(crosswalk, row["district_name"], row["county_name"])
        code = hit["district_code"] if hit else ""
        key = (year, code or f"name:{district_key(row['district_name'])}")
        return staffing.setdefault(key, {
            "year": year,
            "district_code": code,
            "district_name": row["district_name"],
            "county_name": row["county_name"],
            "unit_type": unit_type(row["district_name"]),
            "source": row["source"],
        })

    for row in yb_summary:
        own = staffing_row(row["year"], row)
        for key in ("schools_elementary", "schools_middle", "schools_senior",
                    "schools_other", "graduation_rate", "dropout_rate"):
            if row.get(key) is not None:
                own[key] = row[key]
        if row.get("schools_total") is not None:
            own["schools_published"] = row["schools_total"]
        if row.get("enrollment") is not None:
            own["enrollment_published"] = row["enrollment"]

        staff = staffing_row(row["staff_year"], row) if row["staff_year"] != row["year"] else own
        if row.get("teacher_fte") is not None:
            staff["teacher_fte_published"] = row["teacher_fte"]
        for key in ("staff_certificated_fte", "staff_noncertificated_fte",
                    "pupil_teacher_ratio"):
            value = row.get({"staff_certificated_fte": "staff_certificated_fte",
                             "staff_noncertificated_fte": "staff_noncertificated_fte",
                             "pupil_teacher_ratio": "pupil_teacher_ratio"}[key])
            if value is not None:
                staff[key] = value

    matched = sum(1 for r in staffing.values() if r["district_code"])
    print(f"\nDistrict staffing, the yearbook era")
    print(f"  {len(staffing):,} district-years 1986-1999; "
          f"{matched:,} matched to a CDE district code ({matched / len(staffing):.1%})")

    # This step adds the yearbook years to a table pipeline.teacher_fte has
    # already written the modern years into, so it has to read that file
    # before rewriting it - and it must drop the rows it is about to replace
    # first. Without that the step appends to its own output: nine runs of the
    # pipeline had put nine identical copies of every 1986-1999 district-year
    # in the file, 23,931 rows where there are 2,659, and every reader of it
    # multiplied to match. A pipeline that cannot be run twice is not a
    # pipeline, so the guard is on the source, which says who owns each row.
    existing_path = PROCESSED / "district-teacher-fte-cde.csv"
    existing = []
    if existing_path.exists():
        with existing_path.open(encoding="utf-8") as handle:
            existing = [dict(r) for r in csv.DictReader(handle)
                        if not str(r.get("source", "")).startswith("yearbook-")]
            for row in existing:
                row["unit_type"] = unit_type(row.get("district_name", ""))
    columns = ["year", "district_code", "district_name", "county_name", "unit_type",
               "teacher_fte_published", "teacher_fte_school_sum", "teacher_fte_difference",
               "staff_certificated_fte", "staff_noncertificated_fte",
               "pupil_teacher_ratio",
               "schools_published", "schools_elementary", "schools_middle",
               "schools_senior", "schools_other", "schools_in_sum",
               "enrollment_published", "enrollment_school_sum",
               "graduation_rate", "dropout_rate", "source"]
    for row in existing:
        row["schools_in_sum"] = row.pop("schools", "")
    combined = sorted(list(staffing.values()) + existing,
                      key=lambda r: (int(r["year"]), str(r["district_code"]),
                                     str(r["district_name"])))
    filled = 0
    for row in combined:
        stated = (row.get("county_name") or "").strip()
        known = district_county.get(str(row.get("district_code") or ""))
        if not stated and known:
            row["county_name"] = known["county_name"]
            filled += 1
    if filled:
        print(f"  {filled:,} district-years given a county from the crosswalk")
    write_csv(existing_path, combined, columns)
    years = sorted({int(r["year"]) for r in combined})
    print(f"  the table now spans {years[0]}-{years[-1]}")

    # ---- reconciliation --------------------------------------------------
    print("\nReconciling CDE against CCD")
    recon = []
    for year in sorted({r["year"] for r in cde_school}):
        cde_year = {k[1]: v for k, v in cde_totals.items() if k[0] == year}
        ccd_year: dict[str, int] = defaultdict(int)
        ccd_prek = 0
        for row in ccd_enrollment:
            if row["year"] != year or not row["school_code"]:
                continue
            if row["grade"] == "PK":
                ccd_prek += row["enrollment"]
                continue
            ccd_year[row["school_code"]] += row["enrollment"]
        if not ccd_year:
            continue
        cde_prek = sum(r["enrollment"] for r in cde_school
                       if r["year"] == year and r["grade"] == "PK")
        overlap = set(cde_year) & set(ccd_year)
        exact = sum(1 for c in overlap if cde_year[c] == ccd_year[c])
        diffs = sorted(abs(cde_year[c] - ccd_year[c]) for c in overlap)
        recon.append({
            "year": year,
            "cde_schools": len(cde_year),
            "ccd_schools": len(ccd_year),
            "matched": len(overlap),
            "exact_agreement": exact,
            "median_abs_diff": diffs[len(diffs) // 2] if diffs else "",
            "cde_total": sum(cde_year.values()),
            "ccd_total": sum(ccd_year.values()),
            "cde_prek": cde_prek,
            "ccd_prek": ccd_prek,
            "gap_excluding_prek": sum(cde_year.values()) - cde_prek - sum(ccd_year.values()),
        })
        print(f"  {year}: {len(overlap):,}/{len(cde_year):,} matched, "
              f"{exact:,} exact, gap ex-PK {recon[-1]['gap_excluding_prek']:+,}")
    write_csv(PROCESSED / "source-reconciliation.csv", recon, list(recon[0].keys()) if recon else ["year"])

    # ---- district reconciliation, the yearbook tier's real check ----------
    # The row-total checksum can only speak for rows it was given, and it
    # passes on an aggregate row that sums correctly against itself - which is
    # exactly how a "** STATE TOTALS:" row doubled three volumes while every
    # checksum reported clean. Summing each volume's numbered grades and
    # comparing against NCES for the same year is the check that caught it,
    # because NCES is collected independently of the scanned book.
    print("\nReconciling the yearbook tier against NCES")
    district_recon = []
    ccd_by_year: dict[int, int] = defaultdict(int)
    for row in ccd_enrollment:
        if row["grade"] != "UNGRADED":
            ccd_by_year[row["year"]] += row["enrollment"]
    yb_by_year: dict[int, int] = defaultdict(int)
    yb_districts: dict[int, set] = defaultdict(set)
    for row in yb_grades:
        yb_districts[row["year"]].add(row["district_name"])
        if row["grade"] not in ("SPECIAL_EDUCATION", "UNGRADED", "PK"):
            yb_by_year[row["year"]] += row["enrollment"]
    for year in sorted(yb_by_year):
        ccd_total = ccd_by_year.get(year)
        if not ccd_total:
            continue
        diff = yb_by_year[year] - ccd_total
        district_recon.append({
            "year": year,
            "districts": len(yb_districts[year]),
            "yearbook_k12": yb_by_year[year],
            "ccd_k12": ccd_total,
            "difference": diff,
            "pct_difference": round(diff / ccd_total, 6),
        })
        print(f"  {year}: yearbook {yb_by_year[year]:,} vs NCES {ccd_total:,}  {diff:+,} ({diff / ccd_total:+.2%})")
    if district_recon:
        write_csv(PROCESSED / "district-reconciliation.csv", district_recon,
                  list(district_recon[0].keys()))

    report["counts"] = {
        "school_enrollment_rows": len(panel),
        "school_year_rows": len(school_year_rows),
        "schools_in_registry": len(registry),
        "district_grade_rows": len(district_grade),
        "district_year_rows": len(district_year),
        "reconciliation_years": len(recon),
        "years_covered_school": sorted({r["year"] for r in panel})[:1] + sorted({r["year"] for r in panel})[-1:],
        "years_covered_district": sorted({r["year"] for r in district_year})[:1] + sorted({r["year"] for r in district_year})[-1:],
    }
    report["parse_meta"] = {
        "cde_school": cde_school_meta, "cde_teacher": cde_teacher_meta,
        "ccd": ccd_meta, "yearbooks": yb_meta,
    }
    (AUDIT / "normalize-report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\nWrote {AUDIT / 'normalize-report.json'}")


if __name__ == "__main__":
    main()
