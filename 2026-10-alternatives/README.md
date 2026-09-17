# 2026-10-alternatives

A cleaned archive of Colorado public-school enrollment and teaching staff, built from four sources spanning 1977 to 2024.

## Question

Which Colorado schools have closed, when, and where were they? And what would a steady-state distribution of schools look like under the State Demography Office's forecasts to 2050 and 2060?

Boulder Valley's Resilient Schools proposal treats four closures as a local problem with a local answer. Colorado has been opening and closing schools for forty years. This archive is the evidence base for asking whether Boulder's situation is unusual, and for modelling what a district that stopped losing pupils would look like. The model itself is a separate task (`ROADMAP.md`); the archive is shaped to feed it.

## What is here

| Table | Rows | Span | Grain |
|---|---:|---|---|
| `school-enrollment-by-grade.csv` | 647,881 | 1986–2024 | school × year × grade |
| `school-year.csv` | 65,841 | 1986–2024 | school × year |
| `schools.csv` | 2,723 | — | school |
| `district-enrollment-by-grade.csv` | 93,326 | 1986–2024 | district × year × grade |
| `district-year.csv` | 7,852 | **1977–2024** | district × year |
| `source-reconciliation.csv` | 21 | 2004–2024 | year |
| `district-reconciliation.csv` | 14 | 1986–1999 | year |
| `district-year-overlap.csv` | 1,269 | 1977–1987 | district × year |
| `school-teacher-fte.csv` | 38,777 | 2000–2024 | school × year |
| `district-teacher-fte-ccd.csv` | 7,879 | **1987–2024** | district × year |
| `district-teacher-fte-cde.csv` | 4,037 | 2000–2024 | district × year |

All in `data/processed/`, long format, UTF-8. `DATA-DICTIONARY.md` documents every column; `audit/validation.md` is the report the pipeline writes about itself and is regenerated from the data rather than maintained by hand.

## How good is it

Two checks, both against sources collected independently of the documents being read.

**The scanned 1986–1999 yearbooks, against NCES.** Each volume's numbered grades summed and compared:

| Year | Diff | Year | Diff | Year | Diff |
|---|---:|---|---:|---|---:|
| 1986 | +261 | 1991 | +5 | 1996 | **0** |
| 1987 | +861 | 1992 | **0** | 1997 | **0** |
| 1988 | **−3,842** | 1993 | **0** | 1998 | **0** |
| 1989 | +152 | 1994 | **0** | 1999 | **0** |
| 1990 | **0** | 1995 | +42 | | |

Eight volumes agree to the pupil. All but 1988 land within 0.16%. **1988 is the one weak volume**, at −0.70% with three genuine row-total failures; treat it with more caution than the rest.

**Teacher FTE, against NCES**, year by year. Every one of the twenty-two CDE years lands between 0.7% and 4.4% below the NCES state total, and sixteen of them within 2%. The gap is in the same direction throughout, which is what a consistent difference in what counts as a teacher looks like rather than a parse that comes and goes.

**And CDE against itself.** In 2010, 2023 and 2024 CDE publishes district totals as well as school rows, so the schools can be summed and compared with what CDE says the district holds: **551 district-years carry both, and 396 agree to the hundredth of an FTE — all 185 of them in 2023.**

**The modern CDE spreadsheets, against NCES**, school by school. From 2005 to 2020 the two agree to within a few hundred pupils out of 850,000, several years exactly. From 2021 they diverge by 6,000 to 16,000, concentrated in multi-district online and charter schools that CDE reports centrally and NCES attributes differently — a real difference in attribution, not a parse fault.

**A third check, internal.** Each yearbook reprints the previous nine years, so most district-years are read twice. **1,267 of 1,269 agree exactly (99.8%)** — two OCR passes over the same printed figures. `district-year-overlap.csv` carries every comparison.

## Sources

| Source | Supplies | Years | Role |
|---|---|---|---|
| [CDE Artemis ED5/90.17](https://spl.cde.state.co.us/artemis/edserials/ed59017internet/) | School enrollment by grade | 2004–2018 | Spine |
| [CDE pupil-membership archives](https://ed.cde.state.co.us/cdereval/pupilmembership-statistics/data-insights-resources-archives) | School enrollment by grade | 2019–2024 | Spine |
| [CDE staff statistics](https://ed.cde.state.co.us/cdereval/staffstatistics) and [Artemis ED2.88](https://spl.cde.state.co.us/artemis/edserials/ed288internet/) | Teacher FTE by school | 2000–2024, twenty-two years | Spine |
| [CDE Artemis ED2/79.19](https://spl.cde.state.co.us/artemis/edserials/ed27919internet/) | District enrollment by grade; district trends | 1986–1999, and 1977–1985 via the 1986 volume | District tier |
| [NCES CCD](https://nces.ed.gov/ccd/), via the [Urban Institute API](https://educationdata.urban.org/) | School enrollment by grade, teacher FTE, coordinates, charter flag, status | 1986–2024 | Secondary, harmonized and compared |

CDE is the count of record wherever it publishes. NCES is carried alongside it in its own columns and compared, never silently substituted. The `source` column on every row says which contributed.

## Schema

Full detail in `DATA-DICTIONARY.md`. The shape:

```
school-enrollment-by-grade.csv   the core panel, deliberately narrow
  year, ncessch, school_code, district_code, grade,
  enrollment_cde, enrollment_ccd, source

school-year.csv                  everything that is not per-grade
  year, ncessch, school_code, district_code, school_name, district_name,
  enrollment_total_cde, enrollment_total_ccd,
  teacher_fte_cde, teacher_fte_ccd, enrollment_reported_in_fte_file,
  latitude, longitude, is_charter, status

schools.csv                      the registry, one row per school
  ncessch, school_codes, names, district_codes, first_year, last_year,
  closure_label, closure_confidence, closure_evidence, latitude, longitude

district-year.csv                the longest series, 1977 onward
  year, school_year, district_code, district_name, county_name, unit_type,
  fall_membership, closing_day_membership, average_daily_membership, adae, source
```

Three conventions worth knowing before you join anything:

- **Codes are zero-padded strings.** `0010` is a district; `10.0` is a bug. Read them as text.
- **The grade panel carries no names.** A school has fourteen grade rows a year and its name is identical on all of them, so names live in `school-year.csv`. Join on `(year, school_code)`.
- **`ncessch` is the stable key.** A CDE school code is not unique statewide in every year, and it changes. The NCES id survives renames and recodes, which is what the registry keys on.

## Coverage, honestly

| | |
|---|---|
| School enrollment, CDE | 2004–2024 |
| School enrollment, NCES | 1986–2024 |
| Teacher FTE by school, CDE | **2000–2024**, every year but 2017, 2020 and 2021 |
| Teacher FTE by school, NCES | 1986–2024 |
| **Teacher FTE by district, NCES** | **1987–2024**, with a level breakdown |
| Teacher FTE by district, CDE | **2000–2024**, 181–186 districts a year |
| District enrollment by grade | 1986–2024 |
| District fall membership | **1977–2024**, except 2000–2003 |
| Coordinates | 64,744 of 65,841 school-years |

Two gaps are deliberate and one is not:

- **2000–2003 has no district row, and 2001–2003 no CDE school data.** 2001 and 2002 publish school-by-grade as PDF only; 2003 uses an indented panel layout the parser does not read. NCES covers those years at school grain, so the school panel has no hole — it has one source instead of two.
- **2017 teacher FTE does not exist.** CDE publishes the 2016 and 2017 pupil-teacher ratio reports at different URLs, but the files are byte-identical. The later duplicate is dropped rather than presented as a second year. 2020 and 2021 CDE published no ratio report at all.
- **The 2000–2002 and 2004 membership PDFs still read as nothing**, and 2003's and 2012's ratio reports lose about 200 rows each to layouts the parser does not recover. The staff serial covers every one of those years, so no year is missing — but each is one file's reading rather than two.
- **The yearbooks' Table 1** — school counts, staff, pupil/teacher ratio, dropout rate — is converted and sits in `data/interim/yearbooks/` but is not yet parsed into any table.

## Closures

`schools.csv` labels a school's disappearance from the panel, from the data alone:

| Label | Confidence | Schools |
|---|---|---:|
| still_open | high | 1,934 |
| closed | high | 614 |
| renamed | low | 101 |
| closed | medium | 57 |
| code_changed | low | 17 |

**Never hand-verified**, by decision (`decision-log.md`, D6). A closure, a merger, a rename and a code change can look alike from the data, and the confidence column is the honest part of this table. Anything labelled `low` should be checked before it carries weight.

## Layout

```
2026-10-alternatives/
├── README.md               this file
├── TASK.md                 the task this folder carries out
├── DATA-DICTIONARY.md      every column, its units and its missingness
├── decision-log.md         seventeen dated decisions and why
├── ROADMAP.md              what is deferred, and to when
├── CHANGELOG.md            what changed, and what broke on the way
├── pipeline/
│   ├── sources.py          discover what exists  -> data/lookups/inventory.csv
│   ├── fetch.py            download what is needed, with a checksummed manifest
│   ├── schema.py           canonical grades, code padding, missing-value rules
│   ├── extract.py          one parser per source shape
│   ├── normalize.py        harmonize, join, build the registry, reconcile
│   ├── teacher_fte.py      the staff reports, both grains -> three FTE tables
│   └── audit.py            write audit/validation.md from the pipeline's output
├── datalab-ocr.py          re-OCR the scanned yearbooks through the Datalab API
├── proof-run.py            the original three-year probe, kept as the audit's evidence
├── audit/
│   ├── validation.md       the report the pipeline writes about itself
│   ├── proof-run.md        the sixteen findings the task was designed against
│   ├── check-row-totals.py the yearbook checksum, as a reusable check
│   └── row-totals.json     its results per volume
└── data/
    ├── raw/cde/            56 CDE originals with manifest.json (sha256, URL, date)
    ├── raw/fte/            36 CDE staff reports, likewise
    ├── raw/ccd/            NCES API responses (not committed; re-downloadable)
    ├── raw/yearbooks/      scanned volumes (not committed; 110 MB each)
    ├── interim/yearbooks/  the OCR markdown, one file per converted page
    ├── lookups/            inventory, coverage map, district crosswalk
    └── processed/          the archive
```

## Reproduce

The pipeline needs no key — every source but the yearbook re-OCR is open:

```
pip install pandas openpyxl xlrd
python3 -m pipeline.sources      # what exists  -> data/lookups/inventory.csv
python3 -m pipeline.fetch        # download it  -> data/raw/cde/ + manifest
python3 -m pipeline.teacher_fte  # staffing     -> the three FTE tables
python3 -m pipeline.normalize    # harmonize    -> data/processed/
python3 -m pipeline.audit        # check it     -> audit/validation.md
```

The yearbook re-OCR needs a [Datalab](https://www.datalab.to/) key and costs about 0.75 cents a page — roughly $6 for all fourteen volumes:

```
export DATALAB_API_KEY=...
python3 datalab-ocr.py                 # all volumes, 1986-1999
python3 audit/check-row-totals.py      # verify against their printed totals
```

Every step is resumable: a file already downloaded, or a page already converted, is skipped.

## Limitations

- Nothing here is causal and nothing is a forecast. It is a count of pupils and teachers by school and year.
- **CDE's count is a single October day**; NCES collects on its own basis. They agree closely, but they are not the same measurement.
- **Pre-kindergarten is CDE-only.** NCES publishes no pre-K for Colorado in any year, so `enrollment_ccd` is *missing* for PK, never zero. Colorado's PK is about 31,800 pupils a year, so treating it as zero makes the two sources look irreconcilable when they are not.
- **Kindergarten is a sum.** CDE splits Half-Day K and Full-Day K from about 2014; the archive adds them. The split is not preserved — recover it from `data/raw/cde/`.
- **Coordinates are carried backward** from a recent NCES directory, so a school that moved buildings carries its later location.
- **BOCES are not districts.** Boards of Cooperative Educational Services appear alongside districts in the yearbooks and are flagged `unit_type = 'boces'`, not removed — NCES counts their pupils too, and dropping them breaks four exact reconciliations. Filter to count districts; leave them in to total pupils.
- **71 yearbook rows are short by exactly the ungraded column**, which the OCR drops on some pages. The numbered grades are unaffected.
- County is not district, and district is not attendance area. None of these boundaries nest.

## A note on checking

Ten bugs surfaced building this, and every one produced plausible output. A header read as `1.0` filed first-graders as grade 10. A `STATE TOTALS` row doubled the state in the 2010 CDE file and again in three yearbook volumes. Page selection skipped continuation pages, losing half the districts in a volume. Two columns headed `District Code` collapsed 2006 to a single district. A district code column headed `LEA` rather than `LEA Code` went unmatched, so every district in two years collapsed onto one key and the whole table came out as a single row holding the state total.

**Row-total checksums caught none of the worst four.** An aggregate row sums correctly against itself, and a page never converted cannot fail a test it is never given. Only comparison against an independently collected source exposed them — which is why `district-reconciliation.csv` and `source-reconciliation.csv` are pipeline outputs rather than something done once by hand.

## Column

*Not yet drafted. The archive comes first.*
