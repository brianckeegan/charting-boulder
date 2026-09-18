# Decision log

Dated decisions, with the reason and what would reverse them. Newest last.

## D1 — Statewide, not Boulder County — 2026-09-17

The archive covers every Colorado public school, about 1,900 a year, rather than the Boulder Valley and St. Vrain districts alone.

**Why.** The column's question is whether Boulder's closures are unusual. That cannot be answered from Boulder's own data. Forty years of statewide closures is the comparison set, and a statewide panel at this grain is about 50,000 rows a year — large but unremarkable.

**Cost.** Roughly ten times the audit surface of a county-only archive, and every parser must survive every district's formatting quirks rather than two.

## D2 — CDE is the spine, CCD is harmonized alongside — 2026-09-17

CDE is the count of record wherever it publishes. NCES CCD is retrieved, harmonized onto the same schema and compared school by school, but never silently substituted for a CDE figure.

**Why.** CDE's October count is Colorado's own statutory count and the number the state acts on. CCD is a federal re-publication on its own basis. Carrying both, with a per-row `source`, keeps the authoritative number authoritative while making the disagreement visible instead of hidden.

**What justified it.** The two agree far more closely than expected — 0.03% statewide in 2013 once pre-kindergarten is excluded. That makes the pairing cheap to maintain and makes any future divergence a strong signal that something broke.

**What would reverse it.** If the reconciliation turns out much worse in other years than in 2013, the archive should say so loudly rather than pick a winner.

## D3 — Teacher FTE is left empty before about 2013 on the CDE side — 2026-09-17

Rather than back-filling with a district figure.

**Why.** School teacher FTE and district teacher FTE are different measurements. Putting them in one column would let a reader divide a school's pupils by a district's teachers without noticing. CCD supplies school-grain FTE from 1986 in its own column, so the gap is narrower than it first appears.

## D4 — The 1986–1999 tier is district grain only — 2026-09-17

Not a choice so much as a finding. Every table in those fourteen yearbooks is by school district; there is no school-level table in the series.

**Consequence.** *On the CDE side* the school panel starts in 2004, the first year with a machine-readable school-grain file the parser reads. NCES CCD carries school-grain data from 1986, so the panel itself runs 1986–2024 with CCD alone for the early years. The district panel runs 1977–2024.

## D5 — The scanned yearbooks are re-OCR'd through Datalab — 2026-09-17

Superseding an earlier plan to hand the scans back for processing elsewhere.

**Why.** The embedded OCR layer recovers 3.9% of the district-by-grade table's cells and none of the staff table's. Datalab's accurate mode returns the complete grid, verified against the tables' own printed row totals. It costs 0.75 cents a page, about $5 for all fourteen volumes.

**How it is kept frugal.** The embedded text layer is poor at numbers but good at headings, so it is used to find the wanted tables and only those pages are sent — 48 pages rather than 126 for the 1986 volume.

**Operational note.** The API key lives in `DATALAB_API_KEY` and is never written into the repository.

## D6 — Closures are auto-labelled and never hand-verified — 2026-09-17

A school that stops reporting is labelled from the data alone, with a confidence flag.

**Why.** Hand-checking every disappearance across 178 districts and forty years is larger than the rest of the task combined, and the column's argument rests on the shape of the distribution rather than on any one building.

**Cost, stated plainly.** The closure count is approximate everywhere. A closure, a merger, a rename and a code change can look alike from the data. The data dictionary says so and the confidence flag carries it into every downstream use.

## D7 — Buildings get coordinates, not current use — 2026-09-17

Each school carries a latitude and longitude, carried backward from a recent CCD directory. What a closed building holds today is out of scope.

**Why.** Coordinates come free with a source already being retrieved. Current use exists in no education dataset; it needs county assessor records and local news, and every row would need a hand check and a citation. That is its own task.

## D8 — The steady-state model is a separate task — 2026-09-17

This folder's task ends with a cleaned archive. The model against the State Demography Office forecasts to 2050 and 2060 is deferred to `ROADMAP.md`, and the archive is shaped to feed it.

**Why.** An archive whose cleaning rules are settled while a model is being fitted to it tends to acquire rules that suit the model.

## D9 — Scaffolded at L1, not higher — 2026-09-17

Documented, but with no pipeline-as-code, no CI, no governance set.

**Why.** The data is public school counts with no privacy or governance questions, and the repository already has its own conventions, licence and ignore rules. An L2 pipeline becomes worth building once the cleaning rules stop moving. Deferred concerns are in `ROADMAP.md` rather than generated as empty files.

**Deviations from the L1 template, and why.** No nested `.gitignore`, `.gitattributes` or `LICENSE` — the repository root supplies all three. No `AGENTS.md` — no other folder in this repository has one, and the guidance an agent needs is in `TASK.md` where a human will also read it. `CITATION.cff` sits in this folder rather than the repository root, because the citable thing is this dataset rather than the repository.

## D10 — Raw files: commit the small originals, not the large ones — 2026-09-17

The CDE spreadsheets and PDFs are committed. The CCD API responses (12 MB for three years) and the yearbook PDFs (about 110 MB each) are not.

**Why.** The CDE originals are small, and government files move and vanish. The large files are re-downloadable and their SHA-256 checksums are recorded in `data/raw/manifest.json`, which is what reproducibility actually requires. This follows the repository's existing practice for the OEWS and QCEW raw directories.

## D11 — The long panel carries no names — 2026-09-17

`school-enrollment-by-grade.csv` holds only identifiers, grade and the two counts. Names, districts and coordinates live in `school-year.csv`.

**Why.** A school has about fourteen grade rows a year. Repeating its name, its district's name and a source filename on each of them made the file 65 MB and added nothing: the values are identical within a school-year. Slimming it to identifiers plus counts took it to 24 MB. Join on `(year, school_code)`.

## D12 — Aggregate rows are excluded by name, not just by code — 2026-09-17

Rows whose code is `9999`, or whose name matches a totals pattern, are dropped from the school tier and counted in the parse report.

**Why.** The 2010 file ends with a STATE TOTALS row coded 9999/9999 carrying all 843,316 pupils. Read as a school it doubled the state exactly. **The row-total checksum did not catch it**, because an aggregate row sums correctly against itself — every one of that year's 1,799 rows passed. Only comparing the school sums against the file's own district rows exposed it.

**What this costs.** A real school named "Totals for Something" would be dropped. None exists in 39 years of data, and the count of excluded rows is reported per file so the trade stays visible.

## D13 — Two known parser gaps are left as gaps — 2026-09-17

2001 and 2002 publish school-by-grade as PDF only; 2003 uses an indented panel layout the parser does not read. All three are left unparsed on the CDE side rather than half-extracted.

**Why.** NCES CCD covers those years at school grain, so the panel has no hole — it simply has one source instead of two, and `source` says which. Writing a third parser shape for three years, when a validated source already covers them, buys accuracy the archive can already get.

**What it costs.** Those years have no second source to reconcile against, and CDE is the count of record everywhere else. The reconciliation table has no row for them, which is the honest representation.

## D14 — A teacher-FTE row must satisfy the file's own arithmetic — 2026-09-17

Every row parsed out of a CDE pupil/teacher ratio report is kept only if `enrollment ÷ teacher_fte` equals the printed ratio to within 5%. Rows that fail are dropped and counted, never repaired by guesswork.

**Why.** These reports wrap long school names onto a second line, and a wrapped row shifts every field one place left — the enrollment lands in the FTE column. It produces numbers that look like data: Douglas County High School came out with **1,893 teachers**, and the 2016–2018 state totals ran 31% high. No checksum in the file catches this, because the misread row is internally consistent. The printed ratio is a third figure the file already carries, and it is what makes the shift detectable.

**What it costs.** A row whose published ratio is itself wrong is dropped along with the genuinely broken ones. The parse report in `audit/teacher-fte-parse.json` records how many rows each file lost, so the trade is visible per year.

## D15 — District teacher FTE carries both what CDE states and what its schools sum to — 2026-09-17

`district-teacher-fte-cde.csv` holds two figures per district-year in their own columns: `teacher_fte_published`, which is what CDE states the district holds, and `teacher_fte_school_sum`, which is the district's schools added up. Neither is ever substituted for the other, and `teacher_fte_difference` is the comparison.

**Why.** CDE publishes a district total in three years out of twenty-five: 2010, where the ratio report prints a `<district> TOTALS*` row after each district's schools, and 2023 and 2024, where there is a by-district spreadsheet. Building the table only from those would give three years. Building it only from sums would throw away CDE's own statement in the years it makes one. Carrying both is the rule the school panel already follows with CDE and NCES, and it turns the overlap into a check: **551 district-years carry both and 396 agree to the hundredth of an FTE**, including all 185 districts in 2023.

**What this replaces.** The first version of this table had **seventeen rows**, and every one of them was wrong. Thirteen were schools whose own code had been merged into their name, leaving one code behind — and one code is what marked a row as a district, so "HULSTROM OPTIONS K-8 SCHOOL" was filed as a district. Three more were state totals. The by-district spreadsheets for 2023 and 2024 were being read, but their code column is headed `LEA` rather than `LEA Code`, so every district in both years took an empty code, collapsed onto one key, and survived only as the unnamed row at the bottom of the file carrying the state total. Nothing in the table's own shape showed this: seventeen rows spanning nine years looked like thin coverage, which is how it was described, rather than like a bug.

**Also a source defect, not a decision.** CDE publishes its 2016 and 2017 pupil/teacher ratio reports at different URLs, but the two files are byte-identical — same SHA-256, same 583,100 bytes. The later one is dropped rather than presented as a second year of data, so **2017 is absent from both teacher tables**.

## D16 — A run-together row is re-cut using the file's own arithmetic, never guessed — 2026-09-17

Where two printed columns run together into one field, every way of cutting the trailing text into three figures is tried, and a cut is accepted only if the first divided by the second equals the third to the precision the third is printed at. Where more than one cut survives, the one that keeps the most of the row's own field boundaries wins. Where none does, the row is dropped.

**Why.** In these reports the space between two right-aligned figures is often narrower than a character, so "34.5" and "17.2173913" arrive as "34.517.2173913". Every row of the 2002 report is like this, and 2007, 2008 and 2012 are partly so. The tables print three numbers whose relationship is fixed — membership over teacher FTE is the ratio — and that is what makes the split recoverable rather than a guess.

**The bounds matter, and getting them wrong is silent.** CDE truncates the printed ratio rather than rounding it, so 616 over 31.15 is 19.7753 and the file says 19.77; a half-unit window rejects the correct cut and the row is lost. But a whole-unit window on a ratio printed as "1" accepts almost any pair of numbers, and Hagen Early Education Center came out of a clean row with **8,435 teachers**. Both bounds are applied and the tighter one holds.

**A row that already reads as three figures is taken at its word**, subject to the 5% check the archive has always applied, and only a row that fails that is re-cut. A clean row can never be silently re-split into a different set of numbers.

## D17 — A district row has to be a district the file itself names — 2026-09-17

A row read as district grain is kept only if its code and name appear together as a district in the same file's school rows. A file that publishes districts and nothing else is exempt, because it has no school rows for a missing code to have come from.

**Why.** Grain was decided by counting codes: two codes meant district plus school, one meant district alone. A school row whose school code merged into its name leaves one code behind and passes that test, and that is the whole of how `district-teacher-fte-cde.csv` came to be seventeen rows of schools. The file that prints a school also prints its district beside it, so the file itself says which codes are districts — no list has to be maintained here.

**What it costs.** A real district that appears in no school row would be dropped. None does, and the count of rows this rejects is reported per file in `audit/teacher-fte-parse.json`.

## D18 — A figure is filed under the year it measures, not the volume it appears in — 2026-09-18

The 1999 yearbook's classroom teacher FTE is stored under **1998**. Its school counts and membership stay under 1999.

**Why.** That volume prints Fall 1999 membership beside Fall 1998 teachers, in the same row, under two different "FALL" headings. Filing the staff by the volume would put a whole year of Colorado's teaching staff one year out, and nothing downstream would notice: the numbers are the right size and the series would still look continuous. The heading states which autumn the column measures, so the heading decides.

**How it was caught, and what it costs.** The row's own arithmetic stopped agreeing — students over teachers no longer matched the printed ratio, because the ratio is also the 1998 one. That check is therefore switched off for those rows, which leaves the 1998 staffing with no internal check; it rests instead on NCES, where it lands within 1.3%. The consequence is a real hole: no volume publishes 1999 staffing and CDE's staff serial starts in 2000, so **the CDE teacher series has no 1999**.

## D19 — The yearbook era joins the district table rather than getting its own — 2026-09-18

`district-teacher-fte-cde.csv` holds 1986–2024 in one file, with `source` naming the era each row came from, rather than a separate table for the fourteen scanned volumes.

**Why.** It is one measure of one thing — how many teachers a Colorado district employs — and splitting it by how it happened to be printed would make the ordinary question, how staffing changed over forty years, a join. The archive already mixes eras inside one table wherever the measure is the same: `district-year.csv` runs from 1977 on the same basis.

**What it costs, and the guard.** A scanned 1991 figure and a 2023 spreadsheet figure sit in the same column, distinguished only by `source`. That is a real hazard, so the columns that exist in only one era are kept separate rather than merged into a single "staff" column: `staff_certificated_fte` and `schools_published` are yearbook-era, `teacher_fte_school_sum` and `schools_in_sum` are modern, and a row that carries the first pair and not the second is obviously from the scans without reading `source` at all.

## D20 — The Enrollment Pattern Matrices are read where they already sit — 2026-09-18

The 2025-26 matrices are read from `2026-09-bvsd/data/raw/open-enrollment/` rather than fetched again into this folder's `data/raw/proposal/`.

**Why.** That folder already holds every year from 2016-17, each with the URL it came from and its checksum, and the three files are byte-identical to what the published URLs serve today. A second copy is a second thing to keep in step and a second answer to the question of which is the original. The same reasoning already governs the State Demography Office's single-year-of-age file, read from the same neighbour.

**What it costs.** This folder is no longer self-contained: `alternatives-retrieval.ipynb` will not run without its sibling. That is already true of the demography, and the README's reproduce section names both.

## D21 — Open enrollment is reported, not folded into the levers — 2026-09-18

Section 4 measures where Boulder Valley's pupils actually go. The five levers in section 3 stay resident-based.

**Why.** The matrices say what families chose under today's schools and today's boundaries. Closing a school or redrawing a line changes what they are choosing between, and nothing here says how they would choose again. Carrying a 2025-26 departure rate through to 2060 would dress an assumption as a measurement, and the departure rates are the largest numbers in the analysis: Sanchez keeps 35% of the children living in its area.

**What it costs.** The levers answer "if every child attended their own area's school", which no lever achieves and today's district misses by a third. Section 4 is therefore the honest limit on sections 2 and 3 rather than an extension of them, and it is where the reader is sent: a school small because its area emptied and a school small because its families left are the same number and different problems.
