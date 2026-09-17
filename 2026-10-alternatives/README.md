# 2026-10-alternatives

## Question

Which Colorado schools have closed, when, and where were they? And what would a steady-state distribution of schools look like under the State Demography Office's forecasts to 2050 and 2060?

Boulder Valley's Resilient Schools proposal treats four closures as a local problem with a local answer. Colorado has been closing and opening schools for forty years. The archive built here is the evidence base for asking whether Boulder's situation is unusual, and for modelling what a district that stopped losing pupils would actually look like.

## Status

**Early. The archive does not exist yet.** This folder currently holds the proposal for building it, and the audit evidence the proposal rests on.

- `TASK.md` — the proposed audit, retrieval and cleaning task
- `audit/proof-run.md` — sixteen findings, each established by fetching and parsing a real file
- `proof-run.py` — the probe that produced them, for 2001, 2013 and 2024
- `datalab-ocr.py` — re-OCR of the scanned 1986–1999 yearbooks; 1986 complete, the rest running

## Layout

```
2026-10-alternatives/
├── TASK.md                 the proposed task: audit, retrieval, cleaning
├── DATA-DICTIONARY.md      the schema the task is to produce
├── decision-log.md         dated decisions and why
├── ROADMAP.md              what is deliberately deferred, and to when
├── proof-run.py            probe: three years, both sources, harmonized and compared
├── datalab-ocr.py          re-OCR the scanned yearbooks through the Datalab API
├── audit/
│   ├── proof-run.md        the findings, in prose
│   ├── proof-run.json      the same findings, machine-readable
│   └── ocr-run.log         the OCR job's transcript
└── data/
    ├── raw/                originals as downloaded; never edited
    │   ├── manifest.json   url, bytes, sha256, fetched-at for every file
    │   └── yearbooks/      scanned volumes (not committed; large, re-downloadable)
    ├── interim/            harmonized per-year tables and the OCR markdown
    └── processed/          the archive itself — empty until the task runs
```

## Data

| Dataset | Source | Access | Grain and years |
|---|---|---|---|
| Fall pupil membership by school and grade | [CDE Artemis ED5/90.17](https://spl.cde.state.co.us/artemis/edserials/ed59017internet/) | Committed originals | School × grade, 2000–2024 |
| Pupil membership, current era | [CDE pupil-membership archives](https://ed.cde.state.co.us/cdereval/pupilmembership-statistics/data-insights-resources-archives) | Committed originals | School × grade, 2019–2025 |
| Pupil membership and related information | [CDE Artemis ED2/79.19](https://spl.cde.state.co.us/artemis/edserials/ed27919internet/) | Re-OCR'd; PDFs not committed | District × grade, 1986–1999; district trends from 1977-78 |
| School and district staff statistics | [CDE Artemis ED2.88](https://spl.cde.state.co.us/artemis/edserials/ed288internet/) and [CDE staff statistics](https://ed.cde.state.co.us/cdereval/staffstatistics) | Committed originals | Teacher FTE by school, about 2013–2025; by district, 1986–2025 |
| Common Core of Data | [NCES](https://nces.ed.gov/ccd/), via the [Urban Institute Education Data API](https://educationdata.urban.org/) | API; responses not committed | School enrollment by grade, teacher FTE, coordinates, charter flag, status, 1986–2023 |

CDE is the count of record wherever it publishes. CCD is harmonized alongside it and compared school by school, never silently substituted.

## What the audit established

The full list is in `audit/proof-run.md`. The findings that most change the work:

- **The 1986–1999 yearbooks have no school-level table.** Every table in them is by district. Those fourteen years cannot feed a school-level archive at all, whatever is done about the OCR.
- **But they reach back further than expected.** The 1986 volume's Table 4 is a ten-year district panel, 1977-78 to 1986-87, on four measures. That extends the district tier nine years earlier than the series' own start.
- **The scans' embedded OCR keeps words and loses numbers.** The district-by-grade table recovers 3.9% of its cells; the staff table recovers none. Re-OCR through Datalab returns the complete grid, and the tables' own printed row totals prove it: `HARRISON 2` sums across sixteen cells to exactly the printed 9,463.
- **CDE and NCES agree to 0.03%.** In 2013, school by school, 1,781 of 1,826 schools matched and 1,257 agreed exactly. The statewide gap is 31,967 pupils — of which 31,741 is pre-kindergarten, which CCD does not publish for Colorado. Excluding it, the gap is 226.
- **Teacher FTE at school grain is much younger than enrollment.** Roughly 2013 onward on the CDE side, and not in every year. CCD carries it from 1986, which is the main reason CCD is in the archive at all.

## Reproduce

The probe, which needs no key:

```
pip install pandas openpyxl xlrd
python3 proof-run.py
```

The re-OCR, which needs a [Datalab](https://www.datalab.to/) key:

```
export DATALAB_API_KEY=...
python3 datalab-ocr.py            # all volumes, 1986-1999
python3 datalab-ocr.py 1986       # one volume
```

Both are resumable: a file already downloaded, or a page already converted, is skipped.

## Limitations

These apply to the archive as designed, and will move into the data dictionary as it is built.

- Nothing here is causal, and nothing here is a forecast. The archive is a count of pupils and teachers by school and year.
- A school's disappearance from the panel is auto-labelled and never hand-checked, so the closure count is approximate everywhere. A closure, a merger, a rename and a code change can look alike from the data.
- CDE's count is a single October day, and CCD's is collected on its own basis. The two agree closely but are not the same measurement.
- Pre-kindergarten exists on the CDE side only.
- School coordinates come from a recent directory carried backward. A school that moved buildings carries its later location.
- The 2000–2002 school tables are extracted from PDFs and may not reach the accuracy of the spreadsheet years.
- County is not district, and district is not attendance area. None of these boundaries nest cleanly.

## Column

*Not yet drafted. The archive comes first.*
