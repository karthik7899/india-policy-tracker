// How settled a catalyst is, as a pill on its row.
//
// A policy is a hard measure (approved or in force), a proposal, or a soft
// partnership (a government's MoU or pact), as analysis/policy_impact.py
// labels it. An order win is a confirmed win (an order won or received, a
// letter of award) or an L-1 position (lowest bidder: the award is not yet
// made), as analysis/event_engine.py reads the headline. High conviction is
// the two that have happened: a hard policy and a confirmed win.
//
// Pure, so the rules are tested without a DOM.

export const PILLS = {
  hard: { label: "Hard policy", title: "Approved or in force." },
  proposed: { label: "Proposed", title: "A draft or proposal: not yet approved." },
  soft: { label: "Soft partnership", title: "A government's MoU or pact with a company: no measure yet." },
  win: { label: "Confirmed win", title: "Stated as done: an order won or received, or a letter of award." },
  l1: { label: "L-1 (announced)", title: "Lowest bidder. The award is not yet made, and L-1 bids are sometimes not awarded." },
  announced: { label: "Announced", title: "Announced, not yet done." },
  reported: { label: "Reported", title: "Reported by others, not announced by the company." },
};

// analysis/policy_impact.STRENGTH, for rows saved before strength was.
const STRENGTH_OF_STATUS = { in_force: "hard", approved: "hard", proposed: "proposed" };

// The event engine's L-1 patterns: "emerges L1", "L-1 bidder", "lowest bidder".
const L1 = /\b(?:l-?1|lowest\s+bidder)\b/i;

const isPolicy = (item) => Array.isArray(item.effects) || "measure" in item;
const isOrderWin = (item) => item.event_type === "order_win" || item.kind === "order";

function pill(kind) {
  return { kind, ...PILLS[kind] };
}

/**
 * The pill for a catalyst row (a Flow item, or a company's activity or
 * policy row), or null when it is neither a policy nor an order win, or its
 * stage is not known.
 */
export function catalystPill(item) {
  if (!item || typeof item !== "object") return null;
  const strength = item.strength || (isPolicy(item) ? STRENGTH_OF_STATUS[item.status] : null);
  if (PILLS[strength] && ["hard", "proposed", "soft"].includes(strength)) return pill(strength);
  if (!isOrderWin(item)) return null;
  if (L1.test([item.phrase, item.headline, item.text].filter(Boolean).join(" "))) return pill("l1");
  if (item.certainty === "completed") return pill("win");
  if (item.certainty === "announced") return pill("announced");
  if (item.certainty === "reported") return pill("reported");
  return null;
}

// The pills that mean it has happened.
export const HIGH = new Set(["hard", "win"]);

/** A hard policy or a confirmed win. */
export function isHighConviction(item) {
  const p = catalystPill(item);
  return p !== null && HIGH.has(p.kind);
}
