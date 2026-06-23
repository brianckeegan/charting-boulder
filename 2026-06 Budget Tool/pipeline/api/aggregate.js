// GET /api/aggregate — the anonymous, aggregate-only view of all contributions,
// in the exact shape the widget's AggregateView renders. This is what the
// widget's readAgg() fetches on load when ENDPOINT is set. Never returns an
// individual response. See ../../ARCHITECTURE.md.

import { handlePreflight, missingConfig, fetchAggregate } from "./_supabase.js";

const EMPTY = { n: 0, usedRevenue: 0, usedVote: 0, usedReserves: 0, revShareSum: 0, cutTally: {} };

export default async function handler(req, res) {
  if (handlePreflight(req, res, "GET")) return;

  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  if (missingConfig().length) {
    // Degrade gracefully: an unconfigured backend shows an empty tally rather
    // than an error, so the widget still renders.
    res.status(200).json(EMPTY);
    return;
  }

  try {
    const agg = await fetchAggregate();
    // A short cache softens load spikes without making the tally feel stale.
    res.setHeader("Cache-Control", "public, max-age=15, s-maxage=30, stale-while-revalidate=120");
    res.status(200).json(agg);
  } catch {
    res.status(200).json(EMPTY);
  }
}
