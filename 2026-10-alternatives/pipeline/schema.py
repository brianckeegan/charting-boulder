"""Canonical columns and the normalizing rules every parser funnels into.

One place for the decisions that would otherwise be re-made, differently, in
each parser. Each rule here traces to a finding in audit/proof-run.md.
"""

from __future__ import annotations

import re

# Canonical grade codes, in order. PK is CDE-only: NCES CCD publishes no
# pre-kindergarten rows for Colorado in any year (finding A8).
GRADES = ["PK", "K"] + [str(g) for g in range(1, 13)]

# Extra categories the district yearbooks report alongside the numbered
# grades. They are kept as their own categories and never folded into a grade.
EXTRA_CATEGORIES = ["SPECIAL_EDUCATION", "UNGRADED"]

SCHOOL_ENROLLMENT_COLUMNS = [
    "year", "ncessch", "school_code", "district_code", "district_name",
    "school_name", "grade", "enrollment", "source",
]

DISTRICT_ENROLLMENT_COLUMNS = [
    "year", "district_code", "district_name", "county_name",
    "grade", "enrollment", "source",
]

# CCD grade codes: -1 pre-K, 0 kindergarten, 1-12 graded, 13 grade 13,
# 14 ungraded, 15 adult, 99 school total.
CCD_GRADE = {-1: "PK", 0: "K", **{g: str(g) for g in range(1, 13)}, 14: "UNGRADED"}


def normalize_grade(label: str) -> str | None:
    """Map a source column header onto a canonical grade code.

    Three source quirks, all from finding A5 and the yearbook tables:
      - grades are written as ordinals: "1st" ... "12th";
      - kindergarten arrives split as "Half-Day K" and "Full-Day K", and both
        map to K so the caller can sum them;
      - the yearbooks add "SPEC EDUC" and "UNGR PGRD" columns.
    """
    raw = str(label).strip()
    # A spreadsheet reader turns a numeric header into a float, so the column
    # for grade 1 arrives as "1.0". Stripping punctuation first would make
    # that "10" - a silent off-by-nine that puts first-graders in year ten.
    # Drop the trailing ".0" before anything else touches the string.
    if re.fullmatch(r"\d{1,2}\.0", raw):
        raw = raw[:-2]
    s = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if not s:
        return None
    if s in {"PK", "PREK", "P", "PRESCHOOL", "PREKINDERGARTEN"}:
        return "PK"
    if s in {"K", "KG", "KINDER", "KINDERGARTEN", "HALFDAYK", "FULLDAYK", "HDK", "FDK"}:
        return "K"
    if s.startswith("SPEC"):
        return "SPECIAL_EDUCATION"
    if s.startswith("UNGR") or s.startswith("PGRD"):
        return "UNGRADED"
    match = re.fullmatch(r"(?:GRADE|GR)?0*(\d{1,2})(?:ST|ND|RD|TH)?", s)
    if match and 1 <= int(match.group(1)) <= 12:
        return str(int(match.group(1)))
    return None


def normalize_code(value: object, width: int = 4) -> str:
    """Codes are zero-padded strings, never numbers (finding A6).

    pandas reads a numeric-looking code as a float, so "0010" arrives as
    10.0. Getting this wrong silently destroys every join in the archive.
    """
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    text = re.sub(r"[^0-9A-Za-z]", "", text)
    return text.zfill(width) if text.isdigit() else text


def normalize_ccd_state_code(raw: str | None) -> str:
    """CCD's state school id changed shape in 2016 (finding A7).

    Through 2015 it is a bare four-digit CDE school code ("1608"); from 2016
    it is "<district>-<school>" ("0520-1608"). Taking the part after the
    hyphen spans both eras. A crosswalk that assumes one shape matches
    nothing on the other side of the break.
    """
    text = (raw or "").strip()
    return normalize_code(text.split("-")[-1]) if text else ""


def parse_count(value: object) -> int | None:
    """A cell to an integer, or None where it is missing.

    Empty, "-", "*" and "N/A" are missing. CCD uses negative values as
    missing-data sentinels (finding A8), so those are missing too - summing
    them would silently reduce a school's total.
    """
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "*", "N/A", "n/a", "None", "nan", "."}:
        return None
    try:
        number = int(float(text))
    except (TypeError, ValueError):
        return None
    return None if number < 0 else number


def parse_decimal(value: object) -> float | None:
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "*", "N/A", "n/a", "None", "nan", "."}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return None if number < 0 else number


def usable_coordinate(latitude: object, longitude: object) -> bool:
    """Reject the sentinel coordinates early CCD years carry (finding A12).

    Colorado sits near 37-41N, 102-109W. A latitude of -2.0 is a placeholder,
    not a place, and carrying it into a map puts a school in the Atlantic.
    """
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return False
    return 30.0 < lat < 45.0 and -115.0 < lon < -100.0
