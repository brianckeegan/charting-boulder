# 2026-10-alternatives

A cleaned archive of Colorado public-school enrollment and teaching staff, built from five published sources spanning 1977 to 2024.

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
| `district-teacher-fte-cde.csv` | 6,695 | **1986–2024** | district × year |

All in `data/processed/`, long format, UTF-8. `DATA-DICTIONARY.md` documents every column; `audit/validation.md` is the report the pipeline writes about itself and is regenerated from the data rather than maintained by hand.

## How good is it

Six checks. Five compare the archive against a source collected independently of the documents being read; the sixth is the archive reading the same printed figures twice.

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

**The yearbooks' district staffing, against NCES.** The summary table in each volume prints classroom teacher FTE by district. Summed and compared with the NCES state total: **every year from 1987 to 1998 lands within 1.3%**, five of them within 0.2%, and 1991 agrees to a fifth of one FTE out of 33,093. 1986 is the one year with nothing to check it against, because NCES district staffing starts in 1987.

**And CDE against itself.** In 2010, 2023 and 2024 CDE publishes district totals as well as school rows, so the schools can be summed and compared with what CDE says the district holds: **551 district-years carry both, and 396 agree to the hundredth of an FTE — all 185 of them in 2023.** The 2010 subtotals also sum to 48,449.1 against the NCES state total of 48,450.

**The modern CDE spreadsheets, against NCES**, school by school. From 2005 to 2020 the two agree to within a few hundred pupils out of 850,000, several years exactly. From 2021 they diverge by 6,000 to 16,000, concentrated in multi-district online and charter schools that CDE reports centrally and NCES attributes differently — a real difference in attribution, not a parse fault.

**And the yearbooks against themselves.** Each yearbook reprints the previous nine years, so most district-years are read twice. **1,267 of 1,269 agree exactly (99.8%)** — two OCR passes over the same printed figures. `district-year-overlap.csv` carries every comparison.

## Sources

| Source | Supplies | Years | Role |
|---|---|---|---|
| [CDE Artemis ED5/90.17](https://spl.cde.state.co.us/artemis/edserials/ed59017internet/) | School enrollment by grade | 2004–2018 | Spine |
| [CDE pupil-membership archives](https://ed.cde.state.co.us/cdereval/pupilmembership-statistics/data-insights-resources-archives) | School enrollment by grade | 2019–2024 | Spine |
| [CDE staff statistics](https://ed.cde.state.co.us/cdereval/staffstatistics) and [Artemis ED2.88](https://spl.cde.state.co.us/artemis/edserials/ed288internet/) | Teacher FTE by school | 2000–2024, twenty-two years | Spine |
| [CDE Artemis ED2/79.19](https://spl.cde.state.co.us/artemis/edserials/ed27919internet/) | District enrollment by grade; district staff and school counts; district trends | 1986–1999, and 1977–1985 via the 1986 volume | District tier |
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

school-teacher-fte.csv           CDE's own staff reports, as published
  year, district_code, district_name, school_code, school_name, county_name,
  teacher_fte, enrollment_reported, pupil_teacher_ratio, source

district-teacher-fte-cde.csv     the district panel, 1986 onward
  year, district_code, district_name, county_name, unit_type,
  teacher_fte_published, teacher_fte_school_sum, teacher_fte_difference,
  staff_certificated_fte, staff_noncertificated_fte, pupil_teacher_ratio,
  schools_published, schools_elementary, schools_middle, schools_senior,
  schools_other, schools_in_sum,
  enrollment_published, enrollment_school_sum,
  graduation_rate, dropout_rate, source

district-teacher-fte-ccd.csv     NCES, and the only staffing series before 2000
  year, leaid, district_code, district_name, teacher_fte,
  teacher_fte_prek, teacher_fte_kindergarten, teacher_fte_elementary,
  teacher_fte_secondary, staff_total_fte, enrollment_reported, source
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
| Teacher FTE by district, CDE | **1986–2024**, except 1999, 181–196 districts a year |
| Schools per district, CDE | **1986–1999**, by level |
| District enrollment by grade | 1986–2024 |
| District fall membership | **1977–2024**, except 2000–2003 |
| Coordinates | 64,744 of 65,841 school-years |
| Graduation and dropout rates by district | 1986–1999, from the same table, **unchecked** |

Four things are missing or thin, and each is here for its own reason:

- **2000–2003 has no district row, and 2001–2003 no CDE school data.** 2001 and 2002 publish school-by-grade as PDF only; 2003 uses an indented panel layout the parser does not read. NCES covers those years at school grain, so the school panel has no hole — it has one source instead of two.
- **2017 teacher FTE does not exist.** CDE publishes the 2016 and 2017 pupil-teacher ratio reports at different URLs, but the files are byte-identical. The later duplicate is dropped rather than presented as a second year. 2020 and 2021 CDE published no ratio report at all.
- **The 2000–2002 and 2004 membership PDFs still read as nothing**, and 2003's and 2012's ratio reports lose about 200 rows each to layouts the parser does not recover. The staff serial covers every one of those years, so no year is missing — but each is one file's reading rather than two.
- **1999 has school counts but no staff.** The 1999 volume prints Fall 1998 teachers beside Fall 1999 pupils, so its staffing belongs to 1998 and is filed there. No volume publishes 1999 staffing, and CDE's own staff serial starts in 2000, so the CDE teacher series has a one-year hole at 1999. NCES covers it.
- **Fourteen per cent of the yearbook district-years carry no CDE district code.** Names are matched to codes and 2,275 of 2,659 match; the residue is 172 BOCES, which have no district code, and about 210 district-years whose names changed before 2000 — Northglenn-Thornton 12 is Adams 12 Five Star Schools now. Those rows keep their printed name and county and are usable; only the code is missing.

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
├── decision-log.md         twenty-four dated decisions and why
├── ROADMAP.md              what is deferred, and to when
├── CHANGELOG.md            what changed, and what broke on the way
├── pipeline/
│   ├── sources.py          discover what exists  -> data/lookups/inventory.csv
│   ├── fetch.py            download what is needed, with a checksummed manifest
│   ├── schema.py           canonical grades, code padding, missing-value rules
│   ├── extract.py          one parser per source shape, including the
│   │                    yearbooks' district summary table
│   ├── normalize.py        harmonize, join, build the registry, reconcile
│   ├── teacher_fte.py      the staff reports, both grains -> three FTE tables
│   ├── oe_matrix.py        BVSD's Enrollment Pattern Matrices, ten years of
│   │                    them, read by searching for the arrangement that
│   │                    satisfies each matrix's own arithmetic
│   └── audit.py            write audit/validation.md from the pipeline's output
├── alternatives-retrieval.ipynb  fetch + tidy  -> data/analysis/
├── alternatives-analysis.ipynb   read + argue  -> output/
├── datalab-ocr.py          re-OCR the scanned yearbooks through the Datalab API
├── proof-run.py            the original three-year probe, kept as the audit's evidence
├── audit/
│   ├── validation.md       the report the pipeline writes about itself
│   ├── proof-run.md        the sixteen findings the task was designed against
│   ├── check-row-totals.py the yearbook checksum, as a reusable check
│   ├── row-totals.json     its results per volume
│   ├── teacher-fte-parse.json  rows kept, rows dropped and why, per staff file
│   └── teacher-fte.log     the transcript of the staff run
└── data/
    ├── raw/cde/            56 CDE originals with manifest.json (sha256, URL, date)
    ├── raw/fte/            36 CDE staff reports, likewise
    ├── raw/ccd/            NCES API responses (not committed; re-downloadable)
    ├── raw/yearbooks/      scanned volumes (not committed; 110 MB each)
    ├── interim/yearbooks/  the OCR markdown, one file per converted page
    ├── raw/geo/            census TIGER, PL 94-171 and the 2020 DHC, with
    │                       manifest.json (not committed; re-downloadable)
    ├── raw/proposal/       resolution 26-27, the work session deck, the
    │                       2025-26 school profiles, and Boulder's
    │                       subcommunity boundaries, with checksums
    ├── raw/geo/bvsd/       the district's attendance areas, capacities and
    │                       school locations, from its ArcGIS services
    ├── lookups/            inventory, coverage map, district and county crosswalks
    ├── analysis/           the working set the notebooks build on
    └── processed/          the archive
```

## The analysis

Two notebooks, following the split every other folder in this repository uses.
`alternatives-retrieval.ipynb` may fetch, reshape, join and check; it may not
compute a measure the analysis reports. `alternatives-analysis.ipynb` reads
`data/analysis/`, makes no network call, and does everything else.

They ask three questions about Boulder Valley's Resilient Schools proposal,
and ignore its finances entirely — the question here is whether there are
enough children.

**1. Has this happened before?** Colorado opened 1,397 schools and closed 651
between 1987 and 2023; closure is a rate, not an event. A school that closes
is already half the size of a typical school five years out, and a third the
size a year out. Halving a school's enrollment roughly doubles the odds it is
gone within two years, while its recent trend adds nothing once size is known.
**Boulder Valley has done this before**: it ran 60 schools in 2000 and 53 by
2004.

**2. How many schools does the demography support?** Fitted across 178
Colorado districts over 35 years rather than Boulder's own history, with
district fixed effects. A district that loses 10% of its school-age population
ends up with **7.6% fewer teachers and 4.4% fewer schools** — Colorado
districts have consistently chosen smaller schools over fewer schools. Boulder
County's 5-to-17 population falls to about 2030 and is then flat for thirty
years, which puts Boulder Valley near 53 schools in 2060 against 56 today.
**The decline is front-loaded, not continuing.**

**3. What are the options?** Five levers, each judged on what it is trying to
do rather than against one scorecard: close, reconfigure grades, redraw
boundaries, shrink in place, do nothing. Two viability bars are carried
throughout, and **they land in the same place** — BVSD's two-classes-a-grade
standard is about 300 pupils, which is also where Colorado's observed closure
rate flattens. The district's standard is not unusual.

Built on the district's own attendance areas and capacities, taken from the
three BVSD ArcGIS web maps (last edited 20 February 2026 — the vintage the
proposal was drawn against), and scored against the resolution and the
15 September 2026 work session in `data/raw/proposal/`.

**The archive counts 14 elementary schools below the bar. So does BVSD.** Two
readings of the same district from different data, landing on the same number.

| | buildings | below the bar | pupils moved |
|---|---:|---:|---:|
| Today | 26 | 14 | — |
| The proposal | 22 | 8 | 952 |
| Redraw to capacity, close nothing | 26 | 9 | 694 |

Those two rows are the same answer by different means. The proposal gets one
more school over the bar; redrawing moves 258 fewer children and closes
nothing.

Neither reaches the standard, because **nothing does**. Closing until every
school clears 300 pupils takes twelve closures and leaves the district at
**104% of its own capacity** with eight schools overfull. The bar cannot be
met by closing.

Redrawing attendance boundaries on its own is not among the six options the
board was given (work session, slide 7). It appears six times in the
resolution, always as a consequence of a closure, never as an alternative to
one.

Eleven per cent of the district's children live in an area that loses its
school — concentrated outside the City of Boulder and on University Hill.

**4. Why is a school small?** Every catchment model above assumes a child
attends the school whose area they live in. A third of Boulder Valley's pupils
do not, and the district publishes exactly who: an Enrollment Pattern Matrix
per level, every attendance area against every school. All 69 school rows in
the three 2025-26 matrices rebuild to their printed totals exactly, so this is
the district's own arithmetic rather than an inference from it.

It draws a distinction the proposal does not. **A school can be small because
few children live in its area, or because the children who live there go
elsewhere.** Only the first is demographic, and only the first is fixed by
closing a building. The four closing elementary areas are on the demographic
side — a median of 228 children against 324 for those staying open — and that
case holds. But **the five areas whose families leave most are all staying
open**, and 1,246 children live in them and attend school somewhere else.
Sanchez has 642 children in its area, 276 in its school and 378 going
elsewhere: the largest single pool of pupils the district is not capturing, in
a school below the bar that is not on the list. Across every elementary area,
2,915 children open-enrol out against 7,223 places filled.

**5. Has this been going on long?** The district has published the same matrix
every year since 2016-17, and all ten are read here, so the question the
proposal turns on can be answered rather than assumed. The share of Boulder
Valley's elementary children attending their own neighbourhood school **sat
flat at about 70% from 2017 to 2020**, fell four points in 2021, recovered
half of that in 2022, and has fallen every year since — to **62.6%**. The
proposal did not start it; neither is it a decade of steady decline.

What that costs is arithmetic. Between 2017 and 2026 the children living in an
elementary attendance area fell 22%, from 12,296 to 9,645. The roll of the
neighbourhood schools fell **30%**, from 8,570 to 6,040. Had the 2017 share
held, today's children would fill 6,722 places instead of 6,040, so of the
2,530 pupils lost, **1,848 are demography and 682 are families leaving** —
about a quarter. **16 of 30 areas have lost more than five points of their
catchment**; the three worst are Monarch K-8 (−25), Whittier (−23) and
Eldorado K-8 (−15), and none of them is closing.

**6. Is Boulder unusual?** The model in question 2 is fitted on 178 districts
and was applied to one; here it is applied to all of them, on each district's
own county forecast. **Boulder Valley ranks 69th of 166 by the contraction its
demography implies — 68 Colorado districts face a larger one.** Its county's
5-to-17 population falls 13% to 2060 against a statewide median of 9%, and its
own school count comes out 2% lower.

The second reading is cross-sectional, and it needs no model: among the **19
Colorado districts with 10,000 pupils or more**, Boulder Valley's average
school of 500 pupils is the **8th smallest**, against a peer median of 557.
Seven large districts run smaller schools, Denver (459) and Colorado Springs 11
(377) among them. Colorado Springs runs fifty-nine schools at an average
seventy-seven pupils *below* Boulder Valley's viability bar.

Neither reading makes Boulder Valley an outlier. That cuts against two things
the proposal leans on: that the district faces a decline out of proportion to
the state, and that a district of its size cannot run schools of the size it
has. What it does not settle is whether it *should* — a peer median describes
what districts do, not what is right, and the bar the levers are scored against
remains BVSD's own.

**7. What happened after?** Question 1 asked what predicts a closure; it did
not ask what a closure does, and the proposal's case rests on an answer.
Thirty-three Colorado districts have run a closure round since 1992 — two or
more schools at once, amounting to between a twentieth and a half of the
district — and
**Boulder Valley's own 2004 round, five schools of fifty-eight, is one of
them.** An event study with district and year fixed effects says:

| | at the round | five years later |
|---|---:|---:|
| Schools | **−17%** | **−14%** |
| Enrolment | −2% (n.s.) | +4% (n.s.) |
| Staff | +2% (n.s.) | +7% (n.s.) |

**A closure round changes the number of buildings, not the number of pupils or
the number of teachers.** The closures hold — districts do not quietly reopen
what they shut — but no horizon shows enrolment or staffing differing from the
year before the round, and the intervals rule out an enrolment fall of more
than about five per cent. Whatever case there is for closing schools is a case
about buildings.

Boulder Valley's own round says the same in one district. It closed five
schools in 2004 and by 2012 was **back to fifty-six schools with two thousand
more pupils** than it had at the round; fifty-seven by 2013, where it had been
in 1999. That is not a prediction — the SDO says Boulder County's children do
not come back this time — but it is what a closure round settled last time,
which is less than the proposal implies.

**How many children the district has at all.** The census counts children and
the matrices count pupils, and the 2020 census and the 2019-20 matrix describe
the same months, so the two can be compared without extrapolating. Across the
22 areas with both, **BVSD enrolled 9,560 of the children living in them**
against 11,166 aged 5 to 10 or 13,178 aged 5 to 11 — 86% or 73%, depending
where the elementary band is drawn. The level moves with the band and the
ranking does not (Spearman 0.98), so what this measures is the spread:
Flatirons and Heatherwood sit near the bottom on either reading, and their
children are not in the district's schools at all rather than in a different
one of them.

### What the analysis is missing

**Capacity is February 2026; enrollment is not.** The attendance-area layer's
own enrollment field gives a district utilisation of 86%, the work session
says 68%, and the archive's K–5 enrollment over that capacity gives 62%. The
three disagree school by school. Capacity is a building's size and moves
slowly, so it is the field taken from the layer; the enrollment on top of it
is the archive's.

**Redrawing is modelled as proportional to capacity, not as real lines.** What
it establishes is a ceiling — what the existing buildings could hold — not a
map. An actual redraw is constrained by geography this model does not see.

**Open enrollment is measured, not modelled.** Sections 4 and 5 read where
pupils actually go, for ten years, but the five levers in section 3 are still
resident-based: they move catchment lines, not the choices families make
inside them, and nothing here says how families would choose again under
different schools. **The elementary age band is approximate.** 5-to-17 is exact per block from
the 2020 DHC, but single years of age stop at the tract, so the elementary
split is a tract profile carried onto its blocks — and K-5 spans ages 5 to 11
with the ends only partly in it. Both bands are carried throughout.

**Focus schools have no catchment** and the proposal moves
three of them. `data/analysis/known-gaps.csv` carries the rest.

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

The analysis runs on top of it, and needs `geopandas`, `matplotlib` and
`statsmodels` as well:

```
pip install geopandas matplotlib statsmodels
jupyter execute alternatives-retrieval.ipynb   # -> data/analysis/
jupyter execute alternatives-analysis.ipynb    # -> output/
```

The retrieval notebook reads two files from the folder next door rather than
copying them: the State Demography Office's single-year-of-age county file in
`2026-09-bvsd/data/raw/sdo/`, and the 2025-26 Enrollment Pattern Matrices in
`2026-09-bvsd/data/raw/open-enrollment/`. Both are committed there with their
URLs and checksums. It needs the whole repository, not this folder alone.

The order of the last three matters. `teacher_fte` writes the district staffing table for 2000 onward; `normalize` extends it back to 1986 from the yearbooks, where the district name crosswalk lives. Running `normalize` alone leaves the yearbook era in place but stale; running `teacher_fte` alone truncates the table to 2000.

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
- **A teacher is not the same thing in both sources.** CDE's staff reports run 0.7% to 4.4% below the NCES state total in every one of the twenty-two years, always in the same direction. That is a definitional difference, not a parse fault, and it means the two teacher columns should not be differenced.
- **A district's teachers can be counted two ways**, and `district-teacher-fte-cde.csv` keeps both rather than choosing: what CDE states the district holds, where it says so, and what its schools add up to. They agree exactly in 396 of the 551 district-years where both exist. Where they differ the published figure is usually larger, because online and charter schools are reported centrally in some years and to the school in others.
- County is not district, and district is not attendance area. None of these boundaries nest.

## A note on checking

Every bug that surfaced building this produced plausible output. A header read as `1.0` filed first-graders as grade 10. A `STATE TOTALS` row doubled the state in the 2010 CDE file and again in three yearbook volumes. Page selection skipped continuation pages, losing half the districts in a volume. Two columns headed `District Code` collapsed 2006 to a single district. A district code column headed `LEA` rather than `LEA Code` went unmatched, so every district in two years collapsed onto one key and the table came out as a single row holding the state total. None of these announced itself.

**Row-total checksums caught none of the worst four.** An aggregate row sums correctly against itself, and a page never converted cannot fail a test it is never given. Only comparison against an independently collected source exposed them — which is why `district-reconciliation.csv` and `source-reconciliation.csv` are pipeline outputs rather than something done once by hand.

**Three times, a bug was written down as a property of the source.** Eight years of teacher FTE were recorded here as unparseable, needing a paid OCR pass, on the strength of what the extractor returned. The text was in the files all along, behind a rotated page and an unhandled line operator. And a district table of seventeen rows — thirteen of them schools — was described as thin coverage, because seventeen rows over nine years looks like a source that publishes little rather than like a parser that dropped almost everything.

And the yearbooks' staff table was recorded as unparsed for want of a parser, which was true — but writing one turned up the same page-selection fault the OCR step had already been fixed for, one layer further down: two pages whose running head the OCR could not read were skipped, costing two volumes thirty districts each, and a volume that renames the table was lost whole.

All three were found by asking whether a number was the size it ought to be, which is a question a checksum cannot ask. **A stated limitation deserves the same scepticism as a stated figure.**

## Column

*Not yet drafted. The archive comes first.*
