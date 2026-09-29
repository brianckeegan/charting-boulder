-- ===========================================================================
-- 2027 sliders, phase 2 of 2: DROP — 2026-09-29
--
-- Run this in the Supabase SQL editor only AFTER the 2027 widget is live and
-- a test submission from it has landed (RUNBOOK-2027-sliders.md, step 5).
-- Running it while the 2026 widget is still published would make that
-- widget's submissions fail, because it writes columns this removes.
--
-- What it does, in order:
--   1. Deletes every row the 2026 widget wrote (client_version below 5). They
--      are test rows, and they carry the columns about to go.
--   2. Rebuilds the one constraint that names a dropped column, and drops the
--      reserves guard.
--   3. Drops the 2026 widget's columns: one-time reserves, the total that
--      included them, and the thirteen fund sliders the 2027 locked section
--      no longer has.
--   4. Takes usedReserves out of the public tally.
--   5. Validates every NOT VALID constraint, now that only 2027 rows remain.
--
-- Rows the 2027 widget wrote (client_version 5) are kept. To start from an
-- empty table before launch instead, see the RUNBOOK's optional last step.
--
-- One transaction: an error applies nothing. Running it twice is harmless.
-- ===========================================================================

begin;

-- 1. The 2026 widget's test rows.
delete from public.contributions where coalesce(client_version, 0) < 5;

-- 2. Constraints that name the old columns.
alter table public.contributions drop constraint if exists reserves_nonneg;
alter table public.contributions drop constraint if exists contributions_sane_values;
alter table public.contributions
  add constraint contributions_sane_values check (
    (client_version is null or client_version between 0 and 1000) and
    char_length(coalesce(scenario, '')) <= 64  and
    char_length(coalesce(top_cut, ''))  <= 200 and
    char_length(coalesce(raw::text, '')) <= 8000
  );

-- 3. The 2026 widget's columns.
alter table public.contributions
  drop column if exists reserves,
  drop column if exists revenue_total,
  drop column if exists used_reserves,
  drop column if exists fund_capital,
  drop column if exists fund_water,
  drop column if exists fund_wastewater,
  drop column if exists fund_internal,
  drop column if exists fund_stormwater,
  drop column if exists fund_parkstax,
  drop column if exists fund_ahf,
  drop column if exists fund_recact,
  drop column if exists fund_ssb,
  drop column if exists fund_ccrs,
  drop column if exists fund_arts,
  drop column if exists fund_evict,
  drop column if exists fund_airport;

-- 4. The public tally, without usedReserves.
alter table public.contribution_stats
  alter column agg set default
  '{"n":0,"usedRevenue":0,"usedVote":0,"usedShift":0,"revShareSum":0,"cutTally":{}}'::jsonb;

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
    '{"n":0,"usedRevenue":0,"usedVote":0,"usedShift":0,"revShareSum":0,"cutTally":{}}'::jsonb
  );
$$;
grant execute on function public.budget_aggregate() to anon, authenticated;

-- Recompute the stored tally with the new function. (The delete above
-- refreshed it too, but with the old one, which still counted reserves.)
update public.contributions set scenario = scenario where false;

-- 5. Only 2027 rows remain, so every guard can be checked against all of them.
alter table public.contributions validate constraint rev_levers_in_range;
alter table public.contributions validate constraint locked_in_range;
alter table public.contributions validate constraint top_cut_known_department;
alter table public.contributions validate constraint demo_len_bounded;

commit;
