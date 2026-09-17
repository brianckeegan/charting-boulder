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
