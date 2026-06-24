// Canonical column contract for a contribution. Keep these lists in lockstep
// with the widget's data tables (GF_DEPTS / LOCKED_FUNDS / REVENUE / DEMO),
// the Supabase schema (supabase/schema.sql), and the analysis notebook
// (GF_SLIDERS / FUND_SLIDERS / REV_COLS / DEMO_COLS). They are the single
// source of truth the /submit handler validates against.

export const GF_SLIDERS = [
  "gf_police", "gf_fire", "gf_genadmin", "gf_transfers", "gf_parksrec",
  "gf_hhs", "gf_library", "gf_facilities", "gf_planning",
];

export const FUND_SLIDERS = [
  "fund_capital", "fund_water", "fund_openspace", "fund_transpo",
  "fund_wastewater", "fund_internal", "fund_stormwater", "fund_parkstax",
  "fund_ahf", "fund_recact", "fund_climate", "fund_pds", "fund_ssb",
  "fund_ccrs", "fund_arts", "fund_evict", "fund_airport",
];

export const SLIDER_COLS = [...GF_SLIDERS, ...FUND_SLIDERS]; // integers, −25..25

export const DEMO_COLS = [
  "demo_years", "demo_employment", "demo_workArea", "demo_student",
  "demo_education", "demo_building", "demo_tenure", "demo_income",
  "demo_age", "demo_race", "demo_gender", "demo_lgbtq", "demo_disability",
];

const clampInt = (x) => {
  const n = Math.round(Number(x));
  if (!Number.isFinite(n)) return 0;
  return Math.max(-25, Math.min(25, n));
};
const nonNegNum = (x) => {
  const n = Number(x);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};
const num = (x) => {
  const n = Number(x);
  return Number.isFinite(n) ? n : 0;
};
const str = (x) =>
  x === null || x === undefined || x === "" ? null : String(x).slice(0, 300);
const bool = (x) => x === true || x === "true" || x === 1;

// Build the typed DB row from an arbitrary client payload. Only known keys are
// copied; everything else is ignored (but the full payload is preserved in
// `raw`). Returns the row object ready for PostgREST insert.
export function rowFromPayload(payload) {
  const p = payload && typeof payload === "object" ? payload : {};
  const row = {
    client_ts: typeof p.ts === "string" ? p.ts : null,
    client_version: Number.isFinite(Number(p.v)) ? Number(p.v) : null,
    scenario: str(p.scenario),
    rev_fees: nonNegNum(p.rev_fees),
    rev_property: nonNegNum(p.rev_property),
    rev_sales: nonNegNum(p.rev_sales),
    reserves: nonNegNum(p.reserves),
    spend_change: num(p.spend_change),
    revenue_total: num(p.revenue_total),
    revenue_only: num(p.revenue_only),
    used_vote: bool(p.used_vote),
    used_revenue: bool(p.used_revenue),
    used_reserves: bool(p.used_reserves),
    top_cut: str(p.top_cut),
    repeat_client: bool(p.repeatClient),
    raw: p,
  };
  for (const c of SLIDER_COLS) row[c] = clampInt(p[c]);
  for (const c of DEMO_COLS) row[c] = str(p[c]);
  return row;
}

// The widget requires at least one survey answer before it will submit. We
// re-check server-side so a hand-crafted POST can't bypass it.
export function hasOneDemo(payload) {
  return DEMO_COLS.some((c) => str(payload?.[c]) !== null);
}
