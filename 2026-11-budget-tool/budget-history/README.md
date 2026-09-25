# Boulder budget history, 2002–2027

The City of Boulder's budget over twenty-six years: citywide totals, the General Fund, staffing, revenue by source, sales and use tax, property tax, and spending by department. The city's audited annual financial reports add tax collections back to 2007, staffing by function, the sales tax base and the General Fund's budget against its actuals. Every figure comes from a named document. Wherever that document prints a total beside its parts, the parts are checked against it.

## Question

What has Boulder budgeted each year since the early 2000s? That means the totals, the General Fund, where the money goes by department and where it comes from, and the staff it pays for. The answer gives the 2027 recommended budget its history, and it is the context behind the [Balance Boulder's Budget](../embed/) interactive.

There is no download to answer it from. Boulder publishes these figures in twenty-two years of PDF budget books, council study-session packets, slide decks and press releases, with the numbers in prose, summary blocks, pie charts and multi-year tables. The city's OpenGov budget portal has no public data endpoint. This directory is the transcription, with every step that produced it.

## What is here

| File | Grain | What it is |
|---|---|---|
| `budget-history.csv` | year × measure × basis | **The dataset**, in long format |
| `budget-history-wide.csv` | year | The 13 headline series, one basis each, ready to chart |
| `budget-history-provenance.csv` | source | The source documents, with URLs and retrieval dates |
| `budget-history-department-crosswalk.csv` | year × department line | Each department line as printed, the bucket it went into, and why |
| `budget-history-validation.md` | not a table | Counts, coverage and every check. Rebuilt on every run |
| `budget-history-data-dictionary.md` | not a table | Every column, code and caveat |

All CSVs are UTF-8 with LF line endings. The four `budget-history-*` CSVs are plain ASCII, so Excel opens them cleanly. Money is in millions of nominal dollars. **Read the [data dictionary](budget-history-data-dictionary.md) before charting,** especially [`basis`](budget-history-data-dictionary.md#basis-read-this-first) and [caveat 1](budget-history-data-dictionary.md#1-two-accounting-bases-never-one-series). Mixing a year's adopted figure with another year's actual, or the net headline totals with the gross OpenGov snapshot, produces changes that never happened.

## Coverage

| Series | Years | Notes |
|---|---|---|
| Citywide total | 2004–2027 | From 2008 the total includes the internal service funds; the 2008 book restates 2007 on that footing, 0.35% higher |
| Operating and capital | 2005–2027 | From the books' summary blocks where they print one, 2005–2022 |
| General Fund, all-in uses | 2003–2027 | 2003 is an actual only |
| General Fund revenue | 2003–2026 | 2003 is an actual only |
| Staffing level (FTE) | 2002–2026 | Every year, with later books' restatements beside the adopted figures |
| Spending by department | 2005–2022 | Seven buckets. 2024–2026 come from a filtered export that is **not** comparable |
| Revenue by source | 2005–2026 | The taxonomies differ, so only four categories line up. 2018 and 2022 include borrowing |
| Sales and use tax, property tax | 2007–2026 | Audited actuals for 2007–2025, from the annual financial reports; the packet's adopted, revised and forecast figures beside them ([caveat 20](budget-history-data-dictionary.md#20-tax-collections-are-audited-and-12-above-the-packets-year-end-figures)) |
| Staffing by function | 2007–2025 | Budgeted FTE by function from the annual reports, as printed and in the spending buckets. Its own family: its totals differ from the staffing level in 8 years ([caveat 22](budget-history-data-dictionary.md#22-staffing-by-function-is-the-budgets-count-and-its-totals-do-not-always-match-staffing_fte)) |
| Taxable sales by sector | 2007–2025 | The sales tax base, and the tax rates. 2013, 2014 and 2017 also as restated |
| Assessed value | 2017–2026 | Filed under the year the tax is collected |
| General Fund, budget and actual | 2016–2025 | The annual reports' General Fund: original budget, final budget and actual. Broader than the books' General Fund ([caveat 23](budget-history-data-dictionary.md#23-the-reports-general-fund-is-broader-than-the-books)) |

The exact years for every measure are in the validation report's [coverage table](budget-history-validation.md#coverage-by-measure). A missing year is absent, never zero. [Caveat 8](budget-history-data-dictionary.md#8-coverage-is-uneven-and-the-gaps-are-not-the-same-gaps) says why each gap exists.

## How good is it

**Every published total is checked against the sum of its published parts, and a failure stops the build before any file is written.** The checks are:

- operating + capital = total
- General Fund half + dedicated half = operating
- each year's department buckets sum to that year's total
- revenue components sum to their total
- the OpenGov snapshot's components sum to its totals, to the dollar
- no two rows share a key
- a department never changes bucket without a written reason
- the annual reports' staffing lines and buckets, taxable sales sectors and General Fund lines sum to their printed totals

The [validation report](budget-history-validation.md#checks) lists how many cases each check saw and the largest miss on this build.

**The books check themselves.** Every book from 2005 to 2022 prints a citywide summary block in which capital plus operating equals the total and the General Fund and dedicated halves sum to operating, to within $1,000. The one exception is 2019, whose block has two boxes exactly $255,000 short ([caveat 2](budget-history-data-dictionary.md#2-the-headline-totals-are-one-continuous-net-series)). Each spending pie sums to the citywide total its own book publishes. A figure is kept only if it passes, and a pie that does not add up is rejected rather than guessed at.

**Figures read by OCR are marked, and were tested against figures read without it.** Figures from pages pypdf cannot read, or never reached, cite `booksocr` instead of `books`. They cover the 2007, 2009 and 2010 books, which survive only as scans, nine spending-pie years, most revenue charts from 2007 to 2024, the 2011–2013 and 2018–2022 summary blocks, General Fund pies and tables from 2013 to 2019, the second pages of the 2005 and 2006–2007 General Fund tables, and staffing for 2002, 2019, 2020 and 2024. OCR also re-read every page holding a pie, table or summary block, and the pages around every published figure. It independently confirmed 184 published figures, 166 of them read by pypdf, and contradicted none ([caveat 19](budget-history-data-dictionary.md#19-ocr-read-the-pages-pypdf-could-not-and-got-some-things-wrong)). It also produced three kinds of error, each caught and rejected: values invented from percentages, a bar chart read as numbers, and a misread digit.

**Annual-report figures were read twice, and every one used is confirmed.** The ten reports' tables were read from each PDF's text layer and by Datalab's OCR of the same 98 pages, which cost $0.75. A figure is used only if the two readings agree (4,649 of 5,864 cells), another report prints it identically (900), its page's own sums pin it down (304), or its page's text layer contains it (2). The nine left unconfirmed are never loaded. Comparing every year across the reports that print it found 40 revised figures, all in taxable sales: the 2018 report moves 2013 and 2014 between sectors, and every report after 2017's revises that year, as a footnote explains ([caveat 21](budget-history-data-dictionary.md#21-taxable-sales-are-the-tax-base-and-2013-2014-and-2017-were-revised), [caveat 25](budget-history-data-dictionary.md#25-how-the-annual-report-figures-were-read-and-checked)).

**What the checks cannot catch.** Two families add up perfectly and still do not compare. The first pair is the net headline totals and the gross OpenGov snapshot, $83.4M apart in 2023. The second pair is the books' department pies and the 2024–2026 export, which moves nearly all utility spending out of the departments. The data dictionary's caveats [1](budget-history-data-dictionary.md#1-two-accounting-bases-never-one-series) and [17](budget-history-data-dictionary.md#17-deptexp-and-deptexpfiltered-both-add-up-and-still-do-not-compare) explain both. Keeping each family under its own prefix, `sources_`/`uses_` and `deptexpfiltered_`, makes mixing them take effort rather than inattention.

## Sources

| `source_id` | Document | Supplies |
|---|---|---|
| `books` | [City of Boulder annual budget books](https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2), 2005–2026, read from the PDF text layer | Totals, the General Fund, staffing and the department pies |
| `booksocr` | The same books, pages read by Datalab OCR | What pypdf cannot read or never reached: the 2007, 2009 and 2010 books, nine spending-pie years, most revenue charts from 2007 to 2024, the 2011–2013 and 2018–2022 summary blocks, staffing for 2002, 2019, 2020 and 2024 |
| `snapshot2023` | [OpenGov Sources & Uses, 2023](https://cityofboulderco.opengov.com/transparency/#/65843/accountType=revenuesVersusExpenses&breakdown=types&year=2023), CSV export | Gross revenue and expense by type, 2021–2023 |
| `deptsnapshot2026` | OpenGov Sources and Uses by cost center, 2026, CSV export | Spending by department, 2024–2026, with a fund filter |
| `forecast2026` | 2026 Financial Forecast, council study session, May 14, 2026 | Totals 2023–2026; sales, use and property tax; General Fund gaps |
| `rec2026` | 2026 Recommended Budget, council study session | 2026 revenue by source and position eliminations |
| `rec2027` | [2027 Recommended Budget news release](https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input), August 28, 2026 | 2027 totals, General Fund, gap, positions |
| `glance2027` | [Budget At-A-Glance](https://bouldercolorado.gov/budget-glance) | 2027 percentage changes, positions added and frozen |
| `acfr` | [City of Boulder Annual Comprehensive Financial Reports](https://bouldercolorado.gov/annual-comprehensive-financial-report-popular-annual-financial-report), fiscal 2016–2025, read from the PDF text layer | Audited tax collections from 2007, staffing by function, taxable sales, assessed value, and the General Fund's budget and actual |
| `acfrocr` | The same reports, read by Datalab OCR | The 2021 and 2023 reports, whose text layers are unusable, and cells the text layer could not place |
| `brl2027` | [Boulder Reporting Lab](https://boulderreportinglab.org/2026/09/08/boulders-proposed-2027-budget-would-cut-13-filled-jobs-and-trim-pool-hours/), September 8, 2026 | The savings from the 2027 position cuts |

`budget-history-provenance.csv` has titles, dates and notes for each. The books are 34 PDFs and 10,843 pages. Six volumes are scans with no text layer at all (1,651 pages): 2005 Volume 2, 2007 Volumes 1 and 2, 2009 Volumes 1 and 2, and 2010 Volume 1.

## How it is built

Four stages. The first three find figures in the budget books, and only the second costs money. The fourth is the dataset.

| Stage | Script | Reads | Writes |
|---|---|---|---|
| 1. Inventory | `budget-books-inventory.py` | the PDFs | `budget-books-inventory.csv`, and with `--dump-text` a JSONL of every matched page's text |
| 2. OCR | `budget-books-ocr.py` | the PDFs, and for tiers 3 and 4 the two `budget-books-*` CSVs | a JSONL of OCR'd pages, in the same shape as the text dump |
| 3. Extract | `budget-books-extract.py` | any number of those JSONL files | `budget-books-extracted.csv` (candidates) and `budget-books-pages-of-interest.csv` |
| 4. Build | `budget-history.py` | nothing | the four `budget-history-*` CSVs and the validation report |

Candidates from stage 3 are checked by a person and then typed into `budget-history.py` with their source. The script is the transcription record, and every value in it carries the ID of the document it came from.

**The annual financial reports take a shorter path, and the build reads one file: theirs.** The ten reports are small enough (57 MB) to live in `raw-acfr/`, with Datalab's OCR of the 98 pages read, `raw-acfr/acfr-ocr.jsonl`. `acfr-extract.py` reads five tables from each twice and writes every figure, with both readings and how it was confirmed, to `acfr-extracted.csv`. `budget-history.py` loads the confirmed ones instead of having some 1,700 figures typed in ([caveat 25](budget-history-data-dictionary.md#25-how-the-annual-report-figures-were-read-and-checked)):

```
python3 acfr-extract.py --locate                  # finds the tables' pages: acfr-pages.csv
python3 budget-books-ocr.py raw-acfr --pages-from acfr-pages.csv \
    -o raw-acfr/acfr-ocr.jsonl --estimate         # 98 pages, $0.74; then --yes
python3 acfr-extract.py                           # both readings: acfr-extracted.csv
```

The 2021 and 2023 reports' pages were sent with `--force-ocr`, which makes Datalab read the page image instead of those reports' unusable text layers.

Stages 1–3 run where the PDFs are, which is outside this repository because the books are 4.5 GB. The page dumps and the OCR cache are derived from the PDFs and are not committed. Stage 4 runs anywhere:

```
python3 budget-history.py          # no arguments; reads acfr-extracted.csv and writes next to itself
```

To repeat the book stages on a local copy of the PDFs (Python 3.7 or later, and `pip install pypdf`):

```
python3 budget-books-inventory.py ~/Downloads/ExportedContents/ --dump-text dump.jsonl
export DATALAB_API_KEY=...
python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --estimate     # prints the bill, sends nothing
python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --yes
python3 budget-books-extract.py dump.jsonl budget-books-ocr.jsonl -o budget-books-extracted.csv
```

`budget-books-ocr.py` explains its four tiers and what each costs. It caches every page it pays for, so an interrupted or repeated run never pays for a page twice.

### OCR: batches, cost and guardrails

The OCR stage sends each book's pages in batches of up to 100 and splits Datalab's answer back into one cached file per page. Datalab bills per page, so batching changes how long a run takes, not what it costs: tiers 1 and 3 together are 32 requests rather than 1,379. Sending one page per request was the original design, sized for a few hundred scattered pages. It is still available as `--batch-pages 1`, and is worth it only to isolate a page that keeps failing inside a batch. The script's docstring sets out the trade-offs in full. These are the rules it enforces:

| Guardrail | What it prevents |
|---|---|
| Nothing is sent without `--yes`. `--estimate` prints the pages, the cost, the number of requests and a floor on the time | A surprise bill or a surprise day-long run |
| A cached page is never sent again, whatever batch size wrote it | Paying twice for a page |
| Each batch is recorded in `_pending.json` from upload until its pages are cached, and the next run collects anything left there first | Paying twice after a crash, a sleeping laptop or a timeout. Datalab keeps results about a day |
| A batch that fails, or whose page breaks do not line up with the pages sent, caches nothing and is never re-sent automatically. Its raw output is kept as `_unsplit-…md` | Pages filed under the wrong number, and silent double billing |
| Pages Datalab reports as failed are left uncached | Failed conversions passing as blank pages |
| Uploads and status polls share one budget, `--rpm`, 10 requests a minute by default | Stalling on Datalab's rate limit |
| A batch over `--batch-mb` is halved, and nothing over 190 MB is ever uploaded | Datalab's 200 MB ceiling. The 2024 book is 247 MB |
| HTTP 402, the key's own spend cap, stops the run | Spending past a limit set on purpose. Set one in Datalab's billing settings |
| `_requests.jsonl` in the cache logs every request's pages, cents and time | Unaudited spend, and time estimates that are guesses |

**Batched output needs checking once.** The OCR engine looks across the pages of a request, and can drop text that repeats at the top or bottom of several pages as a running header. The extractor was validated on single-page output. Before relying on batches for a new kind of page, re-read ten pages that single-page runs already cached, into a scratch cache. This costs about 8 cents:

```
python3 budget-books-ocr.py ~/Downloads/ExportedContents/ --book "2011 Annual Budget.pdf" \
    --pages 65-68,83-88 --cache batch-check -o batch-check.jsonl --yes --verify
diff "budget-books-ocr-cache/2011 Annual Budget/p065.md" "batch-check/2011 Annual Budget/p065.md"
```

`--verify` should still find 2011's summary block (`budget_operating_general`) and its department pie. Wording can differ from run to run. A missing heading or table row is the thing to look for. `--verify` writes its own `batch-check-pages-of-interest.csv`, so it cannot overwrite the list tier 4 reads.

**Checked on September 23, 2026, against the real API.** The nine of those ten pages that hold text matched their single-page versions figure for figure, and the extractor read the same 22 figures from both. Page 66 is blank either way. What differed was cosmetic: heading levels, one invented table-header label and the converter's own descriptions of images. No running header was dropped. The same day, two batched requests of three and two pages came back split correctly in about 35 seconds each.

## Layout

```
budget-history/
├── README.md                                this file
├── budget-history-data-dictionary.md        every column, code and caveat
├── budget-history-validation.md             counts, coverage and checks (generated)
│
├── budget-history.py                        stage 4: the transcription record, checks, outputs
├── budget-history.csv                       the dataset, long
├── budget-history-wide.csv                  the headline series, one row per year
├── budget-history-provenance.csv            one row per source document
├── budget-history-department-crosswalk.csv  department lines and their buckets
│
├── budget-books-inventory.py                stage 1: what is in the corpus, and page text
├── budget-books-ocr.py                      stage 2: Datalab OCR, in priced tiers
├── budget-books-extract.py                  stage 3: candidate figures from page text
├── budget-books-extracted.csv               those candidates, with file and page
├── budget-books-pages-of-interest.csv       every page that looks as if it holds a figure
│
├── acfr-extract.py                          the annual reports: find five tables, read them twice
├── acfr-pages.csv                           the pages read
├── acfr-extracted.csv                       every figure, both readings, how it was confirmed
└── raw-acfr/                                the reports, fiscal 2016-2025, and acfr-ocr.jsonl
```
