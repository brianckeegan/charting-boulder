# Boulder budget history, 2002–2027

The City of Boulder's budget over twenty-six years: citywide totals, the General Fund, staffing, revenue by source, sales and use tax, property tax, and spending by department. Every figure is transcribed from a named document. Wherever that document prints a total beside its parts, the parts are checked against it.

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
| Citywide total | 2004–2027, except 2007 and 2009 | 2010 is derived from the 2011 book's stated percentage |
| Operating and capital | 2005–2027, except 2007, 2009 and 2010 | Capital is also missing for 2018–2021 |
| General Fund, all-in uses | 2006–2018 except 2013, and 2024–2027 | 2025 is derived |
| Staffing level (FTE) | 2002–2026, 20 years | Missing for 2014, 2015, 2019, 2020 and 2024 |
| Spending by department | 2005, 2006, 2011–2022 | Seven buckets. 2024–2026 come from a filtered export that is **not** comparable |
| Revenue by source | 2011, 2012, 2026, and a derived 2010 total | The taxonomies differ, so only four categories line up |
| Sales and use tax, property tax | 2022–2026 (property tax from 2023) | Adopted, revised, actual and forecast figures, side by side |

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

The [validation report](budget-history-validation.md#checks) lists how many cases each check saw and the largest miss on this build.

**The books check themselves.** Each readable book from 2005 to 2017 prints a citywide summary block in which capital plus operating equals the total and the General Fund and dedicated halves sum to operating, to within $1,000 in every year. Each spending pie sums to the citywide total its own book publishes. A figure is kept only if it passes, and a pie that does not add up is rejected rather than guessed at.

**Figures read by OCR are marked, and were tested against figures read without it.** Five spending-pie years, the 2012 revenue pie, the 2011–2013 summary blocks and two staffing levels come from pages whose text layer pypdf cannot use, and they cite `booksocr` instead of `books`. OCR also re-read every page holding a pie, table or summary block. It independently confirmed 146 published figures and contradicted none ([caveat 19](budget-history-data-dictionary.md#19-ocr-read-the-pages-pypdf-could-not-and-got-some-things-wrong)). It also produced three kinds of error, each caught and rejected: values invented from percentages, a bar chart read as numbers, and a misread digit.

**What the checks cannot catch.** Two families add up perfectly and still do not compare. The first pair is the net headline totals and the gross OpenGov snapshot, $83.4M apart in 2023. The second pair is the books' department pies and the 2024–2026 export, which moves nearly all utility spending out of the departments. The data dictionary's caveats [1](budget-history-data-dictionary.md#1-two-accounting-bases-never-one-series) and [17](budget-history-data-dictionary.md#17-deptexp-and-deptexpfiltered-both-add-up-and-still-do-not-compare) explain both. Keeping each family under its own prefix, `sources_`/`uses_` and `deptexpfiltered_`, makes mixing them take effort rather than inattention.

## Sources

| `source_id` | Document | Supplies |
|---|---|---|
| `books` | [City of Boulder annual budget books](https://documents.bouldercolorado.gov/WebLink/Browse.aspx?id=187445&dbid=0&repo=LF8PROD2), 2005–2026, read from the PDF text layer | Totals, the General Fund, staffing and the department pies |
| `booksocr` | The same books, pages read by Datalab OCR | What pypdf cannot read: five spending-pie years, the 2012 revenue pie, the 2011–2013 summary blocks, two staffing levels |
| `snapshot2023` | [OpenGov Sources & Uses, 2023](https://cityofboulderco.opengov.com/transparency/#/65843/accountType=revenuesVersusExpenses&breakdown=types&year=2023), CSV export | Gross revenue and expense by type, 2021–2023 |
| `deptsnapshot2026` | OpenGov Sources and Uses by cost center, 2026, CSV export | Spending by department, 2024–2026, with a fund filter |
| `forecast2026` | 2026 Financial Forecast, council study session, May 14, 2026 | Totals 2023–2026; sales, use and property tax; General Fund gaps |
| `rec2026` | 2026 Recommended Budget, council study session | 2026 revenue by source and position eliminations |
| `rec2027` | [2027 Recommended Budget news release](https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input), August 28, 2026 | 2027 totals, General Fund, gap, positions |
| `glance2027` | [Budget At-A-Glance](https://bouldercolorado.gov/budget-glance) | 2027 percentage changes, positions added and frozen |
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

Candidates from stage 3 are checked by a person and then typed into `budget-history.py` with their source. **The build reads no files.** The script is the transcription record, and every value in it carries the ID of the document it came from.

Stages 1–3 run where the PDFs are, which is outside this repository because the books are 4.5 GB. The page dumps and the OCR cache are derived from the PDFs and are not committed. Stage 4 runs anywhere:

```
python3 budget-history.py          # no arguments, no inputs, writes next to itself
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
└── budget-books-pages-of-interest.csv       every page that looks as if it holds a figure
```
