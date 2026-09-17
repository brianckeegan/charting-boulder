# 2026-10-alternatives

## Question

Which Colorado schools have closed, when, and where were they? And what would a steady-state distribution of schools look like under the State Demography Office's forecasts to 2050 and 2060?

Boulder Valley's Resilient Schools proposal treats four closures as a local problem with a local answer. Colorado has been closing and opening schools for forty years. The archive built here is the evidence base for asking whether Boulder's situation is unusual, and for modelling what a district that stopped losing pupils would actually look like.

## Status

**The archive is built.** The school panel runs 1986–2024 and the district panel reaches back to 1977-78. The scanned yearbook tier is still being converted, so the district tier grows as volumes land.

| | |
|---|---|
| School × year × grade | 647,881 rows, 1986–2024 |
| School × year | 65,841 rows |
| School registry | 2,723 schools with auto-labelled closures |
| District × year × grade | 77,377 rows |
| District × year (trends) | reaches back to **1977-78** |

`audit/validation.md` is the report the pipeline writes about itself, failures included. Do not trust this table over that one — it is regenerated from the data.

## Layout

```
2026-10-alternatives/
├── TASK.md                 the task this folder carries out
├── DATA-DICTIONARY.md      the schema, as built
├── decision-log.md         dated decisions and why
├── ROADMAP.md              what is deliberately deferred, and to when
├── pipeline/
│   ├── sources.py          discover every published file -> data/lookups/inventory.csv
│   ├── fetch.py            download what the inventory says is needed, with a manifest
│   ├── schema.py           canonical grades, code padding, missing-value rules
│   ├── extract.py          one parser per source shape
│   ├── normalize.py        harmonize, join, build the registry, reconcile
│   └── audit.py            write audit/validation.md from the pipeline's own output
├── datalab-ocr.py          re-OCR the scanned yearbooks through the Datalab API
├── proof-run.py            the original three-year probe, kept as the audit's evidence
├── audit/
│   ├── validation.md       the report the pipeline writes about itself
│   ├── proof-run.md        the sixteen audit findings, in prose
│   ├── row-totals.json     yearbook checksum results per volume
│   └── *.log               job transcripts
└── data/
    ├── raw/                originals as downloaded; never edited
    │   ├── cde/            56 CDE spreadsheets and PDFs, with manifest.json
    │   ├── ccd/            NCES API responses (not committed; re-downloadable)
    │   └── yearbooks/      scanned volumes (not committed; 110 MB each)
    ├── interim/            the OCR markdown, one file per converted page
    ├── lookups/            inventory, coverage, district crosswalk
    └── processed/          the archive
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

The pipeline, end to end. No key needed — every source but the yearbook re-OCR is open:

```
pip install pandas openpyxl xlrd
python3 -m pipeline.sources      # what exists  -> data/lookups/inventory.csv
python3 -m pipeline.fetch        # download it  -> data/raw/cde/ + manifest
python3 -m pipeline.normalize    # harmonize    -> data/processed/
python3 -m pipeline.audit        # check it     -> audit/validation.md
```

The yearbook re-OCR needs a [Datalab](https://www.datalab.to/) key, and costs about 0.75 cents a page:

```
export DATALAB_API_KEY=...
python3 datalab-ocr.py                 # all volumes, 1986-1999
python3 audit/check-row-totals.py      # verify them against their printed totals
```

Every step is resumable: a file already downloaded, or a page already converted, is skipped.

## Limitations

Fuller detail, and the per-column missingness, is in `DATA-DICTIONARY.md`.

- Nothing here is causal, and nothing here is a forecast. The archive is a count of pupils and teachers by school and year.
- A school's disappearance from the panel is auto-labelled and never hand-checked, so the closure count is approximate everywhere. A closure, a merger, a rename and a code change can look alike from the data.
- CDE's count is a single October day, and CCD's is collected on its own basis. The two agree closely but are not the same measurement.
- Pre-kindergarten exists on the CDE side only.
- School coordinates come from a recent directory carried backward. A school that moved buildings carries its later location.
- CDE publishes no machine-readable school-grain file before 2004. For 1986–2003 the school panel is NCES CCD alone, with no second source to check it against.
- The 2003 file uses an indented panel layout the parser does not read; 2001 and 2002 are PDF only. Those three years are CCD-only as a result.
- From 2021 the two sources diverge by 6,000 to 16,000 pupils. The gap is concentrated in multi-district online and charter schools, which CDE reports centrally and CCD attributes differently; before 2021 the two agree to within a few hundred.
- County is not district, and district is not attendance area. None of these boundaries nest cleanly.

## Column

*Not yet drafted. The archive comes first.*
