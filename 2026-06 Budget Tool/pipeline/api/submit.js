// POST /api/submit — receive one reader budget, store it in Supabase, and
// return the refreshed anonymous aggregate. This is the endpoint the widget's
// writeAgg() posts to when ENDPOINT is set (it then renders the returned
// aggregate). Mirrors the contract documented in ../../ARCHITECTURE.md.

import { rowFromPayload, hasOneDemo } from "./_schema.js";
import {
  handlePreflight,
  missingConfig,
  insertContribution,
  fetchAggregate,
  dedupeHash,
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

  // Vercel parses JSON bodies automatically; tolerate a raw string too.
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

  const row = rowFromPayload(payload);
  row.dedupe_hash = dedupeHash(req);

  try {
    await insertContribution(row);
  } catch (err) {
    res.status(502).json({ error: "Could not store the contribution", detail: String(err.message || err) });
    return;
  }

  // Hand back the fresh aggregate so the widget can update its tally in place.
  try {
    const agg = await fetchAggregate();
    res.status(200).json(agg);
  } catch {
    // The write succeeded, which is what matters; let the widget keep its
    // current tally rather than fail the whole submission on a read hiccup.
    res.status(200).json(null);
  }
}
