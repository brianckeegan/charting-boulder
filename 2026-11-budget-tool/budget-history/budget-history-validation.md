# Budget history: validation report

Written by `budget-history.py` every time it runs, from the rows it has
just built. Nothing here is typed by hand, so where this file and the
data dictionary disagree about a count or a year, this file is right.

## Files

| File | Rows | Years |
|---|---:|---|
| `budget-history.csv` | 2544 | 2002–2027 |
| `budget-history-wide.csv` | 26 | 2002–2027 |
| `budget-history-department-crosswalk.csv` | 351 | 2005–2022, 2024–2027 |
| `budget-history-provenance.csv` | 12 | not applicable |

## Checks

Every check below ran on this build and passed. A failing check stops the
build before any file is written, so a published file has passed all of them.

| Check | Cases | Tolerance | Largest miss |
|---|---:|---|---|
| One row per (year, measure, basis) | 2544 | exact | none |
| Department buckets, plus any balancing line, sum to `budget_total` | 24 | $0.05M | $0.021M (2025 deptexp_*) |
| A department label keeps its bucket from year to year, or a note says why | 76 | exact | none |
| General Fund half + dedicated half = `budget_operating` | 18 | $0.2M | $0.012M (2019 adopted) |
| `budget_operating` + `budget_capital` = `budget_total` | 23 | $0.2M | $0.100M (2025 adopted) |
| Packet sales and use tax components sum to the packet's own total | 8 | $0.05M | $0.040M (2026 forecast) |
| ACFR staffing lines, and the six buckets, sum to `ftefunc_total` | 38 | 0.02 FTE | none |
| ACFR taxable sales by sector sum to `taxablesales_total` | 22 | $0.002M | none |
| ACFR General Fund lines sum to total revenues and total expenditures | 60 | $0.01M | none |
| Revenue components sum to that year's `revenue_total` | 24 | $0.02M | $0.001M (2026 recommended) |
| OpenGov snapshot components sum to their totals, and net = revenue - expense | 9 | $10 | $1 (2021 net) |

## Rounding residuals

The city totals sales and use tax at full precision and prints components
rounded to $0.01M, so a column can miss its own total by a few hundredths.
Each miss is kept in the data as `salesuse_component_residual`:

| Year | Basis | Residual |
|---|---|---:|
| 2025 | `adopted` | +$0.01M |
| 2025 | `revised_projection` | -$0.02M |
| 2026 | `forecast` | +$0.04M |

## Rows by source

| `source_id` | Rows | Years |
|---|---:|---|
| `rec2026` | 13 | 2026 |
| `forecast2026` | 87 | 2022–2027 |
| `rec2027` | 9 | 2027 |
| `glance2027` | 6 | 2027 |
| `recbook2027` | 43 | 2025–2027 |
| `snapshot2023` | 81 | 2021–2023 |
| `books` | 212 | 2003–2026 |
| `deptsnapshot2026` | 24 | 2024–2026 |
| `booksocr` | 228 | 2002, 2004–2005, 2007–2022, 2024 |
| `acfr` | 1541 | 2007–2026 |
| `acfrocr` | 299 | 2007–2025 |
| `brl2027` | 1 | 2027 |

## Rows by basis

| `basis` | Rows | Years |
|---|---:|---|
| `actual` | 736 | 2003–2026 |
| `adopted` | 1345 | 2002–2026 |
| `derived` | 3 | 2024–2026 |
| `final` | 298 | 2016–2025 |
| `forecast` | 9 | 2026–2027 |
| `identified` | 3 | 2025–2026 |
| `policy` | 1 | 2026 |
| `projected` | 3 | 2007, 2009 |
| `recommended` | 57 | 2026–2027 |
| `restated` | 52 | 2007, 2011–2022 |
| `revised_projection` | 10 | 2025–2026 |
| `total_budget` | 27 | 2023 |

## Coverage by measure

Years with at least one row, on any basis. A year that is missing is
absent from the data, never zero.

| Measure | Unit | Years | Bases |
|---|---|---|---|
| `acfrgf_accommodations_taxes` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_administrative_services` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_capital_outlay` | musd | 2025 | `actual`, `adopted`, `final` |
| `acfrgf_charges_for_services` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_culture_and_recreation` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_excess_deficiency_of_revenues_over_under_expenditures` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_excise_taxes` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_franchise_occupation_taxes` | musd | 2018 | `actual`, `adopted`, `final` |
| `acfrgf_franchise_taxes` | musd | 2016–2017 | `actual`, `adopted`, `final` |
| `acfrgf_general_government` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_general_property_taxes` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_housing_and_human_services` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_interest` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_interest_and_investment_earnings` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_intergovernmental` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_leases_rents_and_royalties` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_licenses_permits_and_fines` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_long_term_notes_issued` | musd | 2021 | `actual` |
| `acfrgf_net_change_in_fund_balance` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_occupation_taxes` | musd | 2019–2025 | `actual`, `adopted`, `final` |
| `acfrgf_open_space_and_mountain_parks` | musd | 2016–2020 | `actual`, `adopted`, `final` |
| `acfrgf_other` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_payment_to_refunding_bond_escrow_agent` | musd | 2021 | `actual` |
| `acfrgf_planning_development_services` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_principal` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_proceeds_from_sale_of_capital_asset` | musd | 2021–2025 | `actual`, `adopted`, `final` |
| `acfrgf_public_safety` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_public_works` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_sale_of_goods` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_sales_and_use_taxes` | musd | 2016, 2018–2025 | `actual`, `adopted`, `final` |
| `acfrgf_sales_use_and_other_taxes` | musd | 2017 | `actual`, `adopted`, `final` |
| `acfrgf_specific_ownership_tobacco_taxes` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_total_expenditures` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_total_other_financing_sources_uses` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_total_revenues` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_transfers_in` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `acfrgf_transfers_out` | musd | 2016–2025 | `actual`, `adopted`, `final` |
| `budget_capital` | musd | 2005–2027 | `adopted`, `recommended` |
| `budget_general_fund` | musd | 2003–2027 | `actual`, `adopted`, `projected`, `recommended` |
| `budget_general_fund_revenue` | musd | 2003–2027 | `actual`, `adopted`, `projected`, `recommended` |
| `budget_operating` | musd | 2005–2027 | `adopted`, `recommended` |
| `budget_operating_dedicated` | musd | 2005–2022 | `adopted` |
| `budget_operating_general` | musd | 2005–2022 | `adopted` |
| `budget_total` | musd | 2004–2027 | `adopted`, `recommended`, `restated` |
| `deptexp_administration` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexp_citywide_debt` | musd | 2005–2018, 2025–2027 | `adopted`, `recommended` |
| `deptexp_community_services` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexp_infrastructure` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexp_parks_openspace` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexp_planning_climate` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexp_public_safety` | musd | 2005–2022, 2025–2027 | `adopted`, `recommended` |
| `deptexpfiltered_administration` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_citywide_debt` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_community_services` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_funds_outside_export` | musd | 2024–2026 | `derived` |
| `deptexpfiltered_infrastructure` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_parks_openspace` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_planning_climate` | musd | 2024–2026 | `adopted` |
| `deptexpfiltered_public_safety` | musd | 2024–2026 | `adopted` |
| `ftebucket_administration` | fte | 2007–2025 | `adopted` |
| `ftebucket_community_services` | fte | 2007–2025 | `adopted` |
| `ftebucket_infrastructure` | fte | 2007–2025 | `adopted` |
| `ftebucket_parks_openspace` | fte | 2007–2025 | `adopted` |
| `ftebucket_planning_climate` | fte | 2007–2025 | `adopted` |
| `ftebucket_public_safety` | fte | 2007–2025 | `adopted` |
| `ftefunc_administration` | fte | 2013–2017 | `adopted` |
| `ftefunc_arts` | fte | 2007–2021 | `adopted` |
| `ftefunc_city_attorney` | fte | 2007–2025 | `adopted` |
| `ftefunc_city_council` | fte | 2007–2009 | `adopted` |
| `ftefunc_city_manager_administration` | fte | 2007–2025 | `adopted` |
| `ftefunc_city_manager_communications` | fte | 2007–2025 | `adopted` |
| `ftefunc_city_manager_community_vitality` | fte | 2018–2025 | `adopted` |
| `ftefunc_city_manager_downtown_university_hill_mgt` | fte | 2007–2017 | `adopted` |
| `ftefunc_climate_initiatives` | fte | 2022–2025 | `adopted` |
| `ftefunc_community_planning_and_sustainability` | fte | 2017–2023 | `adopted` |
| `ftefunc_development` | fte | 2017–2025 | `adopted` |
| `ftefunc_energy_strategy_electric_utility` | fte | 2017, 2019–2021 | `adopted` |
| `ftefunc_environmental_affairs` | fte | 2007–2009 | `adopted` |
| `ftefunc_facility_asset_management` | fte | 2007–2022 | `adopted` |
| `ftefunc_finance` | fte | 2007–2025 | `adopted` |
| `ftefunc_fire` | fte | 2007–2025 | `adopted` |
| `ftefunc_fleet` | fte | 2007–2025 | `adopted` |
| `ftefunc_housing` | fte | 2017–2021, 2023–2025 | `adopted` |
| `ftefunc_housing_and_human_services` | fte | 2007–2016, 2022 | `adopted` |
| `ftefunc_human_resources` | fte | 2007–2025 | `adopted` |
| `ftefunc_human_services` | fte | 2017–2021, 2023 | `adopted` |
| `ftefunc_information_technology` | fte | 2007–2025 | `adopted` |
| `ftefunc_library` | fte | 2007–2023 | `adopted` |
| `ftefunc_municipal_court` | fte | 2007–2025 | `adopted` |
| `ftefunc_open_space_mountain_parks` | fte | 2007–2025 | `adopted` |
| `ftefunc_parks_and_recreation` | fte | 2007–2025 | `adopted` |
| `ftefunc_planning_development_services` | fte | 2007–2016 | `adopted` |
| `ftefunc_police` | fte | 2007–2025 | `adopted` |
| `ftefunc_total` | fte | 2007–2025 | `adopted` |
| `ftefunc_transportation` | fte | 2007–2025 | `adopted` |
| `ftefunc_utilities` | fte | 2007–2025 | `adopted` |
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
| `property_assessed_value` | musd | 2017–2026 | `actual`, `adopted`, `revised_projection` |
| `property_mill_levy` | mills | 2026–2027 | `adopted`, `recommended` |
| `property_tax_revenue` | musd | 2007–2027 | `actual`, `adopted`, `recommended`, `revised_projection` |
| `reserve_policy_pct_of_operating` | pct | 2026 | `policy` |
| `revenue_accommodation_admission_tax` | musd | 2026–2027 | `recommended` |
| `revenue_charges_for_services` | musd | 2027 | `recommended` |
| `revenue_development_impact_fees` | musd | 2026–2027 | `recommended` |
| `revenue_franchise_fees` | musd | 2027 | `recommended` |
| `revenue_grants` | musd | 2026–2027 | `recommended` |
| `revenue_intergovernmental` | musd | 2005–2017, 2019–2027 | `adopted`, `recommended` |
| `revenue_investment_earnings_bonds` | musd | 2026–2027 | `recommended` |
| `revenue_leases_rents_royalties` | musd | 2027 | `recommended` |
| `revenue_licenses_permits_fines` | musd | 2026–2027 | `recommended` |
| `revenue_misc_sales_materials_goods` | musd | 2027 | `recommended` |
| `revenue_other_grouped` | musd | 2026 | `recommended` |
| `revenue_other_revenues` | musd | 2027 | `recommended` |
| `revenue_other_unmapped` | musd | 2005–2026 | `adopted` |
| `revenue_parking` | musd | 2026–2027 | `recommended` |
| `revenue_property_tax` | musd | 2005–2027 | `adopted`, `recommended` |
| `revenue_sales_use_tax` | musd | 2005–2027 | `adopted`, `recommended` |
| `revenue_specific_ownership_tobacco` | musd | 2027 | `recommended` |
| `revenue_total` | musd | 2005–2027 | `adopted`, `recommended` |
| `revenue_utility` | musd | 2005–2027 | `adopted`, `recommended` |
| `salestaxrate_direct_city` | pct | 2007–2025 | `actual` |
| `salestaxrate_food_service` | pct | 2007–2025 | `actual` |
| `salestaxrate_total_direct_city` | pct | 2007–2025 | `actual` |
| `salesuse_audits_sales` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_audits_use` | musd | 2022–2025 | `actual` |
| `salesuse_component_residual` | musd | 2025–2026 | `adopted`, `forecast`, `revised_projection` |
| `salesuse_construction_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_consumer_business_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_motor_vehicle_use` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_rec_marijuana_addl` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_retail` | musd | 2022–2026 | `actual`, `adopted`, `forecast`, `revised_projection` |
| `salesuse_total` | musd | 2007–2027 | `actual`, `adopted`, `forecast`, `recommended`, `revised_projection` |
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
| `staffing_fte` | fte | 2002–2027 | `adopted`, `recommended`, `restated` |
| `staffing_savings` | musd | 2027 | `recommended` |
| `taxablesales_all_other` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_apparel_stores` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_automotive_trade` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_building_material_retail` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_computer_related_business_sector` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_construction_sales_tax` | musd | 2007–2014 | `actual`, `restated` |
| `taxablesales_construction_use_tax` | musd | 2007–2014 | `actual`, `restated` |
| `taxablesales_constructions_firms_sales_use_tax` | musd | 2015–2025 | `actual`, `restated` |
| `taxablesales_consumer_electronics` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_eating_places` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_food_stores` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_general_retail` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_home_furnishings` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_refunds` | musd | 2007–2011 | `actual` |
| `taxablesales_total` | musd | 2007–2025 | `actual`, `restated` |
| `taxablesales_transportation_utilities` | musd | 2007–2025 | `actual`, `restated` |
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
| `deptexp` | 2005–2022, 2025–2027 | 291 | 96 | 98 |
| `deptexpfiltered` | 2024–2026 | 60 | 20 | 12 |

Years in which each bucket has a line:

| Bucket | `deptexp` | `deptexpfiltered` |
|---|---|---|
| `public_safety` | 2005–2022, 2025–2027 | 2024–2026 |
| `infrastructure` | 2005–2022, 2025–2027 | 2024–2026 |
| `parks_openspace` | 2005–2022, 2025–2027 | 2024–2026 |
| `community_services` | 2005–2022, 2025–2027 | 2024–2026 |
| `planning_climate` | 2005–2022, 2025–2027 | 2024–2026 |
| `administration` | 2005–2022, 2025–2027 | 2024–2026 |
| `citywide_debt` | 2005–2018, 2025–2027 | 2024–2026 |
