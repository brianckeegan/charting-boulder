# Data dictionary

The schema of `data/processed/`, as built. Row counts and year spans are in `audit/validation.md`, which is regenerated from the data itself rather than maintained by hand.

Conventions that hold everywhere in this archive:

- All identifier codes are **zero-padded strings**, never numbers. `0010` is a district, `10.0` is a bug.
- `year` is the **fall of the school year**: 2024 means the 2024-25 count, taken on or about 1 October 2024.
- Missing is empty, never `0` and never `-1`. A zero means a real count of zero.
- Every table carries a `source` column, so a row can always be traced to the file it came from.
- Long format throughout. One row per observation, not one column per year.

## `school-enrollment-by-grade.csv`

The core panel. One row per school per year per grade.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | Fall of the school year |
| `ncessch` | string | NCES school id, 12 characters. The stable key across renames and code changes |
| `school_code` | string | CDE school code, 4 digits. Not unique statewide in every year |
| `district_code` | string | CDE district code, 4 digits. Empty where only CCD covers the year |
| `grade` | string | `PK`, `K`, `1` … `12`. See the grade notes below |
| `enrollment_cde` | integer | CDE October count. Empty where CDE publishes no school-grain file that year |
| `enrollment_ccd` | integer | NCES CCD. Empty before 1986, after 2024, and for `PK` in every year |
| `source` | string | `cde`, `ccd`, or `both` — which sources contributed this cell |

This table is deliberately narrow. Names, district names and coordinates are **not** repeated here; they live in `school-year.csv`, one row per school-year instead of once per grade row. Carrying them on all fourteen grade rows of every school made the file 65 MB and added no information. Join on `(year, school_code)`.

## `school-year.csv`

One row per school per year. Identity, totals and the things that are not per-grade.

| Column | Type | Notes |
|---|---|---|
| `year`, `ncessch`, `school_code`, `district_code` | | As above |
| `school_name` | string | As printed that year. Names change; the registry holds the history |
| `district_name` | string | As printed that year |
| `enrollment_total_cde` | integer | Sum across grades. Checked against the file's own printed total |
| `enrollment_total_ccd` | integer | CCD grade code 99, where published |
| `teacher_fte_cde` | decimal | Joined from `school-teacher-fte.csv` on `(year, school_code)`. Present in twenty-two years, 2000–2024 |
| `teacher_fte_ccd` | decimal | CCD `teachers_fte`, 1986–2024 |
| `enrollment_reported_in_fte_file` | integer | The staff file's own enrollment count. Not a duplicate of `enrollment_total_cde` — it is an independent figure, and a disagreement is a crosswalk fault worth investigating |
| `latitude`, `longitude` | decimal | Carried backward from a recent CCD directory. Empty where no directory year gives a real value |
| `is_charter` | boolean | CCD `charter`. Empty before 2000, which is when CCD starts carrying it |
| `status` | string | CCD `school_status`: open, closed, new, added, inactive, reopened |

## `schools.csv`

One row per school, not per school-year. The registry.

| Column | Type | Notes |
|---|---|---|
| `ncessch` | string | Primary key |
| `school_codes` | string | Every CDE code the school held, semicolon separated |
| `names` | string | Every name it held, semicolon separated, oldest first |
| `district_codes` | string | Every district it sat in |
| `first_year`, `last_year` | integer | First and last year it appears in any source |
| `closure_label` | string | `closed`, `merged`, `renamed`, `code_changed`, `still_open`, `unknown` |
| `closure_confidence` | string | `high`, `medium`, `low`. **Never hand-verified** — see `decision-log.md`, D6 |
| `closure_evidence` | string | What produced the label: CCD status, a code reuse, a near name match |

## `district-enrollment-by-grade.csv`

`year, district_code, district_name, county_name, grade, enrollment, source`. Two eras, distinguished by `source`: the re-OCR'd yearbooks (`yearbook-<year>`), and the modern years summed up from the school panel (`cde-school-sum`). The yearbook era carries the `SPECIAL_EDUCATION` and `UNGRADED` grade codes, which the school tier does not.

## `unit_type`, on both district tables

`district` or `boces`. A Board of Cooperative Educational Services is a shared agency several districts run together, not a district, and the yearbooks list them alongside districts — which is why a volume reports 180 reporting units where Colorado had 176 districts.

They are flagged, never removed. Their pupils are real and NCES counts them too: dropping the 185 BOCES pupils from 1992 turns an exact match with NCES into a 185-pupil shortfall, and the same happens in 1993, 1996 and 1999. Filter on `unit_type = 'district'` to count districts; leave them in to total pupils.

## `district-year.csv`

The longest series in the archive, and **the only one reaching before 1986**. Built from the yearbooks' Table 4, which each volume prints as its own rolling ten-year window, so the volumes overlap and read the same district-years independently.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | Fall of the school year |
| `school_year` | string | As printed, e.g. `1977-78` |
| `district_code` | string | Matched by name, and empty where the name cannot decide: no modern district carries it, or two do. 98.3% of rows across the archive carry one — 97.2% in 1977–85, 96.0% in 1986–99, 100% from 2000. The eight districts whose old and modern names have nothing in common are listed in `data/lookups/district-aliases.csv` with the membership either side of the change that identifies them |
| `district_name`, `county_name` | string | As printed in the yearbook |
| `fall_membership` | integer | The October count, comparable to the rest of the archive |
| `closing_day_membership` | integer | Empty for each volume's own final year, which had not happened when it was printed |
| `average_daily_membership` | decimal | |
| `adae` | decimal | Average daily attendance equivalent |
| `source` | string | Which volume and table the row came from |

The yearbooks' Table 1 (school counts, staff, pupil/teacher ratio, dropout rate) is converted and sits in `data/interim/yearbooks/`, but is **not yet parsed into this table**. See `ROADMAP.md`.

**What stays uncoded, and why.** Ninety-two non-BOCES district-years. "GARFIELD" covers Rifle in 1987–95 and Parachute in 1996–99, and "EAST"/"WEST YUMA COUNTY" cover two districts each in every yearbook year against four from 2001 — one printed name, two districts, and nothing in the name to separate them. Five small districts — Vona R-3, Egnar 18, Genoa RE-13, Arriba RE-31, Arapahoe R-3 — merged into successors before 2000; a predecessor is not given its successor's code, because that would merge two districts' histories into one series. Every such row keeps its printed name and county.

BVSD and the seven Front Range districts it is compared against — St Vrain, Poudre, Jeffco, Denver, Cherry Creek, Adams 12, Douglas — each run 1977 to 2024 unbroken but for Fall 2000, which CDE never published.

## `school-teacher-fte.csv`

Teacher FTE by school, from CDE's own "Pupil/Teacher Ratio" reports. **38,777 rows, twenty-two years**: 2000–2024, every year except 2017 (a duplicate of 2016, below) and 2020–2021 (not published).

| Column | Type | Notes |
|---|---|---|
| `year` | integer | Fall of the school year |
| `district_code`, `school_code` | string | Zero-padded CDE codes |
| `district_name`, `school_name`, `county_name` | string | As printed that year |
| `teacher_fte` | decimal | Teacher full-time equivalents at that school |
| `enrollment_reported` | integer | The file's own enrollment count — **not** a duplicate of the membership tables, and a disagreement is worth investigating |
| `pupil_teacher_ratio` | decimal | As published, not recomputed |
| `source` | string | The published file each row came from |

Every row satisfies the file's own arithmetic: enrollment ÷ FTE equals the printed ratio to within 5%. Rows that fail are dropped rather than guessed at, because a row that splits across two lines silently puts the enrollment in the FTE column — Douglas County High School came out with 1,893 teachers before this check existed.

Compared against NCES for the same year and state, every year lands between **0.7% and 4.4% below** the NCES state total, sixteen of the twenty-two within 2%. The gap runs the same way in every year, which is a difference in what counts as a teacher rather than a parse fault.

**2006 carries no codes.** It is the one year whose report prints county, district and school names and no codes at all. Those rows are matched to a code by name against the nearest year that prints both: 1,724 of 1,727 resolved, the rest left without a code rather than guessed at.

**2009 lists 84 schools twice**, with different staff on each row, and both readings satisfy the file's own arithmetic — Ortega Middle School is printed with 459 pupils against 29.7 teachers and again against 2, and 459 over 2 really is the 229.5 the second row prints. The fuller staffing is kept and the count is in `audit/teacher-fte-parse.json`.

**2017 is absent, and that is a source defect rather than a gap in this archive.** CDE publishes the 2016 and 2017 pupil-teacher ratio reports at different URLs, but the files are byte-identical — same SHA-256, same 583,100 bytes. Parsing both produced two years with exactly the same 1,784 schools and 49,277.5 FTE. The later duplicate is dropped.

## `district-teacher-fte-ccd.csv`

Teacher FTE by district from NCES. **The longest staffing series in the archive: 7,879 rows, 1987–2024.** It also carries a breakdown by level that CDE never publishes.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | |
| `leaid` | string | NCES district id, the stable key |
| `district_code` | string | CDE district code where NCES carries it |
| `district_name` | string | |
| `teacher_fte` | decimal | Total teacher FTE |
| `teacher_fte_prek`, `teacher_fte_kindergarten`, `teacher_fte_elementary`, `teacher_fte_secondary` | decimal | The level split. Often empty in early years |
| `staff_total_fte` | decimal | All staff, not only teachers. Sparse before about 2015 |
| `enrollment_reported` | integer | NCES district enrollment |

Statewide it runs 30,887 FTE in 1987 to 53,388 in 2024.

## `district-teacher-fte-cde.csv`

The district panel on the CDE side: staffing, school counts and the figures that check them. **6,695 rows, 1986–2024**, 181 to 196 districts a year.

Two eras meet in this table, and the `source` column says which a row came from.

**1986–1999** comes from the yearbooks' summary table — printed as Table 1 in some volumes and Table 2 in others, under a heading that does not change. It is the only CDE source for district staffing before 2000, and it carries the school counts and the rates that no other table in this archive has.

**2000–2024** comes from the modern staff reports. CDE publishes a district total in three of those years only — 2010, where the ratio report prints a `<district> TOTALS*` row after each district's schools, and 2023 and 2024, where there is a by-district spreadsheet. Everywhere else the district total is the sum of its schools.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | Fall of the school year |
| `district_code` | string | Zero-padded CDE code. **Empty for 384 of the 2,659 yearbook district-years**: 172 are BOCES, which have no district code, and the rest are districts that renamed before 2000 |
| `district_name`, `county_name` | string | As printed that year |
| `unit_type` | string | `district` or `boces` |
| `teacher_fte_published` | decimal | What CDE states the district holds. Classroom teacher FTE in the yearbook era; 2010, 2023 and 2024 after it |
| `teacher_fte_school_sum` | decimal | The district's schools in `school-teacher-fte.csv`, added up. 2000–2024 only |
| `teacher_fte_difference` | decimal | `published` minus `school_sum`, where both exist. **A comparison, not a correction** |
| `staff_certificated_fte`, `staff_noncertificated_fte` | decimal | All certificated and non-certificated staff, not only teachers. Yearbook era only, and 1998–1999 do not print them |
| `pupil_teacher_ratio` | decimal | As published, not recomputed |
| `schools_published` | integer | How many schools CDE says the district ran. Yearbook era only |
| `schools_elementary`, `schools_middle`, `schools_senior`, `schools_other` | integer | The split behind that total. They sum to it — that is one of the row's two checks |
| `schools_in_sum` | integer | How many schools the FTE sum covers, 2000–2024 |
| `enrollment_published`, `enrollment_school_sum` | integer | The same pair for enrollment |
| `graduation_rate`, `dropout_rate` | decimal | Per cent, as printed. **Yearbook era only, and unchecked** — no second source carries them, so unlike every other column here they rest on the OCR alone |

### The two checks the yearbook rows carry

Each row states enough to test itself twice: the four school counts must add to the printed total, and students divided by classroom teachers must be the printed ratio. Both are recorded per volume in `audit/normalize-report.json`.

They also repair. A row that drops one cell pulls everything after it one place left, and the result is not obviously wrong — Denver's 1994 row lost its school total and came back with **62,773 teachers and 17 pupils**; Colorado Springs lost its non-certificated staff in 1996 and came back with 33,175 teachers. Both are among the state's largest districts. Every possible loss point is tried and one is accepted only where the row then satisfies both checks; two rows in fourteen volumes needed it.

### 1999 staffing does not exist

The 1999 volume prints **Fall 1999 membership beside Fall 1998 teachers**, under two different "FALL" headings in the same row. Its staffing is therefore filed under 1998, which is where it belongs, and confirmed there: 38,838 FTE against the NCES 1998 total of 39,360. The 1998 volume prints no staff column at all. So the CDE teacher series has one missing year, 1999, between the yearbook era and the staff serial that starts in 2000. NCES covers it.

### How well it reconciles

Summed and compared against the NCES state total, **every year from 1987 to 1998 lands within 1.3%**, five within 0.2%, and 1991 agrees to a fifth of one FTE out of 33,093. 1986 has nothing to check it against: NCES district staffing starts in 1987. On the modern side, the 2010 subtotals sum to 48,449.1 against 48,450.

## `nonpublic-enrollment-by-grade.csv`

CDE's count of the schools this archive is otherwise not about. One row per non-public school, year and grade, 2003 to 2014.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | The autumn of the count, as everywhere else here |
| `county_name` | string | As printed |
| `district_code`, `district_name` | string | The public district whose boundary the school sits in. It does not attend that district; this is geography |
| `school_code` | string | CDE's non-public code, `P` and three digits. Not a public school code and not comparable with one |
| `school_name` | string | As printed |
| `grade` | string | The canonical grades, PK to 12 |
| `enrollment` | integer | Pupils in that grade |
| `source` | string | The file it was read from |

A row is kept only where its grades add to the total the file prints. Every year passes on every row; the district totals also agree in nine years of twelve, and `audit/nonpublic-parse.json` says which.

**This is not the same count as the public tables.** Non-public schools report to CDE under a different statute and the school codes do not join to anything else here. 2007 carries 494 schools against 380 either side, which is the source rather than the reading - its row and district totals both reconcile.

## `nonpublic-year.csv`

The same thing summed: one row per year, with schools, districts and enrollment.

## `county-population.csv` and `municipal-population.csv`

Total population from the State Demography Office, written by the retrieval notebook rather than the pipeline. Counties run 1870 to 2024 and municipalities 1980 to 2024, and `basis` says whether a county row is an annual estimate or a decennial census count.

**Total population, not by age.** The single-year-of-age file starts in 1990 and the district panel starts with it; these do not extend the school-age series, they give the denominator either side of it. A municipality that crosses a county line is printed once per county, marked `(Part)`.

## `source-reconciliation.csv`

One row **per year**, not per school: the two sources compared across the whole state. `cde_schools`, `ccd_schools`, `matched`, `exact_agreement`, `median_abs_diff`, `cde_total`, `ccd_total`, `cde_prek`, `ccd_prek`, `gap_excluding_prek`.

## Grade notes

- **`PK` is CDE-only.** NCES CCD publishes no pre-kindergarten rows for Colorado in any year checked. On the CCD side `PK` is *missing*, not zero. Colorado's PK is roughly 31,800 pupils a year, so treating it as zero would understate CCD by about 3.6% and make the two sources look irreconcilable when they are not.
- **`K` is a sum.** CDE publishes Half-Day K and Full-Day K as separate columns from about 2014; CCD and the yearbooks publish one undivided K. The archive sums them. The half/full split is **not** preserved separately — recovering it means going back to the raw file, which `data/raw/cde/` keeps.
- **Grade headers are ordinals in the source** (`1st` … `12th`), and are stored here as bare numbers.
- **`special_education` and `ungraded`** appear in the yearbooks' district tables and in some school files. They are kept as their own categories and are never folded into a numbered grade.

## The row-total check

Every source table prints its own row total. The cleaning step sums the grade cells and compares, and the pass and fail counts per file land in `audit/validation.md` and `audit/normalize-report.json`. The check is **not** carried as a column on each row.

It has one blind spot worth stating plainly: an aggregate row passes it. The 2010 file ends with a STATE TOTALS row coded 9999 carrying all 843,316 pupils, and that row sums correctly against itself — read as a school it doubled the state exactly while every checksum passed. Only comparing school sums against the district rows caught it. This matters most for the scanned 1986–1999 tier, where it is the only mechanical proof that an OCR'd row was read correctly — in the 1986 volume, `CALHAN RJ-1` sums to exactly its printed 370 and `HARRISON 2` to exactly its printed 9,463.

## Known missingness, by design

| Cell | Why |
|---|---|
| School-level anything, 1986–1999 on the CDE side | The yearbooks have no school-level table |
| `enrollment_cde`, 1986–2003 | CDE publishes no machine-readable school-grain file; CCD covers those years |
| `enrollment_ccd`, 2025 | CCD has not released it |
| `teacher_fte_cde`, before 2000 and in 2017, 2020, 2021 | CDE's staff serial starts in 2000; 2017 duplicates 2016 byte for byte, and no ratio report was published for 2020 or 2021. CCD carries school FTE from 1986 |
| `is_charter`, before 2000 | CCD does not carry the flag that far back |
| `latitude` / `longitude`, schools that closed before about 2013 | No directory year gives them a real coordinate |
| `closing_day_membership`, each volume's own final year | Not yet observed when the volume was printed |
