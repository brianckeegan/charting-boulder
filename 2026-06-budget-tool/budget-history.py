"""
Boulder city budget — historical series builder
===============================================
Emits a tidy long CSV of the City of Boulder's budget totals, major revenues and
staffing changes, plus a chart-ready wide pivot, a provenance sidecar and a data
dictionary.

    python3 budget-history.py

Outputs (written next to this script):
    budget-history.csv              tidy long — one row per (year, measure, basis)
    budget-history-wide.csv         chart-ready pivot of the headline series
    budget-history-provenance.csv   one row per source document
    budget-history-data-dictionary.md

WHY THE VALUES ARE EMBEDDED IN THIS FILE
----------------------------------------
Unlike the OEWS/QCEW pipelines in this repo, there is no bulk download to parse.
Boulder publishes these figures inside council study-session packets, budget
presentations and press releases — narrative PDFs and slide decks, with the
numbers in prose and chart images rather than tables. The OpenGov budget book is
a JavaScript application with no public data endpoint (probed 2026-09-21: the
documented REST paths 404).

So this script IS the transcription record: every value below carries the
`src` id of the document it was read from, and `budget-history-provenance.csv`
resolves those ids to titles, URLs and retrieval dates. That keeps the chain
auditable even though the inputs are not machine-readable.

THE `basis` COLUMN IS LOAD-BEARING
----------------------------------
A budget figure is meaningless without its vintage. The same year-and-measure
routinely has three or four different published values:

    2025 sales & use tax ... 180.17 (adopted budget)
                             176.84 (revised projection, mid-year)
                             178.75 (actuals, unaudited year-end)

Filtering on a single `basis` is almost always what you want. Mixing them
silently produces a series that looks like volatility but is really just
different questions being answered. See the data dictionary.

WHAT THIS DOES NOT COVER
------------------------
  * Years before 2022. The council packets narrate budget history back to 2023
    and chart it back to 2019, but the 2019-2022 totals appear only inside
    chart images, so they are not transcribed here. They are recoverable from
    the published budget books.
  * FTE *levels*. Only year-over-year position CHANGES are published in the
    sources used here. A staffing headcount series needs the budget books'
    personnel schedules.
"""

import csv
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Source registry. `retrieved` is when the figures were read from the document.
# --------------------------------------------------------------------------
SOURCES = {
    "rec2026": {
        "title": "2026 Recommended Budget — City Council study session presentation",
        "publisher": "City of Boulder",
        "date": "2025-09-11",
        "url": "https://bouldercolorado.gov/services/budget",
        "retrieved": "2026-08-29",
        "notes": "Forecasted 2026 revenues by source; 2026 gap; new fee measures.",
    },
    "forecast2026": {
        "title": "2026 Financial Forecast — City Council study session packet (May 14, 2026)",
        "publisher": "City of Boulder",
        "date": "2026-05-14",
        "url": "https://bouldercolorado.gov/services/budget",
        "retrieved": "2026-08-29",
        "notes": "Sales/use tax and property tax tables; 2023-2026 budget history narrative; 2027 gap forecast.",
    },
    "rec2027": {
        "title": "City Manager Releases Balanced Budget… (2027 Recommended Budget release)",
        "publisher": "City of Boulder",
        "date": "2026-08-28",
        "url": "https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input",
        "retrieved": "2026-09-21",
        "notes": "2027 totals, General Fund, gap, position changes.",
    },
    "glance2027": {
        "title": "Budget At-A-Glance (2027)",
        "publisher": "City of Boulder",
        "date": "2026-08-28",
        "url": "https://bouldercolorado.gov/budget-glance",
        "retrieved": "2026-09-21",
        "notes": "2027 year-over-year percentages; position adds/freezes.",
    },
    "snapshot2023": {
        "title": "2023 Budget — Sources & Uses Citywide, Types (OpenGov dataset 65843, CSV export)",
        "publisher": "City of Boulder",
        "date": "2023-01-01",
        "url": "https://cityofboulderco.opengov.com/transparency/#/65843/accountType=revenuesVersusExpenses&breakdown=types&year=2023",
        "retrieved": "2026-09-21",
        "notes": "Citywide gross sources & uses, 2021 actual / 2022 adopted / 2023 total budget. Different basis from the budget_* headline totals — see the data dictionary.",
    },
    "books": {
        "title": "City of Boulder annual budget books, 2016-2026 (narrative summary pages)",
        "publisher": "City of Boulder",
        "date": "2026-09-22",
        "url": "https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2",
        "retrieved": "2026-09-22",
        "notes": "Extracted by budget-books-extract.py from the page-text dump. Figures are stated in prose, not tables. Verified: 10 of 12 overlapping values match the council packets exactly.",
    },
    "brl2027": {
        "title": "Boulder's proposed 2027 budget would cut 13 filled jobs and reduce pool hours",
        "publisher": "Boulder Reporting Lab",
        "date": "2026-09-08",
        "url": "https://boulderreportinglab.org/2026/09/08/boulders-proposed-2027-budget-would-cut-13-filled-jobs-and-trim-pool-hours/",
        "retrieved": "2026-09-21",
        "notes": "General Fund % change; staffing savings; department detail.",
    },
}

# --------------------------------------------------------------------------
# Rows: (year, measure, basis, value, unit, src)
# --------------------------------------------------------------------------
ROWS = []


def add(year, measure, basis, value, unit, src):
    ROWS.append(
        {"year": year, "measure": measure, "basis": basis,
         "value": value, "unit": unit, "source_id": src}
    )


# --- Citywide budget totals ------------------------------------------------
# 2023-2026 from the May 2026 packet's budget-history narrative; 2027 from the
# recommended-budget release. operating + capital = total in every year.
for yr, total, oper, cap, basis, src in [
    (2023, 515.4, 354.6, 160.8, "adopted", "forecast2026"),
    (2024, 515.4, 374.2, 141.2, "adopted", "forecast2026"),
    (2025, 589.3, 399.3, 189.9, "adopted", "forecast2026"),
    (2026, 521.0, 407.7, 113.3, "adopted", "forecast2026"),
    (2027, 552.60, 417.24, 135.36, "recommended", "rec2027"),
]:
    add(yr, "budget_total", basis, total, "musd", src)
    add(yr, "budget_operating", basis, oper, "musd", src)
    add(yr, "budget_capital", basis, cap, "musd", src)

# --- General Fund ----------------------------------------------------------
add(2024, "budget_general_fund", "adopted", 196.2, "musd", "forecast2026")
add(2026, "budget_general_fund", "adopted", 194.5, "musd", "forecast2026")
add(2027, "budget_general_fund", "recommended", 200.5, "musd", "rec2027")
# 2025 GF is not stated directly in these sources. The packet gives 2026 as a
# 7.8% decrease from 2025, so 194.5 / (1 - 0.078) ~= 211.0. Marked `derived`
# and rounded to 0.1 — do not present it as a published figure.
add(2025, "budget_general_fund", "derived", round(194.5 / (1 - 0.078), 1), "musd", "forecast2026")

# --- Operating budget, 2017-2022, from the budget books --------------------
# Each book states its own year-over-year change, which lets the chain be
# checked rather than trusted: 2019 +2.0%, 2020 +2.3%, 2021 -6.0%, 2022 +10%,
# 2023 +18% as published, against +2.0/+2.0/-5.7/+10.2/+18.2 computed from
# these values. The chain terminates at 2023 = 354.6, which matches the council
# packet exactly, so the whole run shares that basis.
#
# The 18% step from 2022 to 2023 looks like an extraction error and is not —
# the 2023 book states it outright.
for yr, v in [(2017, 260.0), (2018, 277.6), (2019, 283.2),
              (2020, 288.9), (2021, 272.3), (2022, 300.1)]:
    add(yr, "budget_operating", "adopted", v, "musd", "books")
add(2022, "budget_capital", "adopted", 162.4, "musd", "books")

# --- Citywide totals from the budget books, 2004-2022 ---------------------
# Earlier I expected a basis break here, because the 2016 book publishes its
# total as "$327 million (excluding transfers)" against $515.4M for 2023. The
# intervening years disprove it: 327, 322, 389, 354, 370, 342, 462, 515 is a
# continuous run, so the books report one consistent NET measure throughout and
# the 2016 note is a scope description, not a different series. (The OpenGov
# Sources & Uses family below is the gross counterpart — see the dictionary.)
#
# Two independent checks fell out of the extraction:
#   * 2022 operating 300.1 + capital 162.4 = 462.5, exactly the stated total;
#   * the 2005 and 2006-2007 books both state 2005 = $196,167,000, so that
#     figure is confirmed by two separately published books.
for yr, v in [(2004, 188.145), (2005, 196.167), (2006, 200.100),
              (2012, 239.0), (2013, 255.0), (2014, 270.0), (2015, 319.0),
              (2016, 327.0), (2017, 322.0), (2018, 389.2), (2019, 353.7),
              (2020, 369.7), (2021, 341.7), (2022, 462.5)]:
    add(yr, "budget_total", "adopted", v, "musd", "books")

# The 2005 and 2006 books carry a structured summary block that yields four
# measures at once and self-checks (capital + operating = total):
#     CITY OF BOULDER 2006 BUDGET (in $1,000s)
#     TOTAL BUDGET $200,100  CAPITAL BUDGET $29,453
#     OPERATING BUDGET (including debt service) $170,647  GENERAL FUND $71,266
# Note the operating figure INCLUDES debt service, which the modern operating
# series does not separate out.
for yr, oper, cap, gf in [(2005, 167.059, 29.108, 69.070),
                          (2006, 170.647, 29.453, 71.266)]:
    add(yr, "budget_operating", "adopted", oper, "musd", "books")
    add(yr, "budget_capital", "adopted", cap, "musd", "books")
    add(yr, "budget_general_fund", "adopted", gf, "musd", "books")

# --- Citywide staffing LEVELS ---------------------------------------------
# Previously unavailable. The budget books state a citywide headcount in prose
# ("a total city staffing level of 1,540.09 full-time equivalents"), which the
# council packets and press releases never do — they report only per-year
# position changes. Years without a row are books that state no citywide figure
# on the pages scanned, not zeros.
for yr, v in [(2016, 1419.00), (2018, 1451.00), (2021, 1375.83), (2022, 1460.71),
              (2023, 1540.09), (2025, 1539.10), (2026, 1548.28)]:
    add(yr, "staffing_fte", "adopted", v, "fte", "books")

# --- General Fund gap ------------------------------------------------------
add(2025, "gap_general_fund_low", "identified", 8.0, "musd", "forecast2026")
add(2025, "gap_general_fund_high", "identified", 10.0, "musd", "forecast2026")
add(2026, "gap_general_fund", "identified", 7.5, "musd", "forecast2026")
add(2027, "gap_general_fund", "forecast", 6.5, "musd", "forecast2026")
add(2027, "gap_general_fund", "recommended", 6.3, "musd", "rec2027")

# --- Sales & use tax, by component ----------------------------------------
# Columns of the May 2026 packet's sales & use tax table. "n/b" (not budgeted)
# is recorded as an omitted row, not as zero.
SALESUSE = {
    # basis            retail  recMJ  cons/bus  constr   mv    stAudit  useAudit  total
    (2022, "actual"):            (135.68, 1.71, 12.11, 12.91, 6.07, 0.08, 0.55, 169.11),
    (2023, "actual"):            (137.73, 1.39, 10.29, 16.54, 6.45, 1.62, 1.50, 175.52),
    (2024, "actual"):            (139.24, 1.18,  9.84, 14.92, 5.97, 2.12, 0.64, 173.90),
    (2025, "adopted"):           (144.86, 1.15, 11.93, 14.31, 6.65, 1.28, None, 180.17),
    (2025, "revised_projection"):(141.57, 1.00, 13.80, 12.70, 6.47, 1.28, None, 176.84),
    (2025, "actual"):            (140.90, 1.00,  9.82, 18.12, 6.14, 1.58, 1.20, 178.75),
    (2026, "adopted"):           (147.35, 1.00, 12.67, 10.66, 6.50, 1.46, None, 179.64),
    (2026, "forecast"):          (139.96, 1.00, 14.63, 13.78, 7.89, 1.49, None, 178.71),
}
SU_NAMES = [
    "salesuse_retail", "salesuse_rec_marijuana_addl", "salesuse_consumer_business_use",
    "salesuse_construction_use", "salesuse_motor_vehicle_use",
    "salesuse_audits_sales", "salesuse_audits_use", "salesuse_total",
]
for (yr, basis), vals in SALESUSE.items():
    for name, v in zip(SU_NAMES, vals):
        if v is not None:
            add(yr, name, basis, v, "musd", "forecast2026")

# --- Property tax + assessed value ----------------------------------------
for yr, basis, rev, av in [
    (2023, "actual",             48.74, 4227),
    (2024, "actual",             60.63, 5095),
    (2025, "adopted",            57.12, 5004),
    (2025, "actual",             57.58, 5091),
    (2026, "adopted",            59.17, 5184),
    (2026, "revised_projection", 57.33, 5022),
]:
    add(yr, "property_tax_revenue", basis, rev, "musd", "forecast2026")
    add(yr, "property_assessed_value", basis, av, "musd", "forecast2026")
add(2026, "property_mill_levy", "adopted", 11.648, "mills", "forecast2026")

# --- 2026 citywide revenue by source (all funds) --------------------------
# From the 2026 Recommended Budget presentation. Sums to 507.20.
for name, v in [
    ("revenue_sales_use_tax", 179.640471),
    ("revenue_utility", 97.444530),
    ("revenue_property_tax", 61.732059),
    ("revenue_other_grouped", 50.582397),
    ("revenue_development_impact_fees", 27.764864),
    ("revenue_licenses_permits_fines", 19.857913),
    ("revenue_intergovernmental", 18.774158),
    ("revenue_investment_earnings_bonds", 16.841629),
    ("revenue_accommodation_admission_tax", 12.863745),
    ("revenue_grants", 10.920529),
    ("revenue_parking", 10.776877),
]:
    add(2026, name, "recommended", round(v, 6), "musd", "rec2026")
add(2026, "revenue_total", "recommended", 507.2, "musd", "rec2026")

# --- Staffing CHANGES (levels are not published in these sources) ---------
add(2026, "positions_eliminated", "adopted", 19, "fte", "rec2026")
add(2027, "positions_eliminated", "recommended", 24, "fte", "rec2027")
add(2027, "positions_eliminated_filled", "recommended", 13, "fte", "rec2027")
add(2027, "positions_eliminated_vacant", "recommended", 11, "fte", "rec2027")
add(2027, "positions_term_limited_ending", "recommended", 12, "fte", "rec2027")
add(2027, "positions_frozen_to_2028", "recommended", 8.5, "fte", "glance2027")
add(2027, "positions_added", "recommended", 11.5, "fte", "glance2027")
add(2027, "staffing_savings", "recommended", 3.0, "musd", "brl2027")

# --- Published year-over-year percentages ---------------------------------
add(2026, "yoy_operating_pct", "adopted", 2.1, "pct", "forecast2026")
add(2026, "yoy_general_fund_pct", "adopted", -7.8, "pct", "forecast2026")
add(2027, "yoy_total_pct", "recommended", 6.07, "pct", "glance2027")
add(2027, "yoy_operating_pct", "recommended", 2.3, "pct", "glance2027")
add(2027, "yoy_capital_pct", "recommended", 19.47, "pct", "glance2027")
add(2027, "yoy_general_fund_pct", "recommended", 3.09, "pct", "brl2027")

# --- Reserve policy --------------------------------------------------------
add(2026, "reserve_policy_pct_of_operating", "policy", 16.7, "pct", "forecast2026")

# --------------------------------------------------------------------------
# Citywide Sources & Uses (OpenGov export, dataset 65843) — 2021-2023
#
# This is a DIFFERENT ACCOUNTING BASIS from the budget_* headline totals above
# and the two must never be charted as one series. For 2023 the snapshot puts
# citywide expenses at $598.79M against the city's published $515.4M adopted
# total — an $83.4M gap. Two reasons, both structural:
#
#   1. The 2023 column is "Total Budget" (adopted plus amendments and
#      carryforward), not "Adopted Budget". The 2022 column IS adopted, and
#      the 2021 column is actuals — three bases in one file.
#   2. It is gross rather than net: interfund flows are left in on both sides
#      (Transfers In, Intragovernmental Charges, Cost Allocation on the
#      revenue side; Transfers and Internal Services on the expense side), so
#      money moving between city funds is counted more than once.
#
# Kept under its own `sources_`/`uses_` prefixes for exactly that reason. The
# value it adds is real: a full expense composition (personnel, capital,
# operating, debt service) that the headline totals never break out, and one
# extra year of history at the front.
# --------------------------------------------------------------------------
SNAPSHOT_YEARS = [(2021, "actual"), (2022, "adopted"), (2023, "total_budget")]

SNAPSHOT_REVENUE = {
    "sales_use_tax":               (152231769, 141001909, 173348612),
    "utility":                     ( 74307851,  78394200,  83183592),
    "investment_earnings_bonds":   (  8444586,  96474638,  52894429),
    "property_tax":                ( 49756122,  53009200,  53051677),
    "intragovernmental_charges":   ( 22709384,  40718659,  46625767),
    "other":                       ( 33539525,  33150725,  26704205),
    "transfers_in":                ( 30151267,  22124637,  19312048),
    "intergovernmental":           ( 16527977,  15285634,  24646751),
    "development_impact_fees":     ( 20139445,  14831983,  19255139),
    "licenses_permits_fines":      ( 12927754,  14722525,  14921153),
    "cost_allocation":             ( 11455827,  11048774,  12741197),
    "leases_rents_royalties":      (  9242514,   8588875,   9471736),
    "accommodation_admission_tax": (  7795783,   8838844,  10292147),
    "charges_for_services":        (  5427693,   6607609,   8330373),
    "misc_sales_materials_goods":  (  9145467,   1560516,   5421235),
    "grants":                      (  4819318,   3067473,   6757248),
    "specific_ownership_tobacco":  (  2788293,   2993454,   3046498),
    "franchise_fees":              (   919275,   1033332,   5541814),
}
SNAPSHOT_REVENUE_TOTAL = (472329850, 553452986, 575545620)

SNAPSHOT_EXPENSE = {
    "personnel":         (151929858, 173338936, 194047344),
    "capital":           ( 56518750, 161968657, 172540892),
    "operating":         (114992085, 104930558, 123858331),
    "transfers":         ( 41607094,  33173414,  32145582),
    "internal_services": ( 20016651,  36803136,  42444015),
    "debt_service":      ( 28616988,  31413300,  33755478),
}
SNAPSHOT_EXPENSE_TOTAL = (413681426, 541628000, 598791642)
SNAPSHOT_NET = (58648425, 11824986, -23246022)

for i, (yr, basis) in enumerate(SNAPSHOT_YEARS):
    for name, vals in SNAPSHOT_REVENUE.items():
        add(yr, f"sources_revenue_{name}", basis, round(vals[i] / 1e6, 6), "musd", "snapshot2023")
    add(yr, "sources_revenue_total", basis, round(SNAPSHOT_REVENUE_TOTAL[i] / 1e6, 6), "musd", "snapshot2023")
    for name, vals in SNAPSHOT_EXPENSE.items():
        add(yr, f"uses_expense_{name}", basis, round(vals[i] / 1e6, 6), "musd", "snapshot2023")
    add(yr, "uses_expense_total", basis, round(SNAPSHOT_EXPENSE_TOTAL[i] / 1e6, 6), "musd", "snapshot2023")
    add(yr, "net_revenues_less_expenses", basis, round(SNAPSHOT_NET[i] / 1e6, 6), "musd", "snapshot2023")


# --------------------------------------------------------------------------
# Reconciliation — fail loudly rather than publish an internally broken series
# --------------------------------------------------------------------------
def reconcile():
    """Check every published total against the sum of its published parts.

    Small residuals are expected and are NOT errors: the city totals at full
    precision and publishes components rounded to $0.01M, so a column of six
    components can legitimately miss its own total by a few hundredths. Those
    are surfaced as `residual` (and written into the dataset as
    `salesuse_component_residual`) rather than swallowed. Anything larger is a
    real problem and fails the build.
    """
    TOL = 0.05
    idx = {(r["year"], r["measure"], r["basis"]): r["value"] for r in ROWS}
    problems, residuals = [], []

    # operating + capital = total, for every year where all three are known,
    # on whichever basis carries them. Checks the book-derived years too rather
    # than only the modern ones.
    for yr in sorted({r["year"] for r in ROWS}):
        for basis in ("adopted", "recommended"):
            t = idx.get((yr, "budget_total", basis))
            o = idx.get((yr, "budget_operating", basis))
            c = idx.get((yr, "budget_capital", basis))
            if None not in (t, o, c) and abs((o + c) - t) > 0.2:
                problems.append(
                    f"{yr} {basis}: operating+capital={o + c:.2f} != total={t:.2f}")

    for (yr, basis), vals in sorted(SALESUSE.items()):
        parts = [v for v in vals[:-1] if v is not None]
        delta = round(sum(parts) - vals[-1], 2)
        if abs(delta) > TOL:
            problems.append(
                f"{yr} {basis} sales/use components={sum(parts):.2f} != total={vals[-1]:.2f}")
        elif delta:
            residuals.append((yr, basis, delta))

    rev = sum(r["value"] for r in ROWS
              if r["measure"].startswith("revenue_") and r["measure"] != "revenue_total")
    tot = idx.get((2026, "revenue_total", "recommended"))
    if tot and abs(rev - tot) > 0.02:
        problems.append(f"2026 revenue components={rev:.3f} != total={tot:.2f}")

    # Sources & Uses snapshot: components vs totals, and the stated net.
    # Published to the dollar, so this is a tight check ($10 tolerance).
    for i, (yr, basis) in enumerate(SNAPSHOT_YEARS):
        for label, parts, total in (
            ("revenue", SNAPSHOT_REVENUE, SNAPSHOT_REVENUE_TOTAL),
            ("expense", SNAPSHOT_EXPENSE, SNAPSHOT_EXPENSE_TOTAL),
        ):
            s = sum(v[i] for v in parts.values())
            if abs(s - total[i]) > 10:
                problems.append(
                    f"{yr} snapshot {label} components={s:,.0f} != total={total[i]:,.0f}")
        net = SNAPSHOT_REVENUE_TOTAL[i] - SNAPSHOT_EXPENSE_TOTAL[i]
        if abs(net - SNAPSHOT_NET[i]) > 10:
            problems.append(
                f"{yr} snapshot net={net:,.0f} != stated={SNAPSHOT_NET[i]:,.0f}")

    return problems, residuals


# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------
# Headline series for charting, with the basis preferred when several exist.
WIDE = [
    ("budget_total", ["adopted", "recommended"]),
    ("budget_operating", ["adopted", "recommended"]),
    ("budget_capital", ["adopted", "recommended"]),
    ("budget_general_fund", ["adopted", "recommended", "derived"]),
    ("salesuse_total", ["actual", "adopted", "forecast"]),
    ("property_tax_revenue", ["actual", "adopted"]),
    ("gap_general_fund", ["identified", "recommended", "forecast"]),
]


def main():
    # Record source-side rounding residuals as data before anything is written,
    # so a downstream user sees them instead of rediscovering them.
    problems, residuals = reconcile()
    for yr, basis, delta in residuals:
        add(yr, "salesuse_component_residual", basis, delta, "musd", "forecast2026")

    ROWS.sort(key=lambda r: (r["year"], r["measure"], r["basis"]))

    long_path = HERE / "budget-history.csv"
    with long_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["year", "measure", "basis", "value", "unit", "source_id"])
        w.writeheader()
        w.writerows(ROWS)

    idx = {(r["year"], r["measure"], r["basis"]): r["value"] for r in ROWS}
    years = sorted({r["year"] for r in ROWS})
    wide_path = HERE / "budget-history-wide.csv"
    with wide_path.open("w", newline="") as fh:
        # Every series carries its own *_basis column. Across a historical
        # series the basis necessarily shifts — actuals for closed years, the
        # adopted or recommended figure for the current one — and a chart that
        # hides that shift is quietly comparing different things.
        cols = ["year"]
        for m, _ in WIDE:
            cols += [m, f"{m}_basis"]
        w = csv.writer(fh)
        w.writerow(cols)
        for yr in years:
            row = [yr]
            for measure, prefs in WIDE:
                val, basis = "", ""
                for b in prefs:
                    if (yr, measure, b) in idx:
                        val, basis = idx[(yr, measure, b)], b
                        break
                row += [val, basis]
            w.writerow(row)

    prov_path = HERE / "budget-history-provenance.csv"
    with prov_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_id", "title", "publisher", "date", "url", "retrieved", "n_values", "notes"])
        for sid, s in SOURCES.items():
            n = sum(1 for r in ROWS if r["source_id"] == sid)
            w.writerow([sid, s["title"], s["publisher"], s["date"], s["url"], s["retrieved"], n, s["notes"]])

    print(f"budget-history.csv            {len(ROWS)} rows, "
          f"{len(years)} years ({min(years)}-{max(years)}), "
          f"{len({r['measure'] for r in ROWS})} measures")
    print(f"budget-history-wide.csv       {len(years)} rows x {len(WIDE)} series")
    print(f"budget-history-provenance.csv {len(SOURCES)} sources")
    if problems:
        print("\nRECONCILIATION FAILED:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("\nreconciliation: every published total matches its parts")
    if residuals:
        print("source-side rounding residuals (recorded as salesuse_component_residual):")
        for yr, basis, delta in residuals:
            print(f"  {yr} {basis}: {delta:+.2f}M")


if __name__ == "__main__":
    main()
