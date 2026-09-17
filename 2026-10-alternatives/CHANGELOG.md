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
