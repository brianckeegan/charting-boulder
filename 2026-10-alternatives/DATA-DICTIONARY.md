# Data dictionary

The schema `TASK.md` is to produce. **Nothing in `data/processed/` exists yet** — this describes the target, so that the cleaning step is written against a stated contract rather than inventing one as it goes. Columns marked *planned* have no data behind them today.

Conventions that hold everywhere in this archive:

- All identifier codes are **zero-padded strings**, never numbers. `0010` is a district, `10.0` is a bug.
- `year` is the **fall of the school year**: 2024 means the 2024-25 count, taken on or about 1 October 2024.
- Missing is empty, never `0` and never `-1`. A zero means a real count of zero.
- Every table carries a `source` column, so a row can always be traced to the file it came from.
- Long format throughout. One row per observation, not one column per year.

## `school-enrollment-by-grade.csv` *(planned)*

The core panel. One row per school per year per grade.

| Column | Type | Notes |
|---|---|---|
| `year` | integer | Fall of the school year |
| `ncessch` | string | NCES school id, 12 characters. The stable key across renames and code changes |
| `school_code` | string | CDE school code, 4 digits. Not unique statewide in every year |
| `district_code` | string | CDE district code, 4 digits |
| `grade` | string | `PK`, `K`, `1` … `12`. See the grade notes below |
| `enrollment_cde` | integer | CDE October count. Empty where CDE publishes no school-grain file that year |
| `enrollment_ccd` | integer | NCES CCD. Empty before 1986, after 2023, and for `PK` in every year |
| `source` | string | Which file each value came from |

## `school-year.csv` *(planned)*

One row per school per year. Identity, totals and the things that are not per-grade.

| Column | Type | Notes |
|---|---|---|
| `year`, `ncessch`, `school_code`, `district_code` | | As above |
| `school_name` | string | As printed that year. Names change; the registry holds the history |
| `district_name` | string | As printed that year |
| `enrollment_total_cde` | integer | Sum across grades. Checked against the file's own printed total |
| `enrollment_total_ccd` | integer | CCD grade code 99, where published |
| `teacher_fte_cde` | decimal | From the staff series. Empty before about 2013 and in years CDE reports district grain only |
| `teacher_fte_ccd` | decimal | CCD `teachers_fte`, 1986–2023 |
| `pupil_teacher_ratio_cde` | decimal | As CDE publishes it, not recomputed |
| `latitude`, `longitude` | decimal | Carried backward from a recent CCD directory. Empty where no directory year gives a real value |
| `is_charter` | boolean | CCD `charter`. Empty before 2000, which is when CCD starts carrying it |
| `status` | string | CCD `school_status`: open, closed, new, added, inactive, reopened |
| `row_total_check` | string | `pass`, `fail`, or `not_applicable`. See the checksum note below |

## `schools.csv` *(planned)*

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

## `district-enrollment-by-grade.csv` *(planned)*

District × year × grade, 1986–2025. Carries two columns the school tier does not, because the yearbooks report them: `special_education` and `ungraded`.

## `district-year.csv` *(planned)*

District × year, **1977–2025** — the longest series in the archive, and the only one reaching before 1986. From the yearbooks' Table 4 and Table 1.

| Column | Type | Notes |
|---|---|---|
| `year`, `district_code`, `district_name`, `county_name` | | County appears in the yearbooks and in CDE files before about 2019 |
| `fall_membership` | integer | The October count, comparable to every other year in the archive |
| `closing_day_membership` | integer | Yearbooks only. Empty for the volume's own final year, which had not happened when it was printed |
| `average_daily_membership` | decimal | Yearbooks only |
| `adae` | decimal | Average daily attendance equivalent. Yearbooks only |
| `schools_elementary`, `schools_middle`, `schools_senior`, `schools_other`, `schools_total` | integer | Yearbook Table 1 |
| `staff_certificated`, `staff_noncertificated`, `classroom_teachers` | decimal | Yearbook Table 1 |
| `pupil_teacher_ratio`, `teacher_student_ratio` | decimal | As published |
| `dropout_rate` | decimal | Grades 10–12 only, as the yearbooks define it |
| `source_volume`, `source_page` | string | Which yearbook and which page, so any figure can be checked against the scan |

## `source-reconciliation.csv` *(planned)*

One row per school per overlapping year. `enrollment_cde`, `enrollment_ccd`, `difference`, `difference_excluding_prek`, and `expected_reason` where the gap has a known cause.

## Grade notes

- **`PK` is CDE-only.** NCES CCD publishes no pre-kindergarten rows for Colorado in any year checked. On the CCD side `PK` is *missing*, not zero. Colorado's PK is roughly 31,800 pupils a year, so treating it as zero would understate CCD by about 3.6% and make the two sources look irreconcilable when they are not.
- **`K` is a sum.** CDE publishes Half-Day K and Full-Day K as separate columns; CCD and the yearbooks publish one undivided K. The archive sums them and also keeps `k_half` and `k_full` in `school-year.csv`, because the split is itself informative.
- **Grade headers are ordinals in the source** (`1st` … `12th`), and are stored here as bare numbers.
- **`special_education` and `ungraded`** appear in the yearbooks' district tables and in some school files. They are kept as their own categories and are never folded into a numbered grade.

## The row-total check

Every source table prints its own row total. The cleaning step sums the grade cells and compares. `row_total_check` records the outcome, and both numbers are kept when they disagree. This matters most for the scanned 1986–1999 tier, where it is the only mechanical proof that an OCR'd row was read correctly — in the 1986 volume, `CALHAN RJ-1` sums to exactly its printed 370 and `HARRISON 2` to exactly its printed 9,463.

## Known missingness, by design

| Cell | Why |
|---|---|
| School-level anything, 1986–1999 on the CDE side | The yearbooks have no school-level table |
| `enrollment_ccd`, 2024–2025 | CCD had not released those years at the time of the audit |
| `teacher_fte_cde`, before about 2013 | CDE published teacher counts by district only |
| `is_charter`, before 2000 | CCD does not carry the flag that far back |
| `latitude` / `longitude`, schools that closed before about 2013 | No directory year gives them a real coordinate |
| `closing_day_membership`, each volume's own final year | Not yet observed when the volume was printed |
