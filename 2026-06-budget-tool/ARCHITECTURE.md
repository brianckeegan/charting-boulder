# Balance Boulder's Budget — data architecture

How a reader's budget gets from the widget to a database, how it stays
anonymous, and how it comes back out for analysis. This is the document the
widget's comments point to.

The whole pipeline lives in [`pipeline/`](../pipeline/): the Supabase schema, a
small Vercel API, and a one-file export script. The widget is
[`boulder-budget-widget.jsx`](./boulder-budget-widget.jsx); the analysis is
[`budget-survey-analysis.ipynb`](./budget-survey-analysis.ipynb).

---

## Data flow

```
                          ┌─────────────────────────────────────────┐
   reader in a Newspack   │  boulder-budget-widget  (React, in an    │
   article (iframe)       │  iframe; auto-resizes via postMessage)   │
                          └───────────────┬──────────────────────────┘
                                          │  one flat JSON record per submission
                  ┌───────────────────────┴───────────────────────┐
                  │                                                │
        (A) ENDPOINT set                                 (B) no ENDPOINT
        POST /api/submit                                 POST /rest/v1/contributions
        GET  /api/aggregate                              POST /rest/v1/rpc/budget_aggregate
                  │                                                │
        ┌─────────▼──────────┐  secret key (server-side)           │ publishable key
        │  Vercel functions  │  bypasses RLS, validates each write │ (browser-safe, RLS:
        │  pipeline/api/*    │                                     │  insert-only)
        └─────────┬──────────┘                                     │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                          ┌───────────────────────────────┐
                          │  Supabase Postgres            │
                          │  public.contributions  (rows) │
                          │  public.budget_aggregate()    │  ← anonymous tally only
                          └───────────────┬───────────────┘
                                          │  secret key, from a trusted machine
                                  pipeline/export-responses.py
                                          ▼
                                   responses.csv  ──►  budget-survey-analysis.ipynb
                                                       (STUB_MODE = False)
```

Both write paths land in the same table with the same column names, so analysis
doesn't care which one a reader used.

---

## Three runtime modes

The widget picks a backend at load time (see `resolveEndpoint()` and the
`BACKEND CONFIG` block in the JSX):

| Mode | When | Reads / writes |
| --- | --- | --- |
| **Vercel proxy** (A) | `?api=…` on the embed URL, or `window.__BBW_ENDPOINT__` | `GET …/api/aggregate`, `POST …/api/submit` |
| **Supabase direct** (B) | default — `SUPABASE_URL` + publishable `SUPABASE_KEY` are baked in | PostgREST insert + `budget_aggregate` RPC |
| **Cached read** (B+) | `?agg=…` or `window.__BBW_AGG__`, alongside B | tally **read** via the edge-cached `…/api/aggregate`; writes stay direct |
| **Preview** | offline/standalone build sets `window.__BBW_PREVIEW__` | in-memory only; nothing leaves the browser |

Precedence: a full `ENDPOINT` (A) wins; otherwise, on **load**, a cached `AGG`
read is used if set while writes go direct (B+); otherwise B; otherwise preview.
**A** keeps the secret key off the page and gives one server chokepoint; **B**
needs no server; **B+** absorbs traffic spikes by serving the tally from a CDN
while writes stay direct. After a submit the tally is re-read *fresh* (cache
bypassed), so the reader still sees their own contribution counted.

---

## Privacy & trust model

The widget tells readers their response is anonymous. Here is exactly what backs
that up:

- **No identifiers are stored.** No name, account, email, IP address, or browser
  fingerprint is written to a row. The only survey data is what the reader picks.
- **No IP-derived value is persisted.** There is no per-submission hash, no IP,
  and no browser fingerprint anywhere in the dataset.
- **Row Level Security is on.** The publishable key (role `anon`) may **insert**
  a row — and only one that carries at least one survey answer — and nothing
  else: it cannot read, update, or delete any row, and inserts use
  `Prefer: return=minimal` so nothing is echoed back. A leaked publishable key
  can add data; it can never read data.
- **The only public window is the aggregate.** The tally lives in a single
  precomputed `contribution_stats` row, refreshed by a trigger on every write.
  Readers reach it through `budget_aggregate()`, a `SECURITY INVOKER` function
  returning counts and sums only — never an individual row. (It reads the
  precomputed row rather than the table, so it needs no elevated privilege —
  which clears Supabase advisor lints 0028/0029.)
- **The secret key never reaches the browser.** It lives in Vercel env vars and
  on trusted machines running the export, and is never committed.

Publishable vs. secret, at a glance:

| Key | Format | Role | Bypasses RLS? | Safe in the browser / git? |
| --- | --- | --- | --- | --- |
| Publishable | `sb_publishable_…` | `anon` | No | **Yes** — designed to be public |
| Secret | `sb_secret_…` | `service_role` | Yes | **No** — server-side only |

---

## Data dictionary — `public.contributions`

One row per submission. Column names match the widget payload **and** the
notebook's `GF_SLIDERS / FUND_SLIDERS / REV_COLS / DEMO_COLS` one-to-one.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid | server-generated |
| `created_at` | timestamptz | server insert time, forced by a trigger |
| `client_ts` | timestamptz | widget payload `ts` (untrusted) |
| `client_version` | int | widget payload `v` (currently `4`) |
| `scenario` | text | `"dual"` (both 2026 + 2027 tests) |
| `gf_police` … `gf_planning` | int | 9 General Fund sliders, % change, −25..25 |
| `fund_capital` … `fund_airport` | int | 17 locked-fund sliders, % change, −25..25 |
| `rev_fees` | numeric | fees/fines, $M, ≥ 0 |
| `rev_property` | numeric | mill-levy increase, ≥ 0 |
| `rev_sales` | numeric | sales-tax increase, percentage points, ≥ 0 |
| `reserves` | numeric | one-time reserves, $M, ≥ 0 |
| `spend_change` | numeric | signed $M; + = more spending = wider gap |
| `revenue_total` | numeric | recurring revenue + reserves, $M |
| `revenue_only` | numeric | recurring revenue only, $M |
| `used_vote` | bool | a tax requiring a TABOR vote was used |
| `used_revenue` | bool | any new fee or tax was used |
| `used_reserves` | bool | reserves were spent down |
| `top_cut` | text | name of the reader's single deepest GF cut, or null |
| `demo_years` … `demo_disability` | text | 13 survey items; multi-selects joined by `"; "` |
| `repeat_client` | bool | this browser had submitted before |
| `raw` | jsonb | the full original payload, as a safety net |

`"demo_workArea"` is stored with quotes to preserve its camelCase — every other
column is lowercase.

The full slider list lives in three places that must stay in lockstep: the
widget's `GF_DEPTS` / `LOCKED_FUNDS` / `DEMO` tables, `pipeline/api/_schema.js`,
and the notebook's canonical column lists. If you add or rename a department,
update all three (and add the column in `pipeline/supabase/schema.sql`).

A second one-row table, `contribution_stats`, holds the precomputed public tally
(the `{ n, usedRevenue, … }` object). A trigger on `contributions` refreshes it
on every insert/update/delete, and `budget_aggregate()` simply reads it — so the
public aggregate never needs a privileged function over the raw rows.

---

## API contract (Vercel path)

### `POST /api/submit`
Body: the flat payload the widget builds (`v`, `ts`, `scenario`, every `gf_*` /
`fund_*` / `rev_*` / `reserves`, the derived totals, and every `demo_*`).
Returns `200` with the refreshed aggregate (below). At least one `demo_*` answer
is required (`422` otherwise). Unknown keys are ignored but preserved in `raw`.

### `GET /api/aggregate`
Returns the anonymous tally, exactly the shape the widget renders:

```json
{
  "n": 128,
  "usedRevenue": 110,
  "usedVote": 74,
  "usedReserves": 39,
  "revShareSum": 71.4,
  "cutTally": { "Police": 22, "General government & admin": 14 }
}
```

`revShareSum` is the sum over rows of `revenue_total / (revenue_total + net
cuts)`, where net cuts = `max(0, -spend_change)`; the widget divides by `n` to
show the average revenue share. CORS is open by default — set `ALLOWED_ORIGIN`
to lock it to your site.

---

## Setup

### 1. Supabase (once)
Open the project's **SQL Editor → New query**, paste
[`pipeline/supabase/schema.sql`](../pipeline/supabase/schema.sql), and **Run**.
This creates the table, RLS policies, the insert trigger, and
`budget_aggregate()`. Re-running is safe. Find the keys under **Project Settings
→ API keys** (publishable = browser; secret = server).

### 2. Widget (direct mode — no server)
The project URL and the **publishable** key are baked into the JSX
(`SUPABASE_URL` / `SUPABASE_KEY`). Once the schema is live, the widget stores
submissions directly. To rotate the key later, edit those two constants and
rebuild.

### 3. Vercel (optional — proxy mode)
Deploy [`pipeline/`](../pipeline/) as its own Vercel project (set the project's
**Root Directory** to `pipeline`). Add env vars from
[`pipeline/.env.example`](../pipeline/.env.example):

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` — the `sb_secret_…` key (**never** committed)
- `ALLOWED_ORIGIN` — origin allowlist, e.g. `https://boulderreportinglab.org`

Then point the widget at it with `?api=https://your-pipeline.vercel.app/api` on
the embed URL.

---

## Newspack embedding

Host `boulder-budget-widget.html` (build it with
[`pipeline`’s sibling](./build-standalone.sh)), then paste this into a Newspack
**Custom HTML** block. The script makes the iframe grow to the widget's height
using the `boulder-budget:height` message the widget already posts:

```html
<iframe id="bbw"
        src="https://YOUR-HOST/boulder-budget-widget.html"
        title="Balance Boulder's Budget"
        loading="lazy" scrolling="no"
        sandbox="allow-scripts allow-same-origin allow-popups"
        referrerpolicy="no-referrer"
        style="width:100%;border:0;display:block"></iframe>
<script>
  addEventListener("message", function (e) {
    if (e && e.data && e.data.type === "boulder-budget:height") {
      var f = document.getElementById("bbw");
      if (f) f.style.height = e.data.height + "px";
    }
  });
</script>
```

To route writes through the Vercel pipeline instead of writing to Supabase
directly, add `?api=https://your-pipeline.vercel.app/api` to the iframe `src`.

---

## Hardening & going to production

Already enforced on `iplcjxbazezpjdzdpjxx` (DB + project):

- **RLS, insert-only** — the publishable key can insert a row (only with ≥1
  survey answer) and read only the aggregate; never read/update/delete a row.
- **Server-owned columns** — a trigger forces `id` and `created_at`, so a public
  client can't choose an id or backdate a row.
- **Value bounds** — `contributions_sane_values` rejects absurd/oversized data.
- **No IP-derived value stored** — the old `dedupe_hash` column is gone.
- **Aggregate via a precomputed row**, read by a `SECURITY INVOKER` function;
  the Security Advisor shows **0** warnings.
- **Reduced surface** — Auth sign-ups disabled, GraphQL API unexposed, Realtime
  publication empty, no storage buckets, `max_rows` = 1000.

Recommended next layer — **route writes through the Vercel pipeline** so the
secret key stays off the page and every write goes through one server chokepoint
(CORS allowlist + validation):

1. **Deploy** `pipeline/` to Vercel; set `SUPABASE_SECRET_KEY` and `ALLOWED_ORIGIN`.
2. **Rebuild** the embed pointed at it (or pass `?api=…` on the iframe src):
   ```bash
   BBW_PREVIEW=0 BBW_ENDPOINT=https://your-pipeline.vercel.app/api ./build-standalone.sh
   ```
   The widget then posts to `/api/submit`, which writes with the secret key.
3. **Cut over** last — once the Vercel path works, close the direct write path so
   every write goes through that chokepoint:
   ```sql
   drop policy if exists "anon may insert a contribution" on public.contributions;
   revoke insert on public.contributions from anon, authenticated;
   ```
   Reads (the public `contribution_stats`) stay open; only writes lock to the
   secret key. Running this *before* the Vercel path is live would break the
   widget, so it's the final step — until then the direct path keeps working.

If scripted spam ever appears, add rate-limiting at the edge (e.g. Vercel's
firewall) without touching the function.

A note on logs: even with no IP stored, Supabase and Vercel keep request IPs in
their own platform logs transiently. Minimize log retention and reflect that in
the reader-facing privacy note if you promise "we never keep your IP."

---

## Analysis loop

When you're ready to analyze real responses instead of the notebook's synthetic
sample:

```bash
cd "pipeline"
export SUPABASE_URL=https://iplcjxbazezpjdzdpjxx.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_…      # trusted machine only
python3 export-responses.py ../responses.csv
```

Then set `STUB_MODE = False` in `budget-survey-analysis.ipynb` (it reads
`responses.csv`). The export's columns and order already match the notebook's
schema and its integrity checks.
