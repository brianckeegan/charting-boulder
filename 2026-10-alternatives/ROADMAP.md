# Roadmap

What is deliberately not being built now, why, and what would bring it forward. A named deferred concern is worth more than an unmaintained file.

## Deferred work

| Item | Why deferred | What brings it forward | Blocking? |
|---|---|---|---|
| **The steady-state model** — school size and distribution for every Colorado district against SDO county forecasts to 2050 and 2060 | This task ends at a cleaned archive. Fitting a model while the cleaning rules are still moving tends to bend the rules toward the model | The archive passing its acceptance tests in `TASK.md` | No |
| **Current use of closed buildings** | Exists in no education dataset. Needs county assessor records, district property lists and local news, with a hand check and a citation per row | A decision that the column needs it, and a bounded geography — Boulder County alone is perhaps forty buildings, statewide is thousands | No |
| **Hand-verified closures** | Larger than the rest of the task combined. See `decision-log.md`, D6 | A finding that rests on a specific building, rather than on the shape of the distribution | No |
| **Attendance-area boundaries** | Would let enrollment be tied to where pupils live rather than where they are taught. CDE does not publish historical boundaries; districts publish them inconsistently | The column needing a residence-side question | No |
| **L2: pipeline-as-code, pinned environment, CI** | The cleaning rules are not settled. A Snakefile written now would be rewritten during Phase C | Phase C finishing. At that point the retrieval and cleaning should become the repository's usual notebook pair | No |
| **Notebook pair** (`alternatives-retrieval.ipynb` and `alternatives-analysis.ipynb`) | Every other folder in this repository splits fetch-and-tidy from read-and-argue. This one has no argument yet | A column question firm enough to write an analysis notebook against | No |
| **Non-public and home-based education** | CDE publishes both, and both bear on where pupils went when a school closed | The closure analysis showing an unexplained outflow | No |
| **Deposit for a DOI** | Premature for an archive that does not exist | The archive being finished and cited by the column | No |

## Tracking — the current task

From `TASK.md`. These are the assignable pieces of the work this folder proposes.

- [ ] **A** — audit all 26 Artemis year indexes, both CDE archive pages, the staff series and CCD; produce `audit/inventory.csv` and `audit/coverage.md`
- [ ] **A2** — open every staff ratio report and record whether it is school grain or district grain; the titles are not reliable
- [ ] **R** — retrieval with URL discovery, checksummed manifest, and backoff on the Artemis host
- [x] **O (1986)** — re-OCR the 1986 yearbook; 48 pages, 35.25 cents, row totals verified
- [ ] **O (1987–1999)** — running; `audit/ocr-run.log` has the transcript
- [ ] **C** — the eleven cleaning rules in `TASK.md`, each traceable to an audit finding
- [ ] **C9** — extract the 2000–2002 born-digital PDFs by character position; this is the hardest single piece
- [ ] **S** — school registry and auto-labelled closures
- [ ] **V** — reconciliation, reproducing the 2013 benchmark, and `audit/validation.md`
- [ ] **DATA-DICTIONARY** — replace the planned schema with the built one

## Open questions

- Has CCD released 2024 since the audit? If so the overlap extends by a year and `V2` relaxes.
- Do the yearbook table headings drift enough across fourteen volumes to defeat the page-selection patterns in `datalab-ocr.py`? The per-volume `index.json` will show it.
- Is a four-digit CDE school code ever reused across districts within one year? The registry keys on the NCES id so that it does not matter, but the answer changes how much the CDE code can be trusted as a join key elsewhere.
