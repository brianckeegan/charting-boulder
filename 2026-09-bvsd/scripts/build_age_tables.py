#!/usr/bin/env python3
"""Tidy age tables from the NHGIS decennial extracts.

Inputs (data/raw/):
  nhgis/nhgis0005_ds120_1990_{place,county}.csv   1990 STF1  NP11    age (grouped)
  nhgis/nhgis0004_ds146_2000_{place,county}.csv   2000 SF1   NP012B  sex by age (grouped)
                                                             NP014C  sex by single year, under 20
  nhgis/nhgis0004_ds173_2010_{place,county}.csv   2010 SF1   PCT12   sex by single year
  nhgis/nhgis0004_ds259_2020_{place,county}.csv   2020 DHC   PCT12   sex by single year
  places.csv                                      registry of places (and their counties) to keep

Outputs (data/processed/):
  place-age-groups.csv    place_fips, year, age_group, age_lo, age_hi, pop
  county-age-groups.csv   county_fips, year, age_group, age_lo, age_hi, pop
  place-age-single.csv    place_fips, year, age, pop   (ages 0-19; 2000, 2010, 2020)

The 1990 and 2000 tables do not report single years of age above 19, so the
finest age grain shared by all four censuses is the 19-group scheme below
(0-4 ... 15-17, 18-19, 20-24 ... 85+). Sexes are summed. Every variable in
each source table must land in exactly one group, and every closed group must
be fully covered, or the script stops.

Usage (from 2026-09-bvsd/): python scripts/build_age_tables.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NH = ROOT / "data" / "raw" / "nhgis"
PROC = ROOT / "data" / "processed"

GROUPS = [(0, 4), (5, 9), (10, 14), (15, 17), (18, 19), (20, 24), (25, 29), (30, 34),
          (35, 39), (40, 44), (45, 49), (50, 54), (55, 59), (60, 64), (65, 69),
          (70, 74), (75, 79), (80, 84), (85, 999)]
SINGLE_MAX = 19  # single years of age available in every census from 2000 on

# year -> (file stem, table prefix for the grouped/full table, prefix for single-year-under-20 table)
SOURCES = {
    1990: ("nhgis0005_ds120_1990", "ET3", None),   # NP11: no sex split, grouped
    2000: ("nhgis0004_ds146_2000", "FMZ", "FNG"),  # NP012B grouped; NP014C single 0-19
    2010: ("nhgis0004_ds173_2010", "IC3", "IC3"),  # PCT12 single years
    2020: ("nhgis0004_ds259_2020", "VCG", "VCG"),  # PCT12 single years
}

SEX = re.compile(r"^(?:Male|Female)\s*(?:>>|:)\s*")


def label_range(label: str) -> tuple[int, int] | None:
    """'Male: 7 to 9 years' -> (7, 9); 'Under 5 years' -> (0, 4); '85 years and over' -> (85, 999).
    Returns None for subtotal rows (Total / Male / Female)."""
    s = SEX.sub("", label.strip())
    if s in ("Total", "Male", "Female"):
        return None
    if m := re.match(r"^Under (\d+) years?$", s):
        return 0, int(m.group(1)) - 1
    if m := re.match(r"^(\d+) years? and over$", s):
        return int(m.group(1)), 999
    if m := re.match(r"^(\d+) (?:to|and) (\d+) years?$", s):
        return int(m.group(1)), int(m.group(2))
    if m := re.match(r"^(\d+) years?$", s):
        return int(m.group(1)), int(m.group(1))
    raise ValueError(f"unparsed age label: {label!r}")


def codebook_vars(stem: str, geog: str, prefix: str) -> dict[str, tuple[int, int]]:
    """{variable: (lo, hi)} for every age variable of one table, from the shipped codebook."""
    text = (NH / f"{stem}_{geog}_codebook.txt").read_text(encoding="latin-1")
    out = {}
    for var, label in re.findall(rf"^\s+({prefix}\d{{3}}):\s+(.+?)\s*$", text, flags=re.M):
        rng = label_range(label)
        if rng is not None:
            out[var] = rng
    if not out:
        raise ValueError(f"no {prefix} variables found in {stem}_{geog} codebook")
    return out


def group_of(rng: tuple[int, int]) -> tuple[int, int]:
    lo, hi = rng
    hits = [g for g in GROUPS if lo >= g[0] and hi <= g[1]]
    if len(hits) != 1:
        raise ValueError(f"age range {rng} does not fit exactly one group")
    return hits[0]


def check_coverage(vars_: dict[str, tuple[int, int]]) -> None:
    """Every closed group must be tiled exactly once by the distinct ranges assigned to it."""
    for g in GROUPS:
        ranges = {r for r in vars_.values() if group_of(r) == g}
        if g[1] == 999:
            assert ranges, f"group {g} has no source variable"
            continue
        width = sum(hi - lo + 1 for lo, hi in ranges)
        assert width == g[1] - g[0] + 1, f"group {g} covered by {sorted(ranges)}"


def read_table(year: int, geog: str, prefix: str, ids: set[str]) -> tuple[pd.DataFrame, dict]:
    stem, _, _ = SOURCES[year]
    vars_ = codebook_vars(stem, geog, prefix)
    id_cols = ["STATEA", "PLACEA"] if geog == "place" else ["STATEA", "COUNTYA"]
    df = pd.read_csv(NH / f"{stem}_{geog}.csv", dtype=str, encoding="latin-1",
                     usecols=id_cols + list(vars_))
    width = 5 if geog == "place" else 3
    df["fips"] = df["STATEA"].str.zfill(2) + df[id_cols[1]].str.zfill(width)
    df = df[df["fips"].isin(ids)].drop(columns=id_cols)
    df[list(vars_)] = df[list(vars_)].apply(pd.to_numeric)
    return df, vars_


def grouped_long(year: int, geog: str, ids: set[str]) -> pd.DataFrame:
    _, prefix, _ = SOURCES[year]
    df, vars_ = read_table(year, geog, prefix, ids)
    check_coverage(vars_)
    long = df.melt(id_vars="fips", var_name="var", value_name="pop")
    long[["age_lo", "age_hi"]] = pd.DataFrame(
        [group_of(vars_[v]) for v in long["var"]], index=long.index)
    out = (long.groupby(["fips", "age_lo", "age_hi"], as_index=False)["pop"].sum()
           .assign(year=year))
    return out


def single_long(year: int, ids: set[str]) -> pd.DataFrame:
    _, _, prefix = SOURCES[year]
    df, vars_ = read_table(year, "place", prefix, ids)
    keep = {v: r[0] for v, r in vars_.items() if r[0] == r[1] and r[0] <= SINGLE_MAX}
    assert sorted(set(keep.values())) == list(range(SINGLE_MAX + 1)), f"{year}: single ages incomplete"
    long = df.melt(id_vars="fips", value_vars=list(keep), var_name="var", value_name="pop")
    long["age"] = long["var"].map(keep)
    return long.groupby(["fips", "age"], as_index=False)["pop"].sum().assign(year=year)


def finish(frames: list[pd.DataFrame], id_name: str) -> pd.DataFrame:
    out = pd.concat(frames, ignore_index=True).rename(columns={"fips": id_name})
    out["age_group"] = out.apply(
        lambda r: f"{r.age_lo}+" if r.age_hi == 999 else f"{r.age_lo}-{r.age_hi}", axis=1)
    out["pop"] = out["pop"].astype(int)
    cols = [id_name, "year", "age_group", "age_lo", "age_hi", "pop"]
    return out[cols].sort_values([id_name, "year", "age_lo"]).reset_index(drop=True)


def main() -> None:
    reg = pd.read_csv(ROOT / "data" / "raw" / "places.csv", dtype=str)
    places = set(reg["place_fips"])
    counties = set(reg["county_fips"]) | {"08014", "08123"}  # + Broomfield (BVSD) and Weld (Erie)

    place_groups = finish([grouped_long(y, "place", places) for y in SOURCES], "place_fips")
    county_groups = finish([grouped_long(y, "county", counties) for y in SOURCES], "county_fips")
    single = (pd.concat([single_long(y, places) for y in (2000, 2010, 2020)], ignore_index=True)
              .rename(columns={"fips": "place_fips"})[["place_fips", "year", "age", "pop"]]
              .astype({"pop": int}).sort_values(["place_fips", "year", "age"]).reset_index(drop=True))

    # sanity: single-year 0-4 and 5-9 must equal the grouped 0-4 and 5-9 in 2000/2010/2020
    chk = (single.assign(age_lo=(single["age"] // 5) * 5).query("age_lo <= 5")
           .groupby(["place_fips", "year", "age_lo"])["pop"].sum().rename("single"))
    g = place_groups.set_index(["place_fips", "year", "age_lo"])["pop"]
    joined = pd.concat([chk, g], axis=1, join="inner")
    assert (joined["single"] == joined["pop"]).all(), "single-year and grouped tables disagree"

    missing = places - set(place_groups["place_fips"])
    assert not missing, f"registry places absent from NHGIS: {sorted(missing)}"
    n_by_year = place_groups.groupby("year")["place_fips"].nunique()
    assert (n_by_year == len(places)).all(), f"places per year: {n_by_year.to_dict()}"

    PROC.mkdir(parents=True, exist_ok=True)
    place_groups.to_csv(PROC / "place-age-groups.csv", index=False)
    county_groups.to_csv(PROC / "county-age-groups.csv", index=False)
    single.to_csv(PROC / "place-age-single.csv", index=False)
    print(f"place-age-groups.csv   {len(place_groups):>6,} rows · {place_groups.place_fips.nunique()} places × {sorted(SOURCES)}")
    print(f"county-age-groups.csv  {len(county_groups):>6,} rows · {county_groups.county_fips.nunique()} counties "
          f"(Broomfield 08014 exists only from 2010)")
    print(f"place-age-single.csv   {len(single):>6,} rows · ages 0-{SINGLE_MAX} · years {sorted(single.year.unique().tolist())}")


if __name__ == "__main__":
    main()
