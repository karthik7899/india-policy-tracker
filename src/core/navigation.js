// Navigation taxonomy for the research workstation.
// These are presentation groups only: every existing hash route is unchanged.
export const NAV_GROUPS = [
  { id: "daily", label: "Daily Intelligence", views: ["intelligence", "overview", "flow", "calendar"] },
  { id: "companies", label: "Company Research", views: ["companies", "network"] },
  { id: "portfolio", label: "Portfolio", views: ["portfolio", "holdings"] },
  { id: "advanced", label: "Advanced Research", views: ["review", "valuation", "risk", "ask", "system"] },
];

export function groupForView(view) {
  return NAV_GROUPS.find((group) => group.views.includes(view)) || NAV_GROUPS[0];
}

export function navigationViews() {
  return NAV_GROUPS.flatMap((group) => group.views.map((view) => ({ view, group: group.id })));
}
