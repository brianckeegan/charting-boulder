# 2026-09-bvsd

## Question
How many children will live in Boulder Valley School District territory over the next three decades, and is the City of Boulder losing children faster than similar cities? The district's Resilient Schools proposal projects enrollment only to 2030; this project builds the longer view from the State Demography Office's official forecasts and compares Boulder's child population with 25 similar U.S. cities across the 1990–2020 censuses.

## Decision peg
BVSD's Resilient Schools proposal (August 25, 2026): four elementary closures, a target of raising K-5 utilization from 68% to 75%, a two-classes-per-grade standard, and a five-year enrollment horizon. Broader context: BVSD's declining-enrollment planning and the generational politics surfaced in the October 2025 column.

## Layout
```
2026-09-bvsd/
├── enrollment-forecast.ipynb      SDO-grounded BVSD enrollment forecast to 2060
├── peer-projection.ipynb          City of Boulder vs 25 peer cities, 1990–2020, Hamilton–Perry to 2050
├── scripts/
│   ├── build_age_tables.py        NHGIS extracts -> data/processed/*-age-*.csv
│   └── extract_open_enrollment.py BVSD open-enrollment PDFs -> data/processed/open-enrollment/
├── data/
│   ├── raw/                       originals as downloaded; never edited
│   │   ├── places.csv             registry of the 31 places (Boulder, county ring, peer basket)
│   │   ├── sdo/                   State Demography Office, Vintage 2024
│   │   ├── nhgis/                 IPUMS NHGIS extracts 0004 and 0005 (CSV + codebooks)
│   │   └── open-enrollment/       30 BVSD "Enrollment Pattern Matrix" PDFs + manifest.json
│   └── processed/                 tidy tables written by the scripts; the notebooks read only these
└── output/                        figures and CSVs written by the notebooks (forecast-*, peers-*)
```
The notebooks download nothing and generate no synthetic data. Every input is a committed file.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| County population by single year of age, 1990–2060 (Vintage 2024) | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed CSV | `data/raw/sdo/sya-county.csv` |
| County components of change (births, deaths, net migration), 1970–2060 | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed XLSX | `data/raw/sdo/components-change-county.xlsx` |
| County household projections by type and householder age, 2010–2050 | [Colorado State Demography Office](https://demography.dola.colorado.gov/assets/html/sdodata.html) | Committed XLSX | `data/raw/sdo/household-county.xlsx` |
| Decennial census age tables, place and county, 1990 / 2000 / 2010 / 2020 | [IPUMS NHGIS](https://www.nhgis.org/) extracts nhgis0004 and nhgis0005 | Committed CSV + codebooks | `data/raw/nhgis/` |
| BVSD Open Enrollment Pattern Matrices, elementary / middle / high, 2016-17 to 2025-26 | [BVSD Planning and Engineering](https://www.bvsd.org/departments/operational-services/planning-and-engineering) | Committed PDFs + manifest (URL, bytes, sha256) | `data/raw/open-enrollment/` |
| Place registry: Boulder, the Boulder County ring, and the 25-city similar-Boulder basket | Hand-curated; basket from `2025-06-population/similar-boulder.json` | Committed CSV | `data/raw/places.csv` |
| District anchors: K-12 enrollment 2020-21, K-5 enrollment and capacity 2025-26, utilization, 5-year loss | NCES CCD; BVSD Resilient Schools deck | Hardcoded | `enrollment-forecast.ipynb` §1 |

NHGIS tables used: 1990 STF1 NP11 (age), 2000 SF1 NP012B (sex by age) and NP014C (sex by single year under 20), 2010 SF1 PCT12 and 2020 DHC PCT12 (sex by single year). The 1990 and 2000 tables have no single years above 19, so the finest grain shared by all four censuses is 19 age groups (0–4 … 15–17, 18–19, 20–24 … 85+). Extract nhgis0004 also shipped 1990 NP13 (Hispanic-origin sex by age) and 2020 P15/P18 (households and group quarters); those files are kept as shipped but not used.

Processed tables:

| File | Built by | Contents |
|---|---|---|
| `data/processed/place-age-groups.csv` | `scripts/build_age_tables.py` | 31 places × 4 censuses × 19 age groups |
| `data/processed/county-age-groups.csv` | `scripts/build_age_tables.py` | 28 counties × 4 censuses × 19 age groups (Broomfield from 2010) |
| `data/processed/place-age-single.csv` | `scripts/build_age_tables.py` | 31 places, single years 0–19, 2000 / 2010 / 2020 |
| `data/processed/open-enrollment/` | `scripts/extract_open_enrollment.py` | Tidy edgelist (attendance area → school), school, area and district summaries, name crosswalk, provenance, audit report |

The open-enrollment tables are parsed and audited but not yet used by a notebook.

## Notebooks
- `enrollment-forecast.ipynb` — resident children in Boulder + Broomfield counties 1990–2060 from the SDO forecast; births, deaths and migration; households with children; a capture-ratio conversion to BVSD enrollment under four scenarios; utilization of the post-consolidation K-5 system against the district's two-classes-per-grade rule; and the City of Boulder's 2020 age pyramid against Madison and Cambridge.
- `peer-projection.ipynb` — observed school-age (5–17) and under-5 counts, shares and changes for Boulder, the county ring and 25 peer cities, 1990–2020; a Hamilton–Perry cohort projection to 2050 on five-year age groups with a 2010→2020 backtest; a check of the engine against the SDO forecast for Boulder County; and two city-grain decompositions of fewer births versus fewer families.

## Key findings
Enrollment forecast (SDO Vintage 2024, Boulder + Broomfield):
- The resident 5–17 population peaked in 2017 (62,451). SDO has it bottoming in 2034 (49,747) and recovering to 55,080 by 2050 on an assumed birth rebound.
- Annual births fell 20% between 2000 and 2024 (3,719 → 2,980). Deaths overtake births in 2031. Net migration stays positive (about +2,400 a year, 2015–2024), so the counties keep importing adults while losing children.
- The share of households with a child falls from 32.2% (2010) to 27.6% (2025) and 24.9% (2050).
- With capture held at 2025-26 levels, K-5 enrollment reaches 9,349 in 2030 and 2030 utilization on current capacity is 64%, matching the district's 65%. The SDO-based five-year K-12 loss (about 1,990) is steeper than the district's 1,670.
- After the four closures, K-5 utilization bottoms at 72% in 2029 and passes the plan's 75% target again by 2036 under constant capture; it never does if capture erodes, if the birth rebound is removed, or if the city's under-5 trend continues (48% by 2050 in that case).
- In 2020 the City of Boulder had 72 children aged 0–4 per 100 aged 10–14 (99 in 2000, 111 in 2010). Madison had 116 and Cambridge 142.

Peer comparison (decennial census, City of Boulder vs 25 peer cities):
- Boulder's 5–17 count rose 17.4% between 2010 and 2020 (9,572 → 11,242), above the peer median of +10.8%: the 2000s birth echo moving through the schools.
- Boulder's under-5 count fell 17.9% over the same decade (peer median −4.8%), a steeper fall than 84% of peers. Children aged 0–9 in 2020 were 14.7% below what Boulder's own 2010 child ratios imply for its 2020 adults, more negative than 92% of peers.
- Boulder's school-age share (10.4% in 2020) is lower than 76% of peers.
- A Hamilton–Perry projection on the 2010→2020 ratios puts Boulder's 5–17 count at +11.5% by 2050 against a peer median of +20%; averaging the 1990–2020 ratios gives −1.7% against +15%. The ten-year backtest has a median absolute error of 6.4% across places (Boulder −15.6%).
- Run on Boulder County, the same engine projects a 2050 5–17 population 24% above the SDO forecast. The engine carries the 2000s echo forward; SDO models births directly. Read the 2050 projection as "if the 2010s repeat," not as a forecast.

(Headline figures are pinned in the final cell of each notebook and written to `output/forecast-pinned.csv` and `output/peers-pinned.csv`.)

## Limitations
- County ≠ district. Boulder County includes St. Vrain Valley SD territory and Broomfield is split; the capture ratio absorbs the overlap as a share, anchored on one K-12 and one K-5 count.
- SDO's 2040s rebound is an assumption about births and migration, not an observation; the city's under-5 series is the reason to doubt it for Boulder specifically.
- Post-plan capacity is back-derived from the deck's 68→75% and 9,732 K-5 pupils; the district has not published a school-by-school capacity table.
- Hamilton–Perry is validated to about 15 years; 2050 is 30 years out and the backtest band is a floor on uncertainty, not a confidence interval. The April 2020 enumeration sent college students home, which distorts the 18–24 counts that feed the 2010→2020 ratios for exactly this peer type.
- Annexation is inside the cohort ratios: ring towns and Sunbelt peers that grew by annexing family subdivisions show cohort gains that are not migration into a fixed area.
- Sexes are pooled in the child ratios (the 1990 table has no sex split), and 5–17 is prorated from 15–19 using each place's 2020 share.
- The land-use association question (does steeper decline travel with restrictive zoning, prices, or permits?) is out of scope: the place-level covariates, the Hauer county projections, and the IRS county-to-county flows are not in this repository.

## Reproduce
```
pip install pandas numpy matplotlib openpyxl jupyter        # notebooks and build_age_tables.py
pip install pdfplumber tabulate                             # extract_open_enrollment.py only
python scripts/build_age_tables.py                          # data/raw/nhgis -> data/processed
python scripts/extract_open_enrollment.py                   # data/raw/open-enrollment -> data/processed/open-enrollment
jupyter nbconvert --to notebook --execute --inplace enrollment-forecast.ipynb peer-projection.ipynb
```
Run everything from this directory. NHGIS data are redistributed here under IPUMS's allowance for subsets that support a specific publication; cite IPUMS NHGIS, University of Minnesota, www.nhgis.org.

## Column
*BVSD enrollment piece — URL TBD once published.*
