# Bloomberg for institutional managers of Indian listed equities (status as of October 2026)

Tags used in this file: **[Vendor]** = Bloomberg's own press release, product page or brochure (a claim, not independently checked). **[Trade press]** = industry media, which often republishes vendor releases. **[3rd-party est.]** = pricing or review sites, not official. **[Anecdotal]** = forums or Q&A. **[Dated YYYY]** = older than 2025. Inferences are kept in the "Inferences" subsections only.

## 1. PORT / PORT Enterprise: analytics, attribution, ex-ante risk (India model coverage), VaR, stress tests, liquidity, compliance, benchmarks, reporting

### Takeaway
PORT is a Terminal function. PORT Enterprise is the separately licensed premium tier, with 600+ clients in Dec 2024 and 750+ in 2025 (vendor figures). Between them they provide holdings-based performance attribution, ex-ante risk on Bloomberg's MAC3 factor models, VaR by three methods, four families of stress scenario, liquidity and transaction-cost analytics, batch reporting, AI-written attribution commentary (2025) and delivery to Snowflake. Bloomberg's documentation lists a **dedicated India local equity model** among 13 local MAC3 equity models, alongside a global model that covers emerging markets. I could not confirm details of the India model's factors, whether attribution is Brinson-style, PORT-level compliance, or how NSE/BSE/MSCI India benchmarks are licensed.

### Cited Findings
**Product tiers, scale and delivery**
- Bloomberg calls PORT Enterprise its "premium" portfolio and risk analytics product. In 2025 (September 2025 in one search extract, August 2025 in another) it launched **AI Portfolio Commentary**, which combines a portfolio's attribution results with news coverage, including Bloomberg News, to generate explanations of what drove returns. It covers equity and fixed income portfolios. The release states PORT Enterprise has **750+ clients**. [Vendor] — [Bloomberg press release](https://www.bloomberg.com/company/press/bloomberg-advances-portfolio-analytics-with-launch-of-ai-portfolio-commentary-in-port-enterprise); [Finadium](https://finadium.com/?p=154598); [Barchart reprint](https://www.barchart.com/story/news/34977268/bloomberg-advances-portfolio-analytics-with-launch-of-ai-portfolio-commentary-in-port-enterprise)
- Features that Bloomberg describes as Enterprise-level: access to the MAC3 multi-asset factor risk models (tracking-error volatility, VaR, scenario analysis), MAC HPA hybrid performance attribution (fixed income), and centrally administered batch reporting that runs outside the Terminal. Bloomberg also markets PORT Enterprise for top-down analysis of allocation and selection decisions. [Vendor] — [Bloomberg press release](https://www.bloomberg.com/company/press/bloomberg-advances-portfolio-analytics-with-launch-of-ai-portfolio-commentary-in-port-enterprise); [Bloomberg Pro Tips: attribution reporting with PORT Enterprise](https://www.bloomberg.com/professional/insights/markets/bloomberg-pro-tips-simplify-attribution-reporting-with-port-enterprise/)
- **4 Dec 2024:** PORT Enterprise datasets can be pushed into a client's Snowflake warehouse during the routine overnight reporting run, through Data License Plus (DL+). Clients can then join them with Bloomberg pricing, reference and ESG data. The release cited **"more than 600"** PORT Enterprise clients. Josef Kirkland, Global Head of Portfolio & Risk Analytics, is quoted. [Vendor] — [PR Newswire](https://www.prnewswire.com/news-releases/bloomberg-announces-port-enterprise-data-delivery-to-snowflake-with-data-license-plus-dl-302321571.html); [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-announces-port-enterprise-data-delivery-to-snowflake-with-data-license-plus-dl)
- **Base PORT inside the Terminal:** a university-hosted PORT help guide lists historical performance attribution, ex-ante tracking error, scenario analysis and portfolio optimisation. It also describes a "Liquidity Risk" sub-tab with four views, including expected transaction costs from Bloomberg's proprietary transaction-cost model. [Dated c.2015] — [GMU PORT guide](http://somfin.gmu.edu/courses/fnan311/PORT_guide.pdf)
- A pricing site lists "portfolio and risk analytics" among the inclusions of a single Terminal, without saying which PORT tier. [3rd-party est.] — [CostBench](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/)

**Risk models and India coverage**
- The MAC3 equity suite consists of one **global equity model** and **13 local equity models**: Asia Pacific, Australia, Canada, China A-shares, Europe, EMEA, **India**, Japan, Korea, Latin America, South Africa, UK and US.
  - The global model uses one common set of global factors, and its estimation universe spans developed and emerging markets.
  - Each local model is estimated only on stocks from its own region.
  - Many MAC3 equity models add "satellite" factors for region-specific risks.
  - Bloomberg says single-country models use local style and industry factors to reflect domestic market dynamics.
  - [Vendor; the insight page was reported as about 900 days old, i.e. c.2024] — [Bloomberg insight: satellite factors in MAC3 equity models](https://www.bloomberg.com/professional/insights/data/the-benefits-and-impact-of-including-satellite-factors-in-mac3-equity-models/); [MAC3 product page](https://professional.bloomberg.com/products/risk/mac3)
- **2 Apr 2026:** MAC3 was extended into private markets: private equity, private credit, real estate, infrastructure, hedge funds and liquid alternatives.
  - The private-fund model uses dedicated private-asset factors and Bloomberg data on about 50,000 private funds.
  - MAC3 now has **3,000+ risk factors** and **six forecast horizons**, from a responsive daily model to a stable long-term model.
  - **800+ clients** use MAC3 worldwide.
  - Jose Menchero, Head of Portfolio Analytics Research, is quoted.
  - [Vendor; trade press reprints are consistent] — [PR Newswire](https://www.prnewswire.com/news-releases/bloomberg-expands-mac3-risk-models-for-enhanced-portfolio-and-risk-forecasting-across-public-and-private-investments-302732596.html); [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-expands-mac3-risk-models-for-enhanced-portfolio-and-risk-forecasting-across-public-and-private-investments/); [Finadium](https://finadium.com/bloomberg-adds-alternative-assets-to-mac3-for-risk-forecasting/); [A-Team Insight](https://a-teaminsight.com/briefs/bloomberg-expands-mac3-risk-models-for-enhanced-portfolio-and-risk-forecasting-across-public-and-private-investments/)
- Bloomberg research traced the April 2025 tariff sell-off through factor returns using the MAC3 Global and US models. It standardised cumulative five-day factor returns by the one-week volatility forecast. India was not covered. [Vendor research] — [Bloomberg insight: modeling tariffs](https://www.bloomberg.com/professional/insights/markets/modeling-the-impact-of-tariffs-on-the-global-stock-market/)
- A Bloomberg risk article on policy shocks discusses India's tariff exposure. It notes that pharmaceuticals and electronics, about 30% of India's exports to the US by value, are exempt from the 50% US tariff, and that large banks such as ICICI, SBI and HDFC are cushioned by diversification. This is market commentary, not published output from the India model. — [Bloomberg insight: policy shocks](https://www.bloomberg.com/professional/insights/risk/building-next-level-risk-capabilities-in-an-age-of-policy-shocks/)

**VaR, scenarios, liquidity**
- VaR is built on Bloomberg's multi-factor risk models and supports **historical simulation, parametric and Monte Carlo** methods. The Scenarios function stress-tests portfolios on historical and hypothetical scenarios. PORT Enterprise lists **four scenario types: factor-based, full-valuation, macroeconomic and climate**. [Vendor] — [Bloomberg Portfolio & Risk Analytics page](https://professional.bloomberg.com/products/bloomberg-terminal/portfolio-analytics/); [Bloomberg webinar: liquidity, cashflow, VaR, TE, scenarios](https://www.bloomberg.com/professional/insights/webinar/portfolio-liquidity-cashflow-var-tracking-error-and-scenario-analysis/)
- **Bloomberg Liquidity Assessment (LQA):**
  - It estimates liquidation cost and horizon per position, under current and stressed conditions.
  - Scenarios are defined on four parameters: redemption amount, daily available volume, price volatility and bid-ask spread. They can be calibrated to historical events, hypothetical ones, or both.
  - Outputs are percentile-based.
  - It covers 4.2m+ securities, including equities and ETFs.
  - Recent enhancements include a predefined "Tariff 2025" stress scenario and improved SEC Rule 22e-4 classification for emerging markets.
  - The brochures surfaced are built around ESMA and Japanese (JFSA/JITA) liquidity rules. None was SEBI-specific.
  - [Vendor] — [ESMA liquidity stress-testing brochure](https://data.bloomberglp.com/professional/sites/10/ESMA-Liquidity-Stress-Testing-Brochure.pdf); [JFSA/JITA brochure](https://assets.bbhub.io/professional/sites/10/JFSA-JITA-Liquidity-Guidelines-Brochure.pdf)
- Bloomberg won Risk.net's "Liquidity risk solution of the year" and "Market liquidity risk product of the year" (Risk Markets Technology Awards 2022). [Independent awards based on vendor submissions; Dated 2022] — [Risk.net](https://www.risk.net/awards/7879741/liquidity-risk-solution-of-the-year-bloomberg); [Risk.net](https://www.risk.net/awards/7962728/market-liquidity-risk-product-of-the-year-bloomberg); [Bloomberg](https://www.bloomberg.com/professional/insights/markets/market-liquidity-risk-product-of-the-year-bloomberg-wins-risk-markets-technology-awards-2022/)

**Benchmarks / Indian indices**
- A search for a Bloomberg India large/mid-cap equity benchmark found no such product. It surfaced Nasdaq India and NSE indices, and Bloomberg regional indices such as Asia Developed Markets Large & Mid Cap and World Large & Mid Cap, which cover the top 85% of market cap. — [Bloomberg Asia DM Large & Mid Cap](https://www.bloomberg.com/professional/products/indices/quote/asiadt:ind); [Bloomberg World Large & Mid Cap](https://professional.content.cirrus.bloomberg.com/professional2023/products/indices/quote/worldt:ind); [Nasdaq India Large Mid Cap](https://indexes.nasdaq.com/Index/Overview/NQINLM)
- ETF data pages describe a **"Bloomberg India MVP Index"**. It selects Indian large- and mid-caps with a Bloomberg Intelligence factor model that screens on momentum, value, volatility and profitability, keeping roughly the top 15% of the eligible universe. The pages say an Invesco India ETF tracks it. [3rd-party pages; not checked against Bloomberg or Invesco methodology] — [MarketChameleon](https://marketchameleon.com/Overview/IMVP/ETFProfile/); [finanzen.at](https://www.finanzen.at/etf/daten-gebuehr/invesco-india-etf-us46137r1095)
- For foreign investors in fixed income (adjacent to this topic): Bloomberg announced that India's FAR bonds would be included in the Bloomberg EM Local Currency Government Index. — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-announces-india-far-bonds-inclusion-in-the-bloomberg-emerging-market-em-local-currency-government-index)

### Inferences
- **Capability checklist for comparing against a self-built tracker.** Bloomberg's analytics stack offers:
  - (a) ex-ante factor risk on an India-only local model, plus a global model for foreign portfolio investors (FPIs) holding India inside EM or global books;
  - (b) VaR by three methods;
  - (c) factor, full-valuation, macro and climate scenarios;
  - (d) position-level liquidation cost and time under stressed volume, volatility and spread;
  - (e) attribution with AI-generated narrative;
  - (f) batch reporting and delivery into a data warehouse.
  
  To replicate (a) a tracker would need, at minimum: clean daily total returns adjusted for corporate actions, an industry classification, style-factor construction, covariance and specific-risk estimation, and backtesting. That is the hardest piece to build. Items (b) to (d) follow from it plus NSE/BSE volume and spread data.
- The India local model matters most for India-only mandates (domestic mutual funds, PMS, AIFs). FPIs with India inside EM books would more likely use the global or Asia Pacific model.
- Client counts grew from 600+ (Dec 2024) to 750+ (2025) for PORT Enterprise and 800+ (2026) for MAC3. That points to growth in the premium tier, but none of these figures is broken down for India.
- Whether PORT can show Nifty, BSE or MSCI India constituent weights probably depends on separate licences with the index vendors, which is common industry practice. A manager's usable benchmark set may therefore depend on licences held rather than on PORT itself. This is unconfirmed.

### Gaps
- **Method caveat (applies to every section).** Direct page fetches failed. The session's egress proxy refused CONNECT with HTTP 403 for www.bloomberg.com, www.fi-desk.com and economictimes.indiatimes.com, and WebFetch could not resolve DNS. I therefore read no page in full: every finding comes from search-engine extracts of the cited URLs, and where extracts conflicted both versions are given. The per-turn web-search budget ran out before several planned follow-ups, which are marked "not searched" below.
- MAC3 India model internals were not found in any reachable source: number and definitions of style factors, industry scheme (BICS or GICS), estimation-universe cut-offs (e.g. treatment of the SME platforms and of circuit-limited or illiquid stocks), and backtest results.
- Whether attribution is Brinson-Fachler, factor-based, or both for equities; whether returns-based (style) analysis exists; and how currency attribution works for FPIs measuring in USD.
- No evidence of PORT-level compliance or limit monitoring. Compliance appears to sit in AIM's Compliance Manager (Q2).
- Licensing and availability in PORT of NSE Indices (Nifty) and Asia Index (BSE Sensex) constituent data, and of MSCI India.
- No evidence that PORT produces SEBI/AMFI-format reports (monthly portfolio disclosure, risk-o-meter inputs).
- Not searched (budget exhausted): the SEBI/AMFI liquidity stress-test disclosures for small- and mid-cap mutual fund schemes, which are an obvious Indian use case for LQA or PORT liquidity analytics. Also not researched: whether any Indian AMC uses LQA or PORT for them.
- One extract attributed to Bloomberg a claim that PORT/PORT Enterprise are used at "about 15,000 firms". It may be a confusion with AIM's "nearly 15,000 professionals" figure, so treat it as unverified.

## 2. Bloomberg AIM (order and execution management, pre-/post-trade compliance) and its use by Indian asset managers

### Takeaway
AIM is Bloomberg's buy-side order and investment management system. Pre- and post-trade compliance is embedded through Compliance Manager (CMGR), which won a 2025 industry award. Four Indian AMCs have publicly announced AIM adoptions:
- Aditya Birla Sun Life AMC: 2020, extended to its GIFT City unit in 2022.
- Mirae Asset Investment Managers (India): 2022.
- NJ Asset Management: 2023.
- Bajaj Finserv Asset Management: 2023.

I found no quantified Indian case study, and no public evidence that the largest domestic AMCs use AIM.

### Cited Findings
**Named Indian clients**
- **Aditya Birla Sun Life AMC (ABSLAMC), July 2020:** adopted AIM as its order management system across its India and Singapore operations, managing assets of over INR 2,500 billion. It also expanded its Bloomberg Terminal subscriptions. [Vendor / Trade press] — [Digfin](https://www.digfingroup.com/birla-sun-life/); [Bloomberg press (2020)](https://www.bloomberg.com/company/?p=9867)
- **ABSLAMC, Dec 2022:** extended AIM to its GIFT City (IFSC) unit. Bloomberg says this made it the first asset manager in the IFSC to use AIM. [Vendor] — [Bloomberg press](https://www.bloomberg.com/company/press/aditya-birla-sun-life-amc-becomes-indias-first-asset-manager-to-expand-adoption-of-bloomberg-aim-to-its-gift-city-unit)
- **Mirae Asset Investment Managers (India), 4 May 2022:** adopted AIM and **Bloomberg Vault** across fund management, trading, operations, investment risk and compliance, and expanded its Terminal subscriptions. Vault is a hosted archive of electronic communications and trade data for record-keeping and surveillance. [Vendor / Trade press] — [Bloomberg press](https://www.bloomberg.com/company/press/mirae-asset-investment-managers-india-adopts-bloomberg-solutions-for-the-buy-side/); [IBS Intelligence](https://ibsintelligence.com/ibsi-news/mirae-asset-investment-managers-adopts-bloomberg-solutions-for-the-buy-side/)
- **NJ Asset Management (Surat):** adopted AIM and Vault for an "enterprise-wide digital strategy". AIM covers portfolio analytics, order management and trading compliance; Vault covers capture and retention of electronic communications. Bloomberg called NJ one of India's newest AMCs. The date was **July 2023** per a The Trade News extract; another extract placed it around 2024. [Vendor / Trade press] — [The Trade News](https://www.thetradenews.com/nj-asset-management-streamlines-order-management-and-compliance-management-with-bloomberg-solutions/); [A-Team Insight](https://a-teaminsight.com/blog/indias-nj-asset-management-selects-bloomberg-solutions-for-enterprise-wide-digital-strategy/); [Bloomberg press](https://www.bloomberg.com/company/press/nj-asset-management-adopts-bloomberg-solutions-for-enterprise-wide-digital-strategy/)
- **Bajaj Finserv Asset Management:** chose AIM to support research, fund management, trading, operations and investment compliance. Its CIO is quoted calling AIM "the most scalable, integrated and advanced" on the market, and Bloomberg emphasises automated order processing to reduce manual errors. Dated **October 2023** in one extract; another extract could not pin the date. [Vendor / Trade press] — [Bloomberg press](https://www.bloomberg.com/company/press/bajaj-finserv-asset-management-adopts-bloomberg-aim-to-power-digitization-journey); [fi-desk](https://www.fi-desk.com/bajaj-finserv-asset-management-adopts-bloomberg-aim/)
- APS Asset Management appeared among recent AIM adopters in search results. It is not confirmed as an Indian firm, so it is excluded. — [Bloomberg](https://www.bloomberg.com/professional/insights/press-announcement/aps-asset-management-adopts-bloomberg-aim-to-help-scale-automate-and-streamline-operations/)

**Scale and features**
- **Global scale:** "nearly 15,000 professionals at over 900 client firms globally", managing **more than $22 trillion** in 2025 releases (e.g. CMB Wing Lung, June 2025), up from more than $17 trillion in a September 2022 release. [Vendor] — [Bloomberg press: CMB Wing Lung](https://www.bloomberg.com/company/press/cmb-wing-lung-asset-management-streamlines-front-to-back-office-workflows-with-bloomberg-aim); [Bloomberg press: Goodbody](https://www.bloomberg.com/company/press/goodbody-enhances-portfolio-management-workflow-with-adoption-of-bloomberg-aim)
- **Scope:** multi-asset decision support and portfolio management, order management, trade compliance and post-trade workflows. Automated pre- and post-trade checks align with investment mandates and regulatory guidelines and run inside the order workflow rather than as an overlay. AIM runs on a native security master. [Vendor] — [AIM product page](https://professional.content.cirrus.bloomberg.com/professional2023/products/trading/order-management-system/aim); [Bloomberg compliance products](https://professional.bloomberg.com/products/compliance/)
- **Compliance Manager (CMGR):**
  - It consists of a rules engine, an exception blotter (Violation Manager, VMGR) and reporting tools.
  - A pre-violation workflow supports "split and send" and electronic approval.
  - A real-time blotter serves exceptions and surveillance.
  - A client quoted in the award write-up cites 750+ pre-coded rule templates for pre-trade and post-trade checks, with support for custom data.
  - Winner of WatersTechnology's BST Awards 2025 "Best buy-side compliance product (trading)".
  - [Award write-up with client endorsement] — [WatersTechnology](https://www.waterstechnology.com/awards-rankings/7952788/bst-awards-2025-best-buy-side-compliance-product-trading-bloomberg)
- **Best Execution Analytics (BTCA):** ingests trade data whether execution happens on Bloomberg or on a third-party EMS/OMS. [Vendor] — [Bloomberg trade execution page](https://professional.bloomberg.com/solutions/buy-side/trade-execution/)

### Inferences
- The announced Indian AIM wins cluster in newer or foreign-parented AMCs: Mirae Asset has a Korean parent; NJ is described as one of India's newest AMCs; Bajaj Finserv AMC is a recent entrant. Plus ABSLAMC. New AMCs appear to buy an integrated vendor stack (AIM + Vault + Terminal) rather than build or integrate several systems. Large incumbent AMCs may run other OMS products or in-house systems, but this is not evidenced.
- Vault being bought alongside AIM suggests demand for archiving and surveillance of electronic communications. That plausibly links to SEBI's surveillance expectations for AMC dealing rooms, which was not verified (see Gaps).
- ABSLAMC's GIFT City deployment shows AIM positioned for IFSC fund structures as well as onshore funds.
- For the tracker comparison: order routing, broker FIX connectivity, pre-trade blocking and audit trails are outside a tracker's scope. The part a tracker can approximate is post-trade limit monitoring, such as single-issuer, sector and group-exposure limits.

### Gaps
- No count of Indian AIM clients. No Indian case study with metrics. No evidence of AIM use at Indian insurers, pension fund managers (NPS pension fund managers, EPFO), PMS or AIFs.
- Whether CMGR ships SEBI-specific rule templates, such as the Mutual Fund Regulations' investment limits.
- AIM licensing and pricing.
- Where AIM data for Indian clients is hosted (data residency).
- Electronic order routing and FIX connectivity to Indian brokers for NSE/BSE.
- Not searched: SEBI's front-running and market-abuse "institutional mechanism" rules for AMCs as a driver of Vault and surveillance adoption.

## 3. Indian market data on the Terminal

### Takeaway
Bloomberg has carried Indian exchange data since about 1999, when it added live BSE feeds. Later additions:
- 2018: GIFT IFSC derivatives feeds.
- March 2019: BSE XBRL filings (shareholding patterns, results, voting results, governance).
- May 2019: 25,000+ Indian private companies that are rated debt issuers.

Its India news comes from Bloomberg News directly since the BloombergQuint joint venture ended in March 2022. I found no published coverage counts for Indian companies in BEst consensus estimates, transcripts, ESG scores or alternative data.

### Cited Findings
- **History and footprint:** Bloomberg's India operations began in 1996 with a few employees in a Mumbai business centre. Live BSE feeds for Terminal clients started about three years later. [Vendor] — [Bloomberg Spotlight](https://spotlight.bloomberg.com/story/india-from-crisis-to-opportunity/page/7)
- Offices in **Mumbai, New Delhi and Pune**; the Indian entity is **Bloomberg Data Services India Pvt Ltd**. [Vendor] — [Bloomberg careers](https://www.bloomberg.com/company/careers/global-roles/working-at-bloomberg-in-mumbai-pune/); [Bloomberg company profile](https://www.bloomberg.com/profile/company/6599828Z:IN)
- **BSE XBRL, March 2019:** Bloomberg onboarded XBRL data from BSE, the first Indian exchange to accept XBRL financial statements. The data covers shareholding patterns, financial results, voting results and corporate-governance details. Ashlesh Gosain, Bloomberg's Head of South Asia Sales, said mid- to micro-cap investors would see timeliness and transparency "improve significantly". BSE's Chief Regulatory Officer Nehal Vora was also quoted. [Vendor / Trade press; Dated 2019] — [Bloomberg press](https://www.bloomberg.com/company/?p=3376); [DSIJ](https://insights.dsij.in/dsijarticledetail/bse-limited-new-xbrl-data-set-live-on-bloomberg-terminal-6472); [XBRL International](https://www.xbrl.org/news/bloomberg-lists-bse-xbrl-data/); [WatersTechnology](https://waterstechnology.com/node/4203921)
- **Indian private companies, 15 May 2019:**
  - Coverage of 25,000+ companies, selected from about 1.8m private companies registered with the Ministry of Corporate Affairs (MCA).
  - Selection criteria: the company has market debt (loans or bonds) and an outstanding rating from one of India's six rating agencies.
  - Data includes financial statements, credit ratings, annual reports, shareholder information, and legal and bankruptcy history.
  - [Vendor; Dated 2019] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-adds-indian-private-companies-database-terminal/)
- **GIFT City, 2018:** real-time feeds of USD-denominated derivatives on NSE IFSC and India INX (a BSE subsidiary): stock, index, currency and non-agricultural commodity derivatives, at Terminal pages CEM BGC and CEM NGC. GIFT Nifty, formerly SGX Nifty, now trades on NSE IX. [Vendor / Trade press; Dated 2018] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-introduces-real-time-gift-ifsc-derivatives-data-international-investors); [WatersTechnology](https://waterstechnology.com/node/4004751); [Samco explainer](https://www.samco.in/knowledge-center/articles/what-is-sgx-nifty)
- **Indian mutual funds:** Bloomberg carries quote pages for Indian mutual fund schemes, e.g. Quant Small Cap Fund (ESCIBDG:IN). — [Bloomberg quote](https://www.bloomberg.com/quote/ESCIBDG:IN)
- **Consensus estimates (BEst):** no Bloomberg coverage count for India was found.
  - A BloombergQuint piece screened Indian stocks tracked by at least 10 analysts using Bloomberg data. It found 255 "widely covered" companies, 66 of them trading below the lowest analyst target. [Dated; probably before 2022] — [BloombergQuint](https://www.bloombergquint.com/markets/the-10-stocks-that-disappointed-analysts-the-most)
  - Glossary-level claims that apply to any consensus provider: Nifty 50 panels run to 20–45 analysts, against 3–4 for smaller companies; Indian brokers such as Kotak Institutional Equities, Motilal Oswal, ICICI Securities and Edelweiss contribute estimates to global consensus databases. [Weak source] — [EquitiesIndia glossary](https://equitiesindia.com/glossary/consensus-estimate)
- **Transcripts and AI summaries:** Bloomberg launched **AI-Powered Earnings Call Summaries** on **22 Jan 2024**.
  - They condense management discussion by topic, such as guidance, capital allocation and supply chain.
  - They were tuned with input from Bloomberg Intelligence analysts.
  - Each point links to the matching section of the transcript and to Terminal functions.
  - Launch coverage put Terminal subscribers at more than 325,000.
  - Coverage of Indian companies was not stated.
  - [Vendor / Trade press] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-launches-ai-powered-earnings-call-summaries); [Fintech News SG](https://fintechnews.sg/84034/ai/bloomberg-introduces-ai-powered-earnings-call-summaries-for-enhanced-financial-analysis/); [InPublishing](https://inpublishing.co.uk/articles/bloomberg-launches-ai-powered-earnings-call-summaries-22762)
- **Indian transcripts outside Bloomberg:** AlphaStreet publishes Indian concall transcripts. An IEEE DataPort dataset holds about 15,812 transcripts from 1,362 BSE-listed firms covering 2011 to mid-2025. — [AlphaStreet](https://alphastreet.com/india/earnings-call-transcripts); [IEEE DataPort](https://ieee-dataport.org/authors/kanishk-agarwal)
- **ESG:**
  - Bloomberg ESG Scores use only company-disclosed data, with no analyst opinion, are updated as disclosures arrive, and cover 12K+ companies globally. The methodology document is dated December 2025. No India count is given. [Vendor] — [Bloomberg Sustainability Scores](https://professional.bloomberg.com/products/bloomberg-terminal/sustainable-finance/scores/); [Methodology, Dec 2025](https://professional.bloomberg.com/globalassets/professional/products/bloomberg-terminal/sustainable-finance/scores/bloomberg-esg-scores-methodology.pdf?v=639069475520000000)
  - India's BRSR sustainability report is mandatory for the top 1,000 listed companies from FY2022-23, with about 1,600 data points per filing. — [XBRL International paper, Feb 2024](https://www.xbrl.org/wp-content/uploads/2024/02/Unearthing-Insights-from-Indias-ESG-Disclosures.pdf)
  - Dolat Capital (March 2022) found ESG rating data inconsistently available for Indian companies, worst in the environmental and social pillars. [Dated 2022] — [Dolat Capital report](https://images.assettype.com/bloombergquint/2022-03/9d1e5379-2ca3-41d8-9735-2fcd9cdd593e/Dolat_Capital_India_ESG_Report_10_March_2022.pdf)
  - A forum thread reports that some Bloomberg ESG fields were unavailable for Indian companies after the new SEBI rules and could not be exported, and suggests Refinitiv as an alternative. [Anecdotal; undated] — [ResearchGate thread](https://www.researchgate.net/post/How_can_I_get_the_data_for_ESG_scores_of_Indian_companies_Can_I_get_it_from_Bloomberg)
  - Academic studies have used Bloomberg ESG disclosure scores for Indian firms, e.g. a 2014–2022 panel, and 48 firms from the BSE-100. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0161893825001346); [ResearchGate paper](https://www.researchgate.net/publication/362079375_Impact_of_ESG_score_on_financial_performance_of_Indian_firms_static_and_dynamic_panel_regression_analyses)
- **News:**
  - The Bloomberg–Quintillion equity joint venture ended on **1 March 2022** and was replaced by a content-licence agreement. Bloomberg Media said it "remains committed to our presence in India".
  - BloombergQuint was renamed BQ Prime on 5 May 2022. Bloomberg had held 26%.
  - Adani's AMG Media bought 49%, then the remaining 51%, of Quintillion Business Media.
  - BQ Prime merged into NDTV Profit in **December 2023**.
  - — [Talking Biz News](https://talkingbiznews.com/media-news/bloomberg-ends-its-joint-venture-in-india/); [Wikipedia: BQ Prime](https://en.wikipedia.org/wiki/BQ_Prime); [Outlook Business](https://www.outlookbusiness.com/news/adani-to-buy-remaining-51-per-cent-stake-in-bq-publisher-quintillion-business-media-news-310833)
- **Bloomberg News still covers Indian equities directly**, including small caps and fund flows. Examples: "India Equity Funds Draw $3 Billion as Small-Cap Bets Surge" (10 Jul 2026); "Retail Traders Feel the Strain as India's Small Caps Stumble" (9 Dec 2025); "India's Debt Fund Managers Turn Tactical…" (13 Jan 2026); and the retail feature "Where to Invest ₹10 Lakh" (Q4 2025). — [Bloomberg](https://www.bloomberg.com/news/articles/2026-07-10/india-equity-funds-draw-3-billion-as-small-cap-bets-surge); [Bloomberg](https://www.bloomberg.com/news/articles/2025-12-09/retail-traders-feel-the-strain-as-india-s-small-caps-stumble); [Bloomberg](https://www.bloomberg.com/news/articles/2026-01-13/india-s-debt-fund-managers-turn-tactical-as-returns-get-harder); [Bloomberg](https://www.bloomberg.com/features/where-to-invest-10-lakh-india-q4-2025/)
- **Shareholding context (not about Bloomberg):** Indian listed companies file quarterly shareholding patterns under SEBI LODR Regulation 31, and BSE publishes them as XBRL with promoter-group line items. Aggregator sites disagree on category totals. For BSE Ltd in June 2026, Anand Rathi shows 9.63% FII holding, while Value Research and Trendlyne show about 21.3%. This illustrates the risk of mapping Indian ownership categories inconsistently. — [BSE XBRL shareholding example](https://beta.bseindia.com/XBRLFILES/SHPXBRLDataXML/532454_2042026144415_SP.html); [Anand Rathi](https://anandrathi.com/stocks/bse-ltd/shareholding-pattern); [Value Research](https://www.valueresearchonline.com/stocks/97436/bse-ltd/shareholding/); [Trendlyne](https://trendlyne.com/equity/share-holding/52884/BSE/latest/bse-ltd/)
- **Naming trap:** Bloomberg's June 2023 "BSE real-time pricing data" launch refers to the **Beijing** Stock Exchange (exchange code JC), not BSE India. — [The Trade News](https://www.thetradenews.com/bloomberg-terminal-adds-bse-real-time-pricing-data-to-offering/); [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-launches-beijing-stock-exchange-real-time-pricing-data)

### Inferences
- Since 2019, Bloomberg's fundamentals for Indian listed companies have drawn at least partly on BSE XBRL filings, which a self-built tracker can parse too. Bloomberg's advantage is therefore normalisation against global peers, long history, consensus estimates, and integration with PORT, MAC3 and AIM, rather than exclusive Indian primary data.
- The Indian private-company dataset is built for credit (rated debt issuers). It is useful for unlisted debt but says little about unlisted equity.
- After the BloombergQuint exit, whose successor is now Adani-owned NDTV Profit, Bloomberg's own India news is English-language Bloomberg News. Any Hindi or regional-language coverage on the Terminal would come from third-party sources. This is unverified.

### Gaps
- Not covered by any source I reached:
  - NSE cash-market real-time entitlement and fees on the Terminal;
  - completeness of corporate actions for Indian bonuses, splits and rights;
  - coverage of the NSE Emerge / BSE SME platforms;
  - BEst coverage counts for India;
  - Indian transcript and event-calendar coverage;
  - ESG score counts for India and how BRSR fields map into Bloomberg data;
  - Bloomberg Intelligence analyst coverage of India;
  - India-specific alternative data.

## 4. Pricing: Terminal, PORT/AIM licensing, data licences (B-PIPE, Data License) and India-specific pricing

### Takeaway
Bloomberg publishes no price list. The most-cited figures come from NeuGroup:
- Two-year subscriptions starting or renewing from **1 Jan 2025** rose 6.5%.
- A single Terminal costs **$31,980/yr**; firms with several Terminals pay **$28,320/yr per seat**.

2026 guides still cite these numbers. Indian estimates of roughly **₹24–30 lakh per seat per year** look like currency conversions of the USD price, not an Indian price list. PORT Enterprise, AIM, Vault, B-PIPE and Data License are negotiated separately, and I found no public prices for them.

### Cited Findings
- **NeuGroup:**
  - 6.5% increase for two-year subscriptions beginning or renewing on or after 1 Jan 2025.
  - Single Terminal: **$31,980/yr**.
  - More than one Terminal: **$28,320/yr per Terminal**, up from $26,580 after a 9.6% increase in 2023.
  - Bloomberg ties increases to weighted global inflation over the prior two years.
  - [Independent report of vendor pricing] — [NeuGroup](https://connect.neugroup.com/public/blogs/bloomberg-terminals-how-much-more-youll-pay-next-year)
- 2026 guides still quote $31,980/yr ($2,665/month) for a single seat, with ranges of $24k–32k. One site mislabels monthly figures as annual. [3rd-party est.] — [Godel Discount](https://godeldiscount.com/blog/bloomberg-terminal-cost-2026); [CostBench](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/); [Eulerpool](https://eulerpool.com/blog/bloomberg-terminal-cost)
- About $32,000 per user per year now, against about $20,000 in 2010, on two-year contracts with limited flexibility mid-contract. [3rd-party] — [Hudson Labs](https://www.hudson-labs.com/blog/free-and-low-cost-alternatives-to-bloomberg)
- **Extras claimed by third-party sites (unverified):**
  - exchange data fees of $600 to $6,000+ per user per year;
  - a second Terminal only about 11% cheaper;
  - early termination costs 50% of the remaining contract.
  - [3rd-party est.] — [CostBench: hidden costs](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/hidden-costs); [Eulerpool](https://eulerpool.com/blog/bloomberg-terminal-cost)
- **India estimates:**
  - An Indian blog (2026): about ₹26.8 lakh per user per year on a multi-user subscription, and about ₹30.3 lakh for a single Terminal, "subject to exchange rates, taxes and contract terms". [3rd-party est.] — [BullSmart](https://blog.bullsmart.in/world-most-expensive-trading-terminal-bloomberg/)
  - Another guide: ₹18–25 lakh per year. [3rd-party est.] — [LoansJagat](https://www.loansjagat.com/terminal/bloomberg-terminal)
  - A Zerodha forum thread: about ₹17 lakh, i.e. $24k at ₹70/USD. [Anecdotal; c.2019] — [TradingQnA](https://tradingqna.com/t/bloomberg-terminal-india/60786)
  - Quora: two-year contracts costing over ₹23 lakh, with sales via a Bloomberg India helpdesk. [Anecdotal] — [Quora](https://www.quora.com/How-does-one-subscribe-to-a-Bloomberg-terminal-in-India)
- **B-PIPE / Data License:**
  - No public prices.
  - Contracts are negotiated on data fields, exchanges, redistribution rights and the number of consuming applications, separately from the Terminal.
  - Procurement can take months.
  - B-PIPE is listed on Azure Marketplace.
  - [3rd-party] — [APIs.io](https://apis.io/plans/bloomberg/bloomberg-plans-pricing/); [Multiples](https://multiples.vc/compare/bloomberg-api-alternatives); [London Strategic Edge](https://londonstrategicedge.com/directory/data-providers/bloomberg-b-pipe-data-license/); [Azure Marketplace](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/bloomberglp1588954359718.bloomberg_market_data_feed_bpipe?tab=overview)
  - Enterprise data feeds for integration with internal systems are priced separately from Terminal subscriptions. [3rd-party] — [Vendr](https://www.vendr.com/marketplace/bloomberg)
- **Public-sector contract values (UK, not India):**
  - Ofcom: single-supplier contract for Bloomberg access in 2024, £27,000.
  - Ofgem: four-year Bloomberg licence, £135,936.
  - — [Contracts Finder (Ofcom)](https://www.contractsfinder.service.gov.uk/notice/178ae026-113a-49eb-bd06-c98335757221); [Contracts Finder (Ofgem)](https://www.contractsfinder.service.gov.uk/notice/6f8ba355-556e-4d75-98cb-bc1d832e1b7d)
- **PORT tiers:** Bloomberg calls PORT Enterprise "premium". MAC3 models and batch reporting are described as Enterprise features, implying an add-on licence to the Terminal. No price was found. [Vendor] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-advances-portfolio-analytics-with-launch-of-ai-portfolio-commentary-in-port-enterprise)

### Inferences
- **Currency conversion (my arithmetic, not sourced prices):**
  - $31,980 at ₹85–95/USD is about **₹27.2–30.4 lakh** a year.
  - $28,320 at the same rates is about **₹24.1–26.9 lakh** a year.
  - BullSmart's ₹30.3 lakh and ₹26.8 lakh imply roughly ₹94.7/USD. That fits a straight conversion of the USD price rather than a separate rupee price.
  - Pricing in USD with an inflation-linked escalator means rupee depreciation raises costs for Indian buyers.
- **Illustrative estimate for a 10-seat Indian AMC:** about $283k a year, roughly ₹2.4–2.7 crore, for Terminals alone at multi-seat pricing. That is before exchange fees, PORT Enterprise, AIM, Vault and Data License. This is an order-of-magnitude guide only.
- For a PMS or AIF boutique, one or two seats at about ₹25–30 lakh each is a large fixed cost next to Indian local databases. This is the main economic case for a self-built tracker.

### Gaps
- No India-specific price list. No Indian public procurement records: GeM and CPPP tenders were not indexed by search.
- Whether Indian clients are invoiced in INR or USD, and how GST applies.
- Licence fees for PORT Enterprise, MAC3 or LQA, AIM (per user or AUM-based) and Vault.
- B-PIPE and Data License fees, and NSE/BSE exchange fees on the Terminal.
- Academic or start-up pricing in India.

## 5. Adoption and market position in India; Bloomberg's India operations; regulatory considerations (data localisation, SEBI CSCRF, vendors)

### Takeaway
Bloomberg has been in India since 1996 and publicly names four Indian AMCs on AIM. However, no public source quantifies its Indian seat count or market share against LSEG Workspace, FactSet or the Indian databases (ACE Equity, Capitaline, CMIE Prowess). Globally, Bloomberg and LSEG together take about half of market-data revenue (Burton-Taylor coverage of 2024 data).

On regulation, SEBI's cybersecurity framework (CSCRF) makes AMCs responsible for vendor risk. Its data-localisation control has been in abeyance since 31 Dec 2024 and, per secondary sources, still was in May 2026.

### Cited Findings
- **Bloomberg in India:**
  - A Bloomberg release from about 2013 reported 18% growth in India the previous year and a Mumbai office expansion of more than three times. [Vendor; Dated c.2013] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-expands-operations-in-india-2/)
  - "Bloomberg India 20" release: clients in India include corporations, banks, financial institutions, government agencies and 30+ business schools. [Vendor; undated, c.2016] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-india-20-the-next-chapter/)
  - South Asia sales heads named in Bloomberg material: Ashlesh Gosain (2019 releases) and Sunny Chhabria (an undated brochure). The current head was not confirmed. [Vendor] — [Bloomberg press (2019)](https://www.bloomberg.com/company/?p=3370); [Bloomberg "India in the Making" brochure](https://data.bloomberglp.com/promo/sites/12/35607_India_in_the_Making.pdf)
- **Named Indian buy-side users:** ABSLAMC (AIM 2020, GIFT City 2022, more Terminals), Mirae Asset India (AIM + Vault 2022, more Terminals), NJ AMC (AIM + Vault 2023) and Bajaj Finserv AMC (AIM 2023). Sources are in Q2.
- **Job-market signals:**
  - A 2019 BNY Mellon (Pune) posting listed Bloomberg PORT among required risk platforms. [Dated 2019] — [ACCA job listing](https://alljobs.accaglobal.com/job/6282446/sr-analyst-datamgmtqnt-analysis/)
  - A 2026 Michael Page role (AVP, Investment & Market Risk, at an AMC) asks for relative VaR, tracking error, factor exposure and performance attribution across mutual funds, SIFs, PMS, AIFs and offshore funds. The extract names no vendor. — [Michael Page](https://www.michaelpage.co.in/job-detail/senior-manager-avp-investment-market-risk-amc/ref/jn-042026-6993308)
- **Global market size and shares:**
  - Burton-Taylor's 2026 report puts 2025 spending on financial market data and analysis at a record **$49.2bn, up 6.5%**, driven by volatility from US tariffs. — [Burton-Taylor reports](https://burton-taylor.com/reports); [TP ICAP Burton-Taylor 2026 report page](https://tpicap.com/burtontaylor/reports/03/2026/financial-market-dataanalysis-global-share-segment-sizing-2026)
  - Finextra reported spending "hits $44.3bn". If that figure is for 2024, it does not square with +6.5% to $49.2bn in 2025, so it may be the 2023 figure. Unresolved. — [Finextra](https://www.finextra.com/newsarticle/45769/global-spending-on-financial-market-data-hits-443bn)
  - Coverage of the 2024 data says **Bloomberg and LSEG together take about half** of market-data revenues. — [TRG Screen](https://www.trgscreen.com/market-data-spend-hits-another-record-as-complexity-grows)
  - In the research-analyst segment in 2022: S&P Global 22.2%, FactSet 19.3%, Bloomberg 17.8%, LSEG 15.4%; the top four held about 75%. [Dated 2022 data] — [Burton-Taylor PDF (Sept 2023)](https://tpicap.com/burtontaylor/sites/g/files/escbpb181/files/burton-taylor/reports/2023-09/Research%20Analysts%20Data%20Usage.pdf)
- **Indian local alternatives** (all institutional licences; university libraries list them as restricted resources):
  - ACE Equity (Accord Fintech): about 30,000 Indian listed and unlisted companies; mutual fund data sold separately as ACE MF.
  - Capitaline: 74,800+ listed and unlisted companies with about 2,500 data fields.
  - CMIE Prowess: described as the largest standardised database of Indian companies with the longest time series.
  - The numbers come from library and encyclopedia extracts and could not be checked individually. — [IIM Ahmedabad library](https://library.iima.ac.in/subjectguides/subjects/guide.php?subject=CFD); [IIM Trichy](https://www.iimtrichy.ac.in/en/lrc-compinfo); [IIM Bangalore data sources](https://www.iimb.ac.in/ccmrm/resources-at-iim-bangalore-data-sources.php); [Wikipedia: CMIE](https://en.wikipedia.org/wiki/Centre_for_Monitoring_Indian_Economy)
- **SEBI CSCRF scope and localisation:**
  - CSCRF covers mutual funds, AMCs and AMC trustees among other regulated entities. [Secondary] — [Ampcus Cyber](https://www.ampcuscyber.com/blogs/understanding-sebi-cscrf/); [Doverunner](https://doverunner.com/blogs/sebis-cybersecurity-and-cyber-resilience-framework/)
  - SEBI put the data-localisation requirement in abeyance through a 31 Dec 2024 circular, pending further consultation. Secondary sources cite the circulars as 2024/113 (the framework) and 2024/184. — [MediaNama, Jan 2025](https://www.medianama.com/2025/01/223-sebi-holds-off-on-data-localisation-cscrf-framework/)
  - Per security consultancies, the localisation control PR.DS.S2 was not reinstated by the April 2025 amendment (CIR/2025/60), the August 2025 technical clarifications (CIR/2025/119) or a May 2026 AI advisory. It was "non-current" as of 6 May 2026, with no deadline announced. [Secondary; not checked against SEBI circulars] — [Security Brigade](https://securitybrigade.com/blog/sebi-cscrf-data-localisation-abeyance/); [CyberNX](https://www.cybernx.com/data-localisation-under-sebi-cscrf/)
- **Vendor oversight still applies:** the regulated entity stays responsible even when a vendor hosts its data. Cloud use is allowed with a documented risk assessment, board approval for material outsourcing, encryption keys held by the regulated entity, and an exit or portability plan. Pelta argues regulated entities must keep control and legal jurisdiction over regulatory data, treating localisation as substance over form, which conflicts with the "abeyance" reading. [Secondary, consultancy] — [Pelta](https://peltatech.com/resources/sebi-cscrf-data-localisation); [CyberNX: third-party risk](https://www.cybernx.com/third-party-risk-assessment-under-sebi-cscrf/); [RingSafe CSCRF guide 2026](https://ringsafe.in/sebi-cscrf-guide/)

### Inferences
- Bloomberg's visible buy-side penetration in India is at the AMC and institutional tier. PMS and AIF boutiques, facing ₹25–30 lakh per seat, probably run fewer seats plus Indian databases. No survey confirms this.
- FPIs buying India mostly run global stacks offshore (Bloomberg, FactSet, Aladdin). For them, Bloomberg's relevance to India lies in the India and global MAC3 models, GIFT/IFSC data and index work such as FAR bond inclusion.
- AIM, Vault and PORT Enterprise are Bloomberg-hosted services. While PR.DS.S2 remains in abeyance, CSCRF does not bar offshore hosting, but AMCs must document third-party risk. If localisation were reinstated, hosted order-management and communications-archive data would become a compliance question. A self-built tracker hosted in India avoids that question. ABSLAMC's GIFT City unit falls under a different regulator (IFSCA).

### Gaps
- No Indian seat counts, revenue, or market-share estimates. No survey of vendor use by Indian AMCs, PMS or AIFs.
- No evidence of use by insurers (e.g. LIC), pension funds (NPS pension fund managers, EPFO) or AIFs.
- No Bloomberg statement on India data centres or hosting.
- No SEBI commentary specific to Bloomberg.
- Burton-Taylor's 2025 provider-level shares were not visible.

## 6. Known limitations and criticisms for India-focused managers

### Takeaway
The best-documented drawbacks are **cost** (about $32k per seat per year, two-year lock-ins, extra fees) and **thinner depth for Indian small caps and ESG**. Most evidence is indirect, dated or anecdotal. I found no systematic, independent critique of Bloomberg's India coverage, and no head-to-head data-quality comparison with Indian databases.

### Cited Findings
- **Cost:** about $32,000 per user per year, up from about $20,000 in 2010, on two-year contracts with limited flexibility. [3rd-party] — [Hudson Labs](https://www.hudson-labs.com/blog/free-and-low-cost-alternatives-to-bloomberg). Third-party sites also claim early termination costs 50% of the remaining contract and exchange fees are extra. [3rd-party est.] — [CostBench: hidden costs](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/hidden-costs)
- **Small and micro caps:** in 2019 Bloomberg said BSE XBRL would make mid- to micro-cap data more timely and transparent. That implicitly concedes earlier gaps. [Vendor; Dated 2019] — [Bloomberg press](https://www.bloomberg.com/company/?p=3376)
- **Private companies:** Indian private-company coverage is limited to about 25,000 rated debt issuers out of about 1.8m. [Vendor; Dated 2019] — [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-adds-indian-private-companies-database-terminal/)
- **Consensus depth:** analyst coverage is thin below the large caps (3–4 analysts against 20–45 for the Nifty 50). This limits consensus depth from any provider. [Weak source] — [EquitiesIndia glossary](https://equitiesindia.com/glossary/consensus-estimate)
- **ESG gaps for Indian companies:** see Dolat Capital (2022) and the ResearchGate thread. — [Dolat Capital](https://images.assettype.com/bloombergquint/2022-03/9d1e5379-2ca3-41d8-9735-2fcd9cdd593e/Dolat_Capital_India_ESG_Report_10_March_2022.pdf); [ResearchGate thread](https://www.researchgate.net/post/How_can_I_get_the_data_for_ESG_scores_of_Indian_companies_Can_I_get_it_from_Bloomberg)
- **Breadth of Indian databases:** they cover tens of thousands of Indian listed and unlisted companies (ACE Equity about 30k; Capitaline 74.8k+). — [IIM Trichy](https://www.iimtrichy.ac.in/en/lrc-compinfo); [IIM Ahmedabad library](https://library.iima.ac.in/subjectguides/subjects/guide.php?subject=CFD)
- **Local news:** Bloomberg left its Indian news joint venture in 2022, and the successor outlet is now part of Adani's NDTV Profit. — [Talking Biz News](https://talkingbiznews.com/media-news/bloomberg-ends-its-joint-venture-in-india/); [Wikipedia: BQ Prime](https://en.wikipedia.org/wiki/BQ_Prime)
- **Transcripts:** Indian earnings-call transcript sources exist outside Bloomberg (AlphaStreet; the IEEE DataPort dataset of BSE transcripts). — [AlphaStreet](https://alphastreet.com/india/earnings-call-transcripts); [IEEE DataPort](https://ieee-dataport.org/authors/kanishk-agarwal)

### Inferences
- For an India-only manager, what Bloomberg offers that is hard to replicate is the India-specific MAC3 risk model and the global ones, VaR and scenario machinery, LQA, AIM/CMGR compliance with order routing, global cross-asset context, and Bloomberg News. The parts a small tracker can replicate cheaply are Indian prices, filings (BSE/NSE XBRL), corporate actions, shareholding patterns, results calendars and announcement feeds, all of which exchanges publish.
- Bloomberg's weak spots for Indian small caps (few contributing analysts, patchy ESG disclosure) come from the underlying Indian data, not only from Bloomberg. A self-built tracker will hit the same limits unless it adds its own primary-filing parsing (BRSR XBRL, shareholding XBRL).
- A self-built tracker working from primary filings could check its shareholding-category mapping directly against the exchange XBRL. The aggregator disagreements in Q3 show this is a real source of error.

### Gaps
- No independent survey or critique of Bloomberg by Indian fund managers.
- No tests of Bloomberg's accuracy against ACE Equity, Capitaline or Prowess for Indian small caps.
- No evidence on how accurate Bloomberg's corporate actions are for Indian stocks, or how fast BSE/NSE announcements reach the Terminal.
- No evidence on Hindi or regional-language news on the Terminal.
- Not searched (budget exhausted): Indian practitioner commentary such as Mint/ET interviews, or Reddit/forum threads comparing Bloomberg with LSEG Workspace or Indian tools.
