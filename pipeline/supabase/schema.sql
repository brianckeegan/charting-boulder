-- ============================================================================
-- Balance Boulder's Budget — Supabase schema
-- ============================================================================
-- Destination for reader "contributions" from the budget widget
-- (boulder-budget-widget.jsx). Run this once against the project at
-- https://iplcjxbazezpjdzdpjxx.supabase.co using the SQL Editor
-- (Dashboard → SQL → New query → paste → Run), or via the Supabase CLI:
--
--     supabase db execute --file pipeline/supabase/schema.sql
--
-- Re-running is safe: every statement is idempotent (IF NOT EXISTS / OR REPLACE).
--
-- WHAT THIS STORES — one flat row per submission. Column names match the
-- widget payload and the analysis notebook (budget-survey-analysis.ipynb)
-- ONE-TO-ONE, so a CSV export drops straight into the notebook. See
-- ../../2026-06-budget-tool/ARCHITECTURE.md for the full data dictionary and the data flow.
--
-- PRIVACY — no name, account, email, IP address, or browser fingerprint is
-- stored, and NO IP-derived value is persisted at all: rate-limiting and
-- duplicate suppression happen in ephemeral edge storage (see the Vercel
-- function), so nothing here can be tied back to a person. Row Level Security
-- is ON: the publishable key may INSERT a contribution but can never read,
-- update, or delete a row. Readers see only the precomputed public tally in
-- `contribution_stats` (via budget_aggregate()); individual rows are reachable
-- only with the service-role key, server-side.
-- ============================================================================

-- gen_random_uuid() lives in pgcrypto; present by default on Supabase.
create extension if not exists pgcrypto;

create table if not exists public.contributions (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),  -- server insert time
  client_ts       timestamptz,                         -- widget payload `ts`
  client_version  integer,                             -- widget payload `v` (4)
  scenario        text,                                -- "dual"

  -- General Fund sliders (% change, −25..25). See GF_DEPTS in the widget.
  gf_police       integer,
  gf_fire         integer,
  gf_genadmin     integer,
  gf_transfers    integer,
  gf_parksrec     integer,
  gf_hhs          integer,
  gf_library      integer,
  gf_facilities   integer,
  gf_planning     integer,

  -- Locked / dedicated fund sliders (% change, −25..25). See LOCKED_FUNDS.
  fund_capital    integer,
  fund_water      integer,
  fund_openspace  integer,
  fund_transpo    integer,
  fund_wastewater integer,
  fund_internal   integer,
  fund_stormwater integer,
  fund_parkstax   integer,
  fund_ahf        integer,
  fund_recact     integer,
  fund_climate    integer,
  fund_pds        integer,
  fund_ssb        integer,
  fund_ccrs       integer,
  fund_arts       integer,
  fund_evict      integer,
  fund_airport    integer,

  -- Revenue settings, in native units.
  rev_fees        numeric,   -- $M of fees/fines
  rev_property    numeric,   -- mill-levy increase
  rev_sales       numeric,   -- percentage points of sales tax
  reserves        numeric,   -- $M of one-time reserves

  -- Derived totals the widget computes (kept so the aggregate is recomputable
  -- without re-deriving from every slider).
  spend_change    numeric,   -- signed $M; + = more spending = wider gap
  revenue_total   numeric,   -- $M recurring revenue + reserves
  revenue_only    numeric,   -- $M recurring revenue (reserves excluded)
  used_vote       boolean,
  used_revenue    boolean,
  used_reserves   boolean,
  top_cut         text,      -- name of the reader's single deepest GF cut, or null

  -- Optional reader survey (one column per item; multi-selects joined by "; ").
  demo_years      text,
  demo_employment text,
  "demo_workArea" text,   -- quoted to preserve camelCase (matches the widget + notebook)
  demo_student    text,
  demo_education  text,
  demo_building   text,
  demo_tenure     text,
  demo_income     text,
  demo_age        text,
  demo_race       text,
  demo_gender     text,
  demo_lgbtq      text,
  demo_disability text,

  -- Operational, not analytical. (No IP-derived value is stored — dedup and
  -- rate-limiting live in ephemeral edge storage, not here.)
  repeat_client   boolean not null default false,
  raw             jsonb,                      -- full original payload, as a safety net

  -- Guards mirroring the widget's own input bounds.
  constraint gf_in_range check (
    coalesce(gf_police,0)     between -25 and 25 and
    coalesce(gf_fire,0)       between -25 and 25 and
    coalesce(gf_genadmin,0)   between -25 and 25 and
    coalesce(gf_transfers,0)  between -25 and 25 and
    coalesce(gf_parksrec,0)   between -25 and 25 and
    coalesce(gf_hhs,0)        between -25 and 25 and
    coalesce(gf_library,0)    between -25 and 25 and
    coalesce(gf_facilities,0) between -25 and 25 and
    coalesce(gf_planning,0)   between -25 and 25
  ),
  constraint rev_nonneg check (
    coalesce(rev_fees,0)    >= 0 and
    coalesce(rev_property,0)>= 0 and
    coalesce(rev_sales,0)   >= 0 and
    coalesce(reserves,0)    >= 0
  )
);

comment on table public.contributions is
  'One flat row per reader submission from the Balance Boulder''s Budget widget. No PII. Columns match the analysis notebook one-to-one. See ARCHITECTURE.md.';

create index if not exists contributions_created_at_idx on public.contributions (created_at);

-- Hardening, idempotent (applies whether the table is fresh or already exists):
--   • drop the old persisted IP hash entirely (no IP-derived value is kept);
--   • bound values so a scripted insert can't store absurd or oversized data.
alter table public.contributions drop column if exists dedupe_hash;
drop index if exists public.contributions_dedupe_hash_idx;

alter table public.contributions drop constraint if exists contributions_sane_values;
alter table public.contributions add constraint contributions_sane_values check (
  coalesce(rev_fees, 0)     <= 100  and
  coalesce(rev_property, 0) <= 100  and
  coalesce(rev_sales, 0)    <= 10   and
  coalesce(reserves, 0)     <= 1000 and
  (client_version is null or client_version between 0 and 1000) and
  char_length(coalesce(scenario, '')) <= 64  and
  char_length(coalesce(top_cut, ''))  <= 200 and
  char_length(coalesce(raw::text, '')) <= 8000
);

-- ---------------------------------------------------------------------------
-- Row Level Security. Two write paths are supported and both are safe:
--
--   • Direct from the browser with the PUBLISHABLE key (role `anon`): allowed
--     to INSERT a contribution, but NOT to read, update, or delete any row.
--     Reads with `Prefer: return=minimal` so nothing is echoed back.
--   • Through the Vercel function with the SECRET key (role `service_role`):
--     bypasses RLS entirely; used for server-side validation.
--
-- Either way, the only way to READ the data is the aggregate function below
-- (or the secret key, server-side). A leaked publishable key can add rows but
-- can never read one back.
-- ---------------------------------------------------------------------------
alter table public.contributions enable row level security;

grant usage on schema public to anon, authenticated;
revoke all on public.contributions from anon, authenticated;
grant insert on public.contributions to anon, authenticated;

-- A real predicate (not WITH CHECK (true)): mirror the widget's own rule that a
-- submission must answer at least one survey item (security advisor 0024).
drop policy if exists "anon may insert a contribution" on public.contributions;
create policy "anon may insert a contribution"
  on public.contributions for insert
  to anon, authenticated
  with check (
    num_nonnulls(
      demo_years, demo_employment, "demo_workArea", demo_student,
      demo_education, demo_building, demo_tenure, demo_income,
      demo_age, demo_race, demo_gender, demo_lgbtq, demo_disability
    ) >= 1
  );

-- Force a trustworthy server timestamp regardless of what a client sends, so
-- the response timeline can't be spoofed through the public insert path.
create or replace function public.contributions_stamp()
returns trigger
language plpgsql
security invoker
set search_path = ''               -- pin search_path (security advisor 0011)
as $$
begin
  -- Server owns the operational columns: ignore whatever a public client sent,
  -- so an insert can't choose its own id or backdate a row.
  new.id := gen_random_uuid();     -- core since PG13, resolves from pg_catalog
  new.created_at := now();
  return new;
end;
$$;

drop trigger if exists contributions_stamp on public.contributions;
create trigger contributions_stamp
  before insert on public.contributions
  for each row execute function public.contributions_stamp();

-- ---------------------------------------------------------------------------
-- Public tally — readers see only an aggregate, never an individual row.
--
-- A SECURITY DEFINER function callable by anon/authenticated trips the security
-- advisor (lints 0028/0029), so instead we keep ONE precomputed row in
-- `contribution_stats` that the publishable key may read, and recompute it with
-- a trigger whenever a contribution lands. budget_aggregate() is then a plain
-- SECURITY INVOKER reader, so the widget's existing RPC call is unchanged.
-- ---------------------------------------------------------------------------
create table if not exists public.contribution_stats (
  id          integer primary key default 1,
  agg         jsonb not null default
              '{"n":0,"usedRevenue":0,"usedVote":0,"usedReserves":0,"revShareSum":0,"cutTally":{}}'::jsonb,
  updated_at  timestamptz not null default now(),
  constraint contribution_stats_single_row check (id = 1)
);

-- The aggregate is public; individual rows are not. A SELECT policy of USING
-- (true) here is intentional public read and is NOT what advisor lint 0024
-- flags (that targets permissive INSERT/UPDATE/DELETE, not SELECT).
alter table public.contribution_stats enable row level security;
grant select on public.contribution_stats to anon, authenticated;
drop policy if exists "anyone may read the aggregate" on public.contribution_stats;
create policy "anyone may read the aggregate"
  on public.contribution_stats for select
  to anon, authenticated
  using (true);

-- Recompute the single stats row from the table. SECURITY DEFINER so it can
-- read contributions and write stats regardless of which role inserted; it
-- returns `trigger`, so it is never callable through the REST API. search_path
-- is pinned (advisor lint 0011), and EXECUTE is revoked from callers (the
-- trigger fires without needing it).
create or replace function public.refresh_contribution_stats()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.contribution_stats (id, agg, updated_at)
  values (1, (
    select jsonb_build_object(
      'n',            count(*),
      'usedRevenue',  count(*) filter (where used_revenue),
      'usedVote',     count(*) filter (where used_vote),
      'usedReserves', count(*) filter (where used_reserves),
      'revShareSum',  coalesce(sum(
        case
          when (coalesce(revenue_total,0) + greatest(0, -coalesce(spend_change,0))) > 0
          then coalesce(revenue_total,0)
               / (coalesce(revenue_total,0) + greatest(0, -coalesce(spend_change,0)))
          else 0
        end), 0),
      'cutTally', coalesce((
        select jsonb_object_agg(top_cut, c)
        from (
          select top_cut, count(*) as c
          from public.contributions
          where top_cut is not null
          group by top_cut
        ) t
      ), '{}'::jsonb)
    )
    from public.contributions
  ), now())
  on conflict (id) do update
    set agg = excluded.agg, updated_at = excluded.updated_at;
  return null;
end;
$$;
revoke execute on function public.refresh_contribution_stats() from public, anon, authenticated;

drop trigger if exists contributions_stats_refresh on public.contributions;
create trigger contributions_stats_refresh
  after insert or update or delete on public.contributions
  for each statement execute function public.refresh_contribution_stats();

-- The widget's read endpoint, unchanged in shape. SECURITY INVOKER reading the
-- public stats row (so it is not flagged by advisor 0028/0029); search_path
-- pinned (0011). Returns exactly { n, usedRevenue, usedVote, usedReserves,
-- revShareSum, cutTally }.
create or replace function public.budget_aggregate()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
  select coalesce(
    (select agg from public.contribution_stats where id = 1),
    '{"n":0,"usedRevenue":0,"usedVote":0,"usedReserves":0,"revShareSum":0,"cutTally":{}}'::jsonb
  );
$$;

comment on function public.budget_aggregate() is
  'Public anonymous tally in the shape the widget renders, read from contribution_stats. Never returns an individual row.';

grant execute on function public.budget_aggregate() to anon, authenticated;

-- Seed / refresh the stats row from whatever is already in the table, so the
-- tally is correct immediately after this script runs (covers existing data).
insert into public.contribution_stats (id, agg, updated_at)
values (1, (
  select jsonb_build_object(
    'n',            count(*),
    'usedRevenue',  count(*) filter (where used_revenue),
    'usedVote',     count(*) filter (where used_vote),
    'usedReserves', count(*) filter (where used_reserves),
    'revShareSum',  coalesce(sum(
      case
        when (coalesce(revenue_total,0) + greatest(0, -coalesce(spend_change,0))) > 0
        then coalesce(revenue_total,0)
             / (coalesce(revenue_total,0) + greatest(0, -coalesce(spend_change,0)))
        else 0
      end), 0),
    'cutTally', coalesce((
      select jsonb_object_agg(top_cut, c)
      from (
        select top_cut, count(*) as c
        from public.contributions
        where top_cut is not null
        group by top_cut
      ) t
    ), '{}'::jsonb)
  )
  from public.contributions
), now())
on conflict (id) do update
  set agg = excluded.agg, updated_at = excluded.updated_at;
