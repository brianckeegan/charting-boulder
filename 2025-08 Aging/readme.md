# Charting Boulder: Aging

**Author:** [Brian C. Keegan, Ph.D.](http://www.brianckeegan.com)\
**Date:** August 2025\
**License:** [MIT License](https://opensource.org/licenses/MIT)

## Overview

This notebook assembles local, state, and federal data to analyze how the age composition of Boulder County and its municipalities is changing and what that means for budgets, housing, mobility, civic participation, and equity. It cleans and joins datasets, builds reproducible charts/maps, and prepares exportable figures for a newsroom op-ed and the **Charting Boulder** column.

## What this notebook does

- Loads population estimates and projections (e.g., age 65+ vs. under‑25) and visualizes long‑run trends.
- Maps where older residents and voters are concentrated while cautioning against polygon‑based misreads.
- Analyzes election turnout by age group across recent local elections.
- Relates age structure to Boulder’s sales‑tax dependent revenue and consumer‑spending profiles.
- Explores housing fit for aging in place (e.g., ‘missing‑middle’ and ADUs) with simple supply/context indicators.
- Surfaces equity gaps by tenure, income, disability, and heat/wildfire exposure where available.

## Data sources

- (See inline code cells for source links and file paths.)

## Requirements (inferred)

- matplotlib
- pandas
- numpy
- seaborn
- geopandas
- json
- requests

## File Structure

- `Aging.ipynb` — Main analysis notebook
- `sya-county.xlsx` — County-level components of population change
- `Precincts.geojson` — GeoJSON defining voting precincts
- `fred_signup.png` - Image for notebook on accessing FRED API

## License

This project is licensed under the MIT License. See the [LICENSE](https://opensource.org/licenses/MIT) file for details.

## Contact

Questions or feedback? Contact [Brian C. Keegan](http://www.brianckeegan.com) or open an issue.

