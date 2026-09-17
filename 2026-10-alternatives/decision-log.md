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
