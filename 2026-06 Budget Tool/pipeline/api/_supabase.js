// Thin helpers over Supabase's auto-generated REST API (PostgREST) plus the
// cross-cutting concerns of the write path: CORS, bot defense (Cloudflare
// Turnstile), and rate-limiting (Upstash Redis). No SDK, no dependencies — just
// the global fetch the Vercel Node runtime already provides, so cold starts
// stay fast. Every external defense is OPTIONAL and activates only when its env
// vars are set, so the function runs with or without them configured.

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

const TURNSTILE_SECRET = process.env.TURNSTILE_SECRET || "";
const KV_URL = process.env.UPSTASH_REDIS_REST_URL || "";
const KV_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || "";
const RL_MAX = Number(process.env.RATE_LIMIT_MAX || 5);          // submissions…
const RL_WINDOW = Number(process.env.RATE_LIMIT_WINDOW || 3600); // …per this many seconds

export function missingConfig() {
  const missing = [];
  if (!URL) missing.push("SUPABASE_URL");
  if (!SERVICE_KEY) missing.push("SUPABASE_SECRET_KEY");
  return missing;
}

export function turnstileEnabled() { return !!TURNSTILE_SECRET; }
export function rateLimitEnabled() { return !!(KV_URL && KV_TOKEN); }

// First hop in X-Forwarded-For — used transiently for Turnstile + rate-limit
// keys, never stored.
export function clientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  return (Array.isArray(fwd) ? fwd[0] : (fwd || "")).split(",")[0].trim() || "unknown";
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

// ---- Bot defense: Cloudflare Turnstile -------------------------------------
// Returns { ok, skipped?, error? }. Skipped (ok:true) when no secret is set.
export async function verifyTurnstile(token, ip) {
  if (!TURNSTILE_SECRET) return { ok: true, skipped: true };
  if (!token) return { ok: false, error: "missing-turnstile-token" };
  try {
    const form = new URLSearchParams();
    form.set("secret", TURNSTILE_SECRET);
    form.set("response", token);
    if (ip && ip !== "unknown") form.set("remoteip", ip);
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST", body: form,
    });
    const j = await r.json();
    return { ok: !!j.success, error: (j["error-codes"] || []).join(",") || undefined };
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
}

// ---- Rate limit: Upstash Redis (ephemeral; nothing persisted) --------------
// Fixed window per IP. Fails OPEN on a KV error so an infra hiccup never blocks
// a real reader. Returns { ok, skipped?, count? }.
export async function rateLimit(ip) {
  if (!KV_URL || !KV_TOKEN) return { ok: true, skipped: true };
  const bucket = Math.floor(Date.now() / 1000 / RL_WINDOW);
  const key = `bbw:rl:${ip}:${bucket}`;
  try {
    const r = await fetch(`${KV_URL}/pipeline`, {
      method: "POST",
      headers: { Authorization: `Bearer ${KV_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify([["INCR", key], ["EXPIRE", key, String(RL_WINDOW)]]),
    });
    const j = await r.json();
    const count = Array.isArray(j) ? Number(j[0]?.result ?? 0) : Number(j?.result ?? 0);
    return { ok: count <= RL_MAX, count };
  } catch {
    return { ok: true, skipped: true }; // fail open
  }
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
