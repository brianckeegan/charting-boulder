import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  Lock, Building2, Coins, RotateCcw, Check, AlertTriangle,
  Github, ChevronDown, ChevronUp, Users, ArrowDownToLine,
} from "lucide-react";

/* ============================================================================
   BALANCE BOULDER'S BUDGET — an interactive for Boulder Reporting Lab
   ============================================================================

   FOR EDITORS & REPORTERS — HOW TO READ AND EDIT THIS FILE
   --------------------------------------------------------------------------
   You do not need to be a programmer to customize this. Almost everything you
   would change lives in the labeled data tables just below (GF_DEPTS,
   LOCKED_DEPTS, REVENUE, DEDICATED_RATES, GAP, DEMO). Each table is a
   list of rows; each row is a set of "field: value" pairs. Change the text
   between quotation marks, or the number after a colon, then save and reload.

   Two labels keep us honest, and one applies to every figure:
     • OFFICIAL — verified against the City of Boulder's adopted budget or
                  Colorado law. Safe to publish as written.
     • MODELED  — a placeholder estimate so the tool works end to end. Replace
                  it with the city's real line-item figure before publishing.

   WHAT EACH TABLE CONTROLS
     GF_DEPTS         General Fund departments (the sliders). Each slider
                      starts at `base`, the department's status quo: its 2027
                      cost before the city's 2027 changes.       [MODELED #2]
                      `amount` is the 2027 recommended budget, which sets the
                      "proposed" tick, and `was` the 2026 budget restated for
                      the 2027 departments.                     [OFFICIAL #2]
     LOCKED_DEPTS     Each department's spending OUTSIDE the General Fund —
                      dedicated, fee-funded and capital money you can move but
                      whose savings stay trapped. `amount` in $millions; sums
                      to TOTAL − GENERAL_FUND = $352.1M.    [OFFICIAL inputs #7]
     REVENUE          The revenue sliders, each with a one-line list of what
                      the money comes from.
                      Bases are OFFICIAL; yields are MODELED. [see #3 and #4]
     DEDICATED_RATES  Voter-set sales-tax rates shown frozen, with the annual
                      revenue each raises.                    [OFFICIAL — #3]
     GAP              The 2027 General Fund gap to close.      [OFFICIAL — #1]
     DEMO             The optional reader survey (adapted from the 2025 BVCP
                      survey).

   WHAT GETS STORED WHEN A READER SUBMITS — AND WHERE
     One flat record per submission: every slider's position (including the
     ones left at zero — so each row is a complete budget), the revenue
     settings, a few derived totals, and one column per survey answer.
     Field names match the database columns in ARCHITECTURE.md one-to-one.
     ALL of it — the budget AND the survey answers — is stored in Boulder
     Reporting Lab's own Supabase database (Postgres), written directly with a
     browser-safe publishable key. No advertising or analytics third party ever
     receives a response. No name,
     account, email, IP address, or browser fingerprint is stored with a record
     (the rate limiter keeps a salted one-way hash of the sending network for
     two days, in a separate table never linked to a response; see
     ARCHITECTURE.md).

   ADDING A NEWS CITATION (the [1], [2] links next to a row)
     Add a `sources` field to any row, e.g.:
         sources: [SRC.budget2026, SRC.strain2025]
     Define each link once in the SRC table below (a label and a URL) and reuse
     it anywhere. Prefer the most recent relevant coverage as the first cite;
     older but on-topic pieces are fine as a secondary cite. Only a few rows are
     filled in here as a demonstration — add more as you report them, and
     confirm each link still resolves (#6).

   FACT-CHECK BEFORE DEPLOYMENT — every figure below was checked on
   Sept. 29, 2026 against the City Manager's 2027 Recommended Budget
     1. Control totals (TOTAL / OPERATING / CAPITAL / GENERAL_FUND) and the
        $6.3M gap: OFFICIAL. Source: the city's online 2027 budget book
        (OpenGov "Budget in Brief") and the City Manager's budget message.
     2. GF_DEPTS `amount` (2027): OFFICIAL, from the 2027 General Fund Fund
        Financial (1100), "2027 Budget" column. `was` (2026): OFFICIAL, from
        the Budget in Brief's General Fund uses-by-department table, "2026
        Budget" column, which restates 2026 for the 2027 departments. It
        differs from the Fund Financial's "2026 Approved" column only where
        Community Vitality's $1,611,459 moved: into the City Manager's Office
        ($1,388,682) and Facilities & Fleet ($222,777). "General Government"
        is Fundwide / Citywide plus Police/Fire Pensions. Both columns sum to
        their year's General Fund total. `base` (the status quo) is MODELED:
        `amount` with the city's itemized 2027 General Fund changes undone
        (the Budget in Brief's list of reductions, enhancements and
        realignments), plus a share of the rest of the $6.3M gap, which the
        city does not itemize by department, spread in proportion to `amount`.
        Following every "proposed" tick then closes exactly the $6.3M.
        Details: ../PROVENANCE.md.
     3. Sales-tax rates and the dollars they raise (DEDICATED_RATES) and the
        revenue bases in REVENUE: OFFICIAL, from the Budget in Brief's Sales &
        Use Tax Components table and sales-tax chart, the mill levy table
        (general-purpose property tax, 7.948 mills), and the General Fund Fund
        Financial (fees & charges = licenses, permits & fines + parking +
        charges for services). The yields per step are MODELED: a change
        yields its share of the base, with no change in behavior. The
        marijuana tax yield uses the city's forecast that 3.5% → 5.5% raises
        41.2% more; below 3.5%, revenue falls in proportion to the rate.
     4. Legal framing (TABOR vote requirement; the local-income-tax bar;
        fees-are-not-taxes; the 10% marijuana-tax ceiling voters set in 2013,
        Question 2A): OFFICIAL.
     5. The city's own 2027 moves quoted in the copy (24 positions, photo-radar
        vans, pools, the ~$0.32M of General Fund costs shifted to dedicated
        funds, the marijuana tax,
        new fees): OFFICIAL, from the Budget At-A-Glance page and the budget
        book's lists of changes.
     6. News citations in the SRC table: confirm each URL still loads and still
        supports the row it sits next to.
     7. LOCKED_DEPTS: each department's 2027 spending in the book's "Citywide
        Uses" table (net of transfers and internal services) minus its
        General Fund amount. Both inputs are OFFICIAL; the rows sum to
        TOTAL − GENERAL_FUND = $352.1M. The capital budget sits inside them.
     8. Hand-maintained prose figures (NOT pulled from the constants): the
        "$552.6M" eyebrow, the sales-tax split ($3.86, $1.72 and $2.14 of
        every $100), the council dates (Oct. 1 and 15) and the Nov. 3 ballot
        are written into the copy.
        Update them by hand (search the file) when they change — above all
        when council adopts the budget on Oct. 15.

   DEPLOYMENT KNOBS (just below)
     SUPABASE_URL  — the project and its browser-safe PUBLISHABLE key, used to
       /_KEY         write each submission straight to Supabase.
     SRC           — the citation-link table.
     OFFICIAL      — links to the city's budget documents, in Sources & method.
     See ARCHITECTURE.md for setup, the data dictionary, and Newspack embedding.

   This is a teaching model, not the city's budgeting system. Visual identity
   matches BRL's Newspack theme (Public Sans; #CDDE00 / #3A8DDE).

   DESIGN — FRAMING LIVES IN THE COLUMN
     This widget is built to sit inside the column's prose, which carries the
     hook, the peg (the Nov. 2026 ballot / 2027 budget cycle), and the
     diagnostic close. So the widget's own copy is deliberately lean: a short
     title, one-line instructions, one-line source lists, point-of-use caveats, and a
     collapsible "Sources & method" block with the verify-me link. If you ever embed this
     standalone (no surrounding article), restore a sentence or two of framing
     at the top and a closing thought at the bottom — otherwise it will read as
     an interaction with no argument around it.
   ========================================================================== */

/* ---- BACKEND CONFIG ------------------------------------------------------
   Where reader submissions go, resolved at runtime:
     1. SUPABASE_URL + SUPABASE_KEY — write straight to Supabase from the browser
        with the PUBLISHABLE key (safe to publish; Row Level Security lets a
        reader add a row but never read one back). No server to host.
     2. Preview mode (window.__BBW_PREVIEW__) — the tally lives only in this
        browser session; nothing leaves the page.
   See ARCHITECTURE.md for the full data flow, schema, and privacy model. ----- */
// Offline/preview builds (build-standalone.sh) set window.__BBW_PREVIEW__ to
// keep submissions in the browser session only, so a local review copy never
// writes to the live database. Production embeds leave it unset.
const PREVIEW = typeof window !== "undefined" && window.__BBW_PREVIEW__ === true;

// Supabase direct write. The PUBLISHABLE key is browser-safe by design (RLS is
// the real guard), so committing it is expected. The SECRET key is never used
// in the browser — only server-side, for offline analysis (export-responses.py).
const SUPABASE_URL = "https://iplcjxbazezpjdzdpjxx.supabase.co";
const SUPABASE_KEY = "sb_publishable_2jy9CF17cyHSMAnVYSpFcA_tRecRIoi";
const SB_ENABLED = !PREVIEW && !!SUPABASE_URL && !!SUPABASE_KEY;

const AGG_KEY = "boulder_budget_agg_v5";
const WIDGET_VERSION = 5;   // payload `v`, stored as client_version

/* ---- SRC: news-citation links. Define each link once (label + url), then
   reference it by name in any data row's `sources` field, e.g.
   sources: [SRC.ballotFinal, SRC.ballot2026]  (recent first, older second).
   A few rows below are filled in to demonstrate.
   Before publishing, confirm every URL still loads (fact-check #6). --------- */
const SRC = {
  budget2027:   { label: "BRL — Boulder’s proposed 2027 budget would cut 13 filled jobs and trim pool hours (Sep. 2026)",
                  url: "https://boulderreportinglab.org/2026/09/08/boulders-proposed-2027-budget-would-cut-13-filled-jobs-and-trim-pool-hours/" },
  recAccess2027:{ label: "BRL — Boulder could end fully subsidized recreation access for low-income residents in 2027 (Sep. 2026)",
                  url: "https://boulderreportinglab.org/2026/09/10/boulder-proposes-ending-free-recreation-access-for-low-income-residents/" },
  spruce2027:   { label: "BRL — Boulder’s Spruce Pool gets another summer. Its future after 2027 is uncertain. (Sep. 2026)",
                  url: "https://boulderreportinglab.org/2026/09/01/boulders-spruce-pool-will-stay-open-in-2027-after-that-its-future-is-unclear/" },
  ballotFinal:  { label: "BRL — Council sends vacancy tax and $400M bond to the November ballot (Aug. 2026)",
                  url: "https://boulderreportinglab.org/2026/08/06/boulder-city-council-sends-vacancy-tax-and-400-million-bond-to-november-ballot-rejects-downtown-development-authority/" },
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
};

/* ---- OFFICIAL: the city's own budget documents, plus the state's TABOR
   explainer. Linked in the Sources & method text and listed under it. Every
   URL loaded on Sept. 29, 2026. -------------------------------------------- */
const BOOK = "https://stories.opengov.com/cityofboulderco/68d0bc8f-fb31-4578-a8af-59594ef78e4d/published/hgCyk4CwB";
/* Where every number on the page comes from, in the repository. */
const PROVENANCE = { label: "Where every number comes from", url: "https://github.com/brianckeegan/charting-boulder/blob/main/2026-11-budget-tool/embed/PROVENANCE.md" };
const OFFICIAL = {
  book:          { label: "2027 Recommended Budget: the city’s online budget book", url: BOOK },
  brief:         { label: "2027 Budget in Brief: totals, the General Fund gap, revenue forecasts", url: `${BOOK}?currentPageId=6a7a22d6e8cd6b725ef3b5b5` },
  briefMore:     { label: "Budget in Brief, continued: sales-tax rates, mill levies, budget assumptions", url: `${BOOK}?currentPageId=6a7a230c2aaa5815f9944b90` },
  message:       { label: "City manager’s budget message", url: `${BOOK}?currentPageId=6a7a2349492dea63d5fd8d27` },
  gfTable:       { label: "General Fund 2027 Fund Financial (1100), PDF", url: "https://bouldercolorado.gov/media/21600/download?inline" },
  glance:        { label: "Budget At-A-Glance: the city’s summary of 2027 cuts, shifts and fees", url: "https://bouldercolorado.gov/budget-glance" },
  release:       { label: "City news release on the recommended budget (Aug. 28, 2026)", url: "https://bouldercolorado.gov/news/city-manager-releases-balanced-budget-focus-critically-vital-services-and-community-input" },
  policies:      { label: "Financial policies: reserve targets", url: `${BOOK}?currentPageId=6a75e5049edf5ffa8847c1f7` },
  budgetPage:    { label: "City of Boulder budget page: forecasts and past budgets", url: "https://bouldercolorado.gov/services/budget" },
  portal:        { label: "City of Boulder transparency portal (OpenGov)", url: "https://cityofboulderco.opengov.com/transparency/" },
  mjRates:       { label: "City of Boulder marijuana tax rates", url: "https://bouldercolorado.gov/city-boulder-marijuana-tax-rates" },
  fundOurFuture: { label: "Fund Our Future: Our Community’s Priorities (June 29, 2026)", url: "https://bouldercolorado.gov/news/fund-our-future-our-communitys-priorities" },
  tabor:         { label: "TABOR explained, Colorado General Assembly", url: "https://leg.colorado.gov/agencies/legislative-council-staff/tabor" },
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
// Control totals keep one decimal even above $100M ($552.6M, not $553M), so
// they match the figures the city publishes.
const fmt1 = (m) => `${m < 0 ? "−" : ""}$${Math.abs(m).toFixed(1)}M`;
const signed = (m) => `${m < 0 ? "−" : "+"}$${Math.abs(m) >= 100 ? Math.abs(m).toFixed(0) : Math.abs(m).toFixed(1)}M`;

/* ---- OFFICIAL control totals ($M): the City Manager's 2027 Recommended
   Budget. GENERAL_FUND is the General Fund Fund Financial's total uses to the
   thousand ($200,496,242), so the department rows below sum to it exactly;
   the book rounds it to $200.5M. TOTAL is its Citywide Uses total. -------- */
const TOTAL = 552.601, OPERATING = 417.24, CAPITAL = 135.36, GENERAL_FUND = 200.496;

/* ---- GF_DEPTS: the General Fund's largest departments, shown as sliders.
   id      machine name (data key; stored as gf_<id>)
   name    the stored name. These exact strings are the database's allowlist
           for `top_cut` (public.bbw_gf_departments()) — rename one there
           FIRST, then here.
   label   what the reader sees, when it differs from `name`: the allowlist
           says "GF share", readers see "General Fund share".
   base    where the slider starts: the status quo, the department's 2027
           cost before the city's 2027 changes, $millions — MODELED (see the
           editor note above and ../PROVENANCE.md). The column sums to
           GF_STATUS_QUO, $206.4M.
   amount  2027 recommended General Fund budget, $millions — OFFICIAL, from the
           2027 General Fund Fund Financial (1100). The top 10 departments by
           GF spend, plus an "Other" line; the column sums to GENERAL_FUND.
           With `moved`, it sets the "proposed" tick.
   moved   General Fund costs the recommended budget moves onto dedicated
           funds, $millions. They leave through the cost-shift slider, so the
           department's tick sits at `amount` + `moved`.
   was     the same department's 2026 amount, restated for the 2027
           departments (Budget in Brief, General Fund uses by department,
           "2026 Budget"), shown in the tick's tooltip.
   note    sub-label listing the main programs inside the department. */
const GF_DEPTS = [
  { id: "police", name: "Police", base: 55.588, amount: 54.246, was: 50.204, note: "Operations · Investigations · Administration · Alternative response · Dispatch · Support services" },
  { id: "genadmin", name: "General Government", base: 36.493, amount: 35.612, was: 38.436, note: "Citywide costs · Contingency · Debt service · Interfund transfers · Police and fire pensions" },
  { id: "fire", name: "Fire-Rescue", base: 31.800, amount: 30.968, moved: 0.180, was: 29.129, note: "Emergency operations · EMS · Wildland · Support services · Community risk reduction" },
  { id: "hhs", name: "Housing & Human Services (GF share)", label: "Housing & Human Services (General Fund share)", base: 13.699, amount: 14.007, moved: 0.100, was: 12.962, note: "Human services · Homelessness · Behavioral health · Family services" },
  { id: "manager", name: "City Manager's Office", label: "City Manager’s Office", base: 12.083, amount: 11.981, was: 11.087, note: "Economic vitality · City Clerk · Equity · Independent police monitor · New Office of Customer Experience" },
  { id: "it", name: "Innovation & Technology", base: 11.580, amount: 10.680, was: 10.372, note: "Infrastructure · Data & analytics · Application support · Cybersecurity · Project management" },
  { id: "facilities", name: "Facilities & Fleet (GF share)", label: "Facilities & Fleet (General Fund share)", base: 7.387, amount: 7.042, was: 7.153, note: "Facility operations · Maintenance · Energy management · Fleet" },
  { id: "finance", name: "Finance", base: 7.314, amount: 7.024, was: 6.881, note: "Taxpayer services · Budget · Accounting · Licensing · Purchasing · Payroll" },
  { id: "parksrec", name: "Parks & Recreation (GF share)", label: "Parks & Recreation (General Fund share)", base: 6.930, amount: 6.634, moved: 0.036, was: 6.490, note: "Park operations · Natural resources · Planning · Administration" },
  { id: "attorney", name: "City Attorney's Office", label: "City Attorney’s Office", base: 5.477, amount: 5.518, was: 5.067, note: "Administration · Advisory · Prosecution & civil litigation" },
  { id: "other", name: "Other General Fund departments", base: 18.032, amount: 16.784, was: 16.702, note: "Human resources · Communications · Planning · Municipal Court · Climate · City Council · Utilities · Transportation · Community Vitality" },
];
/* The General Fund's status quo, where the department sliders start. */
const GF_STATUS_QUO = GF_DEPTS.reduce((t, d) => t + d.base, 0);
/* What the reader sees: the label when there is one, else the stored name. */
const deptLabel = (d) => d.label || d.name;

/* ---- LOCKED_DEPTS: each department's spending OUTSIDE the General Fund —
   voter-dedicated taxes, fees, utility rates, grants and capital money. You
   can move a slider, but the savings stay trapped in those funds and never
   reach the General Fund gap — that is the lesson.
   amount  2027 recommended, $millions: the department's line in the budget
           book's "Citywide Uses" table (all funds, net of transfers and
           internal services) minus its General Fund amount above. Both
           inputs OFFICIAL. The rows sum to TOTAL − GENERAL_FUND = $352.1M;
           the $135.4M capital budget is spread across them.
   kind    "enterprise" | "dedicated" | "capital" (the small tag)
   why     one line naming the money and its restriction, from each
           department page's list of 2027 changes. ---------------------------- */
const LOCKED_DEPTS = [
  { id: "utilities", name: "Utilities", amount: 136.555, kind: "enterprise", why: "Water, wastewater and stormwater, paid for by utility rates (up 5–7% in 2027) and spent only on those systems, including capital projects." },
  { id: "transpo", name: "Transportation & Mobility", amount: 60.028, kind: "dedicated", why: "The 0.75% transportation sales tax, the new Transportation Maintenance Fee, the airport and grants; roads, transit, paths and bridges only." },
  { id: "openspace", name: "Open Space & Mountain Parks", amount: 37.423, kind: "dedicated", why: "The 0.77% open space sales tax; open space and mountain parks only.", sources: [SRC.salesTax2025] },
  { id: "hhs", name: "Housing & Human Services", amount: 35.715, kind: "dedicated", why: "Affordable-housing funds, the community housing property tax, eviction prevention and the sugary-drink tax; housing and human services only.", sources: [SRC.housing2025] },
  { id: "parksrec", name: "Parks & Recreation", amount: 30.478, kind: "dedicated", why: "Recreation fees, the .25-cent parks sales tax and the permanent parks property tax; parks and recreation only." },
  { id: "facilities", name: "Facilities & Fleet", amount: 16.946, kind: "capital", why: "Parking garages run by the downtown, University Hill and Boulder Junction districts, and capital money for city buildings." },
  { id: "pds", name: "Planning & Development Services", amount: 16.232, kind: "enterprise", why: "Permit and development-review fees and development impact fees; development review and growth-related projects only." },
  { id: "manager", name: "City Manager’s Office", amount: 7.448, kind: "dedicated", why: "The Arts, Culture & Heritage tax and the downtown, University Hill and Boulder Junction district funds." },
  { id: "climate", name: "Climate Initiatives", amount: 6.493, kind: "dedicated", why: "The voter-approved Climate Tax; climate and wildfire-resilience work only." },
  { id: "fire", name: "Fire-Rescue", amount: 4.082, kind: "dedicated", why: "The Open Space tax’s share of the wildland fire crew (90% in 2027, up from 75%) and capital for Knox-Box locks and breathing apparatus." },
  { id: "other", name: "Other departments", amount: 0.705, kind: "dedicated", why: "Small amounts in Finance and citywide accounts charged to dedicated funds." },
];

/* ---- Revenue sliders -------------------------------------------------- *
   pieces: one line naming what the money comes from (for a locked row, also
           why it is locked), shown under the label
   type:   pct     −25..25 % over `base`, the source's 2027 General Fund
                   revenue ($M); yield = base × pct/100, negative = a cut
           rate    a tax rate from `min` to `max`, starting at `now`, where it
                   raises `base` $M. Each point above `now` adds `perPoint`
                   $M; below `now`, revenue falls in proportion to the rate,
                   to $0 at 0%. The row shows the revenue at the chosen rate.
           dollars $M moved from `min` to `max` (not revenue: see "shift")
   city:   where the recommended budget puts this slider, drawn as the
           "proposed" tick
   locked: shown greyed out, with its `pieces` line and no slider
   Every number here is traced to its source in ../PROVENANCE.md.           */
const REVENUE = [
  { id: "fees", type: "pct", label: "Fees & charges", base: 10.973,
    pieces: "Licenses, permits & fines · Parking · Charges for services" },
  { id: "property", type: "pct", label: "Property tax", base: 39.459,
    pieces: "General-purpose levy (7.948 of the city’s 11.648 mills)" },
  { id: "sales", type: "pct", label: "Sales & use tax", base: 82.597,
    pieces: "Sales tax · Use tax (the General Fund’s 1.72% of the city’s 3.86% rate)" },
  { id: "marijuana", type: "rate", label: "Recreational marijuana tax", min: 0, max: 10, step: 0.5, now: 3.5, base: 1.0, perPoint: 0.206, city: 5.5,
    pieces: "Boulder’s additional sales tax on recreational marijuana" },
  { id: "shift", type: "dollars", label: "Shift General Fund costs onto dedicated funds", min: 0, max: 5, step: 0.1, city: 0.316,
    pieces: "Wildland fire crew to the Open Space tax · Urban-ranger equipment to Open Space · Half a behavioral-health contract to the sugary-drink tax" },
  { id: "vacancy", label: "Vacancy tax", locked: true, sources: [SRC.ballotFinal],
    pieces: "$4,000 a year on homes left empty more than half the year · On the Nov. 3 ballot · Would start in 2028" },
  { id: "income", label: "Local income tax", locked: true,
    pieces: "Residents’ and workers’ earnings · Barred for Colorado cities by the state constitution" },
  { id: "wealth", label: "Wealth tax", locked: true,
    pieces: "Household net worth · No Colorado city has the power to levy one" },
];

/* The starting position of every unlocked revenue slider. */
const REV_START = Object.fromEntries(REVENUE.filter((r) => !r.locked).map((r) => [r.id, r.type === "rate" ? r.now : 0]));

/* A revenue slider's yield, $M. Shifting costs is not revenue, so it yields 0
   here and is counted on its own. A tax rate yields the city's per-point
   estimate above today's rate; below it, revenue falls in proportion to the
   rate, so a 0% tax raises nothing. */
function revYield(r, v) {
  if (r.locked || r.type === "dollars") return 0;
  if (r.type === "rate") return v >= r.now ? (v - r.now) * r.perPoint : r.base * (v / r.now - 1);
  return r.base * (v / 100);
}

/* ---- DEDICATED_RATES: the sales-tax rates voters froze, shown as locked
   sliders. The council cannot move these.
   rate  the rate, as a % of the city's 3.86% total sales tax     [OFFICIAL]
   revM  2027 recommended revenue, $millions                      [OFFICIAL]
         (Budget in Brief: Sales & Use Tax Components table and the
         Sales Tax Revenues 2023-2027 chart)
   note  context shown beneath the (disabled) slider
   sources optional [n] links. ---------------------------------------------- */
const DEDICATED_RATES = [
  { id: "os", label: "Open Space taxes", rate: 0.77, revM: 36.6, note: "Voter-dedicated to open space. In 2035, 0.12% moves to the General Fund; another 0.15% expires after 2039.", sources: [SRC.salesTax2025] },
  { id: "tr", label: "Transportation taxes", rate: 0.75, revM: 35.7, note: "Voter-dedicated to transportation. In 2030, 0.15% moves to the General Fund." },
  { id: "cc", label: "Community, Culture, Resilience & Safety (CCRS) tax", rate: 0.30, revM: 14.3, note: "Pays for capital projects. Voters made it permanent in November 2025.", sources: [SRC.salesTax2025] },
  { id: "pr", label: ".25-cent Parks & Recreation tax", rate: 0.25, revM: 11.9, note: "Voter-dedicated to parks and recreation. It expires after 2035 unless voters renew it.", sources: [SRC.ballot2026] },
  { id: "ach", label: "Arts, Culture & Heritage tax", rate: 0.075, revM: 3.6, note: "Voter-dedicated to arts and culture from 2025 through 2044." },
];

/* ---- GAP: the 2027 General Fund shortfall the recommended budget closes.
   OFFICIAL: the City Manager's 2027 Recommended Budget ($6.3M; the May 2026
   Financial Forecast had put it at $6.5M). ------------------------------- */
const GAP = 6.3;

/* ---- DEMO: optional reader survey. Adapted from the 2025 BVCP survey; some
   brackets are expanded and several questions were added or swapped, so not
   every item maps 1:1 to the city's survey (years, employment, building, tenure,
   race, gender, LGBTQ still match). Every row keeps "Prefer not to say"; one
   answer (any of them) is required to submit. t: "single" = pick one,
   "multi" = select all. - */
const DEMO = [
  { id: "years", t: "single", q: "How many years have you lived in the Boulder Valley?",
    o: ["5 years or less", "6-10 years", "11-20 years", "More than 20 years", "Prefer not to say"] },
  { id: "area", t: "single", q: "Which area of Boulder do you currently live in?",
    o: ["North Boulder", "Central Boulder", "University Hill", "South Boulder", "University of Colorado", "Southeast Boulder", "East Boulder", "Crossroads", "Palo Park", "Gunbarrel", "Other", "Outside the city", "Prefer not to say"] },
  { id: "employment", t: "single", q: "What is your employment status?",
    o: ["Working full time for pay", "Working part time for pay", "Unemployed, looking for paid work", "Not retired, not looking for paid work", "Fully retired", "Prefer not to say"] },
  { id: "commute", t: "single", q: "How do you usually get around Boulder?",
    o: ["Drive (alone)", "Carpool or rideshare", "Bus or other transit", "Bike", "Scooter", "Walk or roll", "Mostly work or stay at home", "Prefer not to say"] },
  { id: "student", t: "single", q: "Are you a student at CU Boulder or any other college or university?",
    o: ["Yes, an undergraduate student", "Yes, a graduate student", "No", "Prefer not to say"] },
  { id: "education", t: "single", q: "What is the highest level of education you have finished?",
    o: ["No high school diploma", "High school diploma", "GED", "Some college, no degree", "Associate degree", "Bachelor's degree", "Master's degree", "Professional degree (MD, JD, DDS)", "Doctoral degree (PhD, EdD)", "Prefer not to say"] },
  { id: "building", t: "single", q: "Which best describes the building you live in?",
    o: ["Single-unit house detached from any other houses", "Building with two or more homes (duplex, townhome, apartment or condominium)", "Manufactured home", "Other", "Prefer not to say"] },
  { id: "tenure", t: "single", q: "Do you own or rent your home?",
    o: ["Own", "Rent", "Other", "Prefer not to say"] },
  { id: "income", t: "single", q: "How would you describe your annual household income?",
    o: ["Less than $25,000 per year", "$25,000 to $49,999 per year", "$50,000 to $99,999 per year", "$100,000 to $149,999 per year", "$150,000 to $299,999 per year", "$300,000 per year or more", "Prefer not to say"] },
  { id: "age", t: "single", q: "What is your age range?",
    o: ["18-24", "25-34", "35-44", "45-54", "55-64", "65 and over", "Prefer not to say"] },
  { id: "race", t: "multi", q: "Which race(s) and/or ethnic group(s) do you most identify with? Select all that apply.",
    o: ["American Indian or Alaskan Native", "Asian", "Black or African American", "Latine/Latinx/Hispanic", "Middle Eastern or North African", "Native Hawaiian or Pacific Islander", "White", "Other", "Prefer not to say"] },
  { id: "gender", t: "single", q: "What is your gender?",
    o: ["Woman", "Man", "Non-binary/Genderqueer", "Prefer to self-describe", "Prefer not to say"] },
  { id: "lgbtq", t: "single", q: "Are you a member of the LGBTQ+ community?",
    o: ["Yes", "No", "Prefer not to say"] },
  { id: "disability", t: "single", q: "Do you have a disability?",
    o: ["Yes, visible", "Yes, invisible", "Yes, visible and invisible", "No", "Prefer not to say"] },
];

export default function BoulderBudgetWidget() {
  const [deptPct, setDeptPct] = useState({});      // id -> -25..25
  const [lockedPct, setLockedPct] = useState({});  // id -> -25..25
  const [rev, setRev] = useState(REV_START);        // id -> slider value (see REVENUE `type`)
  const [showLocked, setShowLocked] = useState(false);
  const [showDemo, setShowDemo] = useState(true);
  const [showSources, setShowSources] = useState(false);
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

  // Load Public Sans (Boulder Reporting Lab's typeface) so the widget renders in
  // the BRL face even as a standalone embed, instead of a system fallback.
  // Skipped in the inline (web component) build, where the widget deliberately
  // inherits the host page's typography and makes no third-party font request.
  useEffect(() => {
    if (typeof window !== "undefined" && window.__BBW_INHERIT_FONTS__) return;
    if (typeof document === "undefined" || document.getElementById("bbw-fonts")) return;
    const mk = (rel, href, cross) => { const l = document.createElement("link"); l.rel = rel; l.href = href; if (cross) l.crossOrigin = "anonymous"; return l; };
    const css = mk("stylesheet", "https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap");
    css.id = "bbw-fonts";
    document.head.append(
      mk("preconnect", "https://fonts.googleapis.com"),
      mk("preconnect", "https://fonts.gstatic.com", true),
      css,
    );
  }, []);

  /* derived math — spending change is signed (+ = more spending = worse gap) */
  const netSpendChange = useMemo(() => GF_DEPTS.reduce((s, d) => s + d.base * ((deptPct[d.id] || 0) / 100), 0), [deptPct]);
  const netCuts = Math.max(0, -netSpendChange);
  const revenueOnly = useMemo(() => REVENUE.reduce((s, r) => s + revYield(r, rev[r.id] ?? REV_START[r.id]), 0), [rev]); // signed change in taxes/fees (− = cut)
  const shifted = rev.shift || 0;                   // $M of General Fund costs moved onto dedicated funds
  const trappedChange = useMemo(() => LOCKED_DEPTS.reduce((s, f) => s + f.amount * ((lockedPct[f.id] || 0) / 100), 0), [lockedPct]);

  // One test: the 2027 gap, closed by cuts, recurring revenue, or costs moved
  // onto dedicated funds. There is no one-time money here — a gap that comes
  // back every year needs a fix that does too.
  const remaining = GAP + netSpendChange - revenueOnly - shifted;
  const balanced = remaining <= 0.05;
  const surplus = -remaining;
  const lockedTotal = TOTAL - GENERAL_FUND;
  const pctMovable = (GENERAL_FUND / TOTAL) * 100;
  const usedRevenue = revenueOnly > 0.01;
  const usedVote = (rev.sales || 0) > 0 || (rev.property || 0) > 0;
  const usedShift = shifted > 0;
  const totalFix = Math.max(0, revenueOnly) + netCuts + shifted;

  useEffect(() => { let alive = true; (async () => { const a = await readAgg(); if (alive) { setAgg(a || emptyAgg()); setAggState("ready"); } })(); return () => { alive = false; }; }, []);

  const submit = useCallback(async () => {
    const answered = Object.values(demo).filter((v) => (Array.isArray(v) ? v.length : v)).length;
    if (!balanced || submitted || answered === 0) return;
    const topCut = GF_DEPTS.map((d) => ({ name: d.name, amt: -d.base * ((deptPct[d.id] || 0) / 100) })).sort((a, b) => b.amt - a.amt)[0];
    // Share of the fix that came from new revenue; a revenue cut counts as none.
    const revShare = totalFix > 0 ? Math.max(0, revenueOnly) / totalFix : 0;
    /* FLAT PAYLOAD — one field per slider, zeros included, so the database
       stores every reader's complete budget, not just what they changed.
       Field names match the columns in ARCHITECTURE.md one-to-one:
         gf_<id>        General Fund slider, −25..25 (% change)
         fund_<id>      a department's spending outside the General Fund,
                        −25..25 (% change; trapped, never reaches the gap)
         rev_fees / rev_property / rev_sales
                        −25..25 (% change of the source's GF revenue)
         rev_marijuana  the recreational marijuana tax rate, 0..10 (%)
         rev_shift      $M of General Fund costs moved onto dedicated funds, 0..5
         demo_<id>      one column per survey item (multi-selects joined by "; ") */
    const payload = { v: WIDGET_VERSION, ts: new Date().toISOString(), scenario: "2027" };
    GF_DEPTS.forEach((d) => { payload[`gf_${d.id}`] = deptPct[d.id] || 0; });
    LOCKED_DEPTS.forEach((f) => { payload[`fund_${f.id}`] = lockedPct[f.id] || 0; });
    payload.rev_fees = rev.fees || 0;               // % change of GF fees & charges
    payload.rev_property = rev.property || 0;       // % change of GF property tax
    payload.rev_sales = rev.sales || 0;             // % change of GF sales & use tax
    payload.rev_marijuana = rev.marijuana ?? REV_START.marijuana;   // rate, %
    payload.rev_shift = round(shifted);             // $M moved onto dedicated funds
    payload.spend_change = round(netSpendChange);
    payload.revenue_only = round(revenueOnly);
    payload.used_vote = usedVote;
    payload.used_revenue = usedRevenue;
    payload.used_shift = usedShift;
    payload.top_cut = topCut && topCut.amt > 0.01 ? topCut.name : null;
    DEMO.forEach((q) => { const v = demo[q.id]; payload[`demo_${q.id}`] = Array.isArray(v) ? v.join("; ") : (v ?? null); });

    const next = await writeAgg({ revShare, usedRevenue, usedVote, usedShift, topCut, payload });
    if (next) setAgg(next);
    setSubmitted(true);
  }, [balanced, submitted, deptPct, lockedPct, rev, shifted, netSpendChange, revenueOnly, usedRevenue, usedVote, usedShift, totalFix, demo]);

  const reset = () => { setDeptPct({}); setLockedPct({}); setRev(REV_START); setDemo({}); setSubmitted(false); };
  const demoCount = Object.values(demo).filter((v) => (Array.isArray(v) ? v.length : v)).length;
  const canSubmit = balanced && !submitted && demoCount > 0;

  return (
    <div ref={rootRef} style={{ background: C.paper, color: C.ink, fontFamily: FONT }} className="w-full">
      <style>{`
        @media (prefers-reduced-motion: reduce){ *{transition:none!important;animation:none!important} }
        .bbw, .bbw *{ box-sizing:border-box; }
        .bbw{ font-family:${FONT}; -webkit-text-size-adjust:100%; text-size-adjust:100%; }
        .bbw button, .bbw a, .bbw input[type=range]{ touch-action:manipulation; }
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
        .bbw .tickwrap{ --th:20px; }   /* the thumb's width, so a tick lines up with the value it marks */
        /* Bigger touch targets on phones/tablets (coarse pointers) — WCAG 2.5.8 */
        @media (pointer: coarse){
          .bbw input[type=range]{ height:8px; }
          .bbw input[type=range]::-webkit-slider-thumb{ width:28px; height:28px; }
          .bbw input[type=range]::-moz-range-thumb{ width:28px; height:28px; }
          .bbw .tickwrap{ --th:28px; }
          .bbw button{ min-height:44px; }
        }
      `}</style>

      <div className="bbw mx-auto" style={{ maxWidth: 680, padding: "8px 16px 56px" }}>

        <header className="pt-6 pb-5" style={{ borderBottom: `3px solid ${C.lime}` }}>
          <div className="tnum" style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: C.blueDk, fontWeight: 800 }}>Charting Boulder · Interactive</div>
          <h1 style={{ fontSize: "clamp(23px,5.6vw,32px)", fontWeight: 800, lineHeight: 1.08, marginTop: 8, letterSpacing: "-0.02em" }}>Balance Boulder’s 2027 budget</h1>
          <p style={{ fontSize: 15.5, lineHeight: 1.5, color: C.inkSoft, marginTop: 10 }}>
            Boulder’s General Fund, which pays for police, firefighters and much of city government, would come up <strong style={{ color: C.ink }}>{fmt(GAP)} short in 2027</strong> if the city kept all of this year’s services. The city manager’s recommended budget closes the gap. The city council votes Oct. 15. Now it’s your turn: Close the gap by cutting spending, changing taxes or shifting costs onto voter-dedicated funds, within the limits imposed by state law and voters.
          </p>
        </header>

        {/* Reveal bar */}
        <section className="mt-6">
          <Eyebrow>Boulder’s $552.6M budget</Eyebrow>
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 8 }}>The General Fund, where the shortfall is, holds <strong style={{ color: C.ink }}>{fmt1(GENERAL_FUND)}, about {pctMovable.toFixed(0)}¢ of every budget dollar</strong>, and it’s the one large pot the council has broad discretion over. The rest is restricted to specific purposes. The {fmt1(TOTAL)} total includes {fmt1(OPERATING)} for operations and {fmt1(CAPITAL)} for one-time capital projects.</p>
          <div className="mt-2 rounded-md overflow-hidden flex" style={{ height: 44, border: `1px solid ${C.ink}` }}>
            <div style={{ width: `${pctMovable}%`, background: C.lime, color: C.ink }} className="flex items-center justify-center"><span style={{ fontSize: 12, fontWeight: 800 }}>{pctMovable.toFixed(0)}¢ General Fund</span></div>
            <div style={{ width: `${100 - pctMovable}%`, background: C.lockBg, color: C.inkSoft }} className="flex items-center justify-center gap-1"><Lock size={12} /><span style={{ fontSize: 11.5, fontWeight: 700 }}>{(100 - pctMovable).toFixed(0)}¢ other funds</span></div>
          </div>
        </section>

        {/* The gap explainer scrolls away; the live tally below sticks. */}
        <section className="mt-6">
          <Eyebrow>The 2027 gap</Eyebrow>
          <p style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 6 }}>The <strong style={{ color: C.ink }}>{fmt(GAP)}</strong> is the city’s own estimate, and it comes on top of cuts made in 2025 and 2026. Colorado law requires a balanced budget, so the council has to close the gap before it adopts one. The gap also comes back every year. One-time money only postpones it. <em>The city’s plan for closing it is under Sources &amp; method, below.</em></p>
        </section>

        {/* Live balance — sticks to the top of the screen so the surplus/deficit
            stays in view while you scroll down and tweak the sliders. */}
        {/* Sticks to the top of whatever is scrolling: the iframe viewport in the
            standalone build, the article page in the inline build. --bbw-sticky-top
            is set by the web component to clear the host site's own sticky header;
            it falls back to 0 everywhere else. */}
        <section className="mt-3 rounded-lg" style={{ background: C.limeTint, border: `1px solid ${C.hair}`, position: "sticky", top: "var(--bbw-sticky-top, 0px)", zIndex: 30, padding: 12, boxShadow: "0 6px 16px rgba(26,26,26,0.10)" }}>
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-baseline gap-2" style={{ minWidth: 0 }}>
              <span className="tnum" style={{ fontSize: 22, fontWeight: 800, lineHeight: 1, color: balanced ? C.green : C.red }}>{balanced ? "Closed" : fmt(remaining)}</span>
              <span style={{ fontSize: 11, letterSpacing: "0.07em", textTransform: "uppercase", fontWeight: 800, color: C.inkSoft }}>{balanced ? "2027 gap" : "left to close"}</span>
            </div>
            <div style={{ fontSize: 12, color: C.inkSoft }}>{netSpendChange === 0 ? "no spending change" : `${signed(netSpendChange)} spending`} · {Math.abs(revenueOnly) < 0.005 ? "no revenue change" : `${signed(revenueOnly)} revenue`}{shifted > 0 ? ` · ${fmt(shifted)} shifted` : ""}</div>
          </div>
          <div className="mt-2">
            <GapBar label={`2027 General Fund gap: ${fmt(GAP)}`} gap={GAP} remaining={remaining} balanced={balanced} />
          </div>
        </section>

        {/* General Fund — bidirectional */}
        <section className="mt-7">
          <SectionHead icon={<Building2 size={18} style={{ color: C.ink }} />} title="The General Fund: Money the council can move" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>The sliders below break down, by department, the {fmt1(GF_STATUS_QUO)} the General Fund would spend in 2027 before the city’s cuts and changes. Slide one left to cut spending and shrink the gap, or right to spend more and widen it. Heading into 2027, the city manager asked every department to draw up <strong style={{ color: C.ink }}>ongoing cuts of about 4%</strong>.</p>
          <p style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 6 }}><span aria-hidden="true" style={{ display: "inline-block", width: 3, height: 11, background: C.blueDk, borderRadius: 2, marginRight: 6, verticalAlign: "-1px" }} />The blue tick shows where the recommended budget puts each department.</p>
          <div className="mt-3 grid gap-2.5">
            {GF_DEPTS.map((d) => {
              const pct = deptPct[d.id] || 0, delta = d.base * (pct / 100);
              const city = ((d.amount + (d.moved || 0)) / d.base - 1) * 100;
              const ticks = [{ value: city, label: `proposed ${city > 0 ? "+" : "−"}${Math.abs(city).toFixed(1)}%`, title: `The recommended budget: ${fmt(d.amount)}${d.moved ? `, plus ${fmt(d.moved)} it moves onto dedicated funds` : ""}. In 2026: ${fmt(d.was)}.` }];
              return (
                <div key={d.id} className="rounded-md p-3" style={{ background: C.paper, border: `1px solid ${C.hair}` }}>
                  <div className="flex items-center justify-between gap-2">
                    <div style={{ minWidth: 0 }}><div style={{ fontSize: 14.5, fontWeight: 700 }}>{deptLabel(d)}<Cites sources={d.sources} /></div>{d.note && <div style={{ fontSize: 11.5, color: C.inkSoft }}>{d.note}</div>}</div>
                    <div className="tnum text-right" style={{ flexShrink: 0 }}><span style={{ fontSize: 14, fontWeight: 800 }}>{fmt(d.base)}</span><span style={{ fontSize: 12, color: pct === 0 ? C.inkSoft : C.blueDk, marginLeft: 8, fontWeight: 700 }}>{pct === 0 ? "unchanged" : signed(delta)}</span></div>
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <TickTrack ticks={ticks} min={-25} max={25}>
                      <input type="range" min={-25} max={25} step={1} value={pct} onChange={(e) => { setDeptPct({ ...deptPct, [d.id]: +e.target.value }); setSubmitted(false); }} aria-label={`Adjust ${deptLabel(d)}`} aria-valuetext={pct === 0 ? "no change" : `${pct > 0 ? "increase" : "cut"} ${Math.abs(pct)} percent, ${signed(delta)}`} />
                    </TickTrack>
                    <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, flexShrink: 0, textAlign: "right", fontWeight: 700 }}>{pct > 0 ? "+" : ""}{pct}%</span>
                  </div>
                  <Scale left="−25% cut" mid="0" right="+25% more" ticks={ticks} min={-25} max={25} />
                </div>
              );
            })}
          </div>
        </section>

        {/* Revenue */}
        <section className="mt-7">
          <SectionHead icon={<Coins size={18} style={{ color: C.blueDk }} />} title="Revenue" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>The fee and tax sliders start at zero and move both ways, so you can cut a tax as well as raise one, or trade sales tax for property tax. Blue ticks mark what the recommended budget proposes.</p>
          <div className="mt-3 grid gap-2.5">
            {REVENUE.map((r) => {
              const v = rev[r.id] ?? REV_START[r.id]; const yield_ = revYield(r, v);
              const moved = r.type === "rate" ? v !== r.now : v !== 0;
              const headline = r.type === "rate" ? fmt(r.base + yield_) : r.type === "dollars" ? fmt(v) : fmt(r.base);
              const change = r.type === "dollars" ? (v > 0 ? `${fmt(v)} moved` : "none moved") : (!moved ? "unchanged" : signed(yield_));
              const changeColor = !moved ? C.inkSoft : r.type === "dollars" ? C.blueDk : (yield_ > 0 ? C.green : C.red);
              const set = (x) => { setRev({ ...rev, [r.id]: x }); setSubmitted(false); };
              const ticks = r.city == null ? [] : [{ value: r.city, label: r.type === "rate" ? `proposed ${r.city}%` : `proposed ~${fmt(r.city)}`, title: r.type === "rate" ? `The recommended budget sets it at ${r.city}%` : `The recommended budget moves about ${fmt(r.city)}` }];
              return (
                <div key={r.id} className="rounded-md p-3" style={{ background: r.locked ? C.lockBg : C.paper, border: `1px solid ${r.locked ? C.lock : C.hair}` }}>
                  <div className="flex items-center justify-between gap-2">
                    <div style={{ minWidth: 0 }}>
                      <div className="flex items-center gap-1.5 flex-wrap"><span style={{ fontSize: 14.5, fontWeight: 700, color: r.locked ? C.inkSoft : C.ink }}>{r.label}</span>{r.locked && <Lock size={12} style={{ color: C.lock }} />}</div>
                      {r.pieces && <div style={{ fontSize: 11.5, color: C.inkSoft }}>{r.pieces}</div>}
                    </div>
                    <div className="tnum text-right" style={{ flexShrink: 0 }}>{r.locked ? <span style={{ fontSize: 14, fontWeight: 800, color: C.lockText }}>—</span> : <><span style={{ fontSize: 14, fontWeight: 800 }}>{headline}</span><span style={{ fontSize: 12, color: changeColor, marginLeft: 8, fontWeight: 700 }}>{change}</span></>}</div>
                  </div>
                  {r.locked ? null : r.type === "rate" ? (
                    <>
                      <div className="flex items-center gap-3 mt-2">
                        <TickTrack ticks={ticks} min={r.min} max={r.max}>
                          <input type="range" min={r.min} max={r.max} step={r.step} value={v} onChange={(e) => set(+e.target.value)} aria-label={`Set the ${r.label.toLowerCase()} rate`} aria-valuetext={`${v} percent, raising ${fmt(r.base + yield_)}${moved ? `, ${signed(yield_)}` : ", today's rate"}`} />
                        </TickTrack>
                        <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, flexShrink: 0, textAlign: "right", fontWeight: 700 }}>{v}%</span>
                      </div>
                      <Scale left={`${r.min}%`} right={`${r.max}% cap`} marks={[{ value: r.now, label: `${r.now}% today` }]} ticks={ticks} min={r.min} max={r.max} />
                    </>
                  ) : r.type === "dollars" ? (
                    <>
                      <div className="flex items-center gap-3 mt-2">
                        <TickTrack ticks={ticks} min={r.min} max={r.max}>
                          <input type="range" min={r.min} max={r.max} step={r.step} value={v} onChange={(e) => set(+e.target.value)} aria-label={r.label} aria-valuetext={v > 0 ? `${fmt(v)} moved onto dedicated funds` : "nothing moved"} />
                        </TickTrack>
                        <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, flexShrink: 0, textAlign: "right", fontWeight: 700 }}>{fmt(v)}</span>
                      </div>
                      <Scale left="$0" right={fmt(r.max)} ticks={ticks} min={r.min} max={r.max} />
                    </>
                  ) : (
                    <>
                      <div className="flex items-center gap-3 mt-2">
                        <input type="range" min={-25} max={25} step={1} value={v} onChange={(e) => set(+e.target.value)} aria-label={`Adjust ${r.label}`} aria-valuetext={v === 0 ? "no change" : `${v > 0 ? "raise" : "cut"} ${Math.abs(v)} percent, ${signed(yield_)}`} />
                        <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, flexShrink: 0, textAlign: "right", fontWeight: 700 }}>{v > 0 ? "+" : ""}{v}%</span>
                      </div>
                      <Scale left="−25% cut" mid="0" right="+25% more" />
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Locked-by-voters revenue */}
        <section className="mt-7">
          <SectionHead icon={<Lock size={18} style={{ color: C.lock }} />} title="Revenue and spending chosen by voters" />
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>On every $100 of taxable sales, the city collects $3.86 in sales tax. The General Fund gets $1.72 of it (the sales-tax slider above). Voters set aside the other $2.14 for five funds, and the council can’t change those rates or spend that money on anything else. Revenue figures are from the 2027 recommended budget.</p>
          <div className="mt-3 grid gap-2">
            {DEDICATED_RATES.map((d) => (
              <div key={d.id} className="rounded-md p-3" style={{ background: C.lockBg, border: `1px solid ${C.lock}` }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap" style={{ minWidth: 0 }}><Lock size={12} style={{ color: C.lock }} /><span style={{ fontSize: 14, fontWeight: 700, color: C.inkSoft }}>{d.label}</span></div>
                  <div className="tnum text-right" style={{ flexShrink: 0 }}>
                    <span style={{ fontSize: 12.5, fontWeight: 700, color: C.inkSoft }}>{d.rate.toFixed(d.rate < 0.1 ? 3 : 2)}%</span>{d.revM != null && <span style={{ fontSize: 14, fontWeight: 800, color: C.inkSoft, marginLeft: 8 }}>{fmt(d.revM)}/yr</span>}
                  </div>
                </div>
                <div style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 8 }}>{d.note}</div>
              </div>
            ))}
          </div>
          <div className="mt-2 rounded-md p-3" style={{ background: C.lockBg, border: `1px solid ${C.lock}` }}>
            <span style={{ fontSize: 12.5, color: C.inkSoft }}>Some new 2027 revenue is restricted from the start. The Transportation Maintenance Fee adds about <strong style={{ color: C.ink }}>$3.0M</strong>, which can pay only for transportation maintenance. Utility rates rise <strong style={{ color: C.ink }}>5–7%</strong>, and that money can pay only for water, wastewater and stormwater.</span>
          </div>
          <p style={{ fontSize: 12.5, color: C.inkSoft, marginTop: 10 }}><strong style={{ color: C.ink }}>The Nov. 3 ballot.</strong> Voters will decide four city measures this fall: a <strong style={{ color: C.ink }}>$400M recreation-and-safety bond</strong> for aging rec centers, fire stations and a police facility (about $400 a year on a $1 million home); a charter change letting the city borrow against property’s actual value rather than its assessed value; collective bargaining for firefighters; and a <strong style={{ color: C.ink }}>$4,000-a-year tax on homes left empty</strong> more than half the year. Of those, only the vacancy tax would generate flexible revenue that could go into the General Fund. The city estimates it would raise about $6M annually, starting in 2028, too late to help close the 2027 gap. A parks mill levy the council studied, which would have opened dedicated money to wider use, didn’t make the ballot.</p>
        </section>

        {/* Locked spending funds */}
        <section className="mt-7">
          <button onClick={() => setShowLocked(!showLocked)} className="w-full flex items-center justify-between" style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}>
            <SectionHead icon={<Lock size={18} style={{ color: C.lock }} />} title={`The other ${fmt1(lockedTotal)}: Cuts here don’t close the General Fund gap`} />
            {showLocked ? <ChevronUp size={18} color={C.inkSoft} /> : <ChevronDown size={18} color={C.inkSoft} />}
          </button>
          <p style={{ fontSize: 13.5, color: C.inkSoft, marginTop: 4 }}>This is each department’s spending outside the General Fund, paid for by utility rates, voter-dedicated taxes, fees and grants. The {fmt1(CAPITAL)} capital budget is spread across these rows. Move the sliders if you like. But savings here stay within those restricted funds and can’t be used to close the General Fund gap.</p>
          {showLocked && (
            <div className="mt-3 grid gap-2">
              {LOCKED_DEPTS.map((f) => {
                const pct = lockedPct[f.id] || 0, delta = f.amount * (pct / 100);
                return (
                  <div key={f.id} className="rounded-md p-3" style={{ background: C.wash, border: `1px solid ${C.hair}` }}>
                    <div className="flex items-center justify-between gap-2">
                      <div style={{ minWidth: 0 }}><div className="flex items-center gap-1.5 flex-wrap"><span style={{ fontSize: 14, fontWeight: 700, color: C.inkSoft }}>{f.name}</span></div><div style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 1 }}>{f.why}</div></div>
                      <div className="tnum text-right" style={{ flexShrink: 0 }}><span style={{ fontSize: 14, fontWeight: 800, color: C.inkSoft }}>{fmt(f.amount)}</span>{pct !== 0 && <div style={{ fontSize: 11, color: C.lockText, fontWeight: 700 }}>{signed(delta)} stays in its funds</div>}</div>
                    </div>
                    <div className="flex items-center gap-3 mt-2">
                      <input className="lk" type="range" min={-25} max={25} step={1} value={pct} onChange={(e) => { setLockedPct({ ...lockedPct, [f.id]: +e.target.value }); setSubmitted(false); }} aria-label={`Adjust ${f.name} spending outside the General Fund`} aria-valuetext={pct === 0 ? "no change" : `${pct > 0 ? "increase" : "cut"} ${Math.abs(pct)} percent; ${signed(delta)} stays in its funds`} />
                      <span className="tnum" style={{ fontSize: 12, color: C.inkSoft, width: 46, flexShrink: 0, textAlign: "right", fontWeight: 700 }}>{pct > 0 ? "+" : ""}{pct}%</span>
                    </div>
                  </div>
                );
              })}
              {Math.abs(trappedChange) > 0.05 && (
                <div className="rounded-md p-3 flex items-start gap-2" style={{ background: C.limeTint, border: `1px solid ${C.lock}` }}>
                  <AlertTriangle size={15} style={{ color: C.red, marginTop: 2, flexShrink: 0 }} />
                  <span style={{ fontSize: 13 }}>You’ve changed locked spending by <strong>{signed(trappedChange)}</strong>. None of it reaches the General Fund gap, because each fund can spend its money only on its own purpose.</span>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Submit + aggregate */}
        <section className="mt-7 rounded-lg p-4" style={{ background: C.wash, border: `1px solid ${C.hair}` }}>
          <div style={{ maxWidth: 540 }}>
            <Eyebrow>{balanced ? "You closed the 2027 gap" : "Keep going"}</Eyebrow>
            <p style={{ fontSize: 14, color: C.inkSoft, marginTop: 6 }}>
              {balanced
                ? <>It took {[
                    netCuts > 0.01 && <strong key="c" style={{ color: C.ink }}>{fmt(netCuts)} in net cuts</strong>,
                    revenueOnly > 0.01 && <strong key="r" style={{ color: C.ink }}>{fmt(revenueOnly)} in recurring revenue</strong>,
                    shifted > 0 && <strong key="s" style={{ color: C.ink }}>{fmt(shifted)} moved onto dedicated funds</strong>,
                  ].filter(Boolean).reduce((acc, el, i, arr) => acc.concat(i === 0 ? [el] : [i === arr.length - 1 ? " and " : ", ", el]), [])}.</>
                : <>You’re still <strong style={{ color: C.ink }}>{fmt(remaining)} short</strong>. Cut deeper, raise a fee or a tax, or move a cost onto a dedicated fund.</>}
            </p>
          </div>

          {balanced && (
            <div className="mt-4 rounded-lg p-3" style={{ background: C.limeTint, border: `2px solid ${demoCount > 0 ? C.limeDk : C.ink}` }}>
              <div className="flex items-start justify-between gap-3">
                <div style={{ minWidth: 0 }}>
                  <div className="flex items-center gap-1.5"><Users size={15} style={{ color: C.ink }} /><span style={{ fontSize: 14.5, fontWeight: 800 }}>One step before you add your budget</span></div>
                  <div style={{ fontSize: 13, color: C.inkSoft, marginTop: 3 }}>Answer at least one question; <em>“Prefer not to say”</em> counts. Answers are anonymous.</div>
                </div>
                <span className="tnum flex items-center gap-1" style={{ fontSize: 12, fontWeight: 800, flexShrink: 0, color: demoCount > 0 ? C.green : C.inkSoft }}>{demoCount > 0 && <Check size={13} />}{demoCount} answered</span>
              </div>
              <button onClick={() => setShowDemo(!showDemo)} className="flex items-center gap-1" style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, marginTop: 8, fontSize: 12, fontWeight: 800, color: C.blueDk }}>{showDemo ? <>Hide questions <ChevronUp size={13} /></> : <>Show questions <ChevronDown size={13} /></>}</button>
              {showDemo && (
                <div className="mt-3 grid gap-3">
                  <p style={{ fontSize: 11.5, color: C.inkSoft }}>The questions are adapted from the city’s 2025 Boulder Valley Comprehensive Plan survey.</p>
                  {DEMO.map((d) => <DemoQuestion key={d.id} d={d} value={demo[d.id]} onChange={(val) => setDemo({ ...demo, [d.id]: val })} />)}
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 mt-4">
            <button onClick={submit} disabled={!canSubmit} className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 800, padding: "10px 18px", borderRadius: 7, cursor: canSubmit ? "pointer" : "not-allowed", border: `2px solid ${canSubmit ? C.ink : C.hair}`, background: canSubmit ? C.lime : C.hair, color: canSubmit ? C.ink : C.inkSoft }}><ArrowDownToLine size={14} /> {submitted ? "Added to the tally" : "Add my budget"}</button>
            <button onClick={reset} className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 700, padding: "10px 14px", borderRadius: 7, cursor: "pointer", border: `1.5px solid ${C.hair}`, background: C.paper, color: C.inkSoft }}><RotateCcw size={14} /> Reset</button>
            {balanced && !submitted && demoCount === 0 && <span style={{ fontSize: 12.5, color: C.blueDk, fontWeight: 700 }}>Pick at least one answer above to add your budget.</span>}
            {submitted && <span className="flex items-center gap-1" style={{ fontSize: 12.5, color: C.green, fontWeight: 700 }}><Check size={14} /> Your budget is saved. Thank you.</span>}
          </div>
          {submitted && (
            <div className="mt-4 pt-3" style={{ borderTop: `1px solid ${C.hair}` }}>
              <div className="flex items-center gap-1.5"><Users size={14} style={{ color: C.inkSoft }} /><Eyebrow>Other readers’ budgets</Eyebrow></div>
              {aggState === "loading" && <p style={{ fontSize: 13, color: C.inkSoft, marginTop: 8 }}>Loading the shared tally…</p>}
              {aggState === "ready" && agg && (agg.n === 0 ? <p style={{ fontSize: 13, color: C.inkSoft, marginTop: 8 }}>No budgets have been counted yet. Submissions are anonymous, and readers see only the combined results.</p> : <AggregateView agg={agg} />)}
              <p style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 10, fontStyle: "italic" }}>Readers chose to take part, so this is not a scientific survey of Boulder.</p>
              <p style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 4, fontStyle: "italic" }}>For comparison, the city’s own trade-off exercise earlier this year, <Doc to={OFFICIAL.fundOurFuture}>Fund Our Future</Doc>, heard from more than 500 people, who ranked wildfire response and facility maintenance highest.</p>
            </div>
          )}
        </section>

        {/* Provenance & trust contract. The column's prose carries the hook, the
            peg, and the diagnostic close; the widget keeps only what speaks to
            its own numbers — what's official vs. modeled, and the verify link. */}
        <section className="mt-8" style={{ borderTop: `3px solid ${C.ink}`, paddingTop: 18 }}>
          <button onClick={() => setShowSources(!showSources)} aria-expanded={showSources} className="w-full flex items-center justify-between" style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}>
            <Eyebrow>Sources &amp; method</Eyebrow>
            {showSources ? <ChevronUp size={18} color={C.inkSoft} /> : <ChevronDown size={18} color={C.inkSoft} />}
          </button>
          <p style={{ fontSize: 14, lineHeight: 1.55, color: C.inkSoft, marginTop: 10 }}>Budget totals, department figures, revenue bases, tax rates and legal limits come from <Doc to={OFFICIAL.book}>the city manager’s 2027 recommended budget</Doc> and <Doc to={OFFICIAL.tabor}>Colorado law</Doc>. What each revenue change would raise is an estimate, and so is each department’s starting point, its cost before the city’s 2027 changes. <Doc to={PROVENANCE}>The provenance file</Doc> traces every number to its source and says which ones are estimates.</p>
          {showSources && (<>
          <p style={{ fontSize: 13, lineHeight: 1.55, color: C.inkSoft, marginTop: 10 }}><strong style={{ color: C.ink }}>Rising costs, flat revenue.</strong> Payroll grows under <Doc to={OFFICIAL.message}>new contracts</Doc> that give police and firefighters 5% raises and most other union staff 4%, and software, insurance and other contracts add to the bill. <Doc to={OFFICIAL.briefMore}>Revenue hasn’t kept pace</Doc>: sales and use tax has been flat since 2023, and property tax is down 2.4% under recent state law. The <Doc to={OFFICIAL.budgetPage}>May 2026 Financial Forecast</Doc> put the gap at $6.5M; <Doc to={OFFICIAL.brief}>the recommended budget</Doc>, <Doc to={OFFICIAL.release}>released Aug. 28</Doc>, puts it at {fmt(GAP)}.</p>
          <p style={{ fontSize: 13, lineHeight: 1.55, color: C.inkSoft, marginTop: 8 }}><strong style={{ color: C.ink }}>The city’s plan.</strong> <Doc to={OFFICIAL.glance}>The recommended budget</Doc> eliminates 24 positions, 13 of them filled, ends the photo-radar vans and trims pool hours and custodial service. It moves about $0.3M of General Fund costs onto the Open Space and sugary-drink taxes, raises the recreational marijuana tax from 3.5% to 5.5% and increases several licensing and parking-permit fees. It also adds three police lieutenants. The council holds hearings Oct. 1 and 15 and can change any of it before it adopts the budget Oct. 15.</p>
          <p style={{ fontSize: 13, lineHeight: 1.55, color: C.inkSoft, marginTop: 8 }}><strong style={{ color: C.ink }}>Past gaps.</strong> In mid-2025, the city closed an $8–10M gap with a hiring freeze, 5% savings from each department and cuts to one-time transfers. For 2026, it closed $7.5M with department cuts and reorganizations that eliminated 19 mostly vacant positions, plus about $6M in new citywide fees: $2.25M for transportation maintenance, $2.6M from speed-on-green cameras, $0.8M from parking and $0.4M from single-family expansion. It kept the <Doc to={OFFICIAL.policies}>emergency reserve</Doc>, about 16.7% of operating spending, at its target. The city holds its reserves for downturns.</p>
          <div className="mt-4">
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.04em", color: C.inkSoft }}>OFFICIAL BUDGET DOCUMENTS</div>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12.5, lineHeight: 1.6, color: C.inkSoft }}>
              {Object.values(OFFICIAL).map((d) => (
                <li key={d.url} style={{ marginTop: 3 }}><a href={d.url} target="_blank" rel="noopener noreferrer" style={{ color: C.blueDk, fontWeight: 600, textDecoration: "none" }}>{d.label}</a></li>
              ))}
            </ul>
          </div>
          <div className="mt-4">
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.04em", color: C.inkSoft }}>RELATED REPORTING</div>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12.5, lineHeight: 1.6, color: C.inkSoft }}>
              {Object.values(SRC).map((d) => (
                <li key={d.url} style={{ marginTop: 3 }}><a href={d.url} target="_blank" rel="noopener noreferrer" style={{ color: C.blueDk, fontWeight: 600, textDecoration: "none" }}>{d.label}</a></li>
              ))}
            </ul>
          </div>
          </>)}
          <a href={PROVENANCE.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 mt-4" style={{ fontSize: 13.5, fontWeight: 800, color: C.ink, textDecoration: "none", border: `2px solid ${C.ink}`, borderRadius: 7, padding: "9px 14px" }}><Github size={15} /> Verify me: where every number comes from</a>
          <p style={{ fontSize: 11.5, color: C.inkSoft, marginTop: 12, lineHeight: 1.5 }}>Figures in millions of dollars, as of Sept. 29, 2026: the city manager’s recommended budget, before the council’s Oct. 15 vote. Built for Boulder Reporting Lab as a simplified teaching model of the city’s budget.</p>
        </section>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- storage */
function emptyAgg() { return { n: 0, usedRevenue: 0, usedVote: 0, usedShift: 0, revShareSum: 0, cutTally: {} }; }
function round(x) { return Math.round(x * 100) / 100; }

/* Supabase direct-write helpers. PostgREST wants the publishable key in both
   the apikey and Authorization headers. */
function sbHeaders() {
  return { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json" };
}
/* Map the flat payload onto the exact DB columns, reusing the widget's own data
   tables so the stored column set can never drift from the sliders above. */
function sbRow(p) {
  const row = {
    client_ts: p.ts ?? null, client_version: p.v ?? null, scenario: p.scenario ?? null,
    rev_fees: p.rev_fees ?? 0, rev_property: p.rev_property ?? 0, rev_sales: p.rev_sales ?? 0,
    rev_marijuana: p.rev_marijuana ?? REV_START.marijuana, rev_shift: p.rev_shift ?? 0,
    spend_change: p.spend_change ?? 0, revenue_only: p.revenue_only ?? 0,
    used_vote: !!p.used_vote, used_revenue: !!p.used_revenue, used_shift: !!p.used_shift,
    top_cut: p.top_cut ?? null, repeat_client: !!p.repeatClient, raw: p,
  };
  GF_DEPTS.forEach((d) => { row[`gf_${d.id}`] = p[`gf_${d.id}`] ?? 0; });
  LOCKED_DEPTS.forEach((f) => { row[`fund_${f.id}`] = p[`fund_${f.id}`] ?? 0; });
  DEMO.forEach((q) => { row[`demo_${q.id}`] = p[`demo_${q.id}`] ?? null; });
  return row;
}

async function readAgg() {
  if (SB_ENABLED) {
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/budget_aggregate`, { method: "POST", headers: sbHeaders(), body: "{}" });
      return r.ok ? ((await r.json()) || emptyAgg()) : emptyAgg();
    } catch { return emptyAgg(); }
  }
  if (typeof window !== "undefined" && window.storage) { try { const r = await window.storage.get(AGG_KEY, true); return r ? JSON.parse(r.value) : emptyAgg(); } catch { return emptyAgg(); } }
  return emptyAgg();
}

async function writeAgg({ revShare, usedRevenue, usedVote, usedShift, topCut, payload }) {
  // Flag a likely repeat from this browser (best-effort, localStorage only).
  try { if (typeof window !== "undefined" && window.localStorage?.getItem("bb_submitted_v5")) payload.repeatClient = true; window.localStorage?.setItem("bb_submitted_v5", "1"); } catch {}

  if (SB_ENABLED) {
    try {
      const ins = await fetch(`${SUPABASE_URL}/rest/v1/contributions`, { method: "POST", headers: { ...sbHeaders(), Prefer: "return=minimal" }, body: JSON.stringify(sbRow(payload)) });
      if (!ins.ok) return null;
      return await readAgg();   // re-read so the tally includes this submission
    } catch { return null; }
  }
  if (typeof window !== "undefined" && window.storage) {
    try {
      const cur = (await readAgg()) || emptyAgg();
      cur.n += 1;
      cur.usedRevenue += usedRevenue ? 1 : 0;
      cur.usedVote += usedVote ? 1 : 0;
      cur.usedShift = (cur.usedShift || 0) + (usedShift ? 1 : 0);
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
  // Diverging bar with a FIXED symmetric range: −$20M (deficit) on the left to
  // +$20M (surplus) on the right, for both bars. Balanced (0) sits at the
  // center; values past the range clamp to an edge.
  const MIN = -20, MAX = 20, span = MAX - MIN;            // $M
  const surplus = -remaining;                             // + surplus, − deficit
  const zeroPct = ((0 - MIN) / span) * 100;               // balanced line (center)
  const valPct = ((Math.max(MIN, Math.min(MAX, surplus)) - MIN) / span) * 100;
  const fillLeft = Math.min(valPct, zeroPct);             // fill spans balanced ↔ value
  const fillWidth = Math.abs(valPct - zeroPct);
  return (
    <div style={{ marginTop: 10 }}>
      <div className="flex items-center justify-between gap-2">
        <div style={{ minWidth: 0 }}>
          <span style={{ fontSize: 13.5, fontWeight: 800 }}>{label}</span>
          {sub && <span style={{ fontSize: 11.5, color: C.inkSoft, marginLeft: 6 }}>{sub}</span>}
        </div>
        <div className="flex items-center gap-1.5" style={{ flexShrink: 0 }}>
          <span className="tnum" style={{ fontSize: 13.5, fontWeight: 800, color: balanced ? C.green : C.red }}>
            {balanced ? (surplus > 0.05 ? `+${fmt(surplus)}` : "Gap closed") : `${fmt(remaining)} short`}
          </span>
          <span aria-hidden="true" style={{ fontSize: 15, lineHeight: 1 }}>{balanced ? "\u2705" : "\u2B1C"}</span>
        </div>
      </div>
      <div className="relative" style={{ height: 12, marginTop: 5, background: C.paper, border: `1px solid ${C.hair}`, borderRadius: 99, overflow: "hidden" }}>
        {/* deficit (left) / surplus (right) faint zones, split at the balanced line */}
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${zeroPct}%`, background: "rgba(207,46,46,0.06)" }} />
        <div style={{ position: "absolute", left: `${zeroPct}%`, top: 0, bottom: 0, right: 0, background: "rgba(31,122,77,0.06)" }} />
        {/* fill */}
        <div style={{ position: "absolute", top: 0, bottom: 0, left: `${fillLeft}%`, width: `${fillWidth}%`, background: balanced ? C.green : C.red, transition: "left .2s ease, width .2s ease" }} />
        {/* balanced (0) tick */}
        <div style={{ position: "absolute", left: `${zeroPct}%`, top: -1, bottom: -1, width: 2, background: C.ink, transform: "translateX(-1px)" }} />
      </div>
      <div className="relative" style={{ fontSize: 10, color: C.inkSoft, marginTop: 2, height: 13 }} aria-hidden="true">
        <span style={{ position: "absolute", left: 0 }}>−$20M</span>
        <span style={{ position: "absolute", left: `${zeroPct}%`, transform: "translateX(-50%)", fontWeight: 700 }}>closed</span>
        <span style={{ position: "absolute", right: 0 }}>+$20M</span>
      </div>
    </div>
  );
}
/* A slider with ticks drawn behind it. Each tick marks a value in the
   slider's own units; the thumb's half-width (--th) is allowed for, so a tick
   sits exactly where the thumb would be at that value. */
function TickTrack({ ticks = [], min, max, children }) {
  return (
    <div className="tickwrap" style={{ position: "relative", flex: 1, minWidth: 0, display: "flex", alignItems: "center" }}>
      {ticks.map((t) => {
        const f = (t.value - min) / (max - min);
        if (!(f >= 0 && f <= 1)) return null;
        return <span key={t.label} aria-hidden="true" style={{ position: "absolute", left: `calc(var(--th) / 2 + (100% - var(--th)) * ${f.toFixed(4)})`, top: "50%", width: 3, height: 16, transform: "translate(-50%, -50%)", background: C.blueDk, borderRadius: 2, pointerEvents: "none", zIndex: 0 }} />;
      })}
      <div style={{ position: "relative", zIndex: 1, width: "100%", display: "flex" }}>{children}</div>
    </div>
  );
}

/* The labels under a slider, mirroring the slider row (flexible track + 12px
   gap + fixed 46px column) so each label sits under the value it names: the
   ends, an optional centre, optional grey marks, and the blue tick labels. */
function Scale({ left, mid, right, marks = [], ticks = [], min, max }) {
  const pos = (v) => `${Math.max(7, Math.min(93, ((v - min) / (max - min)) * 100))}%`;
  return (
    <>
      <div className="flex gap-3 mt-1" aria-hidden="true">
        <div className="scale" style={{ flex: 1, minWidth: 0, marginTop: 0, position: "relative", height: 16 }}>
          <span style={{ position: "absolute", left: 0 }}>{left}</span>
          {mid != null && <span style={{ position: "absolute", left: "50%", transform: "translateX(-50%)" }}>{mid}</span>}
          {marks.map((m) => <span key={m.label} style={{ position: "absolute", left: pos(m.value), transform: "translateX(-50%)" }}>{m.label}</span>)}
          <span style={{ position: "absolute", right: 0 }}>{right}</span>
        </div>
        <span style={{ width: 46, flexShrink: 0 }} />
      </div>
      {ticks.length > 0 && (
        <div className="flex gap-3" aria-hidden="true">
          <div style={{ flex: 1, minWidth: 0, position: "relative", height: 14 }}>
            {ticks.map((t) => <span key={t.label} title={t.title} style={{ position: "absolute", left: pos(t.value), transform: "translateX(-50%)", fontSize: 10.5, fontWeight: 800, color: C.blueDk, whiteSpace: "nowrap" }}>{t.label}</span>)}
          </div>
          <span style={{ width: 46, flexShrink: 0 }} />
        </div>
      )}
    </>
  );
}

function Cites({ sources }) {
  // Earlier-coverage reference links ([1], [2] …) are disabled per request; each
  // row keeps its `sources` data. Delete the next line to restore the links.
  return null;
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
/* An inline link to an official document: underlined, so it doesn't rely on
   colour alone. */
function Doc({ to, children }) { return <a href={to.url} target="_blank" rel="noopener noreferrer" style={{ color: C.blueDk, fontWeight: 600, textDecoration: "underline", textUnderlineOffset: 2 }}>{children}</a>; }
function Eyebrow({ children }) { return <div style={{ fontSize: 11, letterSpacing: "0.13em", textTransform: "uppercase", color: C.inkSoft, fontWeight: 800 }}>{children}</div>; }
function SectionHead({ icon, title }) { return <div className="flex items-center gap-2"><span style={{ display: "inline-flex", flexShrink: 0 }}>{icon}</span><h2 style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.01em", lineHeight: 1.15 }}>{title}</h2></div>; }

function AggregateView({ agg }) {
  const pct = (x) => Math.round((x / agg.n) * 100);
  const avgRev = Math.round((agg.revShareSum / agg.n) * 100);
  const topCut = Object.entries(agg.cutTally).sort((a, b) => b[1] - a[1])[0];
  // The tally keys on stored names; show the reader-facing label.
  const shown = (name) => { const d = GF_DEPTS.find((x) => x.name === name); return d ? deptLabel(d) : name; };
  const rows = [
    { label: "raised new revenue", v: pct(agg.usedRevenue) },
    { label: "moved costs onto dedicated funds", v: pct(agg.usedShift || 0) },
  ];
  return (
    <div className="mt-3">
      <div style={{ fontSize: 13, color: C.inkSoft }}><strong style={{ color: C.ink }} className="tnum">{agg.n}</strong> {agg.n === 1 ? "reader has" : "readers have"} closed it. On average, they covered <strong style={{ color: C.ink }} className="tnum">{avgRev}%</strong> of the gap with new revenue and the rest with cuts or costs moved onto dedicated funds.{topCut ? <> Their deepest cut fell most often on <strong style={{ color: C.ink }}>{shown(topCut[0])}</strong>.</> : null}</div>
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
