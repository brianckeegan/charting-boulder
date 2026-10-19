# pipeline

The data plumbing behind the Balance Boulder's Budget widget: the Supabase
schema the widget writes to, a one-file script that exports responses for
analysis, and one that builds the public, de-identified file from that export. Full design, data dictionary, and privacy model are in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).

```
pipeline/
├── supabase/schema.sql     run once in the Supabase SQL Editor
├── supabase/migrations/    dated changes to the live table, with runbooks
├── export-responses.py     Supabase → responses.csv for the notebook
├── make-public-data.py     responses.csv → ../data/budget-survey-public.csv, de-identified
└── .env.example            env vars to copy for the export
```

## How it runs

There is no server. The published widget (static HTML on GitHub Pages) writes
each submission **straight to Supabase** with the browser-safe publishable key,
and reads the anonymous tally back through `budget_aggregate()`. Row Level
Security is the boundary: that key can insert a row but can never read one back.

1. **Apply the schema.** Open the Supabase project's **SQL Editor → New query**,
   paste [`supabase/schema.sql`](./supabase/schema.sql), and **Run**. It creates
   the `contributions` table, the insert-only RLS policy, the stats trigger, and
   `budget_aggregate()`. Re-running is safe. It always shows the table's end
   state; the live table is changed with the dated files in
   [`supabase/migrations/`](./supabase/migrations/), each with its steps.
2. **Build & deploy the widget.** The project URL and publishable key are baked
   into the widget. `BBW_PREVIEW=0 ./build-standalone.sh`, run in
   `../embed/src/`, produces the production HTML, and the GitHub Pages
   workflow serves it. A widget change that sends new fields needs its
   migration run on the live table before it merges — see
   [`RUNBOOK-2027-sliders.md`](./supabase/migrations/RUNBOOK-2027-sliders.md)
   and [`../ARCHITECTURE.md`](../ARCHITECTURE.md) → *Setup*.

## Exporting responses for analysis

Reading individual rows needs the SECRET key (the publishable key is insert-only
under RLS), so it runs only on a trusted machine — never in the browser.

```bash
cd 2026-11-budget-tool/pipeline
export SUPABASE_URL=https://iplcjxbazezpjdzdpjxx.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_…       # trusted machine only; never commit
python3 export-responses.py ../responses.csv
```

The notebook, `../budget-survey-analysis.ipynb`, runs on the public file by
default. Set its `RESPONSES_CSV = 'responses.csv'` to run on this export, or on
the Supabase dashboard's CSV export of the `contributions` table, renamed
`responses.csv`. Never commit either.

## Building the public file

```bash
python3 make-public-data.py ../responses.csv     # writes ../data/budget-survey-public.csv
```

It keeps the budgets the notebook analyzes, every slider and the five survey
answers the column analyzed, and drops times, ids, the raw payload and the other
nine survey items. [`../data/README.md`](../data/README.md) explains each choice.
It needs no key and no third-party packages.

## Environment variables

| Var | Notes |
| --- | --- |
| `SUPABASE_URL` | the project URL |
| `SUPABASE_SECRET_KEY` | `sb_secret_…`; bypasses RLS; export only; **never commit** |

See [`.env.example`](./.env.example) for a template.
