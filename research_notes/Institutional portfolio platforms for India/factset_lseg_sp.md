# Institutional portfolio platforms for Indian listed equities: FactSet, LSEG (Refinitiv), S&P Global Market Intelligence, and Morningstar Direct for fund-peer work (as of October 2026)

Method note (applies to every section): research was done on 2026-10-10. No full page could be read. WebFetch returned DNS errors (ENOTFOUND) for every host tried: insight.factset.com, go.factset.com, investor.factset.com, tpicap.com, www.morningstar.in, www.nasdaq.com and assets.applytosupply.digitalmarketplace.service.gov.uk. One curl test to www.factset.com was refused by the egress proxy with HTTP 403; it was not retried and no workaround was tried. The findings below therefore rest on search-engine excerpts of the cited pages, not full reads. The URL given is the page the excerpt came from. Figures should be spot-checked against the source before publication. The session's web-search budget ran out before the last planned query, which was about CRISIL's analytical-centre work for S&P Global Ratings.

Labels used below:
- **[Vendor claim]**: marketing material or a product page.
- **[3rd-party est.]**: a figure from an aggregator, or an estimate.
- **[Dated]**: a source from before 2024.
- **[Low-quality source]**: an SEO or aggregator site of doubtful reliability.

## 1. FactSet: portfolio analysis (PA), SPAR, Brinson and multi-factor attribution, risk models, Portfolio Commentary, OMS/EMS, and how deeply its data covers Indian companies

### Takeaway
FactSet has the most complete holdings-based analytics stack of the three vendors:
- Portfolio Analysis, with more than 10 attribution models (Brinson and risk/factor-based).
- SPAR for returns-based style analysis.
- Its own multi-asset class (MAC) and equity factor risk models, plus hosted MSCI Barra and Axioma models.
- AI-drafted Portfolio Commentary that cites the underlying numbers (April 2024).
- Front-office trading through the Portware EMS (bought in 2015) and the LiquidityBook OMS/IBOR (bought February 2025 for $246.5M).

FactSet publishes only global coverage counts: about 78–86k companies in Fundamentals, and about 16–19k companies with 800–1,200 contributors in Estimates. Its largest office worldwide is in Hyderabad. I found no public India-specific coverage figures for Fundamentals, Estimates, StreetAccount or transcripts.

### Cited Findings
**Portfolio Analysis (PA) and attribution**
- FactSet says it offers "more than 10 attribution models", covering equity, fixed income, multi-asset class, risk-based, top-down and multi-manager analysis. The risk side breaks absolute and relative risk into factor contributions, and adds stress testing and extreme-event analysis. [Vendor claim] — [FactSet Portfolio Analysis brochure](https://insight.factset.com/hubfs/Resources%20Section/Brochures/portfolio-analysis-brochure.pdf); [The Wealth Mosaic: FactSet performance measurement & attribution](https://www.thewealthmosaic.com/vendors/factset/performance-measurement-attribution/)
- FactSet has published a multi-factor attribution framework, meant to sit alongside Brinson. It runs on the FactSet/Northfield Global Equity Risk Model, which has country, currency and economic factors. The article gives no India example. [Vendor content] — [FactSet Insight: multi-factor attribution framework](https://insight.factset.com/how-a-multi-factor-attribution-framework-can-provide-a-deeper-insight-into-the-sources-of-relative-performance_)
- Brinson basics, for context. Brinson splits active return into allocation, selection and interaction effects. The result depends heavily on the grouping chosen (sector, region, market cap). Risk/factor-based attribution is the more granular alternative. — [SimCorp: Risk-based or Brinson attribution (2024)](https://www.simcorp.com/resources/insights/industry-articles/2024/Risk-based-or-Brinson-attribution)

**SPAR (returns-based style analysis)**
- SPAR stands for "Style, Performance and Risk". FactSet introduced it in fiscal 2000 to analyse the style, performance and risk of portfolios, benchmarks and competitor funds. [Dated: 2001] — [FactSet 10-K, 2001](https://www.sec.gov/Archives/edgar/data/1013237/000101323701500062/f10kstart.htm)
- The SPAR brochure describes returns-based analysis against a benchmark, a competitor or a peer universe. It shows whether a fund leans towards small or large caps, and towards value or growth. [Vendor claim; undated] — [FactSet SPAR 3 brochure](https://go.factset.com/hubfs/Resources%20Section/Brochures/spar_3_brochure.pdf)
- Background on the method. Returns-based style analysis compares a fund's monthly returns, usually over 3–5 years, against style indices. The results depend heavily on which style benchmarks are chosen. — [Morningstar Style Analysis factsheet](https://advisor.morningstar.com/Principia/pdf/StyleAnalysis_FactSheet.pdf); [NBER w9111, Ben Dor & Jagannathan](https://www.nber.org/system/files/working_papers/w9111/w9111.pdf)

**Risk models (FactSet's own and hosted third-party models)**
- FactSet MAC model:
  - Uses Monte Carlo simulation.
  - Computes tracking error, VaR and expected tail loss.
  - Has factors for equities, fixed income, commodities and alternatives, joined in a full cross-asset factor covariance matrix.
  - [Vendor claim; one brochure is FY2019] — [FactSet MAC risk brochure](https://insight.factset.com/hubfs/Resources%20Section/Brochures/multi-asset-class-risk-management-brochure.pdf); [FactSet MAC Model brochure FY19](https://go.factset.com/hubfs/Resources%20Section/Brochures/ID120_FSM%20293%20MAC%20Model%20Brochure_FY19_Final.pdf)
- FactSet global daily equity model: 1 global market factor, 11 style factors, 69 industry factors and 52 country (or country-group) factors. [Vendor claim] — [FactSet Equity Model Global Daily brochure](https://advantage.factset.com/hubfs/Website/Resources%20Section/Brochures/factset-equity-model-global-daily-brochure.pdf)
- FactSet global monthly equity model: 10 style factors, 52 regional factors, 69 industry factors and 1 global market factor. [Vendor claim] — [FactSet global equity factor model white paper](https://advantage.factset.com/global-equity-factor-model-white-paper)
- MSCI Barra on FactSet:
  - Barra models are built into FactSet's portfolio analytics.
  - They show tracking error, risk split into common-factor and stock-specific parts, active exposures, and contributions to risk.
  - The factsheet marks in bold the countries that have their own dedicated model, on top of the global, regional and integrated models. The excerpt did not show whether India is one of them.
  - [Vendor claim] — [MSCI: Barra Analytics on FactSet](https://www.msci.com/resources/factsheets/Barra_Analytics_on_FactSet.pdf)
- MSCI overall: 70+ equity factor models covering 90,000+ securities, 49 industries and 85+ countries. [Vendor claim] — [MSCI equity factor models](https://www.msci.com/data-and-analytics/factor-investing/equity-factor-models)
- Axioma on FactSet:
  - FactSet already offered Axioma's fundamental and statistical equity risk models.
  - It later added Axioma's linear fixed-income and multi-asset class models.
  - The partnership began in March 2010.
  - [Dated: the article is undated, apparently mid-2010s] — [WatersTechnology: FactSet adds Axioma's linear fixed-income, MAC models](https://waterstechnology.com/node/2480400)
- Axioma's ownership changed. In November 2023 SimCorp, part of Deutsche Börse, announced a merger with Axioma, which until then had been part of Qontigo. SimCorp said it would keep an open-platform strategy, including access to other risk providers. — [SimCorp: SimCorp to merge with Axioma (Nov 2023)](https://simcorp.com/about-us/news/2023/SimCorp-to-merge-with-Axioma)

**Portfolio Commentary and reporting**
- Launched 30 April 2024. It produces AI-written explanations of the performance attribution inside the Portfolio Analysis application. — [GlobeNewswire: FactSet Introduces AI-Powered Portfolio Commentary (30 Apr 2024)](https://www.globenewswire.com/news-release/2024/04/30/2872173/7768/en/factset-introduces-ai-powered-portfolio-commentary.html); [SoftwareOne product listing](https://platform.softwareone.com/product/portfolio-commentary/PCP-5202-4056)
- Each generated sentence carries "auditable connections" to the numbers behind it, and users can move between the text and the data. FactSet presents the output as an editable first draft. [Vendor claim] — [GlobeNewswire release](https://www.globenewswire.com/news-release/2024/04/30/2872173/7768/en/factset-introduces-ai-powered-portfolio-commentary.html); [FactSet Insight: baseline commentary in 60 seconds](https://insight.factset.com/watch-how-to-generate-a-baseline-portfolio-commentary-with-ai-in-60-seconds)

**OMS/EMS (trading)**
- FactSet bought the Portware EMS in 2015. An unnamed industry source quoted by Burton-Taylor called Portware "a good EMS but tends to be overkill for many firms". — [TP ICAP Burton-Taylor: FactSet-LiquidityBook, the buy-side OMS space continues to shrink (Feb 2025)](https://tpicap.com/burtontaylor/news/02/2025/factset-liquiditybook-buy-side-oms-space-continues-shrink)
- LiquidityBook acquisition:
  - Announced 10 February 2025, for $246.5M in cash.
  - Adds cloud-native order management (OMS) and investment book of record (IBOR) capability.
  - LiquidityBook runs its own FIX network with links to more than 200 brokers.
  - The company was founded in 2005, is based in New York and had about 70 staff.
  - Before the deal, a partnership had already integrated LiquidityBook's OMS into the FactSet Workstation.
  - Sources: [FactSet IR: FactSet Acquires LiquidityBook](https://investor.factset.com/news-releases/news-release-details/factset-acquires-liquiditybook); [FinTech Futures](https://www.fintechfutures.com/press-releases/factset-acquires-liquiditybook); [Pulse 2.0](https://pulse2.com/factset-buying-liquiditybook-in-246-5-million-deal/)

**FactSet Fundamentals: depth and history**
- History of the database:
  - In April 2008 FactSet won the right to buy a copy of Thomson's Worldscope database, which then covered more than 43,000 companies with history back to 1980.
  - Since May 2010 FactSet has collected the data entirely itself.
  - Annual history runs back to 1980 for developed markets and to the early 1990s for emerging markets.
  - Interim (quarterly) history runs from 1998 for US companies and from 2001 for non-US companies.
  - [Dated brochure] — [FactSet Fundamentals brochure (hosted by Univ. Hamburg)](https://www.wiso.uni-hamburg.de/bibliothek/recherche/datenbanken/unternehmensdaten/factset-fundamentals.pdf)
- Published coverage counts differ by date:
  - An older brochure: 73,000+ public and private companies, 42,500 actively covered, about 2,000 data items.
  - A 2019 DataFeed document: 86,000+ companies, including inactive ones, from more than 115 countries.
  - A Xignite listing: 78,000+ companies from 118 countries.
  - An ICE listing: 120 countries.
  - Sources: [FactSet Fundamentals DataFeed at a glance](https://insight.factset.com/resources/at-a-glance-factset-fundamental-datafeed); [Xignite listing](https://cmsstaging.xignite.com/wiki/49); [ICE developer catalog](https://developer.ice.com/fixed-income-data-services/catalog/factset)
- **Coverage selection rule (relevant to Indian small caps):** FactSet decides what to cover based on "Market Capitalization, Index Constituents, Broker Coverage, Size, and Importance of the Market". — [Xignite listing of FactSet Fundamentals](https://cmsstaging.xignite.com/wiki/49)

**FactSet Estimates**
- The global figures differ between documents. One says 16,000+ active companies in 90 countries from "over 800 contributors". Later FactSet material says 19,000+ active companies in 90+ countries and "more than 1,200 contributing brokers". — [FactSet Estimates OnDemand](https://go.factset.com/hubfs/Website_Downloads/Statistical%20Package%20Integration/Docs%203.0/estimates-ondemand.pdf); [FactSet Consensus Estimates DataFeed](https://insight.factset.com/resources/factset-consensus-estimates-datafeed); [FactSet corporate services brochure](https://go.factset.com/hubfs/Website/Resources%20Section/Brochures/solutions-for-corporate-services-brochure.pdf)
- In November 2022 FactSet added 70,000+ private companies with revenue above $1M in Malaysia, India and Vietnam. These are private-company financials, not estimates. — [FactSet: expands private company data coverage in Asia (Nov 2022)](https://go.factset.com/news/factset-expands-private-company-data-coverage-in-asia)
- By June 2024 FactSet's Asia-Pacific private-company coverage exceeded 1.6M firms, after an expansion focused on China, Japan and Australia. — [FactSet: expands APAC private company data coverage (2024)](https://go.factset.com/news/factset-expands-existing-suite-of-asia-pacific-private-company-data-coverage)

**StreetAccount news and transcripts**
- FactSet bought StreetAccount, a news provider based in Jackson, Wyoming, partly to increase its coverage of Europe and Asia. [Dated: 2013 filing] — [FactSet SEC filing R14](https://www.sec.gov/Archives/edgar/data/1013237/000143774913000323/R14.htm)
- An AWS Marketplace listing says StreetAccount covers the US and Europe "with expanding Asia coverage", plus round-the-clock market summaries for the US, Europe and Asia. — [AWS Marketplace: StreetAccount](https://aws.amazon.com/marketplace/pp/prodview-7luwmqro77biw)
- The XML news archive goes back to 2003 and holds more than 2M stories. — [FactSet Document Distributor: XML StreetAccount News](https://insight.factset.com/resources/factset-document-distributor-xml-streetaccount-news)
- On its Q3 FY2021 earnings call, FactSet linked the expansion of StreetAccount into Canada and Asia to demand from wealth managers. — [Motley Fool transcript, FactSet Q3 FY2021](https://www.fool.com/earnings/call-transcripts/2021/06/29/factset-research-systems-inc-fds-q3-2021-earnings/)

**India footprint and business scale**
- FactSet has operated in India since 2008. In 2016 it had more than 3,000 staff across Hyderabad and Mumbai, and its Hyderabad Global Operations Center was its largest office worldwide. [Dated: 2016] — [FactSet IR: expands India operations](https://investor.factset.com/news-releases/news-release-details/factset-expands-india-operations-hosts-lamp-lighting)
- Built In Hyderabad lists about 10,310 FactSet employees in Hyderabad. [3rd-party; undated] — [Built In Hyderabad: FactSet](https://builtinhyderabad.in/company/factset)
- Hyderabad job ads in 2025–26 are for content and data roles, such as a content specialist for the Media data offering. — [Built In Hyderabad FactSet jobs](https://builtinhyderabad.in/company/factset/jobs); [MarketingMonk job listing](https://www.marketingmonk.so/jobboard/jobs/content-specialist-deep-sector-at-factset-jwzuwy)
- FY2025 (year to 31 August 2025): ASV $2,405.6M, organic ASV $2,370.9M (+5.7%). — [FactSet Q4/FY2025 results](https://seekingalpha.com/pr/20236646-factset-reports-results-for-fourth-quarter-and-fiscal-2025)
- Asia-Pacific ASV was $229.0M (Q1 FY25), $233.7M (Q2) and $240.1M (Q3), with 7.1% organic growth in Q3. At 31 May 2025 FactSet had 8,811 clients and 220,496 users. — [FactSet Q3 FY2025 results (Barchart)](https://www.barchart.com/story/news/32998235/factset-reports-results-for-third-quarter-2025); [FactSet Q2 FY2025 results](https://www.streetinsider.com/Press+Releases/FactSet+Reports+Results+for+Second+Quarter+2025/24525218.html)
- Asia-Pacific organic ASV growth was about 7% in fiscal Q2 2026 (from a summary of earnings-call coverage). — [TipRanks: FactSet earnings call](https://www.tipranks.com/news/company-announcements/factsets-earnings-call-growth-amid-challenges)

### Inferences
- Asia-Pacific is about 10% of FactSet's ASV ($240M of $2,406M), and FactSet does not report India separately. India revenue is therefore probably a small part of a small region. FactSet's India presence is mainly a content and operations base, not a sales market.
- FactSet covers companies according to index membership and broker coverage. Fundamentals are therefore probably complete and timely for NSE/BSE index constituents and broker-covered mid caps, and thinner or later for Indian micro caps. This is not verified against any India count.
- The global daily model has 52 country factors, so India very likely has its own country factor. An India-only manager, however, needs within-India factors (size, value and momentum inside the Indian universe). Whether FactSet hosts a single-country India model, from Barra, Axioma or FactSet itself, is unconfirmed.
- Comparison with a self-built tracker:
  - Brinson attribution by sector or market-cap bucket can be replicated easily with exchange and benchmark-weight data.
  - The hard parts to replicate are:
    - Factor risk models and their covariance matrices.
    - Multi-model, multi-currency attribution.
    - AI commentary audited against the numbers.
    - The OMS/IBOR/EMS link to trading.

### Gaps
- No India-specific counts were found for FactSet Fundamentals (number of Indian listed companies covered, or how far down the cap scale), for FactSet Estimates (which Indian brokers contribute, or how many Indian companies have consensus), for StreetAccount India news, or for FactSet/CallStreet transcripts of Indian earnings calls.
- It is not confirmed whether MSCI Barra or Axioma single-country India models are hosted on FactSet.
- No India pricing or India client counts were found.
- It is unknown whether Portware or LiquidityBook connect to Indian brokers or exchanges.
- FactSet product pages could not be read (proxy 403 on www.factset.com; DNS failures on the other FactSet hosts).

## 2. LSEG Workspace (formerly Eikon), Datastream and Refinitiv data: I/B/E/S India coverage, StarMine, Indian fundamentals, ownership, Reuters news, Lipper, and portfolio analytics

### Takeaway
I/B/E/S is the largest estimates network by stated scale: 22–23k active companies in 90+ countries, 950+ contributing firms "from large global houses to regional and local brokers", and 18,000+ analysts. LSEG-compiled consensus does appear for Indian stocks; for example, 15 analysts covered LG Electronics India. StarMine adds SmartEstimate and the Analyst Revisions Model for 17,500 companies worldwide.

Datastream and LSEG pricing cover NSE from 1994. Lipper has an India mutual fund pricing dataset sourced via NSE. Lipper Fund Awards India ran until at least 2022.

Workspace includes multi-asset Portfolio Analytics (attribution, contribution, style, risk) and the MSCI Barra Optimizer. These are described only in marketing terms, and no India-specific depth was found.

### Cited Findings
**I/B/E/S estimates**
- I/B/E/S covers 22,000+ active companies in 90+ countries, sourced from 18,000+ analysts. More than 950 firms contribute estimates, "from large global houses to regional and local brokers". The regions listed include Asia/Pacific, with no breakdown by country. An older LSEG page gives 890+ contributors. — [LSEG Data Catalogue: I/B/E/S Broker Estimates](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates)
- A WRDS/LSEG brief from November 2025 gives 23,000+ active companies in 90 countries and 950+ brokers. — [WRDS I/B/E/S brief, Nov 2025 (hosted by NCCU library)](https://www.lib.nccu.edu.tw/var/file/0/1000/img/101/WRDS_IBES_202511.pdf)
- LSEG's contributions programme lists 1,300 sell-side and independent research firms contributing research and estimates. [Vendor claim] — [LSEG: Contribute to LSEG Data brochure](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/contribute-to-lseg-data-brochure.pdf)
- Indian coverage in practice: LG Electronics India was "rated 'strong buy' on avg by 15 analysts covering it; median PT at 1,890 rupees – data compiled by LSEG". The page carries no date. — [Stockopedia news item on LG Electronics India](https://www.stockopedia.com/share-prices/lg-electronics-india-NSI:LGEINDIA/news/lg-electronics-india-rises-after-jefferies-initiates-with-apos-buy-apos-019e69f8-f6b2-77fc-97c1-200a871871d2/)

**StarMine**
- SmartEstimate is a weighted average of analyst estimates that gives more weight to recent estimates and to more accurate analysts. "Predicted Surprise" is the gap between SmartEstimate and the I/B/E/S mean. LSEG says that when the gap is significant, it predicts the direction of the earnings surprise 70% of the time. [Vendor claim] — [LSEG Data Catalogue: StarMine SmartEstimates](https://www.lseg.com/en/data-catalogue/analytics/quantitative-analytics/starmine-smartestimates)
- The Analyst Revisions Model, which includes SmartEstimate measures for EPS, EBITDA and revenue, covers 17,500 companies worldwide. SmartEstimate history goes back to 1998. LSEG gives no country breakdown. — [LSEG data for quant research brochure](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/lseg-data-for-quant-research-brochure.pdf)

**Datastream, pricing and Indian market data**
- Datastream covers 107,000+ active equity securities in 100 developed and emerging markets. — [Aalto University DataHub: Datastream](https://datahub.aalto.fi/en/data-sources/datastream)
- LSEG says that "for many markets there is full coverage of all traded equity instruments, with over 50 years of history for the key developed markets", with data taken directly from exchanges. — [LSEG Datastream brochure](https://thesource.lseg.com/TheSource/getfile/download/2364521f-042c-4a2b-be22-66284363a2df); [UNC Workspace guide: Datastream](https://guides.lib.unc.edu/workspace-guide/datastream)
- LSEG's NSE equities pricing dataset has history from 1994 and about 65,000 listings. — [LSEG Data Catalogue: Equities, National Stock Exchange of India](https://www.lseg.com/en/data-catalogue/equities/pricing/equities-national-stock-exchange-of-india-nsei-ll)
- An NSE index dataset (flagship benchmarks and sub-indices) is delivered through feeds and APIs. — [LSEG Data Catalogue: Indices, NSE India](https://www.lseg.com/en/data-catalogue/indices-benchmarks/pricing/indices-national-stock-exchange-of-india-nsei-ll)
- Historical India infrastructure:
  - Thomson Reuters' Elektron went live at NSE's Mumbai co-location facility (undated). — [Institutional Investor](https://institutionalinvestor.com/article/b150z9rb0mb0tq/thomson-reuters-deploys-elektron-at-nse)
  - An earlier direct low-latency BSE feed was linked to SEBI's 2008 move to allow direct market access. — [The Trade](https://www.thetradenews.com/thomson-reuters-fuels-low-latency-trading-on-nse)
- A domestic competitor in news and data: NSE Data & Analytics bought Cogencis Information Services, now Informist Media, in January 2021. — [Informist News app listing](https://apps.apple.com/app/id6477534229)

**Ownership and shareholding**
- LSEG's ownership dataset covers more than 70 countries and 70,000+ listed securities, with history from 1997. Its sources include regulatory filings, stock-exchange notices and mutual fund reports. India is not named. — [LSEG: company ownership information](https://www.lseg.com/en/data-analytics/financial-data/company-data/company-ownership-information-profiles); [LSEG Data Catalogue: Ownership](https://www.lseg.com/en/data-catalogue/company-data/ownership/ownership); [LSEG Ownership API](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/ownership-API)

**Reuters news**
- LSEG's Workspace content pages describe Reuters news and cross-asset coverage only in general terms. The search turned up nothing on India-specific news products. — [LSEG Workspace: data and content](https://www.lseg.com/en/data-analytics/search/workspace/data-and-content)

**Lipper (fund data)**
- Global coverage: 393,000+ active share classes in 80+ countries on one LSEG page, and 335,000+ on another. — [LSEG: Lipper fund price and performance](https://www.lseg.com/en/data-catalogue/funds/lipper-fund-data/fund-price-and-performance); [LSEG fund data](https://www.lseg.com/en/data-analytics/financial-data/fund-data)
- There is an India-specific mutual fund dataset priced via NSE. It covers fund prices, NAVs, identifiers, currency, share-class attributes, dates and distributions. — [LSEG Data Catalogue: Mutual fund, National Stock Exchange of India](https://www.lseg.com/en/data-catalogue/funds/pricing/mutual-fund-national-stock-exchange-of-india-nsei-ll)
- Lipper Fund Awards India:
  - 2018 awards. — [Lipper Alpha: Lipper Fund and Research Awards India 2018](https://lipperalpha.refinitiv.com/2018/05/lipper-fund-and-research-awards-india-2018)
  - 2019 Refinitiv awards: 28 awards in total (24 fund-classification awards, 3 group asset-class awards and 1 overall group award). Lipper said Indian fund NAVs grew strongly to the end of 2018 while net inflows fell sharply from 2017. — [Advisorkhoj, 2019](https://www.advisorkhoj.com/news/Mutual-Fund/Refinitiv-Announces-India-Lipper-Fund-Awards-2019-Winners)
  - A 2022 India awards event page exists. — [Lipper Alpha: Refinitiv Lipper Fund Awards India 2022](https://lipperalpha.refinitiv.com/upcoming-events/refinitiv-lipper-fund-awards-india-2022)
- Offshore "Equity India" categories appear in the 2025 LSEG Lipper awards in Hong Kong (Jupiter) and Singapore (Manulife MGF India Equity Fund, best fund over 10 years). — [Jupiter HK awards](https://www.jupiteram.com/hk/en/professional/about-jupiter/awards); [Manulife IM Singapore, LSEG awards 2025](https://www.manulifeim.com.sg/content/dam/wam/sg/lseg-awards-2025.pdf)

**Portfolio analytics in Workspace**
- Portfolio Analytics in Workspace gives "a view of performance, attribution and risk for multi-asset class portfolios". It includes cross-asset attribution, contribution, performance and style analysis, and finds the main drivers of absolute and relative performance at sector and security level. [Vendor claim] — [LSEG: portfolio management](https://www.lseg.com/en/data-analytics/asset-management-solutions/portfolio-management); [LSEG Workspace for analysts and portfolio managers](https://lseg.com/en/data-analytics/asset-management-solutions/workspace-analysts-portfolio-managers)
- The wealth-adviser version adds historical return attribution, financial risk factors, dashboards, curated alerts and "Watchlist Pulse". [Vendor claim] — [LSEG Workspace for wealth advisors](https://www.lseg.com/en/data-analytics/wealth-management-solutions/automate-advisor-workflow/workspace-wealth-advisors)
- The MSCI Barra Optimizer in Workspace uses MSCI's multi-asset risk model for portfolio construction. [Vendor factsheet] — [LSEG Workspace portfolio manager factsheet](https://www.lseg.com/content/dam/data-analytics/en_us/documents/fact-sheets/final_re1570059_ws_ia_rpm_factsheet_portfolio_manager_a4_v6_web.pdf)
- The move from Eikon to Workspace is described as "an upgrade but a rocky journey". [Low-quality source] — [rfp.wiki: Bloomberg vs Refinitiv](https://www.rfp.wiki/investment/bloomberg/refinitiv)

### Inferences
- The LSEG estimates network explicitly includes local brokers, and LSEG-compiled consensus appears in news copy on Indian stocks. I/B/E/S therefore actively covers Indian large and mid caps. Small-cap depth is not verified.
- Workspace Portfolio Analytics looks less specialised than FactSet PA. LSEG publishes no model counts and names no Brinson or factor-attribution variants, and its risk work leans on hosted MSCI tools. For Indian managers, LSEG's distinctive strengths are I/B/E/S and StarMine, Reuters news, and Lipper fund data, not attribution.
- No India Lipper awards were found after 2022. The India-specific Lipper presence may have shrunk, but this is not confirmed.

### Gaps
- No India-specific I/B/E/S figures were found (number of Indian companies covered, Indian contributors, history start). StarMine India coverage was not found either.
- The size of Reuters' India bureau and any India-specific news product were not found.
- How deeply LSEG covers Indian ownership data was not confirmed: promoter holdings, pledges, and quarterly shareholding patterns from BSE/NSE.
- The number of Indian mutual funds covered by Lipper was not found.
- The specific attribution models in Workspace were not found.
- No India pricing was found.

## 3. S&P Global Market Intelligence: Capital IQ / Capital IQ Pro coverage of India, S&P estimates, the CRISIL relationship, and portfolio analytics

### Takeaway
Capital IQ Pro's India strength is research and estimates aggregation. As of March 2024, 60 Indian research providers were in S&P's Investment Research collection, including HDFC Securities, Motilal Oswal, Kotak Securities, ICICI Securities and Spark Capital. Some providers' estimates are available to approved clients.

S&P Capital IQ Estimates covers 20,000+ companies. Visible Alpha, now integrated into Capital IQ Pro (March 2025), covers 7,500+.

S&P Global owns about 66.6% of CRISIL. CRISIL's Indian mutual fund rankings, fund database and portfolio-analysis services are sold through Crisil Intelligence. I found no evidence that they are built into Capital IQ Pro; the 2015 evidence covers only CRISIL ratings research appearing on the Capital IQ desktop.

Capital IQ Pro's Portfolio Analytics add-on offers grouping-based attribution (allocation versus selection), factor groupings, the Alpha Factor Library and risk measures.

### Cited Findings
**Capital IQ Pro coverage**
- The launch release described coverage of "sixty-two thousand public and eighteen million private companies". [Dated] — [S&P Global MI launches S&P Capital IQ Pro](https://spglobal.com/marketintelligence/en/media-center/press-release/sp-global-market-intelligence-launches-sp-capital-iq-pro)
- Later Capital IQ Pro material gives 109,000+ public companies (49,000+ active with current financials) and 54M+ private companies (14M+ with financials). [Vendor claim] — [Capital IQ Pro document hosted by IIM Sambalpur library (uploaded 30 Mar 2026)](https://library.iimsambalpur.ac.in/uploads/usermanuals/20260330212818_55664729_Capital_IQ_Pro__SPGMI_.pdf)
- 2015 Asia-Pacific expansion:
  - Desktop subscribers got research from 400+ sell-side, industry and specialty firms covering 28,000+ APAC companies.
  - The credit sources included "CRISIL Ratings, a division of McGraw Hill Financial (India)".
  - S&P said: "Our coverage of ASEAN countries as well as India, South Korea, Japan and China only continues to deepen."
  - [Dated: 2015] — [S&P press release, 2 Jun 2015](https://press.spglobal.com/2015-06-02-S-P-Capital-IQ-Expands-APAC-Third-Party-Sell-Side-and-Credit-Ratings-Research-on-its-Desktop)
- HDFC Securities research added (blog dated 1 March 2024):
  - HDFC Securities is the 60th Indian research provider in the S&P Global Investment Research collection, "along with Motilal Oswal, Kotak Securities, ICICI Securities, Spark Capital".
  - HDFC Securities analysts cover more than 200 Indian companies.
  - Access is either real-time for approved clients or through an Aftermarket Research licence. Approved clients also get HDFC Securities' earnings estimates.
  - The whole collection holds 40M+ reports from 1,800+ banks and independent research providers.
  - Source: [S&P Global MI: HDFC Securities research now available through Capital IQ Pro](https://www.spglobal.com/market-intelligence/en/news-insights/research/hdfc-securities-investment-research-now-available-through-sp-capital-iq-pro)
- In 2014 S&P added 83 aftermarket research providers from 30 countries, expanding coverage of Latin America and Asia. [Dated] — [S&P MI: 83 new aftermarket research providers](https://pages.marketintelligence.spglobal.com/Investment-Research-83-New-Aftermarket-Research-Providers-Available-Expanded-Coverage-in-Latin-America-and-Asia.html)
- June 2025 platform update: GenAI-powered Document Intelligence and charting, and headcount and people data for private companies. India is not mentioned. — [S&P press release, 25 Jun 2025](https://press.spglobal.com/2025-06-25-S-P-Global-Market-Intelligence-Unveils-GenAI-Powered-Enhancements-to-Capital-IQ-Pro-and-Expands-Insights-in-Private-Markets-and-Energy-Transition)
- One user review says "for some of the small private companies, there is no data available". [Single user review] — [G2 reviews: S&P Global Market Intelligence](https://www.g2.com/products/s-p-global-market-intelligence/reviews)

**S&P estimates**
- S&P Capital IQ Estimates covers 20,000+ companies (60,000+ including history). Visible Alpha covers 7,500+ companies, with "200+ of the world's leading banks and research houses" contributing. [Vendor claim] — [S&P Global MI: Estimates](https://spglobal.com/market-intelligence/en/solutions/products/estimates)
- Visible Alpha was launched on the Capital IQ Pro platform on 25 March 2025. — [S&P press release, 25 Mar 2025](https://press.spglobal.com/2025-03-25-S-P-Global-Market-Intelligence-Launches-Visible-Alpha-on-S-P-Capital-IQ-Pro-Platform)
- S&P's own guidance on how estimates vendors differ:
  - Vendors define an "active contributor" differently.
  - "Coverage by small regional contributors may differ amongst estimates vendors, whereas bulge bracket coverage tends to be consistent among the major vendors."
  - Brokers that mainly provide automated forecasts are generally excluded.
  - Source: [S&P Global MI: estimates expansion](https://www.spglobal.com/market-intelligence/en/solutions/resources/estimates-expansion)
- Downstream use: Simply Wall St attributes its Indian stock data, including analyst consensus and price targets, to S&P Global Market Intelligence (example: Motilal Oswal Financial Services). — [Simply Wall St: Motilal Oswal Financial Services](https://simplywall.st/stocks/in/diversified-financials/nse-motilalofs/motilal-oswal-financial-services-shares/information)

**Portfolio analytics**
- Capital IQ Pro Portfolio Analytics [Vendor claim]:
  - Historical or intraday performance and risk analysis, built on S&P Capital IQ financials, estimates and market data.
  - Optional ESG and climate data, plus "proprietary risk and Alpha Factor Library models".
  - Attribution by industry, geography, currency or factor groupings, showing whether top-down allocation or bottom-up selection drove returns.
  - Forward-looking risk: volatility, liquidity, and environmental and regulatory risks.
  - Holdings can be loaded ad hoc or straight from a custodian or accounting system.
  - Comparison against index benchmarks and against mutual fund and ETF holdings.
  - A chart and table library, with ad hoc or scheduled batch reports.
  - Sources: [S&P Marketplace: Portfolio Analytics](https://www.marketplace.spglobal.com/en/solutions/portfolio-analytics-%2814c14734-29f8-4f56-af06-2437187f438d%29); [S&P MI: Streamline your investment process with Portfolio Analytics](https://pages.marketintelligence.spglobal.com/Streamline-Your-Investment-Process-with-Portfolio-Analytics.html)
- Waters Rankings named S&P the best performance measurement and attribution system provider in 2015 (S&P Capital IQ, where the module was an add-on to the flagship platform) and in 2022 (S&P Global MI). — [WatersTechnology 2015](https://waterstechnology.com/node/2420502); [WatersTechnology 2022](https://waterstechnology.com/node/7948731)
- A separate 2021 alliance added CloudAttribution's fixed-income and multi-asset attribution to S&P's thinkFolio platform. This is a different product from the Capital IQ Pro module. — [S&P/IHS Markit: thinkFolio–CloudAttribution](https://ssl.ihsmarkit.com/marketintelligence/en/mi/research-analysis/thinkFolio-CloudAttribution.html)

**CRISIL (an S&P Global company)**
- At 31 December 2023, S&P Global owned 66.65% of CRISIL through subsidiaries including S&P India LLC and S&P Global Asian Holdings Pte Ltd. — [CRISIL Annual Report 2023, p.306](https://www.crisil.com/crisil-annual-report-flipbook/crisil-annual-report2023/files/basic-html/page306.html)
- The promoter holding was 66.64% in every quarter from December 2024 to December 2025. [3rd-party tracker] — [Torus Digital: CRISIL shareholding](https://torusdigital.com/stocks/crisil-ltd-share-price)
- CRISIL Ratings Ltd is a subsidiary of CRISIL Ltd, "an S&P Global company". — [CRISIL Ratings shareholding pattern](https://integraliq.crisil.com/content/dam/crisil/generic-images1/our-businesses/ratings/regulatory-disclosure-highlighted-policies/highlighted-policies/shareholding-pattern%20of-crisil-ratings-ltd.pdf)
- CRISIL mutual fund research, sold through Crisil Intelligence:
  - The Crisil Mutual Fund Ranking has run since June 2000.
  - It combines NAV-based and portfolio-based attributes: risk-adjusted returns, concentration, liquidity and asset quality.
  - Within each peer group, Rank 1 is the top 10th percentile and Rank 2 the next 20th percentile.
  - CRISIL also offers customised rankings for wealth managers, distributors and private banks, plus a mutual fund tracker and fund due diligence.
  - Its Mutual Fund Database serves AMCs and distributors.
  - Monthly factsheets go to AMCs, life insurers and distributors.
  - "PF Analytics" provides portfolio analysis and valuation for pension and provident funds.
  - [Vendor claim] — [Crisil Intelligence: mutual fund research](https://www.crisil.com/en/home/our-businesses/crisil-intelligence/india-research/capital-market/mutual-fund-research.html); [Crisil: mutual fund ranking](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/mutual-fund-research/mutual-fund-ranking.html); [Crisil Intelligence: mutual fund research (alt page)](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/mutual-fund-research.html)
- The CRISIL Fund Analyser lets clients view, compare, monitor and run custom queries on 6,500+ mutual fund schemes. [Vendor claim; date unclear] — [Crisil Intelligence: mutual fund research](https://www.crisil.com/en/home/our-businesses/crisil-intelligence/india-research/capital-market/mutual-fund-research.html)
- Crisil Intelligence offers "granular portfolio analysis services for asset managers, financial intermediaries, retirement funds and institutional investors". [Vendor claim] — [Crisil Intelligence: institutional investors](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/institutional-investors.html)
- CRISIL's Global Research & Risk Solutions arm lists a "portfolio risk management" offering under quantitative services. The page was surfaced but its content was not retrieved. — [CRISIL GR&RS: portfolio risk management](https://crisil.com/content/crisilcom/en/home/our-businesses/global-research-and-risk-solutions/our-offerings/quantitative-services/portfolio-risk-management.html)
- CRISIL Independent Equity Research: of 109 companies covered, 51 had no analyst coverage before the CRISIL report. [Dated, c. 2010–12] — [Moneylife](https://www.moneylife.in/article/investor-behaviour-shifts-with-usage-of-independent-equity-research-crisil/20017.html)

### Inferences
- S&P has two separate India assets:
  - Capital IQ Pro, a global platform with strong aggregation of Indian broker research and estimates.
  - CRISIL, a majority-owned domestic franchise covering mutual fund rankings, fund databases, ratings and portfolio-analysis services.
- Nothing found shows that the two are integrated for buy-side users, for example CRISIL fund analytics inside Capital IQ Pro. An Indian AMC would probably license them separately.
- Capital IQ Pro's Portfolio Analytics is best described as grouping-based (Brinson-style) attribution plus factor and risk add-ons. Compared with FactSet, less is published about named commercial factor risk models (Barra or Axioma) being hosted.

### Gaps
- The number of Indian listed companies covered in Capital IQ Pro, and how far down the cap scale, was not found.
- The number of Indian companies with S&P or Visible Alpha consensus was not found.
- Whether CRISIL ratings and research are still carried on Capital IQ Pro in 2026 is unknown. The only evidence is from 2015.
- CRISIL's analytical-centre support for S&P Global Ratings was not researched because the search budget ran out.
- The status of thinkFolio in 2026 is unknown.
- No Indian adopters of Capital IQ Pro Portfolio Analytics were found.

## 4. Morningstar Direct: use by Indian AMCs and distributors for fund-peer analysis, holdings-based style analysis, and Indian fund and stock coverage (brief)

### Takeaway
Morningstar Direct offers user-defined peer groups, holdings-based style analysis (style boxes) and returns-based style analysis. Morningstar India categorises funds by what they actually hold. The only India adoption figure found is old and small: "around 30 subscribers in India" (AMCs and wealth managers), undated and probably about 2017–18. Third-party pricing puts the first licence at about $18,000 a year.

### Cited Findings
- In 2018 Morningstar described Direct as an investment analysis platform for asset-management and financial-services professionals. It combines Morningstar data and institutional research, private and third-party content, analytics and productivity tools. [Dated: 2018] — [Morningstar India: Power your research with Morningstar Direct](https://www.morningstar.in/library/article.aspx?p=47831)
- Direct's features include peer analysis on user-defined peer groups built from portfolio, risk, operations and performance data, holdings-based style analysis, and returns-based style analysis. [Vendor documentation] — [Morningstar Direct help: Coverage Reports Presentations](https://gladmainnew.morningstar.com/directhelp/Coverage_Reports_Presentations.pdf)
- Morningstar's methodology paper:
  - Holdings-based analysis classifies a portfolio by the characteristics of the securities it holds.
  - Returns-based analysis compares the fund's returns with style indices.
  - Style analysis is also used to build peer groups and choose style-specific benchmarks.
  - Source: [Morningstar Direct help: Returns vs Holdings paper](https://gladmainnew.morningstar.com/directhelp/Returns_vs_HoldingsPaper.pdf)
- A Morningstar India executive said AMCs and wealth-management companies subscribe to Direct: "We have around 30 subscribers in India." [Undated; likely around 2017–18] — [Cafemutual interview with Morningstar India](https://cafemutual.com/news/industry/9518-use-star-ratings-as-a-first-level-check-but-dont-blindly-follow-them-aditya-agarwal-morningstar)
- Ratings rules (same Cafemutual interview):
  - A star rating needs a 3-year track record and enough funds in the category to form a peer group.
  - Analyst ratings use five pillars: People, Process, Parent, Performance and Price.
- A fund without an analyst-assigned peer group cannot receive a Medalist Rating; one Morningstar India fund page shows this case. — [Morningstar India fund page example](https://morningstar.in/mutualfunds/f00001jk0v/parag-parikh-dyn-ast-allc-dir-gr/overview.aspx)
- A 2018 Mumbai event covered comparing funds across peer groups using risk parameters and ratios. — [Outlook Money: Picking the right mutual funds](https://www.outlookmoney.com/invest/picking-the-right-mutual-funds-2542)
- Morningstar India fund pages show the Morningstar category (for example "India Fund Small-Cap"), investment style, expense ratio, asset allocation and holdings. An editor's reply on one page said Morningstar categorises by actual portfolio positioning, not by the AMC's label: the small/mid-cap category requires at least 65% of assets in small and mid caps. The exact page carrying the reply was not pinned down. — [Morningstar India fund page example](https://morningstar.in/mutualfunds/f00000pcza/abc/overview.aspx); [Morningstar India fund page example 2](https://morningstar.in/mutualfunds/f00000zc8i/kotak-bluechip-direct-reinvestment-of-income-distribution-cum-cap-wdrl/overview.aspx)
- The SPIVA India scorecard (S&P Dow Jones Indices) uses Morningstar data. Over the five years to June 2017, style consistency was 36.65% for Indian large-cap funds and 49.25% for mid/small-cap funds. [Dated: 2017] — [Indexology blog: style drift of active funds domiciled in India](https://www.indexologyblog.com/2017/10/18/style-drift-of-active-funds-domiciled-in-india/)
- Morningstar Direct licences worldwide:
  - Up 0.6% in Q1 2025. — [Morningstar Q1 2025 results](https://businesswire.com/news/home/20250429168139/en/Morningstar-Inc.-Reports-First-Quarter-2025-Financial-Results)
  - An aggregator gives 18,799 (Q1), 18,810 (Q2) and 18,771 (Q3 2025), flat year on year in Q3. [3rd-party; unverified] — [Fintool MORN Q3 2025](https://fintool.com/app/research/companies/MORN/earnings/Q3%202025); [Morningstar Q3 2025 results](https://www.businesswire.com/news/home/20251028378573/en/Morningstar-Inc.-Reports-Third-Quarter-2025-Financial-Results)
- Pricing: see section 6.

### Inferences
- In India, Morningstar Direct looks like a niche tool: dozens of subscribers, not hundreds, at least as of the last data point. The domestic fund-research stack (CRISIL rankings and Fund Analyser, Value Research, ACE MF) is the low-cost default.
- Direct's distinctive value for Indian AMCs is global-standard peer groups, holdings-based style boxes and Medalist ratings. Distributors and wealth managers mainly consume Morningstar's ratings, not the Direct seat.

### Gaps
- No 2025–26 count of Indian Direct subscribers was found.
- No count was found of Indian schemes or stocks covered in Direct.
- No India-specific pricing was found.
- No current documentation was found on how Direct maps Morningstar categories onto SEBI scheme categories.

## 5. Where Indian managers get consensus earnings estimates, and how many analysts typically cover large-, mid- and small-cap Indian stocks

### Takeaway
There are four kinds of source:
- **Global consensus databases:** I/B/E/S (22–23k companies, including local brokers), FactSet Estimates (16–19k), S&P Capital IQ Estimates / Visible Alpha (20k+ / 7.5k+), and Bloomberg consensus. Brokers cite Bloomberg consensus in India; for example, Nomura used it for the BSE 200+ universe in August 2026.
- **Brokers' own aggregate trackers:** JM Financial, Motilal Oswal and Elara publish Nifty EPS revision tracking.
- **Domestic aggregators:** Trendlyne Forecaster, which covers about 900 companies.
- **Retail portals:** such as Investing.com.

Coverage counts in the sources: about 26–44 analysts for top large caps, about 15–17 for large new listings and mid caps that have gained coverage, and none for the large majority of roughly 5,000–6,000 listed stocks.

### Cited Findings
**Global vendors (scale)**
- I/B/E/S: 22,000+ active companies, 950+ contributors "from large global houses to regional and local brokers". — [LSEG I/B/E/S Broker Estimates](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates)
- FactSet: 16,000–19,000+ active companies and 800–1,200+ contributors, depending on the document. — [FactSet Estimates OnDemand](https://go.factset.com/hubfs/Website_Downloads/Statistical%20Package%20Integration/Docs%203.0/estimates-ondemand.pdf); [FactSet corporate services brochure](https://go.factset.com/hubfs/Website/Resources%20Section/Brochures/solutions-for-corporate-services-brochure.pdf)
- S&P: 20,000+ companies in Estimates; Visible Alpha 7,500+ companies with 200+ contributors. — [S&P Global MI: Estimates](https://spglobal.com/market-intelligence/en/solutions/products/estimates)
- HDFC Securities' estimates are available to approved S&P clients, and HDFC Securities covers 200+ Indian companies. — [S&P Global MI blog, Mar 2024](https://www.spglobal.com/market-intelligence/en/news-insights/research/hdfc-securities-investment-research-now-available-through-sp-capital-iq-pro)
- An Indian glossary says domestic brokers such as Kotak Institutional Equities, Motilal Oswal, ICICI Securities and Edelweiss feed global consensus databases. It adds that for smaller companies, thin coverage means the consensus "may not reflect a genuine market view". [Secondary source] — [equitiesindia.com glossary: consensus estimate](https://equitiesindia.com/glossary/consensus-estimate)

**Bloomberg consensus in Indian use**
- In August 2026 Nomura reported that year to date, Bloomberg consensus estimates for the BSE 200+ universe had been revised down 3.7% for FY27, while FY28 was largely unchanged. — [Business Today, 19 Aug 2026](https://www.businesstoday.in/markets/stocks/story/nifty-at-25900-by-march-2027-nomura-keeps-index-target-shares-key-themes-to-watch-549936-2026-08-19)
- A Bloomberg training manual defines the consensus as the mean of sell-side analyst estimates. [Student manual, not Bloomberg's own methodology] — [WU Vienna: Bloomberg forecasts manual](https://library.wu.ac.at/bib/fit4research/wp-content/uploads/2024/02/Forecasts_manuals_Bloomberg.pdf)

**Brokers' own aggregate tracking**
- JM Financial's monthly tracker: in August 2026, 23 Nifty companies (46%) had FY27 EPS upgrades and 17 had cuts. — [Business Today, 3 Sep 2026](https://www.businesstoday.in/markets/stocks/story/itc-tata-steel-ael-see-highest-eps-cuts-in-august-grasim-leads-upgrades-targets-553137-2026-09-03)
- Motilal Oswal's Q1FY27 preview: Nifty EPS of ₹1,225 for FY27 (+15%) and ₹1,422 for FY28 (+16%). — [Swastika blog citing Motilal Oswal](https://www.swastika.co.in/blog/tcs-share-price-and-sector-outlook-motilal-oswal-q1fy27-earnings-preview)
- Elara Capital, January 2026: Nifty EPS of ₹1,281 for FY27, about 17% growth. — [Business Standard, 14 Jan 2026](https://www.business-standard.com/amp/markets/news/elara-pegs-fy27-nifty-target-at-30-000-sees-earnings-driven-gains-126011400901_1.html)

**Domestic aggregator: Trendlyne Forecaster**
- Coverage:
  - Quarterly and annual analyst estimates for about 900 Indian companies, according to the help centre. A separate FAQ page says about 3,000.
  - It excludes smaller companies because "the top 900 companies contribute to 95% of the market".
  - Metrics: revenue, net profit, EPS, dividend, cash flows, capex, interest expense, and upward and downward revisions.
  - Sources: [Trendlyne help: forecaster/analyst estimates](https://help.trendlyne.com/support/solutions/articles/84000383175-what-are-forecaster-or-analyst-estimates-); [Trendlyne FAQ](https://faq.trendlyne.com/support/solutions/articles/84000391872-what-are-forecaster-or-analyst-estimates-)
- Trendlyne's customers include ICICI Securities, Kotak Securities, 5paisa and Motilal Oswal. It raised a $1.8M Series A led by IIFL Fintech Fund. — [Entrackr](https://entrackr.com/?p=157112); [Craft.co: Trendlyne](https://craft.co/trendlyne)

**Analyst-count examples by size**
- Top large caps:
  - In April 2018, Bloomberg counted 44 analysts covering both Infosys and TCS; 38 rated Infosys a buy. [Dated: 2018] — [Bloomberg, 25 Apr 2018](https://www.bloomberg.com/news/articles/2018-04-25/infosys-buy-calls-mount-even-as-tcs-enters-100-billion-club)
  - Reliance Industries: "Strong Buy" from 28 analysts (26 buy, 1 sell), average target ₹1,673, based on a poll of the past 3 months. The page date is not shown. — [Investing.com: Reliance consensus estimates](https://www.investing.com/equities/reliance-industries-consensus-estimates)
- Large new listing: LG Electronics India, 15 analysts (LSEG). — [Stockopedia](https://www.stockopedia.com/share-prices/lg-electronics-india-NSI:LGEINDIA/news/lg-electronics-india-rises-after-jefferies-initiates-with-apos-buy-apos-019e69f8-f6b2-77fc-97c1-200a871871d2/)
- Mid caps gaining coverage: by June 2021, SBI Cards went from 4 brokerages to 17 in about a year, and more than three dozen BSE 500 companies added at least five analysts (Bloomberg data). [Dated: 2021] — [Business Standard, 24 Jun 2021](https://www.business-standard.com/article/markets/on-the-radar-analysts-expand-coverage-amid-sharp-stock-market-rally-121062400017_1.html)
- The long tail:
  - "Over 5300 of the 6000-odd stocks listed in India are not tracked by any equity analysts." [Undated] — [Value Research: A basic disconnect](https://www.valueresearchonline.com/stories/18224/a-basic-disconnect/)
  - "80 per cent traded companies had no analyst coverage", according to Crisil. The URL date code points to May 2010; the search summary gave January 2013. Either way the figure is more than 10 years old. — [Business Standard: NSE takes lead in stirring inactive stocks](https://www.business-standard.com/amp/article/markets/nse-takes-lead-in-stirring-inactive-stocks-110052300038_1.html)
  - About 90% of more than 6,000 listed companies had no published research, in the context of the CRISIL independent-research programme. [Dated, c. 2010–12; taken from a search excerpt] — [Integrity Research](https://www.integrity-research.com/uncovered-stocks-to-get-research-coverage/)
- Micro caps are "followed by very few, if any, sell-side analysts". — [equitiesindia.com glossary: microcap](https://equitiesindia.com/glossary/microcap-stock)
- Under SEBI's categorisation, small caps are stocks ranked 251st and below by market cap. — [ClearTax: small cap stocks](https://cleartax.in/s/small-cap-stocks)

### Inferences
- A typical coverage profile, inferred from the scattered data points above:
  - Nifty 50 / top-100 stocks: about 25–45 analysts.
  - Large new listings and well-followed mid caps: about 10–20.
  - Typical mid caps (ranks 101–250): roughly 5–15, with wide spread.
  - Small caps (251+): mostly 0–5.
  - The remaining roughly 5,000 listed names: none.
  - Usable consensus therefore exists for roughly 900–1,000 Indian companies, which is consistent with Trendlyne's stated scope.
- Indian institutions probably use Bloomberg consensus and LSEG I/B/E/S (via Workspace) as their main consensus sources. FactSet and S&P serve clients already on those platforms. Brokers' Nifty-aggregate trackers and Trendlyne serve smaller PMS/AIF teams. This is not verified by any survey.

### Gaps
- No vendor publishes the number of Indian companies with consensus or the number of Indian contributors.
- No systematic 2025–26 distribution of analyst coverage by market-cap bucket was found. The figures above are scattered examples, several of them dated.
- Bloomberg's own consensus (BEst) methodology and contributor count were not retrieved.
- How Trendlyne sources its broker estimates is unconfirmed.

## 6. Pricing: typical seat or licence costs for FactSet, LSEG Workspace, Capital IQ Pro and Morningstar Direct (dated), and any India-specific pricing

### Takeaway
None of the vendors publishes list prices.
- **Capital IQ Pro:** the only primary-source price found is a UK government G-Cloud schedule from December 2025: £45,000 a year for up to 5 users, £63,000 for up to 10 and £250,000 for up to 100, at a time-limited public-sector discount.
- **FactSet:** about $12k–$40k per user per year.
- **LSEG Eikon/Workspace desktop:** about $15k–$22k per user per year.
- **Capital IQ Pro (third-party estimates):** about $10k–$50k per user per year.
- **Morningstar Direct:** about $18k for the first user and $9.8k for each additional user.
- No India-specific (rupee) pricing was found.

All of the third-party figures are estimates of varying quality, and some contradict each other.

### Cited Findings
**FactSet**
- A median contract of $25,160 a year, based on 4 verified purchases, and a reported range of $12,000–$40,000 per user per year. The same site lists a "FactSet Workstation Basic $333/user/year", which is implausible. [3rd-party est., 2026; Low-quality source] — [CostBench: FactSet pricing 2026](https://costbench.com/software/financial-data-terminals/factset/)
- About $10,000–$20,000 per user per year for typical deployments. [3rd-party est.] — [multiples.vc: FactSet alternatives](https://multiples.vc/compare/factset-alternatives)
- About $12,000 a year for the full product (older guide). Other excerpts give "starts at $4,000/year" and "$12,000–50,000/user/year depending on modules". [3rd-party est.] — [Wall Street Prep: Bloomberg vs Capital IQ vs FactSet vs Eikon](https://wallstreetprep.com/knowledge/bloomberg-vs-capital-iq-vs-factset-vs-thomson-reuters-eikon); [rfp.wiki: FactSet vs Bloomberg](https://www.rfp.wiki/investment/factset/bloomberg-terminal)
- Implementation, exchange fees and specialised modules often sit outside the headline seat price. [3rd-party] — [CostBench: FactSet negotiation](https://costbench.com/software/financial-data-terminals/factset/negotiation/)

**LSEG Eikon / Workspace**
- Full desktop $15,000–$22,000 a year; web entry tier about $3,600 a year. An older CostBench page gives Desktop Premium at $21,960 and Desktop Standard at $15,000 per user per year. Newer 2026 CostBench pages say $300, $1,250 and $1,830, which contradicts this and is treated as unreliable. CostBench also estimates about $100,000 a year for a 5-person research team including Datastream. [3rd-party est.; Low-quality source] — [CostBench: Bloomberg vs Refinitiv Eikon](https://costbench.com/compare/bloomberg-terminal-vs-refinitiv-eikon/); [CostBench: Refinitiv Eikon](https://costbench.com/software/financial-data-terminals/refinitiv-eikon); [CostBench calculator](https://costbench.com/software/financial-data-terminals/refinitiv-eikon/calculator/)
- Vendr: LSEG purchases of $281–$3,414 a year, median $865, across 14 purchases. These are probably add-ons or partial licences, not full desktop seats. [3rd-party] — [Vendr: Refinitiv/LSEG](https://www.vendr.com/marketplace/refinitiv)
- Eikon web version: about $3,600–$6,000 a year, with limited features and delayed data. [3rd-party est.] — [Wall Street Prep](https://wallstreetprep.com/knowledge/bloomberg-vs-capital-iq-vs-factset-vs-thomson-reuters-eikon)

**S&P Capital IQ Pro**
- UK G-Cloud 14 pricing document (December 2025), annual desktop prices by seat band: up to 5 users £45,000, up to 10 users £63,000, up to 100 users £250,000. This was a time-limited discount for UK public-sector clients that ended 31 December 2025. [Primary vendor filing] — [UK G-Cloud 14 S&P pricing document](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-14/documents/716762/461639550806531-pricing-document-2025-12-08-1330.pdf)
- Third-party figures [3rd-party est.]:
  - $10,000–$50,000+ per user per year depending on modules and seats.
  - Another estimate: $13,000–$30,000+.
  - Procurement data: contracts of about $14,800–$215,000 a year, median about $53,000.
  - Sources: [CostBench: S&P Capital IQ Pro](https://costbench.com/software/financial-data-terminals/sp-capital-iq/); [multiples.vc: Capital IQ alternatives](https://multiples.vc/compare/capital-iq-alternatives)
- CostBench claims an April 2026 cut to "$2.1K/user/year" for the top tier. CostBench's own FAQ warns that such tier names and prices "are not sourced from any official S&P publication". [Unreliable] — [CostBench changelog, Apr 2026](https://costbench.com/changelog/sp-capital-iq-price-decrease-2026-04/)

**Morningstar Direct**
- First user licence $18,000 a year, second $11,500, each additional $9,800. [3rd-party est.] — [FitGap: Morningstar Direct](https://us.fitgap.com/products/morningstar-direct)
- Pricing varies with the number of users and the scope of data. — [Gartner Peer Insights: Morningstar Direct](https://www.gartner.com/reviews/product/morningstar-direct)
- Average spend across all Morningstar products, from 160 customers: $40,107 a year for SMBs and $224,340 for enterprises. [3rd-party] — [SpendHound: Morningstar pricing](https://www.spendhound.com/marketplace/morningstar-pricing)

**Bloomberg, for reference**
- About $27,660 a year for a single seat on a 2-year lease, and $24,240 per seat for 2 or more. — [Wall Street Prep](https://wallstreetprep.com/knowledge/bloomberg-vs-capital-iq-vs-factset-vs-thomson-reuters-eikon)
- Another estimate: about $32,000 single and $28,320 multi-seat. — [ThePricer](https://www.thepricer.org/how-much-does-bloomberg-terminal-cost/)

**India-specific**
- No rupee or India price was found. The one Indian public-sector disclosure found (DICGC, April 2026) lists the contract value as "N.A.". — [DICGC: work issued on nomination basis](https://www.dicgc.org.in/sites/default/files/2026-04/work-issued-on-nomination-basis.pdf)

### Inferences
- At the UK public-sector discount, the 5-seat Capital IQ Pro band works out to about £9,000 per seat (£45,000 ÷ 5), which is at the low end of the third-party range. Commercial buyers probably pay more.
- A small Indian PMS/AIF team of 3–5 people would probably face roughly $40k–$120k a year for one global platform, before any exchange fees. This is a rough inference from the per-seat ranges above; no rupee conversion is attempted because no India price was found. Cost is plausibly a main reason smaller Indian managers lean on domestic databases and broker research, but no source says so directly.

### Gaps
- There is no official list pricing for any of the vendors.
- No India-specific pricing was found: rupee contracts, GST treatment, or any discounts for Indian AMCs.
- No current Workspace tier names or prices were found.
- The figures in the G-Cloud document could not be confirmed by reading the full document (DNS failure).

## 7. Adoption in India: which vendors Indian AMCs, PMS, AIFs, insurers and FPIs are reported to use, and any market-share figures

### Takeaway
No India-specific market-share data exists in public sources. Globally, Burton-Taylor ranks Bloomberg first (about 32.5% in 2018), then Refinitiv/LSEG, then S&P Global MI. Asia is about 18% of a $37.3B market (2022).

India-specific evidence is anecdotal:
- A deposit-insurance body, DICGC (an RBI subsidiary), uses Refinitiv, Bloomberg and Cogencis on a nomination basis (April 2026).
- Morningstar Direct reported about 30 Indian subscribers.
- S&P counts 60 Indian research providers in its research collection.
- A global asset manager's Mumbai attribution team asks for FactSet, Aladdin and Bloomberg experience.
- Indian AMC job ads seen did not name data tools.
- Domestic databases (ACE Equity, Capitaline, CMIE Prowess) are widely licensed.

### Cited Findings
- Burton-Taylor, 2022 [Dated]:
  - Global spend on financial market data and news rose 4.7% to a record $37.3B.
  - Asia's share was 18.1%. Asian spend grew 1.8%, against 8.3% in the Americas.
  - Bloomberg holds the largest share, followed by Refinitiv and S&P Global MI.
  - S&P Global MI grew fastest in 2022, followed by Morningstar, Moody's Analytics and FactSet.
  - Sources: [Markets Media: market data spend reaches record $37.3bn](https://www.marketsmedia.com/market-data-spend-reaches-record-37-3bn); [TP ICAP Burton-Taylor release (PDF)](https://tpicap.com/tpicap/sites/g/files/escbpb106/files/2023-04/GLOBAL%20SPEND%20ON%20FINANCIAL%20MARKET%20DATA%20TOTALS%20A%20RECORD%20%2437.3%20BILLION%20IN%202022%2C%20RISING%204.7_%20ON%20DEMAND%20FOR%20RESEARCH%2C%20PRICING%2C%20REFERENCE%20AND%20PORTFOLIO%20MANAGEMENT%20DATA%20-%20.pdf)
- Burton-Taylor, 2021: Asia's share was 18.7%, with 6.6% growth. [Dated] — [Markets Media: global spending reaches record](https://articles.marketsmedia.com/global-spending-on-financial-market-data-reaches-record)
- Bloomberg's share was 32.5% in 2018, down from 33.2% in 2017. [Dated] — [Talking Biz News](https://talkingbiznews.com/1/bloomberg-maintains-market-share-lead-over-reuters/)
- FactSet had about 2.5% of the global market in 2008 (Burton-Taylor, cited by Jinfo). [Dated] — [Jinfo](https://jinfo.com/go/blog/66941)
- FactSet's Asia-Pacific ASV was $240.1M in Q3 FY25, with no India breakout. — [FactSet Q3 FY2025 results (Barchart)](https://www.barchart.com/story/news/32998235/factset-reports-results-for-third-quarter-2025)
- DICGC (Deposit Insurance and Credit Guarantee Corporation), April 2026: "utilises the services of data agencies for financial markets data, insights, and analytics", naming Refinitiv India Pvt Ltd, Bloomberg Data Services (India) Pvt Ltd and Cogencis Information Services. The work is issued on a nomination basis because "there are no reasonable substitute/alternatives". — [DICGC disclosure (Apr 2026)](https://www.dicgc.org.in/sites/default/files/2026-04/work-issued-on-nomination-basis.pdf)
- Morningstar Direct: "around 30 subscribers in India" (AMCs and wealth managers). [Undated] — [Cafemutual](https://cafemutual.com/news/industry/9518-use-star-ratings-as-a-first-level-check-but-dont-blindly-follow-them-aditya-agarwal-morningstar)
- CRISIL's Mutual Fund Ranking is "highly popular among investors, intermediaries, and asset management companies". [Vendor claim] — [Crisil Intelligence: mutual fund research](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/mutual-fund-research.html)
- S&P's Investment Research collection had 60 Indian research providers as of March 2024. — [S&P Global MI blog](https://www.spglobal.com/market-intelligence/en/news-insights/research/hdfc-securities-investment-research-now-available-through-sp-capital-iq-pro)
- Morgan Stanley Investment Management's GPAR team in Mumbai (performance attribution) prefers "experience in using FactSet, Blackrock Aladdin, Bloomberg, and other performance attribution vendor systems". This is a global manager's India operation, not a domestic AMC. — [DE Jobs listing: Analyst/Associate GPAR, Mumbai](https://militaryspouse.dejobs.org/mumbai-ind/analyst-associate-gpar-investment-management/C155BB70FBE94E9CB5B3B7CD5CD747F6/job)
- Equity research analyst ads for Indian AMCs did not name any data tools in the excerpts seen. They stress modelling, DCF and relative valuation, and CA/CFA/MBA credentials. Examples: Navi AMC, Groww Mutual Fund, and recruiters hiring for AMC/PMS/insurer roles. — [QuintEdge: Navi AMC](https://jobs.quintedge.com/jobs/equity-research-analyst-amc-navi-1jdu34); [Greenhouse: Groww](https://job-boards.greenhouse.io/groww/jobs/4588364101); [Weekday: Green Lane, BFSI buy-side analyst](https://jobs.weekday.works/bfsi-equity-research-analyst-buyside-at-green-lane-talent-management-wkdyo9npws); [iimjobs listing](https://www.iimjobs.com/j/equity-research-analyst-sector-agnostic-1721757?jobPos=97)
- Domestic databases licensed by Indian business schools:
  - ACE Equity: 40,000+ Indian companies (about 7,000 listed and 33,000 private) with 1,750 data fields; a separate ACE MF product covers mutual funds.
  - CMIE Prowess IQ: 37,780 companies.
  - Capitaline: shareholding patterns and 10-year P&L and balance sheets, aimed at users including "fund managers".
  - Bloomberg is licensed alongside them.
  - Sources: [IIM Trichy library: ACE Equity](https://www.iimtrichy.ac.in/lrc-compinfo); [IIM Indore e-resources](https://iimidr.ac.in/facilities/library/electronic-resources/category-wise-list-of-electronic-resources/); [IIM Bangalore data sources](https://iimb.ac.in/ccmrm/resources-at-iim-bangalore-data-sources.php)
- The Indian press sources coverage and consensus statistics from Bloomberg (for example BS 2021 on BSE 500 coverage). Reuters-sourced items carry LSEG-compiled consensus (for example LG Electronics India). — [Business Standard, 2021](https://www.business-standard.com/article/markets/on-the-radar-analysts-expand-coverage-amid-sharp-stock-market-rally-121062400017_1.html); [Stockopedia](https://www.stockopedia.com/share-prices/lg-electronics-india-NSI:LGEINDIA/news/lg-electronics-india-rises-after-jefferies-initiates-with-apos-buy-apos-019e69f8-f6b2-77fc-97c1-200a871871d2/)

### Inferences
- The likely Indian institutional pattern:
  - Bloomberg is the dominant terminal.
  - LSEG Workspace is used for Reuters news and I/B/E/S, and is common in the public sector (DICGC).
  - Low-cost domestic databases (ACE Equity, Capitaline, Prowess) cover deep Indian small-cap financials and shareholding.
  - CRISIL and Value Research cover mutual fund rankings and data.
  - FactSet and Capital IQ Pro are more common at FPIs, global managers' Indian captives and the largest AMCs or insurers that need portfolio analytics and risk.
  - This pattern is inferred and is not confirmed by any survey.

### Gaps
- No survey or market-share figures were found for India.
- No Indian AMC, PMS, AIF or insurer annual report or disclosure naming FactSet, Capital IQ Pro or Morningstar Direct was found.
- No vendor discloses Indian client counts.
- Indian job ads that name tools need a direct LinkedIn or Naukri search; the excerpts available did not name any.

## 8. Known limitations for India-focused managers: small-cap coverage, filing depth, cost and local news

### Takeaway
The main constraint for an India-focused manager is data, not analytics:
- Consensus exists for roughly the top 900–1,000 companies.
- The global vendors decide fundamentals coverage partly by index membership and broker coverage.
- Small regional contributors are covered unevenly across vendors.
- StreetAccount's Asia coverage is still "expanding".
- Seats cost about $10k–$40k per user per year.

Domestic databases claim broader coverage of Indian listed companies (about 7,000 listed in ACE Equity).

### Cited Findings
- FactSet Fundamentals' coverage depends on market cap, index membership, broker coverage, size and the importance of the market. — [Xignite listing](https://cmsstaging.xignite.com/wiki/49)
- FactSet's emerging-market annual history starts in the early 1990s, and interim history for non-US companies starts in 2001. — [FactSet Fundamentals brochure](https://www.wiso.uni-hamburg.de/bibliothek/recherche/datenbanken/unternehmensdaten/factset-fundamentals.pdf)
- Coverage by small regional contributors differs across estimates vendors, while bulge-bracket coverage is consistent. — [S&P Global MI: estimates expansion](https://www.spglobal.com/market-intelligence/en/solutions/resources/estimates-expansion)
- For smaller companies, thin coverage means the consensus may not reflect a genuine market view, and micro caps have few or no analysts. — [equitiesindia.com: consensus estimate](https://equitiesindia.com/glossary/consensus-estimate); [equitiesindia.com: microcap](https://equitiesindia.com/glossary/microcap-stock)
- Trendlyne's consensus deliberately leaves out smaller companies and covers about 900. — [Trendlyne help](https://help.trendlyne.com/support/solutions/articles/84000383175-what-are-forecaster-or-analyst-estimates-)
- More than 5,300 of about 6,000 listed stocks are not tracked by any analyst. [Undated] — [Value Research](https://www.valueresearchonline.com/stories/18224/a-basic-disconnect/)
- StreetAccount covers the US and Europe "with expanding Asia coverage". — [AWS Marketplace: StreetAccount](https://aws.amazon.com/marketplace/pp/prodview-7luwmqro77biw)
- In S&P, there is no data for some small private companies (one user review). — [G2](https://www.g2.com/products/s-p-global-market-intelligence/reviews)
- ACE Equity covers about 7,000 Indian listed companies and 33,000 private ones with 1,750 fields. — [IIM Trichy library](https://www.iimtrichy.ac.in/lrc-compinfo)
- DICGC says there are "no reasonable substitute/alternatives" to its Refinitiv, Bloomberg and Cogencis services. — [DICGC](https://www.dicgc.org.in/sites/default/files/2026-04/work-issued-on-nomination-basis.pdf)
- The Eikon-to-Workspace migration has been described as "rocky". [Low-quality source] — [rfp.wiki](https://www.rfp.wiki/investment/bloomberg/refinitiv)
- For costs, see section 6, e.g. [CostBench: FactSet](https://costbench.com/software/financial-data-terminals/factset/) and [UK G-Cloud S&P pricing](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-14/documents/716762/461639550806531-pricing-document-2025-12-08-1330.pdf).

### Inferences
- For a small-cap or micro-cap Indian portfolio, the global platforms add the most value on factor risk models, attribution and reporting. They add the least on the long tail: companies without consensus, without broker research, or with slow fundamentals updates.
- A self-built tracker that pulls NSE/BSE filings, shareholding patterns and corporate announcements directly can match or exceed the global vendors on that long tail. It cannot easily replicate:
  - Licensed consensus data for the top 900–1,000 names.
  - Factor risk models.
  - Reuters, StreetAccount or transcript content.
  - OMS/IBOR integration.
- None of the sources describes native support in FactSet, LSEG, S&P or Morningstar for Indian regulatory outputs. Examples are SEBI scheme categories, AMFI's half-yearly market-cap lists, SEBI-format portfolio disclosures and PMS client reporting. These probably need custom configuration. This was not researched directly.

### Gaps
- No direct evidence was found on how deep any of the four vendors goes into Indian filings: BSE/NSE announcement capture, quarterly shareholding patterns, promoter pledges, related-party transactions, or turnaround time for results.
- No India-specific user reviews comparing global and domestic data quality were found.
- No public evidence was found on local-language or regional news coverage by Reuters or StreetAccount in India.
