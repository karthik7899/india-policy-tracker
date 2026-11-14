// A single read-only view of the existing briefing for the research workspace.
//
// The scraper and dashboard payload remain the source of truth. This adapter
// only normalises the watchlist into a company index and resolves the existing
// sidecars once, so new research views do not each invent their own data path.
// Missing keys remain null; present-but-empty arrays/objects remain empty.

import { resolve } from "./data.js";

// Sidecars shared by the new research views and the existing analytics views.
// Keep this list explicit: it documents the payload contract and avoids
// eagerly fetching per-ticker manifests such as stock_topics.
export const RESEARCH_SIDECARS = [
  "peer_competitors",
  "candidate_screen",
  "industry_share",
  "market_share",
  "corporate_agreements",
  "product_launches",
  "institutional_activity",
  "corporate_filings",
  "global_market_news",
  "state_policy",
  "publisher_news",
  "policy_impacts",
  "market_events",
  "policy_partnerships",
  "sector_blocks",
  "company_digest",
  "event_calendar",
  "results",
  "portfolio",
  "buffett_valuation",
  "thesis_check",
];

const labelFor = (sectors, key) =>
  sectors?.[key]?.label || sectors?.[key]?.name || String(key).replace(/_/g, " ");

/** Build the shared research context from already-loaded payload/sidecar data. */
export function buildResearchContext(payload, resolved = {}) {
  const watchlist = payload?.watchlist || {};
  const sectors = payload?.sectors || {};
  const briefing = payload?.briefing || {};
  const companies = Object.entries(watchlist).flatMap(([sector, rows]) =>
    (Array.isArray(rows) ? rows : [])
      .filter((row) => row && row.ticker)
      .map((row) => ({ ...row, ticker: String(row.ticker).toUpperCase(), sector, sectorLabel: labelFor(sectors, sector) })),
  );
  const companiesByTicker = new Map(companies.map((company) => [company.ticker, company]));
  const companiesBySector = Object.fromEntries(
    Object.keys(watchlist).map((sector) => [sector, companies.filter((company) => company.sector === sector)]),
  );
  const newsBySector = Object.fromEntries(
    Object.keys(watchlist).map((sector) => [sector, Array.isArray(briefing[sector]) ? briefing[sector] : null]),
  );

  return {
    asOf: payload?.last_updated || null,
    watchlist,
    sectors,
    companies,
    companiesByTicker,
    companiesBySector,
    newsBySector,
    // Keep the full original briefing available: this is an adapter, not a
    // second schema that silently drops existing analysis fields.
    briefing,
    insights: {
      emergingPlayers: briefing.emerging_players ?? null,
      emergingCompetitors: briefing.emerging_competitors ?? null,
      readThroughs: briefing.read_throughs ?? null,
      policyBalance: briefing.policy_balance ?? null,
      supplyStress: briefing.supply_stress ?? null,
      earlyWarnings: briefing.early_warnings ?? null,
      changes: briefing.changes ?? null,
      thesisHealth: briefing.thesis_health ?? null,
      institutionalBaseline: briefing.institutional_baseline ?? null,
      variantPerception: briefing.variant_perception ?? null,
    },
    sidecars: { ...resolved },
    stockTopicsManifest: briefing["stock_topics"] ?? null,
  };
}

/** Load all shared sidecars through the existing cache/resolver. */
export async function loadResearchContext(payload) {
  const briefing = payload?.briefing || {};
  const pairs = await Promise.all(
    RESEARCH_SIDECARS.map(async (key) => [key, await resolve(briefing, key)]),
  );
  return buildResearchContext(payload, Object.fromEntries(pairs));
}
