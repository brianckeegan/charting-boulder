"""
OEWS Extractor — Boulder MSA, Colorado statewide, US national (local files)
============================================================================
Reads BLS OEWS zip files from three local folders and writes three separate
long-format panel CSVs, one per geography:

    oews_metro_raw/     oesm??ma.zip   ->  oews_boulder_combined.csv
    oews_state_raw/     oes??st.zip    ->  oews_colorado_combined.csv
    oews_national_raw/  oesm??nat.zip  ->  oews_national_combined.csv

Drop whichever zips you have into the matching folder; scopes with no zips are
skipped. Download them from https://www.bls.gov/oes/tables.htm (the
"Metropolitan" / "State" / "National" bulk files for each year). BLS pattern:
    https://www.bls.gov/oes/special.requests/oesm{YY}ma.zip   (metro)
    https://www.bls.gov/oes/special.requests/oes{YY}st.zip     (state, older)
    https://www.bls.gov/oes/special.requests/oesm{YY}nat.zip  (national)

For each scope EVERY occupation BLS publishes is kept; no occupation
subsetting happens here.  Slicing to specific occupations is left to
downstream analysis.

Why this is non-trivial — the BLS files change shape across vintages:

  * Headers move.    1997-2000 bury the column header under a metadata block
                     (rows 32-43, and the two 2000 splits even differ: 34 vs 42);
                     2001-2025 put it on row 0.  We never assume a fixed row —
                     the header is DETECTED by signature anywhere in the first 80
                     rows, so an offset of 8-12 (or any other) is handled too.
  * Files split.     1997-2013 split the metro estimates across 2-3 spreadsheets
                     (MSA_..._1/_2/_3); Boulder lands in exactly one of them.
                     We read every data file in each zip, filter, then concat.
  * Columns rename.  Percentiles are `h_wpct10` in 1998-2002 and `h_pct10` from
                     2003 on; 2000 truncates `occ_title` to `occ_titl`; 2019+
                     lead with `area`/`area_title`.  A synonym map normalises all.
  * Area is renamed. 1997-2004 = "Boulder-Longmont, CO PMSA" (code 1125);
                     2005-2025 = "Boulder, CO" (CBSA 14500).
  * Occupations recode. 1997-1998 use old 5-digit OES codes; 1999+ use SOC.
                     We keep occ_code verbatim and document the break.

Requirements:
    pip install pandas openpyxl xlrd tqdm
Run:
    python oews_boulder.py
"""

import io
import re
import hashlib
import logging
import zipfile
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# ── Configuration ─────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
LOG_LEVEL = logging.INFO

# ── Scope definitions ─────────────────────────────────────────────────────────
# Each scope maps a zip folder + glob to a geographic filter and output files.
# National has no filter — the entire file IS the national estimate.
SCOPES = {
    "boulder": {
        "label":      "Boulder MSA",
        "zip_dir":    HERE / "oews_metro_raw",
        "zip_glob":   "oes*ma.zip",
        "output_csv": HERE / "oews_boulder_combined.csv",
        "prov_csv":   HERE / "oews_boulder_provenance.csv",
        "dict_md":    HERE / "oews_boulder_data_dictionary.md",
    },
    "colorado": {
        "label":      "Colorado statewide",
        "zip_dir":    HERE / "oews_state_raw",
        "zip_glob":   "oes*st.zip",
        "output_csv": HERE / "oews_colorado_combined.csv",
        "prov_csv":   HERE / "oews_colorado_provenance.csv",
        "dict_md":    HERE / "oews_colorado_data_dictionary.md",
    },
    "national": {
        "label":      "US national",
        "geo_name":   "United States",   # national files pre-2019 carry no area col
        "zip_dir":    HERE / "oews_national_raw",
        "zip_glob":   "oes*nat.zip",
        "output_csv": HERE / "oews_national_combined.csv",
        "prov_csv":   HERE / "oews_national_provenance.csv",
        "dict_md":    HERE / "oews_national_data_dictionary.md",
    },
}

# ── Geographic filter parameters ──────────────────────────────────────────────
# Boulder: match on name first (robust across all vintages), fall back to code.
# NB: 0880 is Billings MT — do NOT add it to BOULDER_AREA_CODES.
BOULDER_NAME_RE    = re.compile(r"boulder", re.IGNORECASE)
BOULDER_AREA_CODES = {"1125", "14500"}

# Colorado state: name match, then prim_state abbreviation, then FIPS.
# State files use "Colorado" as the area_name; prim_state is "CO".
CO_NAME_RE    = re.compile(r"^colorado$", re.IGNORECASE)
CO_PRIM_STATE = {"CO"}
CO_FIPS       = {"08", "8"}

# US national: the national row(s). Match a clean U.S./United States label, or
# the national area code, so we never grab a stray "U.S." substring from a
# title column.
US_NAME_RE    = re.compile(r"^\s*(u\.?\s?s\.?|united states|u\.?s\.? total"
                           r"|national|all u\.?s\.?)\s*$", re.IGNORECASE)
US_AREA_CODES = {"99", "0000000", "00000", "N0000000", "099", "1"}

# Inner files that are NOT occupation tables — skip them in every scope.
SKIP_FILE_RE = re.compile(r"(^~\$)|(\baMSA)|(\bBOS)|(field_desc)|(file_desc)"
                          r"|(readme)|(layout)|(glossary)", re.IGNORECASE)
DATA_EXT = re.compile(r"\.(xlsx?|csv|txt)$", re.IGNORECASE)


# ── Year inference from filename ──────────────────────────────────────────────
def year_from_filename(path: Path):
    """
    oesm24ma.zip -> 2024 | oes97st.zip -> 1997 | oesn04st.zip -> 2004.
    BLS prefixes the year with nothing (oes97), 'm' (oesm24), or 'n' (oesn04),
    so accept an optional single letter before the two-digit year.
    """
    m = re.search(r"oes[mn]?(\d{2})(ma|st|nat)", path.stem, re.IGNORECASE)
    if not m:
        return None
    yy = int(m.group(1))
    return 1900 + yy if yy >= 97 else 2000 + yy


# ── Column normalisation ──────────────────────────────────────────────────────
COL_MAP = {
    "area_code":    ["area", "area_code", "msa_code", "pmsa_code", "cbsa_code",
                     "state_code", "naics_code"],
    "area_name":    ["area_name", "area_title", "area_titl", "msa", "pmsa",
                     "cbsa", "state", "state_name"],
    "prim_state":   ["prim_state", "state", "st"],
    "occ_code":     ["occ_code", "soc", "oes_code", "occ"],
    "occ_title":    ["occ_title", "occ_titl", "occupation", "occupation_title",
                     "oes_title"],
    "occ_group":    ["occ_group", "o_group", "group"],
    "tot_emp":      ["tot_emp", "emp", "employment"],
    "emp_prse":     ["emp_prse"],
    "h_mean":       ["h_mean", "hrly_mean"],
    "a_mean":       ["a_mean", "annl_mean"],
    "mean_prse":    ["mean_prse"],
    "h_median":     ["h_median", "hrly_median"],
    "a_median":     ["a_median", "annl_median"],
    "h_pct10":      ["h_pct10", "h_wpct10"],
    "h_pct25":      ["h_pct25", "h_wpct25"],
    "h_pct75":      ["h_pct75", "h_wpct75"],
    "h_pct90":      ["h_pct90", "h_wpct90"],
    "a_pct10":      ["a_pct10", "a_wpct10"],
    "a_pct25":      ["a_pct25", "a_wpct25"],
    "a_pct75":      ["a_pct75", "a_wpct75"],
    "a_pct90":      ["a_pct90", "a_wpct90"],
    "jobs_1000":    ["jobs_1000"],
    "loc_quotient": ["loc_quotient", "loc quotient", "loc_q"],
    "annual":       ["annual"],
    "hourly":       ["hourly"],
}
_SYNONYM = {syn.upper().strip(): canon
            for canon, syns in COL_MAP.items() for syn in syns}

CANONICAL_ORDER = [
    "year", "area_code", "area_name", "prim_state",
    "occ_code", "occ_title", "occ_group",
    "tot_emp", "emp_prse",
    "h_mean", "a_mean", "mean_prse",
    "h_median", "a_median",
    "h_pct10", "h_pct25", "h_pct75", "h_pct90",
    "a_pct10", "a_pct25", "a_pct75", "a_pct90",
    "jobs_1000", "loc_quotient", "annual", "hourly",
]

_AREA_TOK = {"area", "area_name", "area_title", "area_titl",
             "area_code", "cbsa", "msa", "pmsa", "state", "state_name"}
_OCC_TOK  = {"occ_code", "occ_title", "occ_titl"}


def normalise_columns(df):
    rename = {}
    for c in df.columns:
        canon = _SYNONYM.get(str(c).upper().strip())
        if canon and canon not in rename.values():
            rename[c] = canon
    return df.rename(columns=rename)


# ── Header detection + reader ─────────────────────────────────────────────────
def _read_raw(zf, name):
    """Read an inner file with no header applied, everything as str."""
    data = zf.read(name)
    ext = Path(name).suffix.lower()
    if ext == ".xlsx":
        return pd.read_excel(io.BytesIO(data), dtype=str, header=None,
                             engine="openpyxl")
    if ext == ".xls":
        return pd.read_excel(io.BytesIO(data), dtype=str, header=None,
                             engine="xlrd")
    if ext in (".csv", ".txt"):
        for sep in ("\t", ","):
            try:
                df = pd.read_csv(io.StringIO(data.decode("latin-1")), sep=sep,
                                 header=None, dtype=str, low_memory=False)
                if df.shape[1] > 3:
                    return df
            except Exception:
                pass
    return None


def _find_header_row(raw, scan=80):
    """
    Index of the first row that names an occ column. occ_code/occ_title only
    ever appear in the real header (never in the metadata preamble or data),
    so they are a sufficient anchor. We do NOT also require an area column:
    national files (national_M????_dl) carry occupations with no area column.
    """
    for i in range(min(scan, len(raw))):
        toks = {str(v).strip().lower() for v in raw.iloc[i].tolist()}
        if toks & _OCC_TOK:
            return i
    return None


def read_table(zf, name):
    """Return a DataFrame with the real header applied, wherever it sits."""
    raw = _read_raw(zf, name)
    if raw is None or raw.empty:
        return None
    hdr = _find_header_row(raw)
    if hdr is None:
        return None
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(v).strip() for v in raw.iloc[hdr].tolist()]
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].str.strip()
    return df.reset_index(drop=True)


# ── Geographic filter functions ───────────────────────────────────────────────
def filter_boulder(df):
    """Keep only Boulder MSA rows (name match then area-code fallback)."""
    if "area_name" in df.columns:
        m = df["area_name"].astype(str).str.contains(BOULDER_NAME_RE, na=False)
        if m.any():
            return df[m]
    if "area_code" in df.columns:
        m = df["area_code"].astype(str).str.strip().isin(BOULDER_AREA_CODES)
        if m.any():
            return df[m]
    return df.iloc[0:0]


def filter_colorado(df):
    """Keep only Colorado statewide rows from a state-level file."""
    # 1. area_name exact match
    if "area_name" in df.columns:
        m = df["area_name"].astype(str).str.strip().str.match(CO_NAME_RE)
        if m.any():
            return df[m]
    # 2. prim_state abbreviation (state files often carry this column)
    if "prim_state" in df.columns:
        m = df["prim_state"].astype(str).str.strip().str.upper().isin(CO_PRIM_STATE)
        if m.any():
            return df[m]
    # 3. area_code FIPS (08)
    if "area_code" in df.columns:
        m = df["area_code"].astype(str).str.strip().isin(CO_FIPS)
        if m.any():
            return df[m]
    return df.iloc[0:0]


def filter_national(df):
    """
    Keep the US-national row(s). National files contain only the US estimate,
    but guard against a file that also carries lower-level rows: match a clean
    U.S. area label or the national area code; otherwise fall back to the whole
    file (it IS national).
    """
    if "area_name" in df.columns:
        m = df["area_name"].astype(str).str.strip().str.match(US_NAME_RE)
        if m.any():
            return df[m]
    if "area_code" in df.columns:
        m = df["area_code"].astype(str).str.strip().isin(US_AREA_CODES)
        if m.any():
            return df[m]
    return df


# Map scope key -> filter function
FILTER_FN = {
    "boulder":  filter_boulder,
    "colorado": filter_colorado,
    "national": filter_national,
}


# ── Per-zip processor ─────────────────────────────────────────────────────────
def data_files(zf):
    """Inner data files, skipping docs, lock files, and non-occupation tables."""
    return [
        n for n in zf.namelist()
        if DATA_EXT.search(Path(n).name)
        and not SKIP_FILE_RE.search(Path(n).name)
    ]


def process_zip(zip_path, filter_fn, label=""):
    """
    Extract rows matching filter_fn from one yearly zip.
    Returns (df, provenance_dict) or (None, None) on failure.
    """
    year = year_from_filename(zip_path)
    if year is None:
        logging.warning(f"  {zip_path.name}: cannot infer year -- skipping.")
        return None, None
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        logging.warning(f"  {zip_path.name}: bad zip -- skipping.")
        return None, None

    parts, src_files = [], []
    for name in data_files(zf):
        try:
            df = read_table(zf, name)
        except Exception as e:
            logging.warning(f"  {year}: could not read {Path(name).name}: {e}")
            continue
        if df is None or df.empty:
            continue
        gdf = filter_fn(normalise_columns(df))
        if not gdf.empty:
            parts.append(gdf)
            src_files.append(Path(name).name)

    if not parts:
        logging.warning(f"  {year} [{label}]: not found in {zip_path.name}.")
        return None, None

    out = pd.concat(parts, ignore_index=True, sort=False)
    out = out.drop_duplicates()
    out = out.drop(columns=[c for c in out.columns
                            if str(c).strip().lower() == "year"], errors="ignore")
    out.insert(0, "year", year)

    area = out["area_name"].dropna().iloc[0] if "area_name" in out.columns else label
    logging.info(f"  {year} [{label}]: {len(out):,} rows  "
                 f"(area: '{area}', from {', '.join(src_files)})")

    prov = {
        "year":       year,
        "zip_file":   zip_path.name,
        "inner_file": "; ".join(src_files),
        "area_name":  area,
        "n_rows":     len(out),
        "sha256":     hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    }
    return out, prov


# ── Output helpers ────────────────────────────────────────────────────────────
def order_columns(combined):
    return combined[[c for c in CANONICAL_ORDER if c in combined.columns]]


def write_data_dictionary(combined, prov_df, scope_cfg):
    yrs = sorted(combined["year"].unique())
    label = scope_cfg["label"]
    path  = scope_cfg["dict_md"]
    lines = [
        f"# {label} — OEWS extract: data dictionary & caveats",
        "",
        f"Generated by `oews_boulder.py` from BLS OEWS files in "
        f"`{scope_cfg['zip_dir'].name}/`. "
        f"Coverage: **{yrs[0]}-{yrs[-1]}** "
        f"({len(yrs)} years, {len(combined):,} occupation-rows).",
        "",
        "## Area definition",
        "",
        "| Years | area_name | area_code |",
        "|---|---|---|",
    ]
    for name, sub in combined.groupby("area_name"):
        ys = sorted(sub["year"].unique())
        codes = ", ".join(sorted(sub["area_code"].dropna().astype(str).unique()))
        lines.append(f"| {ys[0]}-{ys[-1]} | {name} | {codes} |")
    lines += [
        "",
        "## Occupation coding",
        "",
        "- **1997-1998** use the legacy 5-digit OES codes.",
        "- **1999-present** use SOC codes.",
        "- All occupations retained (totals, major/minor/broad/detailed).",
        "",
        "## Wage columns",
        "",
        "- Values kept as published strings. Suppression: `*` = not released, "
        "`#` = ≥ $100/hr.",
        "- Percentiles named `h_wpct10` in 1998-2002; normalised to `h_pct10`.",
        "",
        "## Provenance",
        "",
        f"Per-year source files and zip SHA-256 hashes in "
        f"`{scope_cfg['prov_csv'].name}`.",
    ]
    path.write_text("\n".join(lines))


# ── Scope runner ──────────────────────────────────────────────────────────────
def run_scope(scope_key, scope_cfg):
    """Process all zips for one geographic scope. Returns summary dict."""
    label   = scope_cfg["label"]
    zip_dir = scope_cfg["zip_dir"]
    glob    = scope_cfg["zip_glob"]
    filter_fn = FILTER_FN[scope_key]

    if not zip_dir.exists():
        print(f"\n  [{label}] SKIP — folder not found: {zip_dir}")
        print(f"            Create it and place your {glob} files inside.")
        return None

    zip_files = sorted(zip_dir.glob(glob), key=lambda p: year_from_filename(p) or 0)
    if not zip_files:
        print(f"\n  [{label}] SKIP — no {glob} files in {zip_dir}")
        return None

    print(f"\n{'─'*56}")
    print(f"  {label}  ({len(zip_files)} zips)")

    frames, provs, failed = [], [], []
    for zp in tqdm(zip_files, desc=f"  {scope_key}"):
        df, prov = process_zip(zp, filter_fn, label)
        if df is not None and not df.empty:
            frames.append(df)
            provs.append(prov)
        else:
            failed.append(zp.name)

    if not frames:
        print(f"  [{label}] No data extracted.")
        return None

    combined = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()
    # Give every row a consistent area_name. National files pre-2019 carry no
    # area column, so force the scope's geo_name; otherwise only backfill when
    # the column is entirely absent/blank.
    geo_name = scope_cfg.get("geo_name")
    if geo_name:
        combined["area_name"] = geo_name
    elif "area_name" not in combined.columns or combined["area_name"].isna().all():
        combined["area_name"] = label
    # Some years ship two near-identical releases (e.g. 2003 state oesm03st +
    # oesn03st). One row per (year, occ_code) per scope is the panel we want.
    if "occ_code" in combined.columns:
        combined = combined.drop_duplicates(subset=["year", "occ_code"], keep="first")
    sort_keys = [c for c in ("year", "occ_code") if c in combined.columns]
    combined = order_columns(
        combined.sort_values(sort_keys, kind="stable").reset_index(drop=True)
    )
    combined.to_csv(scope_cfg["output_csv"], index=False)

    prov_df = pd.DataFrame(provs)
    prov_df.to_csv(scope_cfg["prov_csv"], index=False)
    write_data_dictionary(combined, prov_df, scope_cfg)

    yrs = sorted(combined["year"].unique())
    return {
        "label":   label,
        "years":   yrs,
        "rows":    len(combined),
        "failed":  failed,
        "output":  scope_cfg["output_csv"].name,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )

    print("\nBLS OEWS Extractor — Boulder / Colorado / National")

    results = {}
    for key, cfg in SCOPES.items():
        results[key] = run_scope(key, cfg)

    print(f"\n{'='*56}")
    print("DONE\n")
    for key, r in results.items():
        if r is None:
            print(f"  {SCOPES[key]['label']:<24}  SKIPPED (no zip folder or no files)")
        else:
            yrs = r["years"]
            print(f"  {r['label']:<24}  {len(yrs)} years "
                  f"({yrs[0]}-{yrs[-1]})  "
                  f"{r['rows']:,} rows  ->  {r['output']}")
            if r["failed"]:
                print(f"    no match: {r['failed']}")


if __name__ == "__main__":
    main()
