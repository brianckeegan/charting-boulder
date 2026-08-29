# Runbook — applying `2026-08-29-security-hardening.sql`

Step-by-step for running the security migration against the live Supabase
project. Takes about five minutes.

**You run this; no credential goes anywhere near the build tooling.**

---

## What it changes

| # | Fix | Effect |
|---|---|---|
| 1 | `top_cut` allowlist + read-time filter | Only real department names can be stored, and only allowlisted names are ever counted into the public tally |
| 2 | `demo_*` length caps | A submission can no longer carry megabytes of payload |
| 3 | Per-IP rate limit | Max 20 submissions per IP per 10 minutes (tunable) |

It does **not** change any existing row, and it does **not** change the widget.

---

## Before you start

- You need access to the Supabase dashboard for the project
  (`iplcjxbazezpjdzdpjxx`) with permission to run SQL.
- Nothing needs to be taken offline. The migration runs in a transaction and
  takes well under a second on a table of this size.

---

## Step 1 — Open the SQL editor

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) and open the
   project.
2. In the left sidebar choose **SQL Editor**.
3. Click **New query**.

## Step 2 — Paste and run

1. Open `2026-08-29-security-hardening.sql` (next to this file) and copy its
   **entire** contents.
2. Paste into the editor.
3. Click **Run** (or press ⌘/Ctrl + Enter).

**Expected result:** `Success. No rows returned.`

You may also see `NOTICE: ... does not exist, skipping` lines. Those are normal
on a first run — the script drops things before recreating them so it can be run
twice safely.

**If you see an error,** nothing has been applied: the whole script runs inside a
transaction, so any failure rolls the entire thing back. Send the error text and
stop here.

## Step 3 — Verify it took

Run each of these in a new query and check the result.

**a) The allowlist exists and has 11 departments**

```sql
select array_length(public.bbw_gf_departments(), 1) as departments;
```
Expect: `11`

**b) Defacement is now blocked** — this should FAIL, and failing is the success
condition:

```sql
insert into public.contributions (demo_age, top_cut)
values ('35-44', 'THIS SHOULD BE REJECTED');
```
Expect: `new row for relation "contributions" violates check constraint
"top_cut_known_department"`

**c) Oversized payloads are blocked** — this should also FAIL:

```sql
insert into public.contributions (demo_tenure) values (repeat('z', 100000));
```
Expect: `... violates check constraint "demo_len_bounded"`

**d) A genuine submission still works** — this should SUCCEED:

```sql
insert into public.contributions (demo_age, demo_tenure, top_cut)
values ('35-44', 'Rent', 'Police');
```
Expect: `INSERT 0 1`

Then remove that test row:

```sql
delete from public.contributions
 where demo_age = '35-44' and demo_tenure = 'Rent' and top_cut = 'Police'
   and created_at > now() - interval '10 minutes';
```

**e) The rate limit is configured**

```sql
select max_per_window, window_minutes from public.rate_limit_config;
```
Expect: `20 | 10`

## Step 4 — Check the live widget still works

Open the published interactive, move a slider, answer one survey question and
submit. It should save normally and the tally should tick up.

> The rate limiter allows 20 submissions per IP per 10 minutes, so ordinary
> testing will not trip it.

---

## Afterwards

### Look for junk already in the table

```sql
select top_cut, count(*)
  from public.contributions
 where top_cut is not null
   and top_cut <> all (public.bbw_gf_departments())
 group by top_cut
 order by 2 desc;
```

Zero rows is the healthy answer. Anything listed is **already excluded from the
public tally** by the read-time filter, but it is still sitting in the table and
will show up in the analysis notebook — worth deleting if you find any.

### Promote the constraints to fully validated

The constraints were added `NOT VALID`, meaning they enforce on all new rows but
were never checked against existing ones. Once the query above returns nothing:

```sql
alter table public.contributions validate constraint top_cut_known_department;
alter table public.contributions validate constraint demo_len_bounded;
```

### Tune the rate limit

If legitimate readers are ever blocked — most likely a shared campus or office
address — raise the ceiling:

```sql
update public.rate_limit_config
   set max_per_window = 40, window_minutes = 10
 where id = 1;
```

To see whether anyone is actually hitting it:

```sql
select count(*) as inserts_last_hour,
       count(distinct ip_hash) as distinct_networks
  from public.insert_audit
 where created_at > now() - interval '1 hour';
```

---

## Rolling back

If something goes wrong, this undoes the migration completely:

```sql
begin;
drop trigger if exists contributions_rate_limit on public.contributions;
drop function if exists public.contributions_rate_limit();
alter table public.contributions drop constraint if exists top_cut_known_department;
alter table public.contributions drop constraint if exists demo_len_bounded;
commit;
```

That leaves the allowlist function and the read-time filter in place (both
harmless on their own). To also revert the tally filter, re-run the
`refresh_contribution_stats()` definition from `../schema.sql` as it stood before
this change — it is in git history.

The `rate_limit_config` and `insert_audit` tables can be dropped too, though
leaving them costs nothing:

```sql
drop table if exists public.insert_audit;
drop table if exists public.rate_limit_config;
```

---

## A note on privacy

The rate limiter never stores a reader's IP address. It stores a SHA-256 hash of
the address combined with a random per-project salt, in a table that the public
key cannot read (privileges revoked, row-level security on with no policies).
The hashes cannot be reversed to addresses, and rows older than two days are
pruned automatically.

---

## How this was tested

The migration was run against a scratch PostgreSQL 16 database before being
handed over, verifying: it applies cleanly and is safe to run twice; a
defacement string is rejected while a real department name is accepted; a
194-character multi-select race answer (the legitimate maximum) is accepted
while 500-character and 1 MB payloads are rejected; 50 pre-existing junk rows
stay out of the public tally; the rate limiter blocks the 4th insert from one IP
when the ceiling is 3 while a different IP is unaffected; and no raw IP is ever
written to the audit table. `schema.sql` was then rebuilt from scratch on a
second database to confirm it matches what this migration produces.
