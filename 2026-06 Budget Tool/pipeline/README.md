# Budget Tool pipeline

Writes reader "contributions" from the Balance Boulder's Budget widget to
Supabase, and serves the anonymous aggregate the widget shows. Full design,
data dictionary, and privacy model are in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

```
pipeline/
├── supabase/schema.sql     run once in the Supabase SQL Editor
├── api/
│   ├── submit.js           POST /api/submit   → store one contribution
│   ├── aggregate.js        GET  /api/aggregate → anonymous tally
│   ├── _schema.js          canonical columns + payload validation
│   └── _supabase.js        PostgREST + CORS + dedupe-hash helpers
├── export_responses.py     Supabase → responses.csv for the notebook
├── vercel.json             function config
├── package.json            no runtime dependencies
└── .env.example            env vars to copy
```

## Two ways to run it

**Direct (no server).** Run `supabase/schema.sql` and you're done — the widget
writes straight to Supabase with the browser-safe publishable key. Best when you
don't want to host anything.

**Vercel proxy (recommended for production).** Adds server-side validation and
privacy-preserving de-duplication, and keeps the secret key off the page.

```bash
# from this directory
cp .env.example .env.local        # fill in SUPABASE_SECRET_KEY + DEDUPE_SALT
npx vercel dev                    # local dev at http://localhost:3000
npx vercel deploy --prod          # ship it
```

Set the same env vars in the Vercel dashboard (Project → Settings → Environment
Variables), and set the project's **Root Directory** to
`2026-06 Budget Tool/pipeline`. Then point the widget at the deployment with
`?api=https://your-pipeline.vercel.app/api` on the embed URL.

## Environment variables

| Var | Where | Notes |
| --- | --- | --- |
| `SUPABASE_URL` | Vercel + export | the project URL |
| `SUPABASE_SECRET_KEY` | Vercel + export | `sb_secret_…`; bypasses RLS; **never commit** |
| `ALLOWED_ORIGIN` | Vercel | origin allowlist, e.g. `https://boulderreportinglab.org` |
| `TURNSTILE_SECRET` | Vercel (optional) | Cloudflare Turnstile secret — bot defense |
| `UPSTASH_REDIS_REST_URL` / `…_TOKEN` | Vercel (optional) | per-IP rate-limit store (ephemeral) |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` | Vercel (optional) | cap + window seconds (default 5 / 3600) |

Each defense activates only when its vars are set; the function runs fine
without them. See [`../ARCHITECTURE.md`](../ARCHITECTURE.md) → *Hardening* for the
production cutover.

## Quick checks

```bash
# aggregate (works as soon as the schema is applied)
curl https://your-pipeline.vercel.app/api/aggregate

# a minimal submission
curl -X POST https://your-pipeline.vercel.app/api/submit \
  -H 'Content-Type: application/json' \
  -d '{"v":4,"scenario":"dual","gf_police":-10,"demo_age":"35-44"}'
```

The publishable key is insert-only under Row Level Security, so it can add a row
but can never read one back; reading rows for analysis uses the secret key via
`export_responses.py`. See [`../ARCHITECTURE.md`](../ARCHITECTURE.md).
