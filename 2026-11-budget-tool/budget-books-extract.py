"""
Boulder budget books — extract facts from the page-text dump
============================================================
Reads the JSONL produced by `budget-books-inventory.py --dump-text` and pulls
out the handful of numbers the historical series needs, with the page each one
came from.

    python3 budget-books-extract.py dump.jsonl -o budget-books-extracted.csv

Several dumps can be read at once, which is how OCR'd pages join born-digital
ones -- same shape in, same candidates out:

    python3 budget-books-extract.py dump.jsonl budget-books-ocr.jsonl -o facts.csv

Why regex over prose rather than table parsing
----------------------------------------------
The figures are not in tables. Every budget book states them in a sentence:

    "The total 2026 Approved Budget is $521.0 million across all funds,
     including a 2026 Operating Budget of $407.7 million and 2026 Capital
     Budget of $113.3 million."
    "The 2023 Approved Budget includes a total city staffing level of
     1,540.09 full-time equivalents (FTEs)."

That is far more tractable than reconstructing table geometry across 22 years
of changing layouts — but it means the phrasing shifts book to book, so each
fact carries several patterns and the ones that match nothing are reported
rather than silently dropped.

PDF text extraction mangles numbers
-----------------------------------
Real examples from this corpus: "1, 451", "1,548. 28", "$ 407.7", "full- time".
Every numeric pattern therefore tolerates internal whitespace, and `to_number`
strips it before parsing. A pattern written against clean text will silently
miss most years.

Output is CANDIDATES, not truth
-------------------------------
Each row carries the page and the surrounding sentence so a human can confirm
it. Where a year yields conflicting values the script reports all of them and
flags the year rather than picking one.
"""

import argparse
import collections
import csv
import json
import re
import sys

# Tolerate the internal whitespace that PDF extraction injects into numbers.
NUM = r'([\d][\d,\.\s]{0,14}\d)'


def to_number(s):
    s = re.sub(r'[\s]', '', s).rstrip('.').replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def plausible(lo, hi):
    return lambda v: v is not None and lo <= v <= hi


# measure -> (patterns, plausibility test, unit)
FACTS = {
    # The gap before "budget" must not swallow "operating" or "capital".
    # Without the lookahead, "The total 2025 Approved OPERATING Budget is
    # $399.3 million" was captured as the 2025 TOTAL budget — off by $190M
    # against the real $589.3M, and wrong in a way that looks plausible.
    "budget_total": (
        [r'total\s+\d{4}(?:(?!operating|capital)[^.$]){0,40}budget is\s*\$\s*' + NUM + r'\s*million',
         r'total annual budget of\s*\$\s*' + NUM + r'\s*million',
         r'total budget(?:(?!operating|capital)[^.$]){0,30}\$\s*' + NUM + r'\s*million'],
        plausible(150, 900), "musd"),
    "budget_operating": (
        [r'operating budget (?:of|is)\s*\$\s*' + NUM + r'\s*million',
         r'total\s+\d{4}[^.$]{0,40}operating budget is\s*\$\s*' + NUM + r'\s*million'],
        plausible(100, 700), "musd"),
    "budget_capital": (
        [r'capital budget (?:of|is)\s*\$\s*' + NUM + r'\s*million'],
        plausible(20, 400), "musd"),
    "staffing_fte": (
        [r'total city staffing level of\s*' + NUM,
         r'staffing level of\s*' + NUM + r'\s*(?:full|FTE)',
         r'includes a total[^.]{0,40}staffing level of\s*' + NUM,
         NUM + r'\s*FULL[- ]TIME EQUIVALENTS'],
        plausible(800, 2500), "fte"),
}


# --------------------------------------------------------------------------
# Pre-2017 books. Three differences from the modern ones force a separate pass:
#
#   * The year is in the SENTENCE, not the book. The 2005 book states 2004's
#     total for comparison, and the 2006-2007 biennial book states 2006 — so
#     taking the year from the filename would misfile both.
#   * Figures are whole dollars or thousands, not "$N million".
#   * The richest source is a summary block rather than prose:
#         CITY OF BOULDER 2006 BUDGET (in $1,000s)
#         TOTAL BUDGET $200,100   CAPITAL BUDGET $29,453
#         OPERATING BUDGET (including debt service) $170,647
#         GENERAL FUND $71,266
#     which yields four measures at once and self-checks, since capital plus
#     operating equals the total.
# --------------------------------------------------------------------------
# The header arrives mangled in different ways per book. 2006 extracts as
# "CITY OF BOULDER 2006 BUDGET (in $1,000s)", but 2008 as "CITY OFBOULDER
# 2008BUDGET in $1,000s)" — spaces dropped inside words and the OPENING PAREN
# missing entirely. Requiring "(in $1,000s)" silently lost 2008's whole block,
# which is the only place that book states its citywide total. Hence \s* between
# every token and an optional paren.
LEGACY_BLOCK = re.compile(
    r'CITY\s*OF\s*BOULDER\s*(20\d\d)\s*BUDGET\s*\(?\s*in\s*\$1,?000s?\)(.{0,340})',
    re.I | re.S)
# The same block, re-titled. From 2012 the books head it "Figure 5-01: 2014
# Annual Budget (in $1,000s)" (2012 and 2013: "Overview of 2012 Approved
# Budget") and drop "CITY OF BOULDER" entirely. The CONTENT is unchanged —
# total, operating, capital, general fund, dedicated funds — so both headers
# feed the same arithmetic reader below.
OVERVIEW_BLOCK = re.compile(
    r'Figure\s*\d[\-\s]*0?\d\s*:?\s*(?:Overview of\s*)?(20\d\d)\s*'
    r'(?:Annual|Approved|Recommended)\s*Budget\b[^\n]{0,24}?(?:in\s*\$?\s*1,?\s?000s?\)?)?(.{0,300})',
    re.I | re.S)
LEGACY_BLOCK_FIELDS = [
    ("TOTAL BUDGET", "budget_total"),
    ("CAPITAL BUDGET", "budget_capital"),
    ("OPERATING BUDGET", "budget_operating"),
    ("GENERAL FUND", "budget_general_fund"),
]
LEGACY_STATED = re.compile(
    r'total\s+(20\d\d)\s+budget for the City of Boulder is\s*\$\s*([\d,]+)', re.I)
LEGACY_PRIOR = re.compile(
    r'(20\d\d)\s+budget of\s*\$\s*([\d,]+)', re.I)
LEGACY_MILLIONS = re.compile(
    r'(20\d\d)\s+(?:Annual|Approved|Recommended)\s+Budget\s+totals\s*\$\s*([\d,.]+)\s*million', re.I)
# "The 2011 budget totals $231,030,000" -- the same sentence to the dollar rather
# than rounded to the million, which is how the 2011 book states the one figure
# nothing else in the corpus provides. The length floor is what separates a whole
# dollar amount from the "$255 million" form above; it must not also match the
# City Manager's "total annual budget of $316,771,328", which in 2014 and 2015
# names a figure $2-3M away from the book's own structural total and in 2014
# calls the citywide total an OPERATING budget.
LEGACY_DOLLARS = re.compile(
    r'(20\d\d)\s+(?:Annual\s+|Approved\s+|Recommended\s+)?budget\s+totals\s*\$\s*'
    r'([\d][\d,\.\s]{9,17}\d)', re.I)


def _first_offset(seg, value):
    """Where `value` first appears in `seg`, however its separator was mangled.

    The digits are reliable; the punctuation between them is not ("130, 862",
    "214.,979", "80,466120,021"). So match on the digit run and allow up to two
    junk characters where the thousands separator belongs.
    """
    d = str(int(value))
    pat = re.escape(d[:-3]) + r'[^\d]{0,2}' + re.escape(d[-3:])
    m = re.search(pat, seg)
    return m.start() if m else len(seg)


def extract_legacy(rows):
    out = []

    def emit(year, measure, value, unit, r, ctx):
        out.append({"year": year, "measure": measure, "value": value, "unit": unit,
                    "file": r["file"], "page": r["page"],
                    "context": re.sub(r'\s+', ' ', ctx)[:190]})

    for r in rows:
        flat = re.sub(r'\s+', ' ', r['text'])

        for m in list(LEGACY_BLOCK.finditer(flat)) + list(OVERVIEW_BLOCK.finditer(flat)):
            yr, seg = int(m.group(1)), m.group(2)
            # Labels are too mangled to anchor on: 2008 gives "CAPITAL
            # BUDGETOPERATING BUDGET" as one run and omits the $ before its
            # total, and 2006 lists dedicated before general fund while 2008
            # reverses them. The ARITHMETIC is unambiguous where the labels are
            # not, and it doubles as validation:
            #     capital + operating   = total
            #     general + dedicated   = operating
            # Both identities hold in every block in this corpus (2005, 2006,
            # 2008), and capital < operating and general < dedicated throughout.
            # The thousands separator is not reliably a comma. 2012 extracts its
            # three figures as "238) 960", "214.,979" and "23,,981", so accept
            # one or two stray punctuation marks where the comma belongs. A
            # spurious match cannot survive: "$1,000s" yields exactly 1000 and is
            # excluded by the strict >, and anything else has to find a partner
            # that sums to the total before a single value is emitted.
            nums = [to_number(re.sub(r'[^\d]', '', x))
                    for x in re.findall(r'\d{1,3}[,\.\)]{1,2}\s?\d{3}', seg)]
            nums = sorted({n for n in nums if n and n > 1000}, reverse=True)
            if len(nums) < 3:
                continue
            total = nums[0]
            rest = nums[1:]
            pair = next(((a, b) for i, a in enumerate(rest) for b in rest[i + 1:]
                         if abs(a + b - total) < 1), None)
            if not pair:
                continue
            operating, capital = max(pair), min(pair)
            emit(yr, "budget_total", round(total / 1000.0, 3), "musd", r, m.group()[:190])
            emit(yr, "budget_capital", round(capital / 1000.0, 3), "musd", r, m.group()[:190])
            emit(yr, "budget_operating", round(operating / 1000.0, 3), "musd", r, m.group()[:190])
            # The block splits operating into a General Fund half and a Dedicated
            # Funds half. That General Fund figure is NOT the headline General
            # Fund the modern books quote -- it runs about 12% lower, because the
            # headline one adds transfers out and the .15% sales tax allocation.
            # Hence the distinct measure names: mixing them fakes a step change.
            inner = [n for n in rest if n not in (operating, capital)]
            gpair = next(((a, b) for i, a in enumerate(inner) for b in inner[i + 1:]
                          if abs(a + b - operating) < 1), None)
            if gpair:
                # Which half is which cannot be settled by size: the General Fund
                # is the smaller half every year through 2016 and the LARGER one
                # in 2017 (130,862 against 129,815). Nor by position -- 2005
                # prints dedicated first, 2008 general first. What does hold is
                # that the two labels and the two figures appear in the SAME
                # order, even where extraction fuses them ("GENERALDEDICATED
                # FUNDFUNDS 80,466120,021"), so zip the sequences.
                labels = [w.group(1).lower() for w in
                          re.finditer(r'(GENERAL|DEDICATED)', seg, re.I)]
                order = sorted(gpair, key=lambda v: _first_offset(seg, v))
                if sorted(labels) == ["dedicated", "general"]:
                    half = dict(zip(labels, order))
                    emit(yr, "budget_operating_general",
                         round(half["general"] / 1000.0, 3), "musd", r, m.group()[:190])
                    emit(yr, "budget_operating_dedicated",
                         round(half["dedicated"] / 1000.0, 3), "musd", r, m.group()[:190])

        # "The total 2005 budget ... is $196,167,000" — whole dollars.
        for m in LEGACY_STATED.finditer(flat):
            v = to_number(m.group(2))
            if v and v > 1e6:
                emit(int(m.group(1)), "budget_total", round(v / 1e6, 3), "musd",
                     r, flat[max(0, m.start() - 60):m.start() + 150])
        # The same sentence usually names the PRIOR year's total for comparison.
        for m in LEGACY_PRIOR.finditer(flat):
            v = to_number(m.group(2))
            if v and v > 1e6:
                emit(int(m.group(1)), "budget_total", round(v / 1e6, 3), "musd",
                     r, flat[max(0, m.start() - 90):m.start() + 120])

        for m in LEGACY_DOLLARS.finditer(flat):
            v = to_number(m.group(2))
            if v and 1e8 <= v <= 1e9:
                emit(int(m.group(1)), "budget_total", round(v / 1e6, 3), "musd",
                     r, flat[max(0, m.start() - 60):m.start() + 170])

        # "The 2013 Annual Budget totals $255 million"
        for m in LEGACY_MILLIONS.finditer(flat):
            v = to_number(m.group(2))
            if v and 100 <= v <= 900:
                emit(int(m.group(1)), "budget_total", v, "musd",
                     r, flat[max(0, m.start() - 60):m.start() + 170])
    return out


# --------------------------------------------------------------------------
# Multi-year tables. The legacy books do something the modern ones don't: every
# summary table is three or four years WIDE, with the basis of each column in
# its header:
#
#     CITY OF BOULDER / SUMMARY OF USES OF FUNDS (in $1,000s)
#         2006      2007       2008       2009
#       ACTUAL   APPROVED   APPROVED   PROJECTED
#     Total General Fund Uses  89,123  89,650  94,238  95,883
#
# One page therefore carries four years, which is how 2007, 2009 and 2010 get
# values at all: all three exist only as scanned PDFs, and a neighbouring book
# states each of them in its own comparison columns -- the 2008 book carries
# 2007, the 2011 book carries 2009 and 2010. Reading these tables is worth more
# than any amount of OCR, and it is free.
#
# Each entry is gated on the table's TITLE, because the row label alone is not
# distinctive enough -- "TOTALS" appears in dozens of tables, and "TOTAL General
# Fund" means revenue in a Sources table and expenditure in a Uses one.
# --------------------------------------------------------------------------
MULTIYEAR_TABLES = [
    (r'SUMMARY\s*OF\s*SOURCES\s*OF\s*FUNDS', r'TOTAL\s*General\s*Fund(?!\s*Uses)',
     "budget_general_fund_revenue", "thousands", plausible(40, 400)),
    (r'SUMMARY\s*OF\s*USES\s*OF\s*FUNDS', r'Total\s*General\s*Fund\s*Uses',
     "budget_general_fund", "thousands", plausible(40, 400)),
    # Two headings for the same table. The pre-2012 books call it "SUMMARY OF
    # STANDARD FTEs"; from 2012 it is "Table 4-6: Staffing Levels in Standard
    # FTEs by Department". Gating on the narrower wording lost 2012 and 2013,
    # which are the years that close the gap to 2016.
    (r'STANDARD\s*FTEs?|STANDARD\s*FULL\s*TIME', r'TOTALS?|Total\b',
     "staffing_fte", "fte", plausible(800, 2500)),
]
# Years and basis words both arrive fused in the 2008 book ("2006200720082009",
# "ACTUALAPPROVEDAPPROVEDPROJECTED"), so neither pattern can require whitespace.
# Demanding consecutive years is what keeps \s* from matching arbitrary digits.
YEAR_RUN = re.compile(r'((?:19|20)\d\d)\s*((?:19|20)\d\d)\s*((?:19|20)\d\d)\s*((?:19|20)\d\d)?')
BASIS_WORD = re.compile(r'(ACTUAL|APPROVED|PROJECTED|PROPOSED|REVISED|RECOMMENDED)', re.I)
YEAR_BASIS_PAIRS = re.compile(
    r'((?:19|20)\d\d)\s*\|?\s*(ACTUAL|APPROVED|PROJECTED|PROPOSED|REVISED|RECOMMENDED)', re.I)
BASIS_MAP = {"actual": "actual", "approved": "adopted", "projected": "projected",
             "proposed": "recommended", "revised": "revised_projection",
             "recommended": "recommended"}

# A thousands table and an FTE table have different numeric grammar, and one
# pattern for both silently corrupts one of them.
#
#   thousands: every figure is an integer of at least four digits, and the
#     separator may come out as a comma or a PERIOD -- the 2011 book prints
#     "105, 848 96, 713 100. 449" in one row. Accept either and then keep only
#     the digits; reading that period as a decimal point turns $100,449 thousand
#     into $100.449 and loses the row. A bare space is NOT accepted as a
#     separator, even though the digits are often spaced: with it, that same row
#     matched "96, 713 100. 449" as the single number 96713100.449, because
#     " 100" is a space followed by three digits.
#   fte: the period IS a decimal point, two digits after it, and the figures fuse
#     into each other completely ("1, 218. 841, 251. 341, 281. 1729. 83" is four
#     values). Allowing a period in the thousands group here would run one match
#     across the whole line.
NUM_THOUSANDS = re.compile(r'\d{1,3}(?:[,\.]\s?\d{3})+')
# Four integer digits with no separator at all: the 2012 book's totals row is
# "TOTAL 1248. 24 1230. 50 1243. 20", where extraction dropped the commas the
# 2013 book keeps ("1, 231.25"). Requiring a separator read the 2012 table as
# having no plausible totals row, so that book's own figures were replaced by
# the 2013 book's later restatement of them.
NUM_FTE = re.compile(r'\d{1,4}(?:[,\s]\s?\d{3})*\.\s?\d{1,2}')


def read_numbers(text, kind):
    if kind == "fte":
        return [to_number(re.sub(r'[,\s]', '', m.group())) for m in NUM_FTE.finditer(text)]
    return [float(re.sub(r'\D', '', m.group())) / 1000.0
            for m in NUM_THOUSANDS.finditer(text)]


def table_columns(text):
    """The (year, basis) of each column, or None if this page has no such header.

    Two header shapes, because the two ways of reading a PDF flatten a table
    differently. pypdf reads by position and so gives the years as one run and
    the basis words as another:

        2006200720082009  ACTUALAPPROVEDAPPROVEDPROJECTED

    OCR'd markdown gives a pipe table, which zips them per column instead:

        | Department | 2008 APPROVED | 2009 APPROVED | 2010 APPROVED | VAR |

    The stacked form is tried first: it is unambiguous when it matches, whereas
    the interleaved pattern would read the fused example above as the single
    pair (2009, actual) -- 2009 is PROJECTED there, not actual. Requiring three
    pairs is what stops that one wrong pair from ever being used.
    """
    for ym in YEAR_RUN.finditer(text):
        years = [int(y) for y in ym.groups() if y]
        if any(years[i] + 1 != years[i + 1] for i in range(len(years) - 1)):
            continue
        bases = [BASIS_MAP[w.lower()] for w in
                 BASIS_WORD.findall(text[ym.end(): ym.end() + 140])]
        if len(bases) < len(years):
            continue
        return list(zip(years, bases[:len(years)]))

    pairs = [(int(y), BASIS_MAP[b.lower()]) for y, b in YEAR_BASIS_PAIRS.findall(text)]
    if len(pairs) >= 3 and all(pairs[i][0] + 1 == pairs[i + 1][0]
                               for i in range(len(pairs) - 1)):
        return pairs
    return None


def extract_multiyear(rows):
    out = []
    for r in rows:
        flat = re.sub(r'\s+', ' ', r['text'])
        for title, label, measure, kind, ok in MULTIYEAR_TABLES:
            if not re.search(title, flat, re.I):
                continue
            cols = table_columns(flat)
            if not cols:
                continue
            for lm in re.finditer(label, flat, re.I):
                vals = read_numbers(flat[lm.end(): lm.end() + 110], kind)[:len(cols)]
                # The first row whose every figure is plausible wins. This is what
                # lets the loop tolerate a stray "TOTAL" in a department name: a
                # wrong row fails the range test instead of poisoning the output.
                if len(vals) < 3 or not all(ok(v) for v in vals):
                    continue
                for (yr, basis), v in zip(cols, vals):
                    out.append({"year": yr, "measure": measure, "basis": basis,
                                "value": round(v, 3),
                                "unit": "fte" if kind == "fte" else "musd",
                                "file": r["file"], "page": r["page"],
                                "context": re.sub(r'\s+', ' ',
                                                 flat[lm.start(): lm.end() + 90])[:190]})
                break
    return out


# --------------------------------------------------------------------------
# The citywide spending pie. Every book states where the money went by
# DEPARTMENT, as a pie with the dollars and the share printed on each slice.
# This is the only expense breakdown that reaches back to 2005 -- the
# Personnel/Capital/Operating/Debt-Service split is an OpenGov construct that
# appears in two books in this whole corpus.
#
# THREE PIES SHARE ONE HEADING, AND THAT IS THE TRAP
# --------------------------------------------------
# A book prints the same words, "2005 Uses of Funds Total = $NN (in $1,000s)",
# over three different scopes:
#
#     citywide             total = that year's citywide budget  ($196,167 in 2005)
#     citywide, no utils   says "without Utilities" / "excluding Utilities"
#     General Fund         total = that year's General Fund     ($80,059 in 2005)
#
# Nothing in the heading separates them; the scope appears only in surrounding
# prose, worded differently in every book. Reading them as one series is not a
# subtle error: the 2005 CITYWIDE pie puts Parks & Recreation at $21.1M and the
# 2005 GENERAL FUND pie puts Parks at $3.9M, because most of Parks is funded
# outside the General Fund. An earlier version of this reader recorded both
# under the same measure name.
#
# So scope is settled arithmetically, against the citywide total this same run
# extracted for that year. A pie whose total matches is citywide; anything else
# is REPORTED with its total instead of recorded, so an unrecognised pie shows
# up as a line of output rather than as silently wrong data.
#
# ONE SLICE ORDER
# ---------------
# Every readable pie prints "Police $22,680 12%" -- label, value, share. The 2018
# book prints "Public Works 44% 170,485" instead, which is why 2018 is among the
# unreadable years below rather than a supported format; see _pie_slices.
#
# AND THREE PIES CANNOT BE READ AT ALL
# ------------------------------------
# 2011 and 2012 come out of the PDF interleaved beyond repair -- 2012's reads
# "Pol ice 29, 593 Comm Planning Parks and Rec 12% and SUSt 24, 229 S/, 644
# 10%", in which the 32% belongs to Public Works and "577,340" is $77,340 with a
# stray digit. 2019 prints its total and leaves the slices in an image. The sum
# gate rejects all three, which is the point: pairing those labels to those
# values would be guessing, and a wrong guess does not look wrong -- it just
# moves Police's budget to Open Space.
# --------------------------------------------------------------------------
# The "(in $1,000s)" that sits between the heading and the total contains a $,
# so the gap here must not exclude one. Requiring no $ hid 2012 and 2019
# entirely from an earlier pass.
# The year is captured from BEFORE the heading ("2006 Uses of Funds"), not from
# the filename. The 2006-2007 biennial book is named for 2007 but its pie is
# 2006's, so a filename fallback files that pie under a year whose citywide total
# does not exist -- and the scope test then discards a perfectly good pie. 2005
# survived the same bug only because its filename happened to be right.
DEPT_PIE = re.compile(
    r'(?:(20\d\d)\s+)?(?:Citywide\s+)?(?:Expenses|Expenditures|Uses)(?:\s+of\s+Funds)?\b'
    r'[^\n]{0,90}?TOTAL\s*=\s*\$?\s*([\d][\d,\.\s]{4,14}\d)', re.I)
# The thousands group is optional, not required. Demanding one drops every
# slice under $1,000 thousand -- Arts is $440 in 2005 and $451 in 2006 -- and
# that loss is small enough to slip through a percentage-based sum gate, which
# is exactly how it went unnoticed once already.
DEPT_SLICE_VALUE_FIRST = re.compile(
    r"([A-Za-z][A-Za-z&/\.,'\- ]{2,46}?)\s*\$?\s*(\d{1,3}(?:[,\.]\s?\d{3})*)"
    r"\s*\(?\s*<?\s*\d{1,2}(?:\.\d)?\s*%")
DEPT_EX_UTILITIES = re.compile(r'with(?:out)?\s+utilit|excluding\s+utilit', re.I)
# A FLAT tolerance, not a percentage of the total. A percentage scales with the
# pie and so grows past the size of the smallest slice: 0.5% of the 2005 pie is
# $981 thousand, which quietly admitted a reading that had dropped the $440 Arts
# slice entirely. Measured across the nine readable years, every pie lands within
# $1 thousand of its printed total -- the city rounds slices to the thousand --
# so anything past a few thousand means a slice is missing, whatever the pie's
# size.
TOL_ABS = 3_000


def slug(label):
    """Match on the letters alone. PDF extraction inserts spaces inside words:
    the 2005 pie prints "De bt", "Fir e", "General Governm ent"."""
    return re.sub(r'[^a-z0-9]', '', label.lower())


def _pie_slices(seg, total):
    """The pie's slices, or None if they do not add up to the printed total.

    ONE slice order, "Police $22,680 12%". The 2018 book prints the reverse and a
    pattern for it was tried here; it recovered no year this one misses, and it
    broke 2020. After that pie's eleven real slices the book lists sub-components
    with shares and NO values ("Electric Utility Development - 1% Sustainability
    - 1% Police - 10%"), which the reversed pattern read as thirteen slices, two
    worth nothing. They summed correctly and won on slice count, so 2020 gained
    Transportation and Utilities at $0 -- printed next to 2021's $30.8M and
    $84.9M, that reads as a collapse that never happened.
    """
    got = [(lab.strip(), to_number(re.sub(r'\D', '', val)))
           for lab, val in DEPT_SLICE_VALUE_FIRST.findall(seg)]
    # The floor is on the SHARE, not the dollars, because the early books print
    # thousands and the later ones whole dollars. No real department line is a
    # ten-thousandth of the city's spending; a match that small is a legend entry
    # whose percentage was read as its value.
    got = [(lab, v) for lab, v in got if v and v / total >= 0.0001]
    # A pie is whole or it is not used. TOL_ABS covers the city rounding a slice
    # to the nearest thousand; it does not cover a missing slice, which is the
    # failure this gate exists to catch.
    if got and abs(sum(v for _l, v in got) - total) <= TOL_ABS:
        return got
    return None


def extract_dept_pie(rows, citywide_totals):
    """Slices of the CITYWIDE pie only.

    `citywide_totals` is {year: value in $M} taken from the totals this same run
    extracted, and is what settles the scope of an otherwise ambiguous heading.
    """
    out, rejected = [], []
    for r in rows:
        flat = re.sub(r'\s+', ' ', r['text'])
        for m in DEPT_PIE.finditer(flat):
            total = to_number(re.sub(r'[^\d]', '', m.group(2)))
            if not total or total < 50_000:
                continue
            # The early books print the pie in thousands, the later ones in
            # whole dollars, and both appear with the same heading.
            in_thousands = total < 1_000_000
            musd = total / (1000.0 if in_thousands else 1e6)
            ym = m.group(1) or (re.search(r'\b(20\d\d)\b', m.group()) or [None])
            yr = int(m.group(1)) if m.group(1) else (
                int(ym.group(1)) if hasattr(ym, 'group') else r['year'])
            head = flat[max(0, m.start() - 260):m.end()]
            known = citywide_totals.get(yr)
            why = None
            if DEPT_EX_UTILITIES.search(head):
                why = "excludes utilities"
            elif known is None:
                why = "no citywide total known for this year"
            elif abs(musd - known) > 1.5:
                why = f"total {musd:,.1f}M is not the citywide {known:,.1f}M"
            slices = None if why else _pie_slices(flat[m.end(): m.end() + 1400], total)
            if why or not slices:
                rejected.append((yr, r['file'], r['page'], round(musd, 1),
                                 why or "slices do not sum to the printed total"))
                continue
            for lab, v in slices:
                out.append({"year": yr, "measure": "dept_" + slug(lab),
                            "value": round(v / (1000.0 if in_thousands else 1e6), 3),
                            "unit": "musd", "file": r["file"], "page": r["page"],
                            "context": f"pie slice as printed: {lab!r} "
                                       f"({100 * v / total:.1f}% of {total:,.0f})"})
    return out, rejected


def extract(rows):
    out = []
    for r in rows:
        flat = re.sub(r'\s+', ' ', r['text'])
        for measure, (pats, ok, unit) in FACTS.items():
            for pat in pats:
                for m in re.finditer(pat, flat, re.I):
                    v = to_number(m.group(1))
                    if not ok(v):
                        continue
                    ctx = flat[max(0, m.start() - 70): m.start() + 110].strip()
                    out.append({
                        "year": r["year"], "measure": measure, "value": v, "unit": unit,
                        "file": r["file"], "page": r["page"],
                        "context": re.sub(r'\s+', ' ', ctx),
                    })
    return out


def main():
    ap = argparse.ArgumentParser(description="Extract budget facts from a page-text dump.")
    ap.add_argument("dump", nargs="+",
                    help="one or more JSONL dumps: born-digital pages from "
                         "budget-books-inventory.py --dump-text, OCR'd pages from "
                         "budget-books-ocr.py, or both together")
    ap.add_argument("-o", "--out", default="budget-books-extracted.csv")
    args = ap.parse_args()

    rows = []
    for path in args.dump:
        with open(path) as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    # --extract writes excerpt PDFs beside the originals; if they were scanned
    # too, every page appears twice. Drop them.
    rows = [r for r in rows if 'excerpt' not in r['file'].lower()]
    if not rows:
        sys.exit("no usable pages in the dump")

    base = extract(rows) + extract_legacy(rows) + extract_multiyear(rows)
    # The pie reader needs each year's citywide total to tell three
    # identically-headed pies apart, so it runs last, on what the rest found.
    citywide = {}
    for f in base:
        if f["measure"] == "budget_total":
            citywide.setdefault(f["year"], f["value"])
    dept, dept_rejected = extract_dept_pie(rows, citywide)
    found = base + dept

    # Collapse duplicates (the same sentence can appear in a summary and again
    # in a detail section), then flag any year where a measure disagrees.
    best, conflicts = {}, collections.defaultdict(set)
    for f in found:
        f.setdefault("basis", "")
        key = (f["year"], f["measure"], f["basis"])
        conflicts[key].add(f["value"])
        best.setdefault(key, f)

    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "year", "measure", "basis", "value", "unit", "file", "page",
            "n_values", "conflict", "context"])
        w.writeheader()
        for key in sorted(best, key=lambda k: (k[0], k[1], k[2])):
            row = dict(best[key])
            vals = conflicts[key]
            row["n_values"] = len(vals)
            row["conflict"] = "" if len(vals) == 1 else " | ".join(str(v) for v in sorted(vals))
            w.writerow(row)

    years = sorted({r["year"] for r in rows})
    print(f"read {len(rows)} pages, {years[0]}-{years[-1]}")
    print(f"wrote {args.out}: {len(best)} facts\n")
    for measure in list(FACTS) + [t[2] for t in MULTIYEAR_TABLES] + [
            "budget_operating_general", "budget_operating_dedicated"]:
        got = sorted({y for (y, m, _b) in best if m == measure})
        miss = [y for y in years if y not in got]
        print(f"  {measure:<18} {len(got):>2} years  {got}")
        if miss:
            print(f"  {'':<18}    missing: {miss}")
    dept_years = sorted({y for (y, mm, _b) in best if mm.startswith("dept_")})
    print(f"  {'departmental pie':<18} {len(dept_years):>2} years  {dept_years}")
    for yr, f, pg, musd, why in sorted(dept_rejected):
        print(f"  {'':<18}    skipped {yr} pie ({f[:26]} p{pg}, {musd:,.1f}M): {why}")

    flagged = sorted({k[0] for k, v in conflicts.items() if len(v) > 1})
    if flagged:
        print(f"\n  years with conflicting values (check the CSV): {flagged}")


if __name__ == "__main__":
    main()
