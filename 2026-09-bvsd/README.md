# 2026-09-bvsd

## Question
BVSD's Resilient Schools proposal recommends closing four elementary schools. Which demographic future is the district planning for, and are the causes it lists for the decline as separate as its list makes them look?

## Decision peg
BVSD's Resilient Schools proposal (August 25, 2026): four elementary closures, a target of raising K-5 utilization from 68% to 75%, a two-classes-per-grade standard, and a five-year enrollment horizon. The board votes September 22, 2026.

## Layout
```
2026-09-bvsd/
├── BVSD.ipynb                     the canonical notebook for the column
├── appendix/                      earlier analyses, archived and still executable
│   ├── enrollment-forecast.ipynb  SDO enrollment forecast to 2060 + open-enrollment dynamics
│   └── peer-projection.ipynb      Boulder vs 25 peer cities, Hamilton–Perry to 2050
├── scripts/
│   ├── build_age_tables.py        NHGIS extracts -> data/processed/*-age-*.csv
│   └── extract_open_enrollment.py BVSD open-enrollment PDFs -> data/processed/open-enrollment/
├── data/
│   ├── raw/                       originals as downloaded; never edited
│   │   ├── places.csv             registry of the 31 places (Boulder, county ring, peer basket)
│   │   ├── sdo/                   State Demography Office, Vintage 2024
│   │   ├── nhgis/                 IPUMS NHGIS extracts 0004 and 0005 (CSV + codebooks)
│   │   ├── bvcp/                  15 editions of the comprehensive plan, Markdown
│   │   └── open-enrollment/       30 BVSD "Enrollment Pattern Matrix" PDFs + manifest.json
│   └── processed/                 tidy tables written by the scripts
└── output/                        figures and CSVs (bvsd-*, forecast-*, peers-*)
```
`BVSD.ipynb` is the only notebook a reader following the column's link needs to open. Everything it uses is a committed file except two live pulls: three house-price and income series from FRED, and one supplementary American Community Survey check from the Census API.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| County population by single year of age, 1990–2060 (Vintage 2024) | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed CSV | `data/raw/sdo/sya-county.csv` |
| County components of change (births, deaths, net migration), 1970–2060 | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed XLSX | `data/raw/sdo/components-change-county.xlsx` |
| County household projections by type and householder age, 2010–**2050** | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed XLSX | `data/raw/sdo/household-county.xlsx` |
| Decennial census age tables, place and county, 1990 / 2000 / 2010 / 2020 | [IPUMS NHGIS](https://www.nhgis.org/) extracts nhgis0004 and nhgis0005 | Committed CSV + codebooks | `data/raw/nhgis/` |
| Boulder Valley Comprehensive Plan, 15 editions 1977–2026 draft | [City of Boulder](https://bouldercolorado.gov/services/boulder-valley-comprehensive-plan); Markdown conversions from `2026-03-bvcp/plans/` | Committed Markdown | `data/raw/bvcp/` |
| County house price index (1975–) and county median household income (1989–) for Boulder and the 25 peer counties | [FHFA All-Transactions HPI](https://www.fhfa.gov/data/hpi) and [Census SAIPE](https://www.census.gov/programs-surveys/saipe.html), both via [FRED](https://fred.stlouisfed.org/) (`ATNHPIUS{county}A`, `MHI{ST}{county}A052NCEN`) | API at runtime — needs `FRED_API_KEY` | (fetched in `BVSD.ipynb`) |
| ACS 1-year population under 5 by sex, City of Boulder and three eligible peers, 2008–2024 | [U.S. Census Bureau](https://www.census.gov/programs-surveys/acs/) table B01001 | API at runtime — needs `CENSUS_API_KEY` | (fetched in `BVSD.ipynb`) |
| BVSD Open Enrollment Pattern Matrices, 2016-17 to 2025-26 | [BVSD Planning and Engineering](https://www.bvsd.org/departments/operational-services/planning-and-engineering) | Committed PDFs + manifest (URL, bytes, sha256) | `data/raw/open-enrollment/` |
| Place registry: Boulder, the Boulder County ring, and the 25-city similar-Boulder basket | Hand-curated; basket from `2025-06-population/similar-boulder.json` | Committed CSV | `data/raw/places.csv` |
| District anchors: K-12 enrollment 2020-21, K-5 enrollment and capacity 2025-26, utilization, five-year loss | NCES CCD; BVSD Resilient Schools proposal | Hardcoded | `BVSD.ipynb` §2 |

The household projection stops at 2050 and is not extended by any model; every series that ends earlier than the others says so where it appears.

NHGIS tables used: 1990 STF1 NP11 (age), 2000 SF1 NP012B (sex by age) and NP014C (sex by single year under 20), 2010 SF1 PCT12 and 2020 DHC PCT12 (sex by single year). The 1990 and 2000 tables have no single years above 19, so the finest grain shared by all four censuses is 19 age groups (0–4 … 15–17, 18–19, 20–24 … 85+). Extract nhgis0004 also shipped 1990 NP13 (Hispanic-origin sex by age) and 2020 P15/P18; those files are kept as shipped but not used.

Every price and income figure is county grain. The Boulder MSA is Boulder County and contains no other county, so the two labels describe one territory; the peer basket has no metropolitan series that matches it, and every peer county has both a price and an income series. `similar-boulder.json` gives Iowa City the county code 19087 while naming Johnson County; 19087 is Henry County and Johnson County is 19103. Both `places.csv` and `2025-06-population/similar-boulder.json` now carry the corrected code, and no finding in this folder depended on it.

The BVCP corpus is 15 editions, not the 17 files in `2026-03-bvcp/plans/`. Two of those files (`bvcp-1978.md`, `bvcp-1978-apr.md`) are printings of the 1977 plan's 1978 revision and share 79–83% of their sentences with each other; both are left out.

Processed tables:

| File | Built by | Contents |
|---|---|---|
| `data/processed/place-age-groups.csv` | `scripts/build_age_tables.py` | 31 places × 4 censuses × 19 age groups |
| `data/processed/county-age-groups.csv` | `scripts/build_age_tables.py` | 28 counties × 4 censuses × 19 age groups (Broomfield from 2010) |
| `data/processed/place-age-single.csv` | `scripts/build_age_tables.py` | 31 places, single years 0–19, 2000 / 2010 / 2020 |
| `data/processed/open-enrollment/` | `scripts/extract_open_enrollment.py` | Tidy edgelist (attendance area → school), school, area and district summaries, name crosswalk, provenance, audit report |

## Notebooks
- `BVSD.ipynb` — the canonical notebook. The district's own baseline; the peer comparison over two decades; the two divergent projections to 2060 and the gap between them; the shared mechanism behind falling births and rising housing cost; and the plan's own vocabulary across fifteen editions. Headline numbers are pinned to `output/bvsd-pinned.csv`.
- `appendix/enrollment-forecast.ipynb` — the fuller SDO-grounded enrollment forecast, four capture-ratio scenarios, post-consolidation utilization against the two-classes-per-grade rule, and ten years of open-enrollment matrices.
- `appendix/peer-projection.ipynb` — the fuller peer analysis: observed counts for all 31 places, the Hamilton–Perry engine with its backtest and a three-vintage sensitivity, and two city-grain decompositions.

The appendix notebooks are archived rather than deleted, and still execute top to bottom from their own directory.

## Key findings
The district's baseline reproduces:
- Applying the capture ratio to the state's resident forecast gives 2030 K-5 utilization of 64% on current capacity, against the district's own 65%. The implied five-year K-12 loss (about 1,990) is steeper than the district's 1,670.

The peer comparison splits in two:
- Boulder's school-age (5–17) count rose 17.4% between 2010 and 2020, above the peer median of +10.8%. The cohort already in the schools grew faster in Boulder than in the median peer.
- Boulder's under-5 count fell 17.9% over the same decade against a peer median of −4.8%, steeper than 84% of peers. Children aged 0–9 in 2020 were 14.7% below what Boulder's own 2010 child ratios imply for its 2020 adults, more negative than 92% of peers.
- In 2020 the City of Boulder had 72 children aged 0–4 per 100 aged 10–14. Madison had 116 and Cambridge 142.
- The annual survey cannot settle the question either way. Boulder's ACS 1-year under-5 estimate moves by 936 children between consecutive years on average, against a decennial 2010→2020 change of 708, and carries the widest margin of error of the four eligible cities.

The two futures diverge:
- The state forecasts 52,276 resident 5–17s in the two counties by 2060. A Hamilton–Perry projection carrying the 2010→2020 cohort transition forward gives 72,898, a gap of 39%. The gap runs from +17% at 2030 to +39% at 2060, narrowing into 2050 where the state's assumed birth rebound lands.
- Carried through the district's own arithmetic, K-5 utilization of the post-consolidation system troughs at 72% in 2029 and reaches 75% by 2060 under the state's forecast; under the cohort projection it never falls below 97% and reaches 113%. The two differ by 38 percentage points of utilization on the same capacity.
- The cohort projection also implies 22% more county residents by 2060 than the state's. Its extra children come with extra adults.

Births and housing cost move together:
- Annual births in the two counties fell 20% between 2000 and 2024. Deaths overtake births in 2031. Net migration stays positive throughout, about +2,400 a year over 2015–2024 and higher in the forecast, so the counties keep importing adults while the child cohorts shrink.
- The share of households with a child falls from 32.2% (2010) to 27.6% (2025) to 24.9% (2050), where the state's household projection ends.
- Boulder County house prices are 17.7 times their 1975 index level.
- Measured consistently at county grain, house price per dollar of median household income stood at 164 in Boulder County in 2024 against a base of 100 in 2000. The peer median is 140, and only three of the 25 peer counties sit above Boulder.
- Across fifteen editions of the comprehensive plan, three vocabularies move differently, measured per 1,000 words. Preservation language rises from 4.6 in 1977 to a peak of 6.4 in 2015 and falls to 3.5 in the 2026 draft. Children-and-schools language is flat for fifty years: 1.0 in 1977, a peak of 2.0 in 2001, and 1.5 in 2026. Housing-affordability language starts at zero, passes children and schools in 2015, and reaches 1.9 by 2026. The plan learned to talk about housing cost. It did not learn to talk about children.

(Headline figures are pinned in the final section of each notebook: `output/bvsd-pinned.csv`, `output/forecast-pinned.csv`, `output/peers-pinned.csv`.)

## Limitations
- Nothing here is causal. The plan-vocabulary, price and demographic series are described together because they move together; no analysis in this folder identifies an effect of land-use policy on births, prices, or enrollment.
- The cohort projection is not a forecast. It carries the 2010→2020 transition forward unchanged, including the 2000s birth echo moving through Boulder's schools, and it implies a substantially larger county. Hamilton–Perry is validated in the literature to roughly 15 years; 2060 is 40 years past the launch, and the backtest error (6.4% median absolute, at ten years) is a floor on uncertainty rather than a confidence interval.
- The state forecast is not an observation either. Its post-2025 recovery rests on assumptions about fertility and migration. Presenting both is the point.
- County is not district. Boulder County includes St. Vrain Valley territory and Broomfield is split; the capture ratio absorbs the overlap as a share, anchored on one K-12 count and one K-5 count.
- Post-plan capacity is back-derived from the proposal's 68→75% and 9,732 K-5 pupils; the district has not published a school-by-school capacity table.
- The April 2020 enumeration sent college students home, which moves the 18–24 counts feeding the 2010→2020 cohort ratios for Boulder and much of its peer basket.
- Annexation sits inside the cohort ratios: ring towns and Sunbelt peers that grew by annexing family subdivisions show cohort gains that are not migration into a fixed area.
- Sexes are pooled in the child ratios (the 1990 table has no sex split), and 5–17 is prorated from 15–19 using each place's 2020 share. The Hamilton–Perry K-5 cohort takes the 5–9 group plus a fifth of the 10–14 group.
- The price-to-income ratio is a relative index, not a multiple of income. A value of 150 means prices grew half again as fast as median household income since 2000; it does not say a house costs 1.5 times a year's income.
- The peer lines in the housing chart are counties, not cities. For several peers the county is far larger than the city the basket names, so the line describes a much bigger housing market than the city. Boulder is the unusual case where city, county and metropolitan area sit close together.
- County median household income publishes no value for 1990, 1991, 1992, 1994 or 1996 in any county, which leaves three isolated years before the annual series becomes continuous in 1997. New Haven County's income stops in 2021, when Connecticut replaced counties with planning regions for federal statistics.
- The plan-vocabulary counts are surface matches over converted text, and they count what the plan says rather than what it did. The three vocabularies are reported separately and never divided into each other: a ratio between two word lists is set by how many terms each list holds and how common those words are, so it measures the lists. The notebook prints a leave-one-out table showing how far each series moves when any single term is dropped. Two term choices carry weight: `famil*` is matched only where it is not part of "single-family" and the like, because 180 of its 343 occurrences are zoning vocabulary; and character is matched as a phrase rather than a stem, because the bare stem picks up 271 occurrences of "characteristics" and "characterized".
- The enrollment matrices (appendix) count BVSD students only, so exits to charters outside the count, private school, or homeschool are invisible. Two of the thirty files fail the row or column reconciliation by one pupil.
- The American Community Survey one-year file gives an annual reading of the City of Boulder's under-5 cohort, and the notebook pulls it, but it cannot referee the decennial finding. Boulder's margin of error runs 23% of the estimate at the median and the series swings between consecutive years by more than the decennial count moved across the whole 2010s. It is reported as a check that failed to resolve, not as corroboration. There is no 2020 release.

## Reproduce
```
pip install pandas numpy matplotlib seaborn openpyxl requests jupyter   # BVSD.ipynb and build_age_tables.py
pip install pdfplumber tabulate                                        # extract_open_enrollment.py only
export FRED_API_KEY=...                    # free from https://fred.stlouisfed.org/docs/api/api_key.html
export CENSUS_API_KEY=...                  # free from https://api.census.gov/data/key_signup.html
python scripts/build_age_tables.py         # data/raw/nhgis -> data/processed
python scripts/extract_open_enrollment.py  # data/raw/open-enrollment -> data/processed/open-enrollment
jupyter nbconvert --to notebook --execute --inplace BVSD.ipynb
```
Run everything from this directory; the appendix notebooks run from `appendix/`. NHGIS data are redistributed here under IPUMS's allowance for subsets that support a specific publication; cite IPUMS NHGIS, University of Minnesota, www.nhgis.org.

## Column
*BVSD enrollment piece — URL TBD once published.*
