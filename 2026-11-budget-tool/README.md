# 2026-11-budget-tool

## Question
Boulder's 2027 budget has to close a General Fund gap. If readers had to close it themselves, where would they cut and what would they raise, and do their choices differ by who they are? And how did the city get to this budget? What has it spent, on what, and with how many staff, over the twenty-odd years before it?

## Decision peg
The City of Boulder's 2027 budget. The city manager released the recommended budget on August 28, 2026. It closes a $6.3 million General Fund gap. City Council's first reading is October 1, 2026 and its final vote October 15, 2026.

## Layout
```
2026-11-budget-tool/
├── README.md                     this file
├── ARCHITECTURE.md               how a reader's budget gets from the interactive to a database and back
│                                 out for analysis, and how it stays anonymous
├── embed/                        the published interactive: the self-contained iframe page, the same
│                                 widget as a Web Component, the Newspack publishing guide, and the
│                                 source they are built from (src/)
├── pipeline/                     the Supabase schema and migrations the interactive writes to, the
│                                 script that exports responses, and the one that builds the public file
├── data/                         the public, de-identified responses the column analyzed (CC BY 4.0),
│                                 with their data dictionary
└── budget-survey-analysis.ipynb  who responded, how they closed the gap, and how far their choices
                                  can be read as the city's; runs on data/ as committed
```

Each directory has its own README.

**The full responses are never committed.** [`data/budget-survey-public.csv`](data/) is the published version: the 216 budgets with five of the 14 survey answers, and no times or database ids. Its README says what it leaves out and why. The private export, with every answer and time, and the notebook's analysis frame stay out of the repository, and its `.gitignore` keeps them out wherever they are written.
