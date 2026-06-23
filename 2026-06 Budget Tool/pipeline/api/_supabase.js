// Thin helpers over Supabase's auto-generated REST API (PostgREST) and a couple
// of cross-cutting concerns (CORS, request fingerprinting). No SDK, no
// dependencies — just the global fetch and crypto that the Vercel Node runtime
// already provides, so cold starts stay fast.

import { createHash } from "node:crypto";

const URL = process.env.SUPABASE_URL || "https://dlnalnozxwrxiekhilqo.supabase.co";
// The server-side SECRET key (sb_secret_… or the legacy service_role JWT). It
// bypasses Row Level Security, so it lives ONLY in Vercel env vars — never in
// the browser or in committed code.
const SERVICE_KEY =
  process.env.SUPABASE_SECRET_KEY ||
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.SUPABASE_SERVICE_KEY ||
  "";
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || "*";
const DEDUPE_SALT = process.env.DEDUPE_SALT || "";

export function missingConfig() {
  const missing = [];
  if (!URL) missing.push("SUPABASE_URL");
  if (!SERVICE_KEY) missing.push("SUPABASE_SECRET_KEY");
  return missing;
}

// Permissive CORS so the widget can call from wherever it's embedded (the
// Newspack article, a preview host, etc.). Lock this down by setting
// ALLOWED_ORIGIN to your site's origin once the embed URL is known.
export function applyCors(res, methods) {
  res.setHeader("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  res.setHeader("Access-Control-Allow-Methods", `${methods}, OPTIONS`);
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Max-Age", "86400");
  if (ALLOWED_ORIGIN !== "*") res.setHeader("Vary", "Origin");
}

export function handlePreflight(req, res, methods) {
  applyCors(res, methods);
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return true;
  }
  return false;
}

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

// Call the SECURITY DEFINER aggregate function and return its JSON. Falls back
// to an empty aggregate so a read failure never blanks the widget.
export async function fetchAggregate() {
  const r = await fetch(`${URL}/rest/v1/rpc/budget_aggregate`, {
    method: "POST",
    headers: headers(),
    body: "{}",
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`aggregate failed (${r.status}): ${detail.slice(0, 500)}`);
  }
  const agg = await r.json();
  // PostgREST returns the function result directly for a scalar-returning fn.
  return agg && typeof agg === "object"
    ? agg
    : { n: 0, usedRevenue: 0, usedVote: 0, usedReserves: 0, revShareSum: 0, cutTally: {} };
}

// Privacy-preserving fingerprint: a salted one-way hash of (IP + UTC day). We
// store ONLY this hash, never the IP, so submissions can be screened for likely
// duplicates without retaining any identifier. Returns null if no salt is set.
export function dedupeHash(req) {
  if (!DEDUPE_SALT) return null;
  const fwd = req.headers["x-forwarded-for"];
  const ip = (Array.isArray(fwd) ? fwd[0] : (fwd || "")).split(",")[0].trim() || "unknown";
  const day = new Date().toISOString().slice(0, 10); // UTC YYYY-MM-DD
  return createHash("sha256").update(`${DEDUPE_SALT}|${ip}|${day}`).digest("hex");
}
