# Budget history: validation report

Written by `budget-history.py` every time it runs, from the rows it has
just built. Nothing here is typed by hand, so where this file and the
data dictionary disagree about a count or a year, this file is right.

## Files

| File | Rows | Years |
|---|---:|---|
| `budget-history.csv` | 664 | 2002–2027 |
| `budget-history-wide.csv` | 26 | 2002–2027 |
| `budget-history-department-crosswalk.csv` | 291 | 2005–2022, 2024–2026 |
| `budget-history-provenance.csv` | 9 | not applicable |

## Checks

Every check below ran on this build and passed. A failing check stops the
build before any file is written, so a published file has passed all of them.

| Check | Cases | Tolerance | Largest miss |
|---|---:|---|---|
| One row per (year, measure, basis) | 664 | exact | none |
| Department buckets, plus any balancing line, sum to `budget_total` | 21 | $0.05M | $0.002M (2026 deptexpfiltered_*) |
| A department label keeps its bucket from year to year, or a note says why | 76 | exact | none |
| General Fund half + dedicated half = `budget_operating` | 18 | $0.2M | $0.012M (2019 adopted) |
| `budget_operating` + `budget_capital` = `budget_total` | 23 | $0.2M | $0.100M (2025 adopted) |
| Sales and use tax components sum to `salesuse_total` | 8 | $0.05M | $0.040M (2026 forecast) |
| Revenue components sum to that year's `revenue_total` | 23 | $0.02M | $0.001M (2026 recommended) |
| OpenGov snapshot components sum to their totals, and net = revenue - expense | 9 | $10 | $1 (2021 net) |

## Rounding residuals

The city totals sales and use tax at full precision and prints components
rounded to $0.01M, so a column can miss its own total by a few hundredths.
Each miss is kept in the data as `salesuse_component_residual`:

| Year | Basis | Residual |
|---|---|---:|
| 2024 | `actual` | +$0.01M |
| 2025 | `actual` | +$0.01M |
| 2025 | `adopted` | +$0.01M |
| 2025 | `revised_projection` | -$0.02M |
| 2026 | `forecast` | +$0.04M |

## Rows by source

| `source_id` | Rows | Years |
|---|---:|---|
| `rec2026` | 13 | 2026 |
| `forecast2026` | 99 | 2022–2027 |
| `rec2027` | 9 | 2027 |
| `glance2027` | 6 | 2027 |
| `snapshot2023` | 81 | 2021–2023 |
| `books` | 208 | 2003–2026 |
| `deptsnapshot2026` | 24 | 2024–2026 |
| `booksocr` | 223 | 2002, 2005–2022, 2024 |
| `brl2027` | 1 | 2027 |

## Rows by basis

| `basis` | Rows | Years |
|---|---:|---|
| `actual` | 78 | 2003–2009, 2021–2025 |
| `adopted` | 494 | 2002–2026 |
| `derived` | 3 | 2024–2026 |
| `forecast` | 9 | 2026–2027 |
| `identified` | 3 | 2025–2026 |
| `policy` | 1 | 2026 |
| `projected` | 2 | 2007, 2009 |
| `recommended` | 28 | 2026–2027 |
| `restated` | 9 | 2007, 2011–2012, 2014–2016, 2020–2022 |
| `revised_projection` | 10 | 2025–2026 |
| `total_budget` | 27 | 2023 |

## Coverage by measure

Years with at least one row, on any basis. A year that is missing is
absent from the data, never zero.

| Measure | Unit | Years | Bases |
|---|---|---|---|
| `budget_capital` | musd | 2005–2027 | `adopted`, `recommended` |
| `budget_general_fund` | musd | 2005–2027 | `actual`, `adopted`, `projected`, `recommended` |
| `budget_general_fund_revenue` | musd | 2003–2026 | `actual`, `adopted`, `projected` |
| `budget_operating` | musd | 2005–2027 | `adopted`, `recommended` |
| `budget_operating_dedicated` | musd | 2005–2022 | `adopted` |
| `budget_operating_general` | musd | 2005–2022 | `adopted` |
| `budget_total` | musd | 2004–2027 | `adopted`, `recommended`, `restated` |
| `deptexp_administration` | musd | 2005–2022 | `adopted` |
| `deptexp_citywide_debt` | musd | 2005–2018 | `adopted` |
| `deptexp_community_services` | musd | 2005–2022 | `adopted` |
| `deptexp_infrastructure` | musd | 2005–2022 | `adopted` |
| `deptexp_parks_openspace` | musd | 2005–2022 | `adopted` |
| `deptexp_planning_climate` | musd | 2005–2022 | `adopted` |
| `deptexp_public_safety` | musd | 2005–2022 | `adopted` |
| `deptexpfiltered_administration` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_citywide_debt` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_community_services` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_funds_outside_export` | musd | 2024–2026 | `derived` |
| `deptexpfiltered_infrastructure` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_parks_openspace` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_planning_climate` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_public_safety` | musd | 2024–2026 | `adopted` |
| `gap_general_fund` | musd | 2026–2027 | `forecast`, `identified`, `recommended` |
| `gap_general_fund_high` | musd | 2025 | `identified` |
| `gap_general_fund_low` | musd | 2025 | `identified` |
| `net_revenues_less_expenses` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `positions_added` | fte | 2027 | `recommended` |
| `positions_eliminated` | fte | 2026–2027 | `adopted`, `recommended` |
| `positions_eliminated_filled` | fte | 2027 | `recommended` |
| `positions_eliminated_vacant` | fte | 2027 | `recommended` |
| `positions_frozen_to_2028` | fte | 2027 | `recommended` |
| `positions_term_limited_ending` | fte | 2027 | `recommended` |
| `property_assessed_value` | musd | 2023–2026 | `actual`, `adopted`, `revised_projection` |
| `property_mill_levy` | mills | 2026 | `adopted` |
| `property_tax_revenue` | musd | 2023–2026 | `actual`, `adopted`, `revised_projection` |
| `reserve_policy_pct_of_operating` | pct | 2026 | `policy` |
| `revenue_accommodation_admission_tax` | musd | 2026 | `recommended` |
| `revenue_development_impact_fees` | musd | 2026 | `recommended` |
| `revenue_grants` | musd | 2026 | `recommended` |
| `revenue_intergovernmental` | musd | 2005–2017, 2019–2026 | `adopted`, `recommended` |
| `revenue_investment_earnings_bonds` | musd | 2026 | `recommended` |
| `revenue_licenses_permits_fines` | musd | 2026 | `recommended` |
| `revenue_other_grouped` | musd | 2026 | `recommended` |
| `revenue_other_unmapped` | musd | 2005–2026 | `adopted` |
| `revenue_parking` | musd | 2026 | `recommended` |
| `revenue_property_tax` | musd | 2005–2026 | `adopted`, `recommended` |
| `revenue_sales_use_tax` | musd | 2005–2026 | `adopted`, `recommended` |
| `revenue_total` | musd | 2005–2026 | `adopted`, `recommended` |
| `revenue_utility` | musd | 2005–2026 | `adopted`, `recommended` |
| `salesuse_audits_sales` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_audits_use` | musd | 2022–2025 | `actual` |
| `salesuse_component_residual` | musd | 2024–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_construction_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_consumer_business_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_motor_vehicle_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_rec_marijuana_addl` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_retail` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_total` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `sources_revenue_accommodation_admission_tax` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_charges_for_services` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_cost_allocation` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_development_impact_fees` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_franchise_fees` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_grants` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_intergovernmental` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_intragovernmental_charges` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_investment_earnings_bonds` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_leases_rents_royalties` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_licenses_permits_fines` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_misc_sales_materials_goods` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_other` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_property_tax` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_sales_use_tax` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_specific_ownership_tobacco` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_total` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_transfers_in` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `sources_revenue_utility` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `staffing_fte` | fte | 2002–2018, 2020–2026 | `adopted`, `restated` |
| `staffing_savings` | musd | 2027 | `recommended` |
| `uses_expense_capital` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_debt_service` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_internal_services` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_operating` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_personnel` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_total` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `uses_expense_transfers` | musd | 2021–2023 | `actual`, `adopted`, `total_budget` |
| `yoy_capital_pct` | pct | 2027 | `recommended` |
| `yoy_general_fund_pct` | pct | 2026–2027 | `adopted`, `recommended` |
| `yoy_operating_pct` | pct | 2026–2027 | `adopted`, `recommended` |
| `yoy_total_pct` | pct | 2027 | `recommended` |

## Department crosswalk

| Family | Years | Rows | Distinct printed labels | Rows with a note |
|---|---|---:|---:|---:|
| `deptexp` | 2005–2022 | 231 | 82 | 89 |
| `deptexpfiltered` | 2024–2026 | 60 | 20 | 12 |

Years in which each bucket has a line:

| Bucket | `deptexp` | `deptexpfiltered` |
|---|---|---|
| `public_safety` | 2005–2022 | 2024–2026 |
| `infrastructure` | 2005–2022 | 2024–2026 |
| `parks_openspace` | 2005–2022 | 2024–2026 |
| `community_services` | 2005–2022 | 2024–2026 |
| `planning_climate` | 2005–2022 | 2024–2026 |
| `administration` | 2005–2022 | 2024–2026 |
| `citywide_debt` | 2005–2018 | 2024–2026 |
