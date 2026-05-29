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

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
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
                // Re-render chart on tab refocus to avoid rendering bugs
                if (appData) renderCharts(appData);
            } else if (targetTab === "sectors") {
                pageTitle.textContent = "Sector Detailed Intelligence";
                pageSubtitle.textContent = "Deep dive sector analysis, announcements history, and watchlists.";
                if (appData) initSectorsTab();
            } else if (targetTab === "stocks") {
                pageTitle.textContent = "Stock Analyst Matrix";
                pageSubtitle.textContent = "Curated list of companies and their policy-related growth drivers.";
                if (appData) renderStocksTable();
            }
        });
    });
}

// Fetch dashboard data
function loadDashboardData() {
    fetch("dashboard_data.json")
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
    
    // Calculate total policy announcements
    let totalAnnouncements = 0;
    Object.values(data.briefing).forEach(items => {
        totalAnnouncements += items.length;
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
            data.briefing[sectorKey].forEach(item => {
                feedItems.push({ ...item, sectorKey: sectorKey });
            });
        });
    } else {
        if (data.briefing[activeSectorFilter]) {
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
        
        el.innerHTML = `
            <div class="feed-item-header">
                <span class="source-badge">${item.source}</span>
                <span class="badge ${badgeClass}">${item.impact} Impact</span>
            </div>
            <a href="${item.link}" class="feed-item-title" target="_blank">${item.title}</a>
            <div class="feed-item-meta">
                <span class="sector-tag">${sectorIcon} ${sectorLabel}</span>
                <span>${item.date}</span>
            </div>
        `;
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
            const rawPct = parseFloat(s.growth_pct.replace('%', ''));
            return { ...s, rawPctValue: rawPct };
        })
        .filter(s => s.rawPctValue >= 28)
        .sort((a,b) => b.rawPctValue - a.rawPctValue);
        
    topPicks.slice(0, 4).forEach(s => {
        const item = document.createElement("div");
        item.className = "highlight-item";
        item.innerHTML = `
            <div class="hl-left">
                <span class="hl-ticker">${s.ticker}</span>
                <span class="hl-name">${s.name}</span>
            </div>
            <div class="hl-right">
                <span class="hl-price">CMP: ₹${s.price}</span>
                <div class="hl-pct">+${s.growth_pct} Target</div>
            </div>
        `;
        container.appendChild(item);
    });
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
        stocks.forEach(s => {
            sum += parseFloat(s.growth_pct.replace('%', ''));
        });
        const avg = stocks.length > 0 ? (sum / stocks.length).toFixed(1) : 0;
        
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
                        <span class="source-badge">${n.source}</span>
                        <span class="badge ${badgeClass}">${n.impact} Impact</span>
                    </div>
                    <a href="${n.link}" class="feed-item-title" target="_blank">${n.title}</a>
                    <span style="font-size:11px; color: var(--text-muted);">${n.date}</span>
                </div>
            `;
        });
    } else {
        newsHtml = `<p style="color:var(--text-secondary); font-style:italic;">No recent announcements or policy changes aggregated for this sector.</p>`;
    }
    
    let stocksHtml = "";
    stocks.forEach(s => {
        stocksHtml += `
            <div class="detail-stock-card">
                <div class="dsc-header">
                    <div class="dsc-ticker-group">
                        <h4>${s.name} <span>${s.ticker}</span></h4>
                    </div>
                    <span class="dsc-pot">+${s.growth_pct}</span>
                </div>
                <div class="dsc-metrics">
                    <span>CMP: <strong>₹${s.price}</strong></span>
                    <span>Target: <strong>₹${s.target}</strong></span>
                </div>
                <p class="dsc-catalyst"><strong>Watchlist Catalyst:</strong> ${s.catalyst}</p>
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
function renderStocksTable(filterQuery = "") {
    const tbody = document.getElementById("stocks-table-body");
    tbody.innerHTML = "";
    
    const query = filterQuery.toLowerCase().trim();
    let rowCount = 0;
    
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
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="t-ticker">${s.ticker}</td>
                    <td><strong>${s.name}</strong></td>
                    <td><span class="chip" style="display:inline-block; border-color:transparent; background-color:rgba(255,255,255,0.03);">${sectorLabel}</span></td>
                    <td>₹${s.price}</td>
                    <td>₹${s.target}</td>
                    <td class="t-potential">+${s.growth_pct}</td>
                    <td class="t-catalyst">${s.catalyst}</td>
                `;
                tbody.appendChild(tr);
                rowCount++;
            }
        });
    });
    
    if (rowCount === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 30px; color: var(--text-secondary);">No companies found matching your search.</td></tr>`;
    }
}

// Search Filter Input
function setupStockSearch() {
    const input = document.getElementById("stock-search");
    input.addEventListener("input", (e) => {
        renderStocksTable(e.target.value);
    });
}
