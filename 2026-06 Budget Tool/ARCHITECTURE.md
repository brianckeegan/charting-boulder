# Balance Boulder's Budget — data architecture

How a reader's budget gets from the widget to a database, how it stays
anonymous, and how it comes back out for analysis. This is the document the
widget's comments point to.

The whole pipeline lives in [`pipeline/`](./pipeline/): the Supabase schema, a
small Vercel API, and a one-file export script. The widget is
[`boulder-budget-widget.jsx`](./boulder-budget-widget.jsx); the analysis is
[`Budget-Survey-Analysis.ipynb`](./Budget-Survey-Analysis.ipynb).

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
        │  Vercel functions  │  bypasses RLS, hashes IP for dedupe │ (browser-safe, RLS:
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
                                  pipeline/export_responses.py
                                          ▼
                                   responses.csv  ──►  Budget-Survey-Analysis.ipynb
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
| **Preview** | offline/standalone build sets `window.__BBW_PREVIEW__` | in-memory only; nothing leaves the browser |

Mode A wins if an endpoint is present; otherwise B; otherwise preview. Use **A**
when you want server-side de-duplication and the publishable key kept off the
page; **B** needs no server at all.

---

## Privacy & trust model

The widget tells readers their response is anonymous. Here is exactly what backs
that up:

- **No identifiers are stored.** No name, account, email, IP address, or browser
  fingerprint is written to a row. The only survey data is what the reader picks.
- **Duplicate flagging without retention.** When the Vercel path is used, the
  function computes `dedupe_hash = sha256(DEDUPE_SALT + IP + UTC-day)` and stores
  *only* that hash. It is salted and one-way, so it cannot be reversed to an IP,
  but repeat submissions from one address on one day collide — enough to screen
  duplicates, nothing more. The direct path stores no hash at all (a browser
  can't see its own public IP); it relies on the widget's `localStorage` flag.
- **Row Level Security is on.** The publishable key (role `anon`) may **insert**
  a row and nothing else — it cannot read, update, or delete any row, and inserts
  use `Prefer: return=minimal` so nothing is echoed back. A leaked publishable
  key can add data; it can never read data.
- **The only public window is the aggregate.** `budget_aggregate()` is
  `SECURITY DEFINER` and returns counts and sums only — never an individual row.
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
| `dedupe_hash` | text | salted one-way hash; no PII (Vercel path only) |
| `repeat_client` | bool | this browser had submitted before |
| `raw` | jsonb | the full original payload, as a safety net |

`"demo_workArea"` is stored with quotes to preserve its camelCase — every other
column is lowercase.

The full slider list lives in three places that must stay in lockstep: the
widget's `GF_DEPTS` / `LOCKED_FUNDS` / `DEMO` tables, `pipeline/api/_schema.js`,
and the notebook's canonical column lists. If you add or rename a department,
update all three (and add the column in `pipeline/supabase/schema.sql`).

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
[`pipeline/supabase/schema.sql`](./pipeline/supabase/schema.sql), and **Run**.
This creates the table, RLS policies, the insert trigger, and
`budget_aggregate()`. Re-running is safe. Find the keys under **Project Settings
→ API keys** (publishable = browser; secret = server).

### 2. Widget (direct mode — no server)
The project URL and the **publishable** key are baked into the JSX
(`SUPABASE_URL` / `SUPABASE_KEY`). Once the schema is live, the widget stores
submissions directly. To rotate the key later, edit those two constants and
rebuild.

### 3. Vercel (optional — proxy mode)
Deploy [`pipeline/`](./pipeline/) as its own Vercel project (set the project's
**Root Directory** to `2026-06 Budget Tool/pipeline`). Add env vars from
[`pipeline/.env.example`](./pipeline/.env.example):

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` — the `sb_secret_…` key (**never** committed)
- `DEDUPE_SALT` — any stable random string
- `ALLOWED_ORIGIN` — optional; e.g. `https://boulderreportinglab.org`

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

## Analysis loop

When you're ready to analyze real responses instead of the notebook's synthetic
sample:

```bash
cd "2026-06 Budget Tool/pipeline"
export SUPABASE_URL=https://dlnalnozxwrxiekhilqo.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_…      # trusted machine only
python3 export_responses.py ../responses.csv
```

Then set `STUB_MODE = False` in `Budget-Survey-Analysis.ipynb` (it reads
`responses.csv`). The export's columns and order already match the notebook's
schema and its integrity checks.
