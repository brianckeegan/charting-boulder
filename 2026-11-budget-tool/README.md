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
│                                 widget as a Web Component, and the Newspack publishing guide
├── pipeline/                     the Supabase schema and migrations the interactive writes to, and the
│                                 script that exports responses for the notebook
├── budget-survey-analysis.ipynb  who responded, how they closed the gap, and how far their choices
│                                 can be read as the city's
└── budget-history/               Boulder's budget 2002-2027 from the city's own documents: the dataset,
                                  its data dictionary, and the four scripts that build it
```

Each directory has its own README. [`budget-history/`](budget-history/) is the historical dataset and can be used without the rest.

**Reader responses are never committed.** The survey export and the notebook's analysis frame hold individual (if anonymous) submissions, and the repository's `.gitignore` keeps both out wherever they are written.
