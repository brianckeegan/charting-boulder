"""Download every file the inventory says we need, once, with a manifest.

Phase R of TASK.md. Originals land in data/raw/cde/ and are never edited in
place; all cleaning happens downstream. The manifest records URL, byte count,
SHA-256 and fetch time for every file, which is what makes the pipeline
reproducible without committing 100 MB of PDFs.

Only the rows the pipeline actually uses are fetched: enrollment and teacher
FTE, preferring a spreadsheet over a PDF where both exist for the same
year-measure-grain, since a spreadsheet needs no OCR and no position-aware
extraction.

Run:  python3 -m pipeline.fetch
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LOOKUPS = HERE / "data" / "lookups"
RAW = HERE / "data" / "raw" / "cde"
USER_AGENT = "charting-boulder/pipeline (+https://github.com/brianckeegan/charting-boulder)"

FORMAT_RANK = {"xlsx": 0, "xls": 1, "pdf": 2}


def choose(rows: list[dict]) -> list[dict]:
    """One file per (year, measure, grain), best format first.

    A year often publishes the same table as both PDF and XLS. The
    spreadsheet is always preferred: the PDFs of that era are kerning-split,
    so `604` arrives as `6 0 4` (finding A10), and extracting them costs
    either careful character-position work or an OCR pass.
    """
    best: dict[tuple, dict] = {}
    for row in rows:
        if row["measure"] == "other" or row["grain"] == "unknown":
            continue
        # The scanned yearbooks are 110 MB each and are handled by
        # datalab-ocr.py, which downloads one, extracts the table pages and
        # deletes it again. Fetching them here would pull 1.5 GB for nothing.
        if row["series"] == "yearbook":
            continue
        key = (int(row["year"]), row["measure"], row["grain"])
        rank = FORMAT_RANK.get(row["fmt"], 9)
        if key not in best or rank < FORMAT_RANK.get(best[key]["fmt"], 9):
            best[key] = row
    return [best[k] for k in sorted(best)]


def fetch(url: str, dest: Path, tries: int = 4) -> bytes:
    if dest.exists() and dest.stat().st_size > 0:
        return dest.read_bytes()
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return data
        except Exception as exc:  # noqa: BLE001
            if attempt == tries - 1:
                print(f"    FAILED {url}: {exc}")
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def main() -> None:
    inventory_path = LOOKUPS / "inventory.csv"
    if not inventory_path.exists():
        raise SystemExit("run `python3 -m pipeline.sources` first")

    with inventory_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    wanted = choose(rows)
    print(f"{len(rows)} files in inventory; {len(wanted)} needed")

    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for row in wanted:
        year, measure, grain, fmt = int(row["year"]), row["measure"], row["grain"], row["fmt"]
        name = f"{measure}-{grain}-{year}.{fmt}"
        dest = RAW / name
        status = "cached" if dest.exists() else "fetching"
        print(f"  {name:38s} {status}")
        try:
            data = fetch(row["url"], dest)
        except Exception:  # noqa: BLE001
            continue
        manifest[name] = {
            "url": row["url"],
            "label": row["label"],
            "series": row["series"],
            "year": year,
            "measure": measure,
            "grain": grain,
            "format": fmt,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"\nManifest: {len(manifest)} files, {sum(m['bytes'] for m in manifest.values()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
