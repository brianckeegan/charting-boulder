# Data for the published charts

The column's charts are built in [Datawrapper](https://www.datawrapper.de/). Every file here is written by section 10 of `alternatives-analysis.ipynb`, so it changes only when the notebook is rerun. Do not edit these files by hand. Change the notebook and rerun it.

**The layout.** Line and bar charts have one row per year or category and one column per series. Scatter plots have one row per point. Each map has a GeoJSON file and a CSV with the same key column. Percentages are written as percentages (62.6, not 0.626). A blank cell is a value that does not exist, not a zero.

**Maps.** Choose a choropleth map in Datawrapper, upload the `.geojson` file as your own map, and pick the key column named below. Then paste or upload the `.csv` file with the same number, and match on that key. The shapes are in WGS84, simplified to about 20 m, and written to RFC 7946.

**The titles below are suggestions.** Each one states a claim that the notebook's printed output supports. If a rerun changes a number, change the title too.

## Section 1 — Colorado closes schools all the time

### `dw-01-colorado-openings-closures.csv`
- **Draft chart:** figure 1, `output/alt-fig1-openings-closures.png`.
- **Chart type:** column chart. Use `opened` above the axis and `closed_below_axis` below it (this is `closed` with a minus sign). Put `schools_open` on a separate line chart.
- **Title:** "Colorado opened 1,397 schools and closed 651 between 1987 and 2023"
- **Source:** Colorado Department of Education and NCES Common Core of Data, compiled in the 2026-10-alternatives archive.
- **Caveat:** A closure is a school that leaves the panel. A merger or a new school code can look like a closure. The archive's `schools.csv` gives a confidence for each one.

### `dw-02-closure-rate-by-size.csv`
- **Draft chart:** figure 2, `output/alt-fig2-closure-hazard.png`.
- **Chart type:** column chart of `closures_per_1000` by `band`.
- **Title:** "Below 250 pupils, a Colorado school closes about ten times as often as one above 400"
- **Source:** 2026-10-alternatives archive, school-years 2000–2023.
- **Caveat:** This is the share of school-years that were a school's last. It is not a rule that any district wrote down.

### `dw-03-front-range-enrolment.csv` and `dw-03b-front-range-enrolment-index.csv`
- **Draft chart:** none. The notebook prints the change since 2017 under the section 10 heading "Boulder Valley against the rest of the Front Range, since 1977".
- **Chart type:** line chart. Show Boulder Valley in color and the other districts in gray. The first file has pupils. The second file has an index where 2017 = 100 (Boulder Valley's peak year).
- **Title (index):** "Boulder Valley is one of 11 large Front Range districts with fewer pupils than in 2017"
- **Source:** Colorado Department of Education pupil membership, 1977–2024, compiled in the 2026-10-alternatives archive.
- **Universe:** every district in the ten Front Range counties of section 9 with more than 10,000 pupils in 2024. There are 17 districts.
- **Caveats:** The values are K-12 fall membership. For 1977–85 the yearbooks print only a total with a different definition, so each district's earlier totals are scaled by its own ratio of the two measures in 1986–87 (0.955 to 0.999). That removes a step at 1986 that is not a change in enrolment. **2000 is blank** because it is a known gap in the archive. Do not let Datawrapper draw a line across it without a note.

### `dw-04-bvsd-schools.csv`
- **Draft chart:** figure 3, `output/alt-fig3-bvsd-schools.png`.
- **Chart type:** line chart of `schools`. `enrollment` and `teacher_fte` are included for a second chart or for tooltips.
- **Title:** "Boulder Valley has closed schools before"
- **Source:** 2026-10-alternatives archive, 1986–2024.
- **Caveat:** `enrollment` here is the sum over schools, which is not the same as the district total in `dw-03`.

## Section 2 — What the demography supports

### `dw-05-bvsd-projection.csv`
- **Draft chart:** figure 4, `output/alt-fig4-projection.png`.
- **Chart type:** line chart. Use `schools_observed` as a solid line and `schools_fitted` as a dashed line, and fill the area between `schools_low` and `schools_high`. Make a second chart with the `teacher_fte_` columns.
- **Title:** "The forecast puts Boulder Valley near 54 schools in 2060, against 56 today"
- **Source:** 2026-10-alternatives archive; Colorado State Demography Office, Vintage 2024.
- **Caveat:** The fitted line comes from 178 Colorado districts, 1990–2024, with district fixed effects. The band is the 95% interval on the fitted line, from 2024 onwards. It is not the range for any one year.

## Section 3 — The levers and what they cost

### `dw-06-lever-combinations-2027.csv` and `dw-06b-lever-combinations-by-year.csv`
- **Draft chart:** figure 5b, `output/alt-fig5b-lever-combinations.png`.
- **Chart type:** a Datawrapper table for the 2027 file. For a chart of the trade-off, use a scatter plot of `children moved` against `pupils to recruit`, with one point for each combination. The by-year file has 2024, 2027, 2030 and 2040.
- **Title:** "Closing five schools moves twice as many children; keeping all 27 needs 382 more recruits"
- **Source:** BVSD elementary attendance areas and capacity (web maps edited 20 February 2026); BVSD Resolution 26-27; 2026-10-alternatives archive; SDO Vintage 2024.
- **Caveats:**
  - The approved plan uses the receivers it names. Where it divides an area among schools, the pupils are split in proportion to each receiver's empty seats, which leaves the fewest pupils over capacity. Every pupil at a closing school is assumed to follow the area.
  - A redraw is proportional to capacity, not a real line.
  - Gold Hill, Jamestown and Nederland are outside both redraw and recruitment, but they are still counted below the bar.
  - The costs are counts of children and pupils. They are not dollars.

### `dw-07-attendance-areas.geojson` and `dw-07-attendance-areas.csv`
- **Draft chart:** none. The map shows the table in section 3.
- **Chart type:** choropleth map. **Key: `area_name`.** Color by `status` for the plan, or by `utilisation_2027_approved` for the load.
- **Title:** "The approved plan fills three of the schools that take closing areas beyond their capacity"
- **Source:** BVSD elementary attendance areas (web maps edited 20 February 2026); BVSD Resolution 26-27; 2026-10-alternatives archive; 2020 Census blocks for `children_5_10`.
- **Columns:**
  - `status` is one of: closes; elementary programme closes (Monarch, which becomes a middle school); takes a closing area; mountain school; stays open; not modelled.
  - `pupils_2027_no_change` is the 2024-25 K-5 roll scaled to the 2027 forecast.
  - `pupils_2027_approved` is that roll after the approved plan.
  - `over_capacity_2027` is blank for the areas that close.
- **Not modelled:** BC-Mesa and BC-Creekside are shared zones with no building of their own. Meadowlark has no elementary capacity in the layer.
- **Caveat:** The layer's own `area_code` is not unique (Lafayette and Meadowlark share 153). That is why the key is the name.

### `dw-08-schools.csv`
- **Chart type:** symbol map or locator map, from `latitude` and `longitude`. Use the `dw-07` GeoJSON as the base map.
- **Source:** as for `dw-07`, with school locations from the NCES Common Core of Data directory.

## Section 4 and 5 — Why a school is small, and since when

### `dw-09-why-small.csv`
- **Draft chart:** figure 6, `output/alt-fig6-why-small.png`.
- **Chart type:** scatter plot. Put `children_living_in_area` on x and `share_staying` on y, size by `enrolment`, and color by `status`.
- **Title:** "Two different reasons a Boulder Valley school is small"
- **Source:** BVSD Enrollment Pattern Matrix, 2025-26.
- **Caveat:** The matrices name areas in their own way ("Mesa*", "Monarch K-8"), so the names do not match `dw-07` exactly.

### `dw-10-neighbourhood-share.csv`
- **Draft chart:** figure 7, `output/alt-fig7-oe-trend.png`.
- **Chart type:** make two line charts. One shows `share_staying`. The other shows `children_living_index` and `children_in_own_school_index` (2017 = 100).
- **Title:** "Boulder Valley's neighbourhood schools have lost pupils faster than they have lost children"
- **Source:** BVSD Enrollment Pattern Matrices, 2016-17 to 2025-26.
- **Caveat:** `year` is the year in which the school year ends.

### `dw-11-catchment-change-by-area.csv`
- **Chart type:** arrow plot or range plot from `share_2017` to `share_2026`, one row for each area, colored by `status`.
- **Title:** "16 of 30 areas have lost more than five points of their catchment since 2017"
- **Source:** BVSD Enrollment Pattern Matrices, 2016-17 and 2025-26.
- **Caveat:** Gold Hill and Jamestown have 11 children each, so their changes are large and mean little.

## Section 6 — Is Boulder unusual?

### `dw-12-statewide-adjustment.csv` and `dw-12b-average-school-size.csv`
- **Draft chart:** figure 8, `output/alt-fig8-statewide.png`.
- **Chart type:** use a histogram or dot plot of `schools_change` for the first file. Use a bar chart of `average_school` for the second. Highlight the row where `boulder_valley` is true.
- **Title:** "Boulder Valley is in the middle of Colorado on both readings"
- **Source:** 2026-10-alternatives archive; SDO Vintage 2024 county forecasts to 2060.
- **Caveat:** Each district is given the forecast for its county. Districts in the same county get the same `pop_change`.

## Section 8 — What happened after a closure round

### `dw-13-closure-impacts.csv`
- **Draft chart:** figure 10, `output/alt-fig10-closure-impacts-staggered.png`.
- **Chart type:** make three line charts (schools, enrolment, staff). For each, show the effect line and fill the area between `_low` and `_high`. The `_section7` columns are the earlier two-way fixed-effects estimate. They are included for comparison and are not needed.
- **Title:** "A closure round removes buildings, and leaves the pupils and the teachers"
- **Source:** 2026-10-alternatives archive; Callaway–Sant'Anna estimator on clean comparisons, 1,000 district resamples.
- **Caveat:** The values are percent differences from the year before the round. The intervals are 95%.

## Section 9 — Where the children went

### `dw-14-tract-change.geojson` and `dw-14-tract-change.csv`
- **Draft chart:** figure 11, `output/alt-fig11-tract-change.png`.
- **Chart type:** choropleth map. **Key: `tract2000`.** Color by `pct_change` on a diverging scale that is centered on zero.
- **Title:** "Boulder Valley has as many school-age children as in 2000, in different places"
- **Source:** U.S. Census Bureau, 2000 Summary File 1 and 2020 PL 94-171, both on 2000 tract boundaries.
- **Caveat:** The values are children aged 5 to 17. The file keeps only the 2000 tracts that lie at least 90% inside the district. The 2020 count includes only the blocks inside the district, but the 2000 count is for the whole tract.

### `dw-15-density-children.csv`
- **Draft chart:** figure 12, `output/alt-fig12-density-children.png`.
- **Chart type:** scatter plot. Put `people_per_sq_mi` on a **log** x-axis and `child_share` on y, and color by `group`.
- **Title:** "Denser tracts have fewer children, but the rule is weak"
- **Source:** 2020 Census PL 94-171 by block; TIGER/Line 2023 tracts.
- **Universe:** 1,091 tracts with more than 200 residents in ten Front Range counties.
- **Caveat:** The rank correlation is −0.12.
