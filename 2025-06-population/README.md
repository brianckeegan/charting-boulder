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

## Correction, September 2026

Two errors were found in `rebuttal.ipynb`'s sister-cities comparison and corrected. Neither
changes the column's finding about Boulder, and Boulder's own figure is unchanged.

**Cities were paired with the wrong county.** The notebook selected 26 places and 26 counties in
two separate operations, then attached the place names to the county figures by row position.
Each selection keeps its own source file's row order, and those orders differ wherever a state
holds more than one city in the basket. Six cities were affected: Irvine was divided by Los
Angeles County, Mountain View by Orange, Pasadena by Santa Barbara, Santa Barbara by Santa Clara,
Chapel Hill by Durham, and Durham by Orange. Both selections are now ordered to match
`similar-boulder.json` before any comparison.

**Iowa City carried the wrong county code.** `similar-boulder.json` named Johnson County but gave
the code 19087, which is Henry County, a rural county of about 20,000 people. Johnson County is
19103. The file is corrected.

What moved, in the place-to-county growth ratio that feeds the sister-cities chart:

| City | Was | Now |
|---|---|---|
| Irvine | 29.27 | 18.58 |
| Iowa City | 1.41 | 0.75 |
| Mountain View | 0.72 | 0.89 |
| Pasadena | 0.72 | 0.86 |
| Santa Barbara | 0.69 | 0.75 |
| Durham | 1.15 | 1.21 |
| Chapel Hill | 0.99 | 0.94 |

Boulder is 0.645 before and after, ranked 24th of 26 either way, and the number of cities that
grew more slowly than their county is 18 either way. The published claim that Boulder's growth
lags the median of the cohort, and that few peers grew as slowly relative to their county, holds
on the corrected figures. The Datawrapper chart in the July 2025 column still shows the earlier
values for the seven cities above.

One further repair was needed to re-run the notebook at all: it loaded `rac-boulder.csv`, a file
that has never been in this repository, into a variable it never used. That dead line is removed,
and the notebook now executes from a fresh kernel top to bottom.

## Columns
- [*The myth of a 'full' Boulder — and how our policies are driving people away*](https://boulderreportinglab.org/2025/06/29/brian-keegan-the-myth-of-a-full-boulder-and-how-our-policies-are-driving-people-away/) — published 2025-06-29.
- [*Rethinking Boulder's growth debate — with data, not nostalgia*](https://boulderreportinglab.org/2025/07/22/brian-keegan-rethinking-boulders-growth-debate-with-data-not-nostalgia/) — published 2025-07-22.
