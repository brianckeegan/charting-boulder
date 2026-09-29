-- ===========================================================================
-- 2027 sliders, phase 1 of 2: ADD — 2026-09-29
--
-- Run this in the Supabase SQL editor BEFORE the 2027 widget is merged and
-- published. Step-by-step: RUNBOOK-2027-sliders.md, next to this file.
--
-- It only adds. The 2026 widget keeps working against the table while it is
-- still live, and the 2027 widget (payload v5) finds every column it writes:
--
--   rev_marijuana  the recreational marijuana tax rate the reader chose,
--                  0..10 (%). 3.5 today; the recommended budget sets 5.5.
--   rev_shift      $M of General Fund costs moved onto dedicated funds, 0..5
--   used_shift     whether the reader moved any
--   fund_utilities, fund_hhs, fund_parksrec, fund_facilities, fund_manager,
--   fund_fire, fund_other
--                  the locked section is now each department's spending
--                  outside the General Fund rather than a list of funds.
--                  With the existing fund_transpo, fund_openspace, fund_pds
--                  and fund_climate, these are its eleven sliders, −25..25.
--
-- The public tally gains `usedShift`. It keeps `usedReserves` until phase 2,
-- so the 2026 widget's tally still renders in the meantime. The share of the
-- gap closed with revenue (`revShareSum`) is now counted the way the 2027
-- widget computes it: new revenue (never below zero) over new revenue + net
-- cuts + costs moved onto dedicated funds.
--
-- Nothing is deleted and no existing value changes. Idempotent: running it
-- twice is harmless. It runs in one transaction, so an error applies nothing.
-- ===========================================================================

begin;

-- ---------------------------------------------------------------------------
-- 1. The new columns.
-- ---------------------------------------------------------------------------
alter table public.contributions
  add column if not exists rev_marijuana   numeric,
  add column if not exists rev_shift       numeric,
  add column if not exists used_shift      boolean,
  add column if not exists fund_utilities  integer,
  add column if not exists fund_hhs        integer,
  add column if not exists fund_parksrec   integer,
  add column if not exists fund_facilities integer,
  add column if not exists fund_manager    integer,
  add column if not exists fund_fire       integer,
  add column if not exists fund_other      integer;

comment on column public.contributions.rev_marijuana is
  'Recreational marijuana tax rate the reader chose, % (0..10; 3.5 today, 5.5 recommended). Widget v5.';
comment on column public.contributions.rev_shift is
  '$M of General Fund costs the reader moved onto voter-dedicated funds (0..5). Not revenue. Widget v5.';
comment on column public.contributions.used_shift is
  'Whether the reader moved any General Fund cost onto a dedicated fund. Widget v5.';

-- ---------------------------------------------------------------------------
-- 2. Guards mirroring the 2027 widget's input bounds. NOT VALID, like the
--    security migration's: enforced on every new row, while the 2026 test rows
--    are not re-checked. Phase 2 validates them once those rows are gone.
-- ---------------------------------------------------------------------------
alter table public.contributions drop constraint if exists rev_levers_in_range;
alter table public.contributions
  add constraint rev_levers_in_range check (
    coalesce(rev_marijuana, 3.5) between 0 and 10 and
    coalesce(rev_shift, 0)       between 0 and 5
  ) not valid;

alter table public.contributions drop constraint if exists locked_in_range;
alter table public.contributions
  add constraint locked_in_range check (
    coalesce(fund_utilities,0)  between -25 and 25 and
    coalesce(fund_transpo,0)    between -25 and 25 and
    coalesce(fund_openspace,0)  between -25 and 25 and
    coalesce(fund_hhs,0)        between -25 and 25 and
    coalesce(fund_parksrec,0)   between -25 and 25 and
    coalesce(fund_facilities,0) between -25 and 25 and
    coalesce(fund_pds,0)        between -25 and 25 and
    coalesce(fund_manager,0)    between -25 and 25 and
    coalesce(fund_climate,0)    between -25 and 25 and
    coalesce(fund_fire,0)       between -25 and 25 and
    coalesce(fund_other,0)      between -25 and 25
  ) not valid;

-- ---------------------------------------------------------------------------
-- 3. The public tally: add usedShift, keep usedReserves for now, and count the
--    revenue share over all three ways of closing the gap.
-- ---------------------------------------------------------------------------
alter table public.contribution_stats
  alter column agg set default
  '{"n":0,"usedRevenue":0,"usedVote":0,"usedShift":0,"usedReserves":0,"revShareSum":0,"cutTally":{}}'::jsonb;

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
      'usedShift',    count(*) filter (where used_shift),
      'usedReserves', count(*) filter (where used_reserves),   -- dropped in phase 2
      'revShareSum',  coalesce(sum(
        case
          when greatest(coalesce(revenue_only,0), 0)
               + greatest(0, -coalesce(spend_change,0))
               + coalesce(rev_shift,0) > 0
          then greatest(coalesce(revenue_only,0), 0)
               / (greatest(coalesce(revenue_only,0), 0)
                  + greatest(0, -coalesce(spend_change,0))
                  + coalesce(rev_shift,0))
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

create or replace function public.budget_aggregate()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
  select coalesce(
    (select agg from public.contribution_stats where id = 1),
    '{"n":0,"usedRevenue":0,"usedVote":0,"usedShift":0,"usedReserves":0,"revShareSum":0,"cutTally":{}}'::jsonb
  );
$$;
grant execute on function public.budget_aggregate() to anon, authenticated;

-- Recompute the stored tally now, so it has the new shape before anyone reads
-- it. An UPDATE that touches no row still fires the statement-level trigger.
update public.contributions set scenario = scenario where false;

commit;

-- ---------------------------------------------------------------------------
-- Check it took (a new query):
--
--   select public.budget_aggregate();
--
-- Expect the same n as before, and a "usedShift" key alongside the others.
-- ---------------------------------------------------------------------------
