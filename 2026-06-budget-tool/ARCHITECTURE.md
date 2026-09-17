# Balance Boulder's Budget — data architecture

How a reader's budget gets from the widget to a database, how it stays
anonymous, and how it comes back out for analysis. This is the document the
widget's comments point to.

The whole pipeline lives in [`pipeline/`](./pipeline/): the Supabase schema and a
one-file export script. The widget is
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
                                          │  publishable key — browser-safe, RLS: insert-only
                                          │  POST /rest/v1/contributions          (write)
                                          │  POST /rest/v1/rpc/budget_aggregate    (anonymous tally)
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

The browser writes straight to Supabase with the browser-safe publishable key;
Row Level Security is the boundary that keeps that key from reading anything
back. The static HTML is served by GitHub Pages — there is no backend to host.

---

## Two runtime modes

The widget picks a backend at load time (see the `BACKEND CONFIG` block in the
JSX):

| Mode | When | Reads / writes |
| --- | --- | --- |
| **Supabase direct** | default — `SUPABASE_URL` + publishable `SUPABASE_KEY` are baked in | PostgREST insert + `budget_aggregate` RPC |
| **Preview** | offline/standalone build sets `window.__BBW_PREVIEW__` | in-memory only; nothing leaves the browser |

In direct mode the on-load tally is read with `budget_aggregate()`, and each
submission is an insert; right after a submit the tally is re-read so the reader
immediately sees their own contribution counted. Preview mode is what the
double-click review build uses, so a local copy never touches the live database.

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
- **The secret key never reaches the browser.** It lives only on trusted machines
  running the export, and is never committed.

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
| `gf_police` … `gf_other` | int | 11 General Fund sliders, % change, −25..25 |
| `fund_capital` … `fund_airport` | int | 17 locked-fund sliders, % change, −25..25 |
| `rev_fees` | int | fees & charges, % change of GF revenue, −25..25 |
| `rev_property` | int | property tax, % change of GF revenue, −25..25 |
| `rev_sales` | int | sales & use tax, % change of GF revenue, −25..25 |
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

The full slider list lives in two places that must stay in lockstep: the
widget's `GF_DEPTS` / `LOCKED_FUNDS` / `DEMO` tables and the notebook's canonical
column lists. If you add or rename a department, update both (and add the column
in `pipeline/supabase/schema.sql`).

A second one-row table, `contribution_stats`, holds the precomputed public tally
(the `{ n, usedRevenue, … }` object). A trigger on `contributions` refreshes it
on every insert/update/delete, and `budget_aggregate()` simply reads it — so the
public aggregate never needs a privileged function over the raw rows.

`budget_aggregate()` returns the anonymous tally, exactly the shape the widget
renders:

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
show the average revenue share.

---

## Setup

### 1. Supabase (once)
Open the project's **SQL Editor → New query**, paste
[`pipeline/supabase/schema.sql`](./pipeline/supabase/schema.sql), and **Run**.
This creates the table, RLS policies, the insert trigger, and
`budget_aggregate()`. Re-running is safe. Find the keys under **Project Settings
→ API keys** (publishable = browser; secret = server).

### 2. Build the widget
The project URL and the **publishable** key are baked into the JSX
(`SUPABASE_URL` / `SUPABASE_KEY`). Once the schema is live, the widget stores
submissions directly. Build the self-contained production HTML with:

```bash
BBW_PREVIEW=0 ./build-standalone.sh
```

To rotate the key later, edit those two constants and rebuild.

### 3. Deploy to GitHub Pages
[`.github/workflows/deploy-widget.yml`](../.github/workflows/deploy-widget.yml)
publishes the built `boulder-budget-widget.html` to GitHub Pages on every push
that touches it (serving the widget at `/boulder-budget-2026/`, with the repo
root redirecting there). One-time setup: in the repo's **Settings → Pages**, set
**Source** to **GitHub Actions**, then re-run the workflow.

---

## Newspack embedding

Host `boulder-budget-widget.html` (build it with
[`build-standalone.sh`](./build-standalone.sh)), then paste this into a Newspack
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

The security boundary is Row Level Security: the publishable key is insert-only
and can never read a row back, so baking it into the page is safe by design. If
scripted spam ever appears, put a WAF/rate-limit rule in front of the Pages site
(e.g. Cloudflare) or tighten the insert policy — without changing the widget.

A note on logs: even with no IP stored, Supabase keeps request IPs in its own
platform logs transiently. Minimize log retention and reflect that in the
reader-facing privacy note if you promise "we never keep your IP."

---

## Analysis loop

When you're ready to analyze real responses instead of the notebook's synthetic
sample:

```bash
cd pipeline
export SUPABASE_URL=https://iplcjxbazezpjdzdpjxx.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_…      # trusted machine only
python3 export-responses.py ../responses.csv
```

Then set `STUB_MODE = False` in `budget-survey-analysis.ipynb` (it reads
`responses.csv`). The export's columns and order already match the notebook's
schema and its integrity checks.
