"""Build the two notebooks from retrieval.py and analysis.py.

Each `# ---- ... <title>` comment line in the scripts starts a new section: a markdown cell with the
section's narrative (from NARRATIVE below) followed by a code cell. Run: python nb_build.py, then
jupyter nbconvert --to notebook --execute --inplace <notebook>.
"""
import re, nbformat as nbf
from pathlib import Path

HEAD_R = """# Charting Boulder: donations and endorsements, retrieval
[Brian C. Keegan, Ph.D.](http://www.brianckeegan.com)
October 2026

Released under a [MIT License](https://opensource.org/licenses/MIT).

This notebook reads the private `boulder-voter-data` archive from a local clone and writes derived,
anonymized tables to `data/processed/`. It draws no charts and computes no measure the column reports;
`donations-analysis.ipynb` does that from `data/processed/` alone.

**What leaves the archive.** Campaigns, committees, candidates, groups and organizations keep their
names: they are public actors on public filings and public pages. Donors and individual endorsers do
not: each becomes a pseudonymous id assigned by a seeded shuffle of the sorted keys, and the mapping
is never written. The archive's own rule is that its files are not republished elsewhere, and this
repository is public, so nothing here can be joined back to a person without the archive.

**Where the archive comes from.** `contributions/city/<year>.csv.gz` is the City of Boulder's
campaign-finance filings, one row per itemized contribution, 2015 to 2026 (2024 on has no address).
`endorsements/guides/parsed.csv` is the positions read from the group, coalition and newspaper slate
pages captured from the Wayback Machine. `endorsements/endorsers.csv` is the names on each candidate's
own endorsements page, also from the archive, with the offices each person has held.

Set `BOULDER_VOTER_DATA` to the clone's path (default `../../boulder-voter-data`).
"""
HEAD_A = """# Charting Boulder: donations and endorsements, analysis
[Brian C. Keegan, Ph.D.](http://www.brianckeegan.com)
October 2026

Released under a [MIT License](https://opensource.org/licenses/MIT).

This notebook reads only `data/processed/` and writes tables and figures to `output/`. It makes no
network call. A reader who clones this repository can run it end to end.

**The networks.** Every year's contributions form a bipartite graph: donors on one side, campaigns
(candidate committees and ballot-measure committees) on the other, an edge where a donor gave. The
one-mode donor projection links two donors who gave to the same campaign; the edge weight is the
number of campaigns they share (`shared`), with a second weight equal to the sum over shared campaigns
of the smaller of the two gifts (`min_dollars`). Annual networks use one year's edges; cumulative
networks use every edge from 2015 through the year. The endorsement networks are built the same way
from the names on candidates' endorsement pages.

**Sides.** The axis is the two poles of Boulder's decade-long divide, PLAN-Boulder County (`A`) against Better Boulder and Boulder Progressives (`B`). The other endorsing groups are aligned to a side year by year from their own picks and label only the years in which they did not endorse across the divide; a candidate is `A` or `B` from the poles and the aligned groups, `AB` when both sides endorsed them, blank when neither did. A donor's side in a year is where most of their candidate dollars went (60/40 rule); `AB`
means split. Modularity of that partition, against the best split Leiden can find and against two
nulls, is the polarization measure.
"""
NARRATIVE = {
 "contributions": "## Contributions to donor-campaign edges\n\nRead every city file, clean names (suffixes off, first token of the first name, organizations flagged by keyword), take the five-digit ZIP where the file has one, and key donors on cleaned name + ZIP. 2024 on has no address: a name-only row is linked to the one earlier name+ZIP donor with that name when that name is unique among earlier donors; otherwise it is its own name-only donor. The edge list keeps monetary and in-kind gifts to candidate and measure committees from named individuals; anonymous gifts, candidates' own money, loans, reimbursements and organizations are left out.",
 "group slates": "## Group slates to side labels\n\nTwo sources, unioned: `parsed.csv` (one row per year, group, contest, choice and position, read by machine from the captured pages) and the checked cells of the reference charts in `endorsements/reference/` (2021, 2023 and 2025). The axis is the two poles, PLAN-Boulder County against Better Boulder and Boulder Progressives. Every other group with a bloc in `groups.csv` is aligned year by year from its own picks: it labels a year on the side where all its pole-labelled picks fall and sits out a year in which its picks split (the Sierra Club in 2015 and 2017, the labor council in 2019 and 2021, Open Boulder in 2025). Newspapers, questionnaire marks and the business groups never label. A candidate is `A`, `B` or `AB` from the union of the poles and the aligned groups; the plain two-pole label is kept as `slate_side_two_poles`.",
 "endorsers": "## Endorsers to anonymized edges\n\nThe archive's `endorsers.csv` names each person or organization listed on a candidate's endorsement page with a stable id across years and the offices they have held. People become pseudonymous `e` ids here; organizations keep their names. Each edge carries what the analysis needs about the endorser: whether they have held Boulder council or mayoral office, any elected office, a city board or commission seat, and whether the page called them current or former.",
 "projections": "## Projections and measures\n\nHelpers: the one-mode projection, Leiden community detection (modularity objective, seeded), modularity of a given partition, a donor's side, the E-I index, and two nulls for the slate modularity: shuffled labels on the same graph, and a degree-preserving rewiring of the bipartite graph.",
 "annual donor networks": "## Annual donor networks\n\nFor every year 2015 to 2026: size, density, the best-split modularity (Leiden), the slate modularity, both nulls, the E-I index, and the shares of donors who gave to both slates or to neither.",
 "cumulative donor networks": "## Cumulative donor networks\n\nThe same measures on the union of edges from 2015 through each council year, with the donor's side taken over all their candidate dollars to date.",
 "consistency of donors": "## Consistency of donors across cycles\n\nHow many council elections each donor appears in, the share of a year's donors (and dollars) that gave in an earlier council election, and whether repeat donors keep their side between consecutive council elections.",
 "other measures": "## Other measures\n\nConcentration of dollars (Gini, top-decile share, share of donors at the $100 cap) and the Jaccard overlap of donor sets between candidates in each council year.",
 "endorsement networks": "## Endorsement networks\n\nThe same construction from the names on candidates' endorsement pages, for the years with captured pages: projection, Leiden and slate modularity, the share of endorsers who back candidates on both sides, and the share of people who have held elected office or served on a city board.",
 "donors vs endorsers": "## Donors against endorsers\n\nAt the candidate level: the Jaccard overlap of donor sets and of endorser sets between candidates, their Mantel correlation (permutation test), and how much of each candidate-level network the slate split explains.",
 "figures": "## Figures\n\nWritten to `output/`.",
}

def build(script, head, out):
    src = Path(script).read_text().split("\n")
    cells = [nbf.v4.new_markdown_cell(head)]
    buf, title = [], None
    def flush():
        code = "\n".join(buf).strip("\n")
        if not code: return
        key = next((k for k in NARRATIVE if title and k in title.lower()), None)
        if key: cells.append(nbf.v4.new_markdown_cell(NARRATIVE[key]))
        cells.append(nbf.v4.new_code_cell(code))
    for line in src:
        m = re.match(r"^# -{10,}\s*(.*)$", line)
        if m:
            flush(); buf = []; title = m.group(1).strip(); continue
        buf.append(line)
    flush()
    # drop the module docstring from the first code cell
    first = cells[1] if len(cells) > 1 and cells[1].cell_type == "code" else None
    if first and first.source.startswith('"""'):
        first.source = re.sub(r'^""".*?"""\n', "", first.source, count=1, flags=re.S).lstrip("\n")
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}, "language_info": {"name": "python"}})
    nbf.write(nb, out)
    print(out, len(cells), "cells")

build("retrieval.py", HEAD_R, "donations-retrieval.ipynb")
build("analysis.py", HEAD_A, "donations-analysis.ipynb")
