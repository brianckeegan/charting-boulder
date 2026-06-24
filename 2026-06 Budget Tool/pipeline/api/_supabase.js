// Thin helpers over Supabase's auto-generated REST API (PostgREST) plus a CORS
// allowlist. No SDK, no dependencies — just the global fetch the Vercel Node
// runtime already provides, so cold starts stay fast.

const URL = process.env.SUPABASE_URL || "https://iplcjxbazezpjdzdpjxx.supabase.co";
// The server-side SECRET key (sb_secret_… or the legacy service_role JWT). It
// bypasses Row Level Security, so it lives ONLY in Vercel env vars — never in
// the browser or in committed code.
const SERVICE_KEY =
  process.env.SUPABASE_SECRET_KEY ||
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.SUPABASE_SERVICE_KEY ||
  "";

// Comma-separated origin allowlist, or "*". Lock this to your site once known.
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGIN || "*")
  .split(",").map((s) => s.trim()).filter(Boolean);

export function missingConfig() {
  const missing = [];
  if (!URL) missing.push("SUPABASE_URL");
  if (!SERVICE_KEY) missing.push("SUPABASE_SECRET_KEY");
  return missing;
}

// ---- CORS (allowlist) ------------------------------------------------------
export function applyCors(req, res, methods) {
  const origin = req.headers.origin;
  if (ALLOWED_ORIGINS.includes("*")) {
    res.setHeader("Access-Control-Allow-Origin", "*");
  } else if (origin && ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  } else {
    res.setHeader("Access-Control-Allow-Origin", ALLOWED_ORIGINS[0] || "null");
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", `${methods}, OPTIONS`);
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Max-Age", "86400");
}

export function handlePreflight(req, res, methods) {
  applyCors(req, res, methods);
  if (req.method === "OPTIONS") { res.status(204).end(); return true; }
  return false;
}

// ---- PostgREST -------------------------------------------------------------
const headers = () => ({
  apikey: SERVICE_KEY,
  Authorization: `Bearer ${SERVICE_KEY}`,
  "Content-Type": "application/json",
});

// Insert one row. Throws on a non-2xx so the caller can surface a 502.
export async function insertContribution(row) {
  const r = await fetch(`${URL}/rest/v1/contributions`, {
    method: "POST",
    headers: { ...headers(), Prefer: "return=minimal" },
    body: JSON.stringify(row),
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`insert failed (${r.status}): ${detail.slice(0, 500)}`);
  }
}

// Read the precomputed public tally via budget_aggregate(). Falls back to an
// empty aggregate so a read failure never blanks the widget.
export async function fetchAggregate() {
  const r = await fetch(`${URL}/rest/v1/rpc/budget_aggregate`, {
    method: "POST", headers: headers(), body: "{}",
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`aggregate failed (${r.status}): ${detail.slice(0, 500)}`);
  }
  const agg = await r.json();
  return agg && typeof agg === "object"
    ? agg
    : { n: 0, usedRevenue: 0, usedVote: 0, usedReserves: 0, revShareSum: 0, cutTally: {} };
}
