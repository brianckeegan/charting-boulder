#!/usr/bin/env python3
"""
BVSD Open Enrollment Pattern Matrices -> tidy edgelist.

Source page:
  https://www.bvsd.org/departments/operational-services/planning-and-engineering
  ("Open Enrollment Matrices" section; Elementary / Middle / High files only)

Layout of each PDF (one table per file):
  * rows    = school attended (includes schools with no attendance area,
              e.g. BCSIS, Peak to Peak, Boulder Universal)
  * columns = neighborhood attendance area where the student lives
              (includes "Optional" areas that have no school of their own)
  * cell    = number of students
  * right block (8 cols, per school): Attending Neighborhood School,
      Open Enrolled from within District, Open Enrolled from outside District,
      Placements into School, Unmatched Addresses, Within BVSD Boundaries,
      Student Enrollment Total, % of Enrollment from Neighborhood Area
  * bottom block (4 rows, per area): Students Placed-Out, Total living in
      area, Open Enrollment out of area, % enrolled in neighborhood school
  * a district-total line sits in the first summary row, right block.

Inputs (data/raw/open-enrollment/):
  <level>_<school_year>.pdf   one PDF per level x year (fetched once; kept as-is)
  manifest.json               url, bytes, sha256 per PDF

Outputs (data/processed/open-enrollment/):
  edgelist.csv          school_year, level, source, target, students, ...
  school_summary.csv    per school x year, the 8 right-block columns
  area_summary.csv      per attendance area x year, the 4 bottom-block rows
  district_summary.csv  per level x year district totals
  crosswalk.csv         raw name -> canonical name (auto-generated; edit by hand)
  provenance.csv        per file: url, sha256, matrix date stamp, grade line
  audit_report.md       reconciliation checks; errors reported, never fatal

Usage (from 2026-09-bvsd/):
  python scripts/extract_open_enrollment.py            # parse + audit (fetches only if a PDF is missing)
  python scripts/extract_open_enrollment.py --refetch  # force re-download of every PDF
Needs pandas, pdfplumber, tabulate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pdfplumber

pd.options.display.max_columns = 100

ROOT = Path(__file__).resolve().parents[1]          # 2026-09-bvsd/
RAW = ROOT / "data" / "raw" / "open-enrollment"       # the PDFs + manifest.json
OUT = ROOT / "data" / "processed" / "open-enrollment"  # tidy CSVs + audit report
PAGE_URL = ("https://www.bvsd.org/departments/operational-services/"
            "planning-and-engineering")
LEVELS = {"elem": "elementary", "middle": "middle", "high": "high"}
PSEUDO_OUTSIDE = "OUTSIDE_DISTRICT"
PSEUDO_UNMATCHED = "UNMATCHED_ADDRESS"
PSEUDO_PLACEMENT = "PLACEMENT"

SUMMARY_COLS = [  # fixed positional order of the right block
    "attending_neighborhood", "oe_from_within_district",
    "oe_from_outside_district", "placements_into_school",
    "unmatched_addresses", "within_bvsd_total", "enrollment_total",
    "pct_from_neighborhood",
]
AREA_ROWS = [  # fixed positional order of the bottom block
    "placed_out", "living_in_area_total", "oe_out_of_area",
    "pct_enrolled_in_neighborhood",
]

# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------

def discover_links() -> list[dict]:
    html = subprocess.run(["curl", "-sL", PAGE_URL], capture_output=True,
                          text=True, check=True).stdout
    links = re.findall(
        r'href="(https://resources\.finalsite\.net/[^"]*Matrix[^"]*\.pdf)"', html)
    rows = []
    for u in dict.fromkeys(links):  # de-dup, keep order
        fn = u.rsplit("/", 1)[1]
        m = re.search(r"(20\d\d)-(\d\d)", fn)
        if not m:
            continue
        y0 = int(m.group(1))
        key = next((k for k in LEVELS if fn.lower().startswith(k)), None)
        if key is None:  # K / 6th / 9th entry-grade files are skipped
            continue
        rows.append(dict(level=LEVELS[key], school_year=f"{y0}-{y0+1}",
                         url=u, source_filename=fn))
    return rows


def fetch(refetch: bool = False) -> list[dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_p = RAW / "manifest.json"
    if manifest_p.exists() and not refetch:
        manifest = json.loads(manifest_p.read_text())
        if all((RAW / r["file"]).exists() for r in manifest):
            return manifest
    manifest = []
    for r in discover_links():
        out = RAW / f"{r['level']}_{r['school_year']}.pdf"
        if refetch or not out.exists():
            subprocess.run(["curl", "-sL", "-o", str(out), r["url"]], check=True)
        r = dict(r, file=out.name, bytes=out.stat().st_size,
                 sha256=hashlib.sha256(out.read_bytes()).hexdigest())
        manifest.append(r)
    manifest.sort(key=lambda r: (r["school_year"], r["level"]))
    manifest_p.write_text(json.dumps(manifest, indent=1))
    return manifest

# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def _decode_rotated(page, bbox) -> str:
    """Rebuild the text of a rotated header cell from character positions.
    pdfplumber reads rotated glyphs in stream order, which scrambles them.
    Sorting by (column-of-glyphs, vertical position) restores reading order."""
    x0, top, x1, bottom = bbox
    chars = [c for c in page.chars
             if c["x0"] >= x0 - 1 and c["x1"] <= x1 + 1
             and c["top"] >= top - 1 and c["bottom"] <= bottom + 1]
    if not chars:
        return ""
    b = chars[0]["matrix"][1]
    if b > 0:   # rotated 90 deg counter-clockwise: reads bottom -> top
        chars.sort(key=lambda c: (round(c["x0"] / 3), -c["top"]))
    else:       # rotated clockwise: reads top -> bottom
        chars.sort(key=lambda c: (round(-c["x0"] / 3), c["top"]))
    return re.sub(r"\s+", " ", "".join(c["text"] for c in chars)).strip()


def _num(s) -> int | None:
    """'1,234' -> 1234; '' / None -> None; strips stray annotation text."""
    if s is None:
        return None
    s = str(s).split("\n")[0].strip().replace(",", "")
    m = re.match(r"^-?\d+$", s)
    return int(m.group()) if m else None


def _pct(s) -> float | None:
    if s is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(s))
    return float(m.group(1)) / 100 if m else None


def _clean(s) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_pdf(path: Path, errors: list) -> dict:
    """Return dict with matrix (list of (school, area, n)), school summary,
    area summary, district totals, and header metadata."""
    rec = dict(file=path.name)
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        if len(pdf.pages) > 1:
            errors.append((path.name, "structure",
                           f"{len(pdf.pages)} pages; only page 1 parsed"))
        text = page.extract_text() or ""
        lines = text.split("\n")
        m = re.search(r"MATRIX,\s*(\d{4}-\d{4})\s*(\d{1,2}/\d{1,2}/\d{2,4})?",
                      lines[0] if lines else "")
        rec["title_year"] = m.group(1) if m else None
        rec["matrix_date"] = m.group(2) if m else None
        rec["grade_line"] = _clean(lines[1]) if len(lines) > 1 else None
        rec["footnotes"] = " | ".join(l for l in lines if l.startswith("*"))

        tables = page.find_tables()
        if not tables:
            errors.append((path.name, "structure", "no table found"))
            return rec
        tf = tables[0]
        grid = tf.extract()
        headers = [_decode_rotated(page, c) if c else "" for c in tf.rows[0].cells]

    # --- locate column blocks -------------------------------------------
    # col 0: row-group marker (blank); col 1: school name; then area columns;
    # then a blank-header column repeating the school name; then 8 summaries.
    ncol = len(grid[0])
    # first blank header after col 1 with a non-empty header before it
    blank_after = [i for i in range(2, ncol) if headers[i] == "" and headers[i-1]]
    if not blank_after:
        errors.append((path.name, "structure", "cannot find summary block"))
        return rec
    name_repeat_col = blank_after[0]
    area_cols = list(range(2, name_repeat_col))
    summary_cols = list(range(name_repeat_col + 1, ncol))
    if len(summary_cols) != 8:
        errors.append((path.name, "structure",
                       f"expected 8 summary columns, found {len(summary_cols)}: "
                       f"{[headers[i] for i in summary_cols]}"))
    summary_hdr_text = " ".join(headers[i] for i in summary_cols).lower()
    for kw in ["neighborhood", "within", "outside", "placement", "unmatched",
               "total", "%"]:
        if kw not in summary_hdr_text:
            errors.append((path.name, "header",
                           f"summary header keyword '{kw}' not found"))
    areas = [_clean(headers[i]) for i in area_cols]
    if any(a == "" for a in areas):
        errors.append((path.name, "header", f"blank area header in {areas}"))

    # --- locate row blocks ----------------------------------------------
    body = grid[1:]
    first_summary_row = next(
        (i for i, r in enumerate(body)
         if r[0] and re.search(r"placed", r[0], re.I)), None)
    if first_summary_row is None:
        errors.append((path.name, "structure", "cannot find bottom block"))
        return rec
    # spacer rows (blank name) carry rotated repeated area labels; drop them
    school_rows = [r for r in body[:first_summary_row] if _clean(r[1])]
    area_rows = body[first_summary_row:first_summary_row + 4]
    if len(area_rows) != 4:
        errors.append((path.name, "structure",
                       f"expected 4 bottom rows, found {len(area_rows)}"))

    # --- matrix + school summaries --------------------------------------
    matrix, school_summary = [], []
    for r in school_rows:
        school = _clean(r[1])
        if not school:
            continue
        for j, area in zip(area_cols, areas):
            n = _num(r[j])
            if n:
                matrix.append((school, area, n))
        row_sum = sum(_num(r[j]) or 0 for j in area_cols)
        s = dict(school_raw=school, matrix_row_sum=row_sum)
        for k, j in zip(SUMMARY_COLS, summary_cols):
            s[k] = _pct(r[j]) if k.startswith("pct") else _num(r[j])
        rep = _clean(r[name_repeat_col])
        if rep and rep.replace(" ", "") != school.replace(" ", ""):
            errors.append((path.name, "header",
                           f"repeated school name mismatch: {school!r} vs {rep!r}"))
        school_summary.append(s)

    # --- area summaries + district totals -------------------------------
    area_summary = {a: dict(area_raw=a) for a in areas}
    for k, r in zip(AREA_ROWS, area_rows):
        for j, a in zip(area_cols, areas):
            area_summary[a][k] = _pct(r[j]) if k.startswith("pct") else _num(r[j])
    for j, a in zip(area_cols, areas):
        area_summary[a]["matrix_col_sum"] = sum(
            _num(r[j]) or 0 for r in school_rows)
    district = {}
    for k, j in zip(SUMMARY_COLS, summary_cols):
        v = area_rows[0][j] if j < len(area_rows[0]) else None
        district[k] = _pct(v) if k.startswith("pct") else _num(v)
    for k, j in zip(SUMMARY_COLS[:4], summary_cols[:4]):
        district[k + "_share"] = _pct(area_rows[1][j]) if len(area_rows) > 1 else None

    rec.update(areas=areas, schools=[s["school_raw"] for s in school_summary],
               matrix=matrix, school_summary=school_summary,
               area_summary=list(area_summary.values()), district=district)
    return rec


# --------------------------------------------------------------------------
# crosswalk
# --------------------------------------------------------------------------

def canonical(name: str) -> str:
    n = name.replace("*", "")
    n = re.sub(r"\s+", " ", n).strip()
    n = re.sub(r"\s*/\s*", "/", n)
    n = re.sub(r"\b(Elem\.|Elem|Elementary)$", "", n).strip()
    n = re.sub(r"\bInt\.$", "International", n)
    n = re.sub(r"^Comm\. ", "Community ", n)
    n = re.sub(r"^Uni-Hill", "University Hill", n)
    n = n.replace("Peak-to-Peak", "Peak to Peak")
    n = re.sub(r"^Contract(ed)? Ed( Prog)?$", "Contracted Ed Program", n)
    n = n.replace("Middle School", "Middle").replace("Middle Sch.", "Middle")
    n = re.sub(r"\bK-?8\b", "K-8", n)
    n = re.sub(r"\bPK-8\b", "K-8", n)
    return n.strip()

# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------

def audit(recs: list[dict], errors: list) -> None:
    for rec in recs:
        f = rec["file"]
        if "matrix" not in rec:
            continue
        for s in rec["school_summary"]:
            a, w = s["attending_neighborhood"], s["oe_from_within_district"]
            exp = (a or 0) + (w or 0)
            if s["matrix_row_sum"] != exp:
                errors.append((f, "row_sum", f"{s['school_raw']}: matrix row sum "
                               f"{s['matrix_row_sum']} != attending+oe_within {exp}"))
            parts = [s[k] or 0 for k in SUMMARY_COLS[:5]]
            if s["enrollment_total"] is not None and sum(parts) != s["enrollment_total"]:
                errors.append((f, "school_total", f"{s['school_raw']}: sum of 5 "
                               f"components {sum(parts)} != enrollment_total "
                               f"{s['enrollment_total']}"))
            inside = sum(parts) - (s["oe_from_outside_district"] or 0)
            if s["within_bvsd_total"] is not None and inside != s["within_bvsd_total"]:
                errors.append((f, "within_total", f"{s['school_raw']}: components "
                               f"minus outside {inside} != within_bvsd_total "
                               f"{s['within_bvsd_total']}"))
        for a in rec["area_summary"]:
            exp = a["matrix_col_sum"] + (a["placed_out"] or 0)
            if a["living_in_area_total"] is not None and exp != a["living_in_area_total"]:
                errors.append((f, "col_sum", f"{a['area_raw']}: matrix column sum "
                               f"{a['matrix_col_sum']} + placed_out {a['placed_out']} "
                               f"!= living_in_area_total {a['living_in_area_total']}"))
        d = rec["district"]
        for k in SUMMARY_COLS[:7]:
            tot = sum(s[k] or 0 for s in rec["school_summary"])
            if d.get(k) is not None and tot != d[k]:
                errors.append((f, "district_total",
                               f"{k}: sum of schools {tot} != district {d[k]}"))
        # diagonal + optional areas naming the school == attending_neighborhood
        # (the source footnote: "* Note optional enrollment areas excluded")
        cells = defaultdict(int)
        for s, a, n in rec["matrix"]:
            cells[(canonical(s), canonical(a))] += n
        area_c = [canonical(a) for a in rec["areas"]]
        for s in rec["school_summary"]:
            c = canonical(s["school_raw"])
            if c not in area_c:
                continue
            own = [a for a in area_c if a == c or
                   ("Optional" in a and re.search(rf"\b{re.escape(c)}\b", a))]
            got = sum(cells.get((c, a), 0) for a in own)
            if got != (s["attending_neighborhood"] or 0):
                errors.append((f, "diagonal", f"{s['school_raw']}: own-area cells "
                               f"{got} ({'+'.join(own)}) != attending_neighborhood "
                               f"{s['attending_neighborhood']}"))
        if rec.get("title_year") and rec["title_year"] != \
                f.split("_")[1].replace(".pdf", ""):
            errors.append((f, "provenance", f"title year {rec['title_year']} "
                           f"!= filename year"))

# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(refetch: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = fetch(refetch)
    errors: list[tuple[str, str, str]] = []
    recs = []
    for m in manifest:
        rec = parse_pdf(RAW / m["file"], errors)
        rec.update(level=m["level"], school_year=m["school_year"], url=m["url"],
                   sha256=m["sha256"])
        recs.append(rec)
    audit(recs, errors)

    # crosswalk
    names = set()
    for r in recs:
        for n in r.get("schools", []):
            names.add((r["level"], n, "school"))
        for n in r.get("areas", []):
            names.add((r["level"], n, "area"))
    seen = defaultdict(set)
    for lvl, n, role in names:
        seen[(lvl, n)].add(role)
    xw = pd.DataFrame([dict(level=l, name_raw=n, canonical=canonical(n),
                            appears_as="+".join(sorted(r)))
                       for (l, n), r in seen.items()])
    xw = xw.sort_values(["level", "canonical", "name_raw"]).reset_index(drop=True)
    xw.to_csv(OUT / "crosswalk.csv", index=False)
    cmap = {(l, n): c for l, n, c in xw[["level", "name_raw", "canonical"]].itertuples(index=False)}

    # edgelist
    edges = []
    for r in recs:
        if "matrix" not in r:
            continue
        base = dict(school_year=r["school_year"], level=r["level"])
        for s, a, n in r["matrix"]:
            edges.append(dict(base, source_raw=a, target_raw=s,
                              source=cmap[(r["level"], a)],
                              target=cmap[(r["level"], s)], students=n,
                              edge_type="matrix"))
        for s in r["school_summary"]:
            t = cmap[(r["level"], s["school_raw"])]
            for col, pseudo in [("oe_from_outside_district", PSEUDO_OUTSIDE),
                                ("unmatched_addresses", PSEUDO_UNMATCHED),
                                ("placements_into_school", PSEUDO_PLACEMENT)]:
                if s[col]:
                    edges.append(dict(base, source_raw=pseudo, target_raw=s["school_raw"],
                                      source=pseudo, target=t, students=s[col],
                                      edge_type=col))
    edges_df = pd.DataFrame(edges)
    edges_df["self_loop"] = edges_df["source"] == edges_df["target"]
    edges_df = edges_df[["school_year", "level", "source", "target", "students",
                         "self_loop", "edge_type", "source_raw", "target_raw"]]
    edges_df.to_csv(OUT / "edgelist.csv", index=False)

    ss = pd.DataFrame([dict(school_year=r["school_year"], level=r["level"],
                            school=cmap[(r["level"], s["school_raw"])], **s)
                       for r in recs if "matrix" in r for s in r["school_summary"]])
    ss.to_csv(OUT / "school_summary.csv", index=False)
    asum = pd.DataFrame([dict(school_year=r["school_year"], level=r["level"],
                              area=cmap[(r["level"], a["area_raw"])], **a)
                         for r in recs if "matrix" in r for a in r["area_summary"]])
    asum.to_csv(OUT / "area_summary.csv", index=False)
    dist = pd.DataFrame([dict(school_year=r["school_year"], level=r["level"],
                              **r["district"]) for r in recs if "matrix" in r])
    dist.to_csv(OUT / "district_summary.csv", index=False)
    prov = pd.DataFrame([dict(school_year=r["school_year"], level=r["level"],
                              file=r["file"], url=r["url"], sha256=r["sha256"],
                              matrix_date=r.get("matrix_date"),
                              grade_line=r.get("grade_line"),
                              footnotes=r.get("footnotes"),
                              n_schools=len(r.get("schools", [])),
                              n_areas=len(r.get("areas", [])),
                              n_edges=len(r.get("matrix", [])))
                         for r in recs])
    prov.to_csv(OUT / "provenance.csv", index=False)

    # audit report
    lines = ["# Audit report", "",
             f"Files parsed: {sum('matrix' in r for r in recs)} / {len(recs)}",
             f"Edges (matrix): {int((edges_df.edge_type == 'matrix').sum())}",
             f"Edges (pseudo-source): {int((edges_df.edge_type != 'matrix').sum())}",
             f"Total students in edgelist: {int(edges_df.students.sum())}",
             f"Issues found: {len(errors)}", ""]
    if errors:
        lines += ["| file | check | detail |", "|---|---|---|"]
        lines += [f"| {f} | {c} | {d} |" for f, c, d in errors]
    else:
        lines.append("All checks passed.")
    lines += ["", "## Per-file counts", "",
              prov[["school_year", "level", "matrix_date", "n_schools",
                    "n_areas", "n_edges"]].to_markdown(index=False)]
    (OUT / "audit_report.md").write_text("\n".join(lines))
    print("\n".join(lines[:8]))
    by_check = pd.Series([c for _, c, _ in errors]).value_counts() if errors else None
    if by_check is not None:
        print(by_check.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true")
    main(**vars(ap.parse_args()))
