"""Read a BVSD Enrollment Pattern Matrix into tidy tables.

One matrix per level per year: every neighbourhood attendance area against
every school, with per-school totals down the right-hand side and per-area
totals along the bottom.

Almost nothing in the file says which row or column is which. The column
headings are set at ninety degrees, the footer rows' captions run together
into a single text box, and the district's TOTAL row shares a line with a
footer row. So the layout is not read off the labels; it is searched for,
and only the arrangement that satisfies the matrix's own arithmetic is
accepted. Two identities do the work:

    the flows in an area's column sum to     living - placed_out
    the areas' open-enrolment-out sums to    the district's open-enrolment-in

Both are exact integer checks, and together they name every footer row.
"""
from __future__ import annotations
import re
from itertools import permutations
from pathlib import Path
import numpy as np
import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

NUMBER = re.compile(r"^-?[\d,]+%?$")

# The eight per-school measures printed to the right of the grid, in the order
# every matrix prints them. Two are headed "District" - open enrolled in from
# within it and from outside it - so they are taken by position, never by name.
TAIL = ["attending_neighborhood_school", "oe_in_from_district", "oe_in_from_outside",
        "placements_into_school", "unmatched_addresses", "total_within_bvsd",
        "total_enrollment", "pct_from_neighborhood_area"]


def _characters(element):
    """Every LTChar under a text container, however deeply it is nested."""
    if isinstance(element, LTChar):
        yield element
        return
    if hasattr(element, "__iter__"):
        for child in element:
            yield from _characters(child)


def _cells(chars):
    """One entry per printed cell, from the characters alone.

    The extractor does not put one cell in one box. In the older matrices it
    runs a whole column of figures into a single box - "269 34" is two cells
    two lines apart - and elsewhere it runs neighbours on a line together.
    Either way the box's own text and position describe none of the figures in
    it. Splitting on the gaps, down the page and then across it, recovers the
    cell that was actually printed.
    """
    for line in _group(chars, key=lambda c: c.y0, tolerance=2.0):
        for run in _group(sorted(line, key=lambda c: c.x0),
                          key=lambda c: c.x0, tolerance=1.8, gap=True):
            text = "".join(c.get_text() for c in run).strip()
            if text:
                yield {"x": min(c.x0 for c in run), "x1": max(c.x1 for c in run),
                       "y": min(c.y0 for c in run), "y1": max(c.y1 for c in run),
                       "text": text}


def _group(chars, key, tolerance, gap=False):
    """Characters in runs, broken wherever the step exceeds the tolerance."""
    groups = []
    for char in sorted(chars, key=key):
        edge = max(c.x1 for c in groups[-1]) if (gap and groups) else None
        step = (key(char) - edge) if gap and groups else (
            abs(key(char) - key(groups[-1][-1])) if groups else None)
        if groups and step <= tolerance:
            groups[-1].append(char)
        else:
            groups.append([char])
    return groups


def _boxes(path: Path):
    """Label boxes, number cells, and every rotated character with its place."""
    page = next(iter(extract_pages(str(path))))
    labels, numbers, turned = [], [], []
    for element in page:
        if not isinstance(element, LTTextContainer):
            continue
        chars = list(_characters(element))
        if not chars:
            continue
        if abs(chars[0].matrix[1]) > 0.5:
            turned.extend({"x": c.x0, "y": c.y0, "text": c.get_text()}
                          for c in chars)
            continue
        for cell in _cells(chars):
            if NUMBER.match(cell["text"]):
                numbers.append(cell)
        text = element.get_text().strip()
        if text and not NUMBER.match(re.sub(r"\s+", " ", text)):
            labels.append({"x": element.x0, "y": element.y0, "x1": element.x1,
                           "y1": element.y1, "text": re.sub(r"\s+", " ", text)})
    return labels, numbers, turned


def _cluster(values, tolerance):
    centres = []
    for value in sorted(values):
        if centres and value - centres[-1][-1] <= tolerance:
            centres[-1].append(value)
        else:
            centres.append([value])
    return [sum(group) / len(group) for group in centres]


def _nearest(value, centres):
    return min(range(len(centres)), key=lambda i: abs(centres[i] - value))


def _heading(chars):
    """One heading from a column of rotated characters.

    Every heading is printed twice, once at each end of the table, and the two
    copies share an x. Sorted by y they appear as two blocks with a wide gap
    between them, so the heading is the first block. Splitting on the gap
    rather than halving the string matters where the second copy overlaps a
    neighbouring heading and the two interleave: "Optional Bear Creek/
    Creekside" comes back doubled as "...Optional CBreeaerk Csirdeeek/", which
    no halving can undo.
    """
    chars = sorted(chars, key=lambda c: c["y"])
    gaps = [chars[i + 1]["y"] - chars[i]["y"] for i in range(len(chars) - 1)]
    if gaps and max(gaps) > 8:
        chars = chars[:gaps.index(max(gaps)) + 1]
    return re.sub(r"\s+", " ", "".join(c["text"] for c in chars)).strip()


ROW_TOLERANCES = (5.0, 3.0, 2.0, 1.5)


def read_matrix(path: Path, row_tolerance: float = 5.0) -> tuple[pd.DataFrame, dict]:
    """The matrix as printed: rows by y, columns by x, text uninterpreted."""
    return _grid(*_boxes(path), row_tolerance)


def _grid(labels, numbers, turned, row_tolerance):
    """Rows and columns from positions alone.

    How far apart two figures must be to be on different lines is not the same
    in every volume - the 2016-17 matrices are set tighter than the rest, and
    at the usual spacing two of their lines merge into one. So the spacing is
    not fixed here; `tidy` tries several and keeps whichever one produces a
    matrix that adds up.
    """
    heads = {}
    for column in _cluster([c["x"] for c in turned], 5.0):
        label = _heading([c for c in turned if abs(c["x"] - column) <= 5.0])
        if label:
            heads[round(column, 1)] = label

    # The figures are centred in their cells, not right-aligned: "35" and "128"
    # share a centre and nothing else. Columns taken from the right-hand edge
    # split a column in two wherever a percentage sits under its counts.
    for box in numbers:
        box["mid"] = (box["x"] + box["x1"]) / 2
    rows = _cluster([b["y"] for b in numbers], row_tolerance)
    cols = _cluster([b["mid"] for b in numbers], 8.0)

    grid = {}
    for box in numbers:
        grid[(_nearest(box["y"], rows), _nearest(box["mid"], cols))] = box["text"]

    names = {}
    for index, y in enumerate(rows):
        candidates = [b for b in labels
                      if abs(b["y"] - y) <= 6.0 and b["x"] < min(cols) - 5]
        if candidates:
            names[index] = min(candidates, key=lambda b: b["x"])["text"]

    frame = pd.DataFrame(
        [[grid.get((r, c), "") for c in range(len(cols))] for r in range(len(rows))],
        index=[names.get(r, f"row{r}") for r in range(len(rows))])
    frame.columns = [heads.get(round(_closest_head(c, heads), 1), f"col{i}")
                     for i, c in enumerate(cols)]
    # A column of figures can be split in two by one stray box, leaving an
    # empty column wedged between two areas. Nothing was printed there, and
    # leaving it in breaks the run of areas the arithmetic is checked over.
    frame = frame.loc[:, (frame != "").any(axis=0)]
    frame = frame.loc[(frame != "").any(axis=1)]
    return frame, {"rows": len(frame), "columns": len(frame.columns),
                   "headings": len(heads), "row_tolerance": row_tolerance}


def _closest_head(x, heads):
    return min(heads, key=lambda h: abs(h - x)) if heads else 0.0


def _count(text):
    """A printed count. Percentages are read separately and never as counts."""
    text = str(text).strip().replace(",", "")
    if not text or text.endswith("%"):
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def _percent(text):
    text = str(text).strip()
    return float(text[:-1]) / 100 if text.endswith("%") else np.nan


def _layout(counts: pd.DataFrame) -> dict:
    """Which rows are the footer, which columns are areas, and what each is.

    Searched rather than read. A candidate is accepted only where every area
    column satisfies `flows = living - placed_out` exactly, which leaves one
    footer row over: the open enrolment out.
    """
    n_rows, n_cols = counts.shape
    found = []
    # The 2016-17 elementary matrix prints each footer total on a line of its
    # own, which doubles the depth of the block, so the search has to go deeper
    # than the four rows the later matrices use.
    for n_foot in range(2, min(10, n_rows)):
        foot, body = counts.iloc[:n_foot], counts.iloc[n_foot:]
        for n_area in range(max(3, n_cols - 10), n_cols - 7):
            flows = body.iloc[:, :n_area].sum(axis=0)
            for living, placed in permutations(range(n_foot), 2):
                # A missing figure makes every comparison against it false, so
                # a blank row would pass this test rather than fail it. Every
                # area has a population, so that row must be complete; none
                # placed out is printed as a blank, and is read as none only
                # because the identity below still has to come out exact.
                if not foot.iloc[living, :n_area].notna().all():
                    continue
                # Blanks read as none, so a row holding no counts at all - the
                # percentages, to the parser, are blank - would otherwise pass
                # as "nobody placed out" and swallow a real footer row.
                if not foot.iloc[placed, :n_area].notna().any():
                    continue
                gap = (foot.iloc[living, :n_area]
                       - foot.iloc[placed, :n_area].fillna(0) - flows).abs()
                if not gap.notna().all():
                    continue
                # One area may miss by a pupil or two without the reading being
                # wrong - in 2016-17 Nederland's high-school column does, and
                # everything else in that matrix reconciles exactly. More than
                # one, or a wider miss, means the arrangement is wrong.
                exact = int((gap < 0.5).sum())
                if exact < n_area - 1 or gap.max() > 2:
                    continue
                # Every area sends somebody elsewhere, so that row is complete
                # too. Requiring it keeps the percentage row from standing in
                # where the extractor has dropped a count into it.
                spare = [r for r in range(n_foot) if r not in (living, placed)
                         and foot.iloc[r, :n_area].notna().all()
                         and foot.iloc[r, :n_area].sum() > 0]
                if len(spare) != 1:
                    continue
                found.append({"footer_rows": n_foot, "areas": n_area,
                              "living": living, "placed": placed,
                              "oe_out": spare[0], "areas_exact": exact})
    if not found:
        raise ValueError("no arrangement of this matrix satisfies its own totals")
    # A shorter prefix of the areas passes the same test, so take the longest.
    return max(found, key=lambda f: (f["areas_exact"], f["areas"], -f["footer_rows"]))


def tidy(path: Path, level: str, school_year: str):
    """Flows, per-school totals, per-area totals and the checks on all three.

    Read at each line spacing in turn and judged on its own arithmetic: the
    reading kept is the one where every school row rebuilds to its printed
    total and the areas' open enrolment out balances the schools' open
    enrolment in.
    """
    boxes = _boxes(path)
    best = None
    for tolerance in ROW_TOLERANCES:
        try:
            result = _tidy(boxes, tolerance, level, school_year)
        except (ValueError, IndexError):
            continue
        checks = result[3]
        score = (checks["school_rows_exact"] == checks["school_rows"],
                 checks["oe_balances"], checks["school_rows_exact"],
                 checks["areas_exact"], checks["areas"])
        if best is None or score > best[0]:
            best = (score, result)
    if best is None:
        raise ValueError(f"no reading of {path.name} satisfies its own totals")
    return best[1]


def _tidy(boxes, tolerance, level: str, school_year: str):
    grid, info = _grid(*boxes, tolerance)
    counts = grid.map(_count)
    plan = _layout(counts)
    n_foot, n_area = plan["footer_rows"], plan["areas"]
    foot, body = counts.iloc[:n_foot], counts.iloc[n_foot:]
    tail = body.iloc[:, len(grid.columns) - len(TAIL):]

    # The district's own TOTAL row is a row like any other here, and would be
    # counted twice. It is the one whose enrollment is every other row's.
    enrollment = tail.iloc[:, TAIL.index("total_enrollment")]
    total_row = [i for i in range(len(body))
                 if abs(enrollment.iloc[i] - (enrollment.sum() - enrollment.iloc[i]))
                 < 0.5]
    schools = [i for i in range(len(body)) if i not in total_row]

    names = [str(c).strip() for c in grid.columns[:n_area]]
    areas = pd.DataFrame({
        "level": level, "school_year": school_year, "attendance_area": names,
        "students_living_in_area": foot.iloc[plan["living"], :n_area].values,
        "oe_out_of_area": foot.iloc[plan["oe_out"], :n_area].fillna(0).values,
        "placed_out_of_area": foot.iloc[plan["placed"], :n_area].fillna(0).values})
    areas["staying_in_neighborhood_school"] = (areas["students_living_in_area"]
                                               - areas["oe_out_of_area"]
                                               - areas["placed_out_of_area"])
    areas["pct_staying_in_neighborhood_school"] = (
        areas["staying_in_neighborhood_school"] / areas["students_living_in_area"])

    rows = []
    for i in schools:
        row = {"level": level, "school_year": school_year,
               "school": str(body.index[i]).strip()}
        for position, name in enumerate(TAIL):
            row[name] = tail.iat[i, position]
        rows.append(row)
    schools_frame = pd.DataFrame(rows)

    flows = []
    for i in schools:
        for column in range(n_area):
            value = body.iat[i, column]
            if value and not np.isnan(value) and value > 0:
                flows.append({"level": level, "school_year": school_year,
                              "school": str(body.index[i]).strip(),
                              "attendance_area": names[column], "students": value})
    flows_frame = pd.DataFrame(flows)

    checks = _checks(grid, plan, areas, schools_frame, flows_frame, n_foot)
    checks.update({"level": level, "school_year": school_year,
                   "areas": n_area, "areas_exact": plan["areas_exact"],
                   "schools": len(schools_frame), **info})
    return flows_frame, schools_frame, areas, checks


def _checks(grid, plan, areas, schools, flows, n_foot):
    """Three independent tests of the reading, reported rather than asserted."""
    drawn = flows.groupby("school")["students"].sum()
    rebuilt = (schools["school"].map(drawn).fillna(0)
               + schools["oe_in_from_outside"].fillna(0)
               + schools["placements_into_school"].fillna(0)
               + schools["unmatched_addresses"].fillna(0))
    school_gap = (rebuilt - schools["total_enrollment"]).abs()

    # Everyone who open-enrols out of an area open-enrols into some school.
    into = schools["oe_in_from_district"].sum()
    out = areas["oe_out_of_area"].sum()

    # The percentages are printed as whole numbers; the computed share must
    # round to them wherever the printed row survived the extraction. They are
    # read only from the footer rows the three counts left over, so a stray
    # percentage in the tail cannot stand in for the row that matters.
    spare = [r for r in range(n_foot)
             if r not in (plan["living"], plan["placed"], plan["oe_out"])]
    printed = (grid.iloc[spare, :len(areas)].map(_percent).max(axis=0, skipna=True)
               if spare else pd.Series(np.nan, index=range(len(areas))))
    shown = printed.notna()
    pct_gap = np.abs(areas["pct_staying_in_neighborhood_school"].values[shown.values]
                     - printed[shown].values)
    return {
        "school_rows_exact": int((school_gap < 0.5).sum()),
        "school_rows": int(len(schools)),
        "oe_out_total": float(out), "oe_in_total": float(into),
        "oe_gap": float(into - out),
        "oe_balances": bool(abs(out - into) < 0.5),
        "pct_checked": int(shown.sum()),
        # The share is printed to the whole percentage point, so agreement
        # means within half of one.
        "pct_agree": int((pct_gap <= 0.005).sum()),
        "pct_worst": float(pct_gap.max()) if len(pct_gap) else float("nan"),
    }


if __name__ == "__main__":
    import sys
    name = Path(sys.argv[1]).stem
    level, year = name.split("_") if "_" in name else (name, "")
    flows, schools, areas, checks = tidy(Path(sys.argv[1]), level, year)
    print(checks)
    print(areas.to_string(index=False))
