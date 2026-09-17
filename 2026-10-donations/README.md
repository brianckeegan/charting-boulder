# 2026-10-donations

## Question
Who funds and who vouches for Boulder's council candidates, and how divided are those two
networks? Since 2015 the city's donors and the people who lend their names to candidates'
endorsement pages have sorted into two camps. How stable are the camps, how many people cross
them, and does the money network look like the endorsement network?

## Decision peg
The November 3, 2026 City of Boulder election: the first even-year election, a mayoral race and
five council seats, with the 2026 finance filings already in the archive.

## Layout
```
2026-10-donations/
├── donations-retrieval.ipynb   reads a local clone of boulder-voter-data, writes data/processed (anonymized)
├── donations-analysis.ipynb    projections, measures, figures; reads data/processed only, no network
├── retrieval.py, analysis.py   the same code as scripts; nb_build.py rebuilds the notebooks from them
├── data/processed/             derived tables committed to this public repository
└── output/                     tables and figures the column draws on
```

The two notebooks split on one rule. The retrieval notebook may read the private archive,
clean, join and pseudonymize; it may not compute a measure the column reports. The analysis
notebook computes every measure and figure from `data/processed/` alone.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| Donor-to-campaign edges, 2015-2026: one row per donor, campaign and year with dollars and gift count | City of Boulder campaign-finance filings, via `contributions/city/<year>.csv.gz` in the private `boulder-voter-data` archive | Derived, committed; donors are pseudonymous ids | `data/processed/donor-campaign-edges.csv` |
| Donors: first and last year, cycles, campaigns, dollars, ZIP (2015-2023 keys only) | same | Derived, committed; no names | `data/processed/donors.csv` |
| Campaigns: candidate and ballot-measure committees with votes, outcome and slate label | city filings; `campaigns/<year>/candidates.csv` and `endorsements/guides/parsed.csv` in the archive | Derived, committed; public names | `data/processed/campaigns.csv` |
| Group alignment: which side each group's picks fell on, per year | `group-slates.csv` and the poles | Derived, committed | `data/processed/group-alignment.csv` |
| Group slates: which group endorsed which candidate, 2015-2026 | the captured slate pages in `endorsements/guides/` (positions read by machine, unchecked) and the checked cells of the reference charts in `endorsements/reference/` (2021, 2023, 2025) | Derived, committed; `source` says which | `data/processed/group-slates.csv` |
| Endorser-to-campaign edges from candidates' own endorsement pages, with office and board flags | `campaigns/<year>/snapshots/` and `endorsements/endorsers.csv` in the archive | Derived, committed; people are pseudonymous ids, organizations named | `data/processed/endorser-campaign-edges.csv`, `endorser-nodes.csv` |

**Privacy.** The archive is private and its files are not republished. Every person here is a
pseudonymous id from a seeded shuffle whose mapping is not written anywhere; only campaigns,
committees, candidates, groups and organizations keep their names. A reader with the archive
can rebuild the tables by setting `BOULDER_VOTER_DATA` to the clone's path and running the
retrieval notebook.

## Method
- **Donor key.** Cleaned name plus five-digit ZIP for 2015-2023, which carry addresses. 2024-2026
  files carry no address: a name-only row is linked to an earlier name+ZIP donor when that name is
  unique among earlier donors, otherwise it is its own donor. `link_method` says which.
- **Campaigns.** Official candidate committees (one node per candidate-year) and issue or
  ballot-measure committees. Unofficial (slate) committees, anonymous gifts, candidates' own
  money, loans, reimbursements and organizational donors are excluded from the edges.
- **Projection.** Two donors are tied when they gave to the same campaign; weight = number of
  shared campaigns, with a second weight = sum over shared campaigns of the smaller gift.
  Annual networks per year; cumulative networks over 2015 through each council year.
- **Sides.** The axis is the decade's two poles: PLAN-Boulder County (`A`) against Better
  Boulder and Boulder Progressives (`B`). Every other endorsing group with a bloc in the archive's
  `groups.csv` (`orientation` growth-skeptic or progressive: Safer Boulder, FRWRD Boulder,
  thinkboulder, Together4Boulder, Boulder Elevated, Advocates for Clean Teens; Open Boulder, the
  Sierra Club, the labor council, United Campus Workers, CWA, DSA, the Working Families Party and
  their partners) is aligned year by year from its own picks (`data/processed/group-alignment.csv`):
  it labels a year on the side where all its pole-labelled picks fall, and does not label a year
  in which its picks split across the poles (the Sierra Club in 2015 and 2017, the labor council
  in 2019 and 2021, Open Boulder in 2025). A group with no pole-labelled pick in a year falls back
  to its bloc. Newspapers, questionnaire marks and the business groups (which sat on different
  sides in 2017 and 2023) never label. A candidate is `A` or `B` from the union of the poles and
  the aligned groups, `AB` when both sides endorsed them, blank when neither did. `campaigns.csv`
  keeps the plain two-pole label (`slate_side_two_poles`) for comparison. A donor's side is where
  60 percent or more of their candidate dollars went; `AB` when split.
- **Polarization.** Modularity of the side partition on the donor projection, against the best
  split Leiden finds and against two nulls: shuffled labels on the same graph, and a
  degree-preserving rewiring of the bipartite graph. Also the E-I index and the share of donors
  who give to both sides.
- **Consistency.** Cycles per donor, share of a year's donors and dollars from returning donors,
  and the side-to-side transition table for repeat donors.
- **Endorsements.** The same construction from the names on candidates' endorsement pages,
  for the years with captured pages; endorser features are whether the person has held Boulder
  council or mayoral office, any elected office, or a city board seat.
- **Comparison.** Candidate-level Jaccard overlap of donor sets and of endorser sets, their
  Mantel correlation with a permutation test, and the slate modularity of each candidate-level
  network.

## Outputs
`output/donor-network-annual.csv`, `donor-network-cumulative.csv`, `donor-retention.csv`,
`donor-side-transitions.csv`, `donor-side-loyalty.csv`, `donor-consistency.json`,
`donor-concentration.csv`, `candidate-donor-overlap-<year>.csv`, `endorsement-network-annual.csv`,
`endorser-consistency.json`, `endorser-side-loyalty.csv`, `candidate-endorser-overlap-<year>.csv`,
`donor-vs-endorser-comparison.csv`, and the figures `fig-modularity.png`, `fig-retention.png`,
`fig-side-transitions.png`, `fig-candidate-overlap-<year>.png`, `fig-donor-vs-endorser.png`.

## Caveats
- Endorsement pages exist for a subset of candidates each year (most in 2019, 2021, 2025 and
  2026; four of fourteen in 2023; few in 2015 and 2017), and several were first archived after
  the election. The endorser names come from a heuristic read of page text and have not been
  checked by hand; the archive's `endorsers.csv` carries a `checked` flag for that review.
- Slate labels rest on the positions read from the group pages (unchecked) and on the checked reference charts for 2021, 2023 and 2025; the bloc each group sits in is the archive owner's call.
- The 2026 rows are the filings and pages as of September 15, 2026, before the election.
