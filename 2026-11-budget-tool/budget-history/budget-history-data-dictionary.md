# Boulder budget history: data dictionary

This file covers the columns, codes and caveats for the CSV files in this directory. [`README.md`](README.md) says what the dataset is and how it is built. [`budget-history-validation.md`](budget-history-validation.md) gives the row counts, the years each measure covers and the result of every check. `budget-history.py` rebuilds that report from the data each time it runs. This file is maintained by hand, so where the two disagree about a count or a year, the report is right.

These conventions hold in every file:

- **Money is in millions of nominal dollars** (unit `musd`) unless the unit says otherwise. Nothing is adjusted for inflation.
- **`year` is the budget year.** Boulder's fiscal year is the calendar year, so 2026 means January to December 2026.
- **Missing is empty, never zero.** If a year has no row for a measure, the sources read do not give that figure. It is not a year of zero spending.
- **Every value carries a `source_id`,** which joins to `budget-history-provenance.csv`.
- **The data is long format.** There is one row per observation, not one column per year. The exception is the wide file, which is built for charting.
- **Files are UTF-8, comma-separated, with LF line endings.** The four `budget-history-*` CSVs contain only ASCII characters, so Excel opens them without garbling anything.

> **Read two things before charting anything.** First, every value has a [`basis`](#basis-read-this-first), which records which version of the figure it is (adopted, actual, and so on). A series that mixes bases shows those version differences as if they were changes in spending. Second, the headline totals and the OpenGov Sources & Uses snapshot use [two different accounting bases](#1-two-accounting-bases-never-one-series), and they are $83.4M apart in 2023.

## Contents

- [Files](#files)
- [`basis`: read this first](#basis-read-this-first)
- [Units](#units)
- [Columns](#columns), file by file
- [Measure catalog](#measure-catalog)
- Caveats:
  - [Reading the series](#reading-the-series): caveats 1–7
  - [Coverage](#coverage): caveat 8
  - [Derived and disagreeing figures](#derived-and-disagreeing-figures): caveats 9–14
  - [Staffing](#staffing): caveat 15
  - [Departments](#departments): caveats 16–18
  - [OCR](#ocr): caveat 19
  - [Annual financial reports](#annual-financial-reports): caveats 20–25
- [Recipes](#recipes)
- [Extending the series](#extending-the-series)

## Files

| File | One row per | Written by |
|---|---|---|
| `budget-history.csv` | Year, measure and basis. This is the dataset | `budget-history.py` |
| `budget-history-wide.csv` | Year. Holds the headline series, one basis each, for charting | `budget-history.py` |
| `budget-history-provenance.csv` | Source document | `budget-history.py` |
| `budget-history-department-crosswalk.csv` | Department line item per year, with the bucket it went into and why | `budget-history.py` |
| `budget-history-validation.md` | Not a table. Holds counts, coverage and every check | `budget-history.py` |
| `budget-books-extracted.csv` | Candidate figure found in the budget books | `budget-books-extract.py` |
| `budget-books-pages-of-interest.csv` | Budget-book page that looks as if it holds a figure | `budget-books-extract.py` |
| `acfr-extracted.csv` | Figure read from an annual financial report, with both readings and how it was confirmed | `acfr-extract.py` |
| `acfr-pages.csv` | Annual-report page holding one of the five tables read | `acfr-extract.py --locate` |

The first five files are the dataset. The two `budget-books-*` files are working files of the book pipeline: they hold candidates that a person checks before typing them into `budget-history.py`, and that script never reads them. The annual reports' files work differently. `acfr-pages.csv` lists the pages OCR was paid for, and `budget-history.py` **loads** the confirmed figures in `acfr-extracted.csv` instead of having them typed in ([caveat 25](#25-how-the-annual-report-figures-were-read-and-checked)).

## `basis`: read this first

A budget figure means little until you know which version it is. The same year and measure often has three or four published values:

| 2025 sales and use tax | Value | `basis` |
|---|---|---|
| What council adopted | $180.17M | `adopted` |
| The mid-year revision | $176.84M | `revised_projection` |
| What actually came in, audited | $182.37M | `actual` |

These differ by up to $5.5M, close to the whole $6.3M General Fund gap the 2027 budget has to close. **Filter to one `basis` before charting.** A series that mixes bases looks volatile when it is really answering different questions. (The audited actual comes from the annual financial report. The council packet's own year-end figure was $178.75M; [caveat 20](#20-tax-collections-are-audited-and-12-above-the-packets-year-end-figures) explains the gap.)

| `basis` | Meaning |
|---|---|
| `adopted` | Approved by council for that year. The default, and most of the data |
| `recommended` | The city manager's proposal, not yet adopted. This covers every 2027 figure, plus the 2026 revenue figures taken from the recommended-budget presentation |
| `actual` | What came in or went out in a closed year. Tax collections and assessed value are audited, from the annual financial reports. The council packet's 2022–2025 sales tax components are its own unaudited year-end figures |
| `final` | The General Fund budget as amended by the end of the year, from the annual reports' budget-and-actual statement. Used only in `acfrgf_*` ([caveat 23](#23-the-reports-general-fund-is-broader-than-the-books)) |
| `revised_projection` | A mid-year revision of an adopted figure |
| `projected` | An out-year column in a budget book's multi-year table: a year the book plans for but does not adopt. There are two such values: 2007 General Fund revenue from the 2006–2007 book, and 2009 General Fund uses from the 2008 book |
| `forecast` | Output of the city's forward-looking financial model |
| `identified` | A General Fund gap named while a budget was being built |
| `restated` | A later book's revision of a figure that its own year's book gives as `adopted`. Used for staffing ([caveat 15](#15-staffing-one-level-series-and-a-separate-family-of-changes)), the 2007 citywide total ([caveat 2](#2-the-headline-totals-are-one-continuous-net-series)) and taxable sales ([caveat 21](#21-taxable-sales-are-the-tax-base-and-2013-2014-and-2017-were-revised)) |
| `total_budget` | Adopted **plus amendments and carryforward**. Used only in the 2023 OpenGov snapshot ([caveat 1](#1-two-accounting-bases-never-one-series)) |
| `derived` | **Computed here, not published by the city.** Each derived value is explained in a caveat |
| `policy` | A standing policy target, not a year-specific amount |

## Units

| `unit` | Meaning |
|---|---|
| `musd` | Millions of dollars, nominal. `196.167` is $196,167,000 |
| `fte` | Full-time equivalent positions. Two half-time positions are one FTE |
| `pct` | Percent. `3.09` is 3.09% |
| `mills` | Property tax rate in mills: dollars of tax per $1,000 of assessed value |

## Columns

### `budget-history.csv`

This is the dataset. It is sorted by `year`, `measure`, `basis`.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | The budget year the value describes |
| `measure` | string | What is measured. See the [measure catalog](#measure-catalog) |
| `basis` | string | Which version of the figure this is. See [`basis`](#basis-read-this-first) |
| `value` | number | In `unit`. Not adjusted for inflation |
| `unit` | string | `musd`, `fte`, `pct` or `mills`. See [units](#units). Each measure uses one unit throughout |
| `source_id` | string | Joins to `budget-history-provenance.csv` |

The key is (`year`, `measure`, `basis`). The build refuses to write a file in which any key appears twice.

### `budget-history-wide.csv`

This file has one row per year and 13 headline series. Each series comes with a `<series>_basis` column that says which basis supplied that year's value. Use it to go straight to a chart, and use the basis column for the footnote.

Where a year has several bases, the file picks one by a single rule:

| Series | Preference, first available wins |
|---|---|
| `budget_total`, `budget_operating`, `budget_capital`, `budget_general_fund_revenue`, `revenue_sales_use_tax`, `revenue_property_tax`, `revenue_utility` | `adopted`, then `recommended` |
| `budget_general_fund`, `revenue_total` | `adopted`, then `recommended`, then `derived` |
| `staffing_fte` | `adopted`, then `recommended`. The `restated` values stay in the long file |
| `salesuse_total`, `property_tax_revenue` | `actual`, then `adopted`, then `recommended`, then `forecast` |
| `gap_general_fund` | `identified`, then `recommended`, then `forecast` |

Budget series take what was adopted. Revenue collections take what actually came in. **An `actual` is never a fallback for a budget series.** An actual sitting among adopted neighbours answers a different question, and a chart would show the difference as a jump. So a year that has only an actual for a budget series is empty in this file. For example, 2003 General Fund revenue and 2005 General Fund uses are in the long file only.

### `budget-history-provenance.csv`

| Column | Type | Notes |
|---|---|---|
| `source_id` | string | The key |
| `title` | string | The document's title, with a short description in parentheses where the title alone is ambiguous |
| `publisher` | string | City of Boulder, or Boulder Reporting Lab |
| `date` | date | The document's own publication date, in ISO format. Empty for a data export or a multi-volume corpus, which have none |
| `url` | string | Where the document was read. For the budget books, the city's Laserfiche folder |
| `retrieved` | date | When the figures were read from the document |
| `n_values` | integer | Rows in `budget-history.csv` that cite this source |
| `notes` | string | What the source supplies, and anything to know about it |

Two sources cover the same budget books. **`books`** means the figure was read from the text layer that pypdf extracts. **`booksocr`** means it was read by Datalab's OCR from pages whose text layer pypdf cannot use ([caveat 19](#19-ocr-read-the-pages-pypdf-could-not-and-got-some-things-wrong)).

### `budget-history-department-crosswalk.csv`

This file has one row per department line item per year. It holds the label exactly as the document printed it, the bucket it was assigned to, and why. `budget-history.py` generates it from the same rows it sums, so the documented assignment cannot drift from the one actually used ([caveat 16](#16-department-spending-is-bucketed-and-the-buckets-are-coarse-on-purpose)).

| Column | Type | Notes |
|---|---|---|
| `year` | integer | 2027's rows are the recommended budget; every other year's are adopted |
| `measure_family` | string | `deptexp` (the books' pies, 2005–2022, and the 2027 budget book's citywide table, 2025–2027) or `deptexpfiltered` (the 2024–2026 OpenGov export). These are **not** one series ([caveat 17](#17-deptexp-and-deptexpfiltered-both-add-up-and-still-do-not-compare)) |
| `source_label` | string | The department as printed, with any letter-spacing damage kept: `Fir e`, `Parks & Re cr e ation`. That string is what you would search the PDF for |
| `bucket` | string | One of seven functional buckets. See the [measure catalog](#measure-catalog) |
| `value_musd` | number | This line's spending |
| `pct_of_year_departmental` | number | Share of that year's lines in the same family. For `deptexp` that is the citywide total. For `deptexpfiltered` it is the export's total, which leaves out three fund groups |
| `source_id` | string | `books`, `booksocr`, `recbook2027` or `deptsnapshot2026` |
| `note` | string | Why, wherever the assignment was a judgment call. Every note stands alone; none sends you to another row |

The balancing line `deptexpfiltered_funds_outside_export` is not in this file, because it is not a department. It is a residual computed against the published total.

### `budget-books-extracted.csv`

This file lists candidate figures, not the dataset. `budget-books-extract.py` finds them and a person checks each one before it goes into `budget-history.py`.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | The year the figure describes, taken from the sentence or column heading and never from the filename. The 2005 book states 2004's total, and the 2006–2007 book is filed under 2007 but prints 2006 |
| `measure` | string | A `budget-history.csv` measure name. A pie slice is `dept_` followed by the printed label reduced to lowercase letters and digits (`dept_parksrecreation`), before any bucketing |
| `basis` | string | Empty for a figure a book states for its own budget year, which is its adopted figure. Otherwise the column heading of a multi-year table, mapped to the dataset's vocabulary: APPROVED becomes `adopted`, and ACTUAL, PROJECTED, REVISED and RECOMMENDED become `actual`, `projected`, `revised_projection` and `recommended` |
| `value` | number | In `unit` |
| `unit` | string | `musd` or `fte` |
| `file` | string | The PDF's filename |
| `page` | integer | The page's position in the PDF, counting from 1. This is not always the number printed on the page |
| `n_values` | integer | How many different values the whole corpus gives for this year, measure and basis |
| `conflict` | string | Those values, separated by ` \| `, when there is more than one. Empty when every reading agrees |
| `context` | string | Up to 190 characters of the surrounding text, for confirming by eye. For a pie slice or an OCR table row, a note of how it was read |

Where the same year, measure and basis turns up on several pages, the row shows the first page found and `n_values` says whether the others agree.

### `budget-books-pages-of-interest.csv`

This file has one row per page that looks as if it holds a figure, whether or not the extractor could read it. It is the target list for OCR tier 4.

| Column | Type | Notes |
|---|---|---|
| `file` | string | The PDF's filename |
| `page` | integer | The page's position in the PDF, counting from 1 |
| `holds` | string | One or more of `pie`, `multiyear_table` and `summary_block`, space-separated |
| `already_extracted_from` | string | `yes` if any row of `budget-books-extracted.csv` came from this page, otherwise `no` |

### `acfr-extracted.csv`

One row per figure read from one report's table, 5,864 in all. `acfr-extract.py` writes it, and `budget-history.py` loads the rows it needs whose `confirmed` column is filled.

| Column | Type | Notes |
|---|---|---|
| `report` | integer | The fiscal year of the report the figure was read from |
| `table` | string | `fundbal` (tax collections), `fte` (staffing by function), `taxsales` (taxable sales), `legal` (assessed value) or `gf` (General Fund budget and actual) |
| `line` | string | The row label as printed |
| `year` | integer | The column's year. A ten-year table gives ten per report |
| `basis` | string | `actual`; `adopted` for staffing and for the General Fund statement's original budget; `final`; or `variance`, which is never loaded |
| `unit` | string | `thousands`, as the reports print dollars, `fte` or `pct` |
| `value` | string | The figure used: a number, `-` for a dash, or a footnote mark such as `(a)` |
| `ocr`, `text` | string | Datalab's reading and the text layer's. `text` is empty for the 2021 and 2023 reports, whose text layers are not used |
| `status` | string | `agree`, `ocr only`, `text only` or `DISAGREE` |
| `confirmed` | string | How the figure is known to be right: `both readings`, `another report`, `own arithmetic` or `text layer` ([caveat 25](#25-how-the-annual-report-figures-were-read-and-checked)). Empty means unconfirmed, and it is never loaded |
| `pages` | string | The PDF pages the table spans, such as `263-264` |

### `acfr-pages.csv`

One row per annual-report page OCR was paid for: `file`, `page` (its position in the PDF) and `table`. `acfr-extract.py --locate` writes it by finding each table's title, and `budget-books-ocr.py --pages-from` reads it.

## Measure catalog

Every measure is listed below. The exact years each one covers are in the validation report's [coverage table](budget-history-validation.md#coverage-by-measure).

| Measure | Unit | What it is |
|---|---|---|
| `budget_total` | musd | The citywide budget, all funds, **net** of interfund transfers. The headline number ([caveat 2](#2-the-headline-totals-are-one-continuous-net-series)) |
| `budget_operating`, `budget_capital` | musd | Its two parts. They sum to `budget_total` within $0.1M in every year that has all three ([caveat 2](#2-the-headline-totals-are-one-continuous-net-series)) |
| `budget_general_fund` | musd | **"Total General Fund Uses"**: General Fund spending plus transfers out plus the 0.15% sales tax allocation. The General Fund series to chart ([caveat 3](#3-two-general-fund-measures-6-to-19-percent-apart)) |
| `budget_general_fund_revenue` | musd | The same fund's Sources side, from the books, 2003–2026, and the 2027 budget book |
| `budget_operating_general`, `budget_operating_dedicated` | musd | The two halves of the operating budget in the 2005–2022 summary blocks. **Not** the General Fund series ([caveat 3](#3-two-general-fund-measures-6-to-19-percent-apart)) |
| `gap_general_fund` | musd | The General Fund shortfall identified for that year |
| `gap_general_fund_low`, `gap_general_fund_high` | musd | The same gap where it was given as a range (2025) |
| `salesuse_retail`, `salesuse_rec_marijuana_addl`, `salesuse_consumer_business_use`, `salesuse_construction_use`, `salesuse_motor_vehicle_use`, `salesuse_audits_sales`, `salesuse_audits_use` | musd | Sales and use tax by component, citywide, all funds. `rec_marijuana_addl` is the additional tax on recreational marijuana |
| `salesuse_total` | musd | Their published total, for the packet's adopted, revised and forecast figures. Its `actual` is audited, from the annual financial reports, 2007–2025 ([caveat 20](#20-tax-collections-are-audited-and-12-above-the-packets-year-end-figures)) |
| `salesuse_component_residual` | musd | The amount by which the rounded components miss their total. Recorded, not hidden ([caveat 13](#13-component-sums-miss-their-totals-by-a-few-hundredths)) |
| `property_tax_revenue` | musd | Property tax collected at the city's own levy. Its `actual`, 2007–2025, is audited, from the annual reports ([caveat 20](#20-tax-collections-are-audited-and-12-above-the-packets-year-end-figures)) |
| `property_assessed_value` | musd | Assessed value of taxable property, in millions of dollars, filed under the year the tax is collected. `actual` 2017–2026 from the annual reports ([caveat 24](#24-assessed-value-is-filed-under-the-year-it-is-taxed)) |
| `property_mill_levy` | mills | The city's levy |
| `revenue_sales_use_tax`, `revenue_utility`, `revenue_property_tax`, `revenue_intergovernmental` | musd | Citywide all-funds revenue by source: the four categories that every year from 2005 to 2027 shares |
| `revenue_development_impact_fees`, `revenue_licenses_permits_fines`, `revenue_investment_earnings_bonds`, `revenue_accommodation_admission_tax`, `revenue_grants`, `revenue_parking`, `revenue_other_grouped` | musd | Categories only the 2026 presentation and the 2027 budget book break out. `other_grouped`, 2026 only, is that presentation's own "other" |
| `revenue_other_revenues`, `revenue_charges_for_services`, `revenue_misc_sales_materials_goods`, `revenue_franchise_fees`, `revenue_leases_rents_royalties`, `revenue_specific_ownership_tobacco` | musd | 2027 only: the six lines the 2027 budget book prints where the 2026 presentation has `other_grouped`. The book's own 2026 column sums them to $50,582,397, the presentation's figure to the dollar |
| `revenue_other_unmapped` | musd | The slices that fit no category, 2005–2026, carried together so each year still sums to its total ([caveat 10](#10-revenue_total-runs-20052027-all-published)) |
| `revenue_total` | musd | Citywide all-funds revenue |
| `sources_revenue_*` | musd | **A different basis**: the OpenGov citywide Sources & Uses snapshot, gross of interfund flows, 18 categories plus `total` ([caveats 1](#1-two-accounting-bases-never-one-series) and [4](#4-the-snapshots-revenue-categories-are-a-different-taxonomy)) |
| `uses_expense_personnel`, `_capital`, `_operating`, `_transfers`, `_internal_services`, `_debt_service`, `_total` | musd | **A different basis**: the same snapshot's spending, by type of expense ([caveat 1](#1-two-accounting-bases-never-one-series)) |
| `net_revenues_less_expenses` | musd | The snapshot's revenue minus expense. Negative in 2023 |
| `deptexp_public_safety`, `_infrastructure`, `_parks_openspace`, `_community_services`, `_planning_climate`, `_administration`, `_citywide_debt` | musd | Citywide spending by department, bucketed, from the books' own pies, 2005–2022, and the 2027 budget book's citywide table, 2025–2027. Sums to `budget_total` ([caveat 16](#16-department-spending-is-bucketed-and-the-buckets-are-coarse-on-purpose)) |
| `deptexpfiltered_*` (the same seven buckets) | musd | The same idea from a 2024–2026 export that leaves out three fund groups. **Not comparable to `deptexp_*`** ([caveat 17](#17-deptexp-and-deptexpfiltered-both-add-up-and-still-do-not-compare)) |
| `deptexpfiltered_funds_outside_export` | musd | What the export leaves out: the published total minus the export's total. `derived` |
| `staffing_fte` | fte | Citywide staffing **level** in standard FTEs ([caveat 15](#15-staffing-one-level-series-and-a-separate-family-of-changes)) |
| `positions_eliminated`, `positions_eliminated_filled`, `positions_eliminated_vacant`, `positions_term_limited_ending`, `positions_frozen_to_2028`, `positions_added` | fte | Year-over-year **changes** in positions, not levels ([caveat 15](#15-staffing-one-level-series-and-a-separate-family-of-changes)) |
| `staffing_savings` | musd | What the 2027 position cuts are expected to save: "about $3 million, according to a city official" |
| `yoy_total_pct`, `yoy_operating_pct`, `yoy_capital_pct`, `yoy_general_fund_pct` | pct | Year-over-year change as the city published it ([caveat 12](#12-the-books-own-percentages-do-not-always-reproduce)) |
| `reserve_policy_pct_of_operating` | pct | The standing reserve target, 16.7% of operating |
| `ftefunc_*` | fte | Staffing by function as the annual reports print it, one measure per line (`ftefunc_police`, `ftefunc_city_manager_community_vitality`), 2007–2025, and the reports' own `ftefunc_total`. **Never mix with `staffing_fte`** ([caveat 22](#22-staffing-by-function-is-the-budgets-count-and-its-totals-do-not-always-match-staffing_fte)) |
| `ftebucket_public_safety`, `_infrastructure`, `_parks_openspace`, `_community_services`, `_planning_climate`, `_administration` | fte | The same lines grouped as the spending pies are. They sum to `ftefunc_total` ([caveat 22](#22-staffing-by-function-is-the-budgets-count-and-its-totals-do-not-always-match-staffing_fte)) |
| `taxablesales_*` | musd | Taxable sales by market sector: the sales tax **base**, not the tax. 2007–2025, with `taxablesales_total` ([caveat 21](#21-taxable-sales-are-the-tax-base-and-2013-2014-and-2017-were-revised)) |
| `salestaxrate_direct_city`, `salestaxrate_food_service`, `salestaxrate_total_direct_city` | pct | The city's sales tax rates, from the same table |
| `acfrgf_*` | musd | The annual reports' General Fund budget-and-actual statement, line by line, 2016–2025, as `adopted` (the original budget), `final` and `actual`. **Broader than `budget_general_fund`** ([caveat 23](#23-the-reports-general-fund-is-broader-than-the-books)) |

The seven buckets are defined in [caveat 16](#16-department-spending-is-bucketed-and-the-buckets-are-coarse-on-purpose).

## Caveats

### Reading the series

#### 1. Two accounting bases, never one series

The `sources_*` and `uses_*` measures come from the OpenGov citywide Sources & Uses export. They are **not** comparable to the `budget_*` headline totals:

| Year | `uses_expense_total` | `budget_total` | Difference |
|---|---|---|---|
| 2023 | $598.79M | $515.40M | **+$83.39M** |

Two structural reasons explain the gap. Neither is an error:

1. **Different vintage.** The snapshot's 2023 column is *Total Budget*, which is adopted plus amendments and carryforward. $515.4M is the *adopted* figure. The snapshot's 2022 column is adopted and its 2021 column is actuals. That is three bases in one file, which is why each carries its own `basis`.
2. **Gross, not net.** Interfund flows stay in on both sides: `transfers_in`, `intragovernmental_charges` and `cost_allocation` on the revenue side, and `transfers` and `internal_services` on the expense side. Money moving between city funds is therefore counted more than once. Removing transfers and internal services alone closes about $75M of the $83M gap. The rest is the difference between amended and adopted.

Charting the two families together produces a fake cliff of about $83M between 2023 and 2024. **Pick one family per chart.** Use `budget_*` for the headline story and `uses_expense_*` for composition by type of expense.

#### 2. The headline totals are one continuous net series

`budget_total` is one net measure from 2004 to 2027, with no break in basis and one small change of scope. The 2016 book gives its total as "$327 million (excluding transfers)" against $515.4M for 2023, which makes them look like different measures. The years between run 327, 322, 389, 354, 370, 342, 462 and 515 without a step, so the 2016 wording describes scope rather than a separate series. The gross counterpart is the `sources_*`/`uses_*` family ([caveat 1](#1-two-accounting-bases-never-one-series)).

**The change of scope comes in 2008.** From the 2008–09 budget process the total takes in the internal service funds, such as fleet, computer replacement and self-insurance, net of the departmental charges that fund them. The 2008 book says so, and restates 2007 on the new footing: $224.336M against the 2007 book's own $223.560M, a difference of 0.35%. The restated figure is in the long file with `basis = restated`. The years 2004–2007 stay on the narrower footing. It is also what the 2008 book's "6.0% greater than the 2007 approved budget" is measured against ([caveat 12](#12-the-books-own-percentages-do-not-always-reproduce)).

`budget_operating + budget_capital = budget_total` holds to the thousand in every year a summary block gives all three: 2005–2018 and 2020–2022. Where a part comes from prose or a council packet rounded to $0.1M, the sum can miss by a rounding step. 2019's prose operating figure of $283.2M plus its block's capital of $70.557M is $353.757M, against $353.746M. 2025's $399.3M + $189.9M is $589.2M, against a stated $589.3M. `budget-history.py` fails the build on any miss over $0.2M, and the validation report gives the largest miss on each build.

Three independent checks support the run. First, the 2005 book and the 2006–2007 book each state 2005 as $196,167,000. Second, the 2018 and 2020–2022 books print their summary blocks to the dollar or the thousand, and each block's total equals the total on the same book's department pie. 2019's block is the exception, described below. Third, the 2007, 2009 and 2010 books, read by OCR from their scans, each print their total three times, in the summary block, the pie heading and a sentence beneath the pie, and the three always agree.

**2019's summary block does not add up.** Its General Fund and dedicated halves sum to $283.188M, the book's prose "$283.2 million". But its operating box prints $282.934M and its total box $353.491M, both exactly $255,000 lower, while the book's pie and prose give the total as $353.746M. The capital box, $70.557M, agrees with its own two halves and equals the pie total less the operating halves. So 2019 keeps the pie's total and the prose's operating figure, and takes its capital budget and operating halves from the block.

#### 3. Two General Fund measures, 6 to 19 percent apart

`budget_general_fund` is **"Total General Fund Uses"**: General Fund spending *plus* transfers out *plus* the 0.15% sales tax allocation. This is the figure the books state in prose, in the 2005–2007 books ("The 2005 General Fund budget is $80,059,000") and from 2012 on, and the figure the modern council packets report, so it is the series to chart.

`budget_operating_general` is something else. It is the General Fund *half of the operating budget* in the summary blocks of 2005–2022, where

```
budget_operating_general + budget_operating_dedicated = budget_operating
```

That identity holds to within $1 thousand, which is rounding, in every year but 2019. There the halves come from the book's block and sum to $283.188M, while the operating figure comes from its prose, rounded to $283.2M ([caveat 2](#2-the-headline-totals-are-one-continuous-net-series)). The operating half runs below the all-in figure, by a varying amount:

| Year | `budget_operating_general` | `budget_general_fund` | Ratio |
|---|---|---|---|
| 2008 | $80.47M | $94.24M | 0.854 |
| 2011 | $87.66M | $100.45M | 0.873 |
| 2014 | $101.96M | $115.68M | 0.881 |
| 2016 | $116.96M | $132.27M | 0.884 |
| 2017 | $130.86M | $139.79M | 0.936 |
| 2018 | $137.68M | $146.32M | 0.941 |
| 2019 | $145.23M | $158.16M | 0.918 |
| 2020 | $132.26M | $161.50M | 0.819 |
| 2022 | $134.15M | $164.66M | 0.815 |

Substituting one for the other creates a step of 6% to 19% that is not in the data. The all-in series is continuous across the 2011→2012 change of document format, and that has been checked rather than assumed. The 2012 book says its General Fund spending is "a 3.8 percent increase over the total expenditures projected for the 2011 Approved Budget", and 100.449 × 1.038 = 104.27 against the stated 104.234.

**Do not assume the smaller half is the General Fund.** It is in most years, but not in 2017 or 2019. In 2017 the General Fund is the *larger* half, $130.86M against $129.82M in dedicated funds, and in 2019 it is $145.23M against $137.96M. The build checks the identity and fails if the halves are swapped.

#### 4. The snapshot's revenue categories are a different taxonomy

The snapshot's revenue categories do not match the `revenue_*` family. The snapshot has 18 categories, including `transfers_in`, `cost_allocation` and `intragovernmental_charges`, which the `revenue_*` family has no equivalent for. Don't join the two families on category name.

#### 5. 2005–2017 operating includes debt service

Those years come from a summary block labelled "OPERATING BUDGET (including debt service)". The modern operating figures do not visibly separate debt service out either, but only the older books say so explicitly.

#### 6. Nominal dollars throughout

Nothing is adjusted for inflation. Year-over-year changes over 2022–2027 partly reflect inflation, which was substantial early in that window.

#### 7. Every 2027 value is `recommended`

Council's first reading is set for October 1, 2026 and its final vote for October 15, 2026. Figures may change on adoption, so check them before publishing anything that depends on them.

Most 2027 figures come from the city's online budget book for the recommended budget (`recbook2027`), which repeats the release's totals, General Fund and gap. The position changes come from the release and the Budget At-A-Glance page.

### Coverage

#### 8. Coverage is uneven, and the gaps are not the same gaps

Check the [coverage table](budget-history-validation.md#coverage-by-measure) for the year you need rather than assuming every measure covers every year. The main gaps are these:

- **The citywide total starts in 2004,** from the 2005 book's statement of the prior year. The archive's books begin with 2005, and none of them states an adopted total for 2002 or 2003.
- **The 2007, 2009 and 2010 books are scans.** Their Volume 1s have no text layer, so everything taken from them was read by OCR (`booksocr`), including the General Fund columns they print for 2005–2009. Each figure passed the same checks as the rest ([caveat 19](#19-ocr-read-the-pages-pypdf-could-not-and-got-some-things-wrong)). Figures for those years that a born-digital book also prints keep that book as their source.
- **2002–2004 are thin.** Without books for those years, they have only what later books print about them: the 2004 total, General Fund spending and revenue for 2003 and 2004, and staffing, which reaches 2002 through the 2011 book's chart.
- **`budget_general_fund` has only an actual for 2003,** so the chart file's series starts in 2004. 2019's two General Fund figures come from that book's Funds Summary table, read by OCR, and the 2020 book's own percentages confirm both ([caveat 12](#12-the-books-own-percentages-do-not-always-reproduce)).
- **Tax collections start in 2007.** Each annual financial report prints ten years, so the ten in hand (fiscal 2016–2025) give `salesuse_total` and `property_tax_revenue` actuals for 2007–2025. The 2005–2015 reports, requested from the city, would reach back to 2002.
- **Staffing by function, taxable sales and the General Fund's budget-and-actual come only from the annual reports:** 2007–2025 for the first two, 2016–2025 for the last.
- **2027 is the recommended budget, with no actuals.** The release and the Budget At-A-Glance page give totals, the General Fund, the gap and position changes. The online budget book adds revenue by source, General Fund revenue, staffing, department spending and the two tax forecasts.

A missing year is absent from the data, not zero. Do not interpolate across a gap without saying so.

### Derived and disagreeing figures

#### 9. 2025 General Fund comes from its own book

`budget_general_fund` for 2025 used to be derived. It was back-computed as `194.5 / (1 − 0.078)` = $211.0M from the packet's statement that 2026 fell 7.8% from 2025. The 2025 book prints $210.9M, which replaces it, and the 2026 book's "7.8% decrease from the 2025 Approved Budget" reproduces against that figure. No General Fund value is derived any more.

#### 10. `revenue_total` runs 2005–2027, all published

Every year comes from its own book, in three layouts:

- **2005–2012: "Sources of Funds" pies,** each summing to its printed total exactly. 2007–2010 were read by OCR, three of them from scans and 2008's from a page whose text layer scrambles which label goes with which number.
- **2013–2022: "Citywide Revenues (Sources)" pies and donuts.** The 2013–2017 slices are rounded to the thousand and sum to within $2 thousand of their totals. 2021 prints its total only in prose, as $337.7 million.
- **2023–2026: the net "total revenue budget"** each book states in prose, with the categories taken from OpenGov's Combined Budget Summary. That table is gross. It includes internal service charges and transfers between funds, so its own total is larger and is not used. The 2023 book labels its column "2023 Total Budget", and the 2025 book labels the same figures "2023 Adopted Budget", so they are recorded as adopted. The 2024 book prints only a table without utilities, so 2024's categories come from the 2025 book.
- **2027: the 2027 budget book's Citywide Sources table,** sixteen lines to the dollar that sum to its printed $527,097,004, the net figure its prose rounds to $527.1 million. The same table prints 2025 and 2026 columns. Its 2025 total, sales and use tax and utility revenue match the 2025 book, while its 2025 property tax is $0.37M higher and intergovernmental revenue $0.50M lower. Eight of the 2026 presentation's eleven lines match to the dollar, and the other three differ by $250,000 of utility revenue and $1,996 moved from investment earnings to property tax. So 2027 continues the series. The six lines the presentation grouped as "other" are kept as the book prints them.

**Two totals include borrowing.** 2018's chart has a $51.9M "Debt Issuance" slice, and 2022's "Other" includes $92.3M of water and wastewater bond proceeds. Earlier pies carry small bond proceeds the same way: $0.4M in 2005 and $1.2M in 2008. A jump in `revenue_total` in 2018 or 2022 is borrowing, not taxes.

2010 used to be derived from the 2011 book's "0.29% increase over the total revenues projected for the 2010 approved budget", which pinned it to $224.25M–$224.27M. The 2010 book's own $224.268M falls inside that range and replaces it. 2026's adopted figures, from its book, equal the recommended ones from the presentation, and both are in the long file.

**Only four categories line up across the years:** sales and use tax, utility, property tax and intergovernmental revenue. The rest are carried together as `revenue_other_unmapped`, the total less those four. That remainder is this dataset's arithmetic, not a printed figure, but it keeps each year summing to its own total. The slices it holds:

- 2005: Other $35.060M, Parks & Recreation $7.735M, Planning & Development Fees $4.992M, Bond Proceeds $0.416M.
- 2006: Other $36.214M, Parks & Recreation $7.575M, Planning & Development Fees $5.064M.
- 2007: Other $35.706M, Parks & Recreation $7.847M, Planning & Development Fees $5.114M, TIF for Garage at 10th & Walnut $1.080M.
- 2008: Other $41.885M, Parks & Recreation $8.167M, Planning & Development Fees $5.415M, Bond Proceeds $1.151M.
- 2009: Other $46.145M, Parks & Recreation $8.701M, Planning & Development Fees $5.388M.
- 2010: Other $42.184M, Parks & Recreation $9.156M, Planning & Development Fees $4.706M.
- 2011: Other Taxes $16.071M, Parks & Recreation Fees $8.479M, Planning & Development Fees $4.994M, Other $25.331M.
- 2012: Other $44.424M, Parks & Recreation $8.206M, Planning and Development Fees $5.518M.
- 2013–2017: Other, Other Taxes, Parks and Recreation, and Planning and Development Fees.
- 2018: Other, Other Taxes and Debt Issuance. Intergovernmental revenue sits inside Other, so `revenue_intergovernmental` has no 2018 row.
- 2019–2022: Other, Other Taxes and Charges for Services.
- 2023–2026: everything in the Combined Budget Summary but the four, net of internal charges and transfers.

**Intergovernmental revenue shifts between books.** The 2013–2017 charts call it "Intergovernmental Grants". The 2026 book restates 2024 and 2025 $496,000 lower each, moving that amount to a new parking line. The earlier books' figures are kept.

**Every chart labels its largest slice as sales tax,** "Sales Tax" to 2012 and "Sales and Use Tax" from 2013. The 2010 and 2011 books call the same source "sales/use taxes", and the 2009 book describes it with the combined sales and use tax rate. So it is read as the aggregate, and recorded as `revenue_sales_use_tax`, in every year.

#### 11. Book figures occasionally disagree with later council packets

In each case the book is what was published at adoption and the packet is a later restatement. Both are correct:

| Year | Measure | Book | Packet |
|---|---|---|---|
| 2024 | `budget_general_fund` | $196.1M | $196.2M |
| 2025 | `budget_total` | $589.5M | $589.3M |

Where both exist, the dataset keeps the packet value. The differences are small but real, so don't treat either one as an error.

A book can also quote a figure that is not its adopted one. The 2024 book's budget message gives $514.8M total, $374.1M operating and $140.7M capital. Those are the city manager's **recommended** budget. The same book's Budget in Brief gives the approved $515.4M, $374.2M and $141.2M, which match the packet exactly. The 2007 and 2009 books likewise state recommended totals of $225.321M and $243.855M, and the 2010 book charts its recommended budget as a pie. None of these is recorded.

#### 12. The books' own percentages do not always reproduce

Most of the books' year-over-year percentages can be reproduced from the books' own figures. The 2015 and 2016 books' operating, capital and total percentages all reproduce to the decimal, and so do the 2009 and 2010 books' totals, +2.1% and −5.2%, and so do most of the General Fund percentages printed since 2013. Among them are the 2020 book's revenue "3.14% increase" and spending "2.1% increase" over 2019: $157.395M against $152.597M, and $161.503M against $158.160M. Those two confirm 2019's figures, which only OCR has read. The 2006 book's General Fund is "a 3.2% increase over the 2005 approved budget", and the 2007 book's "an 8.5% increase over the 2006 approved budget": $82.623M on $80.059M, and $89.650M on $82.623M. Seven percentages do not reproduce:

| Book | Says | Figures give |
|---|---|---|
| 2007 | total +11.8% over 2006 | +11.7% |
| 2013 | total +9.2% over 2012 | +6.6% |
| 2014 | operating +4.6% over 2013 | +2.8% |
| 2017 | General Fund +4.9% over 2016 | +5.7% |
| 2021 | General Fund revenue −6.7% from 2020 | −6.4% |
| 2022 | General Fund +12.1% over 2021 | +12.5% |
| 2024 | General Fund revenue +20.1% over 2023 | +11.1% |

The likeliest explanation is a percentage computed against a revised or amended base rather than the prior book's adopted figure. The 2008 book shows the mechanism at work. Its "6.0% greater than the 2007 approved budget" is measured against 2007 as restated to include the internal service funds, $224.336M ([caveat 2](#2-the-headline-totals-are-one-continuous-net-series)). Against the 2007 book's own $223.560M it would be 6.4%. Either way, **use the values, not the narrative percentages.** A mismatch is not an extraction error.

#### 13. Component sums miss their totals by a few hundredths

The city totals sales and use tax at full precision but publishes the components rounded to $0.01M. A column of six components can therefore miss its own total by a few hundredths. Each miss is recorded as `salesuse_component_residual` rather than hidden, except on the `actual` basis: there the total is the audited one ([caveat 20](#20-tax-collections-are-audited-and-12-above-the-packets-year-end-figures)), which the packet's components were never meant to sum to. The published total is the authoritative figure. The build fails if any miss exceeds $0.05M, and the validation report lists every residual.

#### 14. Two property-tax figures for 2026, and neither is an error

`property_tax_revenue` (adopted) is **$59.17M**, collected at the city's own 11.648-mill levy. `revenue_property_tax`, from the citywide revenue mix, is **$61.73M**, which has a broader all-funds scope. They answer different questions, so don't compare them directly or chart them as one series.

2027 has the same pair. `property_tax_revenue` is **$57.83M**, the 2027 budget book's projection for the city's 11.648 mills, and `revenue_property_tax` is **$60.25M**.

### Staffing

#### 15. Staffing: one level series, and a separate family of changes

`staffing_fte` is the citywide staffing **level** in standard FTEs, from 2002 to 2027. 2027 is the recommended level, 1,532.68, from the 2027 budget book's Staffing Levels by Department table, whose 2025 and 2026 Approved columns are the books' 1,539.10 and 1,548.28. The `positions_*` measures are year-over-year **changes** (eliminated, added, frozen) from the 2026 and 2027 packets and releases.

**The level is one series, not two.** The early books count "standard FTEs" with an explicit scope footnote, while the later books say "citywide staffing level". That makes them look like different measures whose offset cannot be measured. Three books settle it by printing both labels for the same number:

| Book | Prose | Directly beneath it |
|---|---|---|
| 2016, p. 120 | "a citywide staffing level of **1,419** FTE" | *Figure 5-09: Staffing Levels: **Standard FTEs** 2002-2016*, ending at 1,419 FTE |
| 2018, p. 68 | "a citywide staffing level of **1,451** FTE" | *Staffing Levels: **Standard FTEs** 2002 to 2018* |
| 2022, p. 46 | "a citywide staffing level of **1,460.71**" | The same figure, under the same chart title |

The city charts the series continuously from 2002, so the 2011→2016 rise from 1,228.50 to 1,419 is real. The books' department tables give the headline figures exactly, 1,419.12 in 2016, 1,447.36 in 2017 and 1,451.09 in 2018, and those are the values recorded. From 2015 each table also prints the prior year as approved and as adjusted, with a variance column that checks. That is how 2014 is filled, from the 2015 book's "2014 Approved" column.

**Later books restate earlier years:** by one or two FTE up to 2013, and by 8 to 31 FTE since. Every restatement raises the figure except 2020's, which the 2021 book puts 18.50 FTE below the adopted level. Each year keeps its *own* book's figure. The most recent restatement sits beside it as `restated`, so the disagreement stays visible. The 2015–2017 books call a restatement "Adjusted", for changes made after a budget passed, and the 2019–2023 books call it "Revised Staffing":

| Year | Its own book | Restated |
|---|---|---|
| 2011 | 1,228.50 | 1,230.50 in the 2012 book, then **1,231.25** in the 2013 book |
| 2012 | 1,243.20 | **1,244.76** in the 2013 book |
| 2014 | 1,286.01, from the 2015 book's "2014 Approved" | **1,299.58** in the 2015 book |
| 2015 | 1,358.77 | **1,383.12** in the 2016 book |
| 2016 | 1,419.12 | **1,427.24** in the 2017 book |
| 2018 | 1,451.09 | **1,465.07** in the 2019 book |
| 2019 | 1,432.58 | **1,444.11** in the 2020 book |
| 2020 | 1,475.36 | **1,456.86** in the 2021 book |
| 2021 | 1,375.83 | **1,402.20** in the 2022 and 2023 books |
| 2022 | 1,460.71 | **1,491.71** in the 2023 book |

Only the latest restatement is carried, because two rows cannot share one (`year`, `measure`, `basis`) key.

**The scanned books confirm 2005–2010 to the hundredth.** The 2007, 2009 and 2010 books survive only as scans. Read by OCR, each one's "Summary of Standard FTEs by City Department" gives three years exactly as the born-digital books do, and its printed variance column checks: 1,251.34 − 1,218.84 = 32.50 in the 2007 book, 1,288.52 − 1,281.17 = 7.35 in 2009, and 1,248.24 − 1,288.52 = −40.28 in 2010.

**2002 has one source, read by OCR.** It comes from the 2011 book's "History of Standard FTEs" chart. Nine of that table's other columns match independently sourced values to the hundredth, but one does not. The table gives 2006 as 1,218.34, while the 2006–2007, 2007 and 2008 books all say 1,218.84, and the 2006–2007 book's printed variance column (1,218.84 − 1,212.11 = 6.73) confirms 1,218.84. The table therefore carries at least one misread digit, and nothing corroborates 2002. Treat it with more caution than the rest of the series. The same table's 2001 column is not recorded, because it falls outside the chart's own title, "2002 to 2011".

**2024 dips, and the dip is real.** The 2024 book gives 1,509.13 FTE, 31 below both 2023 (1,540.09) and 2025 (1,539.10). That looks like a misread and is not. The 2025 book calls its own figure "an increase of 2.0% from 2024", which puts 2024 at 1,508.9. The 2024 figure comes from the book's "By the Numbers" panel, where the 2023 and 2025 books print their staffing levels too.

**2019 and 2020 come from their own books' staffing tables, read by OCR.** The page dump never held those pages. Each book states its level twice, in prose and in the table, and every column of both tables sums to its printed total. The 2019 table starts from 2018's revised level, 1,465.07, takes off 2.88 and 33.11 FTE to reach 1,429.08, and adds council's 3.50 for 1,432.58. The 2020 table adds 15.00 standard and 16.25 fixed-term FTE to 2019's revised 1,444.11, for 1,475.36. The 2020 book is also the first to list seasonal "non-standard" staff, 190.95 FTE. They are outside the headline and are not recorded.

`positions_*` and `staffing_fte` do not reconcile arithmetically. The changes are General Fund and departmental in scope, while the level is citywide. Subtracting one year's eliminations from the prior level will not land on the next year's level.

### Departments

#### 16. Department spending is bucketed, and the buckets are coarse on purpose

Boulder reorganized its departments repeatedly over twenty years, so the raw labels do not form a series. In 2005, **Public Works is a single $67.4M slice**. By 2024 that money is spread across Transportation and Mobility, Utilities, Facilities and Fleet, and development review. The split cannot be recovered for most years. The books divide Public Works in their *staffing* tables, but the *spending* pies print it as one slice in 2005–2009 and 2012–2020, and divide it only in 2010, 2011 and 2021. So `deptexp_*` uses seven buckets, coarse enough that the coarsest year still maps:

| Bucket | Holds |
|---|---|
| `public_safety` | Police, Fire and Fire-Rescue, police and fire pensions |
| `infrastructure` | Public Works and all its successors (Transportation and Mobility, Utilities, Facilities and Fleet), plus DUHMD/Parking Services, later called Community Vitality |
| `parks_openspace` | Parks and Recreation, Open Space and Mountain Parks |
| `community_services` | Housing and Human Services, Library, Arts |
| `planning_climate` | Planning and Development Services, Community Planning and Sustainability, the energy municipalization effort, Climate Initiatives |
| `administration` | Council, Manager, Attorney, Finance, HR, IT, Communications, Municipal Court, Administrative and Internal Services, General Government and Governance |
| `citywide_debt` | Debt service as printed in the pies, and Fundwide / Citywide |

DUHMD is the Downtown and University Hill Management Division. It mostly runs parking and district management, which is why it sits in `infrastructure` rather than `planning_climate`.

**Every assignment is recorded per year** in `budget-history-department-crosswalk.csv`, with a note wherever the call was a judgment. The validation report counts the rows, labels and notes. Anyone who disagrees with a bucket can re-bucket from that file without reopening the PDFs. The build refuses to run if a pie brings a department label that has no bucket, and it names the label. Defaulting an unknown department into some bucket would put a number in a chart that nobody chose to put there. The build also checks that the buckets plus any balancing line sum to `budget_total`, and that a label never changes bucket between years unless its row carries a note.

Know these boundaries before charting:

- **Police and fire are one slice in 2019 and 2020.** The single "Public Safety" slices are $59.2M and $62.3M. 2021 splits them again at $36.9M and $21.3M.
- **Housing moves between buckets.** It is combined with human services in `community_services` in most years, and printed as a slice of its own in 2013–2015, still in `community_services`. In 2016–2018 it sits inside Planning, Housing and Sustainability, in `planning_climate`. Across 2016–2018 those two buckets therefore trade housing's budget, about $5M a year in the years it is printed separately.
- **The pies print no debt slice in 2019–2022,** so `deptexp_citywide_debt` has no row in those years. The pies still sum to their totals, so the debt service sits inside other slices. It is absent, not zero.
- **`administration` and `citywide_debt` trade content across the series.** The General Government line of 2005–2012 probably holds non-departmental items that the 2024–2026 export and the 2027 budget book put in Fundwide / Citywide. That makes it the least comparable pair. The step shows between 2022 and 2025, when Fundwide / Citywide enters `deptexp`: `administration` is 9.7% of citywide spending in 2022 and 9.1% in 2025, and `citywide_debt` goes from no row to 6.9%.
- **2025–2027 come from one table,** the 2027 budget book's, which prints 2025 and 2026 in the 2027 department structure. The 2022 pie's Community Vitality and Library & Arts have no line of their own there. Community Vitality still had staff in 2025 and 2026, so its spending sits inside other lines in those years.
- **The printed debt slice is General Fund debt only.** The 2005, 2007 and 2009–2011 pies all note that non-General-Fund debt service sits inside the departments. The bucket is consistent across years, but it is not all of the city's debt service.
- **Internal Services, 2013–2022, carries some capital.** The 2018 book defines it as Finance, HR, IT, General Fund capital and other, so `administration` is not purely overhead in those years.
- **The energy municipalization effort** is printed as ES and EUD (Energy Strategy and Electric Utility Development) in 2013–2015, as Energy in 2018 and as Energy Strategy in 2019. It has no line of its own in 2016–2017. It is bucketed as climate and energy policy rather than as a utility, because the city never owned the utility.

#### 17. `deptexp` and `deptexpfiltered` both add up, and still do not compare

This is the sharpest trap in the dataset, because no arithmetic check can catch it.

`deptexp_*` covers 2005–2022 and 2025–2027. The first run comes from the books' own citywide pies, the second from the 2027 budget book's citywide table, which the book draws as a pie. It includes every fund and is on the same footing every year: each year sums to that year's published citywide total.

`deptexpfiltered_*` covers 2024–2026 and comes from an OpenGov cost-center export taken with a 23-fund filter. That filter leaves out the utility, debt-service and internal-service funds. The export's twenty cost centers total $407.8M, $473.4M and $411.9M against published citywide budgets of $515.4M, $589.3M and $521.0M. The shortfall is carried explicitly as `deptexpfiltered_funds_outside_export` (`derived`, because it is a difference rather than a reported figure). So this family *also* sums to `budget_total`, and the reconciliation passes for both families.

What breaks is the **composition**:

| `infrastructure`, as a share of citywide spending | 2022 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| `deptexp` | **51.8%** | none | 44.2% | **39.0%** |
| `deptexpfiltered` | none | 18.1% | 22.9% | **15.8%** |

Boulder did not stop maintaining things in 2023. The filter moves nearly all utility spending out of the departments and into the balancing line. The giveaway is the "Utilities" cost center at **$0.34M in 2026**, against **$124.39M** in the unfiltered table. Charting the two families as one series shows infrastructure halving.

The separate prefixes exist so that this mistake takes effort rather than inattention. 2025 and 2026 are in both families, so the two can be compared directly. **Only 2024 has no unfiltered figures.** The 2026 budget book prints a 2024 column in the same table, but it sums to $514.22M against the published $515.4M, too far off to join `deptexp`.

The 2026 budget book also checks the 2027 book's table. Its 2025 column matches all twenty lines to the dollar. Its 2026 column matches too, except Fundwide / Citywide, which is $237,675 lower. That leaves its table $0.26M short of the $521.0M the book states, and the 2027 book's 2026 column ($520.98M) is used.

#### 18. Nine of the eighteen pie years were read by OCR

pypdf reads nine years of the citywide pie: 2005, 2006, 2014–2017 and 2020–2022. Each one sums, to the thousand, to the citywide total its own book publishes. The other nine come from OCR, for three different reasons:

- **2007, 2009 and 2010** are in books that survive only as scans.
- **2008** is in a born-digital book, but its pie is on p72 and the page dump held only p71 and p73. Tier 3 of the OCR stage, which reads two pages either side of every published figure, reached it from the summary block.
- **2011–2013, 2018 and 2019** are on pages whose pypdf text fails the sum check.

The sum check is what makes the pies trustworthy. This is how pypdf's text of those five years fails it:

- **2011 and 2012** come out interleaved beyond repair. 2012 reads "Pol ice 29, 593 Comm Planning Parks and Rec 12% and SUSt 24, 229 S/, 644 10%", in which the 32% belongs to Public Works.
- **2013's** legible slices fall short of its printed total.
- **2018's** slices double-count the pie's own subtotals.
- **2019** leaves its slices in an image.

Pairing those labels with those values would be guessing. A wrong guess would not look wrong: it would silently move Police's budget to Open Space. So the extractor rejects the pie rather than guess.

OCR recovers all nine years, and every recovered year passes the same sum check. The 2011 pie's fourteen slices come to $231,030 thousand exactly, and the 2012 pie's twelve come to $238,960 thousand. These rows cite `booksocr`.

**The 2010 book prints two pies that both look citywide.** The one on p74, in the citywide summaries, charts the adopted budget and sums to $230,149 thousand, the book's own total. The one on p28, in the budget message, charts the city manager's recommended budget, $229,543 thousand. Both fall within the $1.5M the extractor allows between a pie and the citywide total, so it now keeps the closer one and reports the other.

### OCR

#### 19. OCR read the pages pypdf could not, and got some things wrong

`booksocr` marks figures that Datalab read from pages whose text layer pypdf cannot use. The same pages also produced three kinds of error, and every one was rejected.

**Values invented from percentages.** Where a chart prints shares and not dollars, OCR returns dollars anyway by multiplying. In the 2019 book that gave Police $35,370 against a printed 10%, which is 9.999% of the total, to the dollar. For contrast, the 2018 book's real Police figure is $35,762 against a printed 9%, or 9.188%. A real value misses `pct × total` by hundreds of thousands because the printed percentage is rounded, while a fabricated value lands right on it. A sum check cannot catch this, because fabricated slices add up to the total as neatly as real ones. So `budget-books-extract.py` rejects a pie when more than half its slices land within 0.01% of `pct × total`. The 2019 citywide revenue donut shows a variant: OCR added eleven rows of dollar values, eight of them $5,380, for sub-items the chart gives only as percentages. Only the seven real slices, which sum to the printed total, are recorded.

**A bar chart read as numbers.** The 2019 property-tax chart came back as $25,000 / $2,000 / $2,000 / $1,000, which are round numbers read off bar heights. None of them is recorded. The 2019 and 2020 staffing charts came back the same way, as round numbers such as 1,420 for 2019 beside a printed 1,432.58, and are not recorded either.

**A single-digit misread.** The 2011 book's FTE history table gives 2006 as 1,218.34 where three other books say 1,218.84 ([caveat 15](#15-staffing-one-level-series-and-a-separate-family-of-changes)). The published value stands and the OCR reading was discarded. This is the clearest argument for using OCR to validate rather than to replace: OCR is a second witness, not a better one.

**Validation after all four tiers (September 23, 2026): 184 figures confirmed independently, none contradicted.** Tier 1 read the 1,137 pages of the three scanned Volume 1s. Tier 3 re-read every page a published figure came from, plus two pages either side. With tiers 2 and 4, that makes 1,515 OCR'd pages with text. The extractor was run over the OCR text alone. Each figure it read was compared with the dataset's 541 printed book figures: its rows from the books, the council-packet totals the books restate, and every pie slice. The 22 unmapped revenue remainders are left out, because they are this dataset's arithmetic and were never printed.

| Comparison | Figures |
|---|---:|
| Independent: published from pypdf, re-read by OCR | **166** |
| Independent: a council-packet figure, read by OCR from that year's book | **11** |
| Independent: published from one OCR'd page, printed again on another and read there | **7** |
| Circular: published from OCR, read back from the same page | 123 |
| No reading the extractor can match | 234 |

The circular comparisons are listed separately on purpose. The OCR stage never re-sends a page it has cached, so a figure read from OCR "agreeing" with itself is the same bytes compared twice. Counting those as confirmation would overstate the evidence by two thirds.

**No reading contradicts a published figure.** Eight readings differ from one, and each is a different figure rather than a misread:

- Five are recommended budgets quoted in a city manager's message: the 2007 and 2009 totals, and the 2024 book's total, operating and capital ([caveat 11](#11-book-figures-occasionally-disagree-with-later-council-packets)).
- Three are the 2025 book's own $589.5M, against the packet's $589.3M.

Another 23 are figures the books round in prose, such as "$270 million" or "$277.6 million", and each agrees at the precision printed.

**The extractor does not read everything back.** It has no reader for revenue charts or Funds Summary tables, and it cannot parse several newer layouts, among them the OCR tables of the 2018, 2019, 2021 and 2022 department pies and the revised columns of the 2019 and 2020 staffing tables. So 234 published figures have no matching reading. A direct search finds the printed number for 232 of them: 224 in the OCR text, and 8 on pages that only pypdf has read, such as the 2026 book's revenue table. The last two are council-packet figures that the books print differently, 2024's General Fund and 2025's total ([caveat 11](#11-book-figures-occasionally-disagree-with-later-council-packets)).

Tier 4 also reached two pages the born-digital dump never contained. **2011's summary block** (page 65) gives that year its operating/capital split and is anchored to a total already read independently from prose. **2017's staffing sentence**, "a citywide staffing level of 1,447 FTE", uses the same wording and chart context as the 2016 and 2018 books, and matches the 1,447.36 in its department table. Tier 3 reached three more: the 2008 book's department and revenue pies (pages 72–73), and the 2024 book's "By the Numbers" panel with that year's staffing level. Eight pages added to tier 2 afterwards reached four more: the 2019 and 2020 staffing tables, and the second pages of the 2005 and 2006–2007 Uses of Funds tables, which carry "Total General Fund Uses".

**Batched and single-page OCR agree.** Nine 2011 pages already converted one at a time were converted again as one batch. The extractor read the same 22 figures from both, and no running header was dropped. The README's OCR section has the details.

**What OCR settled.** Tier 1 gave 2007 and 2009 their first citywide totals. It replaced two derived 2010 values, the total and total revenue, with the 2010 book's own figures, both inside the ranges they had been derived to. With tier 3 it also filled the department pies and revenue by source for 2007–2010, and General Fund columns for 2005–2009. Pages that tiers 3 and 4 had already converted filled more: the 2018–2022 summary blocks, which give 2018–2021 their capital budgets, and the 2013–2022 revenue charts. Before OCR, 2013 had only a total rounded to "$255 million". It now has an exact total and a full operating/capital/General Fund split, with both block identities holding. The 2011 revenue pie confirmed all eight hand-transcribed slices, including the two 4% slices whose labels had been assigned by adjacency. The city's own notes on those pages also confirm three bucket assignments:

- "General Government is comprised of City Council, City Manager's Office, City Attorney's Office, Municipal Court".
- "Internal Services includes Human Resources, Finance, Information Technology".
- "Public Works groups together Development and Support Services, Transportation, and Utilities".

### Annual financial reports

#### 20. Tax collections are audited, and 1–2% above the packet's year-end figures

`salesuse_total` and `property_tax_revenue` actuals come from the annual financial reports' "Changes in Fund Balances – Governmental Funds". That table covers every governmental fund on the modified accrual basis, the one budgets use. For 2022–2025 the council packet printed its own year-end figures, and the audited ones run higher:

| Year | Sales and use tax, audited | Packet | Property tax, audited | Packet |
|---|---|---|---|---|
| 2022 | $171.34M | $169.11M | $51.56M | none |
| 2023 | $178.21M | $175.52M | $49.28M | $48.74M |
| 2024 | $176.40M | $173.90M | $61.25M | $60.63M |
| 2025 | $182.37M | $178.75M | $58.52M | $57.58M |

The packet's figures are unaudited, and neither document says what the difference is. The dataset carries the audited figures for every year, so each series has one source from 2007 to 2025. The packet's adopted, revised and forecast figures stay beside them, and its components (`salesuse_retail` and the rest) still sum to its own totals above, not to the audited ones.

The 2027 budget book charts the same collections by fund. Its bars for 2023–2025 repeat the packet's year-end figures to within $0.01M, except 2025 property tax, which it puts at $57.73M against the packet's $57.58M. Its 2026 bars repeat the packet's forecasts, $178.71M and $57.33M, and its 2027 bars sum to the 2027 figures used here.

No report ever revises these two lines: every report prints the same figure for every year it covers. The reports' government-wide statement of activities gives the same taxes on the full accrual basis and matches in every year but 2017 and 2018, where it has $135.91M and $142.34M of sales and use tax against $131.86M and $146.40M. It is not used.

#### 21. Taxable sales are the tax base, and 2013, 2014 and 2017 were revised

`taxablesales_*` is the value of sales subject to the city's tax, by market sector, from the reports' "Taxable Sales by Market Sector". It reached $4.64 billion in 2025. The sectors sum to the printed total in every year of every report. The same table gives the tax rates: the direct city rate was 3.56% in 2007, 3.41% from 2008 to 2013, 3.56% in 2014 and 3.86% since 2015, plus 0.15% on food service throughout.

Two revisions show up in later reports:

- **The 2018 report moved 2013 and 2014 between sectors.** Construction use tax rose by about $11M each year and the others fell, leaving each total within $2 thousand.
- **The 2017 report's own 2017 totals $3.59 billion, and every later report prints $3.52 billion.** A footnote says 2017 revenues were revised, mostly because of a large use tax payment received in March 2018 and accrued back.

Each year keeps its own report's figures (for 2007–2015, the 2016 report's), and the latest report's whole table for that year goes beside it as `restated`, so both versions sum to their totals.

#### 22. Staffing by function is the budget's count, and its totals do not always match `staffing_fte`

The reports' "Full-Time Equivalent City Employees by Functions/Programs" cites the "City of Boulder Summary of Standard FTE's per the annual budget document". So it counts budgeted positions, not people on the payroll. Its total equals the budget's adopted level, `staffing_fte`, in 11 of 19 years. It differs in these:

| Year | Report total | `staffing_fte` adopted | Restated |
|---|---|---|---|
| 2011 | 1,230.50 | 1,228.50 | 1,231.25 |
| 2016 | 1,419.15 | 1,419.12 | 1,427.24 |
| 2020 | 1,442.17 | 1,475.36 | 1,456.86 |
| 2021 | 1,347.30 | 1,375.83 | 1,402.20 |
| 2022 | 1,463.45 | 1,460.71 | 1,491.71 |
| 2023 | 1,487.71 | 1,540.09 | |
| 2024 | 1,508.13 | 1,509.13 | |
| 2025 | 1,538.07 | 1,539.10 | |

2011's is the 2012 book's revision, because the earliest report in hand prints that. The rest are unexplained, and 2023's gap of 52 FTE is the largest. So the reports' figures are their own family, `ftefunc_*`, and never join `staffing_fte`.

Three more things to know:

- **The 2021 report leaves out its Development line,** 54.11 FTE in 2017 to 55.84 in 2021, although its totals include it. Its 2021 figure comes from the 2022 report.
- **Lines get renamed and reorganized.** "City Manager- Downtown & University Hill Mgt" becomes "City Manager- Community Vitality" in the 2018 report, and each name is its own measure. The reports' footnotes record the rest: Energy Strategy & Electric Utility split between Community Planning and Sustainability and Climate Initiatives in 2022, and Planning and Development, Fleet and Facility, and Housing and Human Services were combined in 2024. A dash means the line did not exist that year, and it is not recorded.
- **The buckets, `ftebucket_*`, are the spending pies'** ([caveat 16](#16-department-spending-is-bucketed-and-the-buckets-are-coarse-on-purpose)). Police and fire are public safety. Public Works and Community Vitality, including its earlier Downtown & University Hill name, are infrastructure. Library, arts, housing and human services are community services. Parks and Open Space are parks and open space. The planning, energy and climate lines are planning and climate, and so is Environmental Affairs, a line only in 2007–2009 with no pie counterpart. The rest is administration. No FTE line is debt, so there are six buckets, not seven.

#### 23. The reports' General Fund is broader than the books'

`acfrgf_*` is the General Fund's "Statement of Revenues, Expenditures, and Changes in Fund Balances – Budget and Actual (Budgetary Basis)", line by line, one year per report. Its bases are the statement's columns: `adopted` is the original budget, `final` the budget as amended by year's end, and `actual` what came in and went out. The fund is the one the city reports for audit, and it is not the books' "Total General Fund Uses" ([caveat 3](#3-two-general-fund-measures-6-to-19-percent-apart)). Its original budget, with transfers, differs from the books' figures in every year checked:

| Year | Report: spending + transfers out | Book: `budget_general_fund` | Report: revenue + transfers in | Book: `budget_general_fund_revenue` |
|---|---|---|---|---|
| 2016 | $126.6M | $132.3M | $122.0M | $128.3M |
| 2020 | $164.8M | $161.5M | $160.3M | $157.4M |
| 2025 | $255.1M | $210.9M | $201.1M | $190.6M |

Use it to see how the General Fund's budget moved during the year and how the year turned out, never as more years of `budget_general_fund`. The final budget can run far above the original because it takes in carryforwards and mid-year appropriations: in 2025, $365.5M of spending against an original $222.1M. The revenue and expenditure lines sum to their printed totals in every report.

#### 24. Assessed value is filed under the year it is taxed

Each report's legal debt margin gives the assessed value certified in that fiscal year, which sets the property tax collected the next year. The council packets label it by that next year, and so does `property_assessed_value`: the 2024 report's $5,091.58M is the 2025 value, the packet's $5,091M. The reports give `actual`s for 2017–2026, and the packet's `adopted` and `revised_projection` figures stay beside them. Each report's value is checked against the debt limit printed under it, 3% of assessed value.

#### 25. How the annual-report figures were read and checked

`acfr-extract.py` found five tables in each report, 98 pages in all, and Datalab converted them for $0.75. That includes two pages of the 2023 report's Open Space Fund statement, taken by mistake. Every figure was read twice: from the PDF's text layer, placing each row by its height on the page, and from Datalab's markdown. Of 5,864 cells, the two readings agree on 4,649. Each figure `budget-history.py` loads is confirmed one of four ways:

| Confirmed by | Cells |
|---|---:|
| Both readings agree | 4,649 |
| Another report prints the same figure for the same line and year | 900 |
| The page's own sums pin it down | 304 |
| The page's text layer contains it, where no row could be placed | 2 |
| Unconfirmed, and never loaded | 9 |

The nine are five of Development's 2022-report figures that Datalab moved into the heading row above, and four dashes. The 28 cells where the readings disagree are all settled, 22 by other reports and 6 by their column's sums. Twenty are in the 2022 staffing table. The other eight are in the taxable sales Refunds row, whose only figure (2011) the text layer puts in the wrong year.

What went wrong in the reading, and what caught it:

- **Two reports have no usable text layer.** The 2021 report's statistical section is the city's own OCR of a scan ("Cha1Jges In Fund Balances", "110,01 I"), and the 2023 report's text is font codes. Datalab was made to OCR every page of both instead of reusing those layers, and both rest on its reading, confirmed by the reports that print the same years. The 2023 file was later replaced by a copy run through Acrobat's text recognition. That changed the fonts on five of its 316 pages, none of them these tables, so their text is still font codes. The ten pages were sent to Datalab again, for 7.5 cents, and every figure read the same.
- **Datalab slides a column's cells up or down a row but keeps their order.** The 2021 report's 2021 staffing column moves up a row from Parks and Recreation on. So each right-hand page of a two-page table is matched to the left by order within each column, not by row.
- **Datalab can also drop one row and add another,** which that matching cannot see. In the 2022 staffing table its figures sit a row off from Development down. The text layer, which places rows by position, disagrees, and every other report sides with the text layer.
- **One page can stack two tables.** The 2025 report prints taxable sales for 2016–2020 above 2021–2025. Both readers first read the second block under the first block's years, and on those rows they agreed. Agreement alone is therefore not taken as proof: a year's figures are also compared with every other report that prints them.
- **Simple rules misfire on labels.** "Strategy" contains "rate" and "Construction Sales Tax" ends in "Sales Tax", so both lines were briefly filed as tax rates. The column sums caught both.

## Recipes

**pandas: one measure on one basis, and a composition**

```python
import pandas as pd
df = pd.read_csv("budget-history.csv")

# The headline total, as adopted (2027 as recommended; no year carries both)
totals = (df[(df.measure == "budget_total") & df.basis.isin(["adopted", "recommended"])]
          .set_index("year")["value"])

# Sales and use tax by component, actuals only
comp = (df[df.measure.str.startswith("salesuse_")
           & ~df.measure.isin(["salesuse_total", "salesuse_component_residual"])
           & (df.basis == "actual")]
        .pivot(index="year", columns="measure", values="value"))

# Spending by bucket, 2005-2022 and 2025-2027 -- never mixed with deptexpfiltered_*
dept = (df[df.measure.str.startswith("deptexp_")]
        .pivot(index="year", columns="measure", values="value"))

# Audited tax collections, 2007-2025
tax = (df[df.measure.isin(["salesuse_total", "property_tax_revenue"]) & (df.basis == "actual")]
       .pivot(index="year", columns="measure", values="value"))

# Budgeted staffing by bucket, from the annual reports -- never mixed with staffing_fte
fte = (df[df.measure.str.startswith("ftebucket_")]
       .pivot(index="year", columns="measure", values="value"))
```

`pivot`, unlike `pivot_table`, raises an error if a year and measure appear twice. That happens exactly when a filter has let two bases through, which is the mistake to catch.

**R, tidyverse**

```r
library(tidyverse)
df <- read_csv("budget-history.csv")
totals <- df |>
  filter(measure == "budget_total", basis %in% c("adopted", "recommended")) |>
  select(year, basis, value)
```

**Straight to a chart.** Use `budget-history-wide.csv`. It already has one row per year, and each series carries a `*_basis` column so a footnote can say which version each point is.

## Extending the series

**Adding a year or a figure.** Add the figure to the matching block in `budget-history.py` with its `source_id`, add any new document to `SOURCES`, and re-run the script. Reconciliation will catch a mistyped component, because it checks every published total against the sum of its parts. For the OpenGov snapshot it checks to the dollar.

**The cheapest route backwards is a book's own comparison columns.** Every budget book before 2012 prints its summary tables three or four years wide, with the basis of each column in the header:

```
CITY OF BOULDER / SUMMARY OF USES OF FUNDS (in $1,000s)
    2006       2007       2008       2009
  ACTUAL    APPROVED   APPROVED   PROJECTED
Total General Fund Uses   89,123   89,650   94,238   95,883
```

One page therefore yields four years. That is how 2007, 2009 and 2010 have values at all: the 2008 book states 2007, and the 2011 book states 2009 and 2010, whose own books are scans. `budget-books-extract.py` reads these tables automatically (`MULTIYEAR_TABLES`), and adding a row type takes three lines.

**OpenGov exports are the other route to deeper history.** The `snapshot2023` source is a "Data Snapshot" CSV downloaded from an OpenGov transparency view. The portal has no public API (its documented REST paths return 404), but each view exports clean, to-the-dollar CSV from the page itself. Every additional year is a download, not a PDF transcription. To go further back, open a Sources & Uses view for an earlier budget year and export it the same way:

```
https://cityofboulderco.opengov.com/transparency/#/<dataset-id>
    ?accountType=revenuesVersusExpenses&breakdown=types&year=<year>
```

Each export carries three columns (prior-year actual, current adopted, current total budget), so **one download adds up to three years**. The 2023 view, dataset `65843`, reached back to 2021 actuals. Two things to watch when adding one:

- **Record the column labels as `basis`.** They differ per export, and "Actual", "Adopted Budget" and "Total Budget" are three different things ([caveat 1](#1-two-accounting-bases-never-one-series)).
- **Keep them in the `sources_`/`uses_` family.** Do not fold them into `budget_*`, however well the year seems to match.

**The online budget books cover 2024–2027.** The 2026 and 2027 books are OpenGov Stories sites, and their tables are transparency-portal views embedded in the page: dataset `148111` in the 2026 book, with 2024–2026 approved columns, and `188635` in the 2027 book, with 2025 and 2026 approved and 2027 recommended. The revenue and department figures here come from its views of citywide sources (saved view 842324), General Fund sources (842206) and citywide uses by department (842330). Staffing and the tax forecasts are in the pages' own tables and text. The pages load only in a browser. When council adopts the 2027 budget, its book's tables give the `adopted` figures to put beside these `recommended` ones.

**Adding the 2005–2015 annual financial reports.** Put each PDF in `raw-acfr/`, named by fiscal year (`2014.pdf`), and run the three stages in `acfr-extract.py`'s docstring: `--locate`, then OCR of the pages it lists, then the read. Check the locator's printout before paying for OCR. An older report whose titles read differently needs its pages in `OVERRIDES`, as the 2021 and 2023 reports do. Each report prints ten years, so the 2011–2015 reports reach back to 2002, and every year they share with the 2016 report is a cross-check.

OpenGov does not publish staffing *levels*. Sources & Uses carries `uses_expense_personnel` (payroll dollars), which is a reasonable proxy for staffing cost but not a headcount. The FTE series comes from the budget books.
