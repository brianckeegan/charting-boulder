# 2025-06-population

## Question
Is Boulder "full"? How does the city's recent population trajectory compare to its own past, to peer Colorado municipalities, and to similar cities in other states?

## Decision peg
Boulder's ongoing growth debate: housing supply ordinances, comprehensive-plan updates, and Council-level zoning conversations that recurringly invoke "Boulder is full" as a premise.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| Components-of-change county estimates | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed CSV | `components-change-county.csv` |
| Historical census | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/population.html) | Committed CSV | `historical-census.csv` |
| Annual county/municipal estimates | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/population.html) | Committed CSV | `county-muni-timeseries.csv` |
| LODES jobs (WAC) | [U.S. Census LODES](https://lehd.ces.census.gov/) | Committed CSV | `wac-boulder.csv` |
| Municipal housing units | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/housing.html) | Committed XLSX | `muni-pop-housing.xlsx` |
| CU Boulder enrollment | [Colorado Open Data](https://data.colorado.edu/reports/enrollment-cu-boulder-1877) | Committed CSV | `cu-enrollments.csv` |
| Historical place and county populations | [IPUMS NHGIS](https://www.nhgis.org/) | Committed CSV | `nhgis-ts-place.csv`, `nhgis-ts-county.csv` |
| Similar-cities catalog | Hand-curated | Committed JSON | `similar-boulder.json` |

## Notebooks
- `population.ipynb` — long-run growth trajectory of City of Boulder and Boulder County, with rankings and Colorado-share context.
- `rebuttal.ipynb` — follow-up addressing reader feedback: jobs-housing ratio, CU student share of city population, and sister-cities comparison.

## Key findings
- The City of Boulder's growth has slowed sharply since the late 20th century; the most recent decade shows near-flat population.
- Boulder County is growing faster than the city; surrounding counties grow faster still.
- Boulder's share of Colorado's population has fallen over the long run as faster-growing places climb the municipal rankings.
- Jobs in the city now substantially exceed housing units — the jobs-housing imbalance is the binding pressure, not raw growth.
- Among a cohort of demographically similar U.S. cities, Boulder's 1970-to-2020 growth lags the median; few peers have grown as slowly relative to their county.

(Headline figures are pinned in the final cell of each notebook.)

## Limitations
- Decennial historical census is reliable for trend identification but coarse for recent years; the annual SDO estimates fill the gap with a different methodology and small year-over-year revisions.
- LODES WAC counts jobs at workplace, not employer headquarters, and is delayed roughly two years.
- The similar-cities catalog is a curated rather than rigorous match; the rebuttal piece uses it for context, not as a quasi-experimental control set.

## Columns
- [*The myth of a 'full' Boulder — and how our policies are driving people away*](https://boulderreportinglab.org/2025/06/29/brian-keegan-the-myth-of-a-full-boulder-and-how-our-policies-are-driving-people-away/) — published 2025-06-29.
- [*Rethinking Boulder's growth debate — with data, not nostalgia*](https://boulderreportinglab.org/2025/07/22/brian-keegan-rethinking-boulders-growth-debate-with-data-not-nostalgia/) — published 2025-07-22.
