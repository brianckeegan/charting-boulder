"""Read a BVSD Enrollment Pattern Matrix into a tidy table."""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

NUMBER = re.compile(r"^-?[\d,]+%?$")


def _boxes(path: Path):
    """Upright text boxes, and every rotated character with its position.

    The column headings are set at ninety degrees and the extractor breaks
    them into fragments that are individually reversed, so joining the
    fragments gives "B o u d e r *" with the l missing. Working from the
    characters instead - each with its own y - reconstructs the heading
    exactly.
    """
    page = next(iter(extract_pages(str(path))))
    upright, turned = [], []
    for element in page:
        if not isinstance(element, LTTextContainer):
            continue
        rotated = None
        for obj in element:
            children = obj if hasattr(obj, "__iter__") else [obj]
            for char in children:
                if isinstance(char, LTChar):
                    if rotated is None:
                        rotated = abs(char.matrix[1]) > 0.5
                    if rotated:
                        turned.append({"x": char.x0, "y": char.y0,
                                       "text": char.get_text()})
        text = element.get_text().strip()
        if text and not rotated:
            upright.append({"x": element.x0, "y": element.y0, "x1": element.x1,
                            "y1": element.y1, "text": re.sub(r"\s+", " ", text)})
    return upright, turned


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


def read_matrix(path: Path) -> tuple[pd.DataFrame, dict]:
    upright, turned = _boxes(path)

    # One heading per column of rotated characters, read bottom to top.
    heads = {}
    for column in _cluster([c["x"] for c in turned], 5.0):
        chars = sorted([c for c in turned if abs(c["x"] - column) <= 5.0],
                       key=lambda c: c["y"])
        label = re.sub(r"\s+", " ", "".join(c["text"] for c in chars)).strip()
        # Every heading is printed twice, once at each end of the table, and
        # the two copies share a column, so the reconstruction doubles it.
        half = len(label) // 2
        if half and label[:half] == label[half:]:
            label = label[:half]
        if label:
            heads[round(column, 1)] = label.strip()

    numbers = [b for b in upright if NUMBER.match(b["text"])]
    labels = [b for b in upright if not NUMBER.match(b["text"])]
    rows = _cluster([b["y"] for b in numbers], 5.0)
    cols = _cluster([b["x1"] for b in numbers], 8.0)

    grid = {}
    for box in numbers:
        grid[(_nearest(box["y"], rows), _nearest(box["x1"], cols))] = box["text"]

    # A row's name is the upright text to the left of its numbers.
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
    return frame, {"rows": len(rows), "columns": len(cols), "headings": len(heads)}


def _closest_head(x, heads):
    return min(heads, key=lambda h: abs(h - x)) if heads else 0.0


if __name__ == "__main__":
    import sys
    frame, info = read_matrix(Path(sys.argv[1]))
    print(info)
    print(frame.to_string())
