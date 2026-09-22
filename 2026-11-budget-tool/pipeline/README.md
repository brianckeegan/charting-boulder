# pipeline

The data plumbing behind the Balance Boulder's Budget widget: the Supabase
schema the widget writes to, and a one-file script that exports responses for
analysis. Full design, data dictionary, and privacy model are in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).

```
pipeline/
├── supabase/schema.sql     run once in the Supabase SQL Editor
├── export-responses.py     Supabase → responses.csv for the notebook
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
   `budget_aggregate()`. Re-running is safe.
2. **Build & deploy the widget.** The project URL and publishable key are baked
   into the widget; `BBW_PREVIEW=0 ../build-standalone.sh` produces the
   production HTML, and the GitHub Pages workflow serves it. See
   [`../ARCHITECTURE.md`](../ARCHITECTURE.md) → *Setup*.

## Exporting responses for analysis

Reading individual rows needs the SECRET key (the publishable key is insert-only
under RLS), so it runs only on a trusted machine — never in the browser.

```bash
cd 2026-06-budget-tool/pipeline
export SUPABASE_URL=https://iplcjxbazezpjdzdpjxx.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_…       # trusted machine only; never commit
python3 export-responses.py ../responses.csv
```

Then set `STUB_MODE = False` in `../budget-survey-analysis.ipynb` (it reads
`responses.csv`). Columns and order already match the notebook's schema.

## Environment variables

| Var | Notes |
| --- | --- |
| `SUPABASE_URL` | the project URL |
| `SUPABASE_SECRET_KEY` | `sb_secret_…`; bypasses RLS; export only; **never commit** |

See [`.env.example`](./.env.example) for a template.
