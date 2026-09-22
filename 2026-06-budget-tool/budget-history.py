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

import collections
import csv
import pathlib
import re

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
        "title": "City of Boulder annual budget books, 2005-2026 (summary pages)",
        "publisher": "City of Boulder",
        "date": "2026-09-22",
        "url": "https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2",
        "retrieved": "2026-09-22",
        "notes": "Extracted by budget-books-extract.py from the page-text dump. Three shapes: prose from 2017 on, a self-checking citywide summary block 2005-2017, and three- and four-year-wide Sources/Uses/FTE tables before 2012. Verified: 10 of 12 values overlapping the council packets match exactly.",
    },
    "deptsnapshot2026": {
        "title": "2026 Budget — Sources and Uses, Cost Centers (OpenGov transparency view, CSV export)",
        "publisher": "City of Boulder",
        "date": "2026-01-01",
        "url": "https://cityofboulderco.opengov.com/transparency",
        "retrieved": "2026-09-22",
        "notes": "Expenses by cost centre, 2024/2025/2026 adopted. Exported with a 23-fund filter that omits the utility, debt-service and internal-service funds, so the twenty cost centres fall $108-116M short of the citywide total — carried as deptexp_funds_outside_export. No revenue side in this export.",
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
# 2017 is absent here on purpose: its book states the operating budget twice,
# rounded in prose ("$260 million") and to the thousand in the summary block
# ($260,677). The block value is the one kept, below, because only it satisfies
# operating + capital = total.
for yr, v in [(2018, 277.6), (2019, 283.2),
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
# 2012 and 2014-2017 were previously carried at the rounded figure the City
# Manager's message gives ("totals $270 million"); the summary block on each
# book's citywide-summaries page states them to the thousand, so the exact
# value replaces the rounded one. 2011 comes from a sentence in a whole-dollar
# form nothing else in the corpus uses: "The 2011 budget totals $231,030,000."
for yr, v in [(2004, 188.145), (2005, 196.167), (2006, 200.100),
              (2008, 237.781), (2011, 231.030), (2012, 238.960), (2013, 255.0),
              (2014, 269.496), (2015, 319.096), (2016, 327.699), (2017, 321.866),
              (2018, 389.2), (2019, 353.7), (2020, 369.7), (2021, 341.7),
              (2022, 462.5)]:
    add(yr, "budget_total", "adopted", v, "musd", "books")

# 2010 is one of the two years that exist only as scanned PDFs, and the 2011
# book gives it away: its own total "represents a 0.38% increase over the 2010
# approved budget for all funds". The percentage is rounded to two decimals, so
# the true value is 230.14-230.17 — hence one decimal place, and `derived`.
add(2010, "budget_total", "derived", round(231.030 / 1.0038, 1), "musd", "books")

# --- The citywide summary block, 2005-2017 ---------------------------------
# Every book from 2005 to 2017 carries one block that yields five measures at
# once and validates itself twice over:
#
#     CITY OF BOULDER 2006 BUDGET (in $1,000s)
#     TOTAL BUDGET $200,100        CAPITAL BUDGET $29,453
#     OPERATING BUDGET (including debt service) $170,647
#     DEDICATED FUNDS $99,381      GENERAL FUND $71,266
#
#   capital + operating        = total
#   general fund + dedicated  = operating
#
# Both identities hold to the thousand in all seven years, which is why these
# figures need no cross-checking against another document.
#
# The operating figure INCLUDES debt service, which the modern operating series
# does not separate out either but only these books say so explicitly.
#
# `budget_operating_general` is NOT the headline General Fund. It is the General
# Fund half of the operating budget, and it runs about 12% below the "Total
# General Fund Uses" figure recorded further down, which adds transfers out and
# the 0.15% sales tax allocation. In 2014 the two are $101.96M and $115.68M. The
# gap is structural and stable, and charting them as one series invents a step.
for yr, oper, cap, gf, ded in [(2005, 167.059, 29.108, 69.070, 97.989),
                               (2006, 170.647, 29.453, 71.266, 99.381),
                               (2008, 200.487, 37.294, 80.466, 120.021),
                               (2014, 227.450, 42.046, 101.959, 125.491),
                               (2015, 250.444, 68.652, 113.550, 136.894),
                               (2016, 254.395, 73.304, 116.963, 137.432),
                               (2017, 260.677, 61.189, 130.862, 129.815)]:
    add(yr, "budget_operating", "adopted", oper, "musd", "books")
    add(yr, "budget_capital", "adopted", cap, "musd", "books")
    add(yr, "budget_operating_general", "adopted", gf, "musd", "books")
    add(yr, "budget_operating_dedicated", "adopted", ded, "musd", "books")
# 2012's block extracts with its digits mangled ("238) 960", "214.,979",
# "23,,981"), so these three are transcribed by hand. The reconciliation below
# still checks them: 214.979 + 23.981 = 238.960.
add(2012, "budget_operating", "adopted", 214.979, "musd", "books")
add(2012, "budget_capital", "adopted", 23.981, "musd", "books")
# 2013's block survives extraction with only two of its five figures legible and
# no way to tell which label each belongs to, so 2013 keeps its rounded total
# alone. The split is on page 97 of that book for anyone who wants to read it.

# --- General Fund, the headline "Total General Fund Uses" ------------------
# The legacy books' Uses of Funds tables are three and four years WIDE with the
# basis in the column header, so the 2008 book states 2007 and the 2011 book
# states 2009 and 2010 — years whose own books are scans. From 2012 the figure
# moves into prose ("General Fund expenditures of $146,321,197").
#
# That this is the same measure as the modern 2024-2027 values is not assumed:
# the 2012 book says its General Fund expenditures are "a 3.8 percent increase
# over the total expenditures projected for the 2011 Approved Budget", and
# 100.449 x 1.038 = 104.27 against the stated 104.234.
for yr, basis, v in [(2006, "actual", 89.123), (2007, "adopted", 89.650),
                     (2008, "adopted", 94.238), (2009, "actual", 105.848),
                     (2009, "projected", 95.883), (2010, "adopted", 96.713),
                     (2011, "adopted", 100.449), (2012, "adopted", 104.234),
                     (2014, "adopted", 115.684), (2015, "adopted", 128.483),
                     (2016, "adopted", 132.268), (2017, "adopted", 139.792),
                     (2018, "adopted", 146.321)]:
    add(yr, "budget_general_fund", basis, v, "musd", "books")

# --- General Fund revenue, from the same tables' Sources side --------------
# The revenue counterpart, so the General Fund can be read from both sides.
# 2004 and 2005 appear in two books each and agree, which also confirms the
# column alignment: 2005 is the third column of the 2005 book's table and the
# second of the 2006-2007 book's, and both read $80,091.
for yr, basis, v in [(2003, "actual", 87.252), (2004, "actual", 80.270),
                     (2004, "adopted", 77.962), (2005, "adopted", 80.091),
                     (2006, "adopted", 82.637), (2007, "projected", 85.017),
                     (2009, "actual", 104.020), (2010, "adopted", 96.746),
                     (2011, "adopted", 99.761), (2012, "adopted", 104.299),
                     (2013, "adopted", 109.752)]:
    add(yr, "budget_general_fund_revenue", basis, v, "musd", "books")

# --- Citywide revenue, 2010-2011 ------------------------------------------
# "The 2011 budget is based on projected citywide revenues of $224,912,000.
# This represents a 0.29% increase over the total revenues projected for the
# 2010 approved budget." The 2010 figure is therefore derived, and the rounded
# percentage puts it at 224.25-224.27.
add(2011, "revenue_total", "adopted", 224.912, "musd", "books")
add(2010, "revenue_total", "derived", round(224.912 / 1.0029, 1), "musd", "books")

# --- Citywide staffing LEVELS ---------------------------------------------
# Previously unavailable. The budget books state a citywide headcount in prose
# ("a total city staffing level of 1,540.09 full-time equivalents"), which the
# council packets and press releases never do — they report only per-year
# position changes. Years without a row are books that state no citywide figure
# on the pages scanned, not zeros.
for yr, v in [(2016, 1419.00), (2018, 1451.00), (2021, 1375.83), (2022, 1460.71),
              (2023, 1540.09), (2025, 1539.10), (2026, 1548.28)]:
    add(yr, "staffing_fte", "adopted", v, "fte", "books")

# The pre-2012 books count staffing differently, and say so: "Summary of
# STANDARD FTEs", where a note limits the count to standard Management, BMEA,
# Fire and Police positions. The modern books say "citywide staffing level"
# without that qualifier. No book in the corpus publishes both, so there is no
# way to measure the offset — hence a separate measure. Nine consecutive years,
# and the overlaps between books agree exactly: 2004 and 2005 appear in the 2005
# and 2006-2007 books, 2006 in the 2006-2007 and 2008 books.
#
# The shape is the recession story twice over: 1,290.69 in 2003 down to 1,200.68
# in 2004, back up to 1,288.52 by 2009, then down to 1,228.50 by 2011.
for yr, v in [(2003, 1290.69), (2004, 1200.68), (2005, 1212.11), (2006, 1218.84),
              (2007, 1251.34), (2008, 1281.17), (2009, 1288.52), (2010, 1248.24),
              (2011, 1228.50)]:
    add(yr, "staffing_fte_standard", "adopted", v, "fte", "books")

# --- The revenue big movers, 2011 --------------------------------------------
# The 2011 book prints a citywide all-funds revenue pie whose eight slices sum
# to $224,912 thousand exactly -- the same total the narrative states -- so the
# label-to-value pairing is confirmed by construction and not by reading a
# figure off a garbled line. Each slice's share also matches its printed
# percentage, which is what pins the two 4% slices to the right labels.
#
# Only the slices that map onto an existing `revenue_*` category are recorded.
# Four do not (Other Taxes $16.071M, Parks & Recreation Fees $8.479M, Planning &
# Development Fees $4.994M, Other $25.331M) and inventing categories for them
# would create a third revenue taxonomy for the sake of one year. They are on
# page 68 of `2011 Annual Budget.pdf` if anyone wants them.
#
# The slice is labelled "Sales Tax", but the same page calls the city's largest
# sources "sales/use taxes", so it is the sales-and-use aggregate rather than
# sales tax alone.
for measure, v in [("revenue_sales_use_tax", 86.570), ("revenue_utility", 44.905),
                   ("revenue_property_tax", 28.563), ("revenue_intergovernmental", 9.999)]:
    add(2011, measure, "adopted", v, "musd", "books")
# What the four unmapped slices are worth, so the year still adds up to its own
# published total and the gap is a number rather than an absence.
add(2011, "revenue_other_unmapped", "adopted",
    round(224.912 - (86.570 + 44.905 + 28.563 + 9.999), 3), "musd", "books")

# --- Citywide spending by department, mapped into functional buckets -------
# The expense breakdown that actually reaches back to 2005. The
# Personnel/Capital/Operating/Debt-Service split people reach for first is an
# OpenGov construct that appears in exactly two books in this corpus; the
# citywide spending pie, by department, is in all of them.
#
# Departments were reorganized repeatedly over twenty years, so raw labels do
# not form a series. In 2005, "Public Works" is a single $67.4M slice; by 2024
# that same money is spread across Transportation and Mobility, Utilities,
# Facilities and Fleet, and development review. The 2005 pie does not separate
# them and the split is not recoverable -- the 2005 book splits Public Works
# three ways in its STAFFING table but not in its SPENDING pie. The buckets are
# therefore coarse on purpose: coarse enough that the coarsest year still maps.
#
# Every line below carries the label exactly as its document prints it, the year
# it was printed in, and the bucket it was assigned to. That is the record, not a
# summary of it: budget-history-department-crosswalk.csv is generated from these
# rows, so the documented crosswalk cannot drift from the one actually used, and
# any single assignment can be challenged or re-bucketed without re-reading the
# PDFs. `note` is filled in wherever the call was a judgment rather than obvious.
#
# (year, label as printed, $M, bucket, note)
DEPARTMENT_LINES = [
    # -- 2005 and 2006: the citywide "Uses of Funds" pie in each book. Both
    #    years' twelve slices sum to the published citywide total to the dollar,
    #    which is what makes them trustworthy. 2011's pie exists too but comes
    #    out of the PDF with labels and values interleaved beyond repair, so it
    #    is deliberately absent rather than guessed at.
    (2005, "Police", 22.680, "public_safety", ""),
    (2005, "Fire", 10.996, "public_safety", ""),
    (2005, "Public Works", 67.430, "infrastructure",
     "One slice covering what later becomes Transportation and Mobility, "
     "Utilities, Facilities and Fleet and development review. Not separable "
     "here, and the reason the buckets are this coarse."),
    (2005, "Open Space/Real Estate", 20.658, "parks_openspace",
     "Renamed Open Space/Mountain Parks from 2006. The 2005 label also carries "
     "real-estate functions that later move elsewhere."),
    (2005, "Parks & Recreation", 21.060, "parks_openspace", ""),
    (2005, "Housing/Human Svcs", 12.753, "community_services", ""),
    (2005, "Library", 5.740, "community_services", ""),
    (2005, "Arts", 0.440, "community_services", ""),
    (2005, "Planning & Development Services", 6.233, "planning_climate",
     "The 2026 department of the same name is the development-review enterprise "
     "and is four times the size. Same bucket, not the same thing."),
    (2005, "Administrative Svcs", 8.225, "administration", ""),
    (2005, "General Government", 17.284, "administration",
     "The least comparable line in the crosswalk. It likely holds "
     "non-departmental items that 2024-2026 books to Fundwide/Citywide, so the "
     "administration and citywide buckets trade content across the series."),
    (2005, "Debt", 2.668, "citywide_debt",
     "General Fund debt only -- the pie's own note says non-General Fund debt "
     "service sits inside the departments. True in 2011 as well, so the bucket "
     "is consistent, but it is not all of the city's debt service."),
    (2006, "Police", 23.415, "public_safety", ""),
    (2006, "Fire", 11.258, "public_safety", ""),
    (2006, "Public Works", 66.734, "infrastructure", "As 2005: one undivided slice."),
    (2006, "Open Space/Mountain Parks", 22.188, "parks_openspace", ""),
    (2006, "Parks & Recreation", 20.899, "parks_openspace", ""),
    (2006, "Housing/Human Svcs", 13.339, "community_services", ""),
    (2006, "Library", 5.977, "community_services", ""),
    (2006, "Arts", 0.451, "community_services", ""),
    (2006, "Planning & Development Services", 6.465, "planning_climate", ""),
    (2006, "Administrative Svcs", 9.849, "administration", ""),
    (2006, "General Government", 17.208, "administration", "As 2005."),
    (2006, "Debt", 2.317, "citywide_debt", "As 2005."),
]

# -- 2024-2026: the OpenGov cost-center export. Same twenty cost centers in all
#    three years, so the table is written once and the values zipped in.
DEPARTMENT_2024_2026 = [
    # (label as printed, bucket, 2024, 2025, 2026, note)
    ("Transportation and Mobility", "infrastructure", 56.207, 63.331, 56.772, ""),
    ("Facilities and Fleet", "infrastructure", 36.554, 70.932, 25.218, ""),
    ("Utilities", "infrastructure", 0.648, 0.625, 0.338,
     "Under a million dollars because the export's fund filter leaves out the "
     "utility enterprise funds. The real utility spending is in the balancing "
     "line, not here. The clearest symptom of that filter."),
    ("Police", "public_safety", 43.679, 46.426, 50.204, ""),
    ("Fire-Rescue", "public_safety", 27.573, 33.952, 31.503, ""),
    ("Police/Fire Pensions", "public_safety", 0.414, 0.414, 0.490,
     "A pension obligation rather than operations, bucketed with the "
     "departments it belongs to. Small enough not to matter either way."),
    ("Open Space and Mountain Parks", "parks_openspace", 40.366, 41.384, 41.873, ""),
    ("Parks and Recreation", "parks_openspace", 40.493, 38.142, 38.655, ""),
    ("Housing and Human Services", "community_services", 43.949, 53.819, 52.883, ""),
    ("Planning and Development Services", "planning_climate", 16.433, 17.539, 20.003, ""),
    ("Climate Initiatives", "planning_climate", 10.950, 11.292, 9.604,
     "No 2005 equivalent as a department; its predecessor was Environmental "
     "Affairs inside Community Planning and Sustainability."),
    ("City Manager's Office", "administration", 17.145, 20.139, 18.733, ""),
    ("Innovation and Technology", "administration", 9.792, 10.714, 10.834, ""),
    ("Finance", "administration", 7.081, 7.229, 7.241, ""),
    ("City Attorney's Office", "administration", 4.513, 4.882, 5.067, ""),
    ("Human Resources", "administration", 4.510, 4.613, 4.456, ""),
    ("Communications and Engagement", "administration", 4.556, 3.849, 3.877, ""),
    ("Municipal Court", "administration", 2.650, 2.768, 2.710, ""),
    ("City Council", "administration", 0.480, 0.466, 0.544, ""),
    ("Fundwide / Citywide", "citywide_debt", 39.801, 40.931, 30.904,
     "Citywide allocations and contingency. Partly the counterpart of 2005's "
     "General Government -- see that line's note."),
]
for label, bucket, v24, v25, v26, note in DEPARTMENT_2024_2026:
    for yr, v in ((2024, v24), (2025, v25), (2026, v26)):
        DEPARTMENT_LINES.append((yr, label, v, bucket, note))

BUCKET_ORDER = ["public_safety", "infrastructure", "parks_openspace",
                "community_services", "planning_climate", "administration",
                "citywide_debt"]

for yr in sorted({y for y, *_ in DEPARTMENT_LINES}):
    by_bucket = collections.defaultdict(float)
    for y, _label, v, bucket, _note in DEPARTMENT_LINES:
        if y == yr:
            by_bucket[bucket] += v
    for bucket in BUCKET_ORDER:
        if bucket in by_bucket:
            add(yr, f"deptexp_{bucket}", "adopted", round(by_bucket[bucket], 3),
                "musd", "books" if yr <= 2006 else "deptsnapshot2026")

# The 2024-2026 export was taken with a fund filter that leaves out the utility,
# debt-service and internal-service funds, so its twenty cost centres add up to
# $108-116M less than the citywide budget. Rather than let the departmental
# series quietly not add up, the shortfall is carried as its own explicit line,
# computed against the published total:
#
#     2024   515.4 - 407.8 = 107.6      2026   521.0 - 411.9 = 109.1
#     2025   589.3 - 473.4 = 115.9
#
# It is a real number -- what the excluded funds spend -- but it is a residual,
# not a reported figure, so it is `derived`. One re-export of the same view with
# no fund filter replaces it with actual departmental detail, and is the single
# highest-value download left in this dataset.
DEPARTMENT_EXPORT_TOTAL = {2024: 407.794, 2025: 473.447, 2026: 411.907}
for yr, export_total in DEPARTMENT_EXPORT_TOTAL.items():
    published = next(r["value"] for r in ROWS
                     if (r["year"], r["measure"], r["basis"]) == (yr, "budget_total", "adopted"))
    add(yr, "deptexp_funds_outside_export", "derived",
        round(published - export_total, 3), "musd", "deptsnapshot2026")

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

    # One row per (year, measure, basis). Two rows with the same key are not a
    # tidy-data violation to shrug at: `idx` keeps only the last of them, so a
    # duplicate makes the checks below pass while the CSV ships both values and
    # a reader's pivot silently picks whichever their tool prefers. This caught
    # 2017 carrying its operating budget twice, rounded in prose and exact in
    # the summary block.
    seen = collections.Counter((r["year"], r["measure"], r["basis"]) for r in ROWS)
    for (yr, measure, basis), n in sorted(seen.items()):
        if n > 1:
            vals = sorted({r["value"] for r in ROWS
                           if (r["year"], r["measure"], r["basis"]) == (yr, measure, basis)})
            problems.append(f"{yr} {measure} [{basis}] appears {n} times: {vals}")

    # The departmental buckets, plus the balancing line where there is one, must
    # add up to the published citywide total. For 2005 and 2006 this is exact by
    # construction (the pie sums to its own total); for 2024-2026 it holds only
    # because the balancing line is defined as the difference, so what this
    # really guards is a mistyped cost centre.
    for yr in sorted({y for y, *_ in DEPARTMENT_LINES}):
        parts = sum(v for (y, m, b), v in idx.items()
                    if y == yr and m.startswith("deptexp_"))
        total = idx.get((yr, "budget_total", "adopted"))
        if total and abs(parts - total) > TOL:
            problems.append(
                f"{yr}: departmental buckets sum {parts:,.3f} != budget_total {total:,.3f}")

    # The same department label must land in the same bucket every year it
    # appears, unless the line says why not. Without this, a relabelled
    # department could drift between buckets and the series would show a
    # transfer of money that never happened.
    seen_bucket = {}
    for yr, label, _v, bucket, note in DEPARTMENT_LINES:
        key = re.sub(r'[^a-z0-9]', '', label.lower())
        if key in seen_bucket and seen_bucket[key][0] != bucket and not note:
            problems.append(
                f"{label!r} is {bucket} in {yr} but {seen_bucket[key][0]} in "
                f"{seen_bucket[key][1]} with no note explaining the change")
        seen_bucket.setdefault(key, (bucket, yr))

    # operating + capital = total, for every year where all three are known,
    # on whichever basis carries them. Checks the book-derived years too rather
    # than only the modern ones.
    for yr in sorted({r["year"] for r in ROWS}):
        for basis in ("adopted", "recommended"):
            # The summary block's two halves must add to its operating figure.
            # This is the check that would have caught the assignment bug in the
            # extractor, where the General Fund and Dedicated Funds halves were
            # told apart by size -- true every year through 2016 and false in
            # 2017, when the General Fund became the larger of the two.
            g = idx.get((yr, "budget_operating_general", basis))
            d = idx.get((yr, "budget_operating_dedicated", basis))
            o_ = idx.get((yr, "budget_operating", basis))
            if None not in (g, d, o_) and abs((g + d) - o_) > 0.2:
                problems.append(
                    f"{yr} {basis}: general {g} + dedicated {d} = {g + d:.3f} "
                    f"!= operating {o_}")
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

    # Revenue components against their own year's total. This check used to sum
    # every revenue_* row in the dataset regardless of year and compare the lot
    # to 2026's total -- correct only for as long as 2026 was the only year with
    # a revenue mix, and wrong the moment 2011 was added. Keyed on (year, basis)
    # now, so each year is checked against itself.
    rev_years = collections.defaultdict(float)
    for r in ROWS:
        if r["measure"].startswith("revenue_") and r["measure"] != "revenue_total":
            rev_years[(r["year"], r["basis"])] += r["value"]
    for (yr, basis), parts in sorted(rev_years.items()):
        tot = idx.get((yr, "revenue_total", basis))
        if tot and abs(parts - tot) > 0.02:
            problems.append(
                f"{yr} {basis} revenue components={parts:.3f} != total={tot:.2f}")

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
    ("budget_general_fund_revenue", ["adopted", "actual"]),
    ("staffing_fte", ["adopted"]),
    ("revenue_total", ["adopted", "recommended", "derived"]),
    ("revenue_sales_use_tax", ["adopted", "recommended"]),
    ("revenue_property_tax", ["adopted", "recommended"]),
    ("revenue_utility", ["adopted", "recommended"]),
    ("staffing_fte_standard", ["adopted"]),
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

    # The department crosswalk, generated from DEPARTMENT_LINES rather than
    # written alongside it, so what is documented is exactly what was used. One
    # row per department line item per year: the label as its document printed
    # it, the bucket it went into, its share of that year's citywide total, and
    # the reason wherever the assignment was a judgment call.
    cross_path = HERE / "budget-history-department-crosswalk.csv"
    dept_totals = {yr: sum(v for y, _l, v, _b, _n in DEPARTMENT_LINES if y == yr)
                   for yr in {y for y, *_ in DEPARTMENT_LINES}}
    with cross_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "source_label", "bucket", "value_musd",
                    "pct_of_year_departmental", "source_id", "note"])
        for yr, label, v, bucket, note in sorted(
                DEPARTMENT_LINES, key=lambda r: (r[0], BUCKET_ORDER.index(r[3]), -r[2])):
            w.writerow([yr, label, bucket, v,
                        round(100 * v / dept_totals[yr], 2),
                        "books" if yr <= 2006 else "deptsnapshot2026", note])

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
