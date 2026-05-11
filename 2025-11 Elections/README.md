# 2025-11 Elections

## Question
What do the unfolding vote-share dynamics across update timestamps during the 2025 Boulder municipal election tell us about how progressives and conservatives are distributed across mail-in versus in-person ballots — and how predictable are final shares from early returns?

## Decision peg
The 2025 Boulder City Council and Ballot Issue 2A election; the durable question of how the order of ballot-counting (early mail, day-of, late mail, military/overseas) shapes which candidates appear to be leading or trailing during election week.

## Data
| Dataset | Source | Access | File |
|---|---|---|---|
| 2025 City Council results by update timestamp | [Boulder County election-results portal](https://electionresults.bouldercounty.gov/) | Manually entered committed CSV | `results_2025_council.csv` |
| 2025 Ballot Issue 2A results by update timestamp | [Boulder County election-results portal](https://electionresults.bouldercounty.gov/) | Manually entered committed CSV | `results_2025_2a.csv` |

## Notebooks
- `Vote_Share_Forecasting.ipynb` — vote shares by candidate across each county update, a linear-regression forecast of final share from early returns, and a cumulative-error trajectory for the top-six finishers.

## Key findings
- Final vote shares are well-predicted by early returns through a simple linear model, with mean absolute forecast error in the single-digit percentage range.
- The vote-share trajectory shifts systematically as later batches of ballots are counted, consistent with later ballots leaning more progressive than earlier mail-in returns.
- The largest forecast errors concentrate in the middle of the candidate field, where small absolute changes translate to relatively large share movements.

(Headline figures are pinned in the final cell of the notebook.)

## Limitations
- Returns were manually transcribed from the county portal at each observed update; transcription error is possible but small relative to total vote counts.
- The single-cycle dataset means the model cannot be cross-validated against earlier elections; a CORA request for prior-cycle reports would extend the analysis.
- "Progressive vs. conservative" is inferred from candidate slates and endorsements rather than a formal scoring; readers should treat the framing as descriptive of the 2025 contest, not as a generalizable spatial model.

## Column
[*What Boulder's 2025 election results reveal about how we vote — and why progressives keep coming from behind*](https://boulderreportinglab.org/2025/11/09/brian-keegan-what-boulders-2025-election-results-reveal-about-how-we-vote-and-why-progressives-keep-coming-from-behind/) — published 2025-11-10.
