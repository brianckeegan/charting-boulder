#!/usr/bin/env python3
# Builder for 03-enrollment-forecast.ipynb
# A DOLA-grounded BVSD enrollment forecast to 2060: the long view the district's 2030
# horizon cannot see. Inputs: DOLA V2024 county single-year-of-age, components of change,
# and household projections (Boulder + Broomfield), NHGIS place ages (City of Boulder),
# and the district's own Aug-25-2026 proposal figures. Comments-not-docstrings in cells.

import nbformat as nbf
nb = nbf.v4.new_notebook(); cells = []
def md(t): cells.append(nbf.v4.new_markdown_cell(t.strip("\n")))
def code(t): cells.append(nbf.v4.new_code_cell(t.strip("\n")))

md(r"""
# 03 · The long view: a DOLA-grounded BVSD enrollment forecast to 2060

**Brian Keegan** · *Charting Boulder*, Boulder Reporting Lab · stage 3 of the enrollment-demography pipeline

BVSD's Resilient Schools proposal (Aug 25, 2026) projects enrollment **only to 2030** and has
declined to release the calculations behind its savings estimate. This notebook builds one
version of the longer view from the State Demography Office's official Vintage-2024 forecasts —
single-year-of-age to 2060, components of change (births, deaths, migration) to 2060, and
household composition to 2050 — for **Boulder + Broomfield counties**, the two counties BVSD
spans. It is a *descriptive, transparent* forecast: every input is public, every assumption is a
named parameter, and the district's own figures are the calibration anchors.

**What it can and cannot claim.** It forecasts the resident school-age population from the
state's assumptions and converts it to BVSD enrollment through a **capture ratio** (BVSD
enrollment ÷ resident children) anchored on the district's published counts. It does not
model open enrollment, charter/private switching, or boundary changes except as scenarios on
that ratio. Boulder County includes St. Vrain Valley SD territory (Longmont), so the ratio
absorbs that overlap — it is a share, not a headcount of "BVSD kids."
""")

md(r"""
## 1 · Setup, inputs, and the district's own anchors
""")

code(r"""
import re, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
pd.options.display.max_columns = 100
warnings.filterwarnings("ignore", category=FutureWarning)
plt.rcParams.update({"figure.dpi": 110, "figure.figsize": (9, 5.2), "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "font.size": 11})
HIGHLIGHT, CONTEXT, ACCENT, ALT = "tab:red", "tab:gray", "tab:blue", "tab:orange"
RAW = Path("data/raw"); OUT = Path("output"); OUT.mkdir(exist_ok=True)

# --- District anchors, all from BVSD's own published documents (cite in the column) ---
K12_ENROLL_2020_21 = 29_240      # NCES CCD, 2020-21 total enrollment
K5_ENROLL_2025_26  = 9_732       # Resilient Schools deck: K-5 served, non-charter
K5_CAPACITY_2025   = 14_585      # deck: K-5 capacity, non-charter
UTIL_NOW, UTIL_POST = 0.68, 0.75 # deck: districtwide utilization before/after plan
LOSS_5YR           = 1_670       # deck: projected 5-year enrollment loss (all levels)
CLASS_SIZE         = 22          # pupils per class for the 2-classes/grade rule (sensitivity below)
GRADES_K5          = 6           # K,1,2,3,4,5
ELEM_SCHOOLS_PRE, ELEM_SCHOOLS_POST = 33, 29   # approx. elementary sites before/after 4 closures
SCHOOLS_BELOW_PRE, SCHOOLS_BELOW_POST = 14, 6  # deck: schools below 2 classes/grade before/after
BVSD_COUNTIES = [13, 14]         # DOLA county codes: Boulder=13, Broomfield=14
print("anchors loaded · 2-classes/grade threshold =", CLASS_SIZE * 2 * GRADES_K5, "pupils per school")
""")

code(r"""
# DOLA Vintage 2024 files (county code = county portion of FIPS; Boulder=13, Broomfield=14)
sya = pd.read_csv(RAW / "dola/sya-county.csv", skiprows=1)
sya["countyfips"] = sya["countyfips"].astype(int)
comp = pd.read_excel(RAW / "dola/components-change-county.xlsx", skiprows=1)
hh = pd.read_excel(RAW / "dola/household-county.xlsx", skiprows=1)
for d, c in [(sya, "countyfips"), (comp, "countyfips"), (hh, "area_code")]:
    d[c] = d[c].astype(int)
assert set(BVSD_COUNTIES) <= set(sya.countyfips) and set(BVSD_COUNTIES) <= set(comp.countyfips)
assert set(BVSD_COUNTIES) <= set(hh.area_code)
print(f"DOLA: sya {sya.year.min()}-{sya.year.max()} · components {comp.year.min()}-{comp.year.max()} · households {hh.year.min()}-{hh.year.max()}")
print("vintage notes:", "sya=Mar 2025 prep · components & households=Mar 2026 prep (newer)")
""")

md(r"""
## 2 · The resident school-age population, 2000–2060

Cohorts: **0–4** (the pipeline — becomes kindergarten in five years), **5–10** (≈ K-5),
**11–17** (≈ 6-12), **5–17** (≈ K-12). Boulder + Broomfield combined.
""")

code(r"""
bb = sya[sya.countyfips.isin(BVSD_COUNTIES)]
def cohort(lo, hi):
    return (bb[bb.age.between(lo, hi)].groupby("year")["totalpopulation"].sum())
pop = pd.DataFrame({"age_0_4": cohort(0, 4), "age_5_10": cohort(5, 10),
                    "age_11_17": cohort(11, 17), "age_5_17": cohort(5, 17)})
pop["datatype"] = bb.groupby("year")["datatype"].first()
pop.index.name = "year"
# Boulder County alone (Broomfield did not exist as a county before Nov 2001 -> combined series has a seam there)
bo = sya[sya.countyfips == 13]
pop["age_5_17_boulder_only"] = bo[bo.age.between(5, 17)].groupby("year")["totalpopulation"].sum()
pop["age_0_4_boulder_only"] = bo[bo.age.between(0, 4)].groupby("year")["totalpopulation"].sum()
peak_k12 = int(pop.age_5_17.idxmax()); trough_k12 = int(pop.loc[2025:].age_5_17.idxmin())
trough_k5 = int(pop.loc[2025:].age_5_10.idxmin())
print(f"K-12 cohort (5-17): peak {peak_k12} = {pop.age_5_17.max():,.0f} · trough {trough_k12} = {pop.loc[trough_k12].age_5_17:,.0f}"
      f" · 2050 = {pop.loc[2050].age_5_17:,.0f}")
print(f"K-5 cohort (5-10): trough {trough_k5} = {pop.loc[trough_k5].age_5_10:,.0f} · 2050 = {pop.loc[2050].age_5_10:,.0f}")
print(f"Boulder County ALONE 5-17: 2025 {pop.loc[2025].age_5_17_boulder_only:,.0f} -> 2035 {pop.loc[2035].age_5_17_boulder_only:,.0f} -> 2050 {pop.loc[2050].age_5_17_boulder_only:,.0f}"
      f"  ({(pop.loc[2050].age_5_17_boulder_only/pop.loc[2025].age_5_17_boulder_only-1)*100:+.0f}% vs combined {(pop.loc[2050].age_5_17/pop.loc[2025].age_5_17-1)*100:+.0f}%)")
print("NOTE: Broomfield County was created Nov 2001; pre-2002 'combined' = Boulder County as then bounded (seam).")
pop.loc[[2000,2010,2015,2020,2025,2030,2035,2040,2050,2060]]
""")

code(r"""
fig, ax = plt.subplots()
yrs = pop.index
ax.plot(yrs, pop.age_5_17, color=HIGHLIGHT, lw=3, label="5–17 (≈K-12)")
ax.plot(yrs, pop.age_5_10, color=ACCENT, lw=2, label="5–10 (≈K-5)")
ax.plot(yrs, pop.age_0_4, color=ALT, lw=2, ls="--", label="0–4 (pipeline)")
ax.axvspan(2024.5, 2060, color=CONTEXT, alpha=0.08); ax.axvline(2030, color="k", lw=0.8, ls=":")
ax.text(2030.3, ax.get_ylim()[1]*0.97, "district's\nhorizon ends", fontsize=9, va="top")
ax.axvline(trough_k12, color=HIGHLIGHT, lw=0.8, ls=":")
ax.text(trough_k12+0.3, pop.age_5_17.min()*1.02, f"trough {trough_k12}", fontsize=9, color=HIGHLIGHT)
ax.set_title("Resident children, Boulder + Broomfield counties, 2000–2060 (DOLA V2024; shaded = forecast)")
ax.set_ylabel("Residents"); ax.set_xlabel("Year"); ax.legend(loc="lower left")
fig.tight_layout(); fig.savefig(OUT / "fig1_cohorts_2000_2060.png", bbox_inches="tight")
""")

md(r"""
## 3 · Why: births, deaths, and migration (components of change)

The "demographic destiny" test in the state's own numbers. If the child decline is mostly the
**birth echo**, it is national fertility; if resident kids fall while net migration stays
positive, the county is importing adults and not children.
""")

code(r"""
cc = (comp[comp.countyfips.isin(BVSD_COUNTIES)].groupby("year")[["estimate","births","deaths","netmig"]].sum())
cc["natural_increase"] = cc.births - cc.deaths
cc["datatype"] = comp[comp.countyfips.isin(BVSD_COUNTIES)].groupby("year")["datatype"].first()
b00, b24 = cc.loc[2000].births, cc.loc[2024].births
cross = cc.loc[2020:][cc.loc[2020:].natural_increase < 0].index.min()
print(f"annual births: {b00:,.0f} (2000) -> {cc.loc[2010].births:,.0f} (2010) -> {b24:,.0f} (2024)  = {(b24/b00-1)*100:+.0f}% since 2000")
print(f"deaths overtake births (natural decrease) in: {cross}")
print(f"net migration, 2015-2024 mean: {cc.loc[2015:2024].netmig.mean():+,.0f}/yr · projected 2025-2050 mean: {cc.loc[2025:2050].netmig.mean():+,.0f}/yr")
print(f"DOLA's fertility assumption: births rise to {cc.births.loc[2030:2050].max():,.0f} by {int(cc.births.loc[2030:2050].idxmax())} (the echo that drives the 2040s rebound)")
cc.loc[[2000,2010,2020,2024,2030,2040,2050,2060]]
""")

code(r"""
fig, ax = plt.subplots()
e = cc.loc[1990:2060]
ax.bar(e.index, e.natural_increase, color=ACCENT, alpha=0.8, label="natural increase (births − deaths)")
ax.bar(e.index, e.netmig, bottom=np.where(e.natural_increase > 0, e.natural_increase, 0), color=ALT, alpha=0.7, label="net migration")
ax.axhline(0, color="k", lw=0.8); ax.axvspan(2024.5, 2060, color=CONTEXT, alpha=0.08)
ax.set_title("Components of population change, Boulder + Broomfield, 1990–2060 (DOLA V2024)")
ax.set_ylabel("Persons per year"); ax.legend(loc="upper right")
fig.tight_layout(); fig.savefig(OUT / "fig2_components_of_change.png", bbox_inches="tight")
""")

md(r"""
## 4 · Households with children, 2010–2050

Family formation in the state's household projection: households **with kids** (one- and
multi-adult) vs. without. The share of households that contain a child is the cleanest
single number for whether a place is a place families live.
""")

code(r"""
h = hh[(hh.area_code.isin(BVSD_COUNTIES)) & (hh.age_group_id == 0)]
kids = h[h.household_type_id.isin([2, 4])].groupby("year")["total_households"].sum()
allhh = h[h.household_type_id == 0].groupby("year")["total_households"].sum()
hhk = pd.DataFrame({"hh_with_kids": kids, "hh_all": allhh})
hhk["share_with_kids_pct"] = hhk.hh_with_kids / hhk.hh_all * 100
print(f"households with kids: {hhk.loc[2010].hh_with_kids:,.0f} (2010) -> {hhk.loc[2025].hh_with_kids:,.0f} (2025) -> {hhk.loc[2050].hh_with_kids:,.0f} (2050)")
print(f"share of households with a child: {hhk.loc[2010].share_with_kids_pct:.1f}% (2010) -> {hhk.loc[2025].share_with_kids_pct:.1f}% (2025) -> {hhk.loc[2050].share_with_kids_pct:.1f}% (2050)")
hhk.loc[[2010,2015,2020,2025,2030,2040,2050]].round(1)
""")

md(r"""
## 5 · From resident children to BVSD enrollment: the capture ratio

BVSD enrolls a *share* of the two counties' children — the rest attend St. Vrain (Longmont),
charters outside the count, private, or homeschool. We anchor that share on the district's own
published counts, then forecast enrollment under three explicit scenarios:

- **A · constant capture** — BVSD keeps its current share (pure demography).
- **B · eroding capture** — share slips 0.25 pp/yr, the direction the two anchors imply.
- **C · no birth rebound** — scenario A, but DOLA's assumed post-2025 recovery of the 0–4 pipeline is
  removed (held at its 2025 level). **C2 · city trend continues** — the pipeline keeps shrinking at the
  City of Boulder's observed 2010→2020 rate. Both ask: what if the echo doesn't reach Boulder?
""")

code(r"""
cap_k12 = K12_ENROLL_2020_21 / pop.loc[2020].age_5_17
cap_k5  = K5_ENROLL_2025_26  / pop.loc[2025].age_5_10
print(f"capture ratio K-12 (2020-21 anchor): {cap_k12:.3f}   K-5 (2025-26 anchor): {cap_k5:.3f}")
years = list(range(2025, 2061))
EROSION_PP = 0.0025   # scenario B: -0.25 percentage points of capture per year
def forecast(level_col, cap, erosion=0.0, pipeline_scale=None):
    out = []
    for y in years:
        base = pop.loc[y, level_col]
        if pipeline_scale is not None:
            base = base * pipeline_scale.get(y, 1.0)
        c = max(cap - erosion * (y - 2025), 0.05)
        out.append(base * c)
    return pd.Series(out, index=years)
# scenario C ("no rebound"): DOLA projects the 0-4 pipeline recovering after 2025. Scenario C removes
# that recovery - the 0-4 cohort is held at its 2025 level - and propagates it into K-5 five years later.
# Scenario C2 ("city trend continues"): the pipeline keeps shrinking at the City of Boulder's observed
# 2010-2020 rate (3,955 -> 3,247 = -1.95%/yr). Both are what "no birth echo in Boulder" would mean.
u5_2025 = pop.loc[2025].age_0_4
pipe_no_rebound = {y: (min(1.0, u5_2025 / pop.loc[y - 5].age_0_4) if y - 5 >= 2025 else 1.0) for y in years}  # cap only DOLA's projected recovery
CITY_U5_RATE = (3247 / 3955) ** (1 / 10)      # per-year factor from the City of Boulder decennial 0-4 change
pipe_city_trend = {y: min(1.0, (u5_2025 * CITY_U5_RATE ** (y - 5 - 2025)) / pop.loc[y - 5].age_0_4) for y in years}
fc = pd.DataFrame({
    "K5_A_constant": forecast("age_5_10", cap_k5),
    "K5_B_eroding":  forecast("age_5_10", cap_k5, EROSION_PP),
    "K5_C_no_rebound":   forecast("age_5_10", cap_k5, 0.0, pipe_no_rebound),
    "K5_C2_city_trend":  forecast("age_5_10", cap_k5, 0.0, pipe_city_trend),
    "K12_A_constant": forecast("age_5_17", cap_k12),
    "K12_B_eroding":  forecast("age_5_17", cap_k12, EROSION_PP),
})
print(f"no-rebound multiplier on K-5 by 2040: {pipe_no_rebound[2040]:.3f} · city-trend by 2040: {pipe_city_trend[2040]:.3f}")
print("\nBVSD K-5 forecast (non-charter):")
print(fc[["K5_A_constant","K5_B_eroding","K5_C_no_rebound","K5_C2_city_trend"]].loc[[2025,2027,2030,2035,2040,2050,2060]].round(0))
""")

code(r"""
# check against the district's own 5-year projection
k12_2025 = fc.loc[2025].K12_A_constant
print(f"K-12 scenario A: 2025 ≈ {k12_2025:,.0f} -> 2030 ≈ {fc.loc[2030].K12_A_constant:,.0f}  (change {fc.loc[2030].K12_A_constant-k12_2025:+,.0f})")
print(f"district's stated 5-year loss: -{LOSS_5YR:,}  ->  DOLA-based loss is {'steeper' if (k12_2025-fc.loc[2030].K12_A_constant) > LOSS_5YR else 'shallower'} than the district's")
print(f"K-5 scenario A 2030 utilization on current capacity: {fc.loc[2030].K5_A_constant/K5_CAPACITY_2025*100:.0f}%  (district says 65%)")
""")

md(r"""
## 6 · Round two: what the district's own rule implies after its own horizon

The plan lifts K-5 utilization from 68% to 75% by closing four schools, and the district's
standard is **two classes per grade**. Apply the forecast to the post-consolidation system and ask:
in what year does the consolidated system fall back below that standard — and, on the state's
numbers, when does it need capacity *back*?
""")

code(r"""
K5_CAPACITY_POST = K5_ENROLL_2025_26 / UTIL_POST           # capacity implied by the deck's 75%
seats_removed = K5_CAPACITY_2025 - K5_CAPACITY_POST
threshold_per_school = CLASS_SIZE * 2 * GRADES_K5           # 2 classes/grade
print(f"post-consolidation K-5 capacity ≈ {K5_CAPACITY_POST:,.0f} (removes ≈{seats_removed:,.0f} seats)")
r2 = pd.DataFrame(index=years)
SCEN = ["K5_A_constant", "K5_B_eroding", "K5_C_no_rebound", "K5_C2_city_trend"]
for s in SCEN:
    r2[f"util_{s}"] = fc[s] / K5_CAPACITY_POST * 100
    r2[f"pupils_per_school_{s}"] = fc[s] / ELEM_SCHOOLS_POST
    r2[f"classes_per_grade_{s}"] = r2[f"pupils_per_school_{s}"] / GRADES_K5 / CLASS_SIZE
def first_year(cond):
    idx = r2.index[cond]; return int(idx[0]) if len(idx) else None
print(f"average across the {ELEM_SCHOOLS_POST} remaining elementary sites (the rule is 2 classes/grade; distribution caveat below):")
for s in SCEN:
    u = r2[f"util_{s}"]; cpg = r2[f"classes_per_grade_{s}"]
    back = first_year((r2.index > int(u.idxmin())) & (u >= UTIL_POST * 100))
    print(f"\n{s}: util 2027 {u.loc[2027]:.0f}% -> min {u.min():.0f}% ({int(u.idxmin())}) -> 2050 {u.loc[2050]:.0f}%"
          f" | avg classes/grade 2030 {cpg.loc[2030]:.2f}, 2050 {cpg.loc[2050]:.2f} | back to 75%: {back}")
r2.loc[[2027,2030,2035,2040,2045,2050,2060], [c for c in r2.columns if c.startswith("util") or "classes" in c]].round(2)
""")

code(r"""
# sensitivity: the 2-classes/grade rule is only as firm as the class size behind it
sens = []
for cs in [20, 22, 24, 26]:
    for y in [2030, 2035, 2050]:
        sens.append((cs, y, fc.loc[y].K5_A_constant / ELEM_SCHOOLS_POST / GRADES_K5 / cs))
sens = pd.DataFrame(sens, columns=["class_size", "year", "avg_classes_per_grade"]).round(2)
print("average classes per grade across remaining sites (scenario A), by assumed class size — rule is 2.0:")
print(sens.pivot(index="class_size", columns="year", values="avg_classes_per_grade"))
""")

code(r"""
fig, ax = plt.subplots()
ax.plot(years, r2.util_K5_A_constant, color=ACCENT, lw=3, label="A · constant capture")
ax.plot(years, r2.util_K5_B_eroding, color=ALT, lw=2, label="B · eroding capture")
ax.plot(years, r2.util_K5_C_no_rebound, color=HIGHLIGHT, lw=2, ls="--", label="C · no birth rebound")
ax.plot(years, r2.util_K5_C2_city_trend, color=HIGHLIGHT, lw=1.5, ls=":", label="C2 · city trend continues")
ax.axhline(UTIL_POST*100, color="k", lw=0.8, ls=":"); ax.text(2025.3, UTIL_POST*100+0.6, "plan's 75% target", fontsize=9)
ax.axhline(UTIL_NOW*100, color=CONTEXT, lw=0.8, ls=":"); ax.text(2025.3, UTIL_NOW*100+0.6, "today's 68%", fontsize=9, color=CONTEXT)
ax.axvline(2030, color="k", lw=0.8, ls=":"); ax.text(2030.3, ax.get_ylim()[0]+1, "district's horizon", fontsize=9)
ax.set_title("K-5 utilization of the post-consolidation system, 2025–2060")
ax.set_ylabel("Utilization (%)"); ax.set_xlabel("Year"); ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig(OUT / "fig3_round_two_utilization.png", bbox_inches="tight")
""")

md(r"""
## 7 · The leading indicator: the City of Boulder's inverting age pyramid

County forecasts smooth over the city. The 2020 decennial (NHGIS) shows Boulder's children by
single year of age: **each younger cohort is smaller than the one above it**, while in Madison
or Cambridge the youngest cohort is the largest. This is the observed pipeline behind
scenario C.
""")

code(r"""
NH = RAW / "nhgis/nhgis0004_csv"
def table_labels(cb_path, src):
    cb = open(cb_path, encoding="latin-1").read().replace("\r", "")
    pref = re.search(rf"Source code:\s*{re.escape(src)}\s*\n\s*NHGIS code:\s*([A-Z0-9]+)", cb).group(1)
    return dict(re.findall(rf"^\s+({pref}\d+):\s+(.+)$", cb, flags=re.M))
SEX = r"(?:Male|Female)\s*(?::|>>)\s*"
def age_of(d):
    d = d.strip()
    if not re.match(SEX, d): return None
    if re.search(r"Under 1\b|Under 5\b", d): return 0
    m = re.match(SEX + r"(\d+) (?:year|to)", d); return int(m.group(1)) if m else None
d20 = pd.read_csv(NH / "nhgis0004_ds259_2020_place.csv", dtype=str, encoding="latin-1")
v20 = table_labels(NH / "nhgis0004_ds259_2020_place_codebook.txt", "PCT12")
def pyramid(st, pl):
    r = d20[(d20.STATEA == st) & (d20.PLACEA == pl)]
    v = np.zeros(18)
    for var, lab in v20.items():
        a = age_of(lab)
        if a is not None and a <= 17: v[a] += float(r[var].iloc[0])
    return v
PL = {"Boulder": ("08","07850"), "Madison": ("55","48000"), "Cambridge": ("25","11000"),
      "Fort Collins": ("08","27425"), "Longmont": ("08","45970")}
pyr = pd.DataFrame({k: pyramid(*v) for k, v in PL.items()}); pyr.index.name = "age"
bands = pd.DataFrame({k: [pyr[k][0:5].sum(), pyr[k][5:10].sum(), pyr[k][10:15].sum(), pyr[k][15:18].sum()]
                      for k in PL}, index=["0-4","5-9","10-14","15-17"])
print("2020 children by band (decennial):"); print(bands.astype(int))
print("\n0-4 as share of 10-14 (100 = pipeline replacing itself):")
print((bands.loc["0-4"] / bands.loc["10-14"] * 100).round(0).astype(int))
""")

code(r"""
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharey=False)
for ax, city in zip(axes, ["Boulder", "Madison", "Cambridge"]):
    v = pyr[city]; idx = pyr[city] / v[10:15].mean() * 100
    ax.barh(pyr.index, idx, color=HIGHLIGHT if city == "Boulder" else CONTEXT)
    ax.axvline(100, color="k", lw=0.8, ls=":")
    ax.set_title(city); ax.set_xlabel("per 100 of the 10–14 cohort"); ax.set_ylabel("age" if city == "Boulder" else "")
fig.suptitle("Children by single year of age, 2020 — Boulder hollows from the bottom; peers do not", y=1.03)
fig.tight_layout(); fig.savefig(OUT / "fig4_age_pyramids.png", bbox_inches="tight")
""")

md(r"""
## 8 · Pinned numbers & limits
""")

code(r"""
def _r(x, n=0): return None if x is None or not np.isfinite(x) else (round(float(x), n) if n else int(round(float(x))))
uA = r2.util_K5_A_constant
PINNED = {
  "resident_5_17_peak_year": peak_k12, "resident_5_17_trough_year": trough_k12,
  "resident_5_17_2025": _r(pop.loc[2025].age_5_17), "resident_5_17_trough": _r(pop.loc[trough_k12].age_5_17),
  "resident_5_17_2050": _r(pop.loc[2050].age_5_17),
  "births_change_since_2000_pct": _r((b24/b00-1)*100, 1), "natural_decrease_first_year": int(cross) if cross else None,
  "hh_with_kids_share_2010_pct": _r(hhk.loc[2010].share_with_kids_pct, 1), "hh_with_kids_share_2050_pct": _r(hhk.loc[2050].share_with_kids_pct, 1),
  "capture_ratio_k12_2020": _r(cap_k12, 3), "capture_ratio_k5_2025": _r(cap_k5, 3),
  "k5_forecast_2030_A": _r(fc.loc[2030].K5_A_constant), "k5_forecast_2035_A": _r(fc.loc[2035].K5_A_constant),
  "k5_forecast_2050_A": _r(fc.loc[2050].K5_A_constant), "k5_forecast_2035_C_no_rebound": _r(fc.loc[2035].K5_C_no_rebound), "k5_forecast_2050_C2_city_trend": _r(fc.loc[2050].K5_C2_city_trend),
  "post_plan_k5_capacity": _r(K5_CAPACITY_POST), "util_min_pct_A": _r(uA.min(), 1), "util_min_year_A": int(uA.idxmin()),
  "avg_classes_per_grade_2030_A": _r(r2.loc[2030].classes_per_grade_K5_A_constant, 2), "util_2050_pct_A": _r(uA.loc[2050], 1),
  "city_boulder_0_4_per_100_of_10_14": _r(bands.loc["0-4","Boulder"] / bands.loc["10-14","Boulder"] * 100),
}
pinned = pd.Series(PINNED, name="value").to_frame(); pinned.to_csv(OUT / "pinned_forecast.csv")
fc.round(0).to_csv(OUT / "bvsd_enrollment_forecast_2025_2060.csv"); r2.round(2).to_csv(OUT / "round_two_utilization.csv")
pop.to_csv(OUT / "resident_cohorts_2000_2060.csv"); cc.to_csv(OUT / "components_of_change.csv"); hhk.round(1).to_csv(OUT / "households_with_kids.csv")
print(pinned.to_string())
""")

md(r"""
### Limits — read before citing

1. **County ≠ district.** Boulder County includes St. Vrain (Longmont) territory; Broomfield is split.
   The capture ratio absorbs the overlap as a share, so shifts in *where* families live inside the
   counties can move enrollment with no change in resident children.
2. **The rebound is DOLA's assumption, not an observation.** The 2040s recovery rests on births
   rising to ~2,800/yr and net migration staying positive. The City of Boulder's observed 0–4
   collapse (scenario C) is the reason to doubt it for the city specifically. Present both.
3. **Capture is single-anchored.** One K-12 anchor (2020-21) and one K-5 anchor (2025-26); the
   erosion rate in B is a parameter, not an estimate. Replace with the CDE October-count series.
4. **The 2-classes/grade rule depends on class size**, which the district sets; the sensitivity
   table shows how the "excess schools" count moves with it.
5. **Post-plan capacity is back-derived** from the deck's 68→75% and 9,732, not from a released
   school-by-school capacity table — the district has not published one.
6. **No behavioral feedback.** Closures may themselves change capture (families leaving, choosing
   elsewhere); the forecast holds behavior fixed except through scenario B.
7. **Vintage mismatch is minor but real**: single-year-of-age is the Mar-2025 prep; components and
   households are Mar-2026. All are Vintage 2024.
""")

nb["cells"] = cells
nbf.write(nb, "03-enrollment-forecast.ipynb")
print(f"assembled 03-enrollment-forecast.ipynb: {len(cells)} cells")
