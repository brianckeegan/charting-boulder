# Boulder budget-book archive: data lake architecture and roadmap

**Status:** planning document, September 2026. This is a future project, separate from the `2026-11-budget-tool` column, and nothing in it is built yet.

**In one paragraph.** The City of Boulder's Laserfiche document archive holds its budget book for every year from 2005 to 2026, as PDFs: 34 volumes and 10,843 pages. Today those numbers are locked in page layouts, pie charts and scanned images, and every analysis starts by re-reading the PDFs. This project would convert the whole archive, once, into two things anyone can use: **the full text of every book as markdown**, and **every table and chart as structured data (CSV and JSON)**, each value traceable to its book and page. The result would be published as a citable, public-domain dataset. It would be a *data lake*: a store of every page and table in open file formats, kept close to the source and organized for many future analyses rather than one.

## Contents

1. [Decisions](#1-decisions)
2. [Starting point](#2-starting-point)
3. [Architecture](#3-architecture)
4. [Roadmap](#4-roadmap)
5. [Risks](#5-risks)
6. [Open questions](#6-open-questions)
7. [Appendices](#7-appendices): corpus inventory, lessons from the 2026 project, cost worksheet, glossary

---

## 1. Decisions

These were settled in a scoping interview in September 2026. The "Revisit if" column says what would reopen each one.

| Question | Decision | Why | Revisit if |
|---|---|---|---|
| Which documents? | **The 34 budget books only**, every volume, 2005–2026, including the capital-program Volume 2s | A bounded corpus that can be finished. The books are the city's own statement of each year's budget | Actual spending (the audited annual financial reports) or council packets become the question |
| Who is it for? | Four audiences, served in this order: **public release**, then **analysis for columns**, then **classes**, then **AI search and Q&A** | A citable public release forces the documentation and stable identifiers that every later audience needs | A column deadline needs a table before the release is ready |
| How are pages converted? | **Datalab's hosted converter in its most accurate mode, on every page** | The best tables and charts available, validated on this corpus by the 2026 project, and cheap at this scale: about $81 for all 10,843 pages | Datalab's price or terms change, or an open-source converter matches it on the sample test ([§4, Phase 0](#phase-0--foundations)) |
| How deep are the tables? | **Breadth first.** Every table and chart, machine-read, with automatic checks. **Errors are flagged, not fixed** | Coverage is what makes a lake useful; hand-checking 10,843 pages is not possible in spare time | Particular tables prove important enough to verify by hand. They then become *curated* products ([§3.7](#37-curated-layer)) |
| Where is it published? | **To be decided; most likely Harvard Dataverse** | A research repository with a DOI (a permanent citation link) for every version and long-term preservation | AI audiences need a Hugging Face mirror; this can be added without moving the primary copy |
| Are the original PDFs republished? | **No. Link to them and record each file's fingerprint** (a SHA-256 checksum) | Keeps the release to a few hundred megabytes at most, rather than 4.5 GB of PDFs. The checksum proves exactly which file was converted | The city's links break. Mitigated by archiving them to the Wayback Machine ([§3.9](#39-operations)) |
| License | **CC0**, a public-domain dedication, for the derived text and tables. The code stays MIT | The easiest terms to reuse, and Dataverse's default. The underlying facts are public records in any case | Never, in practice: CC0 cannot be walked back once data is out |
| AI access | **Decide later.** Design the corpus so that any of the three shapes in [§3.8](#38-access-and-the-ai-question) can be built on it | The right shape depends on who ends up using it | A concrete use case appears |
| Who does the work? | **One person in spare time, with Claude doing most of the building.** Phases are sized to a few weekends each | That is the real capacity | A grant, a course or research assistants join |

Assumed, and not separately decided: the archive is updated **once a year**, when each new budget is adopted. **The code starts in this repository** as a new project folder. **The existing `budget-history` dataset** is left untouched now and later rebuilt as one curated product on top of the lake.

## 2. Starting point

### The corpus

| | Volumes | Pages |
|---|---:|---:|
| All budget books, 2005–2026 | 34 | 10,843 |
| with a text layer (born-digital) | 28 | 9,192 |
| scans with no text layer at all | 6 | 1,651 |
| capital-program Volume 2s, included in the above | 12 | 3,356 |

The full list, with a proposed ID for each book, is in [Appendix A](#appendix-a--corpus-inventory). Four points about the corpus shape the design:

- **Five files exceed Datalab's 200 MB upload ceiling**: the 2021, 2022, 2024 and 2025 books and 2017 Volume 2. The largest is 247 MB. Pages have to be sent in slices, as the batching in `budget-books-ocr.py` already does.
- **Years and files do not line up one to one.** 2006 is only in the 2006–2007 biennial book. 2010 has a Volume 1 but no Volume 2 in the archive. 2019's book is the operating budget only. A year is not a file.
- **Scans are the hard part.** 2005 Volume 2, 2007 Volumes 1 and 2, 2009 Volumes 1 and 2, and 2010 Volume 1 have no text at all. Every word of them depends on OCR (optical character recognition).
- **Pages have two numbers.** Each page has its position in the PDF and the folio printed on the page. They differ, and citations need both.

### What the 2026 project already built

The budget-history work in [`2026-11-budget-tool/budget-history/`](../2026-11-budget-tool/budget-history/README.md) built most of the machinery a lake needs, at small scale:

| Piece | What it does now | What the lake reuses |
|---|---|---|
| `budget-books-inventory.py` | Lists the PDFs, tells scans from born-digital files, dumps page text | The corpus manifest, once checksums and URLs are added |
| `budget-books-ocr.py` | Sends pages to Datalab in batches of up to 100 and splits the answer back into pages. Keeps a ledger so nothing is paid for twice, and logs every request's cost | The whole conversion stage, extended to keep Datalab's JSON output as well as markdown |
| `budget-books-extract.py` | Pattern-based readers for five kinds of page: prose, summary blocks, multi-year tables, pies, and OCR tables | Test cases and hard-won rules, not the architecture. The lake reads tables generically instead ([§3.6](#36-table-and-chart-layer)) |
| `budget-history.py` | A reconciled, hand-checked series: 90 measures over 2002–2027 | The first curated product, and a source of known-good values to test the lake against |

### Ground truth for testing

Two assets let the lake measure its own accuracy instead of assuming it:

- **169 figures confirmed by two independent readings.** The same printed number was read from the PDF's text layer and again by OCR, with no disagreements. Any table extractor can be scored on whether it finds these values in the right cell.
- **Arithmetic the books print about themselves.** Summary blocks where operating plus capital equals the total, pies whose slices sum to a printed total, and multi-year tables that restate earlier years. These are free, automatic checks at archive scale.

The 2026 project's four OCR tiers cover about 1,700 pages. Most of them are the 1,137 pages of the three scanned Volume 1s in tier 1, which ran in September 2026 and gave 2007 and 2009 their first citywide totals. Only markdown is kept from those conversions, not the JSON the lake needs, so [§3.4](#34-conversion) recommends converting everything again in one consistent pass.

## 3. Architecture

### 3.1 Principles

1. **Every value leads back to a page.** Each number carries its book, its PDF page, its printed folio, its position on the page where available, and the conversion run that produced it.
2. **Keep what was paid for.** Datalab's responses are stored exactly as returned and never edited. Everything downstream can be rebuilt from them without converting, or paying, again.
3. **Machine-read is not verified, and the data says which is which.** Every table carries its checks and flags. Hand-verified products live in a separate, clearly named layer.
4. **Identifiers are stable.** An ID, once published, always means the same book, page or table.
5. **Build once, publish many ways.** One lake feeds the Dataverse release, local analysis, teaching sets and any future AI access.
6. **Cheap to run, easy to redo.** No servers and no databases to keep alive. Files in open formats, one command per layer, and DuckDB to query them. DuckDB is a free database that runs inside a notebook and reads files directly.

### 3.2 Layers

Data moves through layers, and each layer is built only from the one before it. This is the pattern data engineers call a medallion architecture (bronze, silver, gold). The layer names here say what each one holds:

```
 L0  sources     the 34 PDFs, on the city's server                 manifest only: URL, checksum, pages
      │
 L1  raw         Datalab's responses, exactly as returned           markdown + JSON per batch, request log
      │                                                             (kept forever; never edited)
 L2  pages       one record per page                                text, source, quality, flags
      │
 L3  documents   one markdown file per book, with page markers      + a section map from the PDF outline
      │
 L4  tables      every table and chart                              registry + cells + one CSV/JSON each
      │
 L5  checks      what the arithmetic says about each table          results + flags + confidence grade
      │
 L6  curated     hand-verified series                               budget-history today; more later
      │
 L7  access      the Dataverse release, DuckDB views, notebooks,    built from L2–L6
                 teaching sets, the AI corpus
```

L1 is the only layer that costs money to create. L2–L7 are rebuilt from it with no fees.

### 3.3 Identifiers

| Thing | Form | Example |
|---|---|---|
| Book | `bb-<fiscal year or years>[-v<volume>]` | `bb-2014-v1`, `bb-2006-2007-v2`, `bb-2011` |
| Page | `<book>:p<PDF page, 4 digits>` | `bb-2014-v1:p0101` |
| Printed folio | Stored alongside the page, not part of its ID | `101` might print as "5-12" |
| Table | `<page>:t<order on page, 2 digits>` | `bb-2014-v1:p0101:t02` |
| Chart | `<page>:c<order on page, 2 digits>` | `bb-2012-v1:p0039:c01` |
| Conversion run | Datalab's `request_id`, with the date and a hash of the settings | stored in the request log |

A book whose file changes gets a new version of its manifest row, identified by the new checksum, and keeps its ID. A page whose conversion is redone keeps its ID and gets a new run reference. IDs are never reused for anything else.

### 3.4 Conversion

**Settings.** Accurate mode with `paginate=true`, as validated in 2026, plus:

| Setting | Why | Check in the Phase 0 pilot |
|---|---|---|
| `output_format=markdown,json` | Markdown for reading. JSON for the lake: a tree of layout blocks (tables, figures, headings, text) with their positions on the page, which is what table extraction reads | That both formats in one request are billed once |
| `extras=extract_bookmarks` | The PDF's own outline, where one exists, becomes each book's section map at no extra conversion | Its cost, and how many books have an outline |
| `extras=chart_understanding` | Datalab's chart add-on, **$3 per 1,000 pages at list price** | Whether it beats plain accurate mode on the pie pages whose true values are known, and whether it is billed on every page or only on pages with charts |

The chart add-on is decided at the end of Phase 0. If it is adopted, it goes into the Phase 1 pass, so every page still comes from one set of settings.

**Transport.** The batching in `budget-books-ocr.py` carries over unchanged: slices of up to 100 pages, never more than 190 MB, and a ledger of submitted batches so none is paid for twice. Datalab reports failed pages, and those are recorded; a failed batch is never re-sent automatically. A spend cap on the API key is the backstop. Its docstring explains each of these.

**One pass, not a patchwork.** The 2026 tiers cover about 1,700 pages, but in markdown only and in several separate runs. Datalab's models change, so the same page converted twice can differ. Converting all 10,843 pages in one run, with one set of settings, costs about **$81** at this account's rate. Reusing the old pages would cost about $69. The $12 difference buys a corpus from a single model version, with JSON for every page. Recommended.

**What the price includes.** This account takes Datalab's 25% discount for letting it keep uploads to train its models: $7.50 per 1,000 pages instead of $10. That is no concern for public budget books. It should be reconsidered before any non-public document goes through the same account.

**Stored as raw.** Each batch's full response is kept as returned, compressed, under `raw/<book>/<request_id>.json.gz`, along with the request log line: pages, cents, time, and Datalab's parse-quality score (0–5). Datalab deletes results about a day after they complete, so the raw layer is the only copy.

### 3.5 Text layer

**Pages (L2).** One record per page:
- the page's markdown;
- a plain-text version with markup removed, for search;
- which conversion produced it;
- the printed folio, when one can be found;
- counts of characters, tables and figures;
- Datalab's quality score;
- flags, such as `blank`, `failed`, `scan_only` or `numbers_disagree_with_text_layer`.

**Documents (L3).** One markdown file per book: the pages in order, each opened by a marker such as `<!-- bb-2014-v1:p0101 · folio 5-12 -->`, so a quotation can always be traced back to its page. Headings come from the PDF outline where the book has one, and otherwise from the headings the converter detects. A **section map** lists each book's sections with their page ranges. Department chapters make many analyses possible straight away: every page about Police across twenty years is one filter.

**A free second witness.** For the 9,192 born-digital pages, the PDF's own text layer can be read with no fees. Wherever the numbers on a page differ between the text layer and the conversion, the page is flagged. This is the check that confirmed 169 figures in 2026, and at archive scale it costs nothing. Pages with no usable text layer get no second witness: the scans, and charts drawn as images. There, only the arithmetic and cross-book checks in [§3.6](#36-table-and-chart-layer) can catch a misread. That is how the 2026 project caught OCR reading 2006 in the 2011 book's FTE history as 1,218.34, where two other books print 1,218.84.

### 3.6 Table and chart layer

This is the breadth decision in practice. Every table and chart becomes data. Nothing is hand-checked. Every problem is visible.

**Where tables come from.** The JSON output marks each table as a block with its rows and cells. Reading those blocks generically replaces the 2026 approach of writing a pattern for each kind of page, which does not scale to 10,843 pages.

**Four files:**

| File | One row per | Holds |
|---|---|---|
| `tables` (the registry) | Table | ID, book, page and position. The title (the nearest heading or caption). Units, detected from phrases such as "in $1,000s". Header rows, and the years and basis words found in the headers (ACTUAL, APPROVED, PROJECTED). Row and column counts, the share of numeric cells, and links to continuations on the next page. Its check summary and confidence grade |
| `cells` | Table cell | Table ID, row and column, the row and column header labels, the text exactly as read, the parsed number, the unit, the year and basis taken from the header, and any footnote marks. One long table covering the whole archive, so any question is a query rather than 20,000 file opens |
| `charts` | Chart | ID, book, page, type (pie, bar, line), title, the printed total if any, whether values are printed on the chart, and its checks |
| `chart_series` | Data point in a chart | Chart ID, label, value, percentage, and whether the value was printed or estimated from the drawing |

Each table is also written as its own small CSV, and each chart as its own JSON file, for people who want one table rather than a database.

**Checks, never fixes (L5).** Each check runs where it applies and records a result:

| Check | Catches |
|---|---|
| Rows sum to a TOTAL row; columns sum to a total column; subtotals sum to totals | Misread digits, dropped rows, merged cells |
| Percentage columns sum to about 100 | Misaligned columns |
| Pie slices sum to the printed total | Missing or duplicated slices |
| **Fabrication test**: slice value ≈ printed % × total | The converter inventing dollar values from percentages, seen in the 2019 book in 2026 |
| Chart values printed, or estimated from bar heights | Values read off a drawing, as with the 2019 property-tax chart |
| Text layer and conversion agree on a page's numbers | Single-digit misreads on born-digital pages |
| The same year and line agree across books' multi-year tables | Errors in either book, or genuine restatements, to be told apart later |
| Year headers increase; units found; header rows identified | Structure the parser got wrong |

**Confidence grades**, so a user can filter to a standard:

| Grade | Meaning |
|---|---|
| **A** | At least one sum check applied, and every applicable check passed |
| **B** | No sum check applied, and nothing failed |
| **C** | Something failed. The data is kept and the flags say what failed |

**Measured, not assumed.** Before release, the table layer is scored against the 169 figures confirmed in 2026 and the values in `budget-history.csv`. How many does it contain, in the right cell and year, and how many of those carry grade A? These rates are published with the release, since breadth without a measured error rate would be a liability.

### 3.7 Curated layer

Hand-verified series built from the lake's tables, each reconciled the way `budget-history` is now:

- **`budget-history`**, the existing dataset. It is rebuilt from the lake where its figures are in L4, and keeps its hand-transcribed values where they are not.
- **Table families.** The same table printed in every year's book, such as "Summary of Uses of Funds" or "Staffing Levels in Standard FTEs by Department". These are found by clustering tables on their normalized titles and headers, then joined across years into one longitudinal panel.
- Candidates, in order of value: department spending by fund and year, staffing by department, fund balances, and the capital program by project from the Volume 2s.

Curated products are small, carry their own data dictionaries and validation reports, and never overwrite L4.

### 3.8 Access, and the AI question

**For analysis (columns and classes).** The release is Parquet files, a compact column-based format that pandas, R and DuckDB read directly, plus CSV copies. A notebook of starter queries covers:
- every page mentioning a phrase;
- every table with a given title across years;
- all grade-A cells for a department;
- a book's section map.

**For classes.** A teaching kit: a few curated tables with their stories. The Public Works split, the three pies that share one heading, and the two General Fund measures are real lessons in reading budgets. Exercises would use the lake's own flags as examples of why checking matters.

**For AI, decided later.** Three shapes are possible. The corpus is built so that any of them can be added without rework:

| Shape | What it is | Good for | Costs | Needs from the corpus |
|---|---|---|---|---|
| Published corpus | The text cut into chunks of a few paragraphs, each with its page range and section, plus optional search vectors (embeddings) | Anyone plugging it into their own tools | Nothing to run | Chunk IDs, page spans, section paths |
| AI connector | A small MCP server, the connector standard Claude and similar assistants use. It exposes search, fetch-page and query-tables tools over the lake, and cites book and page | Asking questions from inside an assistant | A little code; runs on a laptop or a small host | The above, plus DuckDB full-text search |
| Web page | A public "ask the budget" page | Readers who would never open a notebook | Hosting, upkeep, model fees, and answering for what it says | All of the above, plus guardrails on answers |

Whichever shape is chosen, one rule holds: **every answer quotes the page it came from**, using the L2 and L3 identifiers. The page citation is what separates this from asking a model what it remembers about Boulder.

### 3.9 Operations

**Where things live:**

| Where | What |
|---|---|
| This repository, in a new `budget-archive/` project folder | Code, schemas, documentation, tests, and small sample fixtures |
| A local lake folder outside git | L1–L6 while working |
| Harvard Dataverse, most likely | Versioned public releases |
| The city's archive | The PDFs themselves, referenced by URL and checksum |

**Packaging for Dataverse.** Its documented behavior shapes the file layout:
- **Zips unpack.** Dataverse unpacks a zip on upload, unless it holds more than 1,000 files, in which case it shows an error and keeps the zip as is. So per-table CSVs and per-book markdown ship as a zip inside a zip, the Dataverse community's standard workaround: Dataverse unpacks only the outer layer, and its Zip Previewer still lets people open single files in the inner one. Uploads that go straight to storage (S3 direct upload) are not unpacked at all, so which path Harvard uses is checked in Phase 2.
- **CSVs get converted.** Uploaded CSVs are "ingested" into Dataverse's archival tab-separated format, and ingest fails on ragged files. The long `cells` table is uniform and ingests cleanly; per-table CSVs stay inside zips.
- **Parquet is stored as is.**
- **Metadata comes for free.** Dataverse generates DOIs, versions and Croissant metadata, the machine-readable dataset description that AI tools read. The release adds a Frictionless `datapackage.json` describing every file and column.
- **Check the per-file size limit** shown in Harvard's upload widget before packaging, and the size limit on CSV ingest. The largest file is likely to be the `cells` table as CSV, perhaps one or two hundred megabytes. Its Parquet copy will be a small fraction of that.

**Versions.** Numbered MAJOR.MINOR.PATCH:
- MAJOR: a schema change that breaks queries;
- MINOR: new books, tables or layers;
- PATCH: corrections.

Each maps to a Dataverse version, with a CHANGELOG entry.

**Corrections.** Reported as GitHub issues with a "data correction" template. A correction never edits L1. It is added to a `corrections.csv`, with who, why and the evidence, which L4–L6 apply on rebuild. The original reading and the correction both stay visible.

**Link rot.** At each release, every source URL is submitted to the Internet Archive's Wayback Machine, and the snapshot link is recorded in the manifest. If the city's archive moves, the fingerprinted files can still be found, without this project republishing them. Whether Laserfiche download links archive cleanly is tested in Phase 0.

**The annual update.** Each winter, once the city posts the newly adopted budget book:
1. Add it to the manifest with its checksum.
2. Run `--estimate`, then convert it (about $2–4).
3. Rebuild L2–L6.
4. Review the new flags.
5. Publish a MINOR version.

A few hours, once a year.

## 4. Roadmap

Phases are sized for spare time, where one weekend is about one working session. Each phase ends in something usable, and the release comes as early as it honestly can.

| Phase | Delivers | Weekends | Fees |
|---|---|---:|---:|
| [0. Foundations](#phase-0--foundations) | Manifest, IDs, settings proven on a 100-page pilot | 1 | ~$1 |
| [1. Convert everything](#phase-1--convert-everything) | L1 and L2 for all 10,843 pages | 1–2 | ~$81, or up to ~$114 with the chart add-on |
| [2. Text release, v1.0](#phase-2--text-release-v10) | **First public release**: full text, page records, section maps, DOI | 1–2 | $0 |
| [3. Tables and charts, v1.1](#phase-3--tables-and-charts-v11) | Every table and chart, checked, graded and measured | 2–3 | $0 |
| [4. For columns](#phase-4--for-columns) | Table families across years, starter notebook, `budget-history` rebuilt on the lake | 2 | $0 |
| [5. For classes](#phase-5--for-classes) | Teaching kit | 1–2 | $0 |
| [6. AI access](#phase-6--ai-access) | Whichever shape is chosen | 1–3 | depends on the shape |
| Every year | The new book added; MINOR release | a few hours | ~$3 |

The first public release comes after roughly **3–5 weekends**, and everything after roughly **9–15**.

### Phase 0 — Foundations

**Goal:** everything that is expensive to change later is decided and tested on a small scale.

- Create `budget-archive/` with its README, the schemas for L2–L5, and tests.
- Build the **manifest** (L0). For each of the 34 books, record:
  - its ID;
  - fiscal years and volume;
  - the Laserfiche URL;
  - the SHA-256 checksum;
  - bytes and pages;
  - born-digital or scanned;
  - the retrieval date;
  - a Wayback snapshot link.

  `budget-books-inventory.py` supplies most of this. The checksums and URLs are new.
- Set a **spend cap** on the Datalab key a little above the Phase 1 estimate.
- **Pilot 100 pages**, chosen to cover each kind of page: scans, pies, multi-year tables, summary blocks, prose, blank dividers and the capital-program tables. Confirm, in order:
  - the billing of `markdown,json` together;
  - what `extract_bookmarks` returns;
  - the JSON table structure;
  - how the chart add-on scores against the pie pages with known values, and how it is billed;
  - that batched and single-page conversions yield the same figures. The 8-cent check in the budget-history README is the pattern.
- Optional, and cheap: run one open-source converter on the same 100 pages, scored against the same known values. Record the result, so a later switch is an informed one.

**Done when:** the manifest is complete; the pilot's costs match the estimate; and a written note records the chosen settings, including whether to use the chart add-on, and the pilot's scores.

### Phase 1 — Convert everything

**Goal:** every page exists as data, and nothing is ever paid for again.

- Run the conversion over all 34 books with the Phase 0 settings: `--estimate` first, then the run.
- Store the raw responses (L1) and build the page records (L2), including the text-layer comparison for born-digital pages.
- Resolve every failed page: retry it once as a single page, and if it still fails, record it in a failed-pages list with Datalab's error.

**Done when:** 10,843 page records exist. Every page is either converted or listed as failed, with a reason. The request log totals match Datalab's invoice. The ledger of pending batches is empty.

### Phase 2 — Text release, v1.0

**Goal:** the first citable, public release. Text is the most broadly useful and least error-prone layer, so it goes first.

- Build the per-book markdown (L3) and the section maps.
- Write the release documentation:
  - a README;
  - a DATA-DICTIONARY for every column of every file;
  - METHODS: conversion settings, known model behaviors, the checks;
  - KNOWN-ISSUES: the failed pages, the scans, the 2019 and 2010 gaps;
  - CITATION.cff;
  - a CHANGELOG.
- Package for Dataverse ([§3.9](#39-operations)): Parquet plus CSV copies of the page records, zipped per-book markdown, the manifest, `datapackage.json`, and CC0.
- Archive the source URLs to the Wayback Machine.
- Publish, and record the DOI in this repository.

**Done when:** a stranger can find, cite, download and query the text of any page of any book from the Dataverse page alone.

### Phase 3 — Tables and charts, v1.1

**Goal:** breadth. Every table and chart as data, with its problems in plain sight.

- Extract tables and charts from the JSON (L4). Run every check and assign grades (L5).
- **Score the layer** against the 169 twice-confirmed figures and `budget-history.csv`: recall, grade distribution, and the most common failure types. Publish the scores with the data.
- If the chart add-on was left out in Phase 0 and the chart checks now show it is needed, re-convert only the pages the JSON marks as holding charts. That is perhaps 1,000–2,000 pages, roughly $10–20 for accurate mode again plus the add-on. It gives those pages a second run, so each chart records which run it came from.
- Release v1.1 with the table registry, cells, charts, chart series, checks and zipped per-table files.

**Done when:** every table block in the JSON is in the registry or listed as unreadable, and the published scores say how far to trust each grade.

### Phase 4 — For columns

**Goal:** the lake answers column questions faster than the PDFs do.

- Cluster tables into families across years ([§3.7](#37-curated-layer)), and build the first longitudinal panels.
- Rebuild `budget-history` on the lake. Where the lake and the hand-transcribed values disagree, that is a finding about one of them, and it gets investigated.
- A starter notebook of DuckDB queries, including queries that read the release straight from Dataverse without downloading it.

**Done when:** a new column's data question takes a query, not a PDF hunt, for anything the books print.

### Phase 5 — For classes

**Goal:** a teaching kit that uses the archive's real problems as lessons.

- Three to five curated tables with short stories: why Public Works' spending cannot be divided among the departments that replaced it, why three pies share one heading, why there are two General Fund measures.
- Exercises that use the lake's flags: find the fabricated chart, explain a restatement.
- Notebooks that run from the public release with no setup beyond Python.

**Done when:** a student can complete an exercise from the Dataverse release alone.

### Phase 6 — AI access

**Goal:** chosen when a use case exists ([§3.8](#38-access-and-the-ai-question)).

- Build the chunked corpus, the prerequisite for all three shapes.
- Then the chosen shape: a published corpus, an MCP connector, or a web page.
- Test it against questions with known answers from the curated layer, and check that every answer cites a page.

**Done when:** it answers a set of known questions correctly and every answer cites a page.

## 5. Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| Machine-read tables contain errors that users take as fact | Certain, to some degree | Wrong numbers in someone's analysis | Grades, flags and published error rates. Curated products kept separate and labeled. The data dictionary says plainly what "machine-read" means |
| Datalab's models change between runs | Likely over years | New pages differ in style from old ones | One conversion pass for the corpus. Raw responses kept. Model date recorded per run. Annual additions noted in the CHANGELOG |
| Datalab's price, terms or availability change | Possible | The next conversion costs more, or cannot be done | Raw layer kept forever. Open-source converter scored in Phase 0 as a known fallback |
| The city's links break | Likely over years | Sources hard to find | Wayback snapshots and checksums in the manifest |
| Costs overrun | Low | Budget surprise | `--estimate`, the key's spend cap, the ledger, the request log |
| Scope creep: audited reports, council packets, other cities | Likely | The lake never ships | This document's scope; the release first; additions as later MAJOR versions |
| Spare time runs out mid-phase | Likely at some point | Half-built layers | Phases end in usable releases. The text release does not wait for tables |
| A reader mistakes the lake for an official record | Possible | Misattribution | README and Dataverse description state it is an independent conversion of public records, not a city product |

## 6. Open questions

- **The host.** Harvard Dataverse is the lead candidate. Confirm its current per-file limit, and whether a Hugging Face mirror is worth adding for AI audiences.
- **The chart add-on.** Decided on Phase 0 evidence, before the Phase 1 run.
- **The AI shape.** Decided when a use case appears.
- **Raw responses in the release.** Publishing L1 makes the conversion fully reproducible without paying Datalab again. It is larger, perhaps a few hundred megabytes, and CC0 makes it legally simple. It leans yes; decide in Phase 2.
- **Later sources.** The audited annual financial reports record what was actually spent, not budgeted, and are the obvious next corpus. Out of scope for this plan by decision, and the first candidate for a MAJOR version 2.

## 7. Appendices

### Appendix A — Corpus inventory

Pages and sizes from `budget-books-inventory.py`, run in September 2026. The IDs are proposed.

| ID | File | Pages | MB | Kind |
|---|---|---:|---:|---|
| `bb-2005-v1` | 2005 Annual Budget, Volume 1.pdf | 314 | 2.3 | born-digital |
| `bb-2005-v2` | 2005 Annual Budget, Volume 2.pdf | 151 | 12.7 | scanned |
| `bb-2006-2007-v1` | 2006-2007 Annual Budget, Volume 1.pdf | 321 | 1.8 | born-digital |
| `bb-2006-2007-v2` | 2006-2007 Annual Budget, Volume 2.pdf | 149 | 161.0 | born-digital |
| `bb-2007-v1` | 2007 Annual Budget, Volume 1.pdf | 377 | 18.7 | scanned |
| `bb-2007-v2` | 2007 Annual Budget, Volume 2.pdf | 152 | 19.2 | scanned |
| `bb-2008-v1` | 2008 Annual Budget, Volume 1.pdf | 357 | 21.3 | born-digital |
| `bb-2008-v2` | 2008 Annual Budget, Volume 2.pdf | 207 | 36.7 | born-digital |
| `bb-2009-v1` | 2009 Annual Budget, Volume 1.pdf | 411 | 53.2 | scanned |
| `bb-2009-v2` | 2009 Annual Budget, Volume 2.pdf | 211 | 13.8 | scanned |
| `bb-2010-v1` | 2010 Annual Budget, Volume 1.pdf | 349 | 189.2 | scanned |
| `bb-2011` | 2011 Annual Budget.pdf | 282 | 92.0 | born-digital |
| `bb-2012-v1` | 2012 Annual Budget, Volume 1.pdf | 330 | 89.6 | born-digital |
| `bb-2012-v2` | 2012 Annual Budget, Volume 2.pdf | 280 | 94.4 | born-digital |
| `bb-2013-v1` | 2013 Annual Budget, Volume 1.pdf | 333 | 99.4 | born-digital |
| `bb-2013-v2` | 2013 Annual Budget, Volume 2.pdf | 502 | 149.1 | born-digital |
| `bb-2014-v1` | 2014 Annual Budget, Volume 1.pdf | 321 | 168.2 | born-digital |
| `bb-2014-v2` | 2014 Annual Budget, Volume 2.pdf | 323 | 168.0 | born-digital |
| `bb-2015-v1` | 2015 Annual Budget, Volume 1.pdf | 339 | 180.5 | born-digital |
| `bb-2015-v2` | 2015 Annual Budget, Volume 2.pdf | 371 | 198.1 | born-digital |
| `bb-2016-v1` | 2016 Annual Budget, Volume 1.pdf | 349 | 187.8 | born-digital |
| `bb-2016-v2` | 2016 Annual Budget, Volume 2.pdf | 366 | 189.2 | born-digital |
| `bb-2017-v1` | 2017 Annual Budget, Volume 1.pdf | 358 | 198.0 | born-digital |
| `bb-2017-v2` | 2017 Annual Budget, Volume 2.pdf | 375 | 203.4 | born-digital |
| `bb-2018-v1` | 2018 Annual Budget - Volume 1.pdf | 268 | 163.4 | born-digital |
| `bb-2018-v2` | 2018 Annual Budget - Volume 2.pdf | 269 | 166.8 | born-digital |
| `bb-2019` | 2019 Approved Operating Budget.pdf | 257 | 140.9 | born-digital |
| `bb-2020` | 2020 Approved Budget.pdf | 307 | 185.1 | born-digital |
| `bb-2021` | 2021 Approved Budget.pdf | 333 | 208.5 | born-digital |
| `bb-2022` | 2022 Approved Budget.pdf | 339 | 222.8 | born-digital |
| `bb-2023` | 2023 Annual Budget.pdf | 346 | 181.1 | born-digital |
| `bb-2024` | 2024 Approved Budget.pdf | 469 | 246.6 | born-digital |
| `bb-2025` | 2025 Approved Budget.pdf | 421 | 223.4 | born-digital |
| `bb-2026` | 2026 Annual Budget.pdf | 306 | 192.7 | born-digital |

### Appendix B — Lessons from the 2026 project

The budget-history work met each of these on real pages. The lake's design answers each one, in the section given:

| Lesson | Where it bit | Answer in the lake |
|---|---|---|
| OCR invents dollar values from printed percentages | 2019 pie: Police at $35,370 against a printed 10%, or 9.999% of the total | Fabrication test ([§3.6](#36-table-and-chart-layer)) |
| Bar heights come back as numbers | 2019 property-tax chart | "Printed or estimated" flag on every chart value |
| A single digit can be misread | The 2011 book's FTE history: 1,218.84 read as 1,218.34 | Text-layer comparison and cross-book agreement |
| Three pies share one heading: citywide, excluding utilities, General Fund | "Uses of Funds" pies. In 2005, Parks is $21.1M citywide and $3.9M in the General Fund | Charts keep their printed total. Scope is a curated-layer judgment, never an L4 guess |
| The year is in the page, not the filename | The 2006–2007 biennial book | Years taken from headers and text, never filenames |
| A column's basis is in its header | ACTUAL / APPROVED / PROJECTED | Basis parsed into every cell |
| Units vary | $1,000s in the books; millions in packets; FTE | Units detected per table; unknown units flagged |
| PDF page and printed folio differ | Throughout | Both recorded ([§3.3](#33-identifiers)) |
| pypdf garbles spacing and order | "Fir e", "Parks & Re cr e ation" | Conversion for layout; the text layer used only as a second witness |
| A batch can drop text that repeats across its pages | Engine behavior; not seen when nine 2011 pages were checked in 2026 | The Phase 0 batch-versus-single check |
| One page per request is slow | The 2026 tier 1 run | Batches of up to 100 |
| A failed conversion can pass as a blank page | Caught in 2026 | Datalab's failure flags honored; failures listed, never cached as blank |
| Excel garbles UTF-8 punctuation | CSV titles with dashes | ASCII-safe CSV text; the encoding documented |

### Appendix C — Cost worksheet

At this account's rate of $7.50 per 1,000 pages: accurate mode, list price $10, less the 25% training discount.

| Item | Pages | Fees |
|---|---:|---:|
| Phase 0 pilot, including pages sent twice for the batch check | 100 and some repeats | ~$1 |
| Full conversion, one consistent pass | 10,843 | ~$81 |
| (alternative: reuse the ~1,700 pages of the 2026 tiers) | ~9,100 | ~$69 |
| Chart add-on in the Phase 1 pass, if adopted (list $3 per 1,000; billing confirmed in Phase 0) | up to 10,843 | up to ~$33 |
| (alternative: add it later, re-converting only the chart pages) | perhaps 1,000–2,000 | ~$10–20 |
| Each new book, yearly | 300–470 | ~$2–4 |
| Hosting on Dataverse | | $0 |
| Compute | a laptop | $0 |

At list price, without the discount, multiply the accurate-mode figures by 4/3. The chart add-on is already at list price.

### Appendix D — Glossary

| Term | Meaning here |
|---|---|
| **Data lake** | A store of raw and lightly processed data in open file formats, kept close to the source and organized for many future uses rather than one |
| **Medallion architecture** | Layers from raw to refined, often called bronze, silver and gold. Here L1–L7 |
| **OCR** | Optical character recognition: turning an image of text into text |
| **Born-digital / scanned** | A PDF made by software, with a text layer, versus a photograph of paper with none |
| **Datalab** | The hosted document converter used here, built on the open-source Marker project |
| **Markdown** | Plain text with light formatting marks, readable as-is and by software |
| **JSON** | A structured text format for nested data, here the converter's tree of page blocks |
| **CSV / Parquet** | A plain-text table; a compact column-based table format for analysis tools |
| **DuckDB** | A free, in-process database that queries CSV and Parquet files directly |
| **SHA-256 checksum** | A fingerprint of a file; any change to the file changes it |
| **DOI** | Digital Object Identifier: a permanent link for citing a dataset version |
| **CC0** | A public-domain dedication: no conditions on reuse |
| **Croissant / Frictionless Data Package** | Machine-readable descriptions of a dataset's files and columns |
| **MCP** | Model Context Protocol: the connector standard that lets AI assistants use outside tools and data |
| **Embeddings** | Numeric fingerprints of text meaning, used for search by similarity |
| **Folio** | The page number printed on the page, as opposed to its position in the PDF |
