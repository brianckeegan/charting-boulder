"""
Boulder budget books — extract facts from the page-text dump
============================================================
Reads the JSONL produced by `budget-books-inventory.py --dump-text` and pulls
out the handful of numbers the historical series needs, with the page each one
came from.

    python3 budget-books-extract.py dump.jsonl -o budget-books-extracted.csv

Why regex over prose rather than table parsing
----------------------------------------------
The figures are not in tables. Every budget book states them in a sentence:

    "The total 2026 Approved Budget is $521.0 million across all funds,
     including a 2026 Operating Budget of $407.7 million and 2026 Capital
     Budget of $113.3 million."
    "The 2023 Approved Budget includes a total city staffing level of
     1,540.09 full-time equivalents (FTEs)."

That is far more tractable than reconstructing table geometry across 22 years
of changing layouts — but it means the phrasing shifts book to book, so each
fact carries several patterns and the ones that match nothing are reported
rather than silently dropped.

PDF text extraction mangles numbers
-----------------------------------
Real examples from this corpus: "1, 451", "1,548. 28", "$ 407.7", "full- time".
Every numeric pattern therefore tolerates internal whitespace, and `to_number`
strips it before parsing. A pattern written against clean text will silently
miss most years.

Output is CANDIDATES, not truth
-------------------------------
Each row carries the page and the surrounding sentence so a human can confirm
it. Where a year yields conflicting values the script reports all of them and
flags the year rather than picking one.
"""

import argparse
import collections
import csv
import json
import re
import sys

# Tolerate the internal whitespace that PDF extraction injects into numbers.
NUM = r'([\d][\d,\.\s]{0,14}\d)'


def to_number(s):
    s = re.sub(r'[\s]', '', s).rstrip('.').replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def plausible(lo, hi):
    return lambda v: v is not None and lo <= v <= hi


# measure -> (patterns, plausibility test, unit)
FACTS = {
    # The gap before "budget" must not swallow "operating" or "capital".
    # Without the lookahead, "The total 2025 Approved OPERATING Budget is
    # $399.3 million" was captured as the 2025 TOTAL budget — off by $190M
    # against the real $589.3M, and wrong in a way that looks plausible.
    "budget_total": (
        [r'total\s+\d{4}(?:(?!operating|capital)[^.$]){0,40}budget is\s*\$\s*' + NUM + r'\s*million',
         r'total annual budget of\s*\$\s*' + NUM + r'\s*million',
         r'total budget(?:(?!operating|capital)[^.$]){0,30}\$\s*' + NUM + r'\s*million'],
        plausible(150, 900), "musd"),
    "budget_operating": (
        [r'operating budget (?:of|is)\s*\$\s*' + NUM + r'\s*million',
         r'total\s+\d{4}[^.$]{0,40}operating budget is\s*\$\s*' + NUM + r'\s*million'],
        plausible(100, 700), "musd"),
    "budget_capital": (
        [r'capital budget (?:of|is)\s*\$\s*' + NUM + r'\s*million'],
        plausible(20, 400), "musd"),
    "staffing_fte": (
        [r'total city staffing level of\s*' + NUM,
         r'staffing level of\s*' + NUM + r'\s*(?:full|FTE)',
         r'includes a total[^.]{0,40}staffing level of\s*' + NUM,
         NUM + r'\s*FULL[- ]TIME EQUIVALENTS'],
        plausible(800, 2500), "fte"),
}


def extract(rows):
    out = []
    for r in rows:
        flat = re.sub(r'\s+', ' ', r['text'])
        for measure, (pats, ok, unit) in FACTS.items():
            for pat in pats:
                for m in re.finditer(pat, flat, re.I):
                    v = to_number(m.group(1))
                    if not ok(v):
                        continue
                    ctx = flat[max(0, m.start() - 70): m.start() + 110].strip()
                    out.append({
                        "year": r["year"], "measure": measure, "value": v, "unit": unit,
                        "file": r["file"], "page": r["page"],
                        "context": re.sub(r'\s+', ' ', ctx),
                    })
    return out


def main():
    ap = argparse.ArgumentParser(description="Extract budget facts from a page-text dump.")
    ap.add_argument("dump", help="JSONL from budget-books-inventory.py --dump-text")
    ap.add_argument("-o", "--out", default="budget-books-extracted.csv")
    args = ap.parse_args()

    rows = []
    with open(args.dump) as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    # --extract writes excerpt PDFs beside the originals; if they were scanned
    # too, every page appears twice. Drop them.
    rows = [r for r in rows if 'excerpt' not in r['file'].lower()]
    if not rows:
        sys.exit("no usable pages in the dump")

    found = extract(rows)

    # Collapse duplicates (the same sentence can appear in a summary and again
    # in a detail section), then flag any year where a measure disagrees.
    best, conflicts = {}, collections.defaultdict(set)
    for f in found:
        key = (f["year"], f["measure"])
        conflicts[key].add(f["value"])
        best.setdefault(key, f)

    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "year", "measure", "value", "unit", "file", "page", "n_values", "conflict", "context"])
        w.writeheader()
        for key in sorted(best, key=lambda k: (k[0], k[1])):
            row = dict(best[key])
            vals = conflicts[key]
            row["n_values"] = len(vals)
            row["conflict"] = "" if len(vals) == 1 else " | ".join(str(v) for v in sorted(vals))
            w.writerow(row)

    years = sorted({r["year"] for r in rows})
    print(f"read {len(rows)} pages, {years[0]}-{years[-1]}")
    print(f"wrote {args.out}: {len(best)} facts\n")
    for measure in FACTS:
        got = sorted(y for (y, m) in best if m == measure)
        miss = [y for y in years if y not in got]
        print(f"  {measure:<18} {len(got):>2} years  {got}")
        if miss:
            print(f"  {'':<18}    missing: {miss}")
    flagged = sorted({k[0] for k, v in conflicts.items() if len(v) > 1})
    if flagged:
        print(f"\n  years with conflicting values (check the CSV): {flagged}")


if __name__ == "__main__":
    main()
