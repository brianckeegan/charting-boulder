# Charting Boulder: Population Growth

**Author:** [Brian C. Keegan, Ph.D.](http://www.brianckeegan.com)\
**Date:** June 2025\
**License:** [MIT License](https://opensource.org/licenses/MIT)

---

## Overview

This Jupyter notebook analyzes long-term population trends for the City of Boulder and Boulder County. Using historical and contemporary data from the Colorado State Demography Office and the U.S. Census Bureau, it challenges the prevailing narrative that Boulder is experiencing explosive population growth and overcrowding. The analysis provides evidence-based context for op-eds and public discussions about growth, housing, and planning in Boulder.

## Data Sources

- **[Colorado State Demography](https://demography.dola.colorado.gov/assets/html/sdodata.html) office**
  - County and municipal population estimates and forecasts
  - Components of population change (births, deaths, migration)
  - Historical census data (decennial)

## What the Notebook Does

- **Imports and cleans** population data for Boulder County and the City of Boulder
- **Visualizes**:
  - Absolute population growth from 1970 to present
  - Growth rates
  - Boulder’s share of Colorado’s total population
  - Comparative rankings of Boulder among other Colorado municipalities
- **Analyzes**:
  - Long-term vs. recent growth trends
  - Differences between city and county patterns

## Key Findings (from the analysis)

- Boulder’s population growth has slowed since the late 20th century
- Recent years show near-zero growth or even small declines
- Surrounding counties are growing more rapidly than Boulder

## How to Use This Notebook

1. **Install dependencies** (see below)
2. **Download data files** as described in the notebook, or update paths to match your environment
3. **Run the notebook** cell by cell to reproduce all analyses and visualizations

## Requirements

- Python 3.x
- Jupyter Notebook or JupyterLab
- Required libraries:
  - `pandas`
  - `numpy`
  - `matplotlib`
  - `seaborn`
  - `requests`
  - `json`

You can install the Python dependencies with:

```
pip install pandas numpy matplotlib seaborn requests
```

## File Structure

- `Population.ipynb` — Main analysis notebook
- `components-change-county.csv` — County-level components of population change
- `historical-census.csv` — Historical census counts by area
- `county-muni-timeseries.csv` — Time series of county and municipal populations

## License

This project is licensed under the MIT License. See the [LICENSE](https://opensource.org/licenses/MIT) file for details.

## Contact

Questions or feedback? Contact [Brian C. Keegan](http://www.brianckeegan.com) or open an issue.

