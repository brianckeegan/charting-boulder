"""
Boulder MSA — OEWS Metropolitan Area Data Extractor (local files)
=================================================================
Reads BLS OEWS metropolitan-area zip files from `oews_boulder_raw/`
and extracts every Boulder MSA row into a clean long-format panel CSV
spanning the full published history (1997-2025).

The only filter is geographic — the Boulder MSA. EVERY occupation BLS
publishes for Boulder is kept (all-occupations totals, major groups, and
detailed occupations alike); no occupation subsetting happens here. Slicing
to specific occupations is left to downstream analysis.

Why this is non-trivial — the BLS metro files change shape across vintages:

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
# Pin paths to wherever THIS script lives, so it works no matter which
# directory you launch it from.
HERE        = Path(__file__).parent
ZIP_DIR     = HERE / "oews_boulder_raw"
OUTPUT_CSV  = HERE / "oews_boulder_combined.csv"
PROV_CSV    = HERE / "oews_boulder_provenance.csv"
DICT_MD     = HERE / "oews_boulder_data_dictionary.md"
LOG_LEVEL   = logging.INFO

# Match BLS metro zips by either modern (oesm24ma) or old (oes97ma) naming.
ZIP_GLOB = "oes*ma.zip"

# Boulder has been published under two definitions.  Match on NAME first
# (robust across every vintage); the area-code set is a secondary check.
#   1125  = Boulder-Longmont, CO PMSA   (1997-2004)
#   14500 = Boulder, CO  CBSA           (2005-2025)
# NB: 0880 is **Billings, MT** — it was wrongly treated as Boulder in an
# earlier version of this script; do not add it back.
BOULDER_NAME_RE    = re.compile(r"boulder", re.IGNORECASE)
BOULDER_AREA_CODES = {"1125", "14500"}

# Inner files that are NOT metro occupation tables — skip them.
#   ~$...            Excel lock/temp files (broke the 2022 extract)
#   aMSA / BOS       'all-MSA' rollups and Balance-of-State (nonmetro) tables
#   *_descriptions   field/file layout documentation
SKIP_FILE_RE = re.compile(r"(^~\$)|(\baMSA)|(\bBOS)|(field_desc)|(file_desc)"
                          r"|(readme)|(layout)|(glossary)", re.IGNORECASE)
DATA_EXT     = re.compile(r"\.(xlsx?|csv|txt)$", re.IGNORECASE)


# ── Year inference from filename ──────────────────────────────────────────────
def year_from_filename(path: Path):
    """oesm24ma.zip -> 2024 | oesm01ma.zip -> 2001 | oesm97ma.zip -> 1997."""
    m = re.search(r"oesm?(\d{2})ma", path.stem, re.IGNORECASE)
    if not m:
        return None
    yy = int(m.group(1))
    return 1900 + yy if yy >= 97 else 2000 + yy


# ── Column normalisation ──────────────────────────────────────────────────────
# canonical -> source header synonyms (compared case-insensitively, stripped).
COL_MAP = {
    "area_code":    ["area", "area_code", "msa_code", "pmsa_code", "cbsa_code"],
    "area_name":    ["area_name", "area_title", "area_titl", "msa", "pmsa", "cbsa"],
    "prim_state":   ["prim_state", "state", "st"],
    "occ_code":     ["occ_code", "soc", "oes_code", "occ"],
    "occ_title":    ["occ_title", "occ_titl", "occupation", "occupation_title", "oes_title"],
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
# Reverse lookup: normalised source token -> canonical name.
_SYNONYM = {syn.upper().strip(): canon
            for canon, syns in COL_MAP.items() for syn in syns}

# Final column order for the combined panel.
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

# Tokens that mark a row as the column header (need an area col AND an occ col).
# occ_code/occ_title are the strong anchor — they only ever appear in the real
# header row, never in the metadata preamble — so broadening the area side is
# safe and keeps detection working wherever the header sits (row 0, 8-12, 32-43…).
_AREA_TOK = {"area", "area_name", "area_title", "area_titl",
             "area_code", "cbsa", "msa", "pmsa"}
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
    """Read an inner spreadsheet/text file with no header, everything as str."""
    data = zf.read(name)
    ext = Path(name).suffix.lower()
    if ext == ".xlsx":
        return pd.read_excel(io.BytesIO(data), dtype=str, header=None, engine="openpyxl")
    if ext == ".xls":
        return pd.read_excel(io.BytesIO(data), dtype=str, header=None, engine="xlrd")
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
    """Index of the first row that names both an area column and an occ column."""
    for i in range(min(scan, len(raw))):
        toks = {str(v).strip().lower() for v in raw.iloc[i].tolist()}
        if (toks & _AREA_TOK) and (toks & _OCC_TOK):
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
    # Strip stray whitespace from every text cell (1999-2000 space-pad codes
    # and counts, e.g. '       13050'). Guard on is_string_dtype, not
    # `== object`: pandas reads dtype=str as StringDtype, so an object check
    # silently skips the strip.
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].str.strip()
    return df.reset_index(drop=True)


# ── Boulder filter ────────────────────────────────────────────────────────────
def filter_boulder(df):
    if "area_name" in df.columns:
        m = df["area_name"].astype(str).str.contains(BOULDER_NAME_RE, na=False)
        if m.any():
            return df[m]
    if "area_code" in df.columns:
        m = df["area_code"].astype(str).str.strip().isin(BOULDER_AREA_CODES)
        if m.any():
            return df[m]
    return df.iloc[0:0]


# ── Per-zip processor ─────────────────────────────────────────────────────────
def data_files(zf):
    """Inner metro data files, skipping docs / lock files / non-metro tables."""
    out = []
    for n in zf.namelist():
        base = Path(n).name
        if not DATA_EXT.search(base) or SKIP_FILE_RE.search(base):
            continue
        out.append(n)
    return out


def process_zip(zip_path):
    """Extract all Boulder rows from one yearly zip. Returns (df, provenance)."""
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
        bdf = filter_boulder(normalise_columns(df))
        if not bdf.empty:
            parts.append(bdf)
            src_files.append(Path(name).name)

    if not parts:
        logging.warning(f"  {year}: Boulder not found in {zip_path.name}.")
        return None, None

    bdf = pd.concat(parts, ignore_index=True, sort=False)
    bdf = bdf.drop_duplicates()
    # Old files (1997-2000) carry a literal `year` column — drop it so our
    # filename-derived year is authoritative and doesn't collide on insert.
    bdf = bdf.drop(columns=[c for c in bdf.columns
                            if str(c).strip().lower() == "year"], errors="ignore")
    bdf.insert(0, "year", year)
    area = bdf["area_name"].dropna().iloc[0] if "area_name" in bdf.columns else "?"
    logging.info(f"  {year}: {len(bdf):,} rows  (area: '{area}', "
                 f"from {', '.join(src_files)})")

    prov = {
        "year": year,
        "zip_file": zip_path.name,
        "inner_file": "; ".join(src_files),
        "area_name": area,
        "n_rows": len(bdf),
        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    }
    return bdf, prov


# ── Output assembly ───────────────────────────────────────────────────────────
def order_columns(combined):
    # Keep only the canonical schema, in order. Unmapped per-vintage extras
    # (mean_aster, rep_units, naics, release, ...) are dropped so the panel is
    # a clean, consistent rectangle across all years.
    return combined[[c for c in CANONICAL_ORDER if c in combined.columns]]


def write_data_dictionary(combined, prov_df):
    yrs = sorted(combined["year"].unique())
    lines = [
        "# Boulder MSA — OEWS extract: data dictionary & caveats",
        "",
        f"Generated by `oews_boulder.py` from BLS OEWS metro files in "
        f"`oews_boulder_raw/`. Coverage: **{yrs[0]}-{yrs[-1]}** "
        f"({len(yrs)} years, {len(combined):,} occupation-rows).",
        "",
        "## Area definition (changes mid-series)",
        "",
        "| Years | area_name | area_code |",
        "|---|---|---|",
    ]
    for name, sub in combined.groupby("area_name"):
        ys = sorted(sub["year"].unique())
        codes = ", ".join(sorted(sub["area_code"].dropna().unique()))
        lines.append(f"| {ys[0]}-{ys[-1]} | {name} | {codes} |")
    lines += [
        "",
        "## Occupation coding (changes mid-series)",
        "",
        "- **1997-1998** use the legacy 5-digit OES occupation codes "
        "(e.g. `13002` = Financial Managers).",
        "- **1999-present** use SOC codes (e.g. `11-1011`). Any SOC-based "
        "occupation lookup therefore only resolves from 1999 onward; for "
        "1997-1998 you must use the legacy OES codes instead.",
        "- All occupations are retained (totals, major/minor/broad groups, and "
        "detailed occupations); `occ_code` is preserved verbatim and the two "
        "code systems are **not** crosswalked here.",
        "",
        "## Wage/percentile columns",
        "",
        "- `1997` publishes only `h_mean`, `h_median`, `a_mean` — no percentiles.",
        "- Percentile fields were named `h_wpct10` etc. in 1998-2002 and "
        "`h_pct10` from 2003; both are normalised to `h_pct10`/`a_pct10`/…",
        "- Values are kept as published **strings**. BLS suppression markers "
        "survive verbatim: `*` = estimate not released, `#` = wage at or above "
        "$100/hr (≈ $208k/yr), blank = not available.",
        "",
        "## Columns",
        "",
        "| column | meaning |",
        "|---|---|",
        "| year | survey/reference year |",
        "| area_code | BLS MSA/PMSA (pre-2005) or CBSA (2005+) code |",
        "| area_name | published area title |",
        "| prim_state | primary state (CO) |",
        "| occ_code | OES (1997-98) or SOC (1999+) occupation code |",
        "| occ_title | occupation title |",
        "| occ_group | aggregation level (total/major/minor/broad/detailed) |",
        "| tot_emp | total employment |",
        "| emp_prse | employment relative standard error (%) |",
        "| h_mean / a_mean | mean hourly / annual wage |",
        "| mean_prse | mean-wage relative standard error (%) |",
        "| h_median / a_median | median hourly / annual wage |",
        "| h_pct10..h_pct90 | hourly wage percentiles |",
        "| a_pct10..a_pct90 | annual wage percentiles |",
        "| jobs_1000 | jobs per 1,000 (2009+) |",
        "| loc_quotient | location quotient (2013+) |",
        "| annual / hourly | flags: wage published only annually / hourly |",
        "",
        "## Provenance",
        "",
        "Per-year source files and zip SHA-256 hashes are recorded in "
        "`oews_boulder_provenance.csv`.",
    ]
    DICT_MD.write_text("\n".join(lines))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S", force=True)
    if not ZIP_DIR.exists():
        raise FileNotFoundError(f"Zip directory not found: {ZIP_DIR}")
    zip_files = sorted(ZIP_DIR.glob(ZIP_GLOB), key=lambda p: year_from_filename(p) or 0)
    if not zip_files:
        raise FileNotFoundError(f"No {ZIP_GLOB} files found in {ZIP_DIR}")

    print("\nBLS OEWS Metro -- Boulder extraction")
    print(f"Folder: {ZIP_DIR}")
    print(f"Found {len(zip_files)} zip(s): {[p.name for p in zip_files]}\n")

    frames, provs, failed = [], [], []
    for zp in tqdm(zip_files, desc="Processing"):
        df, prov = process_zip(zp)
        if df is not None and not df.empty:
            frames.append(df)
            provs.append(prov)
        else:
            failed.append(zp.name)

    if not frames:
        print("\nNo Boulder data extracted. Re-run with LOG_LEVEL = logging.DEBUG.")
        return

    combined = order_columns(pd.concat(frames, ignore_index=True, sort=False))
    combined = combined.sort_values(["year", "occ_code"], kind="stable").reset_index(drop=True)
    combined.to_csv(OUTPUT_CSV, index=False)

    prov_df = pd.DataFrame(provs)
    prov_df.to_csv(PROV_CSV, index=False)
    write_data_dictionary(combined, prov_df)

    yrs = sorted(combined["year"].unique())
    missing = [y for y in range(yrs[0], yrs[-1] + 1) if y not in yrs]
    print(f"\n{'='*56}\nDONE")
    print(f"  Years with Boulder data: {len(yrs)} ({yrs[0]}-{yrs[-1]})")
    if missing:
        print(f"  Missing years in range: {missing}")
    if failed:
        print(f"  Zips with no Boulder match: {failed}")
    print(f"  Total rows: {len(combined):,}")
    print(f"  Output:     {OUTPUT_CSV.name}")
    print(f"  Provenance: {PROV_CSV.name}")
    print(f"  Dictionary: {DICT_MD.name}")

    print("\n  Rows per year:")
    for y, c in combined.groupby("year").size().items():
        print(f"    {y}: {c:,}")

    print("\n  Area-name variants matched:")
    for n, c in combined.groupby("area_name").size().items():
        print(f"    '{n}': {c:,}")

    # The extract keeps EVERY occupation published for Boulder — no occupation
    # filtering. Report the breadth so that's visible.
    if "occ_code" in combined.columns:
        print(f"\n  Occupations kept (all SOC/OES codes): "
              f"{combined['occ_code'].nunique():,} distinct codes")
        if "occ_group" in combined.columns:
            print("  Rows by occupation level (occ_group):")
            for g, c in combined["occ_group"].fillna("(blank)").value_counts().items():
                print(f"    {g}: {c:,}")


if __name__ == "__main__":
    main()
