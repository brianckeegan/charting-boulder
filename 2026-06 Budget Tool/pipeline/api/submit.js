// POST /api/submit — receive one reader budget, defend the write (origin,
// Turnstile, rate-limit), store it in Supabase with the secret key, and return
// the refreshed anonymous aggregate. This is the endpoint the widget's
// writeAgg() posts to when ENDPOINT is set. Mirrors ../../ARCHITECTURE.md.
//
// Turnstile and rate-limiting activate only when their env vars are set, so the
// function works whether or not those services are configured yet.

import { rowFromPayload, hasOneDemo } from "./_schema.js";
import {
  handlePreflight,
  missingConfig,
  insertContribution,
  fetchAggregate,
  clientIp,
  verifyTurnstile,
  rateLimit,
} from "./_supabase.js";

export default async function handler(req, res) {
  if (handlePreflight(req, res, "POST")) return;

  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const missing = missingConfig();
  if (missing.length) {
    res.status(500).json({ error: `Server not configured: missing ${missing.join(", ")}` });
    return;
  }

  let payload = req.body;
  if (typeof payload === "string") {
    try { payload = JSON.parse(payload); } catch { payload = null; }
  }
  if (!payload || typeof payload !== "object") {
    res.status(400).json({ error: "Expected a JSON body" });
    return;
  }

  // The widget enforces "answer at least one survey item"; enforce it here too.
  if (!hasOneDemo(payload)) {
    res.status(422).json({ error: "At least one survey answer is required" });
    return;
  }

  const ip = clientIp(req);

  // Bot defense (no-op unless TURNSTILE_SECRET is set).
  const ts = await verifyTurnstile(payload.turnstileToken || payload["cf-turnstile-response"], ip);
  if (!ts.ok) {
    res.status(403).json({ error: "Verification failed", detail: ts.error });
    return;
  }

  // Rate limit (no-op unless Upstash is configured; fails open on KV error).
  const rl = await rateLimit(ip);
  if (!rl.ok) {
    res.status(429).json({ error: "Too many submissions, please try again later." });
    return;
  }

  // Don't persist the one-time Turnstile token (it would otherwise land in raw).
  delete payload.turnstileToken;
  delete payload["cf-turnstile-response"];

  try {
    await insertContribution(rowFromPayload(payload));
  } catch (err) {
    res.status(502).json({ error: "Could not store the contribution", detail: String(err.message || err) });
    return;
  }

  try {
    res.status(200).json(await fetchAggregate());
  } catch {
    // The write succeeded; don't fail the submission on a read hiccup.
    res.status(200).json(null);
  }
}
