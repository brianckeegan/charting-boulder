# 2026-03-bvcp

## Question
How has the Boulder Valley Comprehensive Plan changed across nearly half a century — what does its vocabulary, structure, and semantic content tell us about which problems Boulder learned to care about, and which it has effectively rewritten?

## Decision peg
Upstream of the 2026 BVCP update cycle and durable conversations about land use, conservation, and the city-county joint-planning compact. The notebooks treat the plan's evolution as a dataset rather than as a single document, surfacing what has been added, removed, or reframed across seventeen versions.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| BVCP plan versions, 1977–2026 draft | [City of Boulder Comprehensive Planning](https://bouldercolorado.gov/services/boulder-valley-comprehensive-plan) and archived historical PDFs | Derived Markdown committed to `corpus/`; source PDFs documented in this README but not committed (size) | `corpus/BVCP YYYY Mmm.md` (×17) |
| Voyage-4-large document embeddings | [Voyage AI](https://docs.voyageai.com/) `voyage-4-large` (1024-dim) | API at runtime — requires `VOYAGE_API_KEY` env var | Cached in `cache/voyage4large_chunk_embeddings.pkl` |

The seventeen plan versions and their nominal dates:

| Year | File |
|---|---|
| 1977 (Aug) | `BVCP 1977 Aug.md` |
| 1977 Rev. 1978 | `BVCP 1978.md` |
| 1978 (Apr) | `BVCP 1978 Apr.md` |
| 1978 (Jun) | `BVCP 1978 Jun.md` |
| 1979 | `BVCP 1979 Jun.md` |
| 1981 | `BVCP 1981 May.md` |
| 1983 | `BVCP 1983 Oct.md` |
| 1986 | `BVCP 1986 Oct.md` |
| 1990 | `BVCP 1990 Dec.md` |
| 1996 | `BVCP 1996 Nov.md` |
| 2001 | `BVCP 2001 Sep.md` |
| 2005 | `BVCP 2005 Dec.md` |
| 2008 | `BVCP 2008.md` |
| 2010 | `BVCP 2010.md` |
| 2015 | `BVCP 2015.md` |
| 2021 | `BVCP 2021 Mar.md` |
| 2026 Draft | `BVCP 2026 Mar.md` |

### Corpus retrieval

The PDFs of each historic BVCP version were collected from the City of Boulder's comprehensive-planning archive, scanned-document holdings, and adjacent municipal archives. They were converted to Markdown via Datalab and other PDF-to-Markdown tools, then placed in `corpus/`. The committed Markdown files are the canonical inputs to both notebooks; the source PDFs are not committed (they are large and reproducible from the Markdown plus the public archive).

## Notebooks
- `bvcp-corpus-analysis.ipynb` — four-movement computational reading: (1) vocabulary trajectories, modal-verb commitment vs. aspiration, and TF-IDF distinctiveness; (2) document architecture, section inventories, and policy-numbering density; (3) sentence-level carryover and longest-surviving passages; (4) semantic drift via TF-IDF cosine similarity, NMF topic structure, and section-level theme drift.
- `bvcp-embeddings.ipynb` — companion analysis using Voyage-4-large document embeddings with token-weighted mean pooling: pairwise cosine similarity, dimensionality reduction (PCA, MDS), hierarchical clustering by era, and drift from the 1977 baseline.

## Key findings
- Sentence carryover between consecutive major BVCP updates averages roughly 30%; the 2015 → 2026 draft transition is the most heavily rewritten in the corpus.
- The 2026 draft is the most semantically distant version from every earlier plan, in both TF-IDF and embedding space — the draft is not a marginal revision of 2021.
- Vocabulary trajectories show "sustainability," "resilience," and "equity" emerging in the 2001–2010 era and intensifying through 2026; "growth management" and "carrying capacity" appear most dense in the 1977–1986 era.
- Modal-verb analysis shows the ratio of directive ("shall," "must") to permissive ("may," "should") language shifts across eras, with implications for how each version functions as policy versus aspiration.
- Hierarchical clustering recovers five planning eras that align with the city's policy history: Founding (1977-79), Growth Management (1981-86), Maturation (1990-96), Modern (2001-10), Contemporary (2015+).

(Headline figures are pinned in the final cell of each notebook.)

## Limitations
- The Markdown corpus is derived from PDFs by OCR/conversion; some artifacts (hyphenation, table rendering, footer text) survive and can affect the lower decimal places of similarity scores.
- TF-IDF and modal-verb analyses operate on surface tokens; semantic synonymy across versions is captured by the embeddings notebook but not by the corpus-analysis notebook.
- Era labels are post-hoc descriptive groupings, not formal cluster solutions; the clustering recovers them but the boundaries are interpretive.
- The 2026 draft is a working document; final similarity to the adopted version will differ.

## Column
*BVCP corpus analysis piece — academic/longer-form treatment; URL TBD once published.*
