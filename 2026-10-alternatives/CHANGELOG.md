# Changelog

Notable changes to this folder. Data vintages are recorded here as they are added, so a figure in the column can be tied to the release it came from.

## Unreleased — 2026-09-17

Folder created. The archive itself does not exist yet; this is the proposal and the evidence behind it.

### Added

- `TASK.md` — the proposed audit, retrieval and cleaning task, with acceptance tests and named risks.
- `DATA-DICTIONARY.md` — the target schema, marked *planned* throughout.
- `decision-log.md` — ten decisions, D1 to D10.
- `ROADMAP.md` — deferred work and the task checklist.
- `proof-run.py` — probe covering 2001, 2013 and 2024 against both CDE and NCES CCD, harmonized and reconciled.
- `datalab-ocr.py` — re-OCR of the scanned 1986–1999 yearbooks through the Datalab convert API.
- `audit/proof-run.md` and `audit/proof-run.json` — sixteen findings, each from a file actually fetched and parsed.

### Data vintages retrieved

- CDE Artemis ED5/90.17: Fall 2001 and Fall 2013 school-by-grade; 2024-25 school-by-grade from the pupil-membership archives.
- CDE staff statistics: 2024-25 pupil–teacher ratio by school.
- CDE Artemis ED2/79.19: the 1986 yearbook, re-OCR'd.
- NCES CCD via the Urban Institute API: Colorado directory and enrollment for 2001, 2013 and 2023.

### Known at time of writing

- The 1986–1999 yearbooks carry no school-level table, so the school panel cannot start before 2000.
- The 1986 volume's Table 4 extends the district panel back to 1977-78.
- CDE and CCD agree to 0.03% statewide in 2013 once pre-kindergarten is excluded.
- CCD publishes no pre-kindergarten for Colorado, and stops at 2023.

## 2026-09-17 — the archive

The pipeline runs end to end and `data/processed/` exists.

### Added

- `pipeline/` — discovery, fetch, schema, parsers, normalization and validation as six modules.
- `audit/check-row-totals.py` — the yearbook checksum, as a reusable check.
- `data/processed/` — six tables. School panel 1986–2024 (647,881 rows); district panel; district trends reaching 1977-78; school registry with auto-labelled closures; a per-year reconciliation of CDE against NCES.
- `data/lookups/` — the 1,511-file inventory, coverage map and district crosswalk.

### Fixed during the build

- A column header read as `1.0` normalized to **grade 10**, putting first-graders nine years out.
- Nine of twenty-four years were silently unparsed because CDE abbreviates headers to `Sch Code` and `Distr Code`.
- A STATE TOTALS row in the 2010 file was read as a school and doubled the state; checksums passed throughout.
- Yearbook page selection under-covered long tables, losing about half the districts in 1986.
- Re-detecting the yearbook header per row let a small rural district's grade counts pose as a header and reset the column map.
- `datalab-ocr.py` rebuilt its index from a single run, under-reporting a resumed volume.

### Known

- 2001–2003 are CCD-only on the school side; no CDE parser reads those layouts.
- From 2021 CDE and NCES diverge by 6,000–16,000 pupils, concentrated in multi-district online and charter schools. Before 2021 they agree to within a few hundred.

## 2026-09-17 — teaching staff

Teacher FTE joins enrollment, at both grains. The archive now answers "how many teachers" on the same panel that answers "how many pupils".

### Added

- `pipeline/teacher_fte.py` — retrieval and parsing of every CDE staff report in both serials, plus the NCES district-level staffing pull.
- `data/processed/school-teacher-fte.csv` — **19,880 rows, eleven years**: 2003, 2004, 2013–2016, 2018, 2019, 2022–2024. The CDE school-grain series was three years before this.
- `data/processed/district-teacher-fte-ccd.csv` — **7,879 rows, 1987–2024**, with a prek/kindergarten/elementary/secondary split CDE never publishes. The longest staffing series in the archive.
- `data/processed/district-teacher-fte-cde.csv` — 17 rows, 2016–2024, as a cross-check against NCES rather than a series.
- `data/raw/fte/` — 36 published originals with `manifest.json` (sha256, URL, retrieval date).
- `audit/teacher-fte-parse.json` and `audit/teacher-fte.log` — rows kept, rows dropped and why, per file.

### Fixed during the build

- **Wrapped rows put enrollment in the FTE column.** Douglas County High School read as 1,893 teachers, and the 2016–2018 totals ran 31% high. Caught with the file's own arithmetic — see D14.
- A **2-digit county code** was counted as a district code, which turned district rows into school rows: 2013 produced 185 "schools".
- A **`STATE OVERALL`** row carrying 53,458 FTE was read as a district.
- `shift_text` skipped every digit, because the guard tested the input character rather than the decoded one, and subset-font numerals sit below codepoint 32.
- Page grouping concatenated 52 copies of the header until the key included the page.
- Field splitting assumed whole runs; some files place each character separately. The split now measures the median run length per line.
- A `17:1` ratio format in the 2024 spreadsheet parsed as missing.

### Known

- **2005–2012 is not parsed.** Those ratio PDFs place every character as its own run with unreliable line positions, so fields merge and rows scramble. Eight years of school-grain FTE sit behind it; NCES covers them at both grains meanwhile.
- **2017 does not exist as a distinct year.** CDE's 2016 and 2017 files are byte-identical. See D15.
- Against NCES for the same year and state, the CDE school totals land within 0.3% to 4.5%.

## 2026-09-17 — the rest of the teacher series

The CDE school-grain series goes from eleven years to **twenty-two**, 2000–2024, and the district table from seventeen rows to **4,037**.

### Added

- `data/processed/school-teacher-fte.csv` — **38,777 rows, 2000–2024**, every year but 2017 (a byte-identical duplicate of 2016) and 2020–2021 (not published). Was 19,880 rows over eleven years.
- `data/processed/district-teacher-fte-cde.csv` — **4,037 rows, 2000–2024**, 181 to 186 districts a year, carrying CDE's own district total where it publishes one and the sum of the district's schools everywhere. Was 17 rows.
- `school-year.csv` now carries `teacher_fte_cde` in twenty-two years rather than eleven — 38,768 school-years.

### Fixed during the build

The 2005–2012 reports were described as needing OCR. They did not: the text was there, and three things in the extractor hid it.

- **The page is rotated.** From 2006 the reports set a text matrix of `0 s -s 0 x y`. Reading its translation as (x, y) groups the table by column instead of by row.
- **The line operator is `TD`, not `Td`.** Matching only `Td` froze the position wherever the last `Tm` put it, so a whole page landed on one line. This alone is why eight years extracted 78 to 1,348 rows of run-together text and parsed to nothing.
- **A page's content is several stream objects**, and the later ones begin inside a text object with no `BT` and no `Tm`. Resetting per stream put those runs in an identity matrix while the rest of the page was rotated. Counting every stream as a page instead merged pages, and because each page's table starts at the same coordinate that put a hundred unrelated rows on one line — which is how 2009 came out with Ortega Middle School twice, once with 29.7 teachers and once with 2.
- **Columns that run together** are now re-cut using the file's own arithmetic (D16). Every row of the 2002 report needed it.
- **`district-teacher-fte-cde.csv` was seventeen rows of schools and state totals.** A district code column headed `LEA` rather than `LEA Code` went unmatched, collapsing both by-district spreadsheets onto one key; and a school whose own code had merged into its name was left with one code, which is what marked a row as a district (D15, D17).
- **2006 prints no codes at all.** Its 1,727 rows are matched to a school by name against the nearest year that prints both; 1,724 resolved.

### Known

- Every one of the twenty-two CDE years is 0.7% to 4.4% below the NCES state total, sixteen within 2%, in the same direction throughout.
- 551 district-years carry both a published CDE total and a school sum; **396 agree to the hundredth of an FTE**, including all 185 districts in 2023.
- The membership serial's 2000–2002 and 2004 ratio PDFs still extract no text; 2003 and 2012 lose about 200 rows each. All are covered by the staff serial.
- CDE's average-salary reports are still unparsed. See `ROADMAP.md`.
