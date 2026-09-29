# Runbook — the 2027 sliders

Step-by-step for moving the live Supabase table from the 2026 widget to the
2027 one. There are two SQL files, run on either side of merging the widget's
pull request, plus a test in between. Allow ten minutes for the whole thing.

**You run this. No credential goes anywhere near the build tooling.**

---

## What changes

The 2027 widget (payload `v` = 5) closes one gap, the 2027 General Fund's
$6.3M. It drops the one-time reserves slider, adds two revenue levers, and
rebuilds the locked section by department. In the table:

| | Columns |
|---|---|
| **Added** (phase 1) | `rev_marijuana` (the marijuana tax rate, 0–10%), `rev_shift` ($M of costs moved onto dedicated funds, 0–5), `used_shift`, and `fund_utilities`, `fund_hhs`, `fund_parksrec`, `fund_facilities`, `fund_manager`, `fund_fire`, `fund_other` |
| **Kept, same meaning** | every `gf_*`, `rev_fees`, `rev_property`, `rev_sales`, `spend_change`, `revenue_only`, `used_vote`, `used_revenue`, `top_cut`, every `demo_*` |
| **Kept, new meaning** | `fund_transpo`, `fund_openspace`, `fund_pds`, `fund_climate`: now that department's spending outside the General Fund, like the other seven `fund_*` columns |
| **Dropped** (phase 2) | `reserves`, `revenue_total`, `used_reserves`, and `fund_capital`, `fund_water`, `fund_wastewater`, `fund_internal`, `fund_stormwater`, `fund_parkstax`, `fund_ahf`, `fund_recact`, `fund_ssb`, `fund_ccrs`, `fund_arts`, `fund_evict`, `fund_airport` |

The public tally (`budget_aggregate()`) gains `usedShift` and loses
`usedReserves`. Its revenue share now counts costs moved onto dedicated funds
alongside cuts. The department names are unchanged, so the `top_cut`
allowlist, the insert policy and the rate limiter are untouched.

## Why two phases

GitHub Pages publishes the widget the moment the pull request merges. The 2027
widget writes columns the table doesn't have yet, and the 2026 widget writes
columns the 2027 table no longer has. So:

1. **Phase 1 adds** the new columns while the 2026 widget is still live. Both
   widgets can save.
2. **Merge.** The 2027 widget goes live and saves into the new columns.
3. **Phase 2 removes** what only the 2026 widget used, along with its test
   rows.

**Don't merge before phase 1.** Until phase 1 runs, every 2027 submission
fails.

---

## Step 1 — Look at what's in the table

In the dashboard for project `iplcjxbazezpjdzdpjxx`: **SQL Editor → New
query**, then run:

```sql
select client_version, count(*) as rows, min(created_at), max(created_at)
  from public.contributions
 group by 1 order by 1;
```

Expect only 2026-widget test rows (`client_version` 4). Phase 2 deletes every
one of them. If you want a copy first, use **Table Editor → contributions →
Export → CSV**.

## Step 2 — Run phase 1 (add)

1. Open `2026-09-29-2027-sliders-1-add.sql` (next to this file) and copy all of it.
2. Paste it into a new query and click **Run**.

**Expected:** `Success. No rows returned.` Two `NOTICE: constraint ... does not
exist, skipping` lines are normal on a first run.

**If you see an error,** nothing was applied, because the script runs in one
transaction. Stop, and send the error text.

Check it took:

**a) The tally has the new key.** Expect your row count as `n`, and a `"usedShift": 0` entry.

```sql
select public.budget_aggregate();
```

**b) The ten new columns exist.** Expect 10 rows.

```sql
select column_name from information_schema.columns
 where table_schema = 'public' and table_name = 'contributions'
   and column_name in ('rev_marijuana','rev_shift','used_shift','fund_utilities',
       'fund_hhs','fund_parksrec','fund_facilities','fund_manager','fund_fire','fund_other');
```

**c) An impossible value is rejected.** This should **fail**, and failing is the success condition:

```sql
insert into public.contributions (client_version, rev_shift, demo_age)
values (5, 6, '35-44');
```

Expect: `violates check constraint "rev_levers_in_range"`.

## Step 3 — Merge the pull request

Merge the widget PR. The **Deploy widget to GitHub Pages** workflow publishes
`embed/index.html` within a few minutes. Check it in the repository's
**Actions** tab.

If the interactive was already uploaded to Newspack as an Iframe Block ZIP,
that copy is still the 2026 widget. Rebuild the ZIP and upload it again:

```
cd 2026-11-budget-tool/embed
zip boulder-budget-interactive.zip index.html
```

## Step 4 — Submit one budget from the live widget

Open <https://brianckeegan.github.io/charting-boulder/boulder-budget-2026/>
and hard-refresh (Shift-reload) so you don't get the cached 2026 page.

1. Check the title reads **Balance Boulder's 2027 budget**.
2. Close the gap. For example: Police −10%, the marijuana tax to 5.5%, and
   $0.5M shifted onto dedicated funds.
3. Answer one survey question and click **Add my budget**.

It should say "Your budget is saved." Then in the SQL editor:

```sql
select created_at, client_version, rev_marijuana, rev_shift, used_shift,
       gf_police, fund_utilities, top_cut
  from public.contributions
 order by created_at desc limit 3;
```

Expect your row on top: `client_version` 5, `rev_marijuana` 5.5, `rev_shift`
0.5, `used_shift` true.

## Step 5 — Run phase 2 (drop)

Only after step 4 shows a version-5 row.

1. Open `2026-09-29-2027-sliders-2-drop.sql`, copy all of it, paste it into a
   new query, and click **Run**.

**Expected:** `Success. No rows returned.`

Check it took:

**a) Only 2027 rows remain.** Expect one row, `5`.

```sql
select client_version, count(*) from public.contributions group by 1;
```

**b) `usedReserves` is gone from the tally.**

```sql
select public.budget_aggregate();
```

**c) Every guard is validated.** Expect zero rows.

```sql
select conname from pg_constraint
 where conrelid = 'public.contributions'::regclass and not convalidated;
```

## Step 6 (optional) — Start the count from zero before launch

Your step-4 test row is still in the table and in the public tally. To launch
with an empty tally:

```sql
delete from public.contributions;
select public.budget_aggregate();   -- expect "n": 0
```

Use `delete`, not `truncate`. The tally is refreshed by a trigger that fires
on insert, update and delete, and `truncate` would leave it showing the old
count.

---

## If something goes wrong

**After phase 1 only.** Phase 1 added columns and constraints and changed no
data. To undo it, run this, then re-run the previous `schema.sql` from git
history, which restores the 2026 tally function:

```sql
begin;
alter table public.contributions
  drop constraint if exists rev_levers_in_range,
  drop constraint if exists locked_in_range,
  drop column if exists rev_marijuana, drop column if exists rev_shift,
  drop column if exists used_shift,   drop column if exists fund_utilities,
  drop column if exists fund_hhs,     drop column if exists fund_parksrec,
  drop column if exists fund_facilities, drop column if exists fund_manager,
  drop column if exists fund_fire,    drop column if exists fund_other;
commit;
```

```
git show 196edff:2026-11-budget-tool/pipeline/supabase/schema.sql
```

**After phase 2.** Phase 2 deleted the 2026 test rows and dropped their
columns. Only a copy (step 1) or a Supabase backup can restore them. The
2026 widget can't save against this table any more, so roll back by
re-publishing it together with the 2026 schema, not by re-running a migration.

**Don't re-run phase 1 after phase 2.** Its tally still counts `used_reserves`,
which phase 2 removed, so it stops with an error and applies nothing.

---

## How this was tested

Both phases were run against a scratch PostgreSQL 16 database. It was loaded
with the pre-2027 `schema.sql`, the `anon` and `authenticated` roles, and four
2026-widget rows inserted as `anon` through the insert policy and rate
limiter. Results:

- **Phase 1** applied cleanly, and the tally gained `usedShift`.
- **Both widgets could save after phase 1.**
  - A 2026-style row still saved.
  - The 2027 widget's exact insert saved as `anon`. The body was captured from
    the built widget in a headless browser, with the Supabase request
    intercepted.
- **Three out-of-range rows were rejected:** a $6M shift, a 12% marijuana
  rate, and a +40% locked slider.
- **Phase 2** deleted the four 2026 rows and kept the 2027 row.
  - It dropped sixteen columns and removed `usedReserves` from the tally.
  - The tally's revenue share matched the widget's own figure: 0.41 ÷ 6.33 =
    0.065.
  - It validated every constraint.
  - Running it a second time changed nothing.
- **After phase 2, a 2026-style insert failed,** as it should.

A fresh database built from the new `schema.sql` then matched the migrated
one in columns, constraints, functions, defaults, triggers and policies. The
one difference is expected: the fresh install leaves its two security guards
`NOT VALID`, as that file always has, where phase 2 validates them.
