"""
Boulder city budget history -- the series builder
=================================================
Builds the City of Boulder's budget history, 2002-2027: citywide totals, the
General Fund, staffing, the revenue mix, sales and use tax, property tax, and
spending by department. The last of four stages. The other three read the PDF
budget books and feed this one; README.md has the whole pipeline.

    python3 budget-history.py

Takes no arguments and reads no files. Writes, next to this script:

    budget-history.csv                        tidy long, one row per (year, measure, basis)
    budget-history-wide.csv                   the headline series, one row per year
    budget-history-provenance.csv             one row per source, joined on source_id
    budget-history-department-crosswalk.csv   every department line and its bucket
    budget-history-validation.md              coverage and every check, rebuilt each run

Nothing is written unless every reconciliation check passes.

WHY THE VALUES ARE TYPED INTO THIS FILE
---------------------------------------
There is no bulk download to parse. Boulder publishes these figures in council
study-session packets, budget presentations, press releases and twenty-two years
of budget books -- PDFs with the numbers in prose, summary blocks, pie charts and
multi-year tables. The OpenGov budget book is a JavaScript application with no
public data endpoint (probed 2026-09-21: the documented REST paths return 404).

So this script IS the transcription record. Every value carries the id of the
document it was read from, and budget-history-provenance.csv resolves each id to
a title, URL and retrieval date. Book figures are located by
budget-books-extract.py and typed in here once checked: the extractor's CSV is a
list of candidates, not an input this script reads.

THE `basis` COLUMN IS LOAD-BEARING
----------------------------------
A budget figure is meaningless without its vintage. The same year-and-measure
routinely has three or four different published values:

    2025 sales & use tax ... 180.17 (adopted budget)
                             176.84 (revised projection, mid-year)
                             178.75 (actuals, unaudited year-end)

Filtering on a single `basis` is almost always what you want. Mixing them
silently produces a series that looks like volatility but is really just
different questions being answered.

budget-history-data-dictionary.md documents every column, the basis vocabulary,
the measure catalog and the caveats.
"""

import collections
import csv
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Source registry. `date` is the document's own publication date, left empty for
# a data export or a multi-volume corpus, which have none. `retrieved` is when
# the figures were read from it.
# --------------------------------------------------------------------------
SOURCES = {
    "rec2026": {
        "title": "2026 Recommended Budget: City Council study session presentation",
        "publisher": "City of Boulder",
        "date": "2025-09-11",
        "url": "https://bouldercolorado.gov/services/budget",
        "retrieved": "2026-08-29",
        "notes": "Forecasted 2026 revenues by source; 2026 gap; new fee measures.",
    },
    "forecast2026": {
        "title": "2026 Financial Forecast: City Council study session packet (May 14, 2026)",
        "publisher": "City of Boulder",
        "date": "2026-05-14",
        "url": "https://bouldercolorado.gov/services/budget",
        "retrieved": "2026-08-29",
        "notes": "Sales/use tax and property tax tables; 2023-2026 budget history narrative; 2027 gap forecast.",
    },
    "rec2027": {
        "title": "City Manager Releases Balanced Budget With Focus on Critically Vital Services and Community Input About Priorities",
        "publisher": "City of Boulder",
        "date": "2026-08-28",
        "url": "https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input",
        "retrieved": "2026-09-21",
        "notes": "The 2027 Recommended Budget news release. 2027 totals, General Fund, gap, position changes.",
    },
    "glance2027": {
        "title": "Budget At-A-Glance (2027)",
        "publisher": "City of Boulder",
        "date": "",
        "url": "https://bouldercolorado.gov/budget-glance",
        "retrieved": "2026-09-21",
        "notes": "2027 year-over-year percentages, General Fund included; position adds and freezes. A web page with no date of its own, published with the 2027 Recommended Budget on 2026-08-28.",
    },
    "snapshot2023": {
        "title": "2023 Budget: Sources & Uses Citywide, Types (OpenGov dataset 65843, CSV export)",
        "publisher": "City of Boulder",
        "date": "",
        "url": "https://cityofboulderco.opengov.com/transparency/#/65843/accountType=revenuesVersusExpenses&breakdown=types&year=2023",
        "retrieved": "2026-09-21",
        "notes": "Citywide gross sources & uses, 2021 actual / 2022 adopted / 2023 total budget. Different basis from the budget_* headline totals -- see the data dictionary.",
    },
    "books": {
        "title": "City of Boulder annual budget books, 2005-2026 (summary pages)",
        "publisher": "City of Boulder",
        "date": "",
        "url": "https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2",
        "retrieved": "2026-09-22",
        "notes": "The 34 PDF volumes of the 2005-2026 annual budgets, read from the text pypdf extracts. The figures come in a handful of shapes: prose, self-checking citywide summary blocks, three- and four-year-wide Sources/Uses/FTE tables (before 2012), staffing tables by department, Funds Summary tables, and the citywide spending and revenue charts. Where these overlap the council packets, 10 of 12 values match exactly.",
    },
    "deptsnapshot2026": {
        "title": "2026 Budget: Sources and Uses, Cost Centers (OpenGov transparency view, CSV export)",
        "publisher": "City of Boulder",
        "date": "",
        "url": "https://cityofboulderco.opengov.com/transparency",
        "retrieved": "2026-09-22",
        "notes": "Expenses by cost center, 2024/2025/2026 adopted. Exported with a 23-fund filter that omits the utility, debt-service and internal-service funds, so the twenty cost centers fall $108-116M short of the citywide total -- carried as deptexpfiltered_funds_outside_export. No revenue side in this export.",
    },
    "booksocr": {
        "title": "City of Boulder annual budget books, pages read by OCR (Datalab)",
        "publisher": "City of Boulder",
        "date": "",
        "url": "https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2",
        "retrieved": "2026-09-23",
        "notes": "Same books as `books`, but pages pypdf cannot reach or cannot use, read by Datalab through budget-books-ocr.py: the 2007, 2009 and 2010 Volume 1s, which survive only as scans, and born-digital pages with interleaved pie labels, dropped commas or figures inside images, or that the page dump never held. A pie or summary block is kept only when it sums to a total the same page prints, and a multi-year table value only when its column header names the year and basis. The single staffing figures, 2002 and 2024 and 2022's restatement, are kept on their wording and context. The data dictionary's caveat on OCR lists what was read wrong and not kept.",
    },
    "brl2027": {
        "title": "Boulder's proposed 2027 budget would cut 13 filled jobs and trim pool hours",
        "publisher": "Boulder Reporting Lab",
        "date": "2026-09-08",
        "url": "https://boulderreportinglab.org/2026/09/08/boulders-proposed-2027-budget-would-cut-13-filled-jobs-and-trim-pool-hours/",
        "retrieved": "2026-09-21",
        "notes": "Staffing savings: \"about $3 million, according to a city official.\"",
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
# 2025 comes from its own book -- see "General Fund, 2013 and 2020-2025" below.
# It was once derived here from the packet's "7.8% decrease" as 211.0; the 2025
# book prints 210.9.

# --- Operating budget, 2017-2023, and the summary blocks of 2018-2022 ---------
# Each book states its own year-over-year change, which lets the chain be
# checked rather than trusted: 2019 +2.0%, 2020 +2.3%, 2021 -6.0%, 2022 +10%,
# 2023 +18% as published, against +2.0/+2.0/-5.8/+10.2/+18.2 computed from
# these values. The chain terminates at 2023 = 354.6, which matches the council
# packet exactly, so the whole run shares that basis.
#
# The 18% step from 2022 to 2023 looks like an extraction error and is not —
# the 2023 book states it outright.
# 2017 is absent here on purpose: its book states the operating budget twice,
# rounded in prose ("$260 million") and to the thousand in the summary block
# ($260,677). The block value is the one kept, below, because only it satisfies
# operating + capital = total.
#
# 2018-2022 print the summary block again, in a newer layout that splits the
# capital budget too, and to the dollar from 2019. Read by OCR, each satisfies
# both identities to the dollar, so the block's exact figures replace the
# prose's rounded ones ("$277.6 million") and give 2018-2021 the capital budget
# the prose never stated:
#
#          total          operating = general + dedicated     capital
#   2018   389,210        277,556 = 137,681 + 139,875         111,654   ($1,000s)
#   2020   369,717,595    288,949,901 = 132,257,455 + 156,692,446    80,767,694
#   2021   341,743,592    272,317,823 = 120,675,887 + 151,641,936    69,425,769
#   2022   462,518,802    300,093,670 = 134,145,347 + 165,948,323   162,425,132
#
# 2019's block does not hold together. Its General Fund and dedicated halves
# sum to 283,188,821 -- the "$283.2 million" of the book's prose -- but its
# operating box prints 282,933,821 and its total box 353,490,978, both exactly
# $255,000 lower, while the book's pie and prose give the total as 353,745,978.
# The capital box, 70,557,157, matches its own halves (4,197,360 General Fund
# plus 66,359,797 dedicated) and is exactly the pie total less the operating
# halves. So 2019 keeps the prose operating figure, and takes its capital
# budget and operating halves from the block.
add(2019, "budget_operating", "adopted", 283.2, "musd", "books")
for yr, oper, cap, gf, ded in [(2018, 277.556, 111.654, 137.681, 139.875),
                               (2020, 288.950, 80.768, 132.257, 156.692),
                               (2021, 272.318, 69.426, 120.676, 151.642),
                               (2022, 300.094, 162.425, 134.145, 165.948)]:
    add(yr, "budget_operating", "adopted", oper, "musd", "booksocr")
    add(yr, "budget_capital", "adopted", cap, "musd", "booksocr")
    add(yr, "budget_operating_general", "adopted", gf, "musd", "booksocr")
    add(yr, "budget_operating_dedicated", "adopted", ded, "musd", "booksocr")
add(2019, "budget_capital", "adopted", 70.557, "musd", "booksocr")
add(2019, "budget_operating_general", "adopted", 145.232, "musd", "booksocr")
add(2019, "budget_operating_dedicated", "adopted", 137.956, "musd", "booksocr")

# --- Citywide totals from the budget books, 2004-2022 ---------------------
# One NET measure throughout, with no basis break. The 2016 book publishes its
# total as "$327 million (excluding transfers)" against $515.4M for 2023, which
# looks like two different measures, but the intervening years run 327, 322,
# 389, 354, 370, 342, 462, 515 without a step, so the 2016 note is a scope
# description rather than a different series. (The OpenGov Sources & Uses
# family below is the gross counterpart -- see the data dictionary.)
#
# Two independent checks fell out of the extraction:
#   * 2022 operating 300.1 + capital 162.4 = 462.5, exactly the stated total;
#   * the 2005 and 2006-2007 books both state 2005 = $196,167,000, so that
#     figure is confirmed by two separately published books.
# For 2012 and 2014-2017 the City Manager's message rounds the total ("totals
# $270 million") and the summary block on the citywide-summaries page states it
# to the thousand; the exact figure is the one kept. 2011 comes from a sentence
# in a whole-dollar form nothing else in the corpus uses: "The 2011 budget
# totals $231,030,000."
for yr, v in [(2004, 188.145), (2005, 196.167), (2006, 200.100),
              (2008, 237.781), (2011, 231.030), (2012, 238.960), (2013, 254.693),
              (2014, 269.496), (2015, 319.096), (2016, 327.699), (2017, 321.866),
              # 2018-2022 to the dollar, off the citywide pie headings, which
              # print "TOTAL = $462,518,802" where the narrative rounds to
              # "$462.5 million". Not cosmetic: the departmental slices are exact,
              # so a total rounded to $0.1M left the bucket-sum check clearing
              # its tolerance by $7,000 in 2021.
              (2018, 389.210), (2019, 353.746), (2020, 369.718),
              (2021, 341.744), (2022, 462.519)]:
    add(yr, "budget_total", "adopted", v, "musd", "books")
# 2007, 2009 and 2010 come from their own books, read by OCR -- see "The three
# scanned years" below.

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
# Both identities hold to the thousand in all seven of these years, which is
# why these figures need no cross-checking against another document.
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
# 2013's whole block and 2012's two halves come from OCR (budget-books-ocr.py
# tier 2) of pages pypdf leaves illegible, and both satisfy the block's two
# identities:
#
#     2012   214.979 + 23.981 = 238.960      91.150 + 123.828 = 214.978*
#     2013   221.266 + 33.427 = 254.693      98.703 + 122.563 = 221.266
#
# * one thousand short of the operating figure, which is the city rounding a half.
#
# Without OCR, 2013 would have only a total rounded to "$255 million" in prose.
# pypdf reads just two numbers off that page, 221,266 and 98,703, with no way to
# tell which label either belongs to; OCR confirms them as operating and the
# General Fund half, which is what they looked like and why they were not
# recorded on a guess.
# 2011's block is on page 65 of its book, which the born-digital page dump never
# contained -- it held page 67 -- so 2011 had a total and nothing else. Tier 4 of
# the OCR pass reached it. Its total is $231,030 thousand, which is exactly the
# 2011 total already published from that book's own prose ("The 2011 budget
# totals $231,030,000"), so the block is anchored to a figure read independently.
for yr, oper, cap, gf, ded in [(2011, 206.317, 24.713, 87.663, 118.654),
                               (2013, 221.266, 33.427, 98.703, 122.563)]:
    add(yr, "budget_operating", "adopted", oper, "musd", "booksocr")
    add(yr, "budget_capital", "adopted", cap, "musd", "booksocr")
    add(yr, "budget_operating_general", "adopted", gf, "musd", "booksocr")
    add(yr, "budget_operating_dedicated", "adopted", ded, "musd", "booksocr")
add(2012, "budget_operating_general", "adopted", 91.150, "musd", "booksocr")
add(2012, "budget_operating_dedicated", "adopted", 123.828, "musd", "booksocr")

# --- The three scanned years, 2007, 2009 and 2010 ----------------------------
# Their Volume 1s survive only as scans, so until tier 1 of the OCR pass read all
# 1,137 of their pages, 2007 and 2009 had no citywide total and 2010 had only one
# derived from the 2011 book. Each book's summary block satisfies both identities,
# and each book states its total three times -- the block, the citywide pie's
# heading and a sentence beneath the pie -- all equal:
#
#            total       capital + operating     general + dedicated      pages
#   2007   223,560  =   35,530 + 188,030       77,313 + 110,717        p75, p77
#   2009   242,706  =   40,714 + 201,992       82,902 + 119,090        p72, p74
#   2010   230,149  =   28,471 + 201,678       83,534 + 118,144        p72, p74
#
# 2010 replaces a value derived from the 2011 book's "0.38% increase over the
# 2010 approved budget", which pinned it to 230.14-230.17; the 2010 book's own
# figure falls inside that range, and the 2011 book's Uses of Funds table prints
# the same 230,149. The 2009 and 2010 books' percentages also reproduce from these
# totals: +2.1% over 2008 and -5.2% from 2009.
#
# The 2007 and 2009 books also state a larger RECOMMENDED total ($225,321 and
# $243,855 thousand), and the 2010 book prints the recommended budget as a pie of
# its own (p28, $229,543 thousand). Those are the city manager's proposals, not
# what council adopted, and none is recorded.
for yr, total, oper, cap, gf, ded in [(2007, 223.560, 188.030, 35.530, 77.313, 110.717),
                                      (2009, 242.706, 201.992, 40.714, 82.902, 119.090),
                                      (2010, 230.149, 201.678, 28.471, 83.534, 118.144)]:
    add(yr, "budget_total", "adopted", total, "musd", "booksocr")
    add(yr, "budget_operating", "adopted", oper, "musd", "booksocr")
    add(yr, "budget_capital", "adopted", cap, "musd", "booksocr")
    add(yr, "budget_operating_general", "adopted", gf, "musd", "booksocr")
    add(yr, "budget_operating_dedicated", "adopted", ded, "musd", "booksocr")

# The 2008 book restates 2007 at $224,336 thousand, $776 thousand above the 2007
# book's own figure, and says why: "the 2007 approved amount has been restated to
# include the Internal Service Funds (ISFs). Beginning with the 2008-09 budget
# process, all ISFs will be included". From 2008 on, the total takes in the ISFs,
# net of the departmental charges that fund them. A change of scope of 0.35%,
# small enough to leave the series whole, but real, and recorded beside the
# adopted figure as staffing's restatements are. It is also what the 2008 book's
# own "6.0% greater than the 2007 approved budget" is measured against:
# 237.781 / 224.336 is +6.0%, where 237.781 / 223.560 would be +6.4%.
add(2007, "budget_total", "restated", 224.336, "musd", "booksocr")

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

# The scanned books' own Sources and Uses tables, read by OCR, fill the years
# between. Each table is three years wide -- ACTUAL two years back, then two
# APPROVED columns -- and where a column overlaps a figure above, it matches to
# the thousand: the 2007 book's 2007 approved uses (89,650) and 2006 approved
# revenue (82,637), the 2009 book's 2008 approved uses (94,238), and the 2010
# book's 2010 approved uses (96,713) and revenue (96,746). 2009's own approved
# figures are printed in both the 2009 and the 2010 book, and the two agree.
#
#   book   page   columns
#   2007   p92    uses:    2005 actual 86,415   2006 approved 82,623   (2007: above)
#   2007   p83    sources: 2005 actual 86,148   (2006: above)          2007 approved 88,520
#   2009   p89    uses:    2007 actual 97,173   (2008: above)          2009 approved 97,219
#   2009   p81    sources: 2007 actual 94,141   2008 approved 93,358   2009 approved 96,167
#   2010   p89    uses:    2008 actual 99,905   2009 approved 97,219   (2010: above)
#   2010   p81    sources: 2008 actual 97,578   2009 approved 96,167   (2010: above)
for yr, basis, v in [(2005, "actual", 86.415), (2006, "adopted", 82.623),
                     (2007, "actual", 97.173), (2008, "actual", 99.905),
                     (2009, "adopted", 97.219)]:
    add(yr, "budget_general_fund", basis, v, "musd", "booksocr")
for yr, basis, v in [(2005, "actual", 86.148), (2007, "adopted", 88.520),
                     (2007, "actual", 94.141), (2008, "adopted", 93.358),
                     (2008, "actual", 97.578), (2009, "adopted", 96.167)]:
    add(yr, "budget_general_fund_revenue", basis, v, "musd", "booksocr")

# --- General Fund, 2013 and 2020-2025, and its revenue from 2014 ---------------
# From 2012 each book states both sides of the General Fund in prose -- "based
# on projected General Fund expenditures of $161.5 million", "...revenues of
# $157.4 million" -- and through 2018 prints each side as a pie whose heading
# gives the exact total. Where the same book also prints the figure to the
# dollar, in the pie heading or the Funds Summary table, the exact one is kept.
#
# These are the same measures as the series above, and that is checked rather
# than assumed. The 2013 book's "General Fund Revenues (Sources)" pie totals
# $109,752 thousand, exactly the TOTAL General Fund of that book's Sources of
# Funds table already recorded for 2013; and the 2014 book's "General Fund
# Expenditures (Uses)" pie totals $115,684 thousand, exactly the 2014 figure
# above. The books' own year-over-year percentages also chain through these
# values, with two exceptions noted in the data dictionary.
#
#   year  uses                                    revenue
#   2013  112,477 (pie, p118)                     (above)
#   2014  (above)                                 115,046 (pie, p106)
#   2015  (above)                                 120,575 (pie, p110)
#   2016  (above)                                 128,264 (pie, p110)
#   2017  (above)                                 138,075 (pie, p112)
#   2018  (above)                                 143,493,428 (pie, p57)
#   2020  161,502,756 (Funds Summary, p41)        157,395,466 (Funds Summary, p41)
#   2021  $146.3 million (prose, p62)             $147.3 million (prose, p52)
#   2022  164,657,129 (pie and Funds Summary)     166,602,128 (Funds Summary, p44)
#   2023  $188.4 million (prose, p15)             $180.5 million (prose, p12)
#   2024  (packet, above)                         $200.5 million (prose, p13)
#   2025  $210.9 million (prose, p13)             $190.6 million (prose, p15)
#   2026  (packet, above)                         $198.8 million (prose, p16)
#
# 2019 is missing from both columns: its book's General Fund pages were never
# read, and the block above gives only the General Fund's operating half.
for yr, v, src in [(2013, 112.477, "booksocr"), (2020, 161.503, "books"),
                   (2021, 146.3, "books"), (2022, 164.657, "books"),
                   (2023, 188.4, "books"), (2025, 210.9, "books")]:
    add(yr, "budget_general_fund", "adopted", v, "musd", src)
for yr, v, src in [(2014, 115.046, "booksocr"), (2015, 120.575, "booksocr"),
                   (2016, 128.264, "booksocr"), (2017, 138.075, "booksocr"),
                   (2018, 143.493, "booksocr"), (2020, 157.395, "books"),
                   (2021, 147.3, "books"), (2022, 166.602, "books"),
                   (2023, 180.5, "books"), (2024, 200.5, "books"),
                   (2025, 190.6, "books"), (2026, 198.8, "books")]:
    add(yr, "budget_general_fund_revenue", "adopted", v, "musd", src)

# --- Citywide revenue, 2011 ------------------------------------------------
# "The 2011 budget is based on projected citywide revenues of $224,912,000.
# This represents a 0.29% increase over the total revenues projected for the
# 2010 approved budget." That percentage once gave 2010 a derived value of
# 224.25-224.27; the 2010 book's own pie, below, gives 224,268.
add(2011, "revenue_total", "adopted", 224.912, "musd", "books")

# --- Citywide staffing levels, 2002-2026 -----------------------------------
# ONE series, not two. The early books count "standard FTEs" with an explicit
# scope footnote while the later ones say "citywide staffing level", which makes
# them look like different measures whose offset no book lets you measure -- and
# this dataset once split them on that ground, as staffing_fte_standard before
# 2012 and staffing_fte after.
#
# Three books settle it, by printing both labels for the same number:
#
#   2016 p120  "...includes a citywide staffing level of 1,419 FTE."
#              Figure 5-09: Staffing Levels: Standard FTEs 2002-2016 ... 1,419 FTE
#   2018 p68   "...includes a citywide staffing level of 1,451 FTE."
#              Staffing Levels: Standard FTEs 2002 to 2018
#   2022 p46   "...includes a citywide staffing level of 1,460.71"  (same figure)
#
# The headline number IS the endpoint of a chart the book itself titles "Standard
# FTEs", and the city charts that series continuously from 2002. So the two are
# the same measure, and splitting them would discourage a comparison the city
# makes itself.
#
# 2012 and 2013 come from the same books' "Staffing Levels in Standard FTEs by
# Department" tables.
#
# So do 2014-2018. From 2015 each book's "Staffing Levels by Department" table
# prints the prior year as approved and as adjusted, then its own year, with a
# variance column that checks: 1,358.77 - 1,299.58 = 59.19 in the 2015 book,
# 1,419.12 - 1,383.12 = 36.00 in 2016, 1,447.36 - 1,427.24 = 20.12 in 2017, and
# 1,451.09 - 1,447.36 = 3.73 in 2018. That gives 2014 from the 2015 book's
# "2014 Approved" column, and the exact figures behind the prose's "1,419",
# "1,447" and "1,451", which they replace. pypdf's text of these tables is
# spaced apart ("1, 358. 77") but every digit is there.
#
# The 2007, 2009 and 2010 books, which survive only as scans, confirm 2005-2010
# to the hundredth. Read by OCR, each book's "Summary of Standard FTEs by City
# Department" gives three years exactly as the born-digital books do, and its
# printed variance column checks: 1,251.34 - 1,218.84 = 32.50 (2007 book),
# 1,288.52 - 1,281.17 = 7.35 (2009), 1,248.24 - 1,288.52 = -40.28 (2010). The
# values stay sourced to `books`, which read them first.
for yr, v in [(2003, 1290.69), (2004, 1200.68), (2005, 1212.11), (2006, 1218.84),
              (2007, 1251.34), (2008, 1281.17), (2009, 1288.52), (2010, 1248.24),
              (2011, 1228.50), (2012, 1243.20), (2013, 1260.62), (2014, 1286.01),
              (2015, 1358.77), (2016, 1419.12), (2017, 1447.36), (2018, 1451.09),
              (2021, 1375.83), (2022, 1460.71), (2023, 1540.09), (2025, 1539.10),
              (2026, 1548.28)]:
    add(yr, "staffing_fte", "adopted", v, "fte", "books")

# Later books restate earlier years slightly. Each year above keeps its OWN
# book's figure; the most recent restatement is recorded beside it so the
# disagreement is visible rather than averaged away. 2011 was restated twice --
# 1,230.50 in the 2012 book, then 1,231.25 in the 2013 book -- and only the
# latter is carried, because two rows would share one (year, measure, basis) key.
#
# The 2015-2017 books call their restatement "Adjusted" ("adjustments remove
# changes approved and incorporated after the passage of the ... Approved
# Budget"), and the 2021-2023 books "Revised Staffing". For 2020 the revised
# figure, 1,456.86 in the 2021 book, is the only one in hand; 2020's own book's
# staffing table was never read, so 2020 has no adopted row yet. 2022's revision
# is in the 2023 book, whose table pypdf cannot read.
for yr, v in [(2011, 1231.25), (2012, 1244.76), (2014, 1299.58), (2015, 1383.12),
              (2016, 1427.24), (2020, 1456.86), (2021, 1402.20)]:
    add(yr, "staffing_fte", "restated", v, "fte", "books")
add(2022, "staffing_fte", "restated", 1491.71, "fte", "booksocr")

# 2002, from a "History of Standard FTEs" chart data table in the 2011 book,
# recovered by OCR. Treat it with more caution than the rest of the series: nine
# of that table's other eleven columns match values sourced independently from
# other books to the hundredth, but ONE does not -- it gives 2006 as 1,218.34
# where the 2006-2007, 2007 and 2008 books all say 1,218.84, and where the
# 2006-2007 book's printed variance (1,218.84 - 1,212.11 = 6.73) confirms
# 1,218.84. So the table carries at least one single-digit misread, and 2002 has
# no second source.
#
# 2001 is in the same table and is NOT recorded: the chart is titled "2002 to
# 2011", so the 2001 column contradicts its own heading and nothing corroborates
# it.
add(2002, "staffing_fte", "adopted", 1304.69, "fte", "booksocr")

# 2017's own sentence, read by OCR, says "a citywide staffing level of 1,447
# FTE" in the same wording and "Figure 5-09" context the 2016 and 2018 books use;
# its table, in the loop above, gives the exact 1,447.36.

# 2024, from the 2024 book's "By the Numbers" panel, read by OCR: "1509.13
# FULL-TIME EQUIVALENTS (EMPLOYEES)". The 2023 and 2025 books print their own
# citywide staffing levels, 1,540.09 and 1,539.10, in the same panel. 2024 sits 31
# FTE below both neighbours, which looks like a misread and is not: the 2025 book
# calls its 1,539.10 "an increase of 2.0% from 2024", which puts 2024 at 1,508.9.
add(2024, "staffing_fte", "adopted", 1509.13, "fte", "booksocr")

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

# --- The revenue big movers, 2005-2010 and 2013-2026 ---------------------------
# The same citywide revenue chart from every other book, recorded as for 2011 and
# 2012: the slices that map onto a revenue_* category, and the rest carried
# together as revenue_other_unmapped, so each year still sums to its own total.
# That remainder is this dataset's arithmetic, never a printed figure.
#
# 2005-2010: "Sources of Funds" pies. 2007, 2009 and 2010 were read by OCR from
# scans, and 2008 from a page (p73) whose pypdf text has every number but
# scrambles which label each belongs to; pypdf reads 2005's and 2006's cleanly.
# Each sums to its printed total exactly:
#
#   year  page  total     sales    utility  property  intergov   unmapped slices
#   2005  p65   185,885   71,240   38,422   20,432     7,588     Other, Parks & Recreation,
#                                                                Plng & Develop Fees, Bond Proceeds
#   2006  p60   192,220   75,351   39,737   20,657     7,622     Other, Plng & Develop Fees,
#                                                                Parks & Recreation
#   2007  p78   213,503   81,567   41,691   21,487    19,011     Other, Parks & Recreation,
#                                                                Plng & Develop Fees, TIF
#                                                                for Garage at 10th & Walnut
#   2008  p73   224,261   87,729   43,496   22,028    14,390     Other, Parks & Recreation,
#                                                                Plng & Develop Fees, Bond Proceeds
#   2009  p75   230,643   90,091   44,264   23,153    12,901     Other, Parks & Recreation,
#                                                                Plng & Develop Fees
#   2010  p75   224,268   84,563   44,137   26,555    12,967     (the same three)
#
# Every one of these pies labels its largest slice "Sales Tax". The 2010 book,
# like 2011's, calls the same source "sales/use taxes", the 2009 book describes it
# with the combined sales and use tax rate, and from 2013 the charts say "Sales
# and Use Tax" outright, so it is recorded as the aggregate, revenue_sales_use_tax.
#
# 2010's total replaces a value derived from the 2011 book's "0.29% increase",
# which pinned it to 224.25-224.27. The 2010 book's own 224,268 falls inside that
# range, and its "2.8% decrease over the total revenues projected for the 2009
# approved budget" reproduces against 2009's 230,643.
#
# 2013-2022: "Citywide Revenues (Sources)", as a pie to 2017 and a donut after,
# each on a page already read by OCR, which also pairs labels with numbers
# where pypdf's text does not:
#
#   year  page  total           sales        utility     property    intergov
#   2013  p101  248,484         97,528       47,626      31,732      10,179 ("Intergovernmental Grants")
#   2014  p100  260,471         102,779      48,274      32,356      11,225
#   2015  p104  313,338         115,396      69,251      32,345       9,687
#   2016  p104  319,535         124,602      62,285      33,442       3,050
#   2017  p106  315,525         127,931      60,988      39,047       4,210
#   2018  p50   390,897,759     125,998      65,155      46,451      (inside "Other")
#   2019  p47   359,019,830     136,327      65,978      47,656      17,194
#   2020  p45   360,262,688     137,718,268  69,414,557  49,968,985   8,801,575
#   2021  p50   $337.7 million  129,929,677  71,917,707  50,267,372   9,715,985
#   2022  p48   471,372,041     141,001,909  76,474,200  53,116,630  15,285,634
#
# The 2013-2017 slices, printed rounded to the thousand, sum to within $2
# thousand of their totals. The 2018 and 2022 totals include borrowing: 2018
# charts $51.9M of "Debt Issuance" as a slice, and 2022's "Other" holds $92.3M of
# water and wastewater bond proceeds. Earlier pies carry their small bond
# proceeds the same way (2005 $0.4M, 2008 $1.2M). 2021 prints its total only in
# prose. The OCR of 2019's donut adds eleven rows of invented values -- eight read
# $5,380 -- for sub-items the chart gives only as percentages. The seven real
# slices sum to the printed total exactly; the rest are ignored.
#
# 2023-2026: the books switch to OpenGov's Combined Budget Summary. Its table is
# gross, including internal service charges and transfers between funds, so the
# total recorded is each book's net "total revenue budget", which excludes them.
# That is the same footing as the 2026 figure below. The four mapped categories
# come from the tables and agree to the dollar across the 2023, 2025 and 2026
# books. The 2023 book labels its column "2023 Total Budget", and the 2025 book
# labels the same figures "2023 Adopted Budget", so they are recorded as adopted.
# 2024's own book prints only the table excluding utilities, so 2024 is taken
# from the 2025 book's "2024 Adopted Budget" column. The 2026 book restates
# 2024's and 2025's intergovernmental revenue $496,000 lower each, moving it
# to a new parking line; the earlier books' figures are kept.
#
#   year  total            sales        utility     property    intergov
#   2023  $492 million     173,348,612  83,183,592  53,051,677  24,646,751
#   2024  $461.9 million   176,867,104  89,583,983  61,217,023  13,403,789
#   2025  $492.5 million   180,169,275  94,116,920  59,644,511  23,589,911
#   2026  $507.2 million   179,640,471  97,444,530  61,732,059  18,774,158
#
# 2026's adopted figures equal the recommended ones already recorded from the
# presentation, and are added so the chart file shows 2026 on the adopted basis
# like every other year.
REVENUE_PIES = {
    # year: (total, sales and use, utility, property, intergovernmental, source)
    2005: (185.885, 71.240, 38.422, 20.432, 7.588, "books"),
    2006: (192.220, 75.351, 39.737, 20.657, 7.622, "books"),
    2007: (213.503, 81.567, 41.691, 21.487, 19.011, "booksocr"),
    2008: (224.261, 87.729, 43.496, 22.028, 14.390, "booksocr"),
    2009: (230.643, 90.091, 44.264, 23.153, 12.901, "booksocr"),
    2010: (224.268, 84.563, 44.137, 26.555, 12.967, "booksocr"),
    2013: (248.484, 97.528, 47.626, 31.732, 10.179, "booksocr"),
    2014: (260.471, 102.779, 48.274, 32.356, 11.225, "booksocr"),
    2015: (313.338, 115.396, 69.251, 32.345, 9.687, "booksocr"),
    2016: (319.535, 124.602, 62.285, 33.442, 3.050, "booksocr"),
    2017: (315.525, 127.931, 60.988, 39.047, 4.210, "booksocr"),
    2018: (390.898, 125.998, 65.155, 46.451, None, "booksocr"),
    2019: (359.020, 136.327, 65.978, 47.656, 17.194, "booksocr"),
    2020: (360.263, 137.718, 69.415, 49.969, 8.802, "booksocr"),
    2021: (337.7, 129.930, 71.918, 50.267, 9.716, "booksocr"),
    2022: (471.372, 141.002, 76.474, 53.117, 15.286, "booksocr"),
    2023: (492.0, 173.349, 83.184, 53.052, 24.647, "books"),
    2024: (461.9, 176.867, 89.584, 61.217, 13.404, "booksocr"),
    2025: (492.5, 180.169, 94.117, 59.645, 23.590, "books"),
    2026: (507.2, 179.640, 97.445, 61.732, 18.774, "books"),
}
# 2024's total is its own book's prose, read by pypdf; its categories are the
# 2025 book's table, read by OCR.
TOTAL_SOURCE = {2024: "books"}
for yr, (total, su, ut, pt, ig, src) in REVENUE_PIES.items():
    add(yr, "revenue_total", "adopted", total, "musd", TOTAL_SOURCE.get(yr, src))
    mapped = [("revenue_sales_use_tax", su), ("revenue_utility", ut),
              ("revenue_property_tax", pt), ("revenue_intergovernmental", ig)]
    for measure, v in mapped:
        if v is not None:
            add(yr, measure, "adopted", v, "musd", src)
    add(yr, "revenue_other_unmapped", "adopted",
        round(total - sum(v for _m, v in mapped if v is not None), 3), "musd", src)

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
    # Empty on purpose. Every pie year, 2005-2022, comes from PIE_LINES below
    # and is folded in from there; a year typed here as well would be counted
    # twice, which the reconciliation against budget_total would catch.
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
     "Citywide allocations and contingency. Partly the counterpart of the "
     "General Government line of 2005-2012, which likely holds the same kind "
     "of non-departmental items -- so administration and citywide_debt trade "
     "content across the series."),
]
# These go into a SEPARATE measure family from the pie years -- see the
# aggregation below for why.
DEPARTMENT_FILTERED_LINES = []
for label, bucket, v24, v25, v26, note in DEPARTMENT_2024_2026:
    for yr, v in ((2024, v24), (2025, v25), (2026, v26)):
        DEPARTMENT_FILTERED_LINES.append((yr, label, v, bucket, note))

# --- The revenue big movers, 2012 --------------------------------------------
# The 2012 book's citywide revenue pie, recovered by OCR, seven slices summing to
# its stated $231,945 thousand exactly. Only the four that map onto an existing
# revenue_* category are recorded; the other three (Other $44.424M, Parks &
# Recreation $8.206M, Planning and Development Fees $5.518M) are carried together
# as revenue_other_unmapped so the year still balances, exactly as 2011 is.
add(2012, "revenue_total", "adopted", 231.945, "musd", "booksocr")
for measure, v in [("revenue_sales_use_tax", 93.209), ("revenue_utility", 45.392),
                   ("revenue_property_tax", 30.868), ("revenue_intergovernmental", 4.328)]:
    add(2012, measure, "adopted", v, "musd", "booksocr")
add(2012, "revenue_other_unmapped", "adopted",
    round(231.945 - (93.209 + 45.392 + 30.868 + 4.328), 3), "musd", "booksocr")

# --- Citywide spending by department, from the books' own pies ---------------
# Eighteen years of the citywide "Uses of Funds" pie, 2005-2022, validated by
# construction: each year's slices sum to the citywide total that same book
# publishes, to the thousand. budget-books-extract.py reads nine of them from
# pypdf's text; the other nine need OCR (see the blocks below). See the extractor for how the
# citywide pie is told apart from the General Fund and excluding-utilities pies
# that share its heading.
#
# Labels are reproduced exactly as each document prints them, letter-spacing
# damage and all ("Fir e", "Parks & Re cr e ation"), because that string is what
# a reader would search the PDF for. The bucket each one maps to is in
# PIE_BUCKETS below, and the per-year result is written to
# budget-history-department-crosswalk.csv.
#
# (year, label as printed, $M)
PIE_LINES = [
    (2005, 'Public Works', 67.43),
    (2005, 'Police', 22.68),
    (2005, 'Parks & Re cr e ation', 21.06),
    (2005, 'Open Space/ Real E state', 20.658),
    (2005, 'General Governm ent', 17.284),
    (2005, 'Housing/Human Svcs', 12.753),
    (2005, 'Fir e', 10.996),
    (2005, 'Administrative Svcs', 8.225),
    (2005, 'Planning & De ve lopm e nt Services', 6.233),
    (2005, 'Library', 5.74),
    (2005, 'De bt', 2.668),
    (2005, 'Arts', 0.44),
    (2006, 'Public Works', 66.734),
    (2006, 'Police', 23.415),
    (2006, 'Open Space/ Mountain Parks', 22.188),
    (2006, 'Parks & Re cr e ation', 20.899),
    (2006, 'General Governm e nt', 17.208),
    (2006, 'Housing/Human Svcs', 13.339),
    (2006, 'Fire', 11.258),
    (2006, 'Administrative Svcs', 9.849),
    (2006, 'Planning & Development Services', 6.465),
    (2006, 'Library', 5.977),
    (2006, 'De bt', 2.317),
    (2006, 'Arts', 0.451),
    (2014, 'Public Works', 98.303),
    (2014, 'Police', 32.041),
    (2014, 'Open Spaceand Mountain Parks', 26.622),
    (2014, 'Parks and Recreation', 26.009),
    (2014, 'Fire', 17.565),
    (2014, 'Internal Services', 14.821),
    (2014, 'General Governance', 10.214),
    (2014, 'DUHMD/ PS', 8.556),
    (2014, 'Library and Arts', 8.147),
    (2014, 'Community Planning and Sustainability', 7.963),
    (2014, 'Human Services', 6.689),
    (2014, 'Housing', 5.142),
    (2014, 'Citywide Debt', 5.112),
    (2014, 'ESand EUD', 2.312),
    (2015, 'Public Works', 132.531),
    (2015, 'Police', 33.666),
    (2015, 'Open Space and Mountain Parks', 29.712),
    (2015, 'Parks and Recreation', 25.076),
    (2015, 'Fire', 18.151),
    (2015, 'Internal Services', 16.009),
    (2015, 'DUHMD/PS', 12.123),
    (2015, 'General Governance', 11.227),
    (2015, 'Community Planning and Sustainability', 8.644),
    (2015, 'Library and Arts', 8.226),
    (2015, 'ESand EUD', 6.943),
    (2015, 'Human Services', 6.728),
    (2015, 'Citywide Debt', 5.105),
    (2015, 'Housing', 4.956),
    (2016, 'Public Works', 133.533),
    (2016, 'Open Spaceand Mountain Parks', 34.251),
    (2016, 'Police', 34.037),
    (2016, 'Parks and Recreation', 25.355),
    (2016, 'Internal Services', 21.798),
    (2016, 'Fire', 18.629),
    (2016, 'Planning, Housing and Sustainability', 14.234),
    (2016, 'General Governance', 13.027),
    (2016, 'Community Vitality', 12.123),
    (2016, 'Library and Arts', 8.514),
    (2016, 'Human Services', 7.097),
    (2016, 'Citywide Debt', 5.101),
    (2017, 'Public Works', 120.033),
    (2017, 'Police', 34.76),
    (2017, 'Open Space and Mountain Parks', 33.658),
    (2017, 'Parks and Recreation', 27.321),
    (2017, 'Internal Services', 24.016),
    (2017, 'Fire', 19.092),
    (2017, 'Planning, Housing and Sustainability', 15.178),
    (2017, 'General Governance', 14.502),
    (2017, 'Community Vitality', 11.098),
    (2017, 'Library and Arts', 9.329),
    (2017, 'Human Services', 7.774),
    (2017, 'Citywide Debt', 5.105),
    (2020, 'Public Works', 145.341),
    (2020, 'Public Safety', 62.318),
    (2020, 'Internal Services', 29.044),
    (2020, 'Parks & Recreation', 28.784),
    (2020, 'Open Space & Mountain Parks', 28.275),
    (2020, 'Housing & Human Services', 21.636),
    (2020, 'General Governance', 18.323),
    (2020, 'Community Vitality', 12.112),
    (2020, 'Library & Arts', 11.305),
    (2020, 'Climate Initiatives', 6.377),
    (2020, 'Planning', 6.203),
    (2021, 'PW - Utilities', 84.924),
    (2021, 'Police', 36.887),
    (2021, 'PW - Transportation & Mobility', 30.84),
    (2021, 'Parks & Recreation', 28.475),
    (2021, 'Open Space & Mountain Parks', 28.306),
    (2021, 'Internal Services', 25.485),
    (2021, 'Fire - Rescue', 21.325),
    (2021, 'Housing & Human Services', 20.053),
    (2021, 'General Governance', 16.865),
    (2021, 'Planning', 13.033),
    (2021, 'Community Vitality', 11.719),
    (2021, 'Library & Arts', 9.252),
    (2021, 'Facilities & Fleet', 6.77),
    (2021, 'Climate Initiatives', 5.758),
    (2021, 'Municipal Court', 2.051),
    (2022, 'Utilities', 174.198),
    (2022, 'Transportation & Mobility', 41.851),
    (2022, 'Police', 40.486),
    (2022, 'Open Space & Mountain Parks', 30.991),
    (2022, 'Internal Services', 28.691),
    (2022, 'Parks & Recreation', 28.19),
    (2022, 'Fire- Rescue', 23.421),
    (2022, 'Housing & Human Services', 22.489),
    (2022, 'Planning & Development Services', 14.204),
    (2022, 'General Governance', 13.862),
    (2022, 'Community Vitality', 12.992),
    (2022, 'Library & Arts', 11.971),
    (2022, 'Facilities & Fleet', 10.581),
    (2022, 'Climate Initiatives', 6.373),
    (2022, 'Municipal Court', 2.219),
    # -- 2011, 2012, 2013, 2018 and 2019: recovered by OCR (budget-books-ocr.py
    #    tier 2) from pages pypdf mangles, so their source is booksocr
    #    (PIE_OCR_YEARS). Every one sums to its own published total; the data
    #    dictionary's caveat on OCR lists what OCR got wrong on the same pages.
    # 2011
    (2011, 'Police', 29.105),
    (2011, 'PW/ Utilities', 46.571),
    (2011, 'Parks & Recreation', 24.86),
    (2011, 'Open Space/ Mtn Prks', 24.518),
    (2011, 'PW/ Transportation', 20.808),
    (2011, 'Fire', 14.983),
    (2011, 'Housing/ Human Svcs', 12.964),
    (2011, 'Gen Govrnmt', 11.951),
    (2011, 'Admin Svcs', 9.925),
    (2011, 'DUHMD/ Prkng Svcs', 9.679),
    (2011, 'PW/ DSS', 9.069),
    (2011, 'Library/ Arts', 7.562),
    (2011, 'Comm Plnng & Sustainability', 6.344),
    (2011, 'Debt', 2.691),
    # 2012
    (2012, 'Public Works', 77.34),
    (2012, 'Police', 29.593),
    (2012, 'Open Space/Mtn Parks', 25.557),
    (2012, 'Parks and Rec', 24.229),
    (2012, 'Fire', 15.552),
    (2012, 'Total Gen Gov', 13.627),
    (2012, 'Housing/Human Services', 12.066),
    (2012, 'Admin Services', 11.845),
    (2012, 'DUHMD/Pkg Svcs', 8.868),
    (2012, 'Library and Arts', 7.863),
    (2012, 'Comm Planning and Sust', 7.644),
    (2012, 'Debt', 4.776),
    # 2013
    (2013, 'Public Works', 90.008),
    (2013, 'Police', 31.747),
    (2013, 'Open Space and Mountain Parks', 25.528),
    (2013, 'Parks and Recreation', 25.042),
    (2013, 'Fire', 16.63),
    (2013, 'Internal Services', 12.666),
    (2013, 'General Governance', 9.615),
    (2013, 'DUHMD/PS', 9.095),
    (2013, 'Library and Arts', 8.133),
    (2013, 'Human Services', 6.822),
    (2013, 'Community Planning and Sustainability', 6.536),
    (2013, 'Citywide Debt', 5.379),
    (2013, 'Housing', 5.288),
    (2013, 'ES and EUD', 2.203),
    # 2018
    (2018, 'Public Works', 170.485),
    (2018, 'Police', 35.762),
    (2018, 'OSMP', 33.38),
    (2018, 'Parks & Rec.', 30.747),
    (2018, 'Internal Services', 24.501),
    (2018, 'Fire', 20.651),
    (2018, 'PH&S', 18.55),
    (2018, 'General Governance', 15.148),
    (2018, 'Community Vitality', 12.921),
    (2018, 'Human Services', 10.128),
    (2018, 'Library & Arts', 9.508),
    (2018, 'Citywide Debt', 7.265),
    (2018, 'Energy', 0.165),
    # 2019
    (2019, 'Public Works', 124.665),
    (2019, 'Public Safety', 59.227),
    (2019, 'Internal Services', 32.701),
    (2019, 'OSMP', 27.551),
    (2019, 'Parks & Recreation', 26.494),
    (2019, 'Housing & Human Services', 23.218),
    (2019, 'General Governance', 20.814),
    (2019, 'Community Vitality', 11.184),
    (2019, 'Library & Arts', 10.344),
    (2019, 'Energy Strategy', 8.834),
    (2019, 'Planning & Sustainability', 8.714),
    # -- 2007, 2008, 2009 and 2010: recovered by OCR in tiers 1 and 3. 2007, 2009
    #    and 2010 are scans. 2008 is born-digital, but its pie is on p72 and the
    #    page dump held only p71 and p73; tier 3, which reads two pages either
    #    side of every published figure, reached it from the summary block on
    #    p71. Each pie's heading prints its book's own citywide total and the
    #    slices sum to it exactly. For 2010 that is the pie on p74, not the one on
    #    p28, which is the city manager's recommended budget ($229,543 thousand).
    # 2007
    (2007, 'Public Works', 79.216),
    (2007, 'Police', 25.456),
    (2007, 'Open Space/ Mtn Parks', 24.744),
    (2007, 'Parks & Rec', 22.742),
    (2007, 'Gen Gvmnt', 18.853),
    (2007, 'HHS', 13.728),
    (2007, 'Fire', 12.427),
    (2007, 'Admin Svcs', 10.453),
    (2007, 'Plng & Dev Svcs', 6.849),
    (2007, 'Library', 6.289),
    (2007, 'Debt', 2.317),
    (2007, 'Arts', 0.486),
    # 2008
    (2008, 'Public Works', 84.416),
    (2008, 'Police', 26.818),
    (2008, 'Open Space/ Mtn Parks', 24.96),
    (2008, 'Parks & Rec', 23.489),
    (2008, 'Gen Gvnmnt', 22.464),
    (2008, 'HHS', 13.895),
    (2008, 'Fire', 12.739),
    (2008, 'Admin Svcs', 11.865),
    (2008, 'Plng & Dev Svcs', 7.605),
    (2008, 'Library', 6.717),
    (2008, 'Debt', 2.311),
    (2008, 'Arts', 0.502),
    # 2009
    (2009, 'Public Works', 82.647),
    (2009, 'Police', 27.939),
    (2009, 'Open Space/ Mtn Parks', 25.788),
    (2009, 'Parks & Rec', 25.611),
    (2009, 'Gen Gvrnmnt', 21.52),
    (2009, 'Housing/ Human Svcs', 15.502),
    (2009, 'Fire', 13.319),
    (2009, 'Admin Svcs', 12.449),
    (2009, 'Plng & Dev Svcs', 8.147),
    (2009, 'Library', 6.992),
    (2009, 'Debt', 2.261),
    (2009, 'Arts', 0.531),
    # 2010
    (2010, 'PW Utilities', 45.119),
    (2010, 'Police', 28.137),
    (2010, 'Open Space/ Mtn Prks', 25.478),
    (2010, 'Parks & Recreation', 24.556),
    (2010, 'PW Transportation', 23.205),
    (2010, 'Fire', 14.666),
    (2010, 'Housing/ Human Svcs', 13.859),
    (2010, 'Gen Gvrnmnt', 10.545),
    (2010, 'PW DSS', 9.955),
    (2010, 'DUHMD/ Prkng Svcs', 9.31),
    (2010, 'Admin Svcs', 8.939),
    (2010, 'Library/ Arts', 7.453),
    (2010, 'Comm Plng & Sustainability', 6.694),
    (2010, 'Debt', 2.233),
]
# The pie years read by OCR. Their rows cite `booksocr` rather than `books`, in
# the dataset and in the crosswalk alike, so a reader can tell a figure pypdf
# read from one Datalab read.
PIE_OCR_YEARS = {2007, 2008, 2009, 2010, 2011, 2012, 2013, 2018, 2019}
if not PIE_OCR_YEARS <= {y for y, _l, _v in PIE_LINES}:
    raise SystemExit("PIE_OCR_YEARS names a year PIE_LINES does not have: "
                     f"{sorted(PIE_OCR_YEARS - {y for y, _l, _v in PIE_LINES})}")


def dept_source(family, year):
    """The source_id for a departmental row: which document, and which reading."""
    if family == "deptexpfiltered":
        return "deptsnapshot2026"
    return "booksocr" if year in PIE_OCR_YEARS else "books"


# Normalized label -> (bucket, why). A note is filled in wherever the
# assignment is a judgment rather than obvious, and those notes are the point of
# this table: seven buckets cannot absorb twenty years of reorganization without
# choices, and a choice nobody can see is indistinguishable from an error.
#
# A note of the form "see:<label>" repeats that label's note, so every row of the
# crosswalk CSV explains itself without sending the reader to another row.
PIE_BUCKETS = {
    # -- public safety ------------------------------------------------------
    "police": ("public_safety", ""),
    "fire": ("public_safety", ""),
    "firerescue": ("public_safety", ""),
    "publicsafety": ("public_safety",
                     "2019 and 2020 do not separate police from fire; their single "
                     "slices, $59.2M and $62.3M, cover both. 2021 splits them "
                     "again at $36.9M and $21.3M."),
    # -- infrastructure -----------------------------------------------------
    "publicworks": ("infrastructure",
                    "One undivided slice, and the reason the buckets are this "
                    "coarse. It holds what later becomes Transportation and "
                    "Mobility, Utilities and Facilities and Fleet. The pies "
                    "print it whole in 2005-2009 and 2012-2020 and divide it "
                    "only in 2010, 2011 and 2021, so no finer bucket holds "
                    "across the series."),
    "pwutilities": ("infrastructure", ""),
    "pwtransportationmobility": ("infrastructure", ""),
    "utilities": ("infrastructure", ""),
    "transportationmobility": ("infrastructure", ""),
    "facilitiesfleet": ("infrastructure", ""),
    "duhmdps": ("infrastructure",
                "Downtown and University Hill Management Division / Parking "
                "Services -- mostly parking operations and district management. "
                "Renamed Community Vitality from 2016."),
    "communityvitality": ("infrastructure",
                          "DUHMD/Parking Services under its later name. Chiefly "
                          "parking and district management, which is why it sits "
                          "with infrastructure rather than with planning, though "
                          "it also carries economic vitality work."),
    # -- parks and open space ----------------------------------------------
    "parksrecreation": ("parks_openspace", ""),
    "parksandrecreation": ("parks_openspace", ""),
    "openspacemountainparks": ("parks_openspace", ""),
    "openspaceandmountainparks": ("parks_openspace", ""),
    "openspacerealestate": ("parks_openspace",
                            "The 2005 name. Renamed Open Space/Mountain Parks in "
                            "2006, and the real-estate functions move elsewhere."),
    # -- community services -------------------------------------------------
    "housinghumansvcs": ("community_services", ""),
    "housinghumanservices": ("community_services", ""),
    "humanservices": ("community_services",
                      "Human services without housing. 2013-2015 print housing "
                      "as a slice of its own, also community_services; 2016-2018 "
                      "fold it into Planning, Housing and Sustainability, in "
                      "planning_climate. The other years combine the two."),
    "housing": ("community_services", "see:humanservices"),
    "library": ("community_services", ""),
    "arts": ("community_services", ""),
    "libraryandarts": ("community_services", ""),
    "libraryarts": ("community_services", ""),
    # -- planning and climate ----------------------------------------------
    "planning": ("planning_climate", ""),
    "planningdevelopmentservices": ("planning_climate",
                                    "Two different things under one name: $6.2M "
                                    "in 2005 for the planning department, $14.2M "
                                    "in 2022 for the development-review "
                                    "enterprise fund. Same bucket, not the same "
                                    "department."),
    "communityplanningandsustainability": ("planning_climate", ""),
    "planninghousingandsustainability": ("planning_climate",
                                         "Absorbs HOUSING, which sits in "
                                         "community_services in the other "
                                         "years, so across 2016-2018 those two "
                                         "buckets trade housing's budget -- "
                                         "about $5M a year when 2013-2015 "
                                         "print it separately."),
    "climateinitiatives": ("planning_climate", ""),
    "esandeud": ("planning_climate",
                 "Energy Strategy and Electric Utility Development -- the "
                 "municipalization effort. Bucketed as climate and energy policy "
                 "rather than as a utility operation, because the city never "
                 "owned the utility. Printed as ES and EUD in 2013-2015, Energy "
                 "in 2018 and Energy Strategy in 2019, with no line of its own in "
                 "2016-2017."),
    # -- administration -----------------------------------------------------
    "generalgovernment": ("administration",
                          "The least comparable line in the crosswalk. It likely "
                          "holds non-departmental items that the 2024-2026 export "
                          "books to Fundwide / Citywide, so administration and "
                          "citywide_debt trade content across the series."),
    "generalgovernance": ("administration", ""),
    "administrativesvcs": ("administration", ""),
    "municipalcourt": ("administration", ""),
    "internalservices": ("administration",
                         "The 2018 book defines it as Finance, HR, IT, General "
                         "Fund capital and other -- mostly administration, but it "
                         "carries some capital, so this bucket is not purely "
                         "overhead."),
    # -- added with the OCR-recovered years. Every one is a naming variant of a
    #    concept already mapped above; the city's own notes on those same pages
    #    confirm the three that carry real content: "General Government is
    #    comprised of City Council, City Manager's Office, City Attorney's Office,
    #    Municipal Court, and several pension and risk management funds",
    #    "Internal Services includes Human Resources, Finance, Information
    #    Technology", and "Public Works groups together Development and Support
    #    Services, Transportation, and Utilities".
    "pwtransportation": ("infrastructure", ""),
    "pwdss": ("infrastructure", "Public Works - Development and Support Services."),
    "duhmdprkngsvcs": ("infrastructure", "see:duhmdps"),
    "duhmdpkgsvcs": ("infrastructure", "see:duhmdps"),
    "openspacemtnprks": ("parks_openspace", ""),
    "openspacemtnparks": ("parks_openspace", ""),
    "osmp": ("parks_openspace", ""),
    "parksandrec": ("parks_openspace", ""),
    "parksrec": ("parks_openspace", ""),
    "commplnngsustainability": ("planning_climate", ""),
    "commplanningandsust": ("planning_climate", ""),
    "planningsustainability": ("planning_climate", ""),
    "phs": ("planning_climate",
            "PH&S is Planning, Housing and Sustainability, abbreviated. Absorbs "
            "HOUSING, which sits in community_services in the other years, so "
            "across 2016-2018 those two buckets trade housing's budget -- about "
            "$5M a year when 2013-2015 print it separately."),
    "energy": ("planning_climate", "see:esandeud"),
    "energystrategy": ("planning_climate", "see:esandeud"),
    "adminsvcs": ("administration", ""),
    "adminservices": ("administration", ""),
    "gengovrnmt": ("administration", "see:generalgovernment"),
    "totalgengov": ("administration", "see:generalgovernment"),
    # -- added with the 2007-2010 pies, which abbreviate differently every year
    "gengvmnt": ("administration", "see:generalgovernment"),
    "gengvnmnt": ("administration", "see:generalgovernment"),
    "gengvrnmnt": ("administration", "see:generalgovernment"),
    "hhs": ("community_services", "Housing and Human Services, abbreviated in the "
                                  "2007 and 2008 pies."),
    "plngdevsvcs": ("planning_climate", "see:planningdevelopmentservices"),
    "commplngsustainability": ("planning_climate", ""),
    # -- citywide and debt --------------------------------------------------
    "debt": ("citywide_debt",
             "General Fund debt only. The pie's own note says non-General-Fund "
             "debt service sits inside the departments, which is true in 2011 "
             "too, so the bucket is consistent -- but it is not all of the "
             "city's debt service."),
    "citywidedebt": ("citywide_debt", "see:debt"),
}


def _slug(label):
    return re.sub(r'[^a-z0-9]', '', label.lower())


# Fold the pies into the same (year, label, value, bucket, note) shape the
# OpenGov cost-center rows use, so one aggregation and one crosswalk cover both.
_unmapped = sorted({_slug(l) for _y, l, _v in PIE_LINES if _slug(l) not in PIE_BUCKETS})
if _unmapped:
    # A new year's pie will bring labels this table has never seen, and a bare
    # KeyError does not say which or what to do about it. Refuse with the list,
    # because the alternative -- defaulting an unknown department into some
    # bucket -- puts a number in a chart that nobody chose to put there.
    raise SystemExit(
        "PIE_BUCKETS has no bucket for: " + ", ".join(_unmapped)
        + "\nAdd each one, with a note if the choice is a judgment call.")


def _bucket_note(slug, via=()):
    """A label's note, following "see:<label>" so each crosswalk row stands alone."""
    note = PIE_BUCKETS[slug][1]
    if not note.startswith("see:"):
        return note
    ref = note[len("see:"):]
    if ref in via or ref not in PIE_BUCKETS or not PIE_BUCKETS[ref][1]:
        raise SystemExit(f"PIE_BUCKETS[{slug!r}] points at {ref!r}, which has no note to repeat")
    return _bucket_note(ref, via + (slug,))


for _yr, _label, _v in PIE_LINES:
    DEPARTMENT_LINES.append((_yr, _label, _v, PIE_BUCKETS[_slug(_label)][0],
                             _bucket_note(_slug(_label))))

BUCKET_ORDER = ["public_safety", "infrastructure", "parks_openspace",
                "community_services", "planning_climate", "administration",
                "citywide_debt"]

# Two families, deliberately not one.
#
# deptexp_*          the books' citywide pies, 2005-2022. Every fund, comparable
#                    year to year.
# deptexpfiltered_*  the OpenGov cost-center export, 2024-2026, taken with a
#                    23-fund filter that omits the utility, debt-service and
#                    internal-service funds.
#
# Both sum to their year's citywide total, so no arithmetic check can tell them
# apart -- and that is exactly the trap. Their COMPOSITION is incomparable.
# Infrastructure is 51.8% of citywide spending in 2022 and 15.8% in 2026, not
# because Boulder stopped maintaining anything but because the filter moves
# nearly all utility spending out of the departments and into the balancing line.
# Charting the two families as one series shows infrastructure halving.
#
# Separate prefixes make that mistake require effort rather than inattention.
# One unfiltered re-export of the same view collapses them back into one family.
for family, lines in (("deptexp", DEPARTMENT_LINES),
                      ("deptexpfiltered", DEPARTMENT_FILTERED_LINES)):
    for yr in sorted({y for y, *_ in lines}):
        by_bucket = collections.defaultdict(float)
        for y, _label, v, bucket, _note in lines:
            if y == yr:
                by_bucket[bucket] += v
        for bucket in BUCKET_ORDER:
            if bucket in by_bucket:
                add(yr, f"{family}_{bucket}", "adopted", round(by_bucket[bucket], 3),
                    "musd", dept_source(family, yr))

# The 2024-2026 export was taken with a fund filter that leaves out the utility,
# debt-service and internal-service funds, so its twenty cost centers add up to
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
    add(yr, "deptexpfiltered_funds_outside_export", "derived",
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

# --- Staffing CHANGES, 2026-2027 --------------------------------------------
# Year-over-year changes from the packets and releases. The level series is
# staffing_fte above; the two do not reconcile (see the data dictionary).
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
add(2027, "yoy_general_fund_pct", "recommended", 3.09, "pct", "glance2027")

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
# Reconciliation -- fail loudly rather than publish an internally broken series
# --------------------------------------------------------------------------
# What each check is called in budget-history-validation.md, and its tolerance.
CHECKS = {
    "keys": ("One row per (year, measure, basis)", "exact"),
    "dept": ("Department buckets, plus any balancing line, sum to `budget_total`", "$0.05M"),
    "bucket": ("A department label keeps its bucket from year to year, or a note says why", "exact"),
    "halves": ("General Fund half + dedicated half = `budget_operating`", "$0.2M"),
    "opcap": ("`budget_operating` + `budget_capital` = `budget_total`", "$0.2M"),
    "salesuse": ("Sales and use tax components sum to `salesuse_total`", "$0.05M"),
    "revenue": ("Revenue components sum to that year's `revenue_total`", "$0.02M"),
    "snapshot": ("OpenGov snapshot components sum to their totals, and net = revenue - expense", "$10"),
}


def reconcile():
    """Check every published total against the sum of its published parts.

    Returns (problems, residuals, checked). `checked` maps each CHECKS key to
    [cases checked, largest miss, where] for the validation report.

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
    checked = {k: [0, 0.0, ""] for k in CHECKS}

    def tally(check, miss, where):
        c = checked[check]
        c[0] += 1
        if abs(miss) > c[1] + 1e-9:
            c[1], c[2] = abs(miss), where

    # One row per (year, measure, basis). Two rows with the same key are not a
    # tidy-data violation to shrug at: `idx` keeps only the last of them, so a
    # duplicate makes the checks below pass while the CSV ships both values and
    # a reader's pivot silently picks whichever their tool prefers. This caught
    # 2017 carrying its operating budget twice, rounded in prose and exact in
    # the summary block.
    seen = collections.Counter((r["year"], r["measure"], r["basis"]) for r in ROWS)
    for (yr, measure, basis), n in sorted(seen.items()):
        tally("keys", 0, "")
        if n > 1:
            vals = sorted({r["value"] for r in ROWS
                           if (r["year"], r["measure"], r["basis"]) == (yr, measure, basis)})
            problems.append(f"{yr} {measure} [{basis}] appears {n} times: {vals}")

    # The departmental buckets, plus the balancing line where there is one, must
    # add up to the published citywide total. For the pie years this is exact by
    # construction (each pie sums to its own total); for 2024-2026 it holds only
    # because the balancing line is defined as the difference, so what this
    # really guards is a mistyped cost center. A year with no total to check
    # against is itself a problem, not a pass.
    for family, lines in (("deptexp_", DEPARTMENT_LINES),
                          ("deptexpfiltered_", DEPARTMENT_FILTERED_LINES)):
        for yr in sorted({y for y, *_ in lines}):
            parts = sum(v for (y, m, b), v in idx.items()
                        if y == yr and m.startswith(family))
            total = idx.get((yr, "budget_total", "adopted"))
            if total is None:
                problems.append(f"{yr}: {family}* has no adopted budget_total to sum to")
                continue
            tally("dept", parts - total, f"{yr} {family}*")
            if abs(parts - total) > TOL:
                problems.append(
                    f"{yr}: {family}* buckets sum {parts:,.3f} != "
                    f"budget_total {total:,.3f}")

    # The same department label must land in the same bucket every year it
    # appears, unless the line says why not. Without this, a relabeled
    # department could drift between buckets and the series would show a
    # transfer of money that never happened.
    seen_bucket = {}
    for yr, label, _v, bucket, note in DEPARTMENT_LINES + DEPARTMENT_FILTERED_LINES:
        key = re.sub(r'[^a-z0-9]', '', label.lower())
        if key in seen_bucket and seen_bucket[key][0] != bucket and not note:
            problems.append(
                f"{label!r} is {bucket} in {yr} but {seen_bucket[key][0]} in "
                f"{seen_bucket[key][1]} with no note explaining the change")
        if key not in seen_bucket:
            tally("bucket", 0, "")
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
            if None not in (g, d, o_):
                tally("halves", (g + d) - o_, f"{yr} {basis}")
                if abs((g + d) - o_) > 0.2:
                    problems.append(
                        f"{yr} {basis}: general {g} + dedicated {d} = {g + d:.3f} "
                        f"!= operating {o_}")
            t = idx.get((yr, "budget_total", basis))
            o = idx.get((yr, "budget_operating", basis))
            c = idx.get((yr, "budget_capital", basis))
            if None not in (t, o, c):
                tally("opcap", (o + c) - t, f"{yr} {basis}")
                if abs((o + c) - t) > 0.2:
                    problems.append(
                        f"{yr} {basis}: operating+capital={o + c:.2f} != total={t:.2f}")

    for (yr, basis), vals in sorted(SALESUSE.items()):
        parts = [v for v in vals[:-1] if v is not None]
        delta = round(sum(parts) - vals[-1], 2)
        tally("salesuse", delta, f"{yr} {basis}")
        if abs(delta) > TOL:
            problems.append(
                f"{yr} {basis} sales/use components={sum(parts):.2f} != total={vals[-1]:.2f}")
        elif delta:
            residuals.append((yr, basis, delta))

    # Revenue components against their own year's total, keyed on (year, basis)
    # so each year is checked against itself. (Summing every revenue_* row in the
    # dataset against one total was right only while one year had a revenue mix.)
    rev_years = collections.defaultdict(float)
    for r in ROWS:
        if r["measure"].startswith("revenue_") and r["measure"] != "revenue_total":
            rev_years[(r["year"], r["basis"])] += r["value"]
    for (yr, basis), parts in sorted(rev_years.items()):
        tot = idx.get((yr, "revenue_total", basis))
        if tot is None:
            problems.append(f"{yr} {basis}: revenue components with no revenue_total")
            continue
        tally("revenue", parts - tot, f"{yr} {basis}")
        if abs(parts - tot) > 0.02:
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
            tally("snapshot", (s - total[i]) / 1e6, f"{yr} {label}")
            if abs(s - total[i]) > 10:
                problems.append(
                    f"{yr} snapshot {label} components={s:,.0f} != total={total[i]:,.0f}")
        net = SNAPSHOT_REVENUE_TOTAL[i] - SNAPSHOT_EXPENSE_TOTAL[i]
        tally("snapshot", (net - SNAPSHOT_NET[i]) / 1e6, f"{yr} net")
        if abs(net - SNAPSHOT_NET[i]) > 10:
            problems.append(
                f"{yr} snapshot net={net:,.0f} != stated={SNAPSHOT_NET[i]:,.0f}")

    return problems, residuals, checked


# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------
# The headline series, one row per year, and the order of preference when a
# year carries several bases. One rule throughout. A budget series takes what
# council adopted, or what the manager recommended for the year not yet
# adopted, and falls back to `derived` only where the data dictionary documents
# the derivation. A revenue-collection series takes actuals for closed years
# and the adopted or forecast figure for open ones. `actual` is deliberately not
# a fallback for a budget series: an actual among adopted neighbours answers a
# different question, and a chart drawn from this file would show the
# difference as a jump.
WIDE = [
    ("budget_total", ["adopted", "recommended"]),
    ("budget_operating", ["adopted", "recommended"]),
    ("budget_capital", ["adopted", "recommended"]),
    ("budget_general_fund", ["adopted", "recommended", "derived"]),
    ("budget_general_fund_revenue", ["adopted", "recommended"]),
    ("staffing_fte", ["adopted"]),
    ("revenue_total", ["adopted", "recommended", "derived"]),
    ("revenue_sales_use_tax", ["adopted", "recommended"]),
    ("revenue_property_tax", ["adopted", "recommended"]),
    ("revenue_utility", ["adopted", "recommended"]),
    ("salesuse_total", ["actual", "adopted", "forecast"]),
    ("property_tax_revenue", ["actual", "adopted", "forecast"]),
    ("gap_general_fund", ["identified", "recommended", "forecast"]),
]

LONG_COLUMNS = ["year", "measure", "basis", "value", "unit", "source_id"]
CROSSWALK_COLUMNS = ["year", "measure_family", "source_label", "bucket",
                     "value_musd", "pct_of_year_departmental", "source_id", "note"]
PROVENANCE_COLUMNS = ["source_id", "title", "publisher", "date", "url",
                      "retrieved", "n_values", "notes"]

# Typographic punctuation, spelled in ASCII on the way out. The CSVs are UTF-8,
# but Excel opens a CSV that has no byte-order mark in the system's legacy
# encoding and turns an em dash into "â€”" -- and Excel is where most readers of
# a city budget will open these.
_ASCII = str.maketrans({"—": "--", "–": "-", "‑": "-", "−": "-",
                        "‘": "'", "’": "'", "“": '"', "”": '"',
                        "…": "...", " ": " ", "×": "x"})


def write_csv(path, header, rows):
    """One output CSV: UTF-8, LF line endings, typographic punctuation as ASCII."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for row in rows:
            w.writerow([c.translate(_ASCII) if isinstance(c, str) else c for c in row])


def span(years):
    """[2004, 2005, 2006, 2008] -> '2004–2006, 2008'."""
    years, runs = sorted(set(years)), []
    for y in years:
        if runs and y == runs[-1][1] + 1:
            runs[-1][1] = y
        else:
            runs.append([y, y])
    return ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs)


def write_validation(path, checked, residuals, cross_rows, wide_rows):
    """budget-history-validation.md: counts, coverage and checks, from the data.

    Everything a hand-maintained document would let drift -- row counts, the
    years each measure covers, how many cases each check saw -- is written here
    on every run instead, and the data dictionary points to it.
    """
    years = [r["year"] for r in ROWS]
    cross_years = [r[0] for r in cross_rows]
    L = ["# Budget history: validation report", "",
         "Written by `budget-history.py` every time it runs, from the rows it has",
         "just built. Nothing here is typed by hand, so where this file and the",
         "data dictionary disagree about a count or a year, this file is right.", "",
         "## Files", "",
         "| File | Rows | Years |", "|---|---:|---|",
         f"| `budget-history.csv` | {len(ROWS)} | {span(years)} |",
         f"| `budget-history-wide.csv` | {len(wide_rows)} | {span(r[0] for r in wide_rows)} |",
         f"| `budget-history-department-crosswalk.csv` | {len(cross_rows)} | {span(cross_years)} |",
         f"| `budget-history-provenance.csv` | {len(SOURCES)} | not applicable |", "",
         "## Checks", "",
         "Every check below ran on this build and passed. A failing check stops the",
         "build before any file is written, so a published file has passed all of them.", "",
         "| Check | Cases | Tolerance | Largest miss |", "|---|---:|---|---|"]
    for key, (label, tol) in CHECKS.items():
        n, miss, where = checked[key]
        if tol == "exact":
            worst = "none"
        elif key == "snapshot":
            worst = f"${miss * 1e6:,.0f} ({where})"
        else:
            worst = f"${miss:.3f}M ({where})"
        L.append(f"| {label} | {n} | {tol} | {worst} |")
    L += ["", "## Rounding residuals", "",
          "The city totals sales and use tax at full precision and prints components",
          "rounded to $0.01M, so a column can miss its own total by a few hundredths.",
          "Each miss is kept in the data as `salesuse_component_residual`:", "",
          "| Year | Basis | Residual |", "|---|---|---:|"]
    L += [f"| {yr} | `{basis}` | {'+' if delta > 0 else '-'}${abs(delta):.2f}M |"
          for yr, basis, delta in residuals]
    L += ["", "## Rows by source", "",
          "| `source_id` | Rows | Years |", "|---|---:|---|"]
    for sid in SOURCES:
        ys = [r["year"] for r in ROWS if r["source_id"] == sid]
        L.append(f"| `{sid}` | {len(ys)} | {span(ys)} |")
    L += ["", "## Rows by basis", "", "| `basis` | Rows | Years |", "|---|---:|---|"]
    for basis in sorted({r["basis"] for r in ROWS}):
        ys = [r["year"] for r in ROWS if r["basis"] == basis]
        L.append(f"| `{basis}` | {len(ys)} | {span(ys)} |")
    L += ["", "## Coverage by measure", "",
          "Years with at least one row, on any basis. A year that is missing is",
          "absent from the data, never zero.", "",
          "| Measure | Unit | Years | Bases |", "|---|---|---|---|"]
    for m in sorted({r["measure"] for r in ROWS}):
        rs = [r for r in ROWS if r["measure"] == m]
        L.append(f"| `{m}` | {rs[0]['unit']} | {span(r['year'] for r in rs)} | "
                 + ", ".join(f"`{b}`" for b in sorted({r['basis'] for r in rs})) + " |")
    L += ["", "## Department crosswalk", "",
          "| Family | Years | Rows | Distinct printed labels | Rows with a note |",
          "|---|---|---:|---:|---:|"]
    for fam in ("deptexp", "deptexpfiltered"):
        rs = [r for r in cross_rows if r[1] == fam]
        L.append(f"| `{fam}` | {span(r[0] for r in rs)} | {len(rs)} | "
                 f"{len({r[2] for r in rs})} | {sum(1 for r in rs if r[7])} |")
    L += ["", "Years in which each bucket has a line:", "",
          "| Bucket | `deptexp` | `deptexpfiltered` |", "|---|---|---|"]
    for bucket in BUCKET_ORDER:
        cells = [span(r[0] for r in cross_rows if r[1] == fam and r[3] == bucket) or "none"
                 for fam in ("deptexp", "deptexpfiltered")]
        L.append(f"| `{bucket}` | {cells[0]} | {cells[1]} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    # Source-side rounding residuals are recorded as data, so a downstream user
    # sees them instead of rediscovering them -- then everything is checked
    # again with those rows in place, and nothing is written unless it all
    # passes. Writing first and checking after would leave a failed build's
    # half-finished CSVs looking like a finished one.
    _, residuals, _ = reconcile()
    for yr, basis, delta in residuals:
        add(yr, "salesuse_component_residual", basis, delta, "musd", "forecast2026")
    problems, _, checked = reconcile()
    if problems:
        print("RECONCILIATION FAILED -- nothing written:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    ROWS.sort(key=lambda r: (r["year"], r["measure"], r["basis"]))

    # The department crosswalk, generated from DEPARTMENT_LINES rather than
    # written alongside it, so what is documented is exactly what was used. One
    # row per department line item per year: the label as its document printed
    # it, the bucket it went into, its share of that year's departmental total,
    # and the reason wherever the assignment was a judgment call.
    all_dept = ([("deptexp", r) for r in DEPARTMENT_LINES]
                + [("deptexpfiltered", r) for r in DEPARTMENT_FILTERED_LINES])
    dept_totals = collections.defaultdict(float)
    for fam, (y, _l, v, _b, _n) in all_dept:
        dept_totals[(fam, y)] += v
    cross_rows = [
        [yr, fam, label, bucket, v, round(100 * v / dept_totals[(fam, yr)], 2),
         dept_source(fam, yr), note]
        for fam, (yr, label, v, bucket, note) in sorted(
            all_dept, key=lambda t: (t[1][0], BUCKET_ORDER.index(t[1][3]), -t[1][2]))]
    write_csv(HERE / "budget-history-department-crosswalk.csv", CROSSWALK_COLUMNS, cross_rows)

    write_csv(HERE / "budget-history.csv", LONG_COLUMNS,
              [[r[c] for c in LONG_COLUMNS] for r in ROWS])

    # Every wide series carries its own *_basis column. Across a historical
    # series the basis necessarily shifts -- actuals for closed years, the
    # adopted or recommended figure for the current one -- and a chart that
    # hides that shift is quietly comparing different things.
    idx = {(r["year"], r["measure"], r["basis"]): r["value"] for r in ROWS}
    years = sorted({r["year"] for r in ROWS})
    wide_cols = ["year"]
    for m, _ in WIDE:
        wide_cols += [m, f"{m}_basis"]
    wide_rows = []
    for yr in years:
        row = [yr]
        for measure, prefs in WIDE:
            basis = next((b for b in prefs if (yr, measure, b) in idx), "")
            row += [idx[(yr, measure, basis)] if basis else "", basis]
        wide_rows.append(row)
    write_csv(HERE / "budget-history-wide.csv", wide_cols, wide_rows)

    write_csv(HERE / "budget-history-provenance.csv", PROVENANCE_COLUMNS,
              [[sid, s["title"], s["publisher"], s["date"], s["url"], s["retrieved"],
                sum(1 for r in ROWS if r["source_id"] == sid), s["notes"]]
               for sid, s in SOURCES.items()])

    write_validation(HERE / "budget-history-validation.md", checked, residuals,
                     cross_rows, wide_rows)

    print(f"budget-history.csv                       {len(ROWS)} rows, "
          f"{len(years)} years ({min(years)}-{max(years)}), "
          f"{len({r['measure'] for r in ROWS})} measures")
    print(f"budget-history-wide.csv                  {len(years)} rows x {len(WIDE)} series")
    print(f"budget-history-department-crosswalk.csv  {len(cross_rows)} rows")
    print(f"budget-history-provenance.csv            {len(SOURCES)} sources")
    print("budget-history-validation.md             coverage and checks")
    print("\nreconciliation: every published total matches its parts")
    if residuals:
        print("source-side rounding residuals (recorded as salesuse_component_residual):")
        for yr, basis, delta in residuals:
            print(f"  {yr} {basis}: {delta:+.2f}M")


if __name__ == "__main__":
    main()
