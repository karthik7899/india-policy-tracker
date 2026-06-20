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
            {"ticker": "TATAPOWER", "name": "Tata Power", "price": "432.50", "target": "520.00", "growth_pct": "20.2%", "catalyst": "Massive scaling in solar generation, microgrids, and leading India's EV charging network grid."},
            {"ticker": "SUZLON", "name": "Suzlon Energy", "price": "50.15", "target": "68.00", "growth_pct": "35.6%", "catalyst": "Turnaround story, completely debt-free, dominating wind turbine supply with a record order book."},
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
        ]
    }
};

// Global App State
let appData = null;
let activeSectorFilter = "all";
let growthChartInstance = null;

// Helper: Sanitize text using safe DOM manipulation
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Helper: Format YoY growth with contextual icon/color
// Helper to prevent XSS
function escapeHTML(str) {
    if (typeof str !== "string") return str;
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function formatGrowthBadge(growthStr, style = 'inline') {
    if (!growthStr || growthStr === "N/A") return `<span class="badge badge-neutral">N/A</span>`;

    let isPositive = false;
    let text = growthStr;

    // Check if it starts with + or is a positive number
    if (typeof growthStr === 'string') {
        if (growthStr.startsWith('+')) isPositive = true;
        else if (growthStr.startsWith('-')) isPositive = false;
        else if (parseFloat(growthStr) > 0) isPositive = true;
    } else if (typeof growthStr === 'number') {
        isPositive = growthStr > 0;
    }

    const val = parseFloat(growthStr.toString().replace('%', ''));
    if (isNaN(val)) return style === 'table' ? `<span style="color: var(--text-muted);">—</span>` : '';
    
    const absValStr = Math.abs(val).toFixed(1) + '%';
    if (val > 0) {
        if (style === 'table') return `<span style="font-weight: 700; color: #34d399;">🔥 +${absValStr} YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">🔥 +${absValStr} YoY</span>`;
    } else if (val < 0) {
        if (style === 'table') return `<span style="font-weight: 700; color: #f87171;">📉 -${absValStr} YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">📉 -${absValStr} YoY</span>`;
    } else {
        if (style === 'table') return `<span style="font-weight: 700; color: #cbd5e1;">0.0% YoY</span>`;
        return `<span style="font-size: 9px; padding: 2px 6px; background: rgba(203, 213, 225, 0.12); color: #cbd5e1; border: 1px solid rgba(203, 213, 225, 0.3); border-radius: 4px; display: inline-block; font-weight: 600;">0.0% YoY</span>`;
    }
}

// Helper: Escape HTML to prevent XSS
function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Helper: Format potential growth with proper sign and color
function formatPotential(pctStr) {
    if ((!pctStr && pctStr !== 0) || pctStr === "N/A") return `<span class="badge badge-neutral">N/A</span>`;

    let isPositive = false;
    if (typeof pctStr === 'string' && pctStr.startsWith('+')) {
        isPositive = true;
    } else if (typeof pctStr === 'number' && pctStr > 0) {
        isPositive = true;
    }

    const val = parseFloat(String(pctStr).replace('%', '').replace('+', ''));
    if (isNaN(val)) return pctStr;
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
    const countStr = count ? ` (${count})` : '';
    return `<span class="badge badge-rating">${rating}${countStr}</span>`;
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupTabToggles();
    loadDashboardData();
    setupStockSearch();
});

// Tab Toggling Logic
function setupTabToggles() {
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            navButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(t => t.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(`tab-${targetTab}`).classList.add("active");
            
            // Adjust title text based on tab
            const pageTitle = document.getElementById("page-title");
            const pageSubtitle = document.getElementById("page-subtitle");
            
            if (targetTab === "dashboard") {
                pageTitle.textContent = "Policy & Sector Overview";
                pageSubtitle.textContent = "Real-time mapping of government policies to market indicators.";
                if (appData) renderCharts(appData);
            } else if (targetTab === "sectors") {
                pageTitle.textContent = "Government Policy Logs";
                pageSubtitle.textContent = "Deep dive sector analysis, announcements history, and watchlists.";
                if (appData) initSectorsTab();
            } else if (targetTab === "agreements") {
                pageTitle.textContent = "Corporate News & Agreements";
                pageSubtitle.textContent = "Scanned news alerts regarding joint ventures, strategic partnerships, and MoUs.";
                if (appData) renderAgreementsTable();
            } else if (targetTab === "launches") {
                pageTitle.textContent = "Product Launches";
                pageSubtitle.textContent = "Real-time alerts on product launches, new manufacturing capacities, and rollouts.";
                if (appData) renderLaunchesTable();
            } else if (targetTab === "institutional") {
                pageTitle.textContent = "Institutional Activity";
                pageSubtitle.textContent = "Scheme Information Documents (SIDs) filed by mutual funds and institutional block deal news.";
                if (appData) renderInstitutionalFlows();
            } else if (targetTab === "graham") {
                pageTitle.textContent = "Margin of Safety (Deep Value)";
                pageSubtitle.textContent = "Defensive investor criteria checks and growth intrinsic value calculations.";
                if (appData) renderGrahamTable();
            } else if (targetTab === "buffett") {
                pageTitle.textContent = "Owner Earnings & Moats";
                pageSubtitle.textContent = "Owner earnings, economic moats, and retained value creation metrics.";
                if (appData) renderBuffettTable();
            } else if (targetTab === "caution") {
                pageTitle.textContent = "Risk Alerts & Valuation Warnings (Caution List)";
                pageSubtitle.textContent = "Stocks that are not meeting standard value/growth investing filters or showing warning signs.";
                if (appData) renderCautionTable();
            } else if (targetTab === "stocks") {
                pageTitle.textContent = "Integrated Stocks Screener";
                pageSubtitle.textContent = "Curated list of companies and their policy-related growth drivers.";
                if (appData) renderStocksTable();
            }
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
            console.log("Live dashboard data loaded successfully.");
            appData = data;
            initDashboard(data);
        })
        .catch(err => {
            console.warn("Failed to load live data, fallback to static mock seed database:", err);
            appData = MOCK_DATA;
            initDashboard(MOCK_DATA);
        });
}

// Dashboard Page Setup
function initDashboard(data) {
    document.getElementById("update-time").textContent = `Last Refreshed: ${data.last_updated}`;
    
    // Hide loading overlay
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.style.display = "none";
    
    // Calculate total policy announcements
    let totalAnnouncements = 0;
    Object.keys(data.briefing).forEach(key => {
        if (key !== "emerging_players" && Array.isArray(data.briefing[key])) {
            totalAnnouncements += data.briefing[key].length;
        }
    });
    document.getElementById("active-signals-val").textContent = totalAnnouncements;
    
    // Calculate total stocks
    let totalStocks = 0;
    Object.values(data.watchlist).forEach(items => {
        totalStocks += items.length;
    });
    document.getElementById("total-stocks-val").textContent = totalStocks;

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
        const chips = document.querySelectorAll(".chip");
        chips.forEach(chip => {
            if (chip.getAttribute("data-sector") === activeSectorFilter) {
                chip.classList.add("active");
            } else {
                chip.classList.remove("active");
            }
        });
        renderPolicyFeed(data);
    });
}

// Render Sector Filter Chips
function renderSectorChips(data) {
    const container = document.getElementById("sector-chips-container");
    container.innerHTML = "";
    
    // Create an 'All' chip
    const allChip = document.createElement("div");
    allChip.className = "chip active";
    allChip.setAttribute("data-sector", "all");
    allChip.innerHTML = `🌐 All Sectors`;
    allChip.addEventListener("click", () => handleChipClick("all", allChip));
    container.appendChild(allChip);
    
    // Create individual chips
    Object.keys(data.sectors).forEach(key => {
        const sect = data.sectors[key];
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.setAttribute("data-sector", key);
        chip.innerHTML = `${sect.icon} ${sect.label}`;
        chip.addEventListener("click", () => handleChipClick(key, chip));
        container.appendChild(chip);
    });
}

function handleChipClick(sectorKey, chipElement) {
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    chipElement.classList.add("active");
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
    
    if (activeSectorFilter === "all") {
        Object.keys(data.briefing).forEach(sectorKey => {
            if (sectorKey !== "emerging_players" && Array.isArray(data.briefing[sectorKey])) {
                data.briefing[sectorKey].forEach(item => {
                    feedItems.push({ ...item, sectorKey: sectorKey });
                });
            }
        });
    } else {
        if (activeSectorFilter !== "emerging_players" && data.briefing[activeSectorFilter]) {
            data.briefing[activeSectorFilter].forEach(item => {
                feedItems.push({ ...item, sectorKey: activeSectorFilter });
            });
        }
    }
    
    if (feedItems.length === 0) {
        container.innerHTML = `<div class="feed-item"><p style="color: var(--text-secondary); text-align: center; padding: 20px 0;">No policy bulletins tracked for this sector in the recent cycle.</p></div>`;
        return;
    }
    
    // Sort items by date descending (simple sorting)
    feedItems.sort((a,b) => new Date(b.date) - new Date(a.date));
    
    feedItems.forEach(item => {
        const el = document.createElement("div");
        el.className = "feed-item";
        
        const badgeClass = item.impact === "Positive" ? "badge-positive" : (item.impact === "Negative" ? "badge-negative" : "badge-neutral");
        const sectorLabel = data.sectors[item.sectorKey].label;
        const sectorIcon = data.sectors[item.sectorKey].icon;
        
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
        sourceBadge.textContent = item.source;

        const impactBadge = document.createElement("span");
        impactBadge.className = `badge ${badgeClass}`;
        impactBadge.textContent = `${item.impact} Impact`;

        headerDiv.appendChild(sourceBadge);
        headerDiv.appendChild(impactBadge);

        const titleLink = document.createElement("a");
        titleLink.href = safeLink;
        titleLink.className = "feed-item-title";
        titleLink.target = "_blank";
        titleLink.textContent = item.title;

        const metaDiv = document.createElement("div");
        metaDiv.className = "feed-item-meta";

        const sectorTag = document.createElement("span");
        sectorTag.className = "sector-tag";
        sectorTag.textContent = `${sectorIcon} ${sectorLabel}`;

        const dateSpan = document.createElement("span");
        dateSpan.textContent = item.date;

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
        
    topPicks.slice(0, 6).forEach(s => {
        const item = document.createElement("div");
        item.className = "highlight-item";
        item.innerHTML = `
            <div class="hl-left">
                <span class="hl-ticker">${escapeHTML(s.ticker)}</span>
                <span class="hl-name">${escapeHTML(s.name)}</span>
            </div>
            <div class="hl-right">
                <span class="hl-price">CMP: ₹${s.price}</span>
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
    
    const emerging = data.briefing.emerging_players || {};
    let hasPlayers = false;
    
    Object.keys(emerging).forEach(sectorKey => {
        const sectorLabel = data.sectors[sectorKey]?.label || sectorKey;
        const sectorIcon = data.sectors[sectorKey]?.icon || "🏢";
        const players = emerging[sectorKey];
        
        players.forEach(p => {
            hasPlayers = true;
            
            let displayName = "";
            let tickerBadge = "";
            let statusText = "Analyzing Listing...";
            let statusStyle = "color: #fbbf24; font-size: 9px; font-weight: 600;";
            let reasonText = "";
            
            if (p && typeof p === 'object') {
                displayName = escapeHTML(p.name) || "Unknown Company";
                const ticker = escapeHTML(p.ticker);
                tickerBadge = ticker ? `<span class="hl-ticker" style="margin-left: 6px; font-size: 10px; background: rgba(59, 130, 246, 0.1); color: var(--primary); padding: 1px 4px; border-radius: 3px;">${ticker}</span>` : '';
                statusText = p.status || "Scanned";
                reasonText = p.reason ? `<div style="font-size: 10px; color: #64748b; margin-top: 4px; max-width: 220px; line-height: 1.2;">${escapeHTML(p.reason)}</div>` : '';
                
                // Color status dynamically
                if (statusText === 'Watchlisted') {
                    statusStyle = 'background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 700;';
                } else if (statusText === 'Pipeline') {
                    statusStyle = 'background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 700;';
                } else if (statusText === 'Growth Divergence') {
                    statusStyle = 'background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 700;';
                } else {
                    statusStyle = 'background: rgba(255, 255, 255, 0.05); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.1); padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 700;';
                }
            } else {
                displayName = p || "Unknown Company";
            }
            
            const item = document.createElement("div");
            item.className = "highlight-item";
            item.style.display = "flex";
            item.style.justifyContent = "space-between";
            item.style.alignItems = "flex-start";
            item.style.padding = "12px 16px";
            
            item.innerHTML = `
                <div class="hl-left" style="display: flex; flex-direction: column; gap: 2px;">
                    <div style="display: flex; align-items: center;">
                        <span class="hl-ticker" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 8px; padding: 2px 4px; border-radius: 4px; font-weight: 800; width: fit-content;">RADAR</span>
                        ${tickerBadge}
                    </div>
                    <span class="hl-name" style="color: #f8fafc; font-weight: 500; font-size: 13px; margin-top: 4px;">${escapeHTML(displayName)}</span>
                    ${reasonText}
                </div>
                <div class="hl-right" style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                    <span class="hl-price" style="font-size: 11px; color: #94a3b8;">${sectorIcon} ${sectorLabel}</span>
                    <div style="${statusStyle}">${statusText}</div>
                </div>
            `;
            container.appendChild(item);
        });
    });
    
    if (!hasPlayers) {
        container.innerHTML = `<div style="color: var(--text-muted); font-size: 12px; font-style: italic; text-align: center; padding: 15px 0;">No new competitors detected in recent feed. Watchlist stable.</div>`;
    }
}

// Render Comparison Chart using Chart.js
function renderCharts(data) {
    const ctx = document.getElementById("growthChart").getContext("2d");
    
    // Calculate average growth potential per sector
    const labels = [];
    const averages = [];
    const colors = [
        "rgba(59, 130, 246, 0.6)",   // Blue
        "rgba(16, 185, 129, 0.6)",  // Green
        "rgba(139, 92, 246, 0.6)",  // Purple
        "rgba(245, 158, 11, 0.6)",   // Orange
        "rgba(239, 68, 68, 0.6)",    // Red
        "rgba(6, 182, 212, 0.6)",    // Cyan
        "rgba(236, 72, 153, 0.6)",   // Pink
        "rgba(107, 114, 128, 0.6)"   // Grey
    ];
    const borderColors = colors.map(c => c.replace("0.6", "1"));
    
    Object.keys(data.watchlist).forEach(sectorKey => {
        const sectorLabel = data.sectors[sectorKey].label;
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
    
    growthChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Avg Watchlist Growth Target (%)',
                data: averages,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1f2937',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: '#374151',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) { return value + '%'; }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 10
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
        btn.className = `sector-nav-item ${idx === 0 ? 'active' : ''}`;
        btn.innerHTML = `<span>${sect.icon}</span> ${sect.label}`;
        btn.addEventListener("click", () => {
            document.querySelectorAll(".sector-nav-item").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
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
                        <span class="source-badge">${escapeHTML(n.source)}</span>
                        <span class="badge ${badgeClass}">${n.impact} Impact</span>
                    </div>
                    <a href="${n.link}" class="feed-item-title" target="_blank">${escapeHTML(n.title)}</a>
                    <span style="font-size:11px; color: var(--text-muted);">${n.date}</span>
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
            const peHtml = sc.pe_ratio ? `<span class="sc-chip" title="Price to Earnings">P/E: <strong>${sc.pe_ratio}</strong>${sc.industry_pe ? ` <small style="opacity:0.6">vs Ind:${sc.industry_pe}</small>` : ''}</span>` : '';
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
            const qtrLabel = sc.latest_quarter ? `<small style="color: #f59e0b; font-size: 9px; font-weight: 700; text-transform: uppercase;">(${sc.latest_quarter})</small>` : '';
            
            screenerHtml = `
                <div class="dsc-fundamentals" style="margin-top: 12px; padding: 12px; background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;">
                    <!-- Ratios & Shareholding Sub-Section -->
                    <div style="margin-bottom: 8px;">
                        <div style="font-size: 8.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 6px; display: flex; justify-content: space-between;">
                            <span>📊 Filed Ratios & Holdings</span>
                            <span style="font-size: 7.5px; opacity: 0.6;">Source: Screener.in</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                            ${mcapHtml}${peHtml}${roceHtml}${roeHtml}${promoterHtml}${fiiHtml}${diiHtml}
                        </div>
                    </div>
                    <!-- Quarterly Earnings Sub-Section -->
                    <div>
                        <div style="font-size: 8.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 6px; display: flex; gap: 6px; align-items: center;">
                            <span>📈 Quarterly Performance</span>
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

        stocksHtml += `
            <div class="detail-stock-card">
                <div class="dsc-header">
                    <div class="dsc-ticker-group">
                        <h4 style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                            ${escapeHTML(s.name)}
                            <span style="background-color: rgba(59, 130, 246, 0.1); color: var(--primary); padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px;">${escapeHTML(s.ticker)}</span>
                            ${analystBadge}
                            ${growthBadge}
                            ${earningsBadge}
                        </h4>
                    </div>
                    <span class="dsc-pot">${formatPotential(s.growth_pct)}</span>
                </div>
                <div class="dsc-metrics" style="margin-top: 12px;">
                    <span>CMP: <strong>₹${s.price}</strong></span>
                    ${analystDisplay}
                    <span>Analysts: <strong>${s.analyst_count || '—'}</strong></span>
                </div>
                <p class="dsc-catalyst"><strong>Watchlist Catalyst:</strong> ${s.catalyst}</p>
                ${screenerHtml}
            </div>
        `;
    });
    
    container.innerHTML = `
        <div class="detail-header">
            <div class="detail-header-top">
                <span>${sect.icon}</span>
                <h3>${sect.label}</h3>
            </div>
            <p>${sect.desc}</p>
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
                s.ticker.toLowerCase().includes(query) ||
                s.name.toLowerCase().includes(query) ||
                s.catalyst.toLowerCase().includes(query) ||
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
            valAlertsHtml = sc.valuation_alerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 8px;">${a}</span>`).join('');
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
                diiBadge = `<span class="badge-success-alert" style="margin-right: 4px; font-size: 9px;">🔥 MFs +${diiChg}%</span>`;
            } else if (diiChg < 0) {
                diiBadge = `<span class="badge-danger-alert" style="margin-right: 4px; font-size: 9px;">📉 MFs ${diiChg}%</span>`;
            }
            if (fiiChg > 0) {
                fiiBadge = `<span class="badge-success-alert" style="font-size: 9px;">✈️ FIIs +${fiiChg}%</span>`;
            } else if (fiiChg < 0) {
                fiiBadge = `<span class="badge-danger-alert" style="font-size: 9px;">📉 FIIs ${fiiChg}%</span>`;
            }
            instChangeHtml = (diiBadge || fiiBadge) ? `${diiBadge}${fiiBadge}` : '<span style="color: var(--text-muted);">0.0%</span>';
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHTML(s.ticker)}</td>
            <td><strong>${escapeHTML(s.name)}</strong></td>
            <td><span class="chip" style="display:inline-block; border-color:transparent; background-color:rgba(255,255,255,0.03);">${sectorLabel}</span></td>
            <td>₹${s.price}</td>
            <td><strong>${peVal}</strong></td>
            <td>${qoqSalesVal}</td>
            <td><strong>${roceVal}</strong></td>
            <td><strong>${roeVal}</strong></td>
            <td>${capexVal}</td>
            <td><strong>${oeVal}</strong></td>
            <td><strong>${grahamVal}</strong></td>
            <td>${s.target ? `₹${s.target}` : '<span style="color: var(--text-muted);">—</span>'}</td>
            <td class="t-potential">${formatPotential(s.growth_pct)}</td>
            <td>${formatGrowthBadge(s.revenue_growth, 'table')}</td>
            <td>${instChangeHtml}</td>
            <td style="max-width: 150px; white-space: normal;">${valAlertsHtml}</td>
            <td>${formatAnalystBadge(s)}</td>
            <td style="max-width: 280px; white-space: normal; font-size: 11px;">${escapeHTML(s.catalyst)}</td>
        `;
        tbody.appendChild(tr);
    });

    if (allStocksList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="18" style="text-align: center; padding: 30px; color: var(--text-secondary);">No companies found matching your search.</td></tr>`;
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
        header.addEventListener("click", () => {
            const column = header.getAttribute("data-sort");
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'desc'; // Default to desc for new column
            }
            renderStocksTable(document.getElementById("stock-search").value);
        });
    });
}

function updateSortHeaders() {
    const headers = document.querySelectorAll("th.sortable");
    headers.forEach(header => {
        header.classList.remove("asc", "desc");
        if (header.getAttribute("data-sort") === currentSortColumn) {
            header.classList.add(currentSortDirection);
        }
    });
}

// Theme Toggle Logic
function setupThemeToggle() {
    const toggleBtn = document.getElementById("theme-toggle");
    if (!toggleBtn) return;

    // Check saved theme or system preference
    const savedTheme = localStorage.getItem('bharat-policy-theme');
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;

    if (savedTheme === 'light' || (!savedTheme && prefersLight)) {
        document.documentElement.setAttribute('data-theme', 'light');
    }

    toggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        let newTheme = 'dark';
        if (currentTheme !== 'light') {
            newTheme = 'light';
        }
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('bharat-policy-theme', newTheme);
    });
}

// Render Corporate Agreements List
function renderAgreementsTable() {
    const tbody = document.getElementById("agreements-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    const agreements = appData.briefing.corporate_agreements || [];
    if (agreements.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 20px; color: var(--text-secondary);">No corporate agreements tracked in this cycle.</td></tr>`;
        return;
    }
    
    agreements.forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span class="source-badge">${escapeHTML(a.source)}</span></td>
            <td><strong>${escapeHTML(a.title)}</strong></td>
            <td>${a.date}</td>
            <td><a href="${a.link}" class="badge-rating" style="text-decoration:none;" target="_blank">View Article</a></td>
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
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 20px; color: var(--text-secondary);">No product launches tracked in this cycle.</td></tr>`;
        return;
    }
    
    launches.forEach(l => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span class="source-badge">${escapeHTML(l.source)}</span></td>
            <td><strong>${escapeHTML(l.title)}</strong></td>
            <td>${l.date}</td>
            <td><a href="${l.link}" class="badge-rating" style="text-decoration:none;" target="_blank">View Article</a></td>
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
            sebiBody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 20px; color: var(--text-secondary);">No thematic fund filings scanned.</td></tr>`;
        } else {
            filings.forEach(f => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${escapeHTML(f.fund_name)}</strong></td>
                    <td><span class="chip" style="display:inline-block; border-color:transparent; background-color:rgba(255,255,255,0.03);">${f.theme}</span></td>
                    <td><span class="badge-success-alert">${f.status}</span></td>
                    <td>${f.date}</td>
                    <td><a href="${f.link}" class="badge-rating" style="text-decoration:none;" target="_blank">View Document</a></td>
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
            instBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 20px; color: var(--text-secondary);">No institutional block deals scanned.</td></tr>`;
        } else {
            activity.forEach(act => {
                const actionBadge = act.action === "Buy" ? 
                    `<span class="badge-success-alert">BUY</span>` : 
                    `<span class="badge-danger-alert">SELL</span>`;
                    
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><span class="source-badge">${escapeHTML(act.source)}</span></td>
                    <td><strong>${escapeHTML(act.buyer)}</strong></td>
                    <td>${actionBadge}</td>
                    <td><strong>${escapeHTML(act.company)}</strong></td>
                    <td>${escapeHTML(act.details)}</td>
                    <td>${act.date}</td>
                    <td><a href="${act.link}" class="badge-rating" style="text-decoration:none;" target="_blank">View</a></td>
                `;
                instBody.appendChild(tr);
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
        const isDefensiveBadge = !hasGrahamFailures ? 
            `<span class="badge-success-alert">PASS</span>` : 
            `<span class="badge-danger-alert">FAIL</span>`;
            
        let alertBadges = '';
        const grahamAlerts = alerts.filter(a => a.includes("Current Ratio") || a.includes("Debt Limit") || a.includes("P/E Screen") || a.includes("Dividend"));
        if (grahamAlerts.length > 0) {
            alertBadges = grahamAlerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 9px;">${a}</span>`).join('');
        } else {
            alertBadges = `<span style="color: var(--text-muted);">None</span>`;
        }
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHTML(s.ticker)}</td>
            <td><strong>${escapeHTML(s.name)}</strong></td>
            <td>₹${s.price}</td>
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
        
        const passedRetained = sc.retained_earnings_ratio >= 1.0 ? 
            `<span class="badge-success-alert">PASS (>= 1.0)</span>` : 
            `<span class="badge-danger-alert">FAIL (< 1.0)</span>`;
            
        const moat = sc.moat_status || 'Weak/None';
        let moatBadge = '';
        if (moat.includes("Strong")) {
            moatBadge = `<span class="badge-success-alert">${moat}</span>`;
        } else if (moat.includes("Medium")) {
            moatBadge = `<span class="badge-warning-alert">${moat}</span>`;
        } else {
            moatBadge = `<span class="badge-danger-alert">${moat}</span>`;
        }
        
        const alerts = sc.valuation_alerts || [];
        const buffettAlerts = alerts.filter(a => a.includes("Retained Earnings") || a.includes("Moat"));
        let alertBadges = '';
        if (buffettAlerts.length > 0) {
            alertBadges = buffettAlerts.map(a => `<span class="badge-danger-alert" style="margin-right: 4px; margin-bottom: 4px; font-size: 9px;">${a}</span>`).join('');
        } else {
            alertBadges = `<span style="color: var(--text-muted);">None</span>`;
        }
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="t-ticker">${escapeHTML(s.ticker)}</td>
            <td><strong>${escapeHTML(s.name)}</strong></td>
            <td>₹${s.price}</td>
            <td><strong>${oe}</strong></td>
            <td><strong>${retainedRatio}</strong></td>
            <td>${passedRetained}</td>
            <td>${moatBadge}</td>
            <td style="max-width: 250px; white-space: normal;">${alertBadges}</td>
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
                return `<span class="${badgeClass}" style="margin-right: 6px; margin-bottom: 6px; display: inline-block; font-size: 9px;">${a}</span>`;
            }).join('');
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="t-ticker">${escapeHTML(s.ticker)}</td>
                <td><strong>${escapeHTML(s.name)}</strong></td>
                <td><span class="chip" style="display:inline-block; border-color:transparent; background-color:rgba(255,255,255,0.03);">${sectorLabel}</span></td>
                <td>₹${s.price}</td>
                <td style="max-width: 450px; white-space: normal;">${alertBadges}</td>
            `;
            tbody.appendChild(tr);
            cautionCount++;
        }
    });
    
    if (cautionCount === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-secondary); font-style: italic;">All watchlist companies have passed core value and growth checks. No caution flags.</td></tr>`;
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
