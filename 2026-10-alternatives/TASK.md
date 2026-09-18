# Task: audit, retrieve and clean the Colorado school panel

A proposal. It describes work to be done, not work already finished. What *is* finished is the audit evidence it rests on: `proof-run.py` fetched and parsed real files for 2001, 2013 and 2024, `datalab-ocr.py` re-read the 1986 yearbook, and `audit/proof-run.md` records the sixteen findings that shaped every rule below.

## Goal

A cleaned CSV archive of **annual school-level enrollment by grade with teacher FTE, for every Colorado public school**, plus the district-level panel that reaches back further than any school-level source does.

The archive exists to serve three questions the column is heading toward: which schools have closed and when, where those buildings are, and what a steady-state distribution of schools would look like under the State Demography Office forecasts to 2050 and 2060. It is built to feed that model. It does not contain it.

## Non-goals

- **The steady-state model itself.** Separate task. See `ROADMAP.md`.
- **What closed buildings are used for today.** Not in any education dataset; needs county records and news. `ROADMAP.md`.
- **Hand-verified closure reasons.** Closures are auto-labelled with a confidence flag and never hand-checked, by decision (see `decision-log.md`, D6).
- **Non-public schools, home-based education, detention facilities.** CDE publishes these separately. Out of scope, and the cleaning step must exclude them explicitly rather than by accident.

## Sources and what each one is for

| Source | Supplies | Years | Role |
|---|---|---|---|
| CDE Artemis ED5/90.17 | School enrollment by grade | 2000–2024 | Spine |
| CDE pupil-membership archives | School enrollment by grade | 2019–2025 | Spine, current era |
| CDE staff statistics (Artemis ED2.88 + current) | Teacher FTE by school | 2000–2024 | Spine |
| CDE Artemis ED2/79.19 yearbooks | District enrollment by grade; district staff and ratios | 1986–1999, and 1977–1986 via the 1986 volume's Table 4 | District tier |
| NCES CCD, via the Urban Institute API | School enrollment by grade, teacher FTE by school and by district, coordinates, charter flag, open/closed status | 1986–2024 | Secondary, harmonized and compared |

CDE is the count of record wherever it publishes. CCD is carried alongside it, never silently substituted, and the two are compared school by school every year they overlap.

## Outputs

All in `data/processed/`, all long-form and UTF-8, with a row-level `source` column throughout.

| File | Grain | Contents |
|---|---|---|
| `school-enrollment-by-grade.csv` | school × year × grade | The core panel. `enrollment_cde`, `enrollment_ccd`, `source` |
| `school-year.csv` | school × year | Identity, totals, `teacher_fte_cde`, `teacher_fte_ccd`, latitude, longitude, charter flag, status |
| `schools.csv` | school | Registry: stable id, every name and code it held, first and last year seen, closure label, confidence |
| `district-enrollment-by-grade.csv` | district × year × grade | 1986–2025, from the yearbooks and the district files |
| `district-year.csv` | district × year | 1977–2025. Fall membership, closing-day membership, average daily membership, ADAE, school counts, staff, pupil/teacher ratio |
| `source-reconciliation.csv` | school × year | CDE against CCD: both totals, the difference, and why it is expected where it is |

`DATA-DICTIONARY.md` documents every column, its units and its missingness.

## Phase A — audit

Nothing is parsed in this phase. The point is to know what exists before writing a parser against it.

- **A1.** Walk all 26 Artemis membership year indexes and both CDE archive pages. Record, per year: which reports exist, their URLs, their formats. **Read the label that follows each link, never the text before it** (finding A4). Verify each file's own title page against its index label and record every disagreement.
- **A2.** Do the same for the staff series, and open every ratio report to record whether it is school grain or district grain. The titles are not reliable — 2013 and 2016–2019 say "by school", 2014 and 2015 do not, and the only way to settle a year is to look inside it.
- **A3.** For each of the 14 yearbooks, list the tables and the pages each occupies.
- **A4.** Probe CCD for every year 1986–2024 and record the row counts, the `seasch` format, and whether a year has been released.
- **Output:** `audit/inventory.csv`, one row per file, plus `audit/coverage.md` naming every year-measure cell that no source fills.

## Phase R — retrieval

- **R1.** Discover URLs from the indexes rather than hardcoding them, so a re-run picks up new vintages. `proof-run.py` hardcodes five files deliberately, because it is a probe; the pipeline must not.
- **R2.** Download to `data/raw/`, never edited in place. Record URL, byte count, SHA-256 and fetch time for every file in `manifest.json`.
- **R3.** Commit the CDE originals (about 3 MB for the proof years; perhaps 60 MB for all 26). Do **not** commit the CCD JSON or the yearbook PDFs — they are large and re-downloadable, and the manifest's checksums prove what was used.
- **R4.** Retry with backoff. The Artemis host resets connections under load; the proof run saw it twice.

## Phase O — OCR the scanned tier

Run `datalab-ocr.py`. It locates the wanted tables using the volumes' own embedded text layer, sends only those page images to Datalab in accurate mode, and deletes each 110 MB PDF once its pages are extracted. It is resumable. About 0.75 cents a page, roughly $5 for all fourteen volumes.

Status: 1986 complete (48 pages, 35.25 cents). 1987–1999 in progress; `audit/ocr-run.log` and each `data/interim/yearbooks/<year>/index.json` record what landed.

## Phase C — cleaning

Each rule below traces to a finding in `audit/proof-run.md`. None of them is a matter of taste; each is a thing the data actually does.

1. **Sum the two kindergarten columns.** CDE splits Half-Day K and Full-Day K; every other source has one K (A5). Keep the split in a `k_half` / `k_full` pair as well, since the ratio between them is itself a fact about a district.
2. **Read ordinal grade headers.** `1st` … `12th`, not bare numbers (A5).
3. **Map the drifting identifier columns onto one schema.** `COUNTY/DISTRICT/SCHOOL` before about 2019, `Organization/School` after (A6).
4. **Treat every code as a zero-padded string.** `0010` is not `10.0`. A spreadsheet reader will get this wrong unless told not to (A6).
5. **Normalize the CCD state id across the 2016 break.** Take the part after the hyphen; it spans both eras (A7).
6. **Record CCD pre-K as missing, never as zero.** CCD publishes no pre-K for Colorado at all (A8).
7. **Drop CCD's negative enrollment values.** They are missing-data sentinels, not counts (A8).
8. **Reject sentinel coordinates.** Take each school's location from a recent CCD directory and carry it backward by identifier, rather than reading a `-2.0` latitude from an early year (A12).
9. **Extract the 2000–2002 PDFs by character position, not by splitting strings.** Those files are born-digital but kerning-split: `604` arrives as `6 0 4` (A10).
10. **Check every row against its printed total.** Both the scanned tables and the born-digital PDFs print a row total. Where the grades do not sum to it, flag the row and keep both numbers. This is the only mechanical proof a row was read correctly (A14).
11. **Exclude non-public, home-based and detention rows explicitly**, and record how many were removed each year.

## Phase S — school identity and closures

- **S1.** Build `schools.csv` keyed on the CCD `ncessch`, which is stable across renames, with the CDE school code and every name the school ever carried as attributes.
- **S2.** Derive a closure as a school's last reporting year, then auto-label it from the data alone: CCD's `school_status`, whether the code was later reused, whether a near-identical name appears elsewhere in the same district that year. Attach a confidence flag.
- **S3.** Do not hand-verify. The labels are approximate everywhere and the data dictionary says so (D6).

## Phase V — validation

- **V1.** Reconcile CDE against CCD for every overlapping year, school by school. The 2013 benchmark: 1,781 of 1,826 schools matched, 1,257 agreeing exactly, median difference 0, and a statewide gap of 226 pupils — 0.03% — once pre-K is set aside (A9). A year that comes out materially worse than that is a parser fault, not a data fault.
- **V2.** Never align CDE 2024 against CCD 2023. Where CCD has not released a year, the CCD columns are empty (A9).
- **V3.** Cross-check the current teacher-FTE file's own `Enrollment Count` against the membership file. They should agree school by school; any disagreement is a crosswalk fault (A11).
- **V4.** Check each district's school-level sum against the published district total for the same year.
- **V5.** Publish the failures. `audit/validation.md` names every check, its pass rate and its worst cases.

## Acceptance

The task is done when:

- every year from 2000 to 2025 has a school-level row count within a few percent of the CCD directory count for that year, or a recorded reason why not;
- `district-year.csv` reaches back to 1977-78;
- every row of every scanned table either passes its printed-total checksum or is flagged;
- the 2013 reconciliation reproduces the benchmark in V1;
- `DATA-DICTIONARY.md` documents every column, and `audit/coverage.md` names every empty cell in the year-by-measure grid;
- no unfilled template placeholder remains anywhere in the folder, and every internal link resolves.

## Effort and cost

| Phase | Rough effort | Money |
|---|---|---|
| A — audit | half a day; it is mostly reading index pages carefully | none |
| R — retrieval | half a day | none |
| O — OCR | runs unattended over a few hours | about $5 |
| C — cleaning | the bulk of it: 2000–2002 PDF extraction and the yearbook tables are the hard parts | none |
| S — identity | a day, most of it on code reuse across districts | none |
| V — validation | half a day | none |

## Known risks

- **Grade-column layouts drift across 26 years** in ways three sample years cannot reveal. Phase A exists to find that before Phase C assumes otherwise.
- **The 2000–2002 PDF extraction may not reach the accuracy the spreadsheet years do.** If it does not, those three years carry a lower-confidence flag rather than being quietly dropped. CCD covers them independently, which is the fallback.
- **Yearbook table headings drift across fourteen volumes**, so `datalab-ocr.py`'s page-selection patterns may miss a table in a later volume. The per-volume `index.json` records what each page actually turned out to be, so a miss is visible rather than silent.
- **Code reuse across districts** means a four-digit CDE school code is not unique statewide in every year. This is why the registry keys on the NCES id.
- **CCD ends at 2023** and CDE at 2025. The overlap is what the reconciliation runs on; outside it, each source stands alone and the archive says which.
