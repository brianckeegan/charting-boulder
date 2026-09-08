# `data/raw/` — canonical sources for the BVSD enrollment-demography analysis

Immutable originals only. Nothing here is edited in place; all cleaning lives in the
notebook's loaders and writes to `data/processed/`. FIPS are stored as zero-padded
strings everywhere. Flip `STUB_MODE = False` in the notebook once these are present.

## Historical place age structure — NHGIS / IPUMS (the H1 outcome + CCR base)
- Portal: https://www.nhgis.org/  ·  API: https://developer.ipums.org/  ·  Python: `ipumspy`
- Pull **single-year-of-age by sex, at PLACE grain, decennial 1990 / 2000 / 2010 / 2020**.
  Tables: 1990 STF1, 2000 SF1, 2010 SF1, 2020 DHC age-by-sex. Request as one extract.
- Geographic crosswalks (place, Sept-2025 vintage) to standardize annexation across decades:
  https://www.nhgis.org/geographic-crosswalks
- Save as: `nhgis_place_syoa_1990_2020.csv` (+ the codebook .txt the extract ships with).

## County control — Hauer county projections, RE-RUN AT SINGLE-YEAR (SSP2)
- Repo: https://github.com/mathewhauer/county_projections_official
- Published 5-year file (reference / smell-test): OSF https://dx.doi.org/10.17605/OSF.IO/9YNFC
  → `SSP_asrc.csv.zip` (GEOID/year/age/sex/race, 2020–2100, five-year ages).
- **Module 3 rebuilds this single-year for target counties only.** Validate the rebuild on the
  2000→2020 decade-aligned backtest (decennial single-year exists only at census years).
- Save rebuilt control as: `hauer_singleyear_ssp2_targetcounties.csv`.

## Migration flows — Hauer IRS-migration-data, EXTENDED to ~2022
- Repo: https://github.com/mathewhauer/IRS-migration-data
- Published flat file (1990–2010): `DATA-PROCESSED/county_migration_data.txt`.
- Extend with newer IRS SOI county-to-county files via `R/999-master_script.R`:
  https://www.irs.gov/statistics/soi-tax-stats-migration-data
  ⚠ Format/methodology seam ~2011–2012 — flag, do not pretend a continuous series.
- Save as: `county_migration_data_1990_2022.txt` (origin/dest 5-digit FIPS; `99999` = <10 filers).

## Land-use restrictiveness — National Zoning Atlas (H2 covariate)
- Portal: https://www.zoningatlas.org/  ·  CO report: https://www.zoningatlas.org/zoning-report-colorado-2025
- Tier-1 (Colorado) coverage is complete; Tier-2 coverage is partial — populate where available,
  leave NA otherwise (do not silently shrink the sample). Snapshot, not a time series.
- Save as: `nza_place_restrictiveness.csv` (place_fips, share single-family-only land, min-lot,
  multifamily by-right flags → collapse to one 0–1 restrictiveness scalar).

## Prices — Zillow Research (H2 covariate)
- https://www.zillow.com/research/data/  → city-level ZHVI (all homes, mid-tier) and ZORI.
- Save as: `zillow_zhvi_city.csv`, `zillow_zori_city.csv`.

## Supply — Census Building Permits Survey (H2 covariate)
- https://www.census.gov/construction/bps/  → PLACE-level annual permits by structure type.
  Use "Estimates with Imputation" consistently. Latest annual released first working day of May.
- Save as: `bps_place_permits.csv`.

## Enrollment peg — Colorado CDE + NCES
- CDE pupil membership: https://www.cde.state.co.us/cdereval/pupilcurrentdistrict
- NCES CCD (national district enrollment): https://nces.ed.gov/ccd/ccddata.asp
- BVSD declining-enrollment context: https://www.bvsd.org/current-topics/declining-enrollment
- Save as: `cde_district_membership.csv`, `nces_ccd_district.csv`.

## Colorado-only reconciliation — DOLA State Demography Office
- https://demography.dola.colorado.gov/assets/html/sdodata.html
- County single-year-of-age 1990–2060: https://storage.googleapis.com/co-publicdata/sya-county.csv
- County components of change: via the SDO data page (births/deaths/net migration).
- Use only to cross-check Boulder County against the Hauer-based control; report divergence
  as disclosed uncertainty, not a silent choice.

## Tier-2 college-town basket
- https://github.com/brianckeegan/charting-boulder/blob/main/2025-06%20Population/similar-boulder.json
  (place_fips / county_fips / MSA per peer; drives the real-mode place registry.)
