-- ===========================================================================
-- Security hardening for public.contributions — 2026-08-29
--
-- Run this in the Supabase SQL editor (see RUNBOOK.md next to this file).
-- It is idempotent: running it twice is harmless.
--
-- Fixes, in order:
--   1. top_cut is free text today, and the most-frequent value is rendered to
--      every reader as "the most common deep cut was X". Anyone holding the
--      publishable key (which is public by design) could therefore put chosen
--      words in the published article. Constrain it to real department names,
--      AND stop counting anything off-list when the tally is built.
--   2. Bound the 14 demo_* columns, which are unbounded `text` today, so a
--      single insert cannot carry megabytes of payload.
--   3. Rate-limit inserts per client IP (stored only as a salted hash).
--
-- All constraints are added NOT VALID: they are enforced on every new row from
-- now on, but existing rows are not re-checked, so this cannot fail on legacy
-- data. See the end of this file for how to validate later if you want to.
-- ===========================================================================

begin;

-- ---------------------------------------------------------------------------
-- 1. The department allowlist. One source of truth, referenced by both the
--    CHECK constraint and the tally builder below. IMMUTABLE so a CHECK
--    constraint may call it.
--
--    If a department is ever renamed in the widget, update this function FIRST
--    (create or replace), then ship the widget change — otherwise real reader
--    submissions naming the new department would be rejected.
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

comment on function public.bbw_gf_departments() is
  'Allowlist of General Fund department names the widget can report as a deepest cut. Keep in lockstep with GF_DEPTS in boulder-budget-widget.jsx.';

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

-- ---------------------------------------------------------------------------
-- 4. Read-time filter: the tally counts allowlisted departments only, so any
--    off-list value already sitting in the table stops being displayed even
--    though the CHECK above was added NOT VALID.
-- ---------------------------------------------------------------------------
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

-- Recompute the tally now so any previously stored off-list value disappears
-- from the public number immediately.
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

commit;

-- ===========================================================================
-- Optional follow-ups (run separately, not part of the migration)
-- ===========================================================================
--
-- Tune the rate limit:
--   update public.rate_limit_config set max_per_window = 40, window_minutes = 10 where id = 1;
--
-- See whether any stored top_cut is off-list (should return 0 rows on a clean table):
--   select top_cut, count(*) from public.contributions
--    where top_cut is not null and top_cut <> all (public.bbw_gf_departments())
--    group by top_cut order by 2 desc;
--
-- Once that returns nothing, promote the constraints from NOT VALID to fully
-- validated (this scans the table and will error if any row violates):
--   alter table public.contributions validate constraint top_cut_known_department;
--   alter table public.contributions validate constraint demo_len_bounded;
