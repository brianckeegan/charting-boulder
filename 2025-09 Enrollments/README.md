# 2025-09 Enrollments

## Question
What does the long-run trajectory of Boulder Valley School District enrollment tell us about Boulder's demographics — and how does the K-12-versus-65+ ratio reshape the political center of the city as it shifts?

## Decision peg
BVSD facilities-and-boundaries planning, district-budget conversations under declining enrollment, and the broader generational politics surfaced by school closures and over-65 voting strength.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| BVSD and St. Vrain pupil counts by grade | [Colorado Department of Education](https://www.cde.state.co.us/cdereval/pupilcurrent) (current); [CDE Artemis ED 59017](https://spl.cde.state.co.us/artemis/edserials/ed59017internet/) (2000–2022); [CDE Artemis ED 27919](https://spl.cde.state.co.us/artemis/edserials/ed27919internet/) (1986–1999) | Standardized committed CSV | `enrollments.csv` |
| Annual county/municipal population estimates | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/population.html) | Committed CSV | `county-muni-timeseries.csv` |
| Single-year-of-age county population estimates and forecasts | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed CSV | `sya-county.csv` |

## Notebooks
- `Enrollments.ipynb` — total BVSD enrollment over time, regression on county K-12 population, cohort-survival forecast through 2050, and the K-12-per-65+ ratio.

## Key findings
- BVSD enrollment has been declining since its mid-2010s peak; the cohort-survival forecast extends the decline well into the 2030s.
- The regression of BVSD enrollment on county K-12 population fits closely, suggesting most of the decline is demographic rather than market-share loss to charter or private alternatives.
- Boulder County's K-12-per-65+ ratio crosses below 1.0 within the observed window, marking a structural shift in the school district's political and fiscal footing.
- OCR transcription errors in the 1986-1999 enrollment records were detected and corrected by the `Total − sum(grades)` integrity check.

(Headline figures are pinned in the final cell of the notebook.)

## Limitations
- The cohort-survival model assumes historical grade-transition ratios continue and does not endogenize school-choice migration to charters, private schools, or homeschool.
- SDO single-year-of-age estimates are modeled rather than observed; the under-19 slice carries more uncertainty than total county population.
- The combined BVSD-area population is approximated by county totals; BVSD's actual catchment area is slightly different.

## Column
[*Boulder's next political divide is generational — and already visible in school enrollment trends*](https://boulderreportinglab.org/2025/10/14/brian-keegan-boulders-next-political-divide-is-generational-and-already-visible-in-school-enrollment-trends/) — published 2025-10-14.
