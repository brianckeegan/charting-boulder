// POST /api/submit — receive one reader budget, store it in Supabase with the
// secret key (server-side, bypasses RLS), and return the refreshed anonymous
// aggregate. This is the endpoint the widget's writeAgg() posts to when ENDPOINT
// is set. CORS is locked to ALLOWED_ORIGIN. Mirrors ../../2026-06-budget-tool/ARCHITECTURE.md.

import { rowFromPayload, hasOneDemo } from "./_schema.js";
import { handlePreflight, missingConfig, insertContribution, fetchAggregate } from "./_supabase.js";

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
