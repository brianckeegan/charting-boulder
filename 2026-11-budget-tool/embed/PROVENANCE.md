# Where every slider number comes from

The widget's figures come from the City of Boulder's 2027 Recommended Budget,
released Aug. 28, 2026, as it stood on Oct. 1, 2026, the night of the City
Council's first reading. The budget and appropriation ordinances introduced
that night carry the same General Fund total, $200,496,242, and the same mill
levies; the council's final vote is Oct. 15. This file traces every number a
slider shows or uses to the document, table, row and column it comes from, and
shows the arithmetic for each number the widget derives.

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
| **Dept** | The budget book's department pages, each with its "Summary of Budget Changes," for example [Police](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d85779d69a2eb6abe1), [Planning & Development Services](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d885b2d1fbcfe410ee), [Fire-Rescue](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8c9bc19d58a7cb1a9), [Parks & Recreation](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8345b07fe00521720) and [Housing & Human Services](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a71c8d8d600ec1e99cb1d16) |
| **RAF** | [Recreation Activity Fund – 2027 Fund Financial (2300)](https://bouldercolorado.gov/media/21595/download?inline), PDF. The budget book's Recreation Activity Fund page links to the .25 Cent Sales Tax Fund's table instead. |
| **POL** | The budget book's [financial policies](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a75e5049edf5ffa8847c1f7), section 7 and its "2027 Budgeted Reserves" table |
| **O1** | City Council agenda packet, [Oct. 1, 2026](https://bouldercolorado.primegov.com/Public/CompiledDocument?meetingTemplateId=1052&compileOutputType=1): the first-reading memo on the 2027 budget and Ordinances 8777–8780 |
| **F26** | 2026 Financial Forecast, City Council study session packet, [May 14, 2026](https://bouldercolorado.primegov.com/Public/CompiledDocument?meetingTemplateId=950&compileOutputType=1) |
| **MJ** | [City of Boulder marijuana tax rates](https://bouldercolorado.gov/city-boulder-marijuana-tax-rates) |
| **BW13** | Boulder Weekly, ["Pot taxes a sticky issue"](https://www.boulderweekly.com/content-archives/voters-guide/vote-2013/pot-taxes-a-sticky-issue/), 2013 voters' guide |

## Reading the numbers

Every slider starts at the status quo: what the General Fund would spend and collect in 2027 if the city kept all of this year's services, before its own fixes. That is the budget with the $6.3 million gap: BiB calls it "the largest anticipated gap of $6.3M if left unaddressed." The blue "proposed" ticks mark the recommended budget, the city's way of closing it:

- each department's recommended 2027 amount;
- the marijuana tax rate the recommended budget sets;
- the General Fund costs it moves onto dedicated funds.

Following every tick closes exactly $6.3 million. The department sliders move in whole percents and the cost shift in $0.1 million steps, so setting each one as close to its tick as it goes closes the gap with $0.2 million to $0.3 million to spare.

The city does not publish each department's status quo, so the department starting points are estimates, built as described under "General Fund sliders." On the revenue side, the property tax starts at the 2027 forecast, which the city does not change; the sales base has the marijuana tax increase taken out; and the fee base includes the city's fee changes, which the budget does not total separately.

## The gap and the totals

| Constant | Value | Source |
|---|---:|---|
| `GAP` | $6.3M | BiB: the General Fund "saw the largest anticipated gap of $6.3M if left unaddressed." O1 repeats it. The May 14, 2026 forecast presentation had put it at $6.5M, as Boulder Reporting Lab [reported](https://boulderreportinglab.org/2026/05/17/boulder-predicting-budget-gap-as-economic-forecast-remains-cloudy/) on May 17; F26's memo gives no 2027 figure. |
| `TOTAL` | $552,600,998 | BiB, citywide uses by department, 2027 Budget column, Total. BiB's text rounds it to "$552.60 million." |
| `OPERATING` | $417.24M | BiB: "The 2027 Recommended Operating Budget is $417.24 million." |
| `CAPITAL` | $135.36M | BiB: "The 2027 Recommended Capital Budget is $135.36 million." |
| `GENERAL_FUND` | $200,496,242 | FF, Total Uses of Funds, 2027 Budget. BiB's General Fund uses-by-department table has the same total. |

The budget bar's "36¢ of every dollar" is `GENERAL_FUND ÷ TOTAL`, 36.3%.

## General Fund sliders

- **Recommended 2027 amounts (`amount`):** FF, "2027 Budget" column. BiB's General Fund uses-by-department table gives the same figures. They set the ticks.
- **2026 amounts (`was`):** BiB's General Fund uses-by-department table, "2026 Budget" column, which restates 2026 for the 2027 departments. They appear in each tick's tooltip.
- **Starting points (`base`), the status quo, are estimates.** For each slider:
  1. Take the recommended 2027 amount.
  2. Undo the city's itemized 2027 changes. The department pages (Dept) list 161 General Fund changes. The 110 reductions, enhancements and realignments are the city's decisions; the 51 base-cost items, such as internal service charges, are part of the status quo. The 110 net to +$419,098: $4,783,613 of reductions, $5,055,577 of enhancements and $147,134 of realignments. General Government has none. BiB's citywide table of changes has the same rows for every other department, except that it leaves out Police entirely (15 decisions netting +$1,377,550) and two Planning & Development Services rows (−$30,261). Innovation & Technology's page doesn't label its rows by type, so its types come from BiB; the page's amounts match BiB's.
  3. Add a share of the rest of the gap. The itemized decisions add $419,098 on net and the marijuana tax increase raises $412,000, so the part of the gap the city does not itemize by department is $6,300,000 + $419,098 − $412,000 = $6,307,098. It covers, for example, most of the $858,330 cut in the General Fund's subsidy to the Recreation Activity Fund (RAF; see the cost shift below). It is spread across all eleven sliders in proportion to their recommended amounts, 3.15% each. (Heading into 2027, the city manager asked every department for ongoing cuts of about 4%.)
- **The tick** is the recommended amount plus any cost the budget moves onto a dedicated fund, which leaves through the cost-shift slider instead: Fire-Rescue $179,718, Parks & Recreation $36,410, Housing & Human Services $100,000 and General Government $250,000 (`moved`). The proposed change is tick ÷ starting point − 1.
- **Check:** following every tick closes $6,300,000: the department ticks save $206,384,242 − $200,496,242 − $566,128 = $5,321,872, the cost shift $566,128 and the marijuana tax $412,000.

| Slider | 2026, restated | 2027 recommended | City's itemized changes | Share of the remainder | Starting point (`base`) | Proposed tick |
|---|---:|---:|---:|---:|---:|---:|
| Police | $50,203,922 | $54,246,256 | $1,377,550 | $1,706,448 | $54,575,154 | −0.6% |
| General Government | $38,436,021 | $35,612,445 | — | $1,120,276 | $36,732,721 | −2.4% |
| Fire-Rescue | $29,129,284 | $30,967,597 | −$65,971 | $974,161 | $32,007,729 | −2.7% |
| Housing & Human Services (General Fund share) | $12,961,613 | $14,007,208 | $654,504 | $440,631 | $13,793,335 | +2.3% |
| City Manager's Office | $11,087,455 | $11,981,255 | $194,527 | $376,900 | $12,163,628 | −1.5% |
| Innovation & Technology | $10,372,051 | $10,680,047 | −$636,048 | $335,967 | $11,652,062 | −8.3% |
| Facilities & Fleet (General Fund share) | $7,153,291 | $7,041,735 | −$171,388 | $221,515 | $7,434,638 | −5.3% |
| Finance | $6,881,016 | $7,023,903 | −$116,016 | $220,954 | $7,360,873 | −4.6% |
| Parks & Recreation (General Fund share) | $6,489,602 | $6,634,292 | −$131,415 | $208,698 | $6,974,405 | −4.4% |
| City Attorney's Office | $5,067,069 | $5,517,903 | $177,084 | $173,579 | $5,514,398 | +0.1% |
| Other General Fund departments | $16,702,126 | $16,783,601 | −$863,729 | $527,969 | $18,175,299 | −7.7% |
| **Total** | **$194,483,450** | **$200,496,242** | **$419,098** | **$6,307,098** | **$206,384,242** | |

The widget rounds each starting point to the nearest $1,000, and each tick here is computed from the widget's rounded figures. Police's $2,639,203 of itemized additions are mostly one-time: $1.2 million more for overtime and $823,950 to extend fixed-term positions. Three new lieutenants add $551,753 a year. Its $1,261,653 of cuts are almost all in photo enforcement.

- **General Government** is FF's "General Government" row. In BiB's table it is "Fundwide / Citywide" ($35,122,830 in 2027) plus "Police/Fire Pensions" ($489,615).
- **Other General Fund departments** are FF's rows for City Council, Climate Initiatives, Communications & Engagement, Human Resources, Municipal Court, Planning & Development Services, Transportation & Mobility and Utilities. Community Vitality and Library have no 2027 budget.
- **Restated versus approved.** FF's "2026 Approved" column still lists Community Vitality, at $1,611,459. BiB counts that money with the departments that took over its work: $1,388,682 with the City Manager's Office and $222,777 with Facilities & Fleet. Those three rows are the only ones that differ (approved: City Manager's Office $9,698,773, Facilities & Fleet $6,930,514, Other $18,313,585), and both columns total $194,483,450.
- **Range:** −25% to +25% of each starting point, an editorial choice.

## Revenue sliders

### Fees & charges: $10,972,890 (`base: 10.973`)

FF, "2027 Budget" column, the sum of three rows:

- Licenses, Permits & Fines: $7,117,405
- Parking Revenues: $3,591,027
- Charges for Services: $264,458

The line under the slider names those three rows. Each 1% moves $109,729. That yield is modeled.

These 2027 figures include the city's fee changes, which the budget does not total separately, so the slider starts there. Whatever those changes contribute to closing the gap is inside the remainder spread across the department sliders.

### Property tax: $39,459,000 (`base: 39.459`)

BiB-C, Mill Levies & Projected Revenue table: the "General Fund - General Purposes" row, 7.948 mills, "2027 Projected Revenue." The "11.648 mills" in the line under the slider is the same table's "General Citywide" row.

FF's Property Tax line, $49,388,300, is this levy plus the voter-dedicated "General Fund - Public Safety" levy: 2.000 mills, $9,929,300. The slider leaves the dedicated levy out.

### Sales & use tax: $82,597,010 (`base: 82.597`)

FF, Sales & Use Tax, "2027 Budget": $83,009,010. BiB-C's Sales Tax Revenues 2023-2027 chart shows the same figure in thousands, $83,009. That figure includes the recreational marijuana sales tax at the recommended 5.5%: FF's separate marijuana row covers only excise and use taxes ($150,000, unchanged), and BiB's revenue notes forecast the retail tax up 41.2% "due to the increase of the tax rate from 3.5% to 5.5%." The slider starts at the status quo, so the $412,000 increase is taken out and left to the marijuana slider: $83,009,010 − $412,000 = $82,597,010.

The rates in the line under the slider are from BiB-C's Sales & Use Tax Components in 2027 table. The General Fund subtotal is 1.72% (1.00 + 0.38 + 0.15 + 0.11 + 0.08) of a 3.86% total. BiB-C notes that this total "includes revenues received from the 3.50% recreational marijuana sales and use tax."

### Recreational marijuana tax

| Number | Value | Source |
|---|---:|---|
| Today's rate (`now`) | 3.5% | MJ: "additional RMB 3.5% city sales and use tax." AAG. |
| Proposed (`city`) | 5.5% | AAG: "An increase in recreational marijuana additional tax, from 3.5% to 5.5%." |
| Cap (`max`) | 10% | BW13: the council "could, in later years, raise each tax to up to 10 percent," under the city's 2013 ballot measure. This is not in the 2027 budget documents. |
| Revenue at today's rate (`base`) | $1.00M | F26's sales and use tax table, the recreational marijuana column, 2026 forecast. |
| Each point above 3.5% (`perPoint`) | $206,000 | Modeled: $1.00M × 41.2% ÷ 2 points. |

- **41.2%:** BiB's revenue notes: "Recreational Marijuana Retail Sales Tax (41.2%): Forecasted year-over-year increase in Recreational Marijuana Retail Tax due to the increase of the tax rate from 3.5% to 5.5% beginning in 2027."
- **Above 3.5%**, each point adds the same $206,000: the city's forecast for the move to 5.5%, spread evenly over its two points.
- **Below 3.5%**, revenue falls in proportion to the rate, to $0 at 0%: $1.00M × rate ÷ 3.5%.
- **The row shows revenue, not the rate:** $1.0M at today's 3.5%, $1.4M at the proposed 5.5%, $2.3M at the 10% cap and $0 at 0%. The rate appears beside the slider.

The line under the slider, "Boulder's additional sales tax on recreational marijuana," follows MJ.

### Shift General Fund costs onto dedicated funds: proposed $566,128 (`city: 0.566`)

The four 2027 changes that move an existing General Fund cost onto a dedicated fund:

| Department | Change, as the budget lists it | Amount |
|---|---|---:|
| Fire-Rescue | "Realignment of Fire-Rescue Wildland Unit to Open Space Fund from 75% to 90%" | $179,718 |
| Parks & Recreation | "Realignment of Urban Ranger equipment funding to Open Space Fund based on shared services One Ranger approach" | $36,410 |
| Housing & Human Services | "Realigning half of the Behavioral Health Intensive Community Service Contract to be funded by the Sugar-Sweetened Beverage Distribution Tax Fund" | $100,000 |
| General Government | "Recreation activities operations funding realignment supported by the Sugar-Sweetened Beverage Tax Distribution" | $250,000 |
| **Total** | | **$566,128** |

The first three are in the department pages' lists of General Fund changes. The fourth is listed in the Recreation Activity Fund, but it replaces General Fund money: AAG lists it under "Using Existing Funds Differently," for programs such as the Youth Services Initiative, EXPAND and REquity, "instead of subsidizing these through the General Fund," and RAF shows the General Fund's subsidy falling from $1,377,713 in 2026 to $519,383 in 2027, with a new $450,000 transfer in from the sugary-drink tax. The slider counts the $250,000 the city gives for the move. The subsidy is a transfer to another fund, so the tool counts it with General Government, whose line includes interfund transfers.

The recommended department amounts already leave these costs out, so each department's tick adds its share back and this slider takes it out.

Not counted:

- $150,000 of urban forestry moved from the .25 Cent Sales Tax Fund to the Climate Tax Fund. Both are dedicated funds. (O1's memo calls it a "realignment from General Fund to Climate Tax Fund," but the line items move it from the .25 Cent fund.)
- A $177,084 Climate Tax transfer to the General Fund pays for a new attorney position.
- Two cuts the budget describes as realignments: Housing & Human Services' $200,000 for the Local Voucher program, to the Affordable Housing Fund, and Fire-Rescue's $60,357 of EMS supplies, to Equipment Replacement Fund reserves. Neither receiving fund lists a matching line, so both stay in their departments' itemized cuts.

The slider's range, $0 to $5M, is an editorial choice.

### Vacancy tax, local income tax, wealth tax

Locked rows with no numbers. Each has a one-line summary under its name.

| Row | The line under the name | Source |
|---|---|---|
| Vacancy tax | $4,000 a year on homes left empty more than half the year · On the Nov. 3 ballot · Would start in 2028 | The city's [2026 ballot measures page](https://bouldercolorado.gov/2026-city-boulder-ballot-measures), Ballot Issue 2J, and Boulder Reporting Lab, Aug. 6, 2026; see the Nov. 3 ballot row under "Other figures on the page." |
| Local income tax | Residents' and workers' earnings · Barred for Colorado cities by the state constitution | Colorado's Taxpayer's Bill of Rights, Colo. Const. Art. X, §20(8)(a), which bars any new "local district income tax." |
| Wealth tax | Household net worth · No Colorado city has the power to levy one | The tool's reading of state law: Colorado exempts intangible personal property, such as stocks and bonds, from property tax (C.R.S. 39-3-118), and no Colorado city taxes net worth. Any new city tax would also need voter approval under TABOR. |

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

## Other figures on the page

The widget's prose uses these figures. They were checked against the sources below, and none of them feeds a slider.

| Figure | Source |
|---|---|
| Sales-tax rates voters set aside: Open Space 0.77%, Transportation 0.75%, Community, Culture, Resilience & Safety 0.30%, .25-cent Parks & Recreation 0.25%, Arts, Culture & Heritage 0.075%; General Fund 1.72% of 3.86% | BiB-C, Sales & Use Tax Components in 2027. The table prints the arts tax as 0.08%; BiB-C's list of rate changes gives its exact 0.075%. |
| What each of those funds raises in 2027: $36.6M, $35.7M, $14.3M, $11.9M, $3.6M | BiB-C, Sales Tax Revenues 2023-2027 (in $1,000s), 2027 Budget: $36,635, $35,684, $14,274, $11,895, $3,568 |
| Transportation Maintenance Fee, about $3.0M in 2027 | BiB revenue notes: "An estimated $3.03M is included in the 2027 Budget supported by a new fee (approved in the 2026 Budget)." The city could not start collecting it in 2026 (AAG: "The city will start collecting the Transportation Maintenance Fee ... in early 2027"). |
| Utility rates up 5–7% | BiB-C, Key Budget Assumptions: water rates 5.00%, wastewater and stormwater 7.00% |
| Raises: 5% for police and firefighters, 4% for most other union staff | City manager's [budget message](https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB?currentPageId=6a7a2349492dea63d5fd8d27); BiB-C, Key Budget Assumptions: Boulder Municipal Employees Association 4.00% |
| Sales and use tax flat since 2023; property tax down 2.4% | BiB-C: the Sales Tax Revenues chart (General Fund $82,137 thousand in 2023, $83,009 thousand in 2027) and Key Budget Assumptions (property tax −2.40%) |
| The city's plan: 24 positions eliminated, 13 of them filled; photo-radar vans ended; shorter pool hours; custodial service cut from five days to three; the marijuana tax to 5.5%; higher licensing and parking-permit fees; three new police lieutenants | AAG, the city's [Aug. 28 release](https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input), the budget message, and BiB's revenue notes (photo enforcement revenue falls 52.8% "driven by the elimination of photo radar van enforcement") |
| Past gaps: $8–10M in mid-2025, $7.5M for 2026, about $6M in 2026 fees ($2.25M transportation maintenance, $2.6M speed-on-green cameras, $0.8M parking, $0.4M single-family expansion), 19 mostly vacant positions | F26's budget history ("an $8.0-$10.0 million shortfall" in 2025; "a forecasted $7.5M shortfall" for 2026), and Boulder Reporting Lab, ["Council approves $521M 2026 budget"](https://boulderreportinglab.org/2025/10/23/boulder-city-council-approves-521-million-2026-budget-adds-demolition-and-transportation-maintenance-fees/) (Oct. 23, 2025) |
| The General Fund's emergency reserve, about 20% of its spending, kept at its target | POL: the 2027 Budgeted Reserves table sets the General Fund's emergency operating reserve at 20.0%, $40,125,842 (16.7% is the operating-reserve goal for most other funds). FF: $39,237,353 in 2026, 20.2% of that year's spending, and $40,125,842 in 2027. F26: in 2025 the city acted "to ensure the city maintained at or above its emergency reserve level target." |
| The Nov. 3 ballot: a $400M recreation-and-safety bond (about $400 a year on a $1 million home), a charter change on the city's debt limit, collective bargaining for firefighters, and a $4,000-a-year tax on homes left empty more than half the year, which the city estimates would raise about $6M a year in flexible revenue starting in 2028 | Boulder Reporting Lab, ["Council sends vacancy tax and $400M bond to the November ballot"](https://boulderreportinglab.org/2026/08/06/boulder-city-council-sends-vacancy-tax-and-400-million-bond-to-november-ballot-rejects-downtown-development-authority/) (Aug. 6, 2026), for the measures. The $6M is from the ballot question itself, on the city's [2026 ballot measures page](https://bouldercolorado.gov/2026-city-boulder-ballot-measures): Ballot Issue 2J asks whether "City of Boulder taxes be increased $6,000,000 annually (which amount represents estimated revenues in 2028, the first full fiscal year of collection)." |
| Fund Our Future heard from more than 500 people, who ranked wildfire response and facility maintenance highest | The city's [Fund Our Future summary](https://bouldercolorado.gov/news/fund-our-future-our-communitys-priorities) (June 29, 2026) |
| Tax increases need voter approval; local income taxes are barred | Colorado's Taxpayer's Bill of Rights, Colo. Const. Art. X, §20; the Colorado General Assembly's [TABOR explainer](https://leg.colorado.gov/agencies/legislative-council-staff/tabor) |

## Choices that are the tool's, not the city's

- The −25% to +25% range on the department, fee and tax sliders, and the $0 to $5M range for moving costs.
- A fee or tax change yields the same share of its 2027 base, with no change in how people buy, park or build.
- Below today's 3.5% marijuana tax rate, revenue falls in proportion to the rate.
- No slider for reserves or other one-time money: the gap comes back every year, and one-time money only postpones it.
- Starting from the status quo, with each department's starting point estimated as described under "General Fund sliders," including the proportional spread of the $6,307,098 the city does not itemize.

## Corrections made while writing this file

- **Moving costs onto dedicated funds:** the proposed tick was $0.47 million. It had missed the $100,000 behavioral-health contract, and it is now $566,128, shown as "proposed ~$0.6M."
- **The 2026 baseline for the General Fund ticks** is now the restated column. Three ticks changed:
  - City Manager's Office: +23.5% to +8.1%
  - Facilities & Fleet: +1.6% to −1.6%
  - Other General Fund departments: −8.4% to +0.5%
- **Other General Fund departments, 2026:** the old figure had also been off by $1,415. The restated figure replaces it.
- **Marijuana tax below 3.5%** (Sept. 29, 2026): the tool had applied the $206,000-a-point estimate below today's rate too, which left about $0.28M of revenue at a 0% rate. Below 3.5%, revenue now falls in proportion to the rate.
- **Vacancy tax revenue** (Oct. 1, 2026): the widget said about $4M a year, Boulder Reporting Lab's Aug. 6 figure from a city estimate of 500 to 1,000 vacant homes. The ballot question the city published, Issue 2J, estimates $6,000,000 in 2028, and the widget now says about $6M.
- **Where the sliders start** (Oct. 1, 2026): the department sliders started at the recommended 2027 amounts, a budget the city had already balanced, while the tool still asked readers to close $6.3 million, and the ticks showed each department's 2026-to-2027 change. Following every tick left a reader about $5.3 million short of a budget that was in fact balanced. The sliders now start at the status quo, and the ticks mark the recommended budget.
- **Two double counts** (Oct. 1, 2026): the sales base included the marijuana tax increase that the marijuana slider also counts, and is now $82,597,010; the cost shift counted $250,000 that relieves the Recreation Activity Fund rather than the General Fund, and is now $316,128.
- **Police and Planning changes** (Oct. 1, 2026): the starting points undid the city's itemized changes from BiB's citywide table, which leaves out all 15 of Police's decisions (+$1,377,550 net) and two Planning & Development Services rows (−$30,261). With each department page's list, the itemized changes net +$419,098 instead of −$928,191, the remainder spread by size is $6,307,098 (3.15%) instead of $4,959,809 (2.47%), and every starting point and tick moved; Police's tick went from −2.4% to −0.6%.
- **The sugary-drink tax for recreation programs** (Oct. 1, 2026): the earlier "two double counts" correction took this $250,000 out of the cost shift as a Recreation Activity Fund item. RAF shows the General Fund's subsidy to that fund falling by $858,330 and a new $450,000 transfer from the sugary-drink tax, and AAG presents the move as replacing General Fund money. It is back in, as General Government's `moved`, and the shift is $566,128, shown as "proposed ~$0.6M."
- **The emergency reserve** (Oct. 1, 2026): the widget said the reserve was "about 16.7% of operating spending." The General Fund's goal is 20.0% (POL); 16.7% is the goal for other funds. The widget now says about 20%.
- **The $6.5M forecast gap** (Oct. 1, 2026): this file cited F26 for it, but the packet's memo has no 2027 figure; it came from the May 14 presentation, which Boulder Reporting Lab reported.
