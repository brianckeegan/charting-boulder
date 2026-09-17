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
| `teacher_fte_cde` | decimal | From the staff series. Empty before about 2013 and in years CDE reports district grain only |
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
| `district_code` | string | Matched by name; empty where no modern district carries that name |
| `district_name`, `county_name` | string | As printed in the yearbook |
| `fall_membership` | integer | The October count, comparable to the rest of the archive |
| `closing_day_membership` | integer | Empty for each volume's own final year, which had not happened when it was printed |
| `average_daily_membership` | decimal | |
| `adae` | decimal | Average daily attendance equivalent |
| `source` | string | Which volume and table the row came from |

The yearbooks' Table 1 (school counts, staff, pupil/teacher ratio, dropout rate) is converted and sits in `data/interim/yearbooks/`, but is **not yet parsed into this table**. See `ROADMAP.md`.

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
| `teacher_fte_cde`, all but 2013, 2016–2019 and 2022–2024 | CDE publishes school-grain teacher FTE in those eight years only; CCD carries it from 1986 |
| `is_charter`, before 2000 | CCD does not carry the flag that far back |
| `latitude` / `longitude`, schools that closed before about 2013 | No directory year gives them a real coordinate |
| `closing_day_membership`, each volume's own final year | Not yet observed when the volume was printed |
