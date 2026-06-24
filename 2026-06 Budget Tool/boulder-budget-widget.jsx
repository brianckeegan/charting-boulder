import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  Lock, Building2, Vote, RotateCcw, Check, AlertTriangle,
  Github, ChevronDown, ChevronUp, Users, ArrowDownToLine,
} from "lucide-react";

/* ============================================================================
   BALANCE BOULDER'S BUDGET — an interactive for Boulder Reporting Lab
   ============================================================================

   FOR EDITORS & REPORTERS — HOW TO READ AND EDIT THIS FILE
   --------------------------------------------------------------------------
   You do not need to be a programmer to customize this. Almost everything you
   would change lives in the labeled data tables just below (GF_DEPTS,
   LOCKED_FUNDS, REVENUE, DEDICATED_RATES, SCENARIOS, DEMO). Each table is a
   list of rows; each row is a set of "field: value" pairs. Change the text
   between quotation marks, or the number after a colon, then save and reload.

   Two labels keep us honest, and one applies to every figure:
     • OFFICIAL — verified against the City of Boulder's adopted budget or
                  Colorado law. Safe to publish as written.
     • MODELED  — a placeholder estimate so the tool works end to end. Replace
                  it with the city's real line-item figure before publishing.

   WHAT EACH TABLE CONTROLS
     GF_DEPTS         General Fund departments (the sliders). `amount` is the
                      2026 budget in $millions.            [MODELED — see #2]
     LOCKED_FUNDS     The capital budget plus dedicated/enterprise funds you
                      can move but whose savings stay trapped. `amount` in
                      $millions; sums to $326.5M.          [see #2]
     REVENUE          The revenue sliders, tagged by Colorado legal status and a
                      "modeled yield" tag. Yields are MODELED.   [see #3 and #4]
     DEDICATED_RATES  Voter-set sales-tax rates shown frozen, with the
                      approximate annual revenue each raises. [MODELED rev — #3]
     SCENARIOS        The gap to close. 2026 is OFFICIAL; downturn is MODELED.
     DEMO             The optional reader survey (adapted from the 2025 BVCP
                      survey).

   WHAT GETS STORED WHEN A READER SUBMITS — AND WHERE
     One flat record per submission: every slider's position (including the
     ones left at zero — so each row is a complete budget), the revenue and
     reserves settings, a few derived totals, and one column per survey answer.
     Field names match the database columns in ARCHITECTURE.md one-to-one.
     ALL of it — the budget AND the survey answers — is stored in Boulder
     Reporting Lab's own Supabase database (Postgres), written either directly
     with a browser-safe publishable key or through a small Vercel function. No
     advertising or analytics third party ever receives a response. No name,
     account, email, IP address, or browser fingerprint is stored with a record
     (a salted one-way hash may be kept to flag duplicate submissions; see
     ARCHITECTURE.md).

   ADDING A NEWS CITATION (the [1], [2] links next to a row)
     Add a `sources` field to any row, e.g.:
         sources: [SRC.budget2026, SRC.policing2023]
     Define each link once in the SRC table below (a label and a URL) and reuse
     it anywhere. Prefer the most recent relevant coverage as the first cite;
     older but on-topic pieces are fine as a secondary cite. Only a few rows are
     filled in here as a demonstration — add more as you report them, and
     confirm each link still resolves (#6).

   FACT-CHECK BEFORE DEPLOYMENT — replace every MODELED figure
     1. Control totals (TOTAL / OPERATING / CAPITAL / GENERAL_FUND and the
        $7.5M gap): OFFICIAL. Source: City of Boulder 2026 Approved Budget
        (OpenGov "Budget in Brief") and the City Manager's budget message,
        Aug. 29, 2025.
     2. Per-department and per-fund `amount`s: MODELED. Replace from the OpenGov
        Budget Book → "Department Budgets" and "Fund Financials" pages. (They
        should sum back to GENERAL_FUND and to OPERATING.)
     3. Sales-tax rates and the dollars they raise (DEDICATED_RATES `rate` and
        `revM`, and the fee/property/sales yields in REVENUE): verify rates on
        the city's "Tax Rates & Types" page; verify dollars against the
        Budget-in-Brief "Sources & Uses Supplemental," which lists sales-tax
        revenue by fund. The `revM` figures here are modeled from each rate's
        share of ~$180M in annual city sales-tax revenue.
     4. Legal framing (TABOR vote requirement; the local-income-tax bar;
        fees-are-not-taxes): OFFICIAL. Source: Colorado Legislative Council
        Staff and Colo. Const. Art. X, §20 (TABOR).
     5. The four 2026 fee figures (parking, speed cameras, transportation
        maintenance fee, single-family expansion fee): OFFICIAL. Source: the
        city budget message, Aug. 29, 2025.
     6. News citations in the SRC table: confirm each URL still loads and still
        supports the row it sits next to.
     7. The locked list includes a $113.3M "Capital budget" row, so LOCKED_FUNDS
        sums to TOTAL − GENERAL_FUND = $326.5M, matching the section heading.
        If you change any amount, re-check that the locked rows still sum to it.
     8. Hand-maintained prose figures (NOT pulled from the constants): the "$521
        million" headline, "3.86%", "56%", "−7.8%", and the "$2.25M / $0.4M"
        born-locked fees are written into the copy. The headline GAP now reads
        from SCENARIOS, but these others do not — update them by hand (search the
        file for each) when the underlying numbers change.

   DEPLOYMENT KNOBS (just below)
     ENDPOINT      — optional Vercel pipeline base (…/api). Set it via ?api= on
                     the embed URL or window.__BBW_ENDPOINT__ to route writes
                     through the server (keeps the secret key server-side).
     SUPABASE_URL  — the project and its browser-safe PUBLISHABLE key, used to
       /_KEY         write straight to Supabase when no ENDPOINT is set.
     SRC           — the citation-link table.
     See ARCHITECTURE.md for setup, the data dictionary, and Newspack embedding.

   This is a teaching model, not the city's budgeting system. Visual identity
   matches BRL's Newspack theme (Public Sans; #CDDE00 / #3A8DDE).

   DESIGN — FRAMING LIVES IN THE COLUMN
     This widget is built to sit inside the column's prose, which carries the
     hook, the peg (the Nov. 2026 ballot / 2027 budget cycle), and the
     diagnostic close. So the widget's own copy is deliberately lean: a short
     title, one-line instructions, the legal tags, point-of-use caveats, and a
     "Sources & method" block with the verify-me link. If you ever embed this
     standalone (no surrounding article), restore a sentence or two of framing
     at the top and a closing thought at the bottom — otherwise it will read as
     an interaction with no argument around it.
   ========================================================================== */

/* ---- BACKEND CONFIG ------------------------------------------------------
   Where reader submissions go, resolved in priority order at runtime:
     1. ENDPOINT — a Vercel pipeline base (…/api). Most private: the secret key
        stays server-side and submissions are de-duplicated there. Set it with
        ?api= on the embed URL, window.__BBW_ENDPOINT__, or by editing below.
     2. SUPABASE_URL + SUPABASE_KEY — write straight to Supabase from the browser
        with the PUBLISHABLE key (safe to publish; Row Level Security lets a
        reader add a row but never read one back). Works with no server at all.
     3. Neither — preview mode: the tally lives only in this browser session.
   See ARCHITECTURE.md for the full data flow, schema, and privacy model. ----- */
// Offline/preview builds (build-standalone.sh) set window.__BBW_PREVIEW__ to
// keep submissions in the browser session only, so a local review copy never
// writes to the live database. Production embeds leave it unset.
const PREVIEW = typeof window !== "undefined" && window.__BBW_PREVIEW__ === true;

function resolveEndpoint() {
  if (PREVIEW || typeof window === "undefined") return "";
  try {
    if (window.__BBW_ENDPOINT__) return String(window.__BBW_ENDPOINT__);
    const q = new URLSearchParams(window.location.search).get("api");
    if (q) return q;
  } catch {}
  return "";
}
const ENDPOINT = resolveEndpoint();

// Supabase direct-write fallback. The PUBLISHABLE key is browser-safe by design
// (RLS is the real guard), so committing it is expected. The SECRET key is
// never used here — only server-side, in the Vercel pipeline.
const SUPABASE_URL = "https://iplcjxbazezpjdzdpjxx.supabase.co";
const SUPABASE_KEY = "sb_publishable_2jy9CF17cyHSMAnVYSpFcA_tRecRIoi";
const SB_ENABLED = !PREVIEW && !!SUPABASE_URL && !!SUPABASE_KEY;

// Optional cached aggregate-read URL (the edge-cached Vercel /api/aggregate
// route). When set, the on-load tally READ goes through a CDN while writes stay
// direct to Supabase — so a traffic spike can't dogpile the database. Set via
// window.__BBW_AGG__ or ?agg= on the embed URL.
function resolveAggEndpoint() {
  if (PREVIEW || typeof window === "undefined") return "";
  try {
    if (window.__BBW_AGG__) return String(window.__BBW_AGG__);
    const q = new URLSearchParams(window.location.search).get("agg");
    if (q) return q;
  } catch {}
  return "";
}
const AGG_ENDPOINT = resolveAggEndpoint();

const AGG_KEY = "boulder_budget_agg_v4";

/* ---- SRC: news-citation links. Define each link once (label + url), then
   reference it by name in any data row's `sources` field, e.g.
   sources: [SRC.ballot2026, SRC.policing2023]  (recent first, older second).
   A few rows below are filled in to demonstrate.
   Before publishing, confirm every URL still loads (fact-check #6). --------- */
const SRC = {
  ballot2026:   { label: "BRL — Council eyes 2026 ballot: vacant-home tax, property-tax increases, debt for facilities (May 2026)",
                  url: "https://boulderreportinglab.org/2026/05/15/boulder-considers-november-2026-ballot-measures-on-vacant-home-tax-property-tax-increases-and-debt-for-underfunded-facilities/" },
  vacancy2026:  { label: "BRL — Council advances vacant-home tax and other potential 2026 ballot measures (Mar. 2026)",
                  url: "https://boulderreportinglab.org/2026/03/12/boulder-advances-vacant-home-tax-other-potential-2026-ballot-measures/" },
  strain2025:   { label: "BRL — Boulder braces for budget strain as revenue slows and federal funds hang in limbo (May 2025)",
                  url: "https://boulderreportinglab.org/2025/05/08/boulder-braces-for-budget-strain-as-revenue-slows-and-federal-funds-hang-in-limbo/" },
  budget2026:   { label: "BRL — Council approves $521M 2026 budget with cuts and new fees (Oct. 2025)",
                  url: "https://boulderreportinglab.org/2025/10/09/boulder-city-council-approves-521-million-2026-budget-with-new-fees-and-cuts/" },
  salesTax2025: { label: "BRL — Voters make CCRS permanent; approve open-space and mental-health taxes (Nov. 2025)",
                  url: "https://boulderreportinglab.org/2025/11/04/boulder-voters-approve-sales-taxes-to-fund-capital-projects-mental-health-services-and-open-space/" },
  housing2025:  { label: "BRL — Housing affordability crisis deepens as homes are torn down and rebuilt (Apr. 2025)",
                  url: "https://boulderreportinglab.org/2025/04/06/boulders-housing-affordability-crisis-deepens-as-older-homes-are-torn-down-and-rebuilt-new-study-finds/" },
  // Older but on-topic — use as a SECONDARY cite, after a more recent one.
  policing2023: { label: "BRL — Budget shifts toward housing and human services over policing (Sep. 2023)",
                  url: "https://boulderreportinglab.org/2023/09/13/budget-2024-in-a-shift-city-of-boulder-may-soon-invest-more-in-housing-and-human-services-than-policing/" },
};

const C = {
  lime: "#CDDE00", limeDk: "#AFC000", limeTint: "#FAFAE1",
  blue: "#3A8DDE", blueDk: "#1265B6",
  ink: "#1A1A1A", inkSoft: "#5A5A5A",
  hair: "#E1E1E1", paper: "#FFFFFF", wash: "#F7F7F4",
  lock: "#7E847E", lockText: "#5A5F5A", lockBg: "#EFEFEC",
  red: "#CF2E2E", green: "#1F7A4D",
};
const FONT = "'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif";

const fmt = (m) => { const v = Math.abs(m); const s = v >= 100 ? v.toFixed(0) : v.toFixed(1); return `${m < 0 ? "−" : ""}$${s}M`; };
const signed = (m) => `${m < 0 ? "−" : "+"}$${Math.abs(m) >= 100 ? Math.abs(m).toFixed(0) : Math.abs(m).toFixed(1)}M`;

/* ---- OFFICIAL control totals ($M) ---------------------------------------- */
const TOTAL = 521.0, OPERATING = 407.68, CAPITAL = 113.3, GENERAL_FUND = 194.5;

/* ---- GF_DEPTS: General Fund departments, shown as sliders.
   id      machine name (don't translate; used as a data key)
   name    label the reader sees
   amount  2026 budget in $millions   [MODELED — replace from the Budget Book,
           fact-check #2; the column should sum to GENERAL_FUND = 194.5]
   note    optional gray sub-label
   sources optional [n] citation links (see SRC). A few are filled in to demo. */
const GF_DEPTS = [
  { id: "police", name: "Police", amount: 48.0, sources: [SRC.budget2026, SRC.policing2023] },
  { id: "fire", name: "Fire-Rescue", amount: 30.0, sources: [SRC.budget2026] },
  { id: "genadmin", name: "General government & admin", amount: 30.0, note: "Council, Manager, Attorney, Finance, HR, Comms, Municipal Court, IT" },
  { id: "transfers", name: "Transfers, debt & non-departmental", amount: 24.5 },
  { id: "parksrec", name: "Parks & Recreation (GF share)", amount: 18.0, sources: [SRC.ballot2026, SRC.budget2026] },
  { id: "hhs", name: "Housing & Human Services (GF)", amount: 14.0, sources: [SRC.housing2025, SRC.policing2023] },
  { id: "library", name: "Library & Arts", amount: 12.0 },
  { id: "facilities", name: "Facilities, Fleet & Public Works (GF)", amount: 10.0 },
  { id: "planning", name: "Planning & Development (GF share)", amount: 8.0 },
];

/* ---- LOCKED_FUNDS: dedicated (voter) or restricted (law) funds, plus the
   capital budget. You can move a slider, but the savings stay trapped in the
   fund and never reach the General Fund gap — that is the lesson.
   The rows sum to TOTAL − GENERAL_FUND = $326.5M (the "locked" share).
   amount  2026 budget in $millions   [capital row OFFICIAL; the rest MODELED —
           fact-check #2]
   kind    "capital" | "enterprise" | "dedicated" | "internal" (the small tag)
   why     one line explaining the restriction
   sources optional [n] links. A few are filled in to demo. ----------------- */
const LOCKED_FUNDS = [
  { id: "capital", name: "Capital budget (all funds)", amount: 113.3, kind: "capital", why: "Construction and infrastructure, much of it CCRS- and bond-funded; project dollars can’t pay for operations.", sources: [SRC.budget2026] },
  { id: "water", name: "Water Utility", amount: 34.0, kind: "enterprise", why: "Self-supporting from water rates; water system only." },
  { id: "openspace", name: "Open Space & Mountain Parks", amount: 28.0, kind: "dedicated", why: "Voter-dedicated sales tax; open space only.", sources: [SRC.salesTax2025, SRC.budget2026] },
  { id: "transpo", name: "Transportation", amount: 27.0, kind: "dedicated", why: "Dedicated transportation tax; roads, transit, paths only." },
  { id: "wastewater", name: "Wastewater Utility", amount: 23.0, kind: "enterprise", why: "Self-supporting from sewer rates." },
  { id: "internal", name: "Internal service & other", amount: 26.2, kind: "internal", why: "Fleet, technology, insurance and debt charged back to departments." },
  { id: "stormwater", name: "Stormwater & Flood Utility", amount: 12.0, kind: "enterprise", why: "Self-supporting from stormwater fees." },
  { id: "parkstax", name: ".25-Cent Sales Tax (Parks & Rec)", amount: 11.0, kind: "dedicated", why: "Voter-dedicated to parks and recreation." },
  { id: "ahf", name: "Affordable Housing & CHAP", amount: 11.0, kind: "dedicated", why: "Dedicated to affordable-housing programs.", sources: [SRC.housing2025] },
  { id: "recact", name: "Recreation Activity", amount: 10.0, kind: "enterprise", why: "Recovers cost from rec-program fees." },
  { id: "climate", name: "Climate Tax", amount: 9.0, kind: "dedicated", why: "Voter climate tax; climate work only." },
  { id: "pds", name: "Planning & Development (fees)", amount: 8.0, kind: "enterprise", why: "Development-review fees fund development review." },
  { id: "ssb", name: "Sugar-Sweetened Beverage Tax", amount: 5.0, kind: "dedicated", why: "Health-program use set by ordinance." },
  { id: "ccrs", name: "CCRS capital tax (operating)", amount: 3.0, kind: "dedicated", why: "0.3% capital tax; capital only; permanent since 2025.", sources: [SRC.salesTax2025] },
  { id: "arts", name: "Arts, Culture & Heritage", amount: 2.5, kind: "dedicated", why: "Dedicated to arts and culture." },
  { id: "evict", name: "Eviction Prevention / Rental Asst.", amount: 2.0, kind: "dedicated", why: "Dedicated to eviction prevention." },
  { id: "airport", name: "Airport", amount: 1.5, kind: "enterprise", why: "FAA grant-assurance restricted." },
];

/* ---- Revenue sliders, by Colorado legal status --------------------------- *
   status: city  = city may set without a vote (TABOR treats fees as non-taxes)
           vote  = requires voter approval under TABOR
           barred= prohibited by the Colorado Constitution (TABOR)
           none  = no legal mechanism exists                                  */
const REVENUE = [
  { id: "fees", label: "Fees & fines", status: "city", unit: "$M", min: 0, max: 8, step: 0.5, per: 1, modeled: true,
    note: "Courts treat fees as non-taxes, so the city can raise many without a vote — but many are capped to the cost of the service. Real 2026 examples: +50¢ parking ≈ $0.8M, speed-on-green cameras ≈ $2.6M." },
  { id: "property", label: "Property tax (mill levy)", status: "vote", unit: "mills", min: 0, max: 4, step: 0.25, per: 1.5, modeled: true,
    note: "A mill-levy increase needs voter approval under TABOR. The legislature sets assessment rates, and recent state law caps annual growth. (≈ $1.5M per mill, modeled.)" },
  { id: "sales", label: "General sales tax", status: "vote", unit: "%", min: 0, max: 0.5, step: 0.05, per: 46, modeled: true,
    note: "Any increase needs voter approval under TABOR. Boulder’s city rate is already 3.86%, among Colorado’s highest. (≈ $4.6M per 0.1%, modeled.)" },
  { id: "income", label: "Local income tax", status: "barred", locked: true,
    note: "Colorado’s TABOR (Const. Art. X, §20) prohibits local income taxes outright. There is no rate to set." },
  { id: "wealth", label: "Wealth tax", status: "none", locked: true,
    note: "No Colorado city has authority to levy a wealth tax, and any new tax would still require a public vote. Shown to mark the edge of the toolbox." },
];

const STATUS = {
  city: { tag: "CITY CAN SET", color: "#1A1A1A", bg: "#CDDE00" },
  vote: { tag: "REQUIRES A VOTE · TABOR", color: "#1265B6", bg: "transparent" },
  barred: { tag: "BARRED BY THE CONSTITUTION", color: "#CF2E2E", bg: "transparent" },
  none: { tag: "NO LEGAL MECHANISM", color: "#7E847E", bg: "transparent" },
};

/* ---- DEDICATED_RATES: the sales-tax rates voters froze, shown as locked
   sliders. The council cannot move these.
   rate  the rate, as a % of the city's 3.86% total sales tax     [OFFICIAL]
   revM  approximate annual revenue it raises, in $millions       [MODELED #3 —
         modeled from the rate's share of ~$180M in city sales-tax revenue;
         verify against the Budget-in-Brief "Sources & Uses Supplemental"]
   note  context shown beneath the (disabled) slider
   sources optional [n] links. ---------------------------------------------- */
const DEDICATED_RATES = [
  { id: "cc", label: "CCRS capital tax", rate: 0.30, revM: 14, note: "Made permanent by voters, Nov. 2025.", sources: [SRC.salesTax2025] },
  { id: "os", label: "Open Space tax", rate: 0.33, revM: 15, note: "Voter-dedicated; a portion shifts to the General Fund in 2035.", sources: [SRC.salesTax2025] },
  { id: "pr", label: ".25-cent Parks & Rec tax", rate: 0.25, revM: 12, note: "Voter-dedicated; expires 2036 unless renewed.", sources: [SRC.ballot2026] },
  { id: "tr", label: "Transportation tax", rate: 0.15, revM: 7, note: "Approved 2014, renewed 2019; shifts to the General Fund in 2030." },
];

const SCENARIOS = {
  y2026: { id: "y2026", label: "2026 (adopted)", gap: 7.5, blurb: "The shortfall the city actually closed for 2026, as sales-tax revenue flattened." },
  y2027: { id: "y2027", label: "2027 (projected)", gap: 18.0, blurb: "A deeper, modeled gap if sales-tax receipts keep sliding into 2027 — the structural test." },
};

/* ---- DEMO: optional reader survey. Adapted from the 2025 BVCP survey; some
   brackets are expanded and two questions were added, so not every item maps
   1:1 to the city's survey (years, employment, building, tenure, race, gender,
   LGBTQ still match). Every row keeps "Prefer not to say"; one answer (any of
   them) is required to submit. t: "single" = pick one, "multi" = select all. - */
const DEMO = [
  { id: "years", t: "single", q: "How many years have you lived in the Boulder Valley?",
    o: ["5 years or less", "6-10 years", "11-20 years", "More than 20 years", "Prefer not to say"] },
  { id: "employment", t: "single", q: "What is your employment status?",
    o: ["Working full time for pay", "Working part time for pay", "Unemployed, looking for paid work", "Not retired, not looking for paid work", "Fully retired", "Prefer not to say"] },
  { id: "workArea", t: "single", q: "Do you work in the Boulder Valley area?",
    o: ["Yes, outside the home", "Yes, from home", "No, I work outside the Boulder Valley", "No, I stay at home or am retired", "No, I'm unemployed", "Prefer not to say"] },
  { id: "student", t: "single", q: "Are you a student at CU Boulder or any other college or university?",
    o: ["Yes, an undergraduate student", "Yes, a graduate student", "No", "Prefer not to say"] },
  { id: "education", t: "single", q: "What is the highest level of education you have finished?",
    o: ["No high school diploma", "High school diploma", "GED", "Some college, no degree", "Associate degree", "Bachelor's degree", "Master's degree", "Professional degree (MD, JD, DDS)", "Doctoral degree (PhD, EdD)", "Prefer not to say"] },
  { id: "building", t: "single", q: "Which best describes the building you live in?",
    o: ["Single-unit house detached from any other houses", "Building with two or more homes (duplex, townhome, apartment or condominium)", "Manufactured home", "Other", "Prefer not to say"] },
  { id: "tenure", t: "single", q: "Do you own or rent your home?",
    o: ["Own", "Rent", "Other", "Prefer not to say"] },
  { id: "income", t: "single", q: "How would you describe your annual household income?",
    o: ["Less than $25,000 per year", "$25,000 to $49,999 per year", "$50,000 to $99,999 a year", "$100,000 to $149,999 a year", "$150,000 to $299,999 a year", "$300,000 a year or more", "Prefer not to say"] },
  { id: "age", t: "single", q: "What is your age range?",
    o: ["18-24", "25-34", "35-44", "45-54", "55-64", "65 and over", "Prefer not to say"] },
  { id: "race", t: "multi", q: "Which race(s) and/or ethnic group(s) do you most identify with? Select all that apply.",
    o: ["American Indian or Alaskan Native", "Asian", "Black or African American", "Latine/Latinx/Hispanic", "Middle Eastern or North African", "Native Hawaiian or Pacific Islander", "White", "Other", "Prefer not to say"] },
  { id: "gender", t: "single", q: "What is your gender?",
    o: ["Woman", "Man", "Non-binary/Genderqueer", "Prefer to self-describe", "Prefer not to say"] },
  { id: "lgbtq", t: "single", q: "Are you a member of the LGBTQ+ community?",
    o: ["Yes", "No", "Prefer not to say"] },
  { id: "disability", t: "single", q: "Do you have a disability?",
    o: ["Yes — visible", "Yes — invisible", "Yes — visible and invisible", "No", "Prefer not to say"] },
];

export default function BoulderBudgetWidget() {
  const [deptPct, setDeptPct] = useState({});      // id -> -25..25
  const [lockedPct, setLockedPct] = useState({});  // id -> -25..25
  const [rev, setRev] = useState({ fees: 0, property: 0, sales: 0 });
  const [reserves, setReserves] = useState(0);
  const [showLocked, setShowLocked] = useState(false);
  const [showData, setShowData] = useState(false);
  const [showDemo, setShowDemo] = useState(true);
  const [demo, setDemo] = useState({});
  const [agg, setAgg] = useState(null);
  const [aggState, setAggState] = useState("loading");
  const [submitted, setSubmitted] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    const send = () => { try { window.parent?.postMessage({ type: "boulder-budget:height", height: document.documentElement.scrollHeight }, "*"); } catch {} };
    send(); const ro = new ResizeObserver(send); if (rootRef.current) ro.observe(document.body);
    window.addEventListener("load", send);
    return () => { ro.disconnect(); window.removeEventListener("load", send); };
  }, []);

  /* derived math — spending change is signed (+ = more spending = worse gap) */
  const netSpendChange = useMemo(() => GF_DEPTS.reduce((s, d) => s + d.amount * ((deptPct[d.id] || 0) / 100), 0), [deptPct]);
  const netCuts = Math.max(0, -netSpendChange);
  const revenueOnly = useMemo(() => REVENUE.reduce((s, r) => s + (r.locked ? 0 : (rev[r.id] || 0) * r.per), 0), [rev]); // new taxes/fees, not reserves
  const totalRevenue = revenueOnly + reserves; // both help close the gap, but only revenueOnly is structural
  const trappedChange = useMemo(() => LOCKED_FUNDS.reduce((s, f) => s + f.amount * ((lockedPct[f.id] || 0) / 100), 0), [lockedPct]);

  // Two tests. Both years are scored from the SAME slider choices. One-time
  // reserves close the 2026 gap but cannot carry into the 2027 projection, so
  // 2027 is the structural test: it counts cuts and recurring revenue only.
  const fix2026 = netCuts + totalRevenue;            // cuts + recurring revenue + one-time reserves
  const fix2027 = netCuts + revenueOnly;             // reserves excluded — structural only
  const remaining2026 = SCENARIOS.y2026.gap + netSpendChange - totalRevenue;
  const remaining2027 = SCENARIOS.y2027.gap + netSpendChange - revenueOnly;
  const balanced2026 = remaining2026 <= 0.05;
  const balanced2027 = remaining2027 <= 0.05;
  const balanced = balanced2026 && balanced2027;     // must pass BOTH to submit
  const remainingGap = Math.max(remaining2026, remaining2027); // the binding test
  const surplus = -remainingGap;
  const lockedTotal = TOTAL - GENERAL_FUND;
  const pctMovable = (GENERAL_FUND / TOTAL) * 100;
  const usedRevenue = revenueOnly > 0.01;
  const usedVote = (rev.sales || 0) > 0 || (rev.property || 0) > 0;
  const totalFix = totalRevenue + netCuts;

  useEffect(() => { let alive = true; (async () => { const a = await readAgg(); if (alive) { setAgg(a || emptyAgg()); setAggState("ready"); } })(); return () => { alive = false; }; }, []);

  const submit = useCallback(async () => {
    const answered = Object.values(demo).filter((v) => (Array.isArray(v) ? v.length : v)).length;
    if (!balanced || submitted || answered === 0) return;
    const topCut = GF_DEPTS.map((d) => ({ name: d.name, amt: -d.amount * ((deptPct[d.id] || 0) / 100) })).sort((a, b) => b.amt - a.amt)[0];
    const revShare = totalFix > 0 ? totalRevenue / totalFix : 0;
    /* FLAT PAYLOAD — one field per slider, zeros included, so the database
       stores every reader's complete budget, not just what they changed.
       Field names match the columns in ARCHITECTURE.md one-to-one:
         gf_<id>    General Fund slider, −25..25 (% change)
         fund_<id>  locked-fund slider, −25..25 (% change; includes capital)
         rev_*      revenue sliders in their native units; reserves in $M
         demo_<id>  one column per survey item (multi-selects joined by "; ") */
    const payload = { v: 4, ts: new Date().toISOString(), scenario: "dual" };
    GF_DEPTS.forEach((d) => { payload[`gf_${d.id}`] = deptPct[d.id] || 0; });
    LOCKED_FUNDS.forEach((f) => { payload[`fund_${f.id}`] = lockedPct[f.id] || 0; });
    payload.rev_fees = rev.fees || 0;          // $M
    payload.rev_property = rev.property || 0;  // mills
    payload.rev_sales = rev.sales || 0;        // percentage points
    payload.reserves = reserves;               // $M, one-time
    payload.spend_change = round(netSpendChange);
    payload.revenue_total = round(totalRevenue);
    payload.revenue_only = round(revenueOnly);
    payload.used_vote = usedVote;
    payload.used_revenue = usedRevenue;
    payload.used_reserves = reserves > 0;
    payload.top_cut = topCut && topCut.amt > 0.01 ? topCut.name : null;
    DEMO.forEach((q) => { const v = demo[q.id]; payload[`demo_${q.id}`] = Array.isArray(v) ? v.join("; ") : (v ?? null); });

    const next = await writeAgg({ revShare, usedRevenue, usedVote, usedReserves: reserves > 0, topCut, payload });
    if (next) setAgg(next);
    setSubmitted(true);
  }, [balanced, submitted, deptPct, lockedPct, rev, reserves, netSpendChange, totalRevenue, revenueOnly, usedRevenue, usedVote, totalFix, demo]);

  const reset = () => { setDeptPct({}); setLockedPct({}); setRev({ fees: 0, property: 0, sales: 0 }); setReserves(0); setDemo({}); setSubmitted(false); };
  const demoCount = Object.values(demo).filter((v) => (Array.isArray(v) ? v.length : v)).length;
  const canSubmit = balanced && !submitted && demoCount > 0;

  return (
    <div ref={rootRef} style={{ background: C.paper, color: C.ink, fontFamily: FONT }} className="w-full">
      <style>{`
        @media (prefers-reduced-motion: reduce){ *{transition:none!important;animation:none!important} }
        .bbw{ font-family:${FONT}; }
        .bbw input[type=range]{ -webkit-appearance:none; appearance:none; height:5px; border-radius:99px; background:${C.hair}; outline:none; width:100%; }
        .bbw input[type=range]::-webkit-slider-thumb{ -webkit-appearance:none; appearance:none; width:20px;height:20px;border-radius:50%;background:${C.lime};cursor:pointer;border:2px solid ${C.ink}; }
        .bbw input[type=range]::-moz-range-thumb{ width:20px;height:20px;border-radius:50%;background:${C.lime};cursor:pointer;border:2px solid ${C.ink}; }
        .bbw input[type=range].lk{ background:${C.lockBg}; }
        .bbw input[type=range].lk::-webkit-slider-thumb{ background:${C.lockBg}; border-color:${C.lock}; cursor:not-allowed; }
        .bbw input[type=range].lk::-moz-range-thumb{ background:${C.lockBg}; border-color:${C.lock}; cursor:not-allowed; }
        .bbw input[type=range].lk{ cursor:not-allowed; }
        .bbw input[type=range][readonly]{ cursor:not-allowed; }
        .bbw input[type=range]:focus-visible{ outline:2px solid ${C.blueDk}; outline-offset:3px; }
        .bbw button:focus-visible, .bbw a:focus-visible{ outline:2px solid ${C.blueDk}; outline-offset:2px; }
        .bbw .tnum{ font-variant-numeric: tabular-nums; }
        .bbw .scale{ display:flex; justify-content:space-between; font-size:11.5px; color:${C.inkSoft}; margin-top:4px; }
      `}</style>

      <div className="bbw mx-auto" style={{ maxWidth: 680, padding: "8px 16px 56px" }}>

        <header className="pt-6 pb-5" style={{ borderBottom: `3px solid ${C.lime}` }}>
          <div className="tnum" style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: C.blueDk, fontWeight: 800 }}>Charting Boulder · Interactive</div>
          <h1 style={{ fontSize: "clamp(23px,5.6vw,32px)", fontWeight: 800, lineHeight: 1.08, marginTop: 8, letterSpacing: "-0.02em" }}>Balance Boulder’s 2026 budget</h1>
          <p style={{ fontSize: 15.5, lineHeight: 1.5, color: C.inkSoft, marginTop: 10 }}>
            Close the <strong style={{ color: C.ink }}>{fmt(SCENARIOS.y2026.gap)} General Fund gap</strong> by cutting spending or raising revenue. The catch is what you’re allowed to touch — and what Colorado law won’t let you.
          </p>
        </header>

        {/* Reveal bar */}
        <section className="mt-6">
          <Eyebrow>Where the $521 million sits</Eyebrow>
          <div className="mt-2 rounded-md overflow-hidden flex" style={{ height: 44, border: `1px solid ${C.ink}` }}>
            <div style={{ width: `${pctMovable}%`, background: C.lime, color: C.ink }} className="flex items-center justify-center"><span style={{ fontSize: 12, fontWeight: 800 }}>{pctMovable.toFixed(0)}¢ movable</span></div>
            <div style={{ width: `${100 - pctMovable}%`, background: C.lockBg, color: C.inkSoft }} className="flex items-center justify-center gap-1"><Lock size={12} /><span style={{ fontSize: 11.5, fontWeight: 700 }}>{(100 - pctMovable).toFixed(0)}¢ locked</span></div>
          </div>
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 8 }}>About <strong style={{ color: C.ink }}>{pctMovable.toFixed(0)}¢ of every budget dollar</strong> sits in the General Fund ({fmt(GENERAL_FUND)}), the only large pot the council can freely redirect. The other {fmt(lockedTotal)} is dedicated by voters or restricted by law.</p>
        </section>

        {/* Scenario + live balance */}
        <section className="mt-6 rounded-lg p-4" style={{ background: C.limeTint, border: `1px solid ${C.hair}` }}>
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div style={{ minWidth: 0 }}>
              <Eyebrow>Two tests — your budget must pass both</Eyebrow>
              <p style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 6, maxWidth: 380 }}>Balance the gap the city closed for 2026 <em>and</em> the deeper gap projected for 2027. One-time reserves count toward 2026 but can’t carry into 2027 — that bar is the structural test.</p>
            </div>
            <div className="text-right" style={{ flex: "0 0 auto" }}>
              <div className="tnum" style={{ fontSize: 26, fontWeight: 800, lineHeight: 1, color: balanced ? C.green : C.red }}>{balanced ? "Both passed" : `${[balanced2026, balanced2027].filter(Boolean).length} of 2`}</div>
              <div style={{ fontSize: 12, color: C.inkSoft, marginTop: 3 }}>{netSpendChange === 0 ? "no spending change" : `${signed(netSpendChange)} spending`} · {fmt(revenueOnly)} revenue{reserves > 0 ? ` · ${fmt(reserves)} reserves` : ""}</div>
            </div>
          </div>
          <div className="mt-3">
            <GapBar label="2026 (adopted)" sub="reserves allowed" gap={SCENARIOS.y2026.gap} remaining={remaining2026} balanced={balanced2026} />
            <GapBar label="2027 (projected)" sub="structural · reserves don’t carry" gap={SCENARIOS.y2027.gap} remaining={remaining2027} balanced={balanced2027} />
          </div>
        </section>

        {/* General Fund — bidirectional */}
        <section className="mt-7">
          <SectionHead icon={<Building2 size={18} style={{ color: C.ink }} />} title="The General Fund — what you can actually move" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>{fmt(GENERAL_FUND)} of discretionary money. Slide left to cut a department, right to spend more. Cuts close the gap; new spending widens it.</p>
          <div className="mt-3 grid gap-2.5">
            {GF_DEPTS.map((d) => {
              const pct = deptPct[d.id] || 0, delta = d.amount * (pct / 100);
              return (
                <div key={d.id} className="rounded-md p-3" style={{ background: C.paper, border: `1px solid ${C.hair}` }}>
                  <div className="flex items-center justify-between gap-2">
                    <div style={{ minWidth: 0 }}><div style={{ fontSize: 14.5, fontWeight: 700 }}>{d.name}<Cites sources={d.sources} /></div>{d.note && <div style={{ fontSize: 11.5, color: C.inkSoft }}>{d.note}</div>}</div>
                    <div className="tnum text-right" style={{ flexShrink: 0 }}><span style={{ fontSize: 14, fontWeight: 800 }}>{fmt(d.amount)}</span><span style={{ fontSize: 12, color: pct === 0 ? C.inkSoft : C.blueDk, marginLeft: 8, fontWeight: 700 }}>{pct === 0 ? "unchanged" : signed(delta)}</span></div>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <input type="range" min={-25} max={25} step={1} value={pct} onChange={(e) => { setDeptPct({ ...deptPct, [d.id]: +e.target.value }); setSubmitted(false); }} aria-label={`Adjust ${d.name}`} aria-valuetext={pct === 0 ? "no change" : `${pct > 0 ? "increase" : "cut"} ${Math.abs(pct)} percent, ${signed(delta)}`} />
                    <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, textAlign: "right", fontWeight: 700 }}>{pct > 0 ? "+" : ""}{pct}%</span>
                  </div>
                  <div className="scale" aria-hidden="true"><span>−25% cut</span><span>0</span><span>+25% more</span></div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Revenue — sliders by legal status */}
        <section className="mt-7">
          <SectionHead icon={<Vote size={18} style={{ color: C.blueDk }} />} title="Raise revenue — within Colorado law" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>The city can set some fees on its own. Tax increases need a public vote under <strong style={{ color: C.blueDk }}>TABOR</strong>. And two tools are off the table entirely: Colorado bars a local income tax, and there’s no mechanism for a wealth tax.</p>
          <div className="mt-3 grid gap-2.5">
            {REVENUE.map((r) => {
              const st = STATUS[r.status]; const val = rev[r.id] || 0; const yield_ = r.locked ? 0 : val * r.per;
              return (
                <div key={r.id} className="rounded-md p-3" style={{ background: r.locked ? C.lockBg : C.paper, border: `1px solid ${r.locked ? C.lock : C.hair}` }}>
                  <div className="flex items-center justify-between gap-2">
                    <div style={{ minWidth: 0 }}>
                      <div className="flex items-center gap-1.5 flex-wrap"><span style={{ fontSize: 14.5, fontWeight: 700, color: r.locked ? C.inkSoft : C.ink }}>{r.label}</span>{r.locked && <Lock size={12} style={{ color: C.lock }} />}</div>
                      <div className="mt-1 flex flex-wrap gap-1"><Tag color={st.color} bg={st.bg}>{st.tag}</Tag>{r.modeled && <Tag color={C.lockText}>modeled yield</Tag>}</div>
                    </div>
                    <span className="tnum" style={{ fontSize: 14, fontWeight: 800, color: r.locked ? C.lockText : (yield_ > 0 ? C.green : C.inkSoft), flexShrink: 0 }}>{r.locked ? "—" : `+${fmt(yield_)}`}</span>
                  </div>
                  {r.locked ? (
                    <input className="lk" type="range" min={0} max={1} step={1} value={0} readOnly onChange={() => {}}
                      onKeyDown={(e) => e.preventDefault()} aria-readonly="true" aria-disabled="true"
                      aria-label={`${r.label}`} aria-valuetext={`unavailable — ${st.tag.toLowerCase()}`} style={{ marginTop: 10 }} />
                  ) : (
                    <>
                      <div className="flex items-center gap-3 mt-2">
                        <input type="range" min={r.min} max={r.max} step={r.step} value={val} onChange={(e) => { setRev({ ...rev, [r.id]: +e.target.value }); setSubmitted(false); }} aria-label={`Adjust ${r.label}`} aria-valuetext={`${val === 0 ? "none" : (r.unit === "$M" ? fmt(val) : `${val}${r.unit === "%" ? " percent" : " mills"}`)}, raises ${fmt(yield_)}`} />
                        <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 64, textAlign: "right", fontWeight: 700 }}>{r.unit === "$M" ? fmt(val) : `${val}${r.unit === "%" ? "%" : " mills"}`}</span>
                      </div>
                    </>
                  )}
                  <div style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 7 }}>{r.note}</div>
                </div>
              );
            })}
            <div className="rounded-md p-3" style={{ background: C.paper, border: `1px solid ${C.hair}` }}>
              <div className="flex items-center justify-between gap-2">
                <div><div style={{ fontSize: 14.5, fontWeight: 700 }}>Spend down one-time reserves</div><Tag color={C.red}>one-time — not a structural fix</Tag></div>
                <span className="tnum" style={{ fontSize: 14, fontWeight: 800, color: reserves ? C.green : C.inkSoft }}>+{fmt(reserves)}</span>
              </div>
              <input type="range" min={0} max={10} step={0.5} value={reserves} onChange={(e) => { setReserves(+e.target.value); setSubmitted(false); }} style={{ marginTop: 10 }} aria-label="Use reserves" />
            </div>
          </div>
        </section>

        {/* Locked-by-voters revenue */}
        <section className="mt-7">
          <SectionHead icon={<Lock size={18} style={{ color: C.lock }} />} title="Rates the voters froze" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>These rates were set at the ballot box. The council can’t slide them, cut them to plug the General Fund, or move them to a new priority. Annual revenue shown is approximate.</p>
          <div className="mt-3 grid gap-2">
            {DEDICATED_RATES.map((d) => (
              <div key={d.id} className="rounded-md p-3" style={{ background: C.lockBg, border: `1px solid ${C.lock}` }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap" style={{ minWidth: 0 }}><Lock size={12} style={{ color: C.lock }} /><span style={{ fontSize: 14, fontWeight: 700, color: C.inkSoft }}>{d.label}</span><Cites sources={d.sources} /><Tag color={C.blueDk}>voter-set</Tag></div>
                  <div className="tnum text-right" style={{ flexShrink: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 800, color: C.inkSoft }}>{d.rate.toFixed(2)}%</div>
                    {d.revM != null && <div style={{ fontSize: 12, fontWeight: 700, color: C.lockText }}>≈ {fmt(d.revM)}/yr</div>}
                  </div>
                </div>
                <input className="lk" type="range" min={0} max={0.5} step={0.01} value={d.rate} readOnly onChange={() => {}}
                  onKeyDown={(e) => e.preventDefault()} aria-readonly="true" aria-disabled="true"
                  aria-label={`${d.label}`} aria-valuetext={`${d.rate.toFixed(2)} percent, set by voters and not adjustable${d.revM != null ? `, about ${fmt(d.revM)} a year` : ""}`} style={{ marginTop: 10 }} />
                <div style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 6 }}>{d.note}</div>
              </div>
            ))}
          </div>
          <div className="mt-2 rounded-md p-3" style={{ background: C.limeTint, border: `1px dashed ${C.lock}` }}>
            <span style={{ fontSize: 12.5, color: C.inkSoft }}>New 2026 revenue that’s also born locked: transportation maintenance fee <strong style={{ color: C.ink }}>+$2.25M</strong> → transportation only · single-family expansion fee <strong style={{ color: C.ink }}>+$0.4M</strong> → affordable housing only.</span>
          </div>
        </section>

        {/* Locked spending funds */}
        <section className="mt-7">
          <button onClick={() => setShowLocked(!showLocked)} className="w-full flex items-center justify-between" style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}>
            <SectionHead icon={<Lock size={18} style={{ color: C.lock }} />} title={`The locked ${fmt(lockedTotal)} in spending — cut it, but it can’t leave`} />
            {showLocked ? <ChevronUp size={18} color={C.inkSoft} /> : <ChevronDown size={18} color={C.inkSoft} />}
          </button>
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>Includes the {fmt(113.3)} capital budget and every dedicated or fee-funded operating fund, down to small outlays like arts. Move them all you like: the savings stay locked inside each fund and can’t reach the General Fund gap.</p>
          {showLocked && (
            <div className="mt-3 grid gap-2">
              {LOCKED_FUNDS.map((f) => {
                const pct = lockedPct[f.id] || 0, delta = f.amount * (pct / 100);
                return (
                  <div key={f.id} className="rounded-md p-3" style={{ background: C.wash, border: `1px solid ${C.hair}` }}>
                    <div className="flex items-center justify-between gap-2">
                      <div style={{ minWidth: 0 }}><div className="flex items-center gap-1.5 flex-wrap"><span style={{ fontSize: 14, fontWeight: 700, color: C.inkSoft }}>{f.name}</span><Cites sources={f.sources} /><Tag color={f.kind === "capital" ? C.ink : f.kind === "enterprise" ? C.lock : C.blueDk}>{f.kind}</Tag></div><div style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 1 }}>{f.why}</div></div>
                      <div className="tnum text-right" style={{ flexShrink: 0 }}><span style={{ fontSize: 14, fontWeight: 800, color: C.inkSoft }}>{fmt(f.amount)}</span>{pct !== 0 && <div style={{ fontSize: 11, color: C.lockText, fontWeight: 700 }}>{signed(delta)} stays in fund</div>}</div>
                    </div>
                    <div className="flex items-center gap-3 mt-2">
                      <input className="lk" type="range" min={-25} max={25} step={1} value={pct} onChange={(e) => { setLockedPct({ ...lockedPct, [f.id]: +e.target.value }); setSubmitted(false); }} aria-label={`Adjust ${f.name}`} aria-valuetext={pct === 0 ? "no change" : `${pct > 0 ? "increase" : "cut"} ${Math.abs(pct)} percent; ${signed(delta)} stays in fund`} />
                      <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, textAlign: "right", fontWeight: 700 }}>{pct > 0 ? "+" : ""}{pct}%</span>
                    </div>
                  </div>
                );
              })}
              {Math.abs(trappedChange) > 0.05 && (
                <div className="rounded-md p-3 flex items-start gap-2" style={{ background: C.limeTint, border: `1px solid ${C.lock}` }}>
                  <AlertTriangle size={15} style={{ color: C.red, marginTop: 2, flexShrink: 0 }} />
                  <span style={{ fontSize: 13 }}>You’ve changed locked funds by <strong>{signed(trappedChange)}</strong>. None of it touches the General Fund gap — it stays inside each fund’s purpose.</span>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Submit + aggregate */}
        <section className="mt-7 rounded-lg p-4" style={{ background: C.wash, border: `1px solid ${C.hair}` }}>
          <div style={{ maxWidth: 540 }}>
            <Eyebrow>{balanced ? "You passed both tests" : "Keep going"}</Eyebrow>
            <p style={{ fontSize: 14, color: C.inkSoft, marginTop: 6 }}>
              {balanced
                ? <>Balanced for 2026 <em>and</em> the 2027 projection, with {netCuts > 0.01 ? <><strong style={{ color: C.ink }}>{fmt(netCuts)} in net cuts</strong>, </> : null}<strong style={{ color: C.ink }}>{fmt(revenueOnly)} in recurring revenue</strong>{reserves > 0 ? <> and <strong style={{ color: C.ink }}>{fmt(reserves)} from one-time reserves</strong></> : null}{usedVote ? <>, including measures that would need a public vote.</> : <>, without asking voters for anything.</>}</>
                : balanced2026
                  ? <>2026 balances, but the <strong style={{ color: C.ink }}>2027 projection is still {fmt(-remaining2027)} short</strong>. One-time reserves won’t carry over — close it with cuts or recurring revenue.</>
                  : <>You’re still {fmt(-remaining2026)} short for 2026{remaining2027 > remaining2026 ? <> and {fmt(-remaining2027)} short for 2027</> : null}. Cut deeper, raise a fee, or send a tax to the ballot.</>}
            </p>
          </div>

          {balanced && (
            <div className="mt-4 rounded-lg p-3" style={{ background: C.limeTint, border: `2px solid ${demoCount > 0 ? C.limeDk : C.ink}` }}>
              <div className="flex items-start justify-between gap-3">
                <div style={{ minWidth: 0 }}>
                  <div className="flex items-center gap-1.5"><Users size={15} style={{ color: C.ink }} /><span style={{ fontSize: 14.5, fontWeight: 800 }}>One step before you add your budget</span></div>
                  <div style={{ fontSize: 13, color: C.inkSoft, marginTop: 3 }}>Answer at least one — even <em>“Prefer not to say.”</em> Optional and confidential, and stored only on Boulder Reporting Lab’s own servers.</div>
                </div>
                <span className="tnum flex items-center gap-1" style={{ fontSize: 12, fontWeight: 800, flexShrink: 0, color: demoCount > 0 ? C.green : C.inkSoft }}>{demoCount > 0 && <Check size={13} />}{demoCount} answered</span>
              </div>
              <button onClick={() => setShowDemo(!showDemo)} className="flex items-center gap-1" style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, marginTop: 8, fontSize: 12, fontWeight: 800, color: C.blueDk }}>{showDemo ? <>Hide questions <ChevronUp size={13} /></> : <>Show questions <ChevronDown size={13} /></>}</button>
              {showDemo && (
                <div className="mt-3 grid gap-3">
                  <p style={{ fontSize: 11.5, color: C.inkSoft }}>These are adapted from the city’s 2025 Boulder Valley Comprehensive Plan survey. All optional and confidential, and stored only on Boulder Reporting Lab’s own servers.</p>
                  {DEMO.map((d) => <DemoQuestion key={d.id} d={d} value={demo[d.id]} onChange={(val) => setDemo({ ...demo, [d.id]: val })} />)}
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 mt-4">
            <button onClick={submit} disabled={!canSubmit} className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 800, padding: "10px 18px", borderRadius: 7, cursor: canSubmit ? "pointer" : "not-allowed", border: `2px solid ${canSubmit ? C.ink : C.hair}`, background: canSubmit ? C.lime : C.hair, color: canSubmit ? C.ink : C.inkSoft }}><ArrowDownToLine size={14} /> {submitted ? "Added to the tally" : "Add my budget"}</button>
            <button onClick={reset} className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 700, padding: "10px 14px", borderRadius: 7, cursor: "pointer", border: `1.5px solid ${C.hair}`, background: C.paper, color: C.inkSoft }}><RotateCcw size={14} /> Reset</button>
            {balanced && !submitted && demoCount === 0 && <span style={{ fontSize: 12.5, color: C.blueDk, fontWeight: 700 }}>Pick at least one answer above to add your budget.</span>}
            {submitted && <span className="flex items-center gap-1" style={{ fontSize: 12.5, color: C.green, fontWeight: 700 }}><Check size={14} /> Saved with your budget. Thank you.</span>}
          </div>
          <div className="mt-4 pt-3" style={{ borderTop: `1px solid ${C.hair}` }}>
            <div className="flex items-center gap-1.5"><Users size={14} style={{ color: C.inkSoft }} /><Eyebrow>How other readers closed the gap</Eyebrow></div>
            {aggState === "loading" && <p style={{ fontSize: 13, color: C.inkSoft, marginTop: 8 }}>Loading the shared tally…</p>}
            {aggState === "ready" && agg && (agg.n === 0 ? <p style={{ fontSize: 13, color: C.inkSoft, marginTop: 8 }}>No budgets submitted yet — yours can be first. Submissions are anonymous and shown to every reader in aggregate.</p> : <AggregateView agg={agg} />)}
            <p style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 10, fontStyle: "italic" }}>These are readers who chose to take part — a self-selected sample, not a representative or statistically valid survey of Boulder. Responses are stored on Boulder Reporting Lab’s own servers and reported only in aggregate.</p>
          </div>
        </section>

        {/* Provenance & trust contract. The column's prose carries the hook, the
            peg, and the diagnostic close; the widget keeps only what speaks to
            its own numbers — what's official vs. modeled, and the verify link. */}
        <section className="mt-8" style={{ borderTop: `3px solid ${C.ink}`, paddingTop: 18 }}>
          <Eyebrow>Sources &amp; method</Eyebrow>
          <p style={{ fontSize: 14, lineHeight: 1.55, color: C.inkSoft, marginTop: 10 }}>The budget totals and the legal limits are verified against the city’s 2026 adopted budget and Colorado law. The per-department and per-fund splits are modeled placeholders pending line-item data. The panel below says which is which.</p>
          <a href="https://github.com/brianckeegan/charting-boulder" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 mt-4" style={{ fontSize: 13.5, fontWeight: 800, color: C.ink, textDecoration: "none", border: `2px solid ${C.ink}`, borderRadius: 7, padding: "9px 14px" }}><Github size={15} /> Verify me: data, assumptions and code on GitHub</a>
          <div className="mt-5">
            <button onClick={() => setShowData(!showData)} style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0 }} className="flex items-center gap-1.5"><span style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.04em", color: C.inkSoft }}>DATA STATUS & SOURCES</span>{showData ? <ChevronUp size={14} color={C.inkSoft} /> : <ChevronDown size={14} color={C.inkSoft} />}</button>
            {showData && (
              <div style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 8, lineHeight: 1.6 }}>
                <p><strong style={{ color: C.ink }}>Official (verified):</strong> total {fmt(TOTAL)}; operating {fmt(OPERATING)}; capital {fmt(CAPITAL)} (shown as a locked row); General Fund {fmt(GENERAL_FUND)} (−7.8% vs 2025); the {fmt(7.5)} gap; city sales/use tax 3.86%, of which 56% is dedicated; CCRS 0.3% (permanent, Nov. 2025); .25-cent Parks/Rec 0.25%; Transportation 0.15% increment; the four 2026 fee figures. Legal framing: TABOR (Colo. Const. Art. X, §20) requires voter approval for tax increases and bars local income taxes; courts treat fees as non-taxes. Sources: City of Boulder 2026 Approved Budget (OpenGov) and budget message (Aug. 29, 2025); BRL election reporting (Nov. 2025); Colorado Legislative Council Staff.</p>
                <p className="mt-2"><strong style={{ color: C.ink }}>Modeled (placeholder):</strong> the per-department General Fund split, every locked operating-fund amount, the Open Space rate (~0.33%), and the revenue yields (per-mill, per-0.1% sales). They sum to the official totals but are estimates pending line-item ingestion. The “2027 projection” gap is illustrative, not a forecast. Treat any single modeled figure as approximate.</p>
                <p className="mt-2" style={{ fontSize: 11.5 }}>As of June 2026. Built for Boulder Reporting Lab. Figures in millions. A teaching model, not the city’s budgeting system.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- storage */
function emptyAgg() { return { n: 0, usedRevenue: 0, usedVote: 0, usedReserves: 0, revShareSum: 0, cutTally: {} }; }
function round(x) { return Math.round(x * 100) / 100; }

/* Supabase direct-write helpers (used when no ENDPOINT proxy is set). PostgREST
   wants the publishable key in both the apikey and Authorization headers. */
function sbHeaders() {
  return { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json" };
}
/* Map the flat payload onto the exact DB columns, reusing the widget's own data
   tables so the stored column set can never drift from the sliders above. */
function sbRow(p) {
  const row = {
    client_ts: p.ts ?? null, client_version: p.v ?? null, scenario: p.scenario ?? null,
    rev_fees: p.rev_fees ?? 0, rev_property: p.rev_property ?? 0, rev_sales: p.rev_sales ?? 0, reserves: p.reserves ?? 0,
    spend_change: p.spend_change ?? 0, revenue_total: p.revenue_total ?? 0, revenue_only: p.revenue_only ?? 0,
    used_vote: !!p.used_vote, used_revenue: !!p.used_revenue, used_reserves: !!p.used_reserves,
    top_cut: p.top_cut ?? null, repeat_client: !!p.repeatClient, raw: p,
  };
  GF_DEPTS.forEach((d) => { row[`gf_${d.id}`] = p[`gf_${d.id}`] ?? 0; });
  LOCKED_FUNDS.forEach((f) => { row[`fund_${f.id}`] = p[`fund_${f.id}`] ?? 0; });
  DEMO.forEach((q) => { row[`demo_${q.id}`] = p[`demo_${q.id}`] ?? null; });
  return row;
}

async function readAgg(fresh) {
  // Cached read path: the edge-cached Vercel aggregate route, used for the
  // on-load tally while writes go direct. Skipped when `fresh` (right after a
  // submit) so the reader immediately sees their own contribution counted.
  if (!fresh && AGG_ENDPOINT && !ENDPOINT) {
    try { const r = await fetch(AGG_ENDPOINT); return r.ok ? await r.json() : emptyAgg(); } catch { return emptyAgg(); }
  }
  if (ENDPOINT) { try { const r = await fetch(`${ENDPOINT}/aggregate`); return r.ok ? await r.json() : emptyAgg(); } catch { return emptyAgg(); } }
  if (SB_ENABLED) {
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/budget_aggregate`, { method: "POST", headers: sbHeaders(), body: "{}" });
      return r.ok ? ((await r.json()) || emptyAgg()) : emptyAgg();
    } catch { return emptyAgg(); }
  }
  if (typeof window !== "undefined" && window.storage) { try { const r = await window.storage.get(AGG_KEY, true); return r ? JSON.parse(r.value) : emptyAgg(); } catch { return emptyAgg(); } }
  return emptyAgg();
}

async function writeAgg({ revShare, usedRevenue, usedVote, usedReserves, topCut, payload }) {
  // Flag a likely repeat from this browser (best-effort, localStorage only).
  try { if (typeof window !== "undefined" && window.localStorage?.getItem("bb_submitted_v4")) payload.repeatClient = true; window.localStorage?.setItem("bb_submitted_v4", "1"); } catch {}

  if (ENDPOINT) {
    try {
      const r = await fetch(`${ENDPOINT}/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      return r.ok ? await r.json() : null;
    } catch { return null; }
  }
  if (SB_ENABLED) {
    try {
      const ins = await fetch(`${SUPABASE_URL}/rest/v1/contributions`, { method: "POST", headers: { ...sbHeaders(), Prefer: "return=minimal" }, body: JSON.stringify(sbRow(payload)) });
      if (!ins.ok) return null;
      return await readAgg(true);   // fresh re-read (bypass cache) so the tally includes this submission
    } catch { return null; }
  }
  if (typeof window !== "undefined" && window.storage) {
    try {
      const cur = (await readAgg()) || emptyAgg();
      cur.n += 1;
      cur.usedRevenue += usedRevenue ? 1 : 0;
      cur.usedVote += usedVote ? 1 : 0;
      cur.usedReserves += usedReserves ? 1 : 0;
      cur.revShareSum += revShare;
      if (topCut && topCut.amt > 0.01) cur.cutTally[topCut.name] = (cur.cutTally[topCut.name] || 0) + 1;
      await window.storage.set(AGG_KEY, JSON.stringify(cur), true);
      return cur;
    } catch { return null; }
  }
  return null;
}

/* ---------------------------------------------------------------- UI bits */
function GapBar({ label, sub, gap, remaining, balanced }) {
  // Diverging bar: center (50%) = balanced. Left of center = deficit (red),
  // right = surplus (green). pos in [-1, 1] maps remaining in [gap, -gap].
  const pos = Math.max(-1, Math.min(1, -remaining / gap));
  const half = 50;                          // each side is 50% of the track
  const fillLeft = pos >= 0 ? half : half + pos * half;   // start of fill (%)
  const fillWidth = Math.abs(pos) * half;                 // width of fill (%)
  const surplus = -remaining;
  return (
    <div style={{ marginTop: 10 }}>
      <div className="flex items-center justify-between gap-2">
        <div style={{ minWidth: 0 }}>
          <span style={{ fontSize: 13.5, fontWeight: 800 }}>{label}</span>
          <span style={{ fontSize: 11.5, color: C.inkSoft, marginLeft: 6 }}>{sub}</span>
        </div>
        <div className="flex items-center gap-1.5" style={{ flexShrink: 0 }}>
          <span className="tnum" style={{ fontSize: 13.5, fontWeight: 800, color: balanced ? C.green : C.red }}>
            {balanced ? (surplus > 0.05 ? `+${fmt(surplus)}` : "Balanced") : `${fmt(-remaining)} short`}
          </span>
          <span aria-hidden="true" style={{ fontSize: 15, lineHeight: 1 }}>{balanced ? "\u2705" : "\u2B1C"}</span>
        </div>
      </div>
      <div className="relative" style={{ height: 12, marginTop: 5, background: C.paper, border: `1px solid ${C.hair}`, borderRadius: 99, overflow: "hidden" }}>
        {/* deficit (left) / surplus (right) faint zones */}
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "50%", background: "rgba(207,46,46,0.06)" }} />
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, right: 0, background: "rgba(31,122,77,0.06)" }} />
        {/* fill */}
        <div style={{ position: "absolute", top: 0, bottom: 0, left: `${fillLeft}%`, width: `${fillWidth}%`, background: balanced ? C.green : C.red, transition: "left .2s ease, width .2s ease" }} />
        {/* center "balanced" tick */}
        <div style={{ position: "absolute", left: "50%", top: -1, bottom: -1, width: 2, background: C.ink, transform: "translateX(-1px)" }} />
      </div>
      <div className="flex justify-between" style={{ fontSize: 10, color: C.inkSoft, marginTop: 2 }} aria-hidden="true">
        <span>deficit</span><span>balanced</span><span>surplus</span>
      </div>
    </div>
  );
}
function Cites({ sources }) {
  if (!sources || !sources.length) return null;
  return (
    <sup style={{ marginLeft: 3, whiteSpace: "nowrap" }}>
      {sources.map((s, i) => (
        <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" title={s.label}
          style={{ color: C.blueDk, fontWeight: 800, fontSize: 10, textDecoration: "none", marginLeft: i ? 2 : 0 }}>[{i + 1}]</a>
      ))}
    </sup>
  );
}
function Eyebrow({ children }) { return <div style={{ fontSize: 11, letterSpacing: "0.13em", textTransform: "uppercase", color: C.inkSoft, fontWeight: 800 }}>{children}</div>; }
function SectionHead({ icon, title }) { return <div className="flex items-center gap-2"><span style={{ display: "inline-flex", flexShrink: 0 }}>{icon}</span><h2 style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.01em", lineHeight: 1.15 }}>{title}</h2></div>; }
function Tag({ children, color, bg }) {
  return <span className="tnum" style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.03em", textTransform: "uppercase", color: bg && bg !== "transparent" ? "#1A1A1A" : (color || C.inkSoft), background: bg && bg !== "transparent" ? bg : "transparent", border: `1px solid ${color || C.hair}`, borderRadius: 4, padding: "1px 5px" }}>{children}</span>;
}

function AggregateView({ agg }) {
  const pct = (x) => Math.round((x / agg.n) * 100);
  const avgRev = Math.round((agg.revShareSum / agg.n) * 100);
  const topCut = Object.entries(agg.cutTally).sort((a, b) => b[1] - a[1])[0];
  const rows = [
    { label: "raised new revenue (not just reserves)", v: pct(agg.usedRevenue) },
    { label: "needed a tax that requires a public vote", v: pct(agg.usedVote) },
    { label: "leaned on one-time reserves", v: pct(agg.usedReserves) },
  ];
  return (
    <div className="mt-3">
      <div style={{ fontSize: 13, color: C.inkSoft }}><strong style={{ color: C.ink }} className="tnum">{agg.n}</strong> reader{agg.n === 1 ? "" : "s"} have balanced it. On average they closed <strong style={{ color: C.ink }} className="tnum">{avgRev}%</strong> of the gap with revenue and the rest with cuts{topCut ? <>; the most common deep cut was <strong style={{ color: C.ink }}>{topCut[0]}</strong>.</> : "."}</div>
      <div className="mt-3 grid gap-2">
        {rows.map((r) => (
          <div key={r.label}><div className="flex justify-between" style={{ fontSize: 12.5, color: C.inkSoft }}><span>{r.label}</span><span className="tnum" style={{ fontWeight: 800, color: C.ink }}>{r.v}%</span></div><div className="rounded-full mt-1" style={{ height: 7, background: C.lockBg }}><div style={{ height: "100%", width: `${r.v}%`, background: C.lime, borderRadius: 99 }} /></div></div>
        ))}
      </div>
    </div>
  );
}

function DemoQuestion({ d, value, onChange }) {
  const isMulti = d.t === "multi";
  const sel = isMulti ? (value || []) : value;
  const toggle = (opt) => {
    if (isMulti) {
      const cur = new Set(value || []);
      if (opt === "Prefer not to say") return onChange(cur.has(opt) ? [] : ["Prefer not to say"]);
      cur.delete("Prefer not to say"); cur.has(opt) ? cur.delete(opt) : cur.add(opt); onChange([...cur]);
    } else { onChange(value === opt ? undefined : opt); }
  };
  return (
    <div className="rounded-md p-3" style={{ background: C.paper, border: `1px solid ${C.hair}` }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 8 }}>{d.q}</div>
      <div className="flex flex-wrap gap-1.5">
        {d.o.map((opt) => {
          const on = isMulti ? sel.includes(opt) : sel === opt;
          return <button key={opt} onClick={() => toggle(opt)} aria-pressed={on} style={{ fontSize: 12.5, fontWeight: 600, padding: "6px 10px", borderRadius: 99, cursor: "pointer", textAlign: "left", border: `1.5px solid ${on ? C.ink : C.hair}`, background: on ? C.lime : C.paper, color: C.ink }}>{isMulti && <span style={{ marginRight: 4 }}>{on ? "✓" : "+"}</span>}{opt}</button>;
        })}
      </div>
    </div>
  );
}
