# Charting Boulder — Tipped Wages and Affordability

**A reproducible analysis of Boulder's 2026 tipped wage debate.**

This repository contains the data pipeline and op-ed for *"Boulder's $40 Number"* (working title), a Charting Boulder column for Boulder Reporting Lab examining the empirical foundations of the city's April 2026 tip offset deliberation and Boulder County's November 2025 minimum wage rollback.

A restaurant industry survey figure of $40 per hour, cited by Councilmember Matt Benjamin in a March 30, 2026 council Hotline message as evidence that tipped workers earn enough to absorb a slower wage trajectory, is wrong by nearly half compared to U.S. Census data — and is also, almost exactly, the hourly wage required to afford a modest apartment in Boulder County under standard affordability guidelines. This notebook documents both findings end-to-end.

---

## Author

Brian C. Keegan, Ph.D.  
Department of Information Science, University of Colorado Boulder  
April 2026

---

## License

MIT License. Code, figures, and derived data may be reused with attribution. Underlying data sources retain their original public-domain status (U.S. Census, BLS, HUD) or original licensing terms (Zillow Research is freely redistributable; see Zillow's terms of use).

---

## What this notebook does

The notebook (`tipped_wages.ipynb`) is structured as a sequential pipeline. Each section pulls a specific dataset from a public source, transforms it into a tidy long-format DataFrame, and uses it to construct one component of the affordability argument. The pipeline produces five figures and one Monte Carlo simulation.

**Sections, in order:**

1. **Boulder minimum wage and tipped wage schedule** — full wage and tipped wage history 2015–2026 from City of Boulder ordinances and Colorado CDLE records, with the $3.02 state-floor tip offset.
2. **Council's four policy scenarios (2025–2030)** — projects tipped wages under each option the city council advanced on April 2, 2026, with the Colorado 25%-of-full-wage offset cap as a binding constraint.
2b. **Option E — Councilmember Benjamin's Modified 2a** — adds the Benjamin freeze proposal (March 30 Hotline) under both strict and lenient interpretations, with sunset paths post-2029.
3. **HUD Fair Market Rents** — Boulder County 2-bedroom FMR, 1983–2026, from HUD's historical FMR dataset.
4. **Zillow Observed Rent Index (ZORI)** — Boulder metro market rent, 2015–2025, from Zillow Research public CSVs.
5. **ACS median gross rent** — Boulder County, 2015–2024, from ACS 1-Year tables B25064 and B25058.
6. **ACS housing cost burden** — Boulder County renter cost-burden rates, 2015–2024, from ACS Table B25070.
7. **ACS food service worker earnings** — Boulder County full-time, year-round male and female food service worker median earnings, 2019–2024, from ACS Table B24022.
7b. **Benjamin's scenario table — ACS rebuttal** — runs Benjamin's five worker income scenarios under both his $40/hr assumption and the ACS-calibrated baseline; reports break-even hours loss.
8. **Census County Business Patterns** — Boulder County NAICS 722 (food service) establishment and employment counts, 2012–2023.
9. **Affordability gap analysis** — computes hourly wages required under the 30% rule for each rent series; compares against each policy scenario.
10. **Figure 1** — Tipped wage vs. rent, indexed growth 2015=100.
11. **Figure 2** — The $40/hr claim vs. ACS reality, horizontal bar chart.
12. **Figure 3** — Policy scenario projections 2025–2030 against rent affordability threshold.
13. **Figure 4** — Food service sector health from CBP.
14. **Summary statistics** — consolidated headline numbers.
15. **Methodology and limitations** — documented assumptions and caveats.
16. **Monte Carlo simulation** — N=8,000 simulations across tip income (log-normal), hours per week (truncated normal), and rent growth (normal); produces a distribution of worker income outcomes per scenario.
17. **Figure 5 — Fan chart** — median income trajectory with 25th–75th and 10th–90th percentile bands per scenario, overlaid on the rent affordability threshold band. **Recommended op-ed centerpiece figure.**

---

## Data sources

All data is publicly accessible without authentication. The notebook downloads each source at runtime; no manual data preparation is required.

| Source | Used for | Access |
|---|---|---|
| U.S. Census Bureau — ACS 1-Year | Median rent, cost burden, food service earnings | `api.census.gov/data/{year}/acs/acs1` |
| U.S. Census Bureau — County Business Patterns | Food service establishments and employment | `api.census.gov/data/{year}/cbp` |
| HUD — Fair Market Rents | 2-bedroom FMR, 1983–2026 | `huduser.gov/portal/datasets/fmr/FMR_2Bed_1983_2026.xlsx` |
| Zillow Research | Boulder metro Observed Rent Index | `files.zillowstatic.com/research/public_csvs/zori/` |
| MIT Living Wage Calculator | Living wage benchmarks | `livingwage.mit.edu/counties/08013` (manual) |
| City of Boulder ordinances | Minimum wage and tip offset history | Public records (hardcoded) |
| Council Hotline (Item 7A, 4/2/2026) | Benjamin's $40/hr claim and scenario table | Public records |

---

## How to run

**Requirements:**

```
python >= 3.10
pandas
numpy
matplotlib
scipy
openpyxl
```

Install with:

```bash
pip install pandas numpy matplotlib scipy openpyxl
```

**Run the notebook:**

```bash
jupyter notebook tipped_wages.ipynb
```

Run all cells in order. Total runtime is approximately 2–3 minutes; most of that is the HUD FMR Excel download (~2.4 MB) and the API calls to the Census Bureau. No caching is implemented; repeated runs re-download all sources.

**Output figures** are written to the working directory:

- `fig1_wage_rent_indexed.png`
- `fig2_claim_vs_reality.png`
- `fig3_scenario_projections.png`
- `fig4_cbp_sector_health.png`
- `fig5_fan_chart_monte_carlo.png`

---

## Key empirical findings

Reported throughout the column and reproducible from the notebook:

- **Boulder County food service worker median earnings (ACS, 2024):** male $46,305/yr ($23.15/hr); female $44,970/yr ($22.49/hr). Both figures cover full-time year-round workers only and skew upward from the part-time and seasonal reality of most restaurant work.
- **Industry survey claim (Benjamin, March 30 Hotline):** $40/hr ≈ $80,000/yr at 40 hrs/wk × 50 wks. Roughly 1.7× to 1.9× the ACS median.
- **Wage required to afford median Boulder County rent (30% rule, 2024 ACS gross rent $1,966/mo):** $38.30/hr.
- **Wage required to afford 2026 HUD FMR 2-bedroom ($2,124/mo):** $42.48/hr.
- **Wage required to afford 2025 Zillow ZORI ($2,249/mo):** $44.98/hr.
- **Boulder County renter cost burden (ACS, 2023):** 59% are cost-burdened (>30% of income on rent); 44.7% are severely burdened (>40%).
- **Food service sector health (CBP):** 858 establishments in 2019, 877 in 2023 — net growth across the pandemic period, no aggregate evidence of crisis.
- **Monte Carlo finding:** Even accepting Benjamin's inflated $40/hr figure at face value, a worker still falls roughly $12,000 short of the income needed to afford median Boulder County rent under the 30% rule.

---

## Methodology notes

**ACS B24022 covers full-time, year-round workers only.** Because many food service workers are part-time, seasonal, or have variable hours, ACS figures likely *overstate* typical food service worker earnings relative to the full tipped workforce. This is the conservative direction for the argument: even the upward-skewed measure is half the industry claim.

**Three rent sources, three different things measured:**

- *HUD FMR* — 40th percentile of standard-quality units; policy benchmark.
- *ACS median gross rent* — actual renter-reported, includes utilities; most representative of what Boulder County renters pay.
- *Zillow ZORI* — observed market listings; sensitive to recent leases and skews toward newly listed units.

The notebook reports all three rather than choosing one, because the affordability gap holds across all three measures.

**Scenario projections** assume post-2026 full-wage growth at +3.5%/yr (near CPI) and rent growth at +3.5%/yr from 2023 ACS baseline. Sensitivity to these assumptions is captured in the Monte Carlo.

**Pre-2000 Boulder geography:** Some longer historical series (notably HUD FMR 1983–2026) reflect "Boulder-Longmont, CO PMSA" before 2004 and "Boulder, CO" CBSA after. Geographic boundaries differ slightly; comparisons across the 2004 break should account for this.

**Monte Carlo parameter choices** are documented inline in the simulation cell:

- Tip income: log-normal with $10/hr median (moderate casual-dining estimate); sensitivity examined at $4/hr (ACS-implied lower bound) and $26/hr (Benjamin's claim).
- Hours per week: truncated normal, mean 30, SD 6, range [15, 45].
- Rent growth: normal, mean 3.5%/yr, SD 1.5%, clipped [0%, 10%].

These distributions are defensible defaults, not estimated parameters; the fan chart should be read as showing what reasonable ranges of uncertainty produce, not as a predictive forecast.

---

## What the data does not capture

Some things are not in any of these datasets, and the column says so explicitly:

- The specific worker working two jobs to make rent.
- The restaurant owner who genuinely cannot raise prices and is trying to keep their staff employed.
- The political question of whose voices are being heard in council chambers and whose are not.
- The structural composition of Boulder's elected bodies and how that shapes whose testimony is credited.