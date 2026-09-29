# Where every slider number comes from

The widget's figures come from the City of Boulder's 2027 Recommended Budget,
released Aug. 28, 2026, as it stood on Sept. 29, 2026, before the City
Council's final vote on Oct. 15. This file traces every number a slider shows or
uses to the document, table, row and column it comes from, and shows the
arithmetic for each number the widget derives.

The numbers live as constants in
[`src/boulder-budget-widget.jsx`](src/boulder-budget-widget.jsx), in millions of
dollars to three decimals. Every figure below was recomputed from the source
tables, and each one matches its constant. Dollar amounts are as the city prints
them, not adjusted for inflation.

## Sources

| Key | Document |
|---|---|
| **BiB** | [2027 Budget in Brief](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a7a22d6e8cd6b725ef3b5b5), in the city's online budget book. Its text gives the totals and the gap. Its embedded tables give citywide and General Fund uses by department, and its revenue notes and list of 2027 changes are on the same page. |
| **BiB-C** | [Budget in Brief, continued](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a7a230c2aaa5815f9944b90): the Sales & Use Tax Components in 2027 table, the Sales Tax Revenues 2023-2027 chart, and the Mill Levies & Projected Revenue table |
| **FF** | [General Fund – 2027 Fund Financial (1100)](https://bouldercolorado.gov/media/21600/download?inline), PDF, also shown on the budget book's [General Fund page](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c7e911737a7a460f5b89). Columns used: "2026 Approved" and "2027 Budget" |
| **AAG** | [Budget At-A-Glance](https://bouldercolorado.gov/budget-glance), the city's summary of 2027 cuts, shifts and fees |
| **Dept** | The budget book's department pages, each with its list of 2027 changes: [Fire-Rescue](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8c9bc19d58a7cb1a9), [Parks & Recreation](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8345b07fe00521720), [Housing & Human Services](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8d600ec1e99cb1d16) |
| **F26** | 2026 Financial Forecast, City Council study session packet, May 14, 2026, on the [city's budget page](https://bouldercolorado.gov/services/budget) |
| **MJ** | [City of Boulder marijuana tax rates](https://bouldercolorado.gov/city-boulder-marijuana-tax-rates) |
| **BW13** | Boulder Weekly, ["Pot taxes a sticky issue"](https://www.boulderweekly.com/content-archives/voters-guide/vote-2013/pot-taxes-a-sticky-issue/), 2013 voters' guide |

## Reading the numbers

Every slider starts at its recommended 2027 amount. The $6.3 million gap is the
shortfall the city projected *before* its own fixes: BiB calls it "the largest
anticipated gap of $6.3M if left unaddressed." A reader therefore closes the gap
their own way, starting from a budget the city has already balanced its way.

The blue "proposed" ticks show the city's own moves:

- each department's change from 2026 to 2027;
- the marijuana tax rate the recommended budget sets;
- the General Fund costs it moves onto dedicated funds.

## The gap and the totals

| Constant | Value | Source |
|---|---:|---|
| `GAP` | $6.3M | BiB: the General Fund "saw the largest anticipated gap of $6.3M if left unaddressed." F26 had put it at $6.5M. |
| `TOTAL` | $552,600,998 | BiB, citywide uses by department, 2027 Budget column, Total. BiB's text rounds it to "$552.60 million." |
| `OPERATING` | $417.24M | BiB: "The 2027 Recommended Operating Budget is $417.24 million." |
| `CAPITAL` | $135.36M | BiB: "The 2027 Recommended Capital Budget is $135.36 million." |
| `GENERAL_FUND` | $200,496,242 | FF, Total Uses of Funds, 2027 Budget. BiB's General Fund uses-by-department table has the same total. |

The budget bar's "36¢ of every dollar" is `GENERAL_FUND ÷ TOTAL`, 36.3%.

## General Fund sliders

- **2027 amounts:** FF, "2027 Budget" column. BiB's General Fund uses-by-department table gives the same figures.
- **2026 amounts:** BiB's General Fund uses-by-department table, "2026 Budget" column, which restates 2026 for the 2027 departments.
- **The proposed change** is 2027 ÷ 2026 − 1.

| Slider | 2027 recommended | 2026, restated | Proposed change | 2026 as approved (FF), where it differs |
|---|---:|---:|---:|---:|
| Police | $54,246,256 | $50,203,922 | +8.1% | |
| General Government | $35,612,445 | $38,436,021 | −7.3% | |
| Fire-Rescue | $30,967,597 | $29,129,284 | +6.3% | |
| Housing & Human Services (General Fund share) | $14,007,208 | $12,961,613 | +8.1% | |
| City Manager's Office | $11,981,255 | $11,087,455 | +8.1% | $9,698,773 |
| Innovation & Technology | $10,680,047 | $10,372,051 | +3.0% | |
| Facilities & Fleet (General Fund share) | $7,041,735 | $7,153,291 | −1.6% | $6,930,514 |
| Finance | $7,023,903 | $6,881,016 | +2.1% | |
| Parks & Recreation (General Fund share) | $6,634,292 | $6,489,602 | +2.2% | |
| City Attorney's Office | $5,517,903 | $5,067,069 | +8.9% | |
| Other General Fund departments | $16,783,601 | $16,702,126 | +0.5% | $18,313,585 |
| **Total** | **$200,496,242** | **$194,483,450** | | |

- **General Government** is FF's "General Government" row. In BiB's table it is "Fundwide / Citywide" ($35,122,830 in 2027) plus "Police/Fire Pensions" ($489,615).
- **Other General Fund departments** are FF's rows for City Council, Climate Initiatives, Communications & Engagement, Human Resources, Municipal Court, Planning & Development Services, Transportation & Mobility and Utilities. Community Vitality and Library have no 2027 budget.
- **Restated versus approved.** FF's "2026 Approved" column still lists Community Vitality, at $1,611,459. BiB counts that money with the departments that took over its work: $1,388,682 with the City Manager's Office and $222,777 with Facilities & Fleet. Those three rows are the only ones that differ, and both columns total $194,483,450. Measured against the approved column, the City Manager's Office would show +23.5%, most of it this reorganization.
- **Range:** −25% to +25% of each 2027 amount, an editorial choice.

## Revenue sliders

### Fees & charges: $10,972,890 (`base: 10.973`)

FF, "2027 Budget" column, the sum of three rows:

- Licenses, Permits & Fines: $7,117,405
- Parking Revenues: $3,591,027
- Charges for Services: $264,458

The line under the slider names those three rows. Each 1% moves $109,729. That yield is modeled.

### Property tax: $39,459,000 (`base: 39.459`)

BiB-C, Mill Levies & Projected Revenue table: the "General Fund - General Purposes" row, 7.948 mills, "2027 Projected Revenue." The "11.648 mills" in the line under the slider is the same table's "General Citywide" row.

FF's Property Tax line, $49,388,300, is this levy plus the voter-dedicated "General Fund - Public Safety" levy: 2.000 mills, $9,929,300. The slider leaves the dedicated levy out.

### Sales & use tax: $83,009,010 (`base: 83.009`)

FF, Sales & Use Tax, "2027 Budget." BiB-C's Sales Tax Revenues 2023-2027 chart shows the same figure in thousands, $83,009.

The rates in the line under the slider are from BiB-C's Sales & Use Tax Components in 2027 table. The General Fund subtotal is 1.72% (1.00 + 0.38 + 0.15 + 0.11 + 0.08) of a 3.86% total. BiB-C notes that this total "includes revenues received from the 3.50% recreational marijuana sales and use tax."

### Recreational marijuana tax

| Number | Value | Source |
|---|---:|---|
| Today's rate (`now`) | 3.5% | MJ: "additional RMB 3.5% city sales and use tax." AAG. |
| Proposed (`city`) | 5.5% | AAG: "An increase in recreational marijuana additional tax, from 3.5% to 5.5%." |
| Cap (`max`) | 10% | BW13: the council "could, in later years, raise each tax to up to 10 percent," under the city's 2013 ballot measure. This is not in the 2027 budget documents. |
| Yield per point (`perPoint`) | $206,000 | Modeled: $1.00M × 41.2% ÷ 2 points. |

- **41.2%:** BiB's revenue notes: "Recreational Marijuana Retail Sales Tax (41.2%): Forecasted year-over-year increase in Recreational Marijuana Retail Tax due to the increase of the tax rate from 3.5% to 5.5% beginning in 2027."
- **$1.00M:** F26's sales and use tax table, the recreational marijuana column, 2026 forecast.
- **The model assumes** revenue moves in proportion to the rate.

The line under the slider, "Boulder's additional sales tax on recreational marijuana," follows MJ.

### Shift costs onto dedicated funds: proposed $566,128 (`city: 0.566`)

The four 2027 changes that move an existing General Fund cost onto a dedicated fund, as listed in BiB's 2027 changes and on each department's page:

| Department | Change, as the budget lists it | Amount |
|---|---|---:|
| Fire-Rescue | "Realignment of Fire-Rescue Wildland Unit to Open Space Fund from 75% to 90%" | $179,718 |
| Parks & Recreation | "Realignment of Urban Ranger equipment funding to Open Space Fund based on shared services One Ranger approach" | $36,410 |
| Parks & Recreation | "Recreation activities operations funding realignment supported by the Sugar-Sweetened Beverage Tax Distribution Fund for health equity" | $250,000 |
| Housing & Human Services | "Realigning half of the Behavioral Health Intensive Community Service Contract to be funded by the Sugar-Sweetened Beverage Distribution Tax Fund" | $100,000 |
| **Total** | | **$566,128** |

AAG describes the wildland crew and the sugary-drink tax moves under "Using Existing Funds Differently."

Two other realignments in the list are not counted, because neither relieves an existing General Fund cost:

- $150,000 of urban forestry moved from the .25 Cent Sales Tax Fund to the Climate Tax Fund. Both are dedicated funds.
- A $177,084 Climate Tax transfer to the General Fund pays for a new attorney position.

The slider's range, $0 to $5M, is an editorial choice.

### Vacancy tax, local income tax, wealth tax

Locked rows with no numbers.

## Locked-spending sliders

Each amount is the department's 2027 spending in all funds (BiB, citywide uses by department, "2027 Budget" column) minus its 2027 General Fund amount (FF).

| Slider | Citywide uses, 2027 | Minus General Fund, 2027 | Slider amount |
|---|---:|---:|---:|
| Utilities | $136,940,407 | $385,315 | $136,555,092 |
| Transportation & Mobility | $60,127,099 | $99,000 | $60,028,099 |
| Open Space & Mountain Parks | $37,422,557 | $0 | $37,422,557 |
| Housing & Human Services | $49,721,865 | $14,007,208 | $35,714,657 |
| Parks & Recreation | $37,112,619 | $6,634,292 | $30,478,327 |
| Facilities & Fleet | $23,987,587 | $7,041,735 | $16,945,852 |
| Planning & Development Services | $19,229,101 | $2,996,678 | $16,232,423 |
| City Manager's Office | $19,429,465 | $11,981,255 | $7,448,210 |
| Climate Initiatives | $8,109,630 | $1,617,070 | $6,492,560 |
| Fire-Rescue | $35,049,888 | $30,967,597 | $4,082,291 |
| Other departments | $125,470,780 | $124,766,092 | $704,688 |
| **Total** | **$552,600,998** | **$200,496,242** | **$352,104,756** |

"Other departments" comes from two lines:

- **Finance:** $187,841, which is $7,211,744 citywide against $7,023,903 in the General Fund.
- **Citywide accounts and pensions:** $516,847. That is "Fundwide / Citywide" plus "Police/Fire Pensions," $36,129,292 citywide, against FF's General Government, $35,612,445.

Police, Innovation & Technology, the City Attorney's Office, Human Resources, Communications & Engagement, Municipal Court and City Council spend nothing outside the General Fund in 2027.

The column sums to `TOTAL − GENERAL_FUND`, $352,104,756. The range is −25% to +25%, an editorial choice. The $135.36 million capital budget is spread across these rows.

## Choices that are the tool's, not the city's

- The −25% to +25% range on the department, fee and tax sliders, and the $0 to $5M range for moving costs.
- A fee or tax change yields the same share of its 2027 base, with no change in how people buy, park or build.
- No slider for reserves or other one-time money: the gap comes back every year, and one-time money only postpones it.
- Starting from the recommended amounts, as described under "Reading the numbers."

## Corrections made while writing this file

- **Moving costs onto dedicated funds:** the proposed tick was $0.47 million. It had missed the $100,000 behavioral-health contract, and it is now $566,128, shown as "proposed ~$0.6M."
- **The 2026 baseline for the General Fund ticks** is now the restated column. Three ticks changed:
  - City Manager's Office: +23.5% to +8.1%
  - Facilities & Fleet: +1.6% to −1.6%
  - Other General Fund departments: −8.4% to +0.5%
- **Other General Fund departments, 2026:** the old figure had also been off by $1,415. The restated figure replaces it.
