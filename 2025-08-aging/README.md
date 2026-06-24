# 2025-08-aging

## Question
How is Boulder's age composition changing, where are older residents concentrated, and what does the shift mean for civic participation, public revenue, and the housing stock?

## Decision peg
Upstream of a durable policy conversation rather than a single vote — Council and County budget priorities, BVSD school-facilities planning, housing supply for aging-in-place, and the design of local services as the over-65 share rises.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| Single-year-of-age county population estimates | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/county.html) | Committed XLSX | `sya-county.xlsx` |
| Voter detail and voting-history extracts (EX-002) | [Boulder County Clerk](https://bouldercounty.gov/elections/maps-and-data/data-access/#Master-Voter-History-Data-File) | **Not committed** — download from County Clerk page; place files next to notebook | `EX-002_Public_Voter_Details_List_Part{1,2}.txt`, `EX-002_Public_Voting_History_List_Part{1..4}.txt` |
| Precinct shapefile | [Boulder County Open Data](https://opendata-bouldercounty.hub.arcgis.com/datasets/c8e2897d283b47f780920af0827d5126_0/explore) | Committed GeoJSON | `precincts.geojson` |
| Consumer expenditure by age | [FRED API](https://fred.stlouisfed.org/docs/api/fred/) (series `CXUTOTALEXPLB0402M`–`CXUTOTALEXPLB0409M`) | API at runtime — requires `fred_api.json` with your own API key | (fetched) |
| Generation boundaries | [Pew Research Center](https://www.pewresearch.org/short-reads/2019/01/17/where-millennials-end-and-generation-z-begins/) | Hardcoded constants | (in-notebook) |

## Notebooks
- `aging.ipynb` — population by generation, precinct-level map of over-65 concentration, voter-turnout by age cohort, and consumer-expenditure trajectories by age.

## Key findings
- The 65+ share of Boulder County has risen meaningfully over the past two decades while the under-25 share has fallen.
- Older voters turn out at higher rates than younger ones in both odd- and even-year cycles, with a larger gap in odd-year (municipal) elections.
- Consumer-expenditure data show households 65+ spend substantially less than 55–64 households across most categories, with implications for sales-tax-dependent municipal revenue.
- Older voters are concentrated in specific precincts; the spatial pattern affects how generational divides map onto neighborhood politics.

(Headline figures are pinned in the final cell of the notebook.)

## Limitations
- The EX-002 voter files capture registered voters as of the extract date; they don't track people who moved in or out between extracts.
- Single-year-of-age estimates from SDO are modeled rather than observed; small-area age structure carries more uncertainty than total population.
- FRED consumer-expenditure series are national, not Boulder-specific; they describe age-group spending patterns generally and are illustrative of revenue implications.
- The precinct map shows where older voters live, not where they vote on — and precinct boundaries change across redistricting cycles.

## Column
[*How Boulder's 'silver wave' could transform the city's future — for the better, if we plan now*](https://boulderreportinglab.org/2025/08/26/brian-keegan-how-boulders-silver-wave-could-transform-the-citys-future-for-the-better-if-we-plan-now/) — published 2025-08-26.
