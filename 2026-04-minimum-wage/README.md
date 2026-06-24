# 2026-04 Minimum Wage

## Question
What do tipped restaurant workers in Boulder County actually earn — and how does that compare to the $40/hour total-compensation claim Councilmember Benjamin cited as a basis for slowing tipped-wage growth, against Boulder County's rent trajectory?

## Decision peg
Boulder City Council's April 2026 deliberation on the tipped-wage offset (Council Hotline Item 7A, April 2, 2026; March 30 Benjamin proposal). Four options on the table, ranging from maintaining the current trajectory to freezing tipped pay through 2029.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| ACS 1-Year: median rent, cost burden, food-service earnings | [U.S. Census Bureau](https://www.census.gov/programs-surveys/acs/data.html) | API at runtime | (fetched from `api.census.gov/data/{year}/acs/acs1`) |
| County Business Patterns: food-service establishments and employment | [U.S. Census Bureau](https://www.census.gov/programs-surveys/cbp.html) | API at runtime | (fetched from `api.census.gov/data/{year}/cbp`) |
| HUD Fair Market Rents historical file (2-bedroom, 1983–2026) | [HUD](https://www.huduser.gov/portal/datasets/fmr.html) | XLSX at runtime | (fetched from `huduser.gov/portal/datasets/fmr/FMR_2Bed_1983_2026.xlsx`) |
| Zillow Observed Rent Index, Boulder metro | [Zillow Research](https://www.zillow.com/research/data/) | CSV at runtime | (fetched from `files.zillowstatic.com`) |
| MIT Living Wage | [livingwage.mit.edu/counties/08013](https://livingwage.mit.edu/counties/08013) | Hardcoded benchmark | (in-notebook) |
| Boulder and Colorado minimum-wage schedule | City of Boulder ordinances; Colorado CDLE | Hardcoded | (in-notebook) |

No data files are committed; the notebook downloads everything at runtime. No authentication required.

## Notebooks
- `tipped-wages.ipynb` — five-figure analysis culminating in a Monte Carlo simulation (N=8,000) over tip income, hours per week, and rent growth to produce a fan chart of worker-income distributions under each policy scenario.

## Key findings
- ACS median full-time food-service earnings in Boulder County are roughly half the $40/hour total-compensation figure Benjamin cited.
- The hourly wage required to keep a Boulder County 2-bedroom apartment at the 30%-of-income affordability threshold is, by coincidence, very close to the same $40/hour claim — meaning Benjamin's figure happens to describe the affordability threshold itself, not actual worker earnings.
- Boulder County renter cost-burden rates have been elevated and rising; a majority of renters spend over 30% of income on rent in the most recent ACS year.
- Across the four policy scenarios on Council's table, the Monte Carlo fan chart shows that even the most generous trajectory leaves a substantial share of simulated tipped workers below the affordability threshold through 2030.
- CBP data show the Boulder County food-service sector has continued to add establishments and employment through the recent minimum-wage trajectory, complicating the claim that wage growth threatens the sector's viability.

(Headline figures are pinned in the final cell of the notebook; consolidated summary statistics are also printed in §14.)

## Limitations
- ACS B24022 covers full-time, year-round workers only; ACS likely overstates typical food-service worker earnings relative to all tipped workers (many are part-time or seasonal).
- The $40/hour claim is from a restaurant-operator survey, not worker self-report; comparing it to ACS earnings compares apples to oranges in one direction (worker reporting vs. operator reporting).
- Post-2026 projection assumptions for full-wage and rent growth (+3.5%/yr) are conservative anchors, not forecasts.
- CBP first-quarter employment may undercount seasonal peak restaurant employment.
- The Monte Carlo simulation parameterizes uncertainty; it does not endogenize the labor-supply response of workers to each policy scenario.

## Column
*Minimum wage and affordability piece — URL TBD once published.*
