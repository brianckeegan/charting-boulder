-- ============================================================================
-- Balance Boulder's Budget — Supabase schema
-- ============================================================================
-- Destination for reader "contributions" from the budget widget
-- (boulder-budget-widget.jsx). Run this once against the project at
-- https://iplcjxbazezpjdzdpjxx.supabase.co using the SQL Editor
-- (Dashboard → SQL → New query → paste → Run), or via the Supabase CLI:
--
--     supabase db execute --file 2026-06-budget-tool/pipeline/supabase/schema.sql
--
-- Re-running is safe: every statement is idempotent (IF NOT EXISTS / OR REPLACE).
--
-- WHAT THIS STORES — one flat row per submission. Column names match the
-- widget payload and the analysis notebook (budget-survey-analysis.ipynb)
-- ONE-TO-ONE, so a CSV export drops straight into the notebook. See
-- ../../ARCHITECTURE.md for the full data dictionary and the data flow.
--
-- PRIVACY — no name, account, email, IP address, or browser fingerprint is
-- stored, and NO IP-derived value is persisted at all, so nothing here can be
-- tied back to a person. Row Level Security is ON: the publishable key may
-- INSERT a contribution but can never read, update, or delete a row. Readers
-- see only the precomputed public tally in `contribution_stats` (via
-- budget_aggregate()); individual rows are reachable only with the
-- service-role key, server-side.
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
  gf_genadmin     integer,   -- General Government (transfers, debt, citywide)
  gf_fire         integer,
  gf_hhs          integer,
  gf_it           integer,
  gf_manager      integer,
  gf_facilities   integer,
  gf_finance      integer,
  gf_parksrec     integer,
  gf_attorney     integer,
  gf_other        integer,   -- the rest of the GF departments, bundled

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

  -- Revenue settings. The three tax/fee sources are percentage-change sliders
  -- (−25..25) over each source's current General Fund revenue, like gf_*; a
  -- negative value is a revenue cut. Reserves stay a one-time dollar draw.
  rev_fees        integer,   -- % change of GF fees & charges, −25..25
  rev_property    integer,   -- % change of GF property tax, −25..25
  rev_sales       integer,   -- % change of GF sales & use tax, −25..25
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
  demo_area       text,   -- which area of Boulder the reader lives in
  demo_employment text,
  demo_commute    text,   -- "how do you get around Boulder"
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
  repeat_client   boolean not null default false,
  raw             jsonb,                      -- full original payload, as a safety net

  -- Guards mirroring the widget's own input bounds.
  constraint gf_in_range check (
    coalesce(gf_police,0)     between -25 and 25 and
    coalesce(gf_genadmin,0)   between -25 and 25 and
    coalesce(gf_fire,0)       between -25 and 25 and
    coalesce(gf_hhs,0)        between -25 and 25 and
    coalesce(gf_it,0)         between -25 and 25 and
    coalesce(gf_manager,0)    between -25 and 25 and
    coalesce(gf_facilities,0) between -25 and 25 and
    coalesce(gf_finance,0)    between -25 and 25 and
    coalesce(gf_parksrec,0)   between -25 and 25 and
    coalesce(gf_attorney,0)   between -25 and 25 and
    coalesce(gf_other,0)      between -25 and 25
  ),
  constraint rev_pct_in_range check (
    coalesce(rev_fees,0)     between -25 and 25 and
    coalesce(rev_property,0) between -25 and 25 and
    coalesce(rev_sales,0)    between -25 and 25
  ),
  constraint reserves_nonneg check ( coalesce(reserves,0) >= 0 ),

  -- Reject absurd or oversized values from a scripted insert.
  constraint contributions_sane_values check (
    coalesce(reserves, 0)     <= 1000 and
    (client_version is null or client_version between 0 and 1000) and
    char_length(coalesce(scenario, '')) <= 64  and
    char_length(coalesce(top_cut, ''))  <= 200 and
    char_length(coalesce(raw::text, '')) <= 8000
  )
);

comment on table public.contributions is
  'One flat row per reader submission from the Balance Boulder''s Budget widget. No PII. Columns match the analysis notebook one-to-one. See ARCHITECTURE.md.';

create index if not exists contributions_created_at_idx on public.contributions (created_at);

-- ---------------------------------------------------------------------------
-- Allowlist of General Fund department names the widget may report as a
-- reader's deepest cut. top_cut is echoed back to every reader in the public
-- tally, so it must never be free text. Keep in lockstep with GF_DEPTS in
-- boulder-budget-widget.jsx; update this function BEFORE shipping a rename.
-- ---------------------------------------------------------------------------
create or replace function public.bbw_gf_departments()
returns text[]
language sql
immutable
parallel safe
set search_path = ''
as $$
  select array[
    'Police',
    'General Government',
    'Fire-Rescue',
    'Housing & Human Services (GF share)',
    'Innovation & Technology',
    'City Manager''s Office',
    'Facilities & Fleet (GF share)',
    'Finance',
    'Parks & Recreation (GF share)',
    'City Attorney''s Office',
    'Other General Fund departments'
  ]::text[];
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security. The browser writes directly with the PUBLISHABLE key
-- (role `anon`): allowed to INSERT a contribution, but NOT to read, update, or
-- delete any row. Inserts use `Prefer: return=minimal` so nothing is echoed
-- back.
--
-- The only way to READ the data is the aggregate function below (or the secret
-- key, server-side, for offline analysis). A leaked publishable key can add
-- rows but can never read one back.
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
      demo_years, demo_area, demo_employment, demo_commute, demo_student,
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
            and top_cut = any (public.bbw_gf_departments())   -- read-time filter
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
          and top_cut = any (public.bbw_gf_departments())
        group by top_cut
      ) t
    ), '{}'::jsonb)
  )
  from public.contributions
), now())
on conflict (id) do update
  set agg = excluded.agg, updated_at = excluded.updated_at;

-- ---------------------------------------------------------------------------
-- Input hardening (see migrations/2026-08-29-security-hardening.sql).
-- Constraints are NOT VALID so they enforce on every new row without failing
-- on legacy data; validate them explicitly once the table is known clean.
-- ---------------------------------------------------------------------------
alter table public.contributions drop constraint if exists top_cut_known_department;
alter table public.contributions
  add constraint top_cut_known_department
  check (top_cut is null or top_cut = any (public.bbw_gf_departments()))
  not valid;

-- ---------------------------------------------------------------------------
-- 2. Length bounds for the survey columns.
--
--    120 is comfortably above every single-select option (the longest is the
--    76-character housing-type answer). demo_race is a MULTI-select joined with
--    "; ", so selecting all nine options legitimately stores 194 characters —
--    it gets 400. Picking 120 for demo_race would silently reject genuine
--    submissions from readers who identify with several groups.
-- ---------------------------------------------------------------------------
alter table public.contributions drop constraint if exists demo_len_bounded;
alter table public.contributions
  add constraint demo_len_bounded check (
    char_length(coalesce(demo_years,      '')) <= 120 and
    char_length(coalesce(demo_area,       '')) <= 120 and
    char_length(coalesce(demo_employment, '')) <= 120 and
    char_length(coalesce(demo_commute,    '')) <= 120 and
    char_length(coalesce(demo_student,    '')) <= 120 and
    char_length(coalesce(demo_education,  '')) <= 120 and
    char_length(coalesce(demo_building,   '')) <= 120 and
    char_length(coalesce(demo_tenure,     '')) <= 120 and
    char_length(coalesce(demo_income,     '')) <= 120 and
    char_length(coalesce(demo_age,        '')) <= 120 and
    char_length(coalesce(demo_gender,     '')) <= 120 and
    char_length(coalesce(demo_lgbtq,      '')) <= 120 and
    char_length(coalesce(demo_disability, '')) <= 120 and
    char_length(coalesce(demo_race,       '')) <= 400   -- multi-select, joined
  ) not valid;

-- ---------------------------------------------------------------------------
-- 3. Per-IP rate limiting.
--
--    The client IP is NEVER stored. It is hashed with a random per-project salt
--    that lives in a table the publishable key cannot read, so the audit table
--    holds opaque hashes that cannot be reversed to an address.
--
--    Defaults: 20 inserts per IP per 10 minutes. Deliberately generous — Boulder
--    readers may share an address behind campus or carrier NAT, and the goal is
--    to stop scripted flooding, not to enforce one submission per person. Tune
--    with the UPDATE at the bottom of this file.
-- ---------------------------------------------------------------------------
create table if not exists public.rate_limit_config (
  id             integer primary key default 1 check (id = 1),
  salt           text    not null default gen_random_uuid()::text,
  max_per_window integer not null default 20,
  window_minutes integer not null default 10
);
insert into public.rate_limit_config (id) values (1) on conflict (id) do nothing;

create table if not exists public.insert_audit (
  ip_hash    text        not null,
  created_at timestamptz not null default now()
);
create index if not exists insert_audit_lookup
  on public.insert_audit (ip_hash, created_at desc);

-- Neither table is reachable with the publishable key: privileges revoked and
-- RLS on with no policies at all.
alter table public.rate_limit_config enable row level security;
alter table public.insert_audit      enable row level security;
revoke all on public.rate_limit_config from anon, authenticated;
revoke all on public.insert_audit      from anon, authenticated;

create or replace function public.contributions_rate_limit()
returns trigger
language plpgsql
security definer                   -- must read the salt and write the audit row
set search_path = ''
as $$
declare
  hdrs json;
  ip   text;
  cfg  public.rate_limit_config%rowtype;
  h    text;
  used integer;
begin
  select * into cfg from public.rate_limit_config where id = 1;
  if not found then
    return new;                    -- unconfigured: fail open rather than block readers
  end if;

  -- PostgREST exposes the request headers as a GUC. Absent for direct SQL
  -- inserts and psql, so treat "no header" as "not a public request".
  begin
    hdrs := current_setting('request.headers', true)::json;
  exception when others then
    hdrs := null;
  end;

  ip := nullif(btrim(split_part(coalesce(hdrs ->> 'x-forwarded-for', ''), ',', 1)), '');
  if ip is null then
    return new;
  end if;

  h := encode(sha256(convert_to(ip || cfg.salt, 'UTF8')), 'hex');

  select count(*) into used
  from public.insert_audit
  where ip_hash = h
    and created_at > now() - make_interval(mins => cfg.window_minutes);

  if used >= cfg.max_per_window then
    raise exception
      'Too many submissions from this network. Please try again in a few minutes.';
  end if;

  insert into public.insert_audit (ip_hash) values (h);

  -- Opportunistic pruning (~1% of inserts) so the audit table stays small.
  if random() < 0.01 then
    delete from public.insert_audit where created_at < now() - interval '2 days';
  end if;

  return new;
end;
$$;

revoke execute on function public.contributions_rate_limit() from public, anon, authenticated;

drop trigger if exists contributions_rate_limit on public.contributions;
create trigger contributions_rate_limit
  before insert on public.contributions
  for each row execute function public.contributions_rate_limit();
