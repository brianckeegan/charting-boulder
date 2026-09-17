"""Proof run for the 2026-10-alternatives retrieval task.

This is NOT the pipeline. It is a small, deliberately narrow probe that
exercises the three hardest years of the proposed archive so that TASK.md
rests on files that were actually fetched and parsed, not on a reading of
the index pages.

Three years, chosen because each breaks a different assumption:

  2001  CDE publishes school-by-grade as PDF only. No spreadsheet exists.
  2013  CDE publishes both PDF and XLS, and the staff report is school
        grain this year (it is district grain in 2015).
  2024  Current era. XLSX from the Finalsite resource manager, and the
        matching teacher-FTE file keys on school code with no district.

For each year it also pulls the NCES Common Core of Data through the Urban
Institute API, harmonizes both sides onto one schema, and compares them.
CCD ends at 2023, so the 2024 CDE year is compared against CCD 2023 and the
report says so rather than hiding the seam.

Run from this directory:

    python3 proof-run.py

Writes:
    data/raw/                 originals, exactly as downloaded
    data/raw/manifest.json    url, bytes, sha256, fetched-at for every file
    data/interim/             the harmonized per-year tables
    audit/proof-run.md        the findings this script establishes
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request

from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
INTERIM = HERE / "data" / "interim"
AUDIT = HERE / "audit"

ARTEMIS = "https://spl.cde.state.co.us/artemis/edserials"
FINALSITE = "https://ed.cde.state.co.us/fs/resource-manager/view"
CCD_API = "https://educationdata.urban.org/api/v1/schools/ccd"

# The proof years. ccd_year differs from cde_year in 2024 because CCD stops
# at 2023; the report carries that gap rather than silently aligning them.
YEARS = [
    {"cde_year": 2001, "ccd_year": 2001},
    {"cde_year": 2013, "ccd_year": 2013},
    {"cde_year": 2024, "ccd_year": 2023},
]

# Every CDE file this proof touches, with the URL resolved by hand from the
# index pages. The real pipeline must discover these instead of hardcoding
# them; see TASK.md step R1.
CDE_FILES = {
    "membership-2001": {
        "url": f"{ARTEMIS}/ed59017internet/2001/ed59017200113internet.pdf",
        "note": "Fall 2001 Pupil Membership by School and Grade Level. PDF only.",
    },
    "membership-2013": {
        "url": f"{ARTEMIS}/ed59017internet/2013/ed590172013033internet.xls",
        "note": "Pupil Membership by School and Grade Level, 2013. XLS.",
    },
    "membership-2024": {
        "url": f"{FINALSITE}/7efacffc-8335-4735-9b12-fee840351810",
        "note": "2024-25 PK-12 Membership Grade Level by School. XLSX.",
        "filename": "membership-2024.xlsx",
    },
    "teacher-fte-2013": {
        # NOTE: ...07 is "Count of teachers by district, ethnicity and gender".
        # The Artemis indexes put each link BEFORE its label, so a scraper that
        # reads the nearest preceding text silently fetches the wrong report.
        # This proof run hit that bug. See audit/proof-run.md finding A3.
        "url": f"{ARTEMIS}/ed288internet/2013/ed288201308internet.pdf",
        "note": "Pupil-teacher ratios by school, Fall 2013. PDF.",
    },
    "teacher-fte-2024": {
        "url": f"{FINALSITE}/9e71cf39-e241-4258-8475-0bdd9724940e",
        "note": "2024-2025 Student Teacher Ratios by School. XLSX.",
        "filename": "teacher-fte-2024.xlsx",
    },
}


# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------

def fetch(url: str, dest: Path, tries: int = 4) -> bytes:
    """Download url to dest, with backoff. Returns the bytes."""
    if dest.exists():
        return dest.read_bytes()
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "charting-boulder/proof-run"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return data
        except Exception as exc:  # noqa: BLE001 - a proof run reports, it does not raise
            if attempt == tries - 1:
                print(f"  FAILED {url}: {exc}", file=sys.stderr)
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def download_cde(manifest: dict) -> None:
    for key, spec in CDE_FILES.items():
        name = spec.get("filename") or f"{key}{Path(spec['url']).suffix}"
        dest = RAW / name
        print(f"  {key}: {name}")
        data = fetch(spec["url"], dest)
        manifest[name] = {
            "url": spec["url"],
            "note": spec["note"],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def fetch_json(url: str, tries: int = 4) -> dict:
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "charting-boulder/proof-run"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def download_ccd(manifest: dict) -> None:
    """CCD directory (one row per school, carries teachers_fte) plus
    enrollment by grade, for Colorado (fips 8) in each proof year."""
    for spec in YEARS:
        year = spec["ccd_year"]

        dest = RAW / f"ccd-directory-{year}.json"
        if not dest.exists():
            print(f"  ccd directory {year}")
            rows, url = [], f"{CCD_API}/directory/{year}/?fips=8"
            while url:
                page = fetch_json(url)
                rows.extend(page["results"])
                url = page.get("next")
            dest.write_text(json.dumps(rows))
        manifest[dest.name] = {
            "url": f"{CCD_API}/directory/{year}/?fips=8",
            "note": f"NCES CCD school directory, Colorado, {year}. Carries teachers_fte.",
            "bytes": dest.stat().st_size,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        dest = RAW / f"ccd-enrollment-{year}.json"
        if not dest.exists():
            print(f"  ccd enrollment {year}")
            rows = []
            # CCD grade codes: -1 pre-K, 0 kindergarten, 1-12 graded,
            # 13 grade 13, 14 ungraded, 15 adult, 99 total.
            for grade in list(range(-1, 15)) + [99]:
                url = f"{CCD_API}/enrollment/{year}/grade-{grade}/?fips=8"
                try:
                    while url:
                        page = fetch_json(url)
                        rows.extend(page["results"])
                        url = page.get("next")
                except Exception as exc:  # noqa: BLE001
                    print(f"    grade {grade}: {exc}", file=sys.stderr)
            dest.write_text(json.dumps(rows))
        manifest[dest.name] = {
            "url": f"{CCD_API}/enrollment/{year}/grade-<g>/?fips=8",
            "note": f"NCES CCD enrollment by grade, Colorado, {year}.",
            "bytes": dest.stat().st_size,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


# --------------------------------------------------------------------------
# read spreadsheets without a hard pandas dependency
# --------------------------------------------------------------------------

def read_sheet(path: Path) -> list[list]:
    """First worksheet as a list of rows. pandas handles both the modern
    .xlsx (openpyxl) and the legacy BIFF .xls (xlrd); CDE publishes both."""
    import pandas as pd  # noqa: PLC0415

    frame = pd.read_excel(path, header=None, dtype=object)
    return [["" if v is None or (isinstance(v, float) and v != v) else v for v in row]
            for row in frame.values.tolist()]


def pdf_text_pages(path: Path) -> list[str]:
    """Pull the text layer out of a PDF using only zlib. Handles both the
    plain (Tj string) encoding and the UTF-16BE hex encoding the scanned
    Artemis volumes use for their invisible OCR layer."""
    import zlib  # noqa: PLC0415

    data = path.read_bytes()
    pages = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        try:
            body = zlib.decompress(data[start:end])
        except Exception:  # noqa: BLE001 - not every stream is text
            continue
        if b"Tj" not in body and b"TJ" not in body:
            continue
        hexes = re.findall(rb"<([0-9A-Fa-f]{4,})>", body)
        if hexes:
            text = "".join(
                bytes.fromhex(h.decode()).decode("utf-16-be", errors="replace") for h in hexes
            )
        else:
            text = " ".join(
                s[1:-1].decode("latin-1")
                for s in re.findall(rb"\((?:[^()\\]|\\.)*\)", body)
            )
        pages.append(re.sub(r"\s+", " ", text).strip())
    return pages


# --------------------------------------------------------------------------
# harmonize
# --------------------------------------------------------------------------

GRADE_ORDER = ["PK", "K"] + [str(g) for g in range(1, 13)]

CCD_GRADE = {-1: "PK", 0: "K", **{g: str(g) for g in range(1, 13)}}


def normalize_grade(label: str) -> str | None:
    """Map a CDE column header onto the canonical grade code.

    CDE writes grades as ordinals ("1st" ... "12th") and splits kindergarten
    into two columns, "Half-Day K" and "Full-Day K". Both map to K and are
    summed downstream, because CCD and the pre-2000 district tables carry a
    single undivided K. That sum is the archive's first real cleaning rule.
    """
    s = re.sub(r"[^A-Z0-9]", "", str(label).upper())
    if s in {"PK", "PREK", "P", "PRESCHOOL", "PREKINDERGARTEN"}:
        return "PK"
    if s in {"K", "KG", "KINDER", "KINDERGARTEN", "HALFDAYK", "FULLDAYK", "HDK", "FDK"}:
        return "K"
    m = re.fullmatch(r"(?:GRADE|GR)?0*(\d{1,2})(?:ST|ND|RD|TH)?", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return str(int(m.group(1)))
    return None


def harmonize_cde_table(rows: list[list], year: int) -> tuple[list[dict], dict]:
    """Find the header row, map its grade columns, and emit long records."""
    header_idx, grade_cols = None, {}
    for i, row in enumerate(rows[:40]):
        mapped = {j: normalize_grade(v) for j, v in enumerate(row) if normalize_grade(v)}
        if len(mapped) >= 8:
            header_idx, grade_cols = i, mapped
            break
    if header_idx is None:
        return [], {"error": "no header row with >=8 grade columns found"}

    header = [str(v).strip() for v in rows[header_idx]]

    def find(*patterns):
        for j, name in enumerate(header):
            for pat in patterns:
                if re.search(pat, name, re.I):
                    return j
        return None

    cols = {
        "school_code": find(r"^school\s*(code|number|no)", r"school.*code"),
        "school_name": find(r"^school\s*name", r"^school$"),
        "district_code": find(r"(district|lea|organization).*(code|number|no)"),
        "district_name": find(r"(district|lea|organization).*name", r"^district$"),
    }

    def cell(row, idx):
        if idx is None or idx >= len(row):
            return ""
        value = row[idx]
        text = str(value).strip()
        # pandas reads numeric-looking codes as floats; "0010" becomes 10.0
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]
        return text

    records, dropped = [], 0
    for row in rows[header_idx + 1:]:
        if not any(str(v).strip() for v in row):
            continue
        code = cell(row, cols["school_code"])
        if not code or not code.isdigit():
            dropped += 1
            continue
        base = {
            "year": year,
            "school_code": code.zfill(4),
            "school_name": cell(row, cols["school_name"]),
            "district_code": cell(row, cols["district_code"]).zfill(4) if cell(row, cols["district_code"]).isdigit() else cell(row, cols["district_code"]),
            "district_name": cell(row, cols["district_name"]),
        }
        # Sum grades rather than append, so the two kindergarten columns
        # collapse into one K.
        totals: dict[str, int] = {}
        for j, grade in grade_cols.items():
            raw = cell(row, j).replace(",", "")
            if raw in {"", "-", "*", "N/A", "n/a"}:
                continue
            try:
                totals[grade] = totals.get(grade, 0) + int(float(raw))
            except ValueError:
                continue
        for grade, value in totals.items():
            records.append({**base, "grade": grade, "enrollment": value})

    k_columns = [header[j] for j, g in sorted(grade_cols.items()) if g == "K"]
    meta = {
        "header_row": header_idx,
        "grade_columns": {str(k): v for k, v in sorted(grade_cols.items())},
        "kindergarten_columns_summed": k_columns,
        "id_columns": {k: (header[v] if v is not None else None) for k, v in cols.items()},
        "schools": len({r["school_code"] for r in records}),
        "records": len(records),
        "rows_dropped_no_school_code": dropped,
    }
    return records, meta


def harmonize_ccd(year: int) -> tuple[list[dict], dict]:
    directory = json.loads((RAW / f"ccd-directory-{year}.json").read_text())
    enrollment = json.loads((RAW / f"ccd-enrollment-{year}.json").read_text())

    def state_code(raw: str | None) -> str:
        """CCD's state school id changed shape in 2016: through 2015 it is a
        bare 4-digit CDE school code, from 2016 it is '<district>-<school>'.
        Take the school part either way, so one crosswalk spans both eras."""
        s = (raw or "").strip()
        return s.split("-")[-1].zfill(4) if s else ""

    info = {
        d["ncessch"]: {
            "school_name": d.get("school_name") or "",
            "district_name": (d.get("lea_name") or "").strip(),
            "seasch": state_code(d.get("seasch")),
            "seasch_raw": (d.get("seasch") or "").strip(),
            "teachers_fte": d.get("teachers_fte"),
            "latitude": d.get("latitude"),
            "longitude": d.get("longitude"),
            "charter": d.get("charter"),
            "status": d.get("school_status"),
        }
        for d in directory
    }

    records = []
    for e in enrollment:
        grade = CCD_GRADE.get(e.get("grade"))
        if grade is None:
            continue
        value = e.get("enrollment")
        if value is None or value < 0:
            continue
        meta = info.get(e["ncessch"], {})
        records.append({
            "year": year,
            "ncessch": e["ncessch"],
            "seasch": meta.get("seasch", ""),
            "school_name": meta.get("school_name", ""),
            "district_name": meta.get("district_name", ""),
            "grade": grade,
            "enrollment": value,
        })

    usable_coords = sum(
        1 for v in info.values()
        if isinstance(v.get("latitude"), (int, float)) and v["latitude"] > 30
    )
    fte_present = sum(1 for v in info.values() if isinstance(v.get("teachers_fte"), (int, float)) and v["teachers_fte"] > 0)

    raw_ids = [v["seasch_raw"] for v in info.values() if v["seasch_raw"]]
    meta = {
        "directory_rows": len(directory),
        "enrollment_rows": len(enrollment),
        "schools_with_grade_rows": len({r["ncessch"] for r in records}),
        "schools_with_teacher_fte": fte_present,
        "schools_with_usable_coordinates": usable_coords,
        "schools_with_state_id": len(raw_ids),
        "state_id_format": ("district-school" if raw_ids and "-" in raw_ids[0] else "bare school code"),
        "state_id_example": raw_ids[0] if raw_ids else None,
    }
    return records, meta


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def total(records: list[dict]) -> int:
    return sum(r["enrollment"] for r in records)


def main() -> None:
    for d in (RAW, INTERIM, AUDIT):
        d.mkdir(parents=True, exist_ok=True)

    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    print("Downloading CDE files...")
    download_cde(manifest)
    print("Downloading CCD...")
    download_ccd(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    findings: dict = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "years": {}}

    for spec in YEARS:
        cde_year, ccd_year = spec["cde_year"], spec["ccd_year"]
        print(f"Year {cde_year}...")
        entry: dict = {"ccd_year": ccd_year}

        # --- CDE side ---
        path_xlsx = RAW / f"membership-{cde_year}.xlsx"
        path_xls = RAW / f"membership-{cde_year}.xls"
        path_pdf = RAW / f"membership-{cde_year}.pdf"

        cde_records: list[dict] = []
        sheet = path_xlsx if path_xlsx.exists() else (path_xls if path_xls.exists() else None)
        if sheet is not None:
            rows = read_sheet(sheet)
            cde_records, meta = harmonize_cde_table(rows, cde_year)
            entry["cde"] = {"format": sheet.suffix.lstrip("."),
                            "parsed": "error" not in meta, **meta}
        elif path_pdf.exists():
            pages = pdf_text_pages(path_pdf)
            has_text = sum(1 for p in pages if len(p) > 40)
            entry["cde"] = {
                "format": "pdf-only",
                "parsed": False,
                "pages": len(pages),
                "pages_with_text_layer": has_text,
                "blocker": "no spreadsheet published this year; needs table extraction from PDF",
                "first_page_sample": (pages[0][:200] if pages else ""),
            }

        if cde_records:
            entry["cde"]["total_enrollment"] = total(cde_records)
            out = INTERIM / f"cde-{cde_year}.json"
            out.write_text(json.dumps(cde_records[:50], indent=2) + "\n")
            entry["cde"]["sample_written"] = str(out.relative_to(HERE))

        # --- teacher FTE ---
        fte_xlsx = RAW / f"teacher-fte-{cde_year}.xlsx"
        fte_pdf = RAW / f"teacher-fte-{cde_year}.pdf"
        if fte_xlsx.exists():
            rows = read_sheet(fte_xlsx)
            # These files carry title rows above the header, so find the row
            # that actually names the FTE column.
            head_idx = next(
                (i for i, r in enumerate(rows[:20])
                 if any(re.search(r"teacher\s*fte", str(v), re.I) for v in r)),
                0,
            )
            header = [str(v).strip() for v in rows[head_idx]]
            fte_col = next((j for j, h in enumerate(header) if re.search(r"teacher\s*fte", h, re.I)), None)
            code_col = next((j for j, h in enumerate(header) if re.search(r"school\s*code", h, re.I)), None)
            fte_by_school = {}
            if fte_col is not None and code_col is not None:
                for row in rows[head_idx + 1:]:
                    if code_col >= len(row) or fte_col >= len(row):
                        continue
                    code = str(row[code_col]).strip()
                    if code.endswith(".0"):
                        code = code[:-2]
                    if not code.isdigit():
                        continue
                    try:
                        fte_by_school[code.zfill(4)] = float(str(row[fte_col]).replace(",", ""))
                    except ValueError:
                        continue
            entry["teacher_fte"] = {
                "format": "xlsx", "parsed": bool(fte_by_school),
                "header_row": head_idx, "columns": header,
                "schools_with_fte": len(fte_by_school),
                "total_fte": round(sum(fte_by_school.values()), 1),
                "has_district_column": any(re.search(r"district|lea|organization", h, re.I) for h in header),
                "carries_own_enrollment_count": any(re.search(r"enrollment", h, re.I) for h in header),
            }
        elif fte_pdf.exists():
            pages = pdf_text_pages(fte_pdf)
            joined = " ".join(pages)
            entry["teacher_fte"] = {
                "format": "pdf", "parsed": False,
                "pages": len(pages),
                "blocker": "published as PDF; needs table extraction",
                "sample": joined[:240],
            }
        else:
            entry["teacher_fte"] = {"format": None,
                                    "blocker": "CDE publishes no school-grain teacher FTE this year"}

        # --- CCD side ---
        ccd_records, ccd_meta = harmonize_ccd(ccd_year)
        ccd_meta["total_enrollment"] = total(ccd_records)
        entry["ccd"] = ccd_meta
        out = INTERIM / f"ccd-{ccd_year}.json"
        out.write_text(json.dumps(ccd_records[:50], indent=2) + "\n")
        entry["ccd"]["sample_written"] = str(out.relative_to(HERE))

        # --- compare, where both sides parsed ---
        if cde_records:
            cde_by_school = {}
            for r in cde_records:
                cde_by_school.setdefault(r["school_code"], 0)
                cde_by_school[r["school_code"]] += r["enrollment"]
            ccd_by_seasch = {}
            for r in ccd_records:
                if r["seasch"]:
                    ccd_by_seasch.setdefault(r["seasch"], 0)
                    ccd_by_seasch[r["seasch"]] += r["enrollment"]

            # CDE school codes are 4-digit; CCD seasch is the state id.
            def keys(d):
                return {k.lstrip("0") for k in d if k.lstrip("0")}

            overlap = keys(cde_by_school) & keys(ccd_by_seasch)
            # PK is the usual suspect when the two state totals diverge, so
            # report the gap with and without it rather than as one number.
            cde_pk = sum(r["enrollment"] for r in cde_records if r["grade"] == "PK")
            ccd_pk = sum(r["enrollment"] for r in ccd_records if r["grade"] == "PK")
            entry["comparison"] = {
                "cde_schools": len(cde_by_school),
                "ccd_schools": len(ccd_by_seasch),
                "matched_on_state_id": len(overlap),
                "cde_total": sum(cde_by_school.values()),
                "ccd_total": sum(ccd_by_seasch.values()),
                "cde_prek": cde_pk,
                "ccd_prek": ccd_pk,
                "gap_all_grades": sum(cde_by_school.values()) - sum(ccd_by_seasch.values()),
                "gap_excluding_prek": (sum(cde_by_school.values()) - cde_pk)
                                      - (sum(ccd_by_seasch.values()) - ccd_pk),
            }
            if overlap:
                cde_norm = {k.lstrip("0"): v for k, v in cde_by_school.items()}
                ccd_norm = {k.lstrip("0"): v for k, v in ccd_by_seasch.items()}
                diffs = [abs(cde_norm[k] - ccd_norm[k]) for k in overlap]
                exact = sum(1 for k in overlap if cde_norm[k] == ccd_norm[k])
                entry["comparison"]["exact_agreement"] = exact
                entry["comparison"]["median_abs_diff"] = sorted(diffs)[len(diffs) // 2]
                entry["comparison"]["max_abs_diff"] = max(diffs)

        findings["years"][str(cde_year)] = entry

    (AUDIT / "proof-run.json").write_text(json.dumps(findings, indent=2) + "\n")
    print(f"\nWrote {AUDIT / 'proof-run.json'}")
    print(json.dumps(findings, indent=2)[:4000])


if __name__ == "__main__":
    main()
