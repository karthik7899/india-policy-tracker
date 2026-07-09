// Static Fallback Seed Data (Mock Data identical in structure to brief.py output)
const MOCK_DATA = {
    "last_updated": "2026-05-29 08:00:00 (Mock Archive)",
    "sectors": {
        "clean_energy": {"label": "Clean Energy", "icon": "⚡", "desc": "Solar, Wind, Green Hydrogen, and Grid Transmission initiatives."},
        "data_center_support": {"label": "Data Center Support", "icon": "🖥️", "desc": "Power cooling, high-speed fiber cables, and server space infrastructure."},
        "cybersecurity": {"label": "Cybersecurity", "icon": "🛡️", "desc": "Data protection, software defense systems, and network security policies."},
        "surveillance_security": {"label": "Surveillance & CCTV", "icon": "📷", "desc": "Smart City CCTVs, border security systems, and commercial surveillance cameras."},
        "manufacturing_electronics": {"label": "Manufacturing & Electronics", "icon": "🏭", "desc": "PLI programs, semiconductor fabrications, and local contract assembly."},
        "fmcg": {"label": "FMCG & Consumption", "icon": "🛒", "desc": "Rural disposable income, food processing, and consumer product growth."},
        "sports_athleisure": {"label": "Sports & Athleisure", "icon": "👟", "desc": "Active footwear, fitness apparel, and sports licensing brands."},
        "big_cap_industries": {"label": "Big Cap Industries", "icon": "🏛️", "desc": "Nation-building conglomerates, heavy engineering, and infrastructure giants."}
    },
    "watchlist": {
        "clean_energy": [
            {"ticker": "TATAPOWER", "name": "Tata Power", "price": "432.50", "target": "520.00", "growth_pct": "20.2%", "estimate_method": "Analyst Consensus", "catalyst": "Massive scaling in solar generation, microgrids, and leading India's EV charging network grid.", "screener": {"pe_ratio": 28.4, "industry_pe": 18.4, "pe_vs_peers": "54% above peers", "roce": 11.2}},
            {"ticker": "SUZLON", "name": "Suzlon Energy", "price": "50.15", "target": "68.00", "growth_pct": "35.6%", "estimate_method": "Fundamental Estimate", "fundamental_value": 71.5, "catalyst": "Turnaround story, completely debt-free, dominating wind turbine supply with a record order book.", "screener": {"pe_ratio": 12.1, "industry_pe": 18.4, "pe_vs_peers": "34% below peers", "roce": 19.8}},
            {"ticker": "ADANIGREEN", "name": "Adani Green Energy", "price": "1845.00", "target": "2200.00", "growth_pct": "19.2%", "catalyst": "Developing the world's largest renewable energy park in Khavda, Gujarat (30 GW capacity target)."}
        ],
        "data_center_support": [
            {"ticker": "SCHNEIDER", "name": "Schneider Electric Infra", "price": "855.00", "target": "1120.00", "growth_pct": "31.0%", "catalyst": "Critical supplier of electrical distribution, smart grids, and high-efficiency cooling for data centers."},
            {"ticker": "STERLITE", "name": "Sterlite Technologies (STL)", "price": "142.10", "target": "195.00", "growth_pct": "37.2%", "catalyst": "Expanding optical fiber and cable capacities to meet hyper-scale data center interconnect demands."},
            {"ticker": "ANANTRAJ", "name": "Anant Raj Ltd", "price": "352.40", "target": "480.00", "growth_pct": "36.2%", "catalyst": "Real-estate developer transitioning commercial properties into major data center hubs in NCR."}
        ],
        "cybersecurity": [
            {"ticker": "TCS", "name": "Tata Consultancy Services", "price": "4015.00", "target": "4800.00", "growth_pct": "19.6%", "catalyst": "Expanding sovereign cloud and secure cyber command centers globally for enterprise clients."},
            {"ticker": "QUICKHEAL", "name": "Quick Heal Technologies", "price": "552.00", "target": "720.00", "growth_pct": "30.4%", "catalyst": "Surging enterprise adoption of their 'Seqrite' cybersecurity platform and government IT contracts."}
        ],
        "surveillance_security": [
            {"ticker": "CPPLUS", "name": "Aditya Infotech (CP PLUS)", "price": "712.50", "target": "920.00", "growth_pct": "29.1%", "catalyst": "CCTV market leader (35%+ share) newly listed, scaling domestic camera manufacturing under PLI."},
            {"ticker": "DIXON", "name": "Dixon Technologies", "price": "11240.00", "target": "14200.00", "growth_pct": "26.3%", "catalyst": "Primary EMS contract manufacturer producing CCTVs and DVRs for CP Plus and others under PLI."},
            {"ticker": "ALLIED", "name": "Allied Digital Services", "price": "182.30", "target": "240.00", "growth_pct": "31.7%", "catalyst": "System integrator winning smart/safe city surveillance projects, managing master command centers."},
            {"ticker": "IDEAFORGE", "name": "IdeaForge Technology", "price": "702.15", "target": "950.00", "growth_pct": "35.3%", "catalyst": "Pioneer in tactical and mapping drone systems, primary supplier for Indian Army and police borders."}
        ],
        "manufacturing_electronics": [
            {"ticker": "DIXON", "name": "Dixon Technologies", "price": "11240.00", "target": "14200.00", "growth_pct": "26.3%", "catalyst": "Leader in electronic assembly (mobile, laptop, LED TV), heavily subsidized under manufacturing PLI."},
            {"ticker": "KAYNES", "name": "Kaynes Technology", "price": "3425.00", "target": "4400.00", "growth_pct": "28.5%", "catalyst": "High-end electronics and PCBA manufacturing, setting up a state-of-the-art semiconductor OSAT plant."},
            {"ticker": "CGPOWER", "name": "CG Power & Industrial", "price": "658.00", "target": "820.00", "growth_pct": "24.6%", "catalyst": "Partnering on a $1B semiconductor fab, strong order pipeline in railways and power grid equipment."}
        ],
        "fmcg": [
            {"ticker": "VBL", "name": "Varun Beverages (PepsiCo)", "price": "1510.00", "target": "1900.00", "growth_pct": "25.8%", "catalyst": "PepsiCo's dominant bottler, expanding into newer territories and scaling dairy/juice products."},
            {"ticker": "TATACONSUM", "name": "Tata Consumer Products", "price": "1122.00", "target": "1350.00", "growth_pct": "20.3%", "catalyst": "Premiumization strategy in foods & beverages, high-growth acquisitions (Capital Foods, Organic India)."},
            {"ticker": "ITC", "name": "ITC Ltd", "price": "431.10", "target": "510.00", "growth_pct": "18.3%", "catalyst": "Resilient cigarette margins funding rapid expansion of high-margin FMCG brands, direct rural boost play."}
        ],
        "sports_athleisure": [
            {"ticker": "METROBRAND", "name": "Metro Brands Ltd", "price": "1152.00", "target": "1480.00", "growth_pct": "28.5%", "catalyst": "Exclusive retail rights for Fila and Foot Locker in India, expanding athleisure footprint rapidly."},
            {"ticker": "CAMPUS", "name": "Campus Activewear", "price": "262.50", "target": "340.00", "growth_pct": "29.5%", "catalyst": "Dominant direct-to-consumer sports footwear brand in tier-2/3 cities, major beneficiary of fitness trends."},
            {"ticker": "PAGEIND", "name": "Page Industries", "price": "36450.00", "target": "44000.00", "growth_pct": "20.7%", "catalyst": "Jockey master franchise holder, expanding sports shorts, tees, and athleisure wear into rural hubs."}
        ],
        "big_cap_industries": [
            {"ticker": "LT", "name": "Larsen & Toubro (L&T)", "price": "3515.00", "target": "4200.00", "growth_pct": "19.5%", "catalyst": "Heavy infrastructure leader, direct beneficiary of the government's ₹11.11 Lakh Cr CAPEX budget."},
            {"ticker": "RELIANCE", "name": "Reliance Industries", "price": "2912.00", "target": "3500.00", "growth_pct": "20.2%", "catalyst": "Consolidating 5G market share, scaling retail stores, and commissioning green energy gigafactories."}
        ]
    },
    "briefing": {
        "clean_energy": [
            {"title": "Cabinet Approves ₹19,744 Crore National Green Hydrogen Mission", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "28 May 2026", "impact": "Positive"},
            {"title": "Adani Green Secures Operationalisation of 2 GW Solar Capacity at Khavda", "source": "Economic Times", "link": "https://economictimes.indiatimes.com", "date": "29 May 2026", "impact": "Positive"},
            {"title": "Suzlon bags new 400 MW wind energy order from leading PSU", "source": "Livemint", "link": "https://livemint.com", "date": "27 May 2026", "impact": "Positive"}
        ],
        "data_center_support": [
            {"title": "MeitY Proposes Unified Data Center Policy to Streamline Single-Window Clearances", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "29 May 2026", "impact": "Positive"},
            {"title": "Anant Raj commits ₹1,500 crore to construct 300MW Data Center parks in Haryana", "source": "Business Standard", "link": "https://business-standard.com", "date": "28 May 2026", "impact": "Positive"}
        ],
        "cybersecurity": [
            {"title": "CERT-In Issues New Directives for Financial Tech Intermediaries on Cloud Security", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "26 May 2026", "impact": "Neutral"},
            {"title": "Quick Heal wins ₹50 crore cybersecurity security mandate from Defence PSU", "source": "Economic Times", "link": "https://economictimes.indiatimes.com", "date": "28 May 2026", "impact": "Positive"}
        ],
        "surveillance_security": [
            {"title": "Ministry of Home Affairs Sanctions ₹800 Cr for CCTV Expansion under Safe City Initiative", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "29 May 2026", "impact": "Positive"},
            {"title": "Aditya Infotech (CP Plus) lists at 30% premium on BSE; outlines PLI expansion roadmap", "source": "Moneycontrol", "link": "https://moneycontrol.com", "date": "25 May 2026", "impact": "Positive"},
            {"title": "Allied Digital selected as Master Integrator for Smart City surveillance grids", "source": "Livemint", "link": "https://livemint.com", "date": "27 May 2026", "impact": "Positive"}
        ],
        "manufacturing_electronics": [
            {"title": "Government Considers PLI Scheme Extension for IT Hardware; Allocates Extra Funds", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "28 May 2026", "impact": "Positive"},
            {"title": "Kaynes Technology OSAT Semiconductor assembly plant in Sanand receives cabinet clearance", "source": "Economic Times", "link": "https://economictimes.indiatimes.com", "date": "29 May 2026", "impact": "Positive"}
        ],
        "fmcg": [
            {"title": "Agriculture Ministry Allocates ₹1.2 Lakh Cr for Rural Infrastructure & Subventions", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "27 May 2026", "impact": "Positive"},
            {"title": "Rural consumption volumes turn positive after three quarters, FMCG margins expand", "source": "Livemint", "link": "https://livemint.com", "date": "29 May 2026", "impact": "Positive"}
        ],
        "sports_athleisure": [
            {"title": "Cabinet clears Draft Sports Footwear PLI scheme to replace imports with local capacity", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "28 May 2026", "impact": "Positive"},
            {"title": "Metro Brands opens 35 new Athleisure flagship stores in tier 2 cities", "source": "Financial Express", "link": "https://financialexpress.com", "date": "26 May 2026", "impact": "Positive"}
        ],
        "big_cap_industries": [
            {"title": "Union Budget targets record Infrastructure CAPEX allocation of ₹11.11 Lakh Crore", "source": "PIB Delhi", "link": "https://pib.gov.in", "date": "24 May 2026", "impact": "Positive"},
            {"title": "Larsen & Toubro emerges as lowest bidder for massive High-Speed Rail Project package", "source": "BSE Filings", "link": "https://bseindia.com", "date": "29 May 2026", "impact": "Positive"}
        ],
        "early_warnings": [
            {"ticker": "SUZLON", "name": "Suzlon Energy", "sector": "Clean Energy", "severity": "High", "direction": "risk", "category": "FII Selling", "signal": "Foreign institutions reduced holdings (-1.40%)."},
            {"ticker": "STERLITE", "name": "Sterlite Technologies (STL)", "sector": "Data Center Support", "severity": "High", "direction": "risk", "category": "High Leverage", "signal": "Debt-to-equity of 1.35 exceeds 1.0."},
            {"ticker": "QUICKHEAL", "name": "Quick Heal Technologies", "sector": "Cybersecurity", "severity": "Medium", "direction": "risk", "category": "Revenue Contraction", "signal": "Quarter-on-quarter sales fell 6.2%."},
            {"ticker": "TATAPOWER", "name": "Tata Power", "sector": "Clean Energy", "severity": "High", "direction": "opportunity", "category": "Institutional Accumulation", "signal": "Both FIIs (+0.80%) and DIIs (+1.10%) are accumulating."},
            {"ticker": "DIXON", "name": "Dixon Technologies", "sector": "Manufacturing & Electronics", "severity": "Medium", "direction": "opportunity", "category": "Policy Catalyst", "signal": "Active policy tailwind — PLI / scheme: IT Hardware approval."},
            {"ticker": "ITC", "name": "ITC Ltd", "sector": "FMCG & Consumption", "severity": "Medium", "direction": "risk", "category": "Competitive Threat", "signal": "Patanjali Foods is growing faster (QoQ +22.0% vs +8.0%) and could pressure market share."}
        ],
        "sector_valuation": [
            {"sector": "clean_energy", "label": "Clean Energy", "icon": "⚡", "median_pe": 18.4, "stock_count": 3, "cheapest_ticker": "SUZLON", "cheapest_pe": 12.1, "most_expensive_ticker": "ADANIGREEN", "most_expensive_pe": 41.0},
            {"sector": "fmcg", "label": "FMCG & Consumption", "icon": "🛒", "median_pe": 32.5, "stock_count": 3, "cheapest_ticker": "ITC", "cheapest_pe": 24.8, "most_expensive_ticker": "VBL", "most_expensive_pe": 58.2},
            {"sector": "manufacturing_electronics", "label": "Manufacturing & Electronics", "icon": "🏭", "median_pe": 45.6, "stock_count": 3, "cheapest_ticker": "CGPOWER", "cheapest_pe": 38.0, "most_expensive_ticker": "DIXON", "most_expensive_pe": 72.4}
        ]
    }
};

// Global App State
let appData = null;
let activeSectorFilter = "all";
let growthChartInstance = null;

const TAB_COPY = {
    dashboard: ["Policy & Sector Overview", "Real-time mapping of government policies to market indicators."],
    sectors: ["Government Policy Logs", "Deep dive sector analysis, announcements history, and watchlists."],
    agreements: ["Corporate News & Agreements", "Scanned news alerts regarding joint ventures, strategic partnerships, and MoUs."],
    launches: ["Product Launches", "Real-time alerts on product launches, new manufacturing capacities, and rollouts."],
    institutional: ["Institutional Activity", "Scheme filings, block deals, and institutional buying signals."],
    graham: ["Margin of Safety (Deep Value)", "Defensive investor criteria checks and growth intrinsic value calculations."],
    buffett: ["Owner Earnings & Moats", "Owner earnings estimates, quality signals, and retained value creation metrics."],
    earlywarning: ["Early Warning System", "Prioritized risk & opportunity signals synthesized across the watchlist."],
    valuation: ["Sector Valuation (Peer P/E)", "Median price-to-earnings per sector peer group — which themes are richly vs cheaply priced."],
    caution: ["Risk Alerts & Valuation Warnings", "Stocks that are not meeting the configured value and growth filters."],
    research: ["Thesis & Signals", "Falsifiable thesis health, estimate-revision momentum, variant perception, sector curve stage, and the rotation engine's own track record."],
    stocks: ["Integrated Stocks Screener", "Curated companies, policy catalysts, and financial screening signals."]
};

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

const escapeHTML = escapeHtml;

function safeExternalUrl(value) {
    if (!value || typeof value !== "string" || !/^https?:\/\//i.test(value.trim())) {
        return "#";
    }
    try {
        const url = new URL(value);
        return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch {
        return "#";
    }
}

function parsePercent(value) {
    const parsed = parseFloat(String(value ?? "").replace("%", ""));
    return Number.isFinite(parsed) ? parsed : null;
}

function getPolicySectorKeys(data) {
    return Object.keys(data?.sectors || {}).filter(
        key => Array.isArray(data?.briefing?.[key])
    );
}

function countEmergingCompetitors(data) {
    const structured = data?.briefing?.emerging_players || {};
    const structuredCount = Object.values(structured).reduce(
        (total, players) => total + (Array.isArray(players) ? players.length : 0),
        0
    );
    const pliCount = Array.isArray(data?.briefing?.emerging_competitors)
        ? data.briefing.emerging_competitors.length
        : 0;
    return structuredCount + pliCount;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function setTableEmpty(tbody, colspan, title, detail = "") {
    tbody.innerHTML = `
        <tr>
            <td colspan="${colspan}">
                <div class="empty-state">
                    <strong>${escapeHtml(title)}</strong>
                    ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
                </div>
            </td>
        </tr>
    `;

}

// Helper: Format YoY growth with contextual icon/color
function formatGrowthBadge(growthStr, style = 'inline') {
    if (!growthStr) return style === 'table' ? `<span style="color: var(--text-muted);">—</span>` : '';
    const val = parseFloat(String(growthStr).replace('%', ''));
    if (isNaN(val)) return style === 'table' ? `<span style="color: var(--text-muted);">—</span>` : '';
    
    const absValStr = Math.abs(val).toFixed(1) + '%';
    if (val > 0) {
        if (style === 'table') return `<span style="font-weight: 700; color: #34d399;">+${absValStr} YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">+${absValStr} YoY</span>`;
    } else if (val < 0) {
        if (style === 'table') return `<span style="font-weight: 700; color: #f87171;">-${absValStr} YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">-${absValStr} YoY</span>`;
    } else {
        if (style === 'table') return `<span style="font-weight: 700; color: #cbd5e1;">0.0% YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(203, 213, 225, 0.12); color: #cbd5e1; border: 1px solid rgba(203, 213, 225, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">0.0% YoY</span>`;
    }
}


// Helper: Format potential growth with proper sign and color
function formatPotential(pctStr) {
    if (!pctStr) return '—';
    const val = parseFloat(String(pctStr).replace('%', ''));
    if (isNaN(val)) return escapeHtml(pctStr);
    const isPositive = typeof pctStr === 'string' ? pctStr.startsWith('+') : val > 0;
    const absValStr = Math.abs(val).toFixed(1) + '%';
    if (isPositive || val > 0) return `<span style="font-weight:700; color:#34d399;">+${absValStr}</span>`;
    if (val < 0) return `<span style="font-weight:700; color:#f87171;">-${absValStr}</span>`;
    return `<span style="font-weight:700; color:#cbd5e1;">0.0%</span>`;
}

// Helper: Format analyst info badge
function formatAnalystBadge(stock) {
    const rating = stock.rating;
    const count = stock.analyst_count;
    if (!rating || rating === 'N/A') return `<span style="color: var(--text-muted);">—</span>`;
    const countStr = count ? ` (${escapeHtml(count)})` : '';
    return `<span class="badge badge-rating">${escapeHtml(rating)}${countStr}</span>`;
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupTabToggles();
    setupQuickActions();
    loadDashboardData();
    setupStockSearch();
    setupWarningFilters();
    setupTickerNavigation();
    setupGenericTableSorting();
});

// Any ticker cell anywhere in the app deep-links into the Stocks Screener,
// pre-filtered to that ticker. Delegated so every renderer gets it for free.
function setupTickerNavigation() {
    document.addEventListener("click", event => {
        const cell = event.target.closest(".t-ticker");
        if (!cell) return;
        const ticker = (cell.textContent || "").trim().split(/\s/)[0];
        if (!ticker) return;
        const searchInput = document.getElementById("stock-search");
        if (searchInput) searchInput.value = ticker;
        activateTab("stocks");
        renderStocksTable(ticker);
    });
}

// Click-to-sort for every data table that doesn't have data-driven sorting
// of its own (the Stocks Screener keeps its dedicated th.sortable path).
// Sorts the rendered rows in place, numeric-aware.
function setupGenericTableSorting() {
    document.addEventListener("click", event => {
        const th = event.target.closest(".premium-table th");
        if (!th || th.classList.contains("sortable")) return;
        const table = th.closest("table");
        const tbody = table && table.querySelector("tbody");
        if (!tbody || tbody.querySelector(".empty-state")) return;

        const index = Array.from(th.parentNode.children).indexOf(th);
        const ascending = th.classList.contains("sorted-desc");
        table.querySelectorAll("th").forEach(h => h.classList.remove("sorted-asc", "sorted-desc"));
        th.classList.add(ascending ? "sorted-asc" : "sorted-desc");

        const numeric = text => {
            const cleaned = text.replace(/[₹,%+,]/g, "").replace(/—/g, "");
            const value = parseFloat(cleaned);
            return Number.isNaN(value) ? null : value;
        };
        const rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort((a, b) => {
            const ta = (a.children[index]?.textContent || "").trim();
            const tb = (b.children[index]?.textContent || "").trim();
            const na = numeric(ta);
            const nb = numeric(tb);
            let cmp;
            if (na !== null && nb !== null) cmp = na - nb;
            else cmp = ta.localeCompare(tb);
            return ascending ? cmp : -cmp;
        });
        rows.forEach(r => tbody.appendChild(r));
    });
}

// Tab Toggling Logic
function setupTabToggles() {
    const navButtons = document.querySelectorAll(".nav-btn[data-tab]");
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            activateTab(btn.getAttribute("data-tab"));
        });
    });
}

function activateTab(targetTab) {
    const targetPane = document.getElementById(`tab-${targetTab}`);
    if (!targetPane || !TAB_COPY[targetTab]) return;

    document.querySelectorAll(".nav-btn[data-tab]").forEach(button => {
        const isActive = button.getAttribute("data-tab") === targetTab;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", String(isActive));
    });
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.toggle("active", pane === targetPane);
    });

    const [title, subtitle] = TAB_COPY[targetTab];
    setText("page-title", title);
    setText("page-subtitle", subtitle);

    if (appData) {
        const renderers = {
            dashboard: () => renderCharts(appData),
            sectors: initSectorsTab,
            agreements: renderAgreementsTable,
            launches: renderLaunchesTable,
            filings: renderFilingsTable,
            institutional: renderInstitutionalFlows,
            overview: () => { /* Rendered by initDashboard */ },
            graham: renderGrahamTable,
            buffett: renderBuffettTable,
            scoring: renderScoringTable,
            earlywarning: renderEarlyWarnings,
            valuation: renderSectorValuation,
            caution: renderCautionTable,
            research: renderResearchEngine,
            stocks: () => renderStocksTable(document.getElementById("stock-search")?.value || "")
        };
        renderers[targetTab]?.();
    }

    const main = document.getElementById("main-content");
    if (main) main.scrollTo({ top: 0, behavior: "smooth" });
    document.querySelector(`.nav-btn[data-tab="${targetTab}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "nearest"
    });
}

function setupQuickActions() {
    document.querySelectorAll("[data-tab-target]").forEach(button => {
        button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
    });
    document.querySelectorAll("[data-scroll-target]").forEach(button => {
        button.addEventListener("click", () => {
            document.getElementById(button.dataset.scrollTarget)?.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        });
    });
}

// Fetch dashboard data
function loadDashboardData() {
    fetch("dashboard_data.json?t=" + Date.now())
        .then(response => {
            if (!response.ok) throw new Error("JSON file missing");
            return response.json();
        })
        .then(data => {
            appData = data;
            initDashboard(data, false);
        })
        .catch(err => {
            console.warn("Failed to load live data, fallback to static mock seed database:", err);
            appData = MOCK_DATA;
            initDashboard(MOCK_DATA, true);
        });
}

// Dashboard Page Setup
function initDashboard(data, isFallback = false) {
    setText("update-time", `Last Refreshed: ${data.last_updated || "Unknown"}`);
    setText("data-mode-text", isFallback ? "Demo dataset" : "Live dataset");
    document.getElementById("data-mode-badge")?.classList.toggle("is-fallback", isFallback);
    
    // Hide loading overlay
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.add("is-hidden");
    
    // Calculate total policy announcements
    const sectorKeys = getPolicySectorKeys(data);
    const totalAnnouncements = sectorKeys.reduce(
        (total, key) => total + data.briefing[key].length,
        0
    );
    setText("active-signals-val", totalAnnouncements);
    setText("tracked-sectors-val", sectorKeys.length);
    
    // Calculate total stocks
    const allStocks = Object.values(data.watchlist || {}).flat();
    setText("total-stocks-val", allStocks.length);

    const potentials = allStocks
        .map(stock => parsePercent(stock.growth_pct))
        .filter(value => value !== null);
    const averagePotential = potentials.length
        ? potentials.reduce((total, value) => total + value, 0) / potentials.length
        : null;
    setText("average-potential-val", averagePotential === null ? "-" : `${averagePotential.toFixed(1)}%`);

    const briefing = data.briefing || {};
    setText("agreements-count", (briefing.corporate_agreements || []).length);
    setText("launches-count", (briefing.product_launches || []).length);
    setText("filings-count", (briefing.corporate_filings || []).length);
    setText(
        "institutional-count",
        (briefing.institutional_activity || []).length + (briefing.sebi_filings || []).length
    );
    setText(
        "deep-value-count",
        (briefing.margin_of_safety || []).filter(item => item.is_defensive_pass).length
    );
    setText("competitors-count", countEmergingCompetitors(data));

    // Render components
    renderSectorChips(data);
    renderPolicyFeed(data);
    renderTopPicks(data);
    renderEmergingRadar(data);
    renderCharts(data);
    
    // Setup sector dropdown filter
    const selector = document.getElementById("sector-selector");
    selector.innerHTML = '<option value="all">All Sectors</option>';
    Object.keys(data.sectors).forEach(key => {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = data.sectors[key].label;
        selector.appendChild(option);
    });
    
    selector.addEventListener("change", (e) => {
        activeSectorFilter = e.target.value;
        // Synchronize active chips with dropdown
        const chips = document.querySelectorAll(".sector-chips .chip");
        chips.forEach(chip => {
            const isActive = chip.getAttribute("data-sector") === activeSectorFilter;
            chip.classList.toggle("active", isActive);
            chip.setAttribute("aria-pressed", String(isActive));
        });
        renderPolicyFeed(data);
    });
}

// Render Sector Filter Chips
function renderSectorChips(data) {
    const container = document.getElementById("sector-chips-container");
    container.innerHTML = "";
    
    // Create an 'All' chip
    const allChip = document.createElement("button");
    allChip.type = "button";
    allChip.className = "chip active";
    allChip.setAttribute("data-sector", "all");
    allChip.setAttribute("aria-pressed", "true");
    allChip.textContent = "All Sectors";
    allChip.addEventListener("click", () => handleChipClick("all", allChip));
    container.appendChild(allChip);
    
    // Create individual chips
    Object.keys(data.sectors).forEach(key => {
        const sect = data.sectors[key];
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.setAttribute("data-sector", key);
        chip.setAttribute("aria-pressed", "false");
        chip.textContent = `${sect.icon} ${sect.label}`;
        chip.addEventListener("click", () => handleChipClick(key, chip));
        container.appendChild(chip);
    });
}

function handleChipClick(sectorKey, chipElement) {
    document.querySelectorAll(".sector-chips .chip").forEach(chip => {
        const isActive = chip === chipElement;
        chip.classList.toggle("active", isActive);
        chip.setAttribute("aria-pressed", String(isActive));
    });
    activeSectorFilter = sectorKey;
    
    // Sync with dropdown filter
    document.getElementById("sector-selector").value = sectorKey;
    
    renderPolicyFeed(appData);
}

// Render Policy Bulletin Feed items
function renderPolicyFeed(data) {
    const container = document.getElementById("policy-feed-list");
    container.innerHTML = "";
    
    let feedItems = [];
    const policySectorKeys = getPolicySectorKeys(data);
    
    if (activeSectorFilter === "all") {
        policySectorKeys.forEach(sectorKey => {
            data.briefing[sectorKey].forEach(item => {
                feedItems.push({ ...item, sectorKey });
            });
        });
    } else {
        if (policySectorKeys.includes(activeSectorFilter)) {
            data.briefing[activeSectorFilter].forEach(item => {
                feedItems.push({ ...item, sectorKey: activeSectorFilter });
            });
        }
    }
    
    if (feedItems.length === 0) {
        container.innerHTML = `
            <div class="feed-item">
                <div class="empty-state">
                    <strong>No policy bulletins found</strong>
                    <span>Try another sector or check the next scheduled data refresh.</span>
                </div>
            </div>
        `;
        return;
    }
    
    // Sort items by date descending (simple sorting)
    feedItems.sort((a,b) => new Date(b.date) - new Date(a.date));
    
    feedItems.forEach(item => {
        const el = document.createElement("div");
        el.className = "feed-item";
        
        const badgeClass = item.impact === "Positive" ? "badge-positive" : (item.impact === "Negative" ? "badge-negative" : "badge-neutral");
        const sector = data.sectors[item.sectorKey] || {};
        const sectorLabel = escapeHtml(sector.label || item.sectorKey);
        const sectorIcon = escapeHtml(sector.icon || "•");
        const source = escapeHtml(item.source || "News");
        const impact = escapeHtml(item.impact || "Neutral");
        const title = escapeHtml(item.title || "Untitled update");
        const date = escapeHtml(item.date || "Date unavailable");
        const link = safeExternalUrl(item.link);
        
        let safeLink = "#";
        try {
            if (item.link) {
                const parsedUrl = new URL(item.link, window.location.origin);
                if (parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:") {
                    safeLink = parsedUrl.href;
                }
            }
        } catch (e) {
            // Invalid URL format
        }

        const headerDiv = document.createElement("div");
        headerDiv.className = "feed-item-header";

        const sourceBadge = document.createElement("span");
        sourceBadge.className = "source-badge";
        sourceBadge.textContent = source;

        const impactBadge = document.createElement("span");
        impactBadge.className = `badge ${badgeClass}`;
        impactBadge.textContent = `${impact} Impact`;

        headerDiv.appendChild(sourceBadge);
        headerDiv.appendChild(impactBadge);

        const titleLink = document.createElement("a");
        titleLink.href = link;
        titleLink.className = "feed-item-title";
        titleLink.target = "_blank";
        titleLink.rel = "noopener noreferrer";
        titleLink.textContent = title;

        const metaDiv = document.createElement("div");
        metaDiv.className = "feed-item-meta";

        const sectorTag = document.createElement("span");
        sectorTag.className = "sector-tag";
        sectorTag.textContent = `${sectorIcon} ${sectorLabel}`;

        const dateSpan = document.createElement("span");
        dateSpan.textContent = date;

        metaDiv.appendChild(sectorTag);
        metaDiv.appendChild(dateSpan);

        el.appendChild(headerDiv);
        el.appendChild(titleLink);
        el.appendChild(metaDiv);
        container.appendChild(el);
    });
}

// Render Top Picks Sidebar Highlights
function renderTopPicks(data) {
    const container = document.getElementById("top-picks-list");
    container.innerHTML = "";
    
    let allStocks = [];
    Object.keys(data.watchlist).forEach(sectorKey => {
        data.watchlist[sectorKey].forEach(stock => {
            allStocks.push({ ...stock, sectorKey });
        });
    });
    
    // Filter stocks with growth potential >= 28% and sort descending
    let topPicks = allStocks
        .map(s => {
            const rawPct = s.growth_pct ? parseFloat(s.growth_pct.replace('%', '')) : -999;
            return { ...s, rawPctValue: rawPct };
        })
        .filter(s => s.rawPctValue >= 28)
        .sort((a,b) => b.rawPctValue - a.rawPctValue);
        
    const visiblePicks = topPicks.slice(0, 6);
    if (visiblePicks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <strong>No high-upside picks</strong>
                <span>No watchlist company currently clears the 28% target threshold.</span>
            </div>
        `;
        return;
    }

    visiblePicks.forEach(s => {
        const item = document.createElement("div");
        item.className = "highlight-item";
        item.innerHTML = `
            <div class="hl-left">
                <span class="hl-ticker">${escapeHtml(s.ticker)}</span>
                <span class="hl-name">${escapeHtml(s.name)}</span>
            </div>
            <div class="hl-right">
                <span class="hl-price">CMP: ₹${escapeHtml(s.price)}</span>
                <div class="hl-pct">${s.growth_pct ? formatPotential(s.growth_pct) : '—'} Target</div>
            </div>
        `;
        container.appendChild(item);
    });
}

// Render Emerging Competitors scanned from news
function renderEmergingRadar(data) {
    const container = document.getElementById("radar-picks-list");
    if (!container) return;
    container.innerHTML = "";
    
    const entries = [];
    const groupedCompetitors = {};
    (data.briefing.emerging_competitors || []).forEach(player => {
        const key = `${player.ticker || ""}|${player.name || ""}`.toLowerCase();
        if (!groupedCompetitors[key]) {
            groupedCompetitors[key] = {
                ...player,
                sectorLabel: "PLI approvals",
                sectorIcon: "🏭",
                schemes: new Set([player.announcement || "Detected in a recent PLI approval announcement."])
            };
        } else {
            groupedCompetitors[key].schemes.add(player.announcement || "Detected in a recent PLI approval announcement.");
        }
    });

    Object.values(groupedCompetitors).forEach(comp => {
        const schemeList = Array.from(comp.schemes).map(s => `<li>${escapeHtml(s)}</li>`).join("");
        comp.reason = `<ul style="margin-left: 20px; margin-top: 5px;">${schemeList}</ul>`;
        entries.push(comp);
    });

    Object.entries(data.briefing.emerging_players || {}).forEach(([sectorKey, players]) => {
        if (!Array.isArray(players)) return;
        players.forEach(player => {
            const normalized = player && typeof player === "object"
                ? player
                : { name: player };
            entries.push({
                ...normalized,
                sectorLabel: data.sectors[sectorKey]?.label || sectorKey,
                sectorIcon: data.sectors[sectorKey]?.icon || "🏢"
            });
        });
    });

    const seen = new Set();
    const uniqueEntries = entries.filter(player => {
        const key = `${player.ticker || ""}|${player.name || ""}`.toLowerCase();
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    if (uniqueEntries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <strong>Watchlist stable</strong>
                <span>No new competitors were detected in the latest feed.</span>
            </div>
        `;
        return;
    }

    uniqueEntries.slice(0, 10).forEach(player => {
        const status = player.status || "Radar";
        const statusClass = status === "Watchlisted" || status === "Added"
            ? "badge-success-alert"
            : status === "Growth Divergence" || status === "Rejected" || status === "Unresolved"
                ? "badge-danger-alert"
                : "badge-warning-alert";
        const link = safeExternalUrl(player.link);
        const articleLink = link === "#"
            ? ""
            : `<a class="article-link" href="${link}" target="_blank" rel="noopener noreferrer">Source</a>`;

        const item = document.createElement("div");
        item.className = "highlight-item radar-item";
        item.innerHTML = `
            <div class="radar-main">
                <div class="radar-labels">
                    <span class="radar-kicker">RADAR</span>
                    ${player.ticker ? `<span class="hl-ticker radar-ticker">${escapeHtml(player.ticker)}</span>` : ""}
                </div>
                <span class="radar-name">${escapeHtml(player.name || player.ticker || "Unknown company")}</span>
                ${player.reason ? `<span class="radar-reason">${player.reason}</span>` : ""}
            </div>
            <div class="radar-meta">
                <span class="radar-sector">${escapeHtml(player.sectorIcon)} ${escapeHtml(player.sectorLabel)}</span>
                <span class="${statusClass}">${escapeHtml(status)}</span>
                ${articleLink}
            </div>
        `;
        container.appendChild(item);
    });
}

// Render Comparison Chart using Chart.js
function renderCharts(data) {
    const canvas = document.getElementById("growthChart");
    if (!canvas || typeof Chart === "undefined") {
        canvas?.parentElement?.classList.add("chart-unavailable");
        return;
    }
    canvas.parentElement?.classList.remove("chart-unavailable");
    const ctx = canvas.getContext("2d");
    
    // Calculate average growth potential per sector
    const labels = [];
    const averages = [];
    
    Object.keys(data.watchlist).forEach(sectorKey => {
        const sectorLabel = data.sectors[sectorKey]?.label || sectorKey;
        const stocks = data.watchlist[sectorKey];
        
        let sum = 0;
        let validCount = 0;
        stocks.forEach(s => {
            if (s.growth_pct) {
                sum += parseFloat(s.growth_pct.replace('%', ''));
                validCount++;
            }
        });
        const avg = validCount > 0 ? (sum / validCount).toFixed(1) : 0;
        
        labels.push(sectorLabel);
        averages.push(avg);
    });
    
    if (growthChartInstance) {
        growthChartInstance.destroy();
    }

    const themeStyles = getComputedStyle(document.documentElement);
    const chartTextColor = themeStyles.getPropertyValue("--text-secondary").trim();
    const chartSurfaceColor = themeStyles.getPropertyValue("--bg-surface").trim();
    const chartBorderColor = themeStyles.getPropertyValue("--border-color").trim();
    // One measure across labeled categories -> one hue; the axis carries identity.
    const chartAccent = themeStyles.getPropertyValue("--primary").trim() || "#2a78d6";
    
    growthChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Avg Watchlist Growth Target (%)',
                data: averages,
                backgroundColor: chartAccent,
                borderWidth: 0,
                borderRadius: 4,
                maxBarThickness: 14
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: chartSurfaceColor,
                    titleColor: themeStyles.getPropertyValue("--text-primary").trim(),
                    bodyColor: chartTextColor,
                    borderColor: chartBorderColor,
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: chartBorderColor
                    },
                    ticks: {
                        color: chartTextColor,
                        callback: function(value) { return value + '%'; }
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: chartTextColor,
                        font: {
                            size: 9
                        }
                    }
                }
            }
        }
    });
}

// Sector Detail Tab Setup
function initSectorsTab() {
    const listContainer = document.getElementById("sectors-nav-list");
    listContainer.innerHTML = "";
    
    const sectorKeys = Object.keys(appData.sectors);
    
    sectorKeys.forEach((key, idx) => {
        const sect = appData.sectors[key];
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `sector-nav-item ${idx === 0 ? 'active' : ''}`;
        btn.setAttribute("aria-pressed", String(idx === 0));
        const icon = document.createElement("span");
        icon.textContent = sect.icon;
        btn.append(icon, document.createTextNode(` ${sect.label}`));
        btn.addEventListener("click", () => {
            document.querySelectorAll(".sector-nav-item").forEach(button => {
                const isActive = button === btn;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-pressed", String(isActive));
            });
            renderSectorDetail(key);
        });
        listContainer.appendChild(btn);
    });
    
    // Auto-select first sector on load
    if (sectorKeys.length > 0) {
        renderSectorDetail(sectorKeys[0]);
    }
}

function renderSectorDetail(sectorKey) {
    const sect = appData.sectors[sectorKey];
    const news = appData.briefing[sectorKey] || [];
    const stocks = appData.watchlist[sectorKey] || [];
    const container = document.getElementById("sector-details-content");
    
    let newsHtml = "";
    if (news.length > 0) {
        news.forEach(n => {
            const badgeClass = n.impact === "Positive" ? "badge-positive" : (n.impact === "Negative" ? "badge-negative" : "badge-neutral");
            newsHtml += `
                <div class="feed-item mt-12">
                    <div class="feed-item-header">
                        <span class="source-badge">${escapeHtml(n.source || "News")}</span>
                        <span class="badge ${badgeClass}">${escapeHtml(n.impact || "Neutral")} Impact</span>
                    </div>
                    <a href="${safeExternalUrl(n.link)}" class="feed-item-title" target="_blank" rel="noopener noreferrer">${escapeHtml(n.title || "Untitled update")}</a>
                    <span style="font-size:11px; color: var(--text-muted);">${escapeHtml(n.date || "Date unavailable")}</span>
                </div>
            `;
        });
    } else {
        newsHtml = `<p style="color:var(--text-secondary); font-style:italic;">No recent announcements or policy changes aggregated for this sector.</p>`;
    }
    
    let stocksHtml = "";
    stocks.forEach(s => {
        const analystBadge = formatAnalystBadge(s);
        const growthBadge = formatGrowthBadge(s.revenue_growth, 'badge');
        const earningsBadge = s.earnings_growth ? `<span style="font-size: 9px; padding: 2px 6px; background: rgba(139, 92, 246, 0.12); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">EPS ${s.earnings_growth}</span>` : '';
        
        // Build Screener.in fundamentals row (actual filed data)
        const sc = s.screener || {};
        let screenerHtml = '';
        if (Object.keys(sc).length > 0) {
            const mcapHtml = sc.market_cap ? `<span class="sc-chip" title="Market Cap">MCAP: <strong>₹${Number(sc.market_cap).toLocaleString('en-IN')} Cr</strong></span>` : '';
            const peerLabel = sc.pe_vs_peers ? ` · ${escapeHtml(sc.pe_vs_peers)}` : '';
            const peHtml = sc.pe_ratio ? `<span class="sc-chip" title="Price to Earnings vs sector peer median">P/E: <strong>${sc.pe_ratio}</strong>${sc.industry_pe ? ` <small style="opacity:0.6">vs Peers:${sc.industry_pe}${peerLabel}</small>` : ''}</span>` : '';
            const roceHtml = sc.roce ? `<span class="sc-chip" title="Return on Capital Employed">ROCE: <strong>${sc.roce}%</strong></span>` : '';
            const roeHtml = sc.roe ? `<span class="sc-chip" title="Return on Equity">ROE: <strong>${sc.roe}%</strong></span>` : '';
            
            const qSalesHtml = sc.q_sales ? `<span class="sc-chip" title="Quarterly Sales">Sales: <strong>₹${Number(sc.q_sales).toLocaleString('en-IN')} Cr</strong></span>` : '';
            
            let profitStyle = '';
            let profitLabel = 'Profit';
            if (sc.q_net_profit) {
                const profitNum = parseFloat(sc.q_net_profit);
                if (profitNum < 0) {
                    profitStyle = 'style="background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25);"';
                    profitLabel = 'Loss';
                } else {
                    profitStyle = 'style="background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25);"';
                }
            }
            const qProfitHtml = sc.q_net_profit ? `<span class="sc-chip" ${profitStyle} title="Quarterly Net Profit/Loss">${profitLabel}: <strong>₹${Number(Math.abs(sc.q_net_profit)).toLocaleString('en-IN')} Cr</strong></span>` : '';
            
            const qOpmHtml = sc.q_opm ? `<span class="sc-chip" title="Operating Profit Margin">OPM: <strong>${sc.q_opm}%</strong></span>` : '';
            const qEpsHtml = sc.q_eps ? `<span class="sc-chip" title="Quarterly Earnings Per Share">EPS: <strong>₹${sc.q_eps}</strong></span>` : '';
            
            const promoterHtml = sc.promoter_pct ? `<span class="sc-chip" title="Promoter Shareholding">Promoter: <strong>${sc.promoter_pct}%</strong></span>` : '';
            const fiiHtml = sc.fii_pct ? `<span class="sc-chip" title="Foreign Institutional Investors">FII: <strong>${sc.fii_pct}%</strong></span>` : '';
            const diiHtml = sc.dii_pct ? `<span class="sc-chip" title="Domestic Institutional Investors">DII: <strong>${sc.dii_pct}%</strong></span>` : '';
            let shareHtml = '';
            if (sc.industry_share_pct) {
                const indChange = Number(sc.industry_share_change_pp) || 0;
                const indDelta = indChange ? ` <span style="color: ${indChange > 0 ? '#34d399' : '#f87171'};">(${indChange > 0 ? '+' : ''}${indChange}pp)</span>` : '';
                shareHtml = `<span class="sc-chip" title="Share of the full ${sc.industry_peer_count || ''}-company industry peer group's quarterly revenue (Screener peer table)">Industry Share: <strong>${sc.industry_share_pct}%</strong>${indDelta}</span>`;
            } else if (sc.peer_share_pct) {
                const shareChange = Number(sc.peer_share_change_pp) || 0;
                const shareDelta = shareChange ? ` <span style="color: ${shareChange > 0 ? '#34d399' : '#f87171'};">(${shareChange > 0 ? '+' : ''}${shareChange}pp)</span>` : '';
                shareHtml = `<span class="sc-chip" title="Share of tracked sector peer revenue, change over ${sc.peer_share_lookback || 1} quarter(s)">Peer Share: <strong>${sc.peer_share_pct}%</strong>${shareDelta}</span>`;
            }
            const qtrLabel = sc.latest_quarter ? `<small style="color: #f59e0b; font-size: 9px; font-weight: 700; text-transform: uppercase;">(${sc.latest_quarter})</small>` : '';
            
            screenerHtml = `
                <div class="dsc-fundamentals" style="margin-top: 12px; padding: 12px; background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;">
                    <!-- Ratios & Shareholding Sub-Section -->
                    <div style="margin-bottom: 8px;">
                        <div style="font-size: 8.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 6px; display: flex; justify-content: space-between;">
                            <span>Filed Ratios & Holdings</span>
                            <span style="font-size: 7.5px; opacity: 0.6;">Source: Screener.in</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            ${mcapHtml}${peHtml}${roceHtml}${roeHtml}${promoterHtml}${fiiHtml}${diiHtml}${shareHtml}
                        </div>
                    </div>
                    <!-- Quarterly Earnings Sub-Section -->
                    <div>
                        <div style="font-size: 8.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 6px; display: flex; gap: 6px; align-items: center;">
                            <span>Quarterly Performance</span>
                            ${qtrLabel}
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            ${qSalesHtml}${qProfitHtml}${qOpmHtml}${qEpsHtml}
                        </div>
                    </div>
                </div>`;
        }
        
        const targetValText = s.target ? `₹${s.target}` : '<span style="color: var(--text-muted);">—</span>';
        const medianText = s.target_median ? ` (Median: ₹${s.target_median})` : '';
        const analystDisplay = s.target ? `<span>Target: <strong>${targetValText}</strong><small style="color: var(--text-secondary);">${medianText}</small></span>` : `<span>Target: <strong>—</strong></span>`;

        // Disclose how the upside figure was derived (analyst consensus vs model).
        let methodBadge = '';
        if (s.estimate_method === 'Analyst Consensus') {
            methodBadge = `<span class="method-badge method-analyst" title="Upside from analyst consensus target">Analyst</span>`;
        } else if (s.estimate_method === 'Fundamental Estimate') {
            const fv = s.fundamental_value ? ` (Graham IV ₹${escapeHtml(s.fundamental_value)})` : '';
            methodBadge = `<span class="method-badge method-fundamental" title="Upside derived from Graham intrinsic value${fv}">Model Est.</span>`;
        }

        stocksHtml += `
            <div class="detail-stock-card">
                <div class="dsc-header">
                    <div class="dsc-ticker-group">
                        <h4 style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                            ${escapeHtml(s.name)}
                            <span style="background-color: rgba(59, 130, 246, 0.1); color: var(--primary); padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px;">${escapeHtml(s.ticker)}</span>
                            ${analystBadge}
                            ${growthBadge}
                            ${earningsBadge}
                        </h4>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px;">
                        <span class="dsc-pot">${formatPotential(s.growth_pct)}</span>
                        ${methodBadge}
                    </div>
                </div>
                <div class="dsc-metrics" style="margin-top: 12px;">
                    <span>CMP: <strong>₹${escapeHtml(s.price)}</strong></span>
                    ${analystDisplay}
                    <span>Analysts: <strong>${escapeHtml(s.analyst_count || '—')}</strong></span>
                </div>
                <p class="dsc-catalyst"><strong>Watchlist Catalyst:</strong> ${escapeHtml(s.catalyst)}</p>
                ${screenerHtml}
            </div>
        `;
    });
    
    container.innerHTML = `
        <div class="detail-header">
            <div class="detail-header-top">
                <span>${escapeHtml(sect.icon)}</span>
                <h3>${escapeHtml(sect.label)}</h3>
            </div>
            <p>${escapeHtml(sect.desc)}</p>
        </div>
        
        <div class="detail-body-grid">
            <div>
                <h4 class="detail-sub-header">Recent Sector Bulletins</h4>
                <div style="max-height:450px; overflow-y:auto; padding-right:8px;">
                    ${newsHtml}
                </div>
            </div>
            
            <div>
                <h4 class="detail-sub-header">Curated Growth Portfolios</h4>
                <div style="max-height:450px; overflow-y:auto; padding-right:8px;">
                    ${stocksHtml}
                </div>
            </div>
        </div>
    `;
}

// Stock Screener Matrix Rendering
let currentSortColumn = 'potential';
let currentSortDirection = 'desc';

function renderStocksTable(filterQuery = "") {
    const tbody = document.getElementById("stocks-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const query = filterQuery.toLowerCase().trim();
    let allStocksList = [];
    
    // Flatten data for sorting
    Object.keys(appData.watchlist).forEach(sectorKey => {
        const sectorLabel = appData.sectors[sectorKey].label;
        const stocks = appData.watchlist[sectorKey];
        
        stocks.forEach(s => {
            const matchesSearch = !query || 
                String(s.ticker || "").toLowerCase().includes(query) ||
                String(s.name || "").toLowerCase().includes(query) ||
                String(s.catalyst || "").toLowerCase().includes(query) ||
                sectorLabel.toLowerCase().includes(query);
                
            if (matchesSearch) {
                allStocksList.push({
                    ...s,
                    sectorLabel: sectorLabel,
                    sectorKey: sectorKey
                });
            }
        });
    });

    // Sort logic
    allStocksList.sort((a, b) => {
        let valA, valB;

        const parseNumeric = (val) => {
            if (val === undefined || val === null || val === 'N/A' || val === '—') return -999999;
            const parsed = parseFloat(String(val).replace(/[^0-9.-]+/g, ""));
            return isNaN(parsed) ? -999999 : parsed;
        };

        switch (currentSortColumn) {
            case 'ticker': valA = a.ticker; valB = b.ticker; break;
            case 'company': valA = a.name; valB = b.name; break;
            case 'sector': valA = a.sectorLabel; valB = b.sectorLabel; break;
            case 'cmp': valA = parseNumeric(a.price); valB = parseNumeric(b.price); break;
            case 'pe': valA = parseNumeric(a.screener?.pe_ratio); valB = parseNumeric(b.screener?.pe_ratio); break;
            case 'qoq': valA = parseNumeric(a.screener?.qoq_sales_growth); valB = parseNumeric(b.screener?.qoq_sales_growth); break;
            case 'roce': valA = parseNumeric(a.screener?.roce); valB = parseNumeric(b.screener?.roce); break;
            case 'roe': valA = parseNumeric(a.screener?.roe); valB = parseNumeric(b.screener?.roe); break;
            case 'capex': valA = parseNumeric(a.screener?.capex); valB = parseNumeric(b.screener?.capex); break;
            case 'oe': valA = parseNumeric(a.screener?.owner_earnings); valB = parseNumeric(b.screener?.owner_earnings); break;
            case 'graham': valA = parseNumeric(a.screener?.graham_intrinsic_value); valB = parseNumeric(b.screener?.graham_intrinsic_value); break;
            case 'target': valA = parseNumeric(a.target); valB = parseNumeric(b.target); break;
            case 'potential': valA = parseNumeric(a.growth_pct); valB = parseNumeric(b.growth_pct); break;
            case 'growth': valA = parseNumeric(a.revenue_growth); valB = parseNumeric(b.revenue_growth); break;
            case 'inst':
                const changeA = parseNumeric(a.screener?.fii_change) + parseNumeric(a.screener?.dii_change);
                const changeB = parseNumeric(b.screener?.fii_change) + parseNumeric(b.screener?.dii_change);
                valA = changeA; valB = changeB; break;
            case 'rating':
                const ratingScore = (r) => {
                    if (r === 'Strong Buy') return 4;
                    if (r === 'Buy') return 3;
                    if (r === 'Hold') return 2;
                    if (r === 'Underperform' || r === 'Sell') return 1;
                    return 0;
                };
                valA = ratingScore(a.rating); valB = ratingScore(b.rating); break;
            default: valA = parseNumeric(a.growth_pct); valB = parseNumeric(b.growth_pct);
        }

        if (typeof valA === 'string' && typeof valB === 'string') {
            return currentSortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else {
            return currentSortDirection === 'asc' ? valA - valB : valB - valA;
        }
    });

    // Render sorted list
    allStocksList.forEach(s => {
        const sectorKey = s.sectorKey;
        const sectorLabel = s.sectorLabel;
        const sc = s.screener || {};
        const peVal = sc.pe_ratio ? sc.pe_ratio : '<span style="color: var(--text-muted);">—</span>';
        const roceVal = sc.roce ? `${sc.roce}%` : '<span style="color: var(--text-muted);">—</span>';
        const roeVal = sc.roe ? `${sc.roe}%` : '<span style="color: var(--text-muted);">—</span>';

        const qoqSalesVal = sc.qoq_sales_growth !== undefined ? `<strong>${sc.qoq_sales_growth}%</strong>` : '<span style="color: var(--text-muted);">—</span>';
        const capexVal = sc.capex !== undefined ? `₹${Number(sc.capex).toLocaleString('en-IN')}` : '<span style="color: var(--text-muted);">—</span>';
        const oeVal = sc.owner_earnings !== undefined ? `₹${Number(sc.owner_earnings).toLocaleString('en-IN')}` : '<span style="color: var(--text-muted);">—</span>';
        const grahamVal = sc.graham_intrinsic_value !== undefined ? `₹${sc.graham_intrinsic_value}` : '<span style="color: var(--text-muted);">—</span>';
        
        let valAlertsHtml = '';
        if (sectorKey === "macro_indicators") {
            valAlertsHtml = '<span style="color: var(--text-muted);">ETF (N/A)</span>';
        } else if (sc.valuation_alerts && sc.valuation_alerts.length > 0) {
            valAlertsHtml = sc.valuation_alerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 8px;">${escapeHtml(a)}</span>`).join('');
        } else {
            valAlertsHtml = '<span class="badge-success-alert" style="font-size: 8px;">PASSED</span>';
        }

        let instChangeHtml = '';
        if (sectorKey === "macro_indicators") {
            instChangeHtml = '<span style="color: var(--text-muted);">—</span>';
        } else {
            const diiChg = sc.dii_change || 0.0;
            const fiiChg = sc.fii_change || 0.0;
            let diiBadge = '';
            let fiiBadge = '';
            if (diiChg > 0) {
                diiBadge = `<span class="badge-success-alert" style="margin-right: 4px; font-size: 9px;">MFs +${diiChg}%</span>`;
            } else if (diiChg < 0) {
                diiBadge = `<span class="badge-danger-alert" style="margin-right: 4px; font-size: 9px;">MFs ${diiChg}%</span>`;
            }
            if (fiiChg > 0) {
                fiiBadge = `<span class="badge-success-alert" style="font-size: 9px;">FIIs +${fiiChg}%</span>`;
            } else if (fiiChg < 0) {
                fiiBadge = `<span class="badge-danger-alert" style="font-size: 9px;">FIIs ${fiiChg}%</span>`;
            }
            instChangeHtml = (diiBadge || fiiBadge) ? `${diiBadge}${fiiBadge}` : '<span style="color: var(--text-muted);">0.0%</span>';
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHtml(s.ticker)}</td>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(sectorLabel)}</span></td>
            <td class="num">₹${escapeHtml(s.price)}</td>
            <td class="num">${peVal}</td>
            <td class="num">${qoqSalesVal}</td>
            <td class="num">${roceVal}</td>
            <td class="num">${roeVal}</td>
            <td class="num">${capexVal}</td>
            <td class="num">${oeVal}</td>
            <td class="num">${grahamVal}</td>
            <td class="num">${s.target ? `₹${escapeHtml(s.target)}` : '<span style="color: var(--text-muted);">—</span>'}</td>
            <td class="t-potential num">${formatPotential(s.growth_pct)}</td>
            <td>${formatGrowthBadge(s.revenue_growth, 'table')}</td>
            <td>${instChangeHtml}</td>
            <td style="max-width: 150px; white-space: normal;">${valAlertsHtml}</td>
            <td>${formatAnalystBadge(s)}</td>
            <td style="max-width: 280px; white-space: normal; font-size: 11px;">${escapeHtml(s.catalyst)}</td>
        `;
        tbody.appendChild(tr);
    });

    if (allStocksList.length === 0) {
        setTableEmpty(tbody, 18, "No matching companies", "Try a ticker, company, sector, or catalyst keyword.");
    }

    updateSortHeaders();
}

// Search Filter Input
function setupStockSearch() {
    const input = document.getElementById("stock-search");
    if (input) {
        input.addEventListener("input", (e) => {
            renderStocksTable(e.target.value);
        });
    }
    setupTableSorting();
}

// Table column sorting setup
function setupTableSorting() {
    const headers = document.querySelectorAll("th.sortable");
    headers.forEach(header => {
        header.tabIndex = 0;
        header.setAttribute("role", "button");
        const applySort = () => {
            const column = header.getAttribute("data-sort");
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'desc'; // Default to desc for new column
            }
            renderStocksTable(document.getElementById("stock-search").value);
        };
        header.addEventListener("click", applySort);
        header.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                applySort();
            }
        });
    });
}

function updateSortHeaders() {
    const headers = document.querySelectorAll("th.sortable");
    headers.forEach(header => {
        header.classList.remove("asc", "desc");
        header.setAttribute("aria-sort", "none");
        if (header.getAttribute("data-sort") === currentSortColumn) {
            header.classList.add(currentSortDirection);
            header.setAttribute(
                "aria-sort",
                currentSortDirection === "asc" ? "ascending" : "descending"
            );
        }
    });
}

// Theme Toggle Logic
function setupThemeToggle() {
    const toggleBtn = document.getElementById("theme-toggle");
    if (!toggleBtn) return;

    const savedTheme = localStorage.getItem('bharat-policy-theme');
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    applyTheme(savedTheme || (prefersLight ? "light" : "dark"));

    toggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || "dark";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        applyTheme(newTheme);
        localStorage.setItem('bharat-policy-theme', newTheme);
        if (appData) renderCharts(appData);
    });
}

function applyTheme(theme) {
    const normalizedTheme = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", normalizedTheme);

    const isLight = normalizedTheme === "light";
    setText("theme-toggle-text", isLight ? "Dark theme" : "Light theme");

    const toggleBtn = document.getElementById("theme-toggle");
    toggleBtn?.setAttribute("aria-label", isLight ? "Switch to dark theme" : "Switch to light theme");
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
        "content",
        isLight ? "#f8fafc" : "#070a13"
    );
}

// Render Corporate Agreements List
function renderAgreementsTable() {
    const tbody = document.getElementById("agreements-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const agreements = appData.briefing.corporate_agreements || [];
    if (agreements.length === 0) {
        setTableEmpty(tbody, 4, "No corporate agreements", "No matching signals were found in this cycle.");
        return;
    }
    
    agreements.forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span class="source-badge">${escapeHtml(a.source || "News")}</span></td>
            <td><strong>${escapeHtml(a.title || "Untitled update")}</strong></td>
            <td>${escapeHtml(a.date || "Date unavailable")}</td>
            <td><a href="${safeExternalUrl(a.link)}" class="article-link" target="_blank" rel="noopener noreferrer">View article</a></td>
        `;
        tbody.appendChild(tr);
    });
}

// Render Product Launches List
function renderLaunchesTable() {
    const tbody = document.getElementById("launches-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const launches = appData.briefing.product_launches || [];
    if (launches.length === 0) {
        setTableEmpty(tbody, 4, "No product launches", "No matching launch signals were found in this cycle.");
        return;
    }
    
    launches.forEach(l => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${escapeHtml(l.company || "Unknown")}</strong></td>
            <td><strong>${escapeHtml(l.product || l.title || "Untitled update")}</strong></td>
            <td><span class="badge badge-neutral">${escapeHtml(l.industry || "Manufacturing")}</span></td>
            <td>${escapeHtml(l.date || "Date unavailable")}</td>
            <td><span class="source-badge">${escapeHtml(l.source || "News")}</span></td>
            <td><a href="${safeExternalUrl(l.link)}" class="article-link" target="_blank" rel="noopener noreferrer">View article</a></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderFilingsTable() {
    const tbody = document.getElementById("filings-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const filings = appData.briefing.corporate_filings || [];
    if (filings.length === 0) {
        setTableEmpty(tbody, 6, "No recent filings", "No matching corporate exchange filings were found in this cycle.");
        return;
    }

    filings.forEach(f => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${escapeHtml(f.company || "Unknown")}</strong></td>
            <td><strong>${escapeHtml(f.filing || "Untitled filing")}</strong></td>
            <td><span class="badge badge-neutral">${escapeHtml(f.industry || "Corporate")}</span></td>
            <td>${escapeHtml(f.date || "Date unavailable")}</td>
            <td><span class="source-badge">${escapeHtml(f.source || "Exchange")}</span></td>
            <td><a href="${safeExternalUrl(f.link)}" class="article-link" target="_blank" rel="noopener noreferrer">View filing</a></td>
        `;
        tbody.appendChild(tr);
    });
}

// Render Institutional Flows
function renderInstitutionalFlows() {
    // SEBI Filings Table
    const sebiBody = document.getElementById("sebi-filings-body");
    if (sebiBody) {
        sebiBody.innerHTML = "";
        const filings = appData.briefing.sebi_filings || [];
        if (filings.length === 0) {
            setTableEmpty(sebiBody, 5, "No thematic fund filings", "No relevant SEBI SID filing was detected.");
        } else {
            filings.forEach(f => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${escapeHtml(f.fund_name || "Unnamed scheme")}</strong></td>
                    <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(f.theme || "Other")}</span></td>
                    <td><span class="badge-success-alert">${escapeHtml(f.status || "Filed")}</span></td>
                    <td>${escapeHtml(f.date || "Date unavailable")}</td>
                    <td><a href="${safeExternalUrl(f.link)}" class="article-link" target="_blank" rel="noopener noreferrer">View document</a></td>
                `;
                sebiBody.appendChild(tr);
            });
        }
    }
    
    // Institutional Activity Table
    const instBody = document.getElementById("inst-activity-body");
    if (instBody) {
        instBody.innerHTML = "";
        const activity = appData.briefing.institutional_activity || [];
        if (activity.length === 0) {
            setTableEmpty(instBody, 7, "No institutional deals", "No matching block or bulk deal was detected.");
        } else {
            activity.forEach(act => {
                const actionBadge = act.action === "Buy" ? 
                    `<span class="badge-success-alert">BUY</span>` : 
                    `<span class="badge-danger-alert">SELL</span>`;
                    
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><span class="source-badge">${escapeHtml(act.source || "News")}</span></td>
                    <td><strong>${escapeHtml(act.buyer || "Institutional investor")}</strong></td>
                    <td>${actionBadge}</td>
                    <td><strong>${escapeHtml(act.company || "Listed company")}</strong></td>
                    <td>${escapeHtml(act.details || "Deal details unavailable")}</td>
                    <td>${escapeHtml(act.date || "Date unavailable")}</td>
                    <td><a href="${safeExternalUrl(act.link)}" class="article-link" target="_blank" rel="noopener noreferrer">View</a></td>
                `;
                instBody.appendChild(tr);
            });
        }
    }

    // Institutional Accumulation Baseline (historical MF NAV backtesting)
    const baselineBody = document.getElementById("mf-baseline-body");
    if (baselineBody) {
        baselineBody.innerHTML = "";
        const baseline = appData.briefing.institutional_baseline || [];
        if (baseline.length === 0) {
            setTableEmpty(baselineBody, 7, "No baseline data", "Historical mutual-fund NAV data was not available in the latest cycle.");
        } else {
            baseline.forEach(b => {
                const trend = b.accumulation_trend || "Steady";
                const trendBadge = trend === "Accelerating"
                    ? `<span class="badge-success-alert">▲ ${escapeHtml(trend)}</span>`
                    : trend === "Decelerating"
                        ? `<span class="badge-danger-alert">▼ ${escapeHtml(trend)}</span>`
                        : `<span class="badge-warning-alert">▬ ${escapeHtml(trend)}</span>`;
                const fmt = v => (v === null || v === undefined) ? "—" : `${v > 0 ? "+" : ""}${v}%`;
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(b.theme || "Other")}</span></td>
                    <td><strong>${escapeHtml(b.fund_name || "Unnamed scheme")}</strong></td>
                    <td>${escapeHtml(String(b.latest_nav ?? "—"))}</td>
                    <td>${fmt(b.return_1m)}</td>
                    <td>${fmt(b.return_3m)}</td>
                    <td><strong>${fmt(b.return_1y)}</strong></td>
                    <td>${trendBadge}</td>
                `;
                baselineBody.appendChild(tr);
            });
        }
    }
}

// Render Graham Valuation Table
function renderGrahamTable() {
    const tbody = document.getElementById("graham-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const stocks = getStockList();
    
    stocks.forEach(s => {
        const sc = s.screener || {};
        
        // Skip macro indicators
        if (s.sectorKey === "macro_indicators") return;
        
        const pe = sc.pe_ratio !== undefined ? sc.pe_ratio : '—';
        const cr = sc.current_ratio !== undefined ? sc.current_ratio : '—';
        const ncav = sc.net_current_assets !== undefined ? `₹${Number(sc.net_current_assets).toLocaleString('en-IN')}` : '—';
        const grahamVal = sc.graham_intrinsic_value !== undefined ? `₹${sc.graham_intrinsic_value}` : '—';
        
        const isBargainBadge = sc.is_bargain ? 
            `<span class="badge-success-alert">YES</span>` : 
            `<span style="color: var(--text-muted);">No</span>`;
            
        // Passed defensive if no "Current Ratio", "Debt Limit", or "P/E Screen" failures
        const alerts = sc.valuation_alerts || [];
        const hasGrahamFailures = alerts.some(a => a.includes("Current Ratio") || a.includes("Debt Limit") || a.includes("P/E Screen"));
        const hasGrahamData = sc.current_ratio !== undefined
            && sc.pe_ratio !== undefined
            && sc.graham_intrinsic_value !== undefined;
        const isDefensiveBadge = !hasGrahamData
            ? `<span class="badge-warning-alert">NOT SCORED</span>`
            : hasGrahamFailures
                ? `<span class="badge-danger-alert">FAIL</span>`
                : `<span class="badge-success-alert">PASS</span>`;
            
        let alertBadges = '';
        const grahamAlerts = alerts.filter(a => a.includes("Current Ratio") || a.includes("Debt Limit") || a.includes("P/E Screen") || a.includes("Dividend"));
        if (grahamAlerts.length > 0) {
            alertBadges = grahamAlerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 9px;">${escapeHtml(a)}</span>`).join('');
        } else {
            alertBadges = `<span style="color: var(--text-muted);">None</span>`;
        }
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHtml(s.ticker)}</td>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td>₹${escapeHtml(s.price)}</td>
            <td><strong>${pe}</strong></td>
            <td>${cr}</td>
            <td>${ncav}</td>
            <td><strong>${grahamVal}</strong></td>
            <td>${isBargainBadge}</td>
            <td>${isDefensiveBadge}</td>
            <td style="max-width: 300px; white-space: normal;">${alertBadges}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Render Buffett Valuation Table
function renderBuffettTable() {
    const tbody = document.getElementById("buffett-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const stocks = getStockList();
    
    stocks.forEach(s => {
        const sc = s.screener || {};
        
        // Skip macro indicators
        if (s.sectorKey === "macro_indicators") return;
        
        const oe = sc.owner_earnings !== undefined ? `₹${Number(sc.owner_earnings).toLocaleString('en-IN')}` : '—';
        const retainedRatio = sc.retained_earnings_ratio !== undefined ? sc.retained_earnings_ratio : '—';
        
        const passedRetained = sc.retained_earnings_ratio === undefined
            ? `<span class="badge-warning-alert">NOT SCORED</span>`
            : sc.retained_earnings_ratio >= 1.0
                ? `<span class="badge-success-alert">PASS (>= 1.0)</span>`
                : `<span class="badge-danger-alert">FAIL (< 1.0)</span>`;
            
        const moat = sc.moat_status || 'Weak/None';
        let moatBadge = '';
        if (moat.includes("Strong")) {
            moatBadge = `<span class="badge-success-alert">${escapeHtml(moat)}</span>`;
        } else if (moat.includes("Medium")) {
            moatBadge = `<span class="badge-warning-alert">${escapeHtml(moat)}</span>`;
        } else {
            moatBadge = `<span class="badge-danger-alert">${escapeHtml(moat)}</span>`;
        }
        
        const alerts = sc.valuation_alerts || [];
        const buffettAlerts = alerts.filter(a => a.includes("Retained Earnings") || a.includes("Moat"));
        let alertBadges = '';
        if (buffettAlerts.length > 0) {
            alertBadges = buffettAlerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 9px;">${escapeHtml(a)}</span>`).join('');
        } else {
            alertBadges = `<span style="color: var(--text-muted);">None</span>`;
        }
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHtml(s.ticker)}</td>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td>₹${escapeHtml(s.price)}</td>
            <td><strong>${oe}</strong></td>
            <td><strong>${retainedRatio}</strong></td>
            <td>${passedRetained}</td>
            <td>${moatBadge}</td>
            <td style="max-width: 250px; white-space: normal;">${alertBadges}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Render AI Scoring Engine Table
function renderScoringTable() {
    const tbody = document.getElementById("scoring-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const stocks = getStockList();
    
    stocks.forEach(s => {
        // Skip macro indicators
        if (s.sectorKey === "macro_indicators") return;
        
        const sc = s.screener || {};
        const scoreData = s.score || {};
        const overallScore = scoreData.overall_score || 0;
        const confidence = scoreData.confidence || "Unknown";
        
        let confBadge = '';
        if (confidence === "High") confBadge = `<span class="badge-success-alert">High</span>`;
        else if (confidence === "Medium") confBadge = `<span class="badge-warning-alert">Medium</span>`;
        else confBadge = `<span class="badge-danger-alert">${escapeHtml(confidence)}</span>`;
        
        let recommendations = (scoreData.recommendations || []).map(r => {
            const cssClass = r.includes("Strong Buy") ? "badge-success-alert" : r.includes("Buy") ? "badge-success-alert" : r.includes("Monitor") ? "badge-danger-alert" : "badge-warning-alert";
            return `<span class="${cssClass}" style="margin-right: 4px; margin-bottom: 4px; display: inline-block;">${escapeHtml(r)}</span>`;
        }).join('');
        
        let reasonsHtml = (scoreData.reasons || []).map(r => `<div style="font-size: 11px; margin-bottom:2px;">ðŸ‘ ${escapeHtml(r)}</div>`).join('');
        if (!reasonsHtml) reasonsHtml = '<span style="color: var(--text-muted);">None</span>';
        
        let risksHtml = (scoreData.risks || []).map(r => `<div style="font-size: 11px; margin-bottom:2px; color: var(--danger-color);">âš ï¸  ${escapeHtml(r)}</div>`).join('');
        if (!risksHtml) risksHtml = '<span style="color: var(--text-muted);">None</span>';
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>
                <div class="t-ticker">${escapeHtml(s.ticker)}</div>
                <div style="font-size: 11px; font-weight: normal; margin-top:2px; color: var(--text-muted);">${escapeHtml(s.name)}</div>
            </td>
            <td><strong>${overallScore}</strong></td>
            <td>${confBadge}</td>
            <td style="max-width: 150px; white-space: normal;">${recommendations}</td>
            <td style="max-width: 250px; white-space: normal;">${reasonsHtml}</td>
            <td style="max-width: 250px; white-space: normal;">${risksHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Render Valuation Warnings & Risk Alerts (Caution List)
function renderCautionTable() {
    const tbody = document.getElementById("caution-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const stocks = getStockList();
    let cautionCount = 0;
    
    stocks.forEach(s => {
        const sc = s.screener || {};
        
        // Skip macro indicators
        if (s.sectorKey === "macro_indicators") return;
        
        const alerts = sc.valuation_alerts || [];
        if (alerts.length > 0) {
            const sectorLabel = appData.sectors[s.sectorKey]?.label || s.sectorKey;
            const alertBadges = alerts.map(a => {
                const badgeClass = a.includes("Warning") ? "badge-danger-alert" : "badge-warning-alert";
                return `<span class="${badgeClass}" style="margin-right: 6px; margin-bottom: 6px; display: inline-block; font-size: 9px;">${escapeHtml(a)}</span>`;
            }).join('');
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="t-ticker">${escapeHtml(s.ticker)}</td>
                <td><strong>${escapeHtml(s.name)}</strong></td>
                <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(sectorLabel)}</span></td>
                <td>₹${escapeHtml(s.price)}</td>
                <td style="max-width: 450px; white-space: normal;">${alertBadges}</td>
            `;
            tbody.appendChild(tr);
            cautionCount++;
        }
    });
    
    if (cautionCount === 0) {
        setTableEmpty(tbody, 5, "No caution flags", "All scored watchlist companies passed the configured checks.");
    }
}

// Early Warning System: prioritized risk & opportunity feed
const SEVERITY_BADGE_CLASS = {
    Critical: "badge-danger-alert",
    High: "badge-danger-alert",
    Medium: "badge-warning-alert",
    Low: "badge-neutral-alert"
};

// Active early-warning filters (severity chip, direction chip, free text).
const warningFilters = { severity: "all", direction: "all", query: "" };

function setupWarningFilters() {
    const bar = document.getElementById("warning-filters");
    if (!bar) return;
    bar.querySelectorAll(".filter-group").forEach(group => {
        const key = group.getAttribute("data-filter-group");
        group.querySelectorAll(".filter-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                group.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                warningFilters[key] = chip.getAttribute("data-filter-value");
                renderEarlyWarnings();
            });
        });
    });
    const search = document.getElementById("warning-search");
    if (search) {
        search.addEventListener("input", e => {
            warningFilters.query = e.target.value.trim().toLowerCase();
            renderEarlyWarnings();
        });
    }
}

function renderEarlyWarnings() {
    const tbody = document.getElementById("early-warning-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const all = (appData && appData.briefing && appData.briefing.early_warnings) || [];
    const warnings = all.filter(w => {
        if (warningFilters.severity !== "all" && (w.severity || "Low") !== warningFilters.severity) return false;
        if (warningFilters.direction !== "all" && w.direction !== warningFilters.direction) return false;
        if (warningFilters.query) {
            const haystack = `${w.ticker} ${w.name} ${w.sector} ${w.category} ${w.signal}`.toLowerCase();
            if (!haystack.includes(warningFilters.query)) return false;
        }
        return true;
    });

    const countEl = document.getElementById("warning-count");
    if (countEl) countEl.textContent = `${warnings.length} of ${all.length} signals`;

    if (warnings.length === 0) {
        const msg = all.length === 0 ? "No active warnings" : "No signals match the current filters";
        setTableEmpty(tbody, 6, msg, all.length === 0 ? "No risk or opportunity signals were triggered in the latest cycle." : "Adjust the severity, direction, or text filters above.");
        return;
    }

    warnings.forEach(w => {
        const severity = w.severity || "Low";
        const badgeClass = SEVERITY_BADGE_CLASS[severity] || "badge-neutral-alert";
        const isRisk = w.direction === "risk";
        const dirIcon = isRisk ? "▼" : "▲";
        const dirColor = isRisk ? "var(--danger, #f87171)" : "var(--success, #34d399)";

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHtml(w.ticker)}</td>
            <td><strong>${escapeHtml(w.name)}</strong></td>
            <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(w.sector)}</span></td>
            <td><span class="${badgeClass}" style="font-size: 9px;">${escapeHtml(severity)}</span></td>
            <td style="color: ${dirColor}; white-space: nowrap;">${dirIcon} ${escapeHtml(w.category)}</td>
            <td style="max-width: 420px; white-space: normal;">${escapeHtml(w.signal)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderSectorValuation() {
    const tbody = document.getElementById("sector-valuation-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const rollup = (appData && appData.briefing && appData.briefing.sector_valuation) || [];

    if (rollup.length === 0) {
        setTableEmpty(tbody, 5, "No valuation data", "No P/E data was available across the watchlist this cycle.");
        return;
    }

    rollup.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${escapeHtml(r.label)}</td>
            <td><strong>${escapeHtml(r.median_pe)}</strong></td>
            <td>${escapeHtml(r.stock_count)}</td>
            <td style="color: var(--success, #34d399);">${escapeHtml(r.cheapest_ticker)} <small>(${escapeHtml(r.cheapest_pe)})</small></td>
            <td style="color: var(--danger, #f87171);">${escapeHtml(r.most_expensive_ticker)} <small>(${escapeHtml(r.most_expensive_pe)})</small></td>
        `;
        tbody.appendChild(tr);
    });

    renderSectorGrowth();
}

function renderSectorGrowth() {
    const tbody = document.getElementById("sector-growth-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const rollup = (appData && appData.briefing && appData.briefing.sector_growth) || [];

    if (rollup.length === 0) {
        setTableEmpty(tbody, 5, "No growth data yet", "Sector growth needs each holding's quarterly revenue series; it populates as Screener fundamentals load.");
        return;
    }

    rollup.forEach(r => {
        const fmt = v => (v > 0 ? `+${v}%` : `${v}%`);
        const yoyColor = (r.median_yoy_pct || 0) >= 0 ? "var(--success, #34d399)" : "var(--danger, #f87171)";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${escapeHtml(r.label)}</td>
            <td class="num" style="color: ${yoyColor}; font-weight: 700;">${escapeHtml(fmt(r.median_yoy_pct))}</td>
            <td class="num">${escapeHtml(fmt(r.median_cagr_pct))}</td>
            <td class="num">${escapeHtml(r.stock_count)}</td>
            <td><span class="t-ticker">${escapeHtml(r.fastest_ticker)}</span> <small style="color: var(--text-secondary);">${escapeHtml(fmt(r.fastest_yoy_pct))}</small></td>
        `;
        tbody.appendChild(tr);
    });
}

const THESIS_BADGE_CLASS = {
    Broken: "badge-danger-alert",
    Weakening: "badge-warning-alert",
    Intact: "badge-success-alert"
};

function renderResearchEngine() {
    const briefing = (appData && appData.briefing) || {};
    const thesisHealth = briefing.thesis_health || {};
    const revisions = briefing.estimate_revisions || [];
    const variant = briefing.variant_perception || [];
    const curveStage = briefing.curve_stage || {};
    const hitRate = briefing.rotation_hit_rate || {};
    const recentOutcomes = briefing.rotation_recent_outcomes || [];

    const thesisRows = Object.values(thesisHealth);
    const flagged = thesisRows.filter(r => r.status !== "Intact")
        .sort((a, b) => (a.status === "Broken" ? 0 : 1) - (b.status === "Broken" ? 0 : 1));
    const intactCount = thesisRows.length - flagged.length;

    setText("thesis-intact-count", thesisRows.length ? intactCount : "—");
    setText("thesis-flagged-count", thesisRows.length ? flagged.length : "—");
    setText("variant-count", variant.length || (variant.length === 0 ? "0" : "—"));

    if (hitRate.total_scored) {
        setText("rotation-win-rate", `${hitRate.win_rate_pct}%`);
        setText("rotation-win-rate-sub", `${hitRate.wins}/${hitRate.total_scored} decisions playing out`);
    } else {
        setText("rotation-win-rate", "—");
        setText("rotation-win-rate-sub", "No decisions have reached the 45-day scoring window yet");
    }

    // Thesis health table
    const thesisBody = document.getElementById("thesis-table-body");
    if (thesisBody) {
        thesisBody.innerHTML = "";
        if (flagged.length === 0) {
            setTableEmpty(thesisBody, 5, "Every thesis is intact", "No holding has a risk signal or negative revision serious enough to flag this cycle.");
        } else {
            flagged.forEach(r => {
                const badgeClass = THESIS_BADGE_CLASS[r.status] || "badge-neutral-alert";
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="t-ticker">${escapeHtml(r.ticker)}</td>
                    <td><strong>${escapeHtml(r.name)}</strong></td>
                    <td><span class="chip" style="display:inline-block; border-color:transparent;">${escapeHtml(r.sector)}</span></td>
                    <td><span class="${badgeClass}" style="font-size: 9px;">${escapeHtml(r.status)}</span></td>
                    <td style="max-width: 380px; white-space: normal; font-size: 12px;">${escapeHtml((r.reasons || []).join(" "))}</td>
                `;
                thesisBody.appendChild(tr);
            });
        }
    }

    // Estimate revision momentum table
    const revBody = document.getElementById("revisions-table-body");
    if (revBody) {
        revBody.innerHTML = "";
        if (revisions.length === 0) {
            setTableEmpty(revBody, 5, "No material revisions", "No stock's consensus target moved enough versus the prior run to register.");
        } else {
            revisions.forEach(r => {
                const up = r.direction === "up";
                const color = up ? "var(--success, #34d399)" : "var(--danger, #f87171)";
                const arrow = up ? "▲" : "▼";
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="t-ticker">${escapeHtml(r.ticker)}</td>
                    <td>${escapeHtml(r.sector)}</td>
                    <td class="num" style="color: ${color}; font-weight: 700;">${arrow} ${r.target_change_pct > 0 ? "+" : ""}${escapeHtml(r.target_change_pct)}%</td>
                    <td class="num">${r.analyst_count_change != null ? (r.analyst_count_change > 0 ? "+" : "") + escapeHtml(r.analyst_count_change) : "—"}</td>
                    <td class="num">${r.rec_score_change != null ? (r.rec_score_change > 0 ? "+" : "") + escapeHtml(r.rec_score_change) : "—"}</td>
                `;
                revBody.appendChild(tr);
            });
        }
    }

    // Variant perception table
    const variantBody = document.getElementById("variant-table-body");
    if (variantBody) {
        variantBody.innerHTML = "";
        if (variant.length === 0) {
            setTableEmpty(variantBody, 5, "No large divergences", "No analyst-covered stock's independent Graham estimate diverges 15% or more from consensus this cycle.");
        } else {
            variant.forEach(r => {
                const bullish = r.direction === "more_bullish";
                const color = bullish ? "var(--success, #34d399)" : "var(--danger, #f87171)";
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="t-ticker">${escapeHtml(r.ticker)}</td>
                    <td>${escapeHtml(r.sector)}</td>
                    <td class="num">&#8377;${escapeHtml(r.our_estimate)}</td>
                    <td class="num">&#8377;${escapeHtml(r.consensus_target)}</td>
                    <td class="num" style="color: ${color}; font-weight: 700;">${r.divergence_pct > 0 ? "+" : ""}${escapeHtml(r.divergence_pct)}%</td>
                `;
                variantBody.appendChild(tr);
            });
        }
    }

    // Sector curve stage table
    const curveBody = document.getElementById("curve-stage-table-body");
    if (curveBody) {
        curveBody.innerHTML = "";
        const sectors = Object.keys(curveStage);
        if (sectors.length === 0) {
            setTableEmpty(curveBody, 3, "No curve data yet", "Needs at least two peers per sector with trailing quarterly sales history.");
        } else {
            sectors.forEach(sectorKey => {
                const info = curveStage[sectorKey];
                const label = (appData.sectors && appData.sectors[sectorKey]?.label) || sectorKey.replace(/_/g, " ");
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${escapeHtml(label)}</td>
                    <td>${escapeHtml(info.stage)}</td>
                    <td class="num">${info.median_qoq_growth_pct > 0 ? "+" : ""}${escapeHtml(info.median_qoq_growth_pct)}%</td>
                `;
                curveBody.appendChild(tr);
            });
        }
    }

    // Rotation engine track record table
    const outcomesBody = document.getElementById("rotation-outcomes-table-body");
    if (outcomesBody) {
        outcomesBody.innerHTML = "";
        if (recentOutcomes.length === 0) {
            setTableEmpty(outcomesBody, 3, "No scored decisions yet", "Add/rotate decisions are scored 45+ days after being made.");
        } else {
            recentOutcomes.forEach(e => {
                const win = e.outcome === "Thesis Playing Out";
                const color = win ? "var(--success, #34d399)" : "var(--danger, #f87171)";
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="t-ticker">${escapeHtml(e.ticker)}</td>
                    <td style="color: ${color}; font-weight: 600;">${escapeHtml(e.outcome)}</td>
                    <td class="num">${e.realized_return_pct > 0 ? "+" : ""}${escapeHtml(e.realized_return_pct)}%</td>
                `;
                outcomesBody.appendChild(tr);
            });
        }
    }
}

// Helper: Get list of all stocks across all sectors
function getStockList() {
    let list = [];
    if (!appData || !appData.watchlist) return list;
    Object.keys(appData.watchlist).forEach(sectorKey => {
        appData.watchlist[sectorKey].forEach(s => {
            list.push({ ...s, sectorKey });
        });
    });
    return list;
}


if (typeof module !== 'undefined' && module.exports) {
    module.exports = { formatPotential };
}
