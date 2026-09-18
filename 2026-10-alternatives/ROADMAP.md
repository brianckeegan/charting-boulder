# Roadmap

What is deliberately not being built now, why, and what would bring it forward. A named deferred concern is worth more than an unmaintained file.

## Deferred work

| Item | Why deferred | What brings it forward | Blocking? |
|---|---|---|---|
| ~~**The steady-state model**~~ | **Done.** `alternatives-analysis.ipynb` fits staffing and school counts on county 5-17 population across 178 districts and carries Boulder Valley to 2060. What remains deferred is the *statewide* version — every district's steady state, not just one | A question that needs the whole state rather than Boulder | No |
| **Current use of closed buildings** | Exists in no education dataset. Needs county assessor records, district property lists and local news, with a hand check and a citation per row | A decision that the column needs it, and a bounded geography — Boulder County alone is perhaps forty buildings, statewide is thousands | No |
| **Hand-verified closures** | Larger than the rest of the task combined. See `decision-log.md`, D6 | A finding that rests on a specific building, rather than on the shape of the distribution | No |
| **Attendance-area boundaries** | Would let enrollment be tied to where pupils live rather than where they are taught. CDE does not publish historical boundaries; districts publish them inconsistently | The column needing a residence-side question | No |
| **L2: pipeline-as-code, pinned environment, CI** | The cleaning rules are not settled. A Snakefile written now would be rewritten during Phase C | Phase C finishing. At that point the retrieval and cleaning should become the repository's usual notebook pair | No |
| ~~**Notebook pair**~~ | **Done.** `alternatives-retrieval.ipynb` and `alternatives-analysis.ipynb`, following the repository's split | — | No |
| **Non-public and home-based education** | CDE publishes both, and both bear on where pupils went when a school closed | The closure analysis showing an unexplained outflow | No |
| **Deposit for a DOI** | Premature for an archive that does not exist | The archive being finished and cited by the column | No |

## Tracking — the current task

From `TASK.md`. These are the assignable pieces of the work this folder proposes. Ticked once the built thing exists and has been checked, not once it was attempted.

- [x] **A** — audit the Artemis year indexes, both CDE archive pages, the staff series and CCD; 1,511 published files in `data/lookups/inventory.csv`
- [x] **A2** — open every staff ratio report and record whether it is school grain or district grain; the titles were not reliable, and reading the files instead took the CDE teacher series from three years to twenty-two
- [x] **R** — retrieval with URL discovery, a checksummed manifest and backoff
- [x] **O (1986)** — re-OCR the 1986 yearbook; 48 pages, 35.25 cents, row totals verified
- [x] **O (1987–1999)** — all fourteen volumes converted; `audit/ocr-run.log` has the transcript
- [x] **C** — the cleaning rules, each traceable to an audit finding
- [x] **C9** — extract the born-digital PDFs by character position. Done for the staff serial, 2000–2019. The membership serial's 2000–2002 and 2004 ratio PDFs still extract no text
- [x] **S** — school registry and auto-labelled closures
- [x] **V** — reconciliation and `audit/validation.md`, regenerated from the data
- [x] **DATA-DICTIONARY** — the built schema, not the planned one

## Open questions

- Has CCD released 2024 since the audit? If so the overlap extends by a year and `V2` relaxes.
- Do the yearbook table headings drift enough across fourteen volumes to defeat the page-selection patterns in `datalab-ocr.py`? The per-volume `index.json` will show it.
- Is a four-digit CDE school code ever reused across districts within one year? The registry keys on the NCES id so that it does not matter, but the answer changes how much the CDE code can be trusted as a join key elsewhere.

## Added after the build — 2026-09-17

- [x] **The teacher-FTE PDFs** — done. The CDE school-grain series went from three years to eleven: 2003, 2004, 2013–2016, 2018, 2019, 2022–2024. A district series from NCES, 1987–2024, came with it.
- [x] **2005–2012 teacher FTE** — done, and 2000–2004 with it. The CDE school-grain series now runs 2000–2024, twenty-two years. No OCR was needed: the text was there all along behind a rotated page, an unhandled line operator and a page whose content is split across several stream objects.
- [x] **District-grain teacher FTE from CDE** — done. `district-teacher-fte-cde.csv` is 4,037 rows over 2000–2024, carrying CDE's own district total where it publishes one and the sum of the district's schools everywhere.
- [ ] **The average-salary reports** — CDE publishes an average teacher salary by district every year from 2000, and the 2016–2019 editions carry a district Total FTE beside it, which would be a third reading of district staffing. They are not parsed: the rows split across two lines with the figures drawn before the district they belong to, and unlike the ratio reports there is no third printed number to check a pairing against. The 2022 and 2024 spreadsheets are the easy ones — a two-row header over `All Schools: Total FTE` and `Average Salary`.
- [ ] **The membership-serial ratio PDFs for 2000–2002 and 2004** — still extract no text at all, and 2003's and 2012's staff reports lose about 200 rows each. Every one of those years is covered by the other serial, so this buys a second reading rather than a year.
- [x] **The yearbooks' summary table** — done. Printed as Table 1 in some volumes and Table 2 in others, which is why the roadmap had the number wrong. It gives district staffing and school counts for 1986–1999 and takes `district-teacher-fte-cde.csv` from 4,037 rows to 6,695, spanning 1986–2024. Every year from 1987 to 1998 reconciles to NCES within 1.3%.
- [ ] **1988** — the one yearbook volume whose *enrollment* does not reconcile against NCES, at −0.70%, with three genuine row-total failures. Every other volume is within 0.16%. Its staffing, read from a different table in the same volume, reconciles at +0.7%, so whatever is wrong is in the by-grade table rather than the scan.
- [ ] **Graduation and dropout rates, 1986–1999** — parsed and carried in `district-teacher-fte-cde.csv`, but **unchecked**: no second source in this archive holds them. CDE publishes dropout and graduation series separately, which would give them the same treatment every other column here gets.
- [ ] **The 384 unmatched yearbook district-years** — no CDE district code, because 172 are BOCES and the rest renamed before 2000 (Northglenn-Thornton 12 is Adams 12 Five Star Schools now). A hand-built rename crosswalk would close most of it; the names and counties are already carried, so nothing is lost meanwhile.
- [ ] **2001–2003 on the CDE side** — 2001 and 2002 are PDF-only, 2003 uses an indented panel layout. NCES covers those years, so this buys a second source rather than filling a hole.

## Added after the analysis — 2026-09-18

- [x] **The Resilient Schools proposal** — supplied by hand and committed to `data/raw/proposal/`: resolution 26-27, the 15 September 2026 work session deck, and the district's own metrics.
- [x] **BVSD capacity by school** — done, from the district's own ArcGIS attendance-area layer rather than the deck, which charts capacity for two schools and tables it for none. The layer carries it for all 31 buildings, at its February 2026 vintage, and the levers are scored against it.
- [x] **City of Boulder neighbourhood boundaries** — supplied by hand as the ten city subcommunities. 16,195 of the district's 41,063 children live inside them; the rest are in Louisville, Lafayette, Superior, Broomfield and the mountains, where the places layer carries the geography.
- [x] **A catchment model that matches both its checks** — closed by dropping the model. Straight-line nearest-school got Mesa within 6% of the district's resident count and Bear Creek at 45%; the district's real attendance-area polygons replaced it, so there is nothing left to check. What remains is the child-to-pupil ratio, still flat district-wide because PL 94-171 gives under-18 by block and no finer.
- [x] **Resident children by single year of age, by block** — done, and better than proposed. The 2020 DHC publishes **P12, sex by age in bands, down to the block**, so the 5-to-17 count per attendance area is measured rather than apportioned: 31,937 of the district's 41,063 under-18s. Every one of the 7,193 blocks agrees with PL 94-171 on population and on under-18 exactly, which is the check on the file offsets. Single years do stop at the tract, so the elementary split is PCT12's tract profile carried onto its blocks, and both a 5-to-10 and a 5-to-11 band are carried because K-5 spans them.
- [x] **Open enrollment in the catchments** — done. `pipeline/oe_matrix.py` reads the three 2025-26 Enrollment Pattern Matrices from `2026-09-bvsd/data/raw/open-enrollment/`, where they were already committed, and all 69 school rows rebuild to their printed totals exactly. Section 4 of the analysis separates a school that is small because its area emptied from one that is small because its families left.
- [x] **Open enrollment as a trend** — done. All thirty matrices, 2016-17 to 2025-26, now read. Neither answer the question offered: the share attending their own neighbourhood school held at about 70% to 2020, broke in 2021, and has fallen every year since to 62.6%. Of the 2,530 pupils the neighbourhood schools have lost, 1,848 are demography and 682 are families leaving.
- [x] **A statewide steady state** — done, in section 6, and the answer is no. Run for all 166 districts on their own county forecasts, Boulder Valley ranks **69th of 166** by implied contraction to 2060; 68 districts face a larger one. Cross-sectionally its average school of 500 pupils is the **8th smallest of the 19 districts with 10,000 pupils or more**, against a peer median of 557. The cross-section deliberately uses no fitted form: over a range from 25 pupils to 90,450 a log-log line puts Denver 60% above its own norm, which says something about the functional form and nothing about Denver.
- [x] **Closure impacts** — done, in section 7. Thirty-three districts have run sixty closure rounds since 1992, Boulder Valley's 2004 among them. A closure round cuts the school count about 17% and holds it 14% down five years on, and moves neither enrolment nor staffing at any horizon, with intervals ruling out an enrolment fall of more than about five per cent. **A closure round changes the number of buildings, not the number of pupils or teachers.**
- [ ] **A closure event study that handles staggered timing** — the comparison group includes districts treated in other years, which biases the average where the effect of a round differs across districts. A Callaway–Sant'Anna or Sun–Abraham estimator would fix it; the finding to check is whether the flat enrolment path survives.
