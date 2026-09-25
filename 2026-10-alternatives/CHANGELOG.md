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

## 2026-09-18 — district staffing back to 1986

`district-teacher-fte-cde.csv` goes from 4,037 rows over 2000–2024 to **6,695 over 1986–2024**. Colorado district staffing is now a thirty-nine-year series on the CDE side, and the archive has school counts by level for the first time.

### Added

- **The yearbooks' summary table**, 1986–1999. The roadmap called it Table 1; it is Table 1 in some volumes and Table 2 in others, under a heading that does not change. `pipeline/extract.py` gains `parse_yearbook_district_summary`.
- Classroom teacher FTE, certificated and non-certificated staff, schools by level, pupil/teacher ratio, graduation rate and dropout rate, by district, for fourteen volumes — 2,659 district-years.
- `unit_type` on the district staffing table, so BOCES can be filtered as they can elsewhere.

### How it is checked

- Against NCES, **every year from 1987 to 1998 lands within 1.3%**, five within 0.2%. 1991 agrees to a fifth of one FTE out of 33,093. 1986 has nothing to check it against: NCES district staffing starts in 1987.
- Each row checks itself twice — the four school counts must add to the printed total, and students over classroom teachers must be the printed ratio.

### Fixed during the build

Four faults, each of which lost districts without failing anything:

- **Two pages whose running head the OCR could not read were skipped**, costing 1996 and 1997 about thirty districts each. This is the same page-selection fault `datalab-ocr.py` was fixed for, one layer further down, and the same answer applies: take the table's whole span, not only the pages that announce themselves.
- **1999 renames the table**, dropping "SELECTED" from the title, and was lost whole.
- **The OCR ran the OTHER and TOTAL headings into one cell** on about one page in eight. The page then had no total column, failed the header test and was dropped entire — 39 districts in 1986, 16 in 1993.
- **The header is set over as many as four rows**, and stopping at the first that looked sufficient left 49 of 1999's districts with school counts and no staff at all.

And two rows that had lost a cell were realigned. A row that drops one cell pulls everything after it one place left: Denver's 1994 row came back with **62,773 teachers and 17 pupils**, Colorado Springs' 1996 row with 33,175 teachers. Both are among the largest districts in the state. Every loss point is tried and one is accepted only where the row then satisfies both of its checks.

### Known

- **1999 staffing does not exist.** The 1999 volume prints Fall 1998 teachers beside Fall 1999 pupils, so its staffing is filed under 1998 — and confirmed there, at 38,838 against the NCES 1998 total of 39,360. No volume publishes 1999 staff, and CDE's staff serial starts in 2000.
- **384 of the 2,659 yearbook district-years carry no CDE district code**: 172 BOCES, which have none, and about 210 district-years that renamed before 2000. The printed name and county are kept.
- **Graduation and dropout rates are unchecked.** Nothing else in this archive carries them.
- A stray district row in 2006 carrying 9 FTE is gone: a district-grain publication covers the state, so a year with one district row is not one.

## 2026-09-18 — the alternatives analysis

Two notebooks on top of the archive, asking whether Boulder Valley's Resilient Schools proposal is the only shape the demography supports. The finances are ignored throughout; the question is whether there are enough children.

### Added

- `alternatives-retrieval.ipynb` — builds the working set in `data/analysis/`: a statewide district panel of 5,989 district-years over 1990–2024 across 180 districts, a school panel of 66,828 school-years, a registry of 2,723 schools, and the geography under them. Census TIGER and PL 94-171 downloads are cached in `data/raw/geo/` with checksums and are not committed.
- `alternatives-analysis.ipynb` — closure history, the steady-state model, five levers, and why a school is small. It makes no network call.
- `data/raw/proposal/` — resolution 26-27, the 15 September 2026 board work session, the 2025-26 school profiles and Boulder's ten subcommunities, all supplied by hand and checksummed.
- `data/raw/geo/bvsd/` — the district's attendance areas, capacities and school locations, read from its three ArcGIS web maps at their February 2026 vintage: the same vintage the proposal was drawn against.
- `pipeline/oe_matrix.py` — the Enrollment Pattern Matrices. Their column headings are printed at ninety degrees and every extractor breaks them into individually reversed fragments, so "Boulder" comes back as "B o u d e r" with the l missing. This works from the characters and their positions instead.
- `data/lookups/district-county.csv` — 169 districts to counties, which is what joins the archive to the State Demography Office.

### What it found

- Colorado opened 1,397 schools and closed 651 between 1987 and 2023. A school that closes is half the size of a typical school five years out and a third the size a year out; halving a school's enrollment roughly doubles the odds it is gone within two years.
- Fitted across 178 districts with district fixed effects, a district that loses 10% of its school-age population ends up with **7.6% fewer teachers and 4.4% fewer schools**. Colorado districts have consistently chosen smaller schools over fewer schools.
- BVSD's own two-classes-a-grade standard is about 300 pupils, which is also where Colorado's observed closure rate flattens.
- The archive counts 14 BVSD elementary schools below that bar. So does BVSD, from different data.
- Redrawing boundaries and closing nothing gets 9 schools over the bar against the proposal's 8, and moves 258 fewer children. Redrawing on its own is not among the six options the board was given.
- A third of BVSD's pupils do not attend their neighbourhood school. The four closing elementary areas have materially fewer children in them — a median of 228 against 324 — but the five areas whose families leave most are all staying open, with 1,246 children living in them and enrolled elsewhere.

### How it is checked

- All 69 school rows in the three 2025-26 Enrollment Pattern Matrices rebuild to their printed totals exactly, from the areas they draw plus open enrollment in, placements and unmatched addresses.
- The steady-state model is fitted statewide and applied to one district, so Boulder's own history is not what sets its own forecast.
- The proposal's own figures — buildings closed, pupils moved, capacity — are parsed from the resolution and the work session and compared against the archive rather than restated.

### Known

- **Capacity is February 2026 and enrollment is not.** The layer's own enrollment gives 86% district utilisation, the work session says 68%, the archive's K–5 enrollment over the same capacity gives 62%. Capacity moves slowly, so it is taken from the layer and the enrollment on top of it is the archive's.
- **Redrawing is modelled as proportional to capacity, not as real lines.** It establishes a ceiling, not a map.
- **Open enrollment is measured but not modelled.** The levers move catchment lines; they do not move the choices families make inside them. Only 2025-26 is read, though `2026-09-bvsd/` holds every year back to 2016-17.
- **The child-to-pupil ratio is flat district-wide.** PL 94-171 publishes under-18 by block and single years of age no finer than the tract.

## 2026-09-18 — ten years of open enrollment

`pipeline/oe_matrix.py` now reads all thirty Enrollment Pattern Matrices, 2016-17 to 2025-26, rather than the three current ones, and reads them by arithmetic rather than by their labels (D22).

### What it found

- The share of Boulder Valley's elementary children attending their own neighbourhood school **held at about 70% from 2017 to 2020**, fell four points in 2021, recovered half of that in 2022, and has fallen in every year since — to **62.6%**. Neither answer the proposal's framing offered is right: this did not start with the proposal, and it is not a decade of steady decline either.
- Between 2017 and 2026 the children living in an elementary attendance area fell 22%; the roll of the neighbourhood schools fell **30%**. Of the 2,530 pupils lost, **1,848 are demography and 682 are families leaving**.
- **16 of 30 areas have lost more than five points of their catchment.** The three worst — Monarch K-8 at −25 points, Whittier at −23, Eldorado K-8 at −15 — are all staying open.

### How it is checked

Three independent tests, reported per file in `data/analysis/oe-checks.csv`:

- **685 of 686 school rows** rebuild to their printed enrollment exactly, from the areas they draw plus open enrolment in, placements and unmatched addresses. The one failure is Halcyon in 2020, a three-pupil school, off by one.
- **497 of 498 areas** balance exactly: the flows in an area's column come to the children living there less those placed out. The one failure is Nederland's high-school column in 2016-17, off by one.
- **The computed share agrees with the printed percentage** to within half a point for **491 of 497** areas. Meadowlark's is printed as 0% in its opening years.
- The areas' open enrolment out equals the schools' open enrolment in **exactly at middle and high level in every year**. At elementary the two differ by between one and seven pupils, which is in the published figures rather than the reading.

### Fixed

- **The district's totals column was carried as an attendance area**, and the middle schools' areas were not carried at all. Both came of matching the printed captions, which in these files do not survive extraction: three different footer labels match the same run-together text box.
- **Columns were taken from the right-hand edge of each cell**, but the figures are centred, not right-aligned. A percentage under its counts was enough to split one column into two.

## 2026-09-18 — how old the children are

The analysis had been counting everyone under eighteen, which is three school systems wide. The 2020 **Demographic and Housing Characteristics file** gives age for the same blocks of the same census, so the school-age count is now measured rather than inferred.

### Added

- `data/raw/geo/co2020.dhc.zip` — 198 MB, fetched and checksummed like the other census downloads, not committed.
- **P12, sex by age in bands, is published down to the block.** Its 5-9, 10-14 and 15-17 bands give an exact 5-to-17 count per block — the same band the State Demography Office forecasts and the staffing model is fitted on. The district holds **31,937 children aged 5 to 17** against 41,063 under 18.
- **PCT12, single years of age, stops at the tract.** Its profile splits each tract's 5-to-17 into the elementary years and the rest, and that split is carried onto the tract's blocks. Both a 5-to-10 and a 5-to-11 band are kept (D23): **13,720 and 16,184** children.
- `children_5_17`, `children_5_10` and `children_5_11` on `bvsd-blocks.geojson` and on every attendance-area table.
- **How many of an area's children the district has at all** — the 2020 census and the 2019-20 matrix describe the same months, so the two can be compared directly. Across the 22 areas with both, BVSD enrolled 9,560 of the children living in them: 86% of those aged 5 to 10, 73% of those aged 5 to 11.

### How it is checked

- **All 7,193 blocks agree exactly** between PL 94-171 and the DHC, on total population and on the under-18 count. The two files are tabulations of the same enumeration, so this is the test of the segment offsets, and it is exact rather than approximate.
- The 5-to-10 and 5-to-11 readings rank the attendance areas the same way (**Spearman 0.98**) while differing by thirteen points on the level, so the spread is reportable and the level is not.
- The share of the district's children in an area that loses its school is **11% on all three age bands**, so that figure does not depend on the choice.

## 2026-09-18 — the statewide steady state

Section 6. The panel model was fitted on 178 districts and applied to one; it is now applied to all of them, which answers a question the proposal keeps implying and never tests.

### What it found

- **Boulder Valley ranks 69th of 166** by the contraction its demography implies to 2060. Sixty-eight Colorado districts face a larger one. Its county's 5-to-17 population falls 13% against a statewide median of 9%, and its own school count comes out 2% lower — 4% on demography alone, before the fitted time trend.
- **Its schools are ordinary too.** Among the 19 Colorado districts with 10,000 pupils or more, Boulder Valley's average school of 500 pupils is the 8th smallest against a peer median of 557. Denver runs 459, Colorado Springs 11 runs 377 across fifty-nine schools — seventy-seven pupils below BVSD's own viability bar.
- 110 of the 166 districts sit in a county whose school-age population falls, but only 71 shed schools on the model, because districts have historically absorbed most of a decline in school size rather than in school count.

### How it is built

- `data/analysis/county-school-age.csv` — the SDO forecast for all 65 counties, 1990-2060, written out by the retrieval notebook. Section 2's Boulder projection now reads it too, instead of reaching into the raw file.
- The within-district reading uses the panel model's elasticity directly: with district fixed effects the level cancels in a ratio, so each district needs only its own county's path.
- **The cross-sectional reading uses no fitted form at all.** A log-log line across a range from 25 pupils to 90,450 puts Denver 60% above its own norm, which is a statement about the functional form rather than about Denver. Average school size by district-size band, and then Boulder Valley against its actual peers, needs no such assumption.

## 2026-09-18 — what a closure round does

Section 7, and the last of the roadmap's analysis items. Section 1 asked what predicts a closure; this asks what one does.

### What it found

- **A closure round changes the number of buildings, and nothing else this can measure.** The school count falls about 17% at the round and is still 14% down five years later, so the closures hold. Enrolment and staffing differ from the year before the round at no horizon, and the intervals rule out an enrolment fall of more than about five per cent.
- Thirty-three Colorado districts have run sixty rounds since 1992 — two or more schools at once amounting to between a twentieth and a half of the district — and **Boulder Valley's own 2004 round, five schools of fifty-eight, is one of them.**
- Boulder Valley closed five schools in 2004 and by 2012 was back to fifty-six with two thousand more pupils than at the round, and fifty-seven by 2013 — where it had been in 1999. Its county's children had come back. The SDO says they do not this time, which is the basis of section 2, so this is not a forecast; it is what the last round settled.

### Fixed

- **Every district reported zero pupils in 2000, 2001, 2002 and 2003.** The district panel summed its schools' CDE enrollment, and a pandas sum over a group whose every value is missing returns zero rather than missing. Those years are NCES-only, so all 166 districts came out at zero — 664 district-years of a false count, in a column with no missing values anywhere to suggest something was wrong. The aggregation now uses `min_count=1` and those years read as absent, which is what they are.

### What it cannot tell you

Stated in the notebook and repeated here: the comparison group includes districts that ran a round in a different year, which biases the average where the effect differs across districts; the window is five years; and an interval that rules out a fall of more than five per cent does not rule out four.

## 2026-09-18 — the years and the files that were not being read

Six things, five of them holes in the archive and one of them a hole in the roadmap.

### The district tier's four-year hole is one year wide

`district-year` ran 1977–1999 and then 2004–2024. `pipeline/membership.py` reads the three files that caused it:

- **2001 and 2002** are PDFs whose grade columns run together as text — "ALTERNATIVE SCHOOL000000000051655938213" is sixteen figures with nothing between them. Read from character positions instead: a column is about twenty-eight points wide and a digit about five. The two are not even the same shape as each other, and which it is comes from counting the names on the lines that carry a full row of figures rather than from the header, whose labels are set to the right of the columns they head.
- **2003** is a spreadsheet laid out as an indented panel, where a school's identity is whatever county and district were last seen above it.

Checked twice over: every row's grades add to its printed total (1,630/1,630, 1,662/1,662, 1,664/1,664) and every district's schools add to its printed district total (178/178, 178/178, 180/181). **Against NCES the two PDF years agree to the pupil** once pre-kindergarten is excluded. Only Fall 2000 remains, and CDE published no school file for it.

### 2017 teacher FTE does not exist, in either serial

The Artemis average-salary volumes carry a district Total FTE, so they are read now: 2016 gives 197 districts and 52,079 FTE against the archive's 51,461 from the school sums, and 2018 gives 195 with every row checked against the two categories that must add to it. The 2017 volume gives the same 197 districts and the same 52,079.2 to the decimal. CDE published 2016 again at the 2017 URL, as it did with the ratio report — except this file is not byte-identical, so the checksum could not catch it (D25).

Two guards came of it: a year whose district figures repeat an earlier year exactly is dropped, and so is a district-grain file covering far fewer districts than the state has. The second is why 2019's salary reading is not published: its cells extract merged, the parts-must-add check throws those rows out, and what survives is 154 districts holding 10,132 FTE where the state has 185 and 53,454.

### The private side of the count

`pipeline/nonpublic.py` reads CDE's non-public school membership by school and grade, **2003 to 2014**: 64,286 rows, 297 to 494 schools a year, 56,832 pupils in 2003 falling to 40,830 in 2014. Every row's grades add to its printed total in every year. Charter schools were already carried — `is_charter` from NCES, 1998 onward, 69 schools in 1999 and 266 in 2024 — so what was missing was the private side, and it is the other half of "where did the pupils go" when a school closes.

### County and municipal population, back to 1980 and 1870

Two State Demography Office files: annual county and municipal population from 1980, and the decennial census from 1870. `data/analysis/county-population.csv` and `municipal-population.csv`. This is **total population, not by age** — the single-year-of-age file still starts in 1990 and the district panel still starts with it — so what it adds is the denominator either side, and the district's own towns, which the panel never carried.

The two SDO products agree to a **median 0.015%**, with 97% of county-years within half a per cent. They do not agree exactly and should not: the age file distributes a county across ninety-odd single years and its ages sum to a little off the headline estimate.

### The roadmap

- **Historical and statewide attendance-area boundaries are removed**, not deferred. They are not obtainable.
- Two stale entries fixed: the statewide steady state has been done since section 6, and the non-public row now says what is read and what is not.


## 2026-09-18 — reading the district names

Two districts' pupils were filed under other districts' codes, and 1977–85 could not be joined to anything. Both came from the same place: a name-matching layer that read Colorado's district names more narrowly than Colorado prints them.

### Two mis-attributions, found and fixed

- **Fort Lupton's pupils under Gilcrest's code.** Weld County has two districts called Weld County — RE-1 (Gilcrest) and RE-8 (Fort Lupton). CDE writes the second as "WELD COUNTY S/D RE-8", and with the "S/D" kept the two had different base names, so nothing noticed the clash. The yearbooks' unsuffixed "WELD COUNTY" went to whichever code was seen last, putting **four years of Fort Lupton's roughly 2,650 pupils under 3080**, which is Gilcrest.
- **Rifle's pupils under Parachute's code.** Garfield County has Garfield RE-2 (Rifle) and Garfield 16 (Parachute). Volumes that print plain "GARFIELD" were handed 1220, so **nine years of Rifle's 2,193 rising to 3,787 sat under Parachute's code**, a district of about 700 at the time. Plain "GARFIELD" means Rifle in 1987–95 and Parachute in 1996–99, so it is now left uncoded rather than coded either way.

The fix beneath both: a base name that two district *codes* answer to is never resolved by that base alone. Ambiguity is now read off the codes rather than off how the suffix happened to be printed — counting printed suffixes flags Durango, which is "9-R" in one volume and "9R" in the next and has no second district.

### 1977–85 joins to the rest of the archive

Those nine years carried names but no codes, so BVSD's series began in 1986. Four faults, in order of what they cost:

- **`split_district_name` could not separate a parenthesised designator.** "BOULDER VALLEY RE 2(J)" kept "RE 2 J" in its base name and so never matched "BOULDER VALLEY". This alone stranded every joint district in the state.
- **A page of the 1986 volume lost the first character of every district name** — "SUMMIT RE-1" read as "UMMIT RE-1", Telluride as "ELLURIDE" — while the figures beside them read cleanly. Repaired against the same volume's other tables, which the crop did not touch: a damaged name is accepted only where exactly one name in that volume's own roster fits it. Nine repairs in 1986, three in 1987, each printed by name when the pipeline runs.
- **County headings read as districts.** Where the OCR split "| GILCREST RE-1 | COUNTY: WELD |" across two lines, the parser took the county line as the district: five counties became districts, "COUNTY: WELD" was filed with Gilcrest's 1,800 pupils, and Gilcrest was lost. The 1986 volume now reads **176 districts, Colorado's own count**, against 165 before.
- **Designators printed every way a typewriter allows** — "9-R", "26 JT", "RE-1-J", "R2-J", "RE NO. 1", and NCES's legal "SCHOOL DISTRICT NO. 1 IN THE COUNTY OF DENVER AND STATE OF COLORADO". The legal clause is turned around rather than struck out, because it is the only part of that name saying which district it is.

**Coverage: 98.3% of district-years now carry a code**, from 97.2% in 1977–85 and 96.0% in 1986–99 to 100% from 2000. BVSD and the seven Front Range districts it is compared against — St Vrain, Poudre, Jeffco, Denver, Cherry Creek, Adams 12, Douglas — each run **1977 to 2024 unbroken**, missing only Fall 2000, which CDE never published.

Every yearbook total still reconciles to NCES exactly where it did before: 0.00% in nine of the fourteen years.

### `data/lookups/district-aliases.csv`

Eight districts no rule can reach, because the yearbook name and the modern name have nothing in common — Fort Lupton RE-8 is now Weld County S/D RE-8, Custer County's only district was called Consolidated C-1 for twenty-three years. Each row records the membership either side of the change that identifies it, so the claim can be checked rather than believed.

### What is still uncoded, and why

Ninety-two non-BOCES district-years, all named in the table and all for stated reasons: Garfield and Yuma, where one printed name covers two districts; and five small districts — Vona, Egnar, Genoa RE-13, Arriba RE-31, Arapahoe R-3 — that merged into successors before 2000. A predecessor is not given its successor's code, because that would silently merge two districts' histories.

## 2026-09-18 — asking what a closure does, without the bad comparisons

### Section 8: the staggered-timing estimator

Section 7 compares a district closing schools against every district not closing schools *that* year — including districts four years into their own aftermath. With rounds spread from 1992 to 2019 the regression makes a great many such comparisons, and the two-way fixed-effects estimate is a weighted average over them in which some weights are negative.

Section 8 builds only the clean comparisons: each cohort against districts not yet treated, averaged by cohort size (Callaway–Sant'Anna), with intervals from 1,000 draws resampling whole districts. 18 cohorts covering 33 districts, against 145 that never ran a round.

**The finding holds and the buildings part gets stronger.** Schools fall 17.3% at the round against section 7's 17.5% — the same answer — but where section 7 has the effect fading to 10.5% by the fifth year with an interval covering zero, the clean estimate is still **16.3% down and excludes zero**. The fade was the comparison group: a district five years past its own round was serving as a yardstick for a district at its round, which closes the gap between them whether or not anything reopened. Nothing reopened.

The pre-period straightens out too. Section 7's school count was already 10.6% down four years before a round with the interval excluding zero — a pre-trend that undermines the design. On clean comparisons it is 8.4% down and covers zero.

**Enrolment and staffing still do not move.** Enrolment five years out is −0.2% [−6.4%, +6.7%]. Staffing is +2.2% [−3.5%, +8.9%], so section 7's apparent upward drift to +5.7% does not survive either. One crack is named rather than hidden: four years *before* a round staffing sits 5.2% high and that interval only just excludes zero, so the staff null rests on less than the enrolment null does.

`output/alt-closure-impacts-staggered.csv` and `alt-fig10-closure-impacts-staggered.png`.

### A stale number in section 7

Section 7's prose said the school count was "still 14% down five years later". Its own output file said 10.1%, with an interval covering zero. The prose was wrong when it was written and is corrected, along with the staffing sentence.

## 2026-09-18 — the sixth lever, the children twenty years ago, and a pipeline that can be run twice

### A lever nobody has costed

Sections 3 and 4 set out five responses to fewer children, all of which adjust the buildings. **Lever 6 goes the other way: raise the number of children in the buildings.**

It is not hypothetical. BVSD already draws pupils from outside its boundary through open enrollment and counts them. Between 2017 and 2026 its elementary roll fell 19.8% — and over the same nine years the pupils it draws from outside **rose 11.2%**, from 5.3% of the roll to 7.3%. That is the one line in the district's accounts going the other way, and no version of the proposal mentions it.

The size of the gap is the surprise. Lifting every school that can reach 300 to 300, filling each only as far as its own building allows, takes **666 more elementary pupils**. The district already draws **765** from outside. The gap is smaller than a flow it is already running.

It is still not quick: at the nine-a-year the district has actually managed, 666 takes seventy-eight years. So it is a lever and not a plan — and it is the only one that *adds* children rather than rearranging them, which makes it the only one that combines with the others instead of competing with them.

### Section 9: the children did not leave, they moved

Every count of children in this folder was 2020, which can say where they are and not whether they went anywhere. The 2000 census counted the same ground.

Both years are put on **2000 tract geometry**: the 2000 counts as published, the 2020 blocks assigned to whichever 2000 tract holds them. Chaining the Census Bureau's 2000→2010→2020 relationship files would have put its largest errors exactly where tracts were redrawn, which is where population changed most, which is the thing being measured. Broomfield County did not exist in 2000, so all four counties the district's ground then sat in are read.

**Boulder Valley has 1.3% more school-age children than it had in 2000** — 28,409 then, 28,780 now. Over the same twenty years its enrollment fell. Nineteen of forty-five tracts gained children and twenty-six lost them; the gainers gained 3,612 and the losers lost 3,241. The movement is large and it very nearly cancels.

So the two facts the proposal runs together are separate. The district is losing pupils; the ground it sits on is not losing children.

### Density is not the explanation

1,091 Front Range tracts across ten counties, from the 2020 blocks aggregated to their own tracts — no crosswalk needed, because blocks nest inside tracts.

The rank correlation between density and the share of residents under eighteen is **−0.12**. By band it is nearly flat: 22.2%, 24.5%, 23.0%, 22.2%, 22.4% from under a hundred people a square mile up to ten thousand. Only above ten thousand does it fall, to 15.2%, in eighty tracts holding 7% of the Front Range's people.

The sign is not consistent. Split each county at 3,000 a square mile and Denver and Boulder run the expected way; **Douglas, Broomfield and Weld run the other way**. And Boulder County's *sparse* tracts, at 20.3%, still hold a smaller share of children than Adams County's *dense* ones at 25.1%. Boulder is low at every density, so density is not what makes it different.

Inside BVSD the correlation between a tract's 2000 density and its change in children is **+0.03**.

### A pipeline that could not be run twice

`pipeline.normalize` adds the yearbook staffing years to a table `pipeline.teacher_fte` has already written the modern years into. It read that file and appended to it without first dropping the rows it was replacing, so **every run of the pipeline added another copy of every 1986–1999 district-year**. The committed file held nine copies: 23,931 rows where there are 2,659.

Everything downstream multiplied to match — the district panel came out at 19,784 rows against its true 6,190. The fix is a guard on `source`, which says which step owns each row, and the step is now idempotent: two consecutive runs give 6,732 rows both times.

The previously published README row count for `district-teacher-fte-cde.csv` was a faithful record of a corrupted file. It now says 6,732.

### A note on the section 8 figures

The numbers in the section 8 entry above were first published against the district panel as it stood before two fixes landed in the same day's work: the district-name crosswalk, which gave 38 more district-years a code, and the duplicate-row bug below. They moved by a few tenths of a percentage point — 16.9% to 17.3% at the round, 15.6% to 16.3% at five years — and the entry now carries the figures the notebook actually produces. Nothing about the finding changed.

## 2026-09-23 — an audit of the enrollment cleanup, and what it fixed

An independent audit of the historical enrollment cleanup found eleven defects: six that changed the published data and five that did not yet. All are fixed. Where the fixes moved a published figure, this entry states the new figure, and it supersedes the figure in the earlier entry.

### The school tables lost 234,000 pupils in 2001 and 2002

The school tables were keyed on the school code, and the 2001 and 2002 PDFs print none. Every row that the name match could not code had the same empty key, and each grade kept only the last row. **124,863 pupils of 2001 and 109,041 of 2002 were not in `school-enrollment-by-grade.csv` or `school-year.csv`**, and one "school" held the combined 124,924 pupils of 371 schools. District totals in `district-year.csv` were correct, because they sum the raw rows. But the district panel sums the school table, so 121 districts in 2001 and 116 in 2002 were undercounted there.

Now a code-less school takes the code the NCES directory of the same year holds for it: 620 by name, all of which agree with NCES to the pupil, and 79 more by an equal total. Seven school-years get a placeholder code starting with `X`. The pipeline now stops if any year loses a pupil between the rows it reads and the table it writes. That check found a second loss at once: CDE gives `0006` and `0001` to facility programmes in more than one district, and 51 pupils were lost where they collided. Those codes now carry their district as a prefix (D32).

### Garfield: two districts, one name

Some pages print a district's number in a cell of its own, "| GARFIELD | RE-2 |". Both yearbook parsers read only the name. So the 1987 trend table dropped Garfield 16 (432 pupils), and the 1989–1995 grade tables **added Rifle and Parachute together into one row**. The #45 entry said nine years of Rifle's pupils sat under Parachute's code; only 1987 and 1988 were Rifle alone. Both parsers now read the number, and both districts carry their codes in every year from 1986 to 1999. The overlap file had also called the 1987 collision an agreement; it now counts agreement only between two different volumes (D32).

### `fall_membership` changes its definition in 1988

To 1987 it is the printed total; from 1988 it is a sum of grades with pre-kindergarten in and special education out. In 1987 the two differ by 0.8% statewide and by up to 2.6% for one district. `district-year.csv` now names the rule on every row in `membership_definition` and carries `fall_membership_k12`, which has one definition from 1986 to 2024 (D33).

### Counties

The printed counties included "Kidwa", "Guray", "Montrase" and "Montr", and six counties spelled two ways. Where the district code is known, the county now comes from `district-county.csv`, so the modern rows have a county too. The 70 coded rows without one are statewide units, the Charter School Institute (8001) and BOCES codes, which sit in no county (D34).

### Five defects that had not yet changed the data

A lookup could match a district in another county; a trend heading with no county line gave its measures to the district before it; "JT" was not removed as a joint marker; a legal name in two counties reduced to a bare "28J"; the ambiguity index was built three times. All five are fixed, and every file in `data/processed/` is byte-identical to the run before these five fixes. The crosswalk loses one key, `27J`, which no row used (D34).

### Figures that moved

The corrected 2001–2002 panel changed the enrolment path of sections 7 and 8. **The finding is the same, and stronger**: enrolment does not move, and the intervals are narrower. At the round the clean estimate is +0.3% [−1.1%, +1.6%], where it was −2.1% [−5.1%, +0.5%]; five years out it is +2.7% [−2.3%, +8.3%]. The intervals now rule out an enrolment fall of more than about 3% in the three years after a round, not 5%. The school effect is 17.3% at the round and 16.2% five years later on clean comparisons (was 16.3%). Section 7's pre-trend is 10.3% (was 10.6%) and section 8's is 7.8% (was 8.4%). Staffing's pre-trend is +5.1% [+0.3%, +10.4%].

Section 2's school elasticity is 0.423 (was 0.424). The statewide coded share of district-years is 98.4%.

### Numbers that were already out of date

The sync also found figures that no earlier change had moved but that no longer matched the notebook, and corrected them: the README ranked Boulder Valley 69th of 166 where section 6 says 73rd of 178; it cited 19 large districts and a peer median of 557 where the output has 20 and 573; section 2's prose said 7.6% fewer teachers where 1 − 0.9^0.744 is 7.5%; section 1's prose said 1,373 openings and 725 closures where the output has 1,397 and 651; and one README sentence said Colorado Springs 11 averages 377 pupils, "*below*" a bar of 300, which its own numbers contradicted. The notebook said CDE publishes no district enrollment for 2000 to 2003; only 2000 is missing, so the 2004 round is now compared with 2003, not 1999.

## 2026-09-25 — the vote, the costed combinations, and data for Datawrapper

On 22 September 2026 the board approved the Resilient Schools plan by five votes to two ([Boulder Reporting Lab](https://boulderreportinglab.org/2026/09/23/boulder-valley-school-board-votes-to-close-four-elementary-schools-amid-calls-to-delay/)). Birch, Douglass, Flatirons and Mesa close in fall 2027, and Monarch K-8 becomes a middle school, so its elementary programme closes too. This entry records what that changes in section 3, and it supersedes the lever figures in earlier entries.

### The approved plan, modelled as voted

Lever 1a was "the proposal", with each closing area sent to the nearest school and Monarch's elementary programme left open. It is now the plan as approved: five elementary programmes close, and each area goes to the schools the plan names (Birch to Kohl, Mesa to Bear Creek, Douglass to Coal Creek, Eisenhower and Heatherwood, Flatirons to Whittier and Foothill, Monarch to Fireside and Superior). Where the plan divides an area, the pupils are split in proportion to each receiver's empty seats (D35). On today's roll the plan leaves 22 elementary schools, 5 below the bar and 4 over capacity, and moves 1,218 children. Monarch's 266 elementary pupils go to schools with 180 empty seats between them, so no split fits them.

### The combinations are costed

A new part of section 3 scores eight combinations of closing, redrawing and recruiting on today's roll and on the SDO forecast for 2027, 2030 and 2040. The costs are counts, not dollars, because the financials are out of scope: schools kept, schools below 300, schools over capacity, children who change school, and pupils to recruit. In 2027, when the closures take effect:

- The approved plan alone leaves 6 schools below the bar and 3 over capacity.
- The approved plan with a redraw leaves 5 below and none over, and moves 1,270 children. 106 recruits bring the two plains schools left below (Whittier and Sanchez) to the bar.
- Keeping all 27 schools, with a redraw and recruitment, moves 642 children, and needs 488 more pupils by 2027 and 694 by 2030. The district draws 765 from outside its boundary today.
- A redraw alone stops helping: on the 2027 roll it leaves 17 schools below the bar, one more than doing nothing.

Output: `output/alt-levers-combinations.csv` and figure 5b.

### Corrections to the levers

- **Sanchez was missing from every lever.** Attendance areas were matched to schools by name, and "Sanchez" did not match "Alicia Sanchez International School". The match now uses the CDE school code in the layer's `State_CD` field (D37). Sanchez has 290 K-5 pupils in a building of 301 places, so the model now has 27 schools, not 26, and the archive counts 15 schools below the bar, not 14. The README's "So does BVSD" was a match that depended on the missing school, and it now says 15 against BVSD's 14.
- **The mountain schools are outside redraw and recruitment** (D36). A redraw in proportion to capacity had sent Boulder's pupils to Nederland, and recruitment had counted pupils for Nederland, Gold Hill and Jamestown. They stay in the count of schools below the bar.
- **Lever 4 counted the forecast decline as children moved.** It now counts only children who change school, against that year's own roll.
- The combination scoring counts moves from the stage before recruitment, so a recruit never reduces the children moved.

### Figures that moved

| | was | now |
|---|---:|---:|
| Schools below the bar today (archive) | 14 | 15 |
| Lever 1a: schools, below the bar, over capacity, children moved | 22, 8, 4, 952 | 22, 5, 4, 1,218 |
| Lever 1b: closures, utilisation, schools over | 12, 104%, 8 | 13, 108%, 9 |
| Lever 3: below the bar, children moved | 9, 694 | 9, 693 |
| Lever 4 in 2030: children moved | 770 | 609 |
| Lever 6: pupils to recruit, years at the recent pace | 666, 78 | 519, 61 |
| Children in an area that loses its school | 11% | 14% |
| Median children, closing and open areas (section 4) | 228, 324 | 260, 326 |

The section 4 figures moved because Monarch is now counted as a closing area. Four of the five areas whose families leave most are staying open. The fifth is Monarch.

### Other corrections

- Section 2 said Boulder Valley lands "roughly three schools fewer than today by 2060". The fitted value is 53.9 against 56, so it now says about two fewer, after a low of about 52 around 2030. The README said "near 53" and now says "near 54".
- The README named Monarch K-8, Whittier and Eldorado K-8 as the three areas that lost most catchment. Leaving aside Gold Hill's eleven children, Douglass is third (−15.0 points) and Eldorado fourth (−14.7).
- The retrieval and analysis notebooks said "nine Front Range counties" and "the other seven counties". There are ten and eight.
- The README called section 3 "five levers"; there are six.
- Three variables were overwritten by later cells: `per_year`, `names` and `usable`. They now have separate names, so section 10 reads the frames the charts were drawn from.
- Three sentences said more than the evidence shows: that the board saw only one option, that the approved plan's split was "most favourable" to it, and that every route to the bar needs a redraw (recruitment alone gets there too).

### Added

- `datawrapper/`: twenty files for the column's Datawrapper charts, written by the new section 10 of the analysis notebook, with a README that gives the chart type, a claim title, the source line and the caveat for each one. There are two maps: the attendance areas under the approved plan, and the change in children by 2000 tract. Each is a GeoJSON file with a CSV that shares its key.
- `dw-03`: Boulder Valley against the 16 other Front Range districts with more than 10,000 pupils, 1977–2024, in K-12 fall membership. For 1977–85 each district is scaled by its own ratio of the two measures in 1986–87 (D38).
