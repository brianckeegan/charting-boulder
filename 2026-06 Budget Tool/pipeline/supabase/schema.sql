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
-- widget payload and the analysis notebook (Budget-Survey-Analysis.ipynb)
-- ONE-TO-ONE, so a CSV export drops straight into the notebook. See
-- ../../ARCHITECTURE.md for the full data dictionary and the data flow.
--
-- PRIVACY — no name, account, email, IP address, or browser fingerprint is
-- stored. `dedupe_hash` is a salted one-way SHA-256 (salt + IP + UTC day),
-- computed in the serverless function and never reversible to an IP; it only
-- lets us flag likely duplicate submissions. Row Level Security is ON and no
-- policy is granted to the anon/authenticated roles, so the only way to read
-- or write rows is the service-role key (held server-side, in Vercel env vars)
-- or the aggregate function below, which never exposes an individual row.
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

  -- Operational, not analytical.
  dedupe_hash     text,                       -- salted one-way hash (no PII)
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
create index if not exists contributions_dedupe_hash_idx on public.contributions (dedupe_hash);

-- ---------------------------------------------------------------------------
-- Row Level Security. Two write paths are supported and both are safe:
--
--   • Direct from the browser with the PUBLISHABLE key (role `anon`): allowed
--     to INSERT a contribution, but NOT to read, update, or delete any row.
--     Reads with `Prefer: return=minimal` so nothing is echoed back.
--   • Through the Vercel function with the SECRET key (role `service_role`):
--     bypasses RLS entirely; used for server-side dedupe hashing and validation.
--
-- Either way, the only way to READ the data is the aggregate function below
-- (or the secret key, server-side). A leaked publishable key can add rows but
-- can never read one back.
-- ---------------------------------------------------------------------------
alter table public.contributions enable row level security;

grant usage on schema public to anon, authenticated;
revoke all on public.contributions from anon, authenticated;
grant insert on public.contributions to anon, authenticated;

drop policy if exists "anon may insert a contribution" on public.contributions;
create policy "anon may insert a contribution"
  on public.contributions for insert
  to anon, authenticated
  with check (true);

-- Force a trustworthy server timestamp regardless of what a client sends, so
-- the response timeline can't be spoofed through the public insert path.
create or replace function public.contributions_stamp()
returns trigger
language plpgsql
as $$
begin
  new.created_at := now();
  return new;
end;
$$;

drop trigger if exists contributions_stamp on public.contributions;
create trigger contributions_stamp
  before insert on public.contributions
  for each row execute function public.contributions_stamp();

-- ---------------------------------------------------------------------------
-- Aggregate function — the ONLY public window into the data. Returns exactly
-- the shape the widget's AggregateView expects, and never an individual row:
--   { n, usedRevenue, usedVote, usedReserves, revShareSum, cutTally }
-- revShare per submission = revenue_total / (revenue_total + net cuts), where
-- net cuts = greatest(0, -spend_change). Summed here; the widget divides by n.
-- SECURITY DEFINER so it can read the table even though the caller's role
-- cannot; it only ever emits aggregates.
-- ---------------------------------------------------------------------------
create or replace function public.budget_aggregate()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
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
  from public.contributions;
$$;

comment on function public.budget_aggregate() is
  'Anonymous aggregate of all contributions in the shape the widget renders. Never returns an individual row.';

-- The aggregate is safe to expose: it leaks no individual response. Granting
-- execute to anon also enables an optional no-server embed (the widget calling
-- Supabase directly); the Vercel path does not rely on this grant.
grant execute on function public.budget_aggregate() to anon, authenticated;
