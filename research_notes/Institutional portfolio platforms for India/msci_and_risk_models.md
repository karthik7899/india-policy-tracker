# MSCI and dedicated equity risk-model vendors for Indian listed equities (as of 10 October 2026)

> **How these notes were collected (read first).** Every finding below comes from web-search result summaries. I could not open the pages themselves. WebFetch failed DNS resolution, and fetching through the session's egress proxy returned **HTTP 403 (policy refusal)** for `help.arcana.io`, `www.sebi.gov.in`, `www.msci.com` and `app2.msci.com`. As instructed, I did not retry those requests or route around them. A figure cited to a URL is therefore what the search engine reported that page says; nobody checked it on the page. Treat exact numbers as "reported by", and re-check them against the primary page before publishing.
>
> **Labels:**
> - **[Primary]**: a regulator, company filing or vendor technical document, as summarised by search.
> - **[Vendor claim]**: vendor marketing copy.
> - **[Secondary]**: press, blogs, third-party help sites or academic papers.
> - **[Estimate]**: a third-party price, flow or market-share estimate.
>
> Anything under "Inferences" is my reasoning, not a sourced fact.

## Q1. Which MSCI Barra equity models cover India, and what factors and outputs do BarraOne and Barra Portfolio Manager provide?

### Takeaway
MSCI does sell a **single-country India model, the "MSCI Barra India Total Market Equity Model (INE2)"**. India is also a country inside MSCI's global models: the Global Total Market suite (GEMLT, 87 countries) and the older GEM2 and GEM3. What I could find about INE2 comes from one third-party help centre. It covers the daily update cycle and the broad style families, but not the estimation universe, factor count or release date. BarraOne and Barra Portfolio Manager (BPM) are holdings-based tools. They produce:
- ex-ante risk: tracking error, factor exposures, and risk broken down by country, currency, industry, style and stock-specific sources
- VaR and stress tests
- attribution
- optimisation, through the shared MSCI/Barra Optimizer

### Cited Findings
**India model (INE2)**
- [Secondary] A help-centre page titled "MSCI Barra India Total Market Equity Model (INE2) Methodology & Handbook PDF" describes INE2 as follows:
  - a multi-factor risk model for institutional investors in Indian equities
  - **daily updates** of style, industry and market factors
  - style factors include **momentum, liquidity, profitability, leverage, value, growth and volatility**
  - stated uses are risk decomposition, stress testing and portfolio optimisation

  The page belongs to Arcana, a third-party portfolio-analytics vendor that hosts the MSCI handbook for its users. This is the only India-model description I found. — [Arcana help centre (INE2)](https://help.arcana.io/en/articles/14983275-msci-barra-india-total-market-equity-model-ine2-methodology-handbook-pdf)
- [Primary] How Barra names single-country models: country code + "E" + generation number. Example: the "Barra US Equity Model (USE4)". — [USE4 Methodology Notes, Aug 2011](https://www.top1000funds.com/wp-content/uploads/2011/09/USE4_Methodology_Notes_August_2011.pdf)
- [Primary] MSCI also markets "Total Market" single-country variants elsewhere, e.g. the Barra US Total Market Equity Models. — [MSCI Barra US Total Market Equity Models factsheet](https://www.msci.com/documents/1296102/1636401/MSCI_Barra_Market+Equity+Models_Factsheet+.pdf/0c9d381f-e4e6-42fc-b7c2-dfff694dd650)

**Model range and global models**
- [Vendor claim] MSCI says it offers **"more than 70 models across 75,000+ securities, 45 industry factors and 87 countries"**. The search summary did not say which of these two pages carries the line. LSEG lists MSCI Barra models among the quantitative-model datasets it distributes. — [MSCI Barra Models page](https://app2.msci.com/products/analytics/models/); [LSEG: MSCI Barra Models](https://www.lseg.com/en/data-analytics/financial-data/company-data/quantitative-models/msci-barra-models)
- [Primary] **GEMLT (Barra Global Total Market Equity Model suite)**:
  - covers **87 countries and 72 currencies**
  - groups **16 style factors into 8 groups**: Value, Size, Momentum, Volatility, Quality, Yield, Growth and Liquidity

  The factsheet, as summarised, does not list each country, so it does not explicitly confirm India as a separate country factor. — [GEMLT factsheet](https://www.msci.com/documents/10199/242721/GEMLT_FactSheet.pdf)
- [Primary] MSCI's Emerging Markets index factsheets compute their factor-group characteristics from GEMLT. So GEMLT is the model MSCI itself applies to the EM universe, which includes India. — [MSCI EM Index factsheet](https://www.msci.com/documents/10199/c0db0a48-01f2-4ba9-ad01-226fd5678111)
- [Primary] The older **GEM3**:
  - had **77 country factors and 63 currencies**
  - **lists India under Asia** in its country list
  - added 22 frontier markets
  
  — [Barra GEM3 brochure](https://www.msci.com/documents/10199/242721/Barra_Global_Equity_Model_GEM3.pdf)
- [Primary] For the earlier GEM2, MSCI says country, industry and style factors explain a large share of the common movement in equity returns. Its estimation universe was based on **MSCI ACWI (~8,000 stocks)**. The search summary did not say which of these two documents makes the universe statement. — [Barra GEM2 page](https://app2.msci.com/products/analytics/models/global_equity_model/); [MSCI Model Insight (2011)](https://www.msci.com/documents/10199/ed6e42a3-c1fa-4430-89ba-efd5a5b52558)
- [Primary] MSCI has published "The Global Equity Model vs. the Emerging Markets Model: A Comparison", so a separate Barra Emerging Markets model exists or existed. The content was not retrieved. — [MSCI research report](https://www.msci.com/www/research-report/the-global-equity-model-vs-the/014553805)
- [Primary] How Barra builds style exposures (useful if replicating in-house):
  - each exposure is standardised so the cap-weighted estimation universe has mean zero, which leaves a cap-weighted diversified portfolio with roughly zero exposure to every style
  - the standard deviation used in the standardisation is equal-weighted, so large caps do not dominate the scale
  
  — [USE4 Methodology Notes](https://www.top1000funds.com/wp-content/uploads/2011/09/USE4_Methodology_Notes_August_2011.pdf)

**BarraOne and Barra Portfolio Manager**
- [Vendor claim] **BarraOne** is a holdings-based framework that brings risk, attribution, stress testing and reporting together. MSCI says it provides Barra factor risk models, **value-at-risk**, and **full-revaluation stress tests** for public and private assets and derivatives. — [MSCI BarraOne page](https://www.msci.com/data-and-analytics/portfolio-management/barra-one)
- [Primary, older user guide] BarraOne annualises the tracking errors it calculates and can compute them from daily, weekly or monthly returns. Factor-based attribution reuses the same factors as the risk model. — [BarraOne Performance Analytics Guide (Scribd copy)](https://www.scribd.com/document/89722958/Barraone-Performance-Analytics-Guide)
- [Vendor claim] **Barra Portfolio Manager** is a hosted equity-analytics platform. Features named: custom factor attribution, scenario and what-if analysis, portfolio optimisation and automated reporting. — [MSCI Barra Portfolio Manager page](https://app2.msci.com/products/analytics/barra_portfolio_manager/)
- [Vendor claim] The Barra Aegis / Portfolio Manager & Optimizer brochure's key features include "Identify sources of risk—Isolate country, currency, industry, [style]…". This is the country/currency/industry/style risk breakdown. — [Barra Aegis Portfolio Manager & Optimizer brochure](https://www.msci.com/documents/10199/242721/Barra_Aegis_Portfolio_Mgr_and_Optimizer.pdf/37f3416e-ac3a-4e34-a7f3-09c90d51332e)
- [Vendor claim] The **MSCI Optimizer engine powers Barra Aegis, BarraOne and BPM**. The BarraOne Optimizer handles single-country, regional, global and multi-asset portfolios. — [BarraOne Optimizer page](https://app2.msci.com/products/analytics/barraone/barraone_optimizer.html); [Barra Open Optimizer PDF](https://www.msci.com/documents/1296102/8335426/Barra-Open-Optimizer.pdf)

### Inferences
- The "2" in INE2 suggests at least one earlier India model generation (by analogy with USE3 → USE4). "Total Market" suggests coverage beyond large and mid caps, by analogy with the US Total Market models. Both are inferred from naming; neither is confirmed.
- **Two ways to model an Indian portfolio with Barra:**
  - *A global model (GEMLT or GEM).* India is one country factor plus an INR currency factor, and Indian stocks share global industry and global style factors. India-specific style premia, such as a domestic size or value effect that differs from the global one, are not estimated separately.
  - *INE2.* Local industries and styles are estimated on Indian data.

  An India-only long-only manager would normally want INE2. A global or EM manager would use GEMLT so risk adds up across countries.
- Outputs an India manager would get from BarraOne or BPM against a Nifty or MSCI India benchmark:
  - ex-ante tracking error
  - active factor exposures
  - marginal and percentage contribution to tracking error by factor and by stock
  - factor versus stock-specific risk split
  - VaR
  - stress profit and loss
  
  These are the standard Barra outputs and are consistent with the sources above. The exact report names and layouts were not retrieved.

### Gaps
- **INE2 specifics I could not confirm:**
  - estimation universe: size, and whether it is MSCI India IMI or a wider NSE/BSE universe
  - number and definitions of industry factors
  - the full style list and its descriptors
  - release date and data history length
  - whether there are short- and long-horizon (S/L) variants
  - whether INE2 is still actively supported in 2026

  MSCI's model pages and the Arcana page were blocked (HTTP 403). The handbook appears to be client-only.
- Whether an "INE1" existed and when it was retired: not found.
- Whether MSCI has replaced or renamed GEMLT with a newer global suite in 2025–26: not found.

## Q2. What attribution, scenario/stress testing, liquidity-risk and limit-monitoring capabilities does MSCI offer, and how are they delivered?

### Takeaway
- **Attribution:** Brinson-Fachler and factor-based, in BarraOne and the MAC performance-attribution model.
- **Stress testing:** historical, hypothetical and user-defined, in BarraOne and RiskMetrics RiskManager.
- **Liquidity risk:** LiquidityMetrics, delivered inside RiskManager.
- **Delivery:**
  - hosted web applications (BarraOne, BPM)
  - APIs (BarraOne Developer's Toolkit, the Optimization Service API)
  - data delivery (Snowflake-native; also LSEG and FactSet)
  - an outsourced data-operations add-on (Barra Managed Services)

I found no documentation of a dedicated limit-monitoring or compliance workflow. Liquidity-limit and transaction-cost-limit checks are described.

### Cited Findings
**Attribution**
- [Primary] BarraOne offers a suite of performance-attribution models. They include **Brinson-Fachler allocation/selection** and **factor-based attribution** for equity, fixed-income and multi-asset portfolios. — [MSCI MAC Performance Attribution factsheet](https://www.msci.com/documents/1296102/8335426/MSCI+MAC+Performance+Attribution+Factsheet.pdf)
- [Primary, older guide] In BarraOne, factor attribution covers only equity and equity-derivative assets. Fixed-income term-structure attribution uses an exposure method. — [BarraOne Performance Analytics Guide](https://www.scribd.com/document/89722958/Barraone-Performance-Analytics-Guide); [BarraOne Performance Attribution: Brinson vs Factor-Based](https://www.scribd.com/document/285202382/BarraOne-Performance-Attribution-Brinson-vs-Factor-Based)

**Stress testing**
- [Vendor claim, older brochure] BarraOne provides **user-defined and historical cross-asset stress tests**. — [BarraOne brochure (Scribd)](https://www.scribd.com/document/359468292/BARRAONE)
- [Vendor claim] **RiskMetrics RiskManager** puts **VaR, factor, stress-testing, liquidity and counterparty-credit-risk** analytics on one platform. — [MSCI RiskManager page](https://www.msci.com/data-and-analytics/risk-management-solutions/riskmetrics-riskmanager)
- [Vendor claim] RiskManager includes a ready-made library of historical and hypothetical scenarios. Users can also build their own stress tests, combining stresses on individual risk factors with stresses on model parameters. The brochure sits under an MSCI "managed-solutions" URL path. — [RiskMetrics RiskManager brochure](https://www.msci.com/downloads/web/msci-com/our-solutions-/analytics/managed-solutions/RiskMetrics_RiskManager.pdf)

**Liquidity risk and limits**
- [Primary] **LiquidityMetrics** is delivered through RiskManager. It estimates:
  - market impact
  - transaction cost
  - liquidation horizon
  - amount available for liquidation
  - liquidation value
  
  It also stress-tests portfolio liquidity under adverse market-liquidity conditions. MSCI positions it for **UCITS, AIFMD, SEC Rule 22e-4 and Form PF**. — [MSCI LiquidityMetrics factsheet](https://www.msci.com/documents/1296102/8335426/MSCI_LiquidityMetrics_Factsheet.pdf/1ef81401-d1d4-6e84-834c-f03d3225c318); [Finextra: MSCI launches liquidity measurement tool (older)](https://www.finextra.com/pressarticle/51662/msci-launches-liquidity-measurement-tool)
- [Vendor claim] Two limit-style checks are described:
  - how long it would take to liquidate portions of a portfolio **within specified transaction-cost limits**
  - the **largest position size that still satisfies a portfolio liquidity limit**
  
  — [MSCI blog: Measuring Liquidity Risk](https://www.msci.com/research-and-insights/blog-post/measuring-liquidity-risk)

**Delivery**
- [Vendor claim] BarraOne offers "automated workflows, **Snowflake-native data delivery** and rich, interactive dashboards". — [MSCI BarraOne page](https://www.msci.com/data-and-analytics/portfolio-management/barra-one)
- [Primary] APIs:
  - the **BarraOne Developer's Toolkit Interactive**, a web-service API that gives client developers detailed access to BarraOne analytics
  - the **MSCI Optimization Service API** (part of MSCI Quantitative Investment Solutions) for building optimiser and rule-based strategies
  
  — [MSCI developer APIs](https://developer.msci.com/apis)
- [Vendor claim] In BPM, "all data and processing is managed on a secure, hosted platform". — [MSCI Barra Portfolio Manager page](https://app2.msci.com/products/analytics/barra_portfolio_manager/)
- [Vendor claim] **Barra Managed Services** is an optional add-on to BPM. A global team of operations specialists runs and monitors the client's end-to-end data workflow, including full reconciliation of portfolio market values and asset coverage. — [Managed Services for BPM (PDF)](https://www.msci.com/documents/10199/242721/Managed_Services_for_BPM.pdf/698498b0-c21c-4e89-bedc-bef5b64634c7)
- [Secondary] Barra models are also reached through third-party platforms. FactSet Portfolio Analytics already hosts "Barra, MSCI and Axioma traditional models", and LSEG distributes MSCI Barra models. — [Quant Insight on FactSet PA](https://www.quant-insight.com/insight/quant-insight-brings-macro-factor-equity-risk-to-factset-portfolio-analytics); [LSEG](https://www.lseg.com/en/data-analytics/financial-data/company-data/quantitative-models/msci-barra-models)

**India context: SEBI-mandated liquidity stress tests that any vendor tool must coexist with**
- [Secondary] **Since March 2024**, SEBI requires small- and mid-cap mutual-fund schemes to disclose **how many days it would take to liquidate 25% and 50% of the portfolio**, liquidating pro rata. Per these summaries, AMFI's method first removes the **20% least-liquid holdings** before applying the pro-rata liquidation. I did not check this against AMFI's own file. — [Oquilia](https://www.oquilia.com/news/sebi-mf-stress-test-smallcap-midcap-liquidation); [Finedge](https://www.finedge.in/blog/mutual-funds/why-the-stress-test-on-mid-and-small-cap-funds-should-not-stress-you-out)
- [Secondary] Reported results:

  | When | Fund / sample | Result | Source |
  |---|---|---|---|
  | Mar 2024 | Quant MF small cap | 22 days to liquidate 50% | [Business Standard, 15 Mar 2024](https://www.business-standard.com/amp/finance/personal-finance/explained-what-is-the-sebi-stress-test-and-why-quant-mf-will-take-22-days-for-50-small-cap-liquidation-124031500192_1.html) |
  | Mar 2024 | DSP Small Cap | 16 days to exit 25% | [Business Standard](https://www.business-standard.com/amp/markets/news/stress-test-dsp-needs-16-days-to-exit-25-in-smallcap-mf-edelweiss-3-days-124031500117_1.html) |
  | Mar 2024 | Edelweiss | 3 days to exit 25% | same article |
  | Mar 2025 | High-risk small-cap portfolios | 25–57 days to liquidate 50% | [BusinessToday, 19 Apr 2025](https://www.businesstoday.in/personal-finance/investment/story/mf-investors-exiting-small-cap-funds-may-take-weeks-in-a-crisis-stress-test-shows-472692-2025-04-19) |
  | May 2026 | HDFC Mid Cap | 34 days to liquidate 50% | [Bajaj Broking, May 2026](https://www.bajajbroking.in/share-market-news/midcap-and-smallcap-fund-stress-test-may-2026-data) |
  | May 2026 | SBI Small Cap | 59 days to liquidate 50% | same |

### Inferences
- LiquidityMetrics is framed around UCITS and SEC 22e-4. Indian AMCs still have to compute the SEBI days-to-liquidate number exactly by AMFI's method. A vendor tool would therefore be a second view (market impact, cost), not the regulatory number. A self-built tracker can reproduce the AMFI-style metric from public NSE/BSE volume data.
- In the sources found, "limit monitoring" at MSCI shows up in three places: liquidity limits, transaction-cost limits, and optimiser constraints. I found no stand-alone compliance or limit-breach engine. Low confidence: the product documentation was not reachable.

### Gaps
- How limit-breach alerts and escalation work in RiskManager and BarraOne: not found.
- How the MSCI ONE platform relates to BarraOne and BPM: not confirmed.
- How LiquidityMetrics handles Indian market features (exchange circuit limits, F&O ban lists, block-deal windows, T+1 settlement), and its India coverage: not found.
- Whether MSCI offers India-hosted data residency for Indian clients: not found.

## Q3. MSCI ESG and climate coverage of Indian companies, and use in Indian ESG mutual funds under SEBI's rules

### Takeaway
- **Registration:** MSCI's Indian ESG entity, **MSCI ESG Ratings and Research Private Limited**, is registered with SEBI as a **Category II, subscriber-pays ESG Rating Provider (ERP)**. The registration is dated 13 August 2024. It matters because SEBI's ESG-fund rules require disclosure of scores from SEBI-registered ERPs.
- **Ratings profile:** MSCI rates the MSCI India Index universe. At February 2024 the split was 8% leaders, 66% average and 26% laggards. MSCI also runs India ESG and climate index variants.
- **Not found:**
  - a source stating how many Indian issuers MSCI rates
  - India-specific controversy coverage
  - any Indian ESG scheme publicly naming MSCI as its ratings source

### Cited Findings
**Coverage**
- [Vendor claim, sources differ on date and definition] Global coverage:

  | Figure | Date | Source |
  |---|---|---|
  | >17,000 issuers; ~999,000 securities | current MSCI page | [MSCI ESG Ratings page](https://www.msci.com/data-and-analytics/sustainability-solutions/esg-ratings) |
  | ~10,001 companies (~16,885 issuers incl. subsidiaries) | 22 Mar 2024 | [IIM Indore user guide to MSCI ESG Ratings Time Series](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-MSCI-ESG-Ratings-Time.pdf) |
  | ~8,500 companies (~14,000 issuers) | — | [LUISS library](https://biblioteca.luiss.it/en/resources/msci-esg-ratings) |

- [Primary] The **MSCI India IMI** is among the indexes covered by the MSCI ESG Ratings time series. The IIM Indore library published a user guide for it (uploaded October 2025), which indicates Indian academic access. — [IIM Indore user guide](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-MSCI-ESG-Ratings-Time.pdf)
- [Primary] At end-February 2024, the MSCI India Index split as follows:
  - **8% leaders**, up from 6% five years earlier
  - **66% average**, up from 55%
  - **26% laggards**
  
  The summary also quoted a 34% laggard share five years earlier. That figure is inconsistent with 6% + 55%, which implies 39%, so check it. — [MSCI blog: Indian firms advance in financially pertinent sustainability risks](https://www.msci.com/research-and-insights/blog-post/indian-firms-advance-in-financially-pertinent-sustainability-risks)
- [Primary] **MSCI India Selection Index**:
  - formerly MSCI India ESG Leaders; the ESG Leaders indexes were renamed "Selection" on 3 Feb 2025
  - **55 constituents**
  - targets 50% of free-float market cap in each GICS sector, choosing constituents mainly on ESG rating
  - reports **100% ESG-score coverage**
  
  — [MSCI India Selection Index page](https://www.msci.com/indexes/index/145848); [factsheet](https://www.msci.com/documents/10199/06d20a9e-bd6b-4ea8-a7a2-31cfb0444273)
- [Primary] Climate-oriented India variant: **MSCI India IMI Low Carbon Target Core Index**, 600 constituents as of 31 Jul 2026. — [MSCI index page](https://www.msci.com/indexes/index/752666/msci-india-imi-low-carbon-target-core-index)
- [Primary] The MSCI ESG Fund Rating rests on a 0–10 Fund ESG Quality Score: the asset-weighted average of the MSCI ESG Ratings of the fund's holdings. Any Indian fund's MSCI fund rating therefore depends on company-level coverage. — [MSCI ESG Fund Ratings Methodology](https://www.msci.com/documents/1296102/34424357/MSCI+ESG+Fund+Ratings+Methodology.pdf)

**SEBI ESG Rating Provider (ERP) regime**
- [Primary] A SEBI board paper lists ERPs registered as of 1 Dec 2024. It includes **MSCI ESG Ratings and Research Private Limited**, dated **13 Aug 2024**, **subscriber-pays** model. — [SEBI board memo, Dec 2024: Ease of Doing Business for ERPs](https://www.sebi.gov.in/sebi_data/meetingfiles/dec-2024/1735215341884_1.pdf)
- [Secondary] Registration number **IN/ERP/Category-II/0013** (Category II, subscriber-pays). The same paper lists **CRISIL ESG Ratings as a Category I ERP**. I could not check SEBI's own registry (HTTP 403). — [IJRAR comparative paper on Indian ESG rating agencies](https://ijrar.org/download.php?file=IJRAR25B3642.pdf)
- [Secondary] In **May 2024** MSCI ESG Ratings and LSEG were still awaiting SEBI certification. The same report says:
  - listed companies are not required to obtain an ESG rating
  - revenue looks limited because the market is nascent
  - an SES executive said there may not be room for many players
  
  — [Business Standard, 16 May 2024](https://www.business-standard.com/amp/markets/news/scramble-for-erp-license-even-as-doubts-remain-on-the-market-size-124051601408_1.html)
- [Secondary] A **SEBI Master Circular for ERPs was issued on 11 July 2025**; ESG scores on Indian companies cannot be published without an ERP licence. LSEG/Refinitiv and Bloomberg withdrew the ESG scores they had published on Indian firms because they were not registered. The search summary did not say which of these two pages carries these statements, so treat them as unverified. — [Rajagiri Business School blog](https://www.rajagiribusinessschool.edu.in/blog-details/esg-ratings-in-india); [Corporate Professionals](https://www.corporateprofessionals.com/articles/disclosure-of-esg-ratings-under-sebi-lodr-regulations-legal-position-rationale-and-interpretive-guidance/)
- [Secondary, draft-stage] Minimum net worth: **INR 5 crore for Category I** ERPs, **INR 10 lakh for Category II**. — [IRCCL on SEBI's draft ERP framework](https://www.irccl.in/post/understanding-sebi-s-draft-regulatory-framework-for-esg-rating-providers)
- [Primary] SEBI's framework defines ESG ratings broadly, as ratings products "marketed as providing an opinion" on a listed or proposed-to-be-listed entity. SEBI also has an ERP FAQ (Jan 2025). — [SEBI board paper Apr 2023: Balanced Framework for ESG Disclosures, Ratings and Investing](https://www.sebi.gov.in/sebi_data/meetingfiles/apr-2023/1681703013916_1.pdf); [SEBI ERP FAQs, Jan 2025](https://www.sebi.gov.in/sebi_data/faqfiles/jan-2025/1737114577492.pdf)

**SEBI ESG mutual-fund rules**
- [Primary] The SEBI circular **SEBI/HO/IMD/IMD-I–PoD1/P/CIR/2023/125 (20 July 2023)** sets these rules for ESG schemes:
  - at least **65% of AUM** in companies that report comprehensive BRSR **and** provide **assurance on BRSR Core**; the rest may go to companies with BRSR disclosures
  - effective **1 Oct 2024**; existing schemes had until **30 Sep 2025** to comply, with no fresh investments in companies lacking BRSR Core assurance during that window
  - monthly portfolio statements must show **security-wise BRSR Core scores "as and when available from SEBI registered ESG Rating Providers"**, the BRSR scores, **and the names of the ERPs**
  - an annual independent reasonable assurance on whether the portfolio follows the stated strategy
  - certification of compliance by the AMC board, based on an internal ESG audit
  
  — [SEBI circular (copy hosted by Skyline RTA)](https://www.skylinerta.com/pdf_file/51_671021621_SEBICircular-ESG-DisclosurebyMutualFund-20.07.2023.pdf); [TaxGuru summary](https://taxguru.in/sebi/sebi-introduces-new-esg-investing-schemes-mutual-funds.html)
- [Secondary] Further rules:
  - ESG schemes must put **≥80% of AUM in equity tied to the stated strategy**, and the remaining 20% must not contradict it
  - SEBI allows **six ESG strategies** under the thematic sub-category, and fund names must reflect the strategy (e.g., "ABC ESG Best-in-class Strategy Fund")
  
  — [Lexology](https://www.lexology.com/library/detail.aspx?g=696972fb-7027-47f6-85e4-eefaaaaa71ac); [LiveLaw](https://www.livelaw.in/news-updates/sebi-introduces-new-category-of-mutual-fund-schemes-for-environmental-social-and-governance-esg-investing-and-related-disclosures-233423); [DSP MF explainer](https://www.dspim.com/knowledge-hub/personal-finance-guide/esg-mutual-funds-in-india); [KPMG India chapter](https://assets.kpmg.com/content/dam/kpmg/in/pdf/2023/09/chapter-2-esg-investing-by-mutual-funds.pdf)
- [Secondary] CRISIL scored India's **nine active ESG mutual funds** using its own proprietary 2022 sustainability evaluations, not MSCI's. — [CRISIL: How India's nine ESG mutual funds stack up](https://www.crisil.com/content/dam/crisil/our-analysis/esg-research/esg-readings/how-indias-nine-esg-mutual-funds-stack-up.pdf)

### Inferences
- SEBI's disclosure rule names "SEBI registered ERPs". MSCI's Category II registration lets Indian ESG schemes cite MSCI scores in monthly disclosures. Without it, foreign ratings could not be published on Indian companies, as the LSEG and Bloomberg withdrawals suggest.
- Because the rules centre on BRSR and BRSR Core, domestic ERPs that build on BRSR data (CRISIL and others) have a natural regulatory fit. MSCI's global-methodology ratings are more likely to be used by FPIs and global funds for their India allocations, and by Indian AMCs with global parents or offshore feeder funds. This is inference; no scheme-level evidence was found.
- MSCI probably rates at least the India IMI constituents (~626 names; see Q4), since India IMI is in the ratings time series. This is a lower-bound inference, not a confirmed count.

### Gaps
- **Number of Indian issuers with MSCI ESG Ratings:** no India-specific count found in any source. India coverage of **MSCI ESG Controversies** and climate metrics (Scope 1–3 emissions, Implied Temperature Rise, Climate VaR) for Indian companies: not found.
- **Indian ESG schemes:** none found that name MSCI as their ERP. This needs a check of scheme information documents and monthly portfolio disclosures.
- **SEBI's own ERP registry page:** blocked (HTTP 403), so MSCI's status after Dec 2024 is not directly confirmed.
- **Later amendments** to the July 2023 ESG circular, or ESG provisions in SEBI's current Master Circular for MFs: not checked.

## Q4. The MSCI India index family: role as benchmarks for FPIs and Indian funds, and index licensing

### Takeaway
The MSCI India family includes:
- MSCI India (large and mid cap)
- India IMI (~626 names)
- India Small Cap
- India Domestic and Domestic IMI (~630 names)
- Selection (ESG), Low Carbon, Islamic and Value-Weighted variants

These are the reference benchmarks for **FPIs and global EM managers' India exposure**. Foreign-ownership-limit (FOL) and foreign-room rules shape their weights. The **India Domestic** indices instead use a Domestic Inclusion Factor for local investors.

India's weight in MSCI EM fell from a ~19–21% peak (Sep 2024) to ~11–12% (Apr–May 2026). That drives large passive FPI flows around rebalances.

Indian domestic mutual funds mostly benchmark to NSE, BSE and CRISIL indices. SEBI's draft list of "significant indices" names only those providers, not MSCI. No public licence-fee figures were found.

### Cited Findings
**India Domestic indices and foreign-ownership rules**
- [Primary] The **MSCI India Domestic Index** measures the large- and mid-cap segments of the *domestic* Indian market. It is built on the Global Investable Market Indexes (GIMI) methodology but uses a **Domestic Inclusion Factor (DIF)** instead of the foreign inclusion factor. — [MSCI India Domestic Index factsheet](https://www.msci.com/documents/10199/af0a5885-9cfd-441f-9071-e8de1b0ef4e7); [MSCI GIMI methodology with India Domestic, Feb 2015](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Feb15_GIMIMethod_with_India_Dom_Final.pdf)
- [Primary, 2015 text] In the international indexes, FOL and **foreign room** adjust weights:
  - Foreign Room = (FOL% − foreign holding%) / FOL%
  - a *new* security needs **≥15% foreign room** to be included
  - existing constituents are not tested against this screen
  
  — [MSCI GIMI methodology, Feb 2015](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Feb15_GIMIMethod_with_India_Dom_Final.pdf)
- [Secondary] From the **November 2020** review, the FOL for Indian securities equals the **automatic-route sectoral limit**. The exceptions are a higher limit approved under the government route or a lower limit set by the company. Business Standard estimated **~$2.5bn of passive inflow** from the change; MSCI had deferred the decision in April 2020. — [Business Standard, 27 Oct 2020](https://www.business-standard.com/amp/article/markets/foreign-ownership-limits-msci-india-to-see-passive-inflow-of-2-5-billion-120102700416_1.html); [Business Standard, 28 Oct 2020](https://www.business-standard.com/article/economy-policy/india-s-weighting-in-widely-tracked-msci-em-index-set-for-major-boost-120102800063_1.html); [Business Standard, Apr 2020](https://www.business-standard.com/amp/article/markets/msci-defers-decision-on-hiking-india-s-weight-in-its-global-indices-120040100993_1.html)
- [Secondary] Recent example: Swiggy was removed from two MSCI indices because its foreign room fell below MSCI's minimum, which triggers weight cuts or deletion. Exact date not captured. — [Outlook Money](https://www.outlookmoney.com/invest/swiggy-shares-in-focus-after-major-msci-index-move-what-triggered-the-decision)

**Constituent counts (2026)**
- [Primary] Reported counts:

  | Index | Constituents | As of | Source |
  |---|---|---|---|
  | MSCI India IMI | 626 | Aug 2026 | [MSCI India IMI page](https://www.msci.com/indexes/index/664231/msci-india-imi-index) |
  | India IMI Value Weighted | 625 | 31 Jul 2026 | [MSCI page](https://www.msci.com/indexes/index/139488/msci-india-imi-value-weighted-index) |
  | India Domestic IMI (INR) | 630 | ~Jul 2026 (factsheet date metadata inconsistent) | [factsheet](https://www.msci.com/documents/10199/509e7d86-7d47-4424-96d2-6e5e0ae5d655) |
  | India Universal | 154 | — | [MSCI page](https://www.msci.com/indexes/index/720090/msci-india-universal-index) |
  | MSCI EM Small Cap (all EM, includes India) | 1,749 | 30 Sep 2026 | [factsheet](https://www.msci.com/documents/10199/255599/msci-emerging-markets-small-cap-index-net.pdf) |

  Other variants exist: [India Domestic IMI Select 30 (INR)](https://www.msci.com/documents/10199/095ae289-be18-830d-addc-06a90affbde3), [India IMI Islamic](https://www.msci.com/indexes/index/143361/msci-india-imi-islamic-index) and [ACWI ex India IMI](https://www.msci.com/documents/10199/1a27d13a-f536-47f8-9333-c7c0b41dd6a3).

**India's weight in MSCI EM**
- [Primary] Recent MSCI factsheets put India at **11.25% of MSCI EM** and **12.47% of MSCI EM IMI**. The two factsheets carry different dates, which were not captured. — [MSCI EM Index factsheet](https://www.msci.com/documents/10199/c0db0a48-01f2-4ba9-ad01-226fd5678111); [MSCI EM IMI factsheet](https://www.msci.com/documents/10199/edec59a6-b41e-44c4-9cf4-1e82863cfda7)
- [Secondary, figures vary slightly by source] Weight path:
  - peak of roughly **19–21% in Sep 2024**
  - **~14.1%** at the Feb 2026 review
  - **11.94% on 30 Apr 2026**
  - **~12% in May 2026**
  
  India slid to **fourth**, behind China, Taiwan and South Korea. — [Republic World](https://www.republicworld.com/business/indias-msci-em-weight-falls-under-14-ranking-slides-to-fourth); [Moneycontrol via TradingView](https://www.tradingview.com/news/moneycontrol:63f5cf591094b:0-india-s-weight-in-msci-em-index-falls-to-near-covid-lows-as-flows-shift/); [Investing.com India](https://in.investing.com/analysis/indias-msci-em-weight-normalises-a-return-to-fundamentals-200638317); [Vajiram & Ravi](https://vajiramandravi.com/current-affairs/msci-rebalancing/); [Bonvista](https://www.bonvista.in/blog/msci-index-rebalancing-impact-indian-stocks)
- [Estimate, secondary blog] Each **1-percentage-point fall in India's EM weight ≈ $1.5–2bn of passive outflow**. Part of the May 2026 FPI selling was tied to passive rebalancing. — [Finnovate, Apr 2026](https://www.finnovate.in/learn/blog/fpi-selling-india-half-april-2026-bfsi-sectoral-flows); [Finnovate, May 2026](https://www.finnovate.in/learn/blog/fpi-flows-may-2026-india-sectoral-analysis)

**Index-provider market and Indian regulation**
- [Estimate] **Burton-Taylor:** MSCI had **24.9% of index-provider revenue in 2024**, against S&P DJI's 25.4% (Bloomberg 3.1%). Global index revenues rose **13.4% in 2025 to a record $7.2bn**. — [Burton-Taylor Index Industry Benchmark Report 2025](https://tpicap.com/burtontaylor/sites/g/files/escbpb181/files/burton-taylor/reports/2025-04/Index%20Industry%20Benchmark%20Report%20-%20Burton%20Taylor_2025_FULL%20YEAR%202024_1.pdf); [Burton-Taylor 2026 report page](https://tpicap.com/burtontaylor/reports/2026index-industry-benchmark-report)
- [Primary/Secondary] The **SEBI (Index Providers) Regulations, 2024** were notified on **8 Mar 2024**:
  - index providers administering "significant indices" based on Indian securities must be registered
  - indices only of global asset classes, or only for use in a foreign jurisdiction, are excluded
  - commentators say global providers such as MSCI may not need to register unless domestic AMCs use their indices widely
  
  Sources disagree on the effective date (118th vs 180th day after notification). — [SCC Online](https://www.scconline.com/blog/post/2024/03/13/sebi-issues-sebi-index-providers-regulations-2024-legal-news/); [Cafemutual](https://cafemutual.com/news/industry/31623-sebi-to-regulate-index-providers); [Taxmann](https://www.taxmann.com/post/blog/sebi-notifies-index-providers-regulations-to-enhance-transparency-accountability-in-index-governance/); [TaxGuru](https://taxguru.in/sebi/securities-exchange-board-india-index-providers-regulations-2024.html); [Lexology/ERGO](https://www.lexology.com/library/detail.aspx?g=390df37c-f1eb-41d3-98f6-ad5d7bbcb062)
- [Secondary] A SEBI consultation proposed that an index is "significant" if domestic MF schemes tracking or benchmarking to it hold **more than ₹20,000 crore** of AUM. The draft list named **NSE Indices, BSE Index Services and CRISIL, not MSCI**. Whether this was finalised: not confirmed. — [Regstreet Law Advisors](https://regstreetlaw.com/blog/sebi-issues-consultation-paper-on-significant-indices-under-index-provider-regulations-2024/)
- [Primary] MSCI ran an India client event in **December 2025** ("MSCI India Presents – Decoding the new DNA of Indian markets"). Its deck was titled "MSCI Index Inclusion: A Roadmap to International Capital and Investor Access". Content not retrieved. — [MSCI event deck (PDF)](https://www.msci.com/downloads/web/msci-com/discover-msci/events/event-assets/2025/december/msci-india-presents-%E2%80%93-decoding-the-new-dna-of-indian-markets/MSCI%20Index%20Inclusion_A%20Roadmap%20to%20International%20Capital%20and%20Investor%20Access.pdf)

### Inferences
- For Indian domestic managers, MSCI India indices matter mainly in three ways:
  1. their rebalances (Feb/May/Aug/Nov) and foreign-room changes drive FPI passive flows and rebalance-day liquidity
  2. they are the benchmark for India-dedicated offshore funds, feeder funds and GIFT-City vehicles
  3. a domestic manager measured against MSCI India, rather than the India Domestic index or Nifty, carries structural active risk in FOL-constrained names
- That no Indian MF benchmark data surfaced, together with MSCI's absence from SEBI's draft significant-index list, suggests little domestic-MF use of MSCI India as a primary benchmark.
- A self-built tracker can monitor MSCI announcements and foreign-room changes (via NSDL/depository FPI-limit data) as event signals.

### Gaps
- Constituent counts for **MSCI India** (standard) and **MSCI India Small Cap** in 2026: not retrieved.
- Number of Indian MF/PMS schemes benchmarked to any MSCI index: not found.
- **Index data licence fees** (benchmark-use or ETF-licence basis points; data-feed costs): no public figures found.
- Whether MSCI applied for or holds SEBI index-provider registration, and whether the "significant index" list was finalised: not confirmed.
- AUM of ETFs tracking MSCI India and MSCI India futures listings: not researched.

## Q5. Axioma (SimCorp), Northfield and other risk-model vendors covering India; any India-local vendors

### Takeaway
- **Axioma**, now "Axioma by SimCorp" within Deutsche Börse, covers India through its global **Worldwide Equity Factor Risk Model (WW5.1, May 2025)** and a **Trading Horizon** variant (Jan 2026). No India single-country Axioma model was found.
- **Northfield** covers India inside its global and "Everything Everywhere" models, with no India model.
- **Bloomberg PORT's MAC3 suite** includes a **local India equity model**. It is the only non-MSCI India-specific commercial model found.
- **FactSet** distributes Barra and Axioma models rather than an India model of its own.
- No Indian commercial factor-risk-model vendor was found. The main local factor resource is the free **IIM Ahmedabad Fama-French and momentum data library**.

### Cited Findings
**Axioma (SimCorp)**
- [Primary] Ownership:
  - Axioma was part of **Qontigo** (Deutsche Börse) from **2019**
  - Deutsche Börse acquired **SimCorp in Sep 2023**
  - the **SimCorp–Axioma merger** was announced in **Nov 2023**
  - SimCorp's 2026 releases describe it as a Deutsche Börse Group subsidiary
  
  — [PR Newswire, Nov 2023](https://www.prnewswire.com/news-releases/simcorp-to-merge-with-axioma-combining-best-in-class-risk-analytics-and-portfolio-construction-with-its-industry-leading-investment-management-platform-301979993.html); [SimCorp news, Jan 2026](https://www.simcorp.com/about-us/news/2026/simcorp-launches-risk-model-to-support-short-horizon-trading)
- [Vendor claim] **Axioma Worldwide Equity Factor Risk Model (WW5.1)**: a multi-factor global model for medium- and short-horizon institutional portfolios across developed and emerging markets. — [SimCorp WW5.1 page](https://www.simcorp.com/solutions/point-solutions/Axioma-Solutions/axioma-factor-risk-models); [Arcana WW5.1 handbook listing](https://help.arcana.io/en/articles/15014378-axioma-worldwide-equity-factor-risk-model-ww5-1-methodology-handbook-pdf)
- [Vendor claim] The **May 2025** next-generation release added factors including **Short Interest, Opinion Divergence, Downside Risk, Investment** and a **Non-linear Residual Structure**. — [SimCorp news, May 2025](https://www.simcorp.com/about-us/news/2025/simcorp-launches-improved-axioma-worldwide-equity-factor-risk-model)
- [Vendor claim] **Trading Horizon model** (7 Jan 2026): aimed at managers who rebalance daily or weekly. It is sold standalone or within the **Axioma Risk** suite on **SimCorp One**. A third-party aggregator gives a 20-day horizon, which I could not confirm from SimCorp's release. — [SimCorp news, Jan 2026](https://www.simcorp.com/about-us/news/2026/simcorp-launches-risk-model-to-support-short-horizon-trading); [Cision release](https://news.cision.com/simcorp/r/simcorp-launches-global-axioma-equity-factor-risk-model-to-support-short-horizon-trading-after-volat,c4289200); [Trading-model page](https://www.simcorp.com/solutions/point-solutions/Axioma-Solutions/trading-model); [allmind.ai (aggregator)](https://allmind.ai/news/b750c58a18e8e22cfdc4d77a54cd2fd289a66f59eb6fdb77c0bb878dfadf199d)
- [Vendor claim] **Axioma Factor Library Suite** (27 Feb 2026): proprietary research data on equity factors and macro exposures. The related offering lets clients build customised, strategy-specific risk models. — [Cision, Feb 2026](https://news.cision.com/simcorp/r/simcorp-empowers-quantitative-investment-managers-with-unique-research-data-to-design-investment-str,c4314140)
- [Vendor claim] **Axioma Risk** is described as a "cloud-native, multi-asset risk management system". In 2026 it added **AI-assisted stress testing**: users design scenarios and propose factor shocks in natural language. — [SimCorp: AI-powered stress testing (2026)](https://www.simcorp.com/about-us/news/2026/ai-powered-stress-testing)
- [Vendor claim] Two Axioma global multi-asset **fund-allocation risk models** launched in Nov 2024. — [SimCorp news, Nov 2024](https://www.simcorp.com/about-us/news/2024/SimCorp-launches-Axioma-fund-allocation-risk-models); [The Asset](https://www.theasset.com/article/52943/simcorp-unveils-fund-allocation-risk-models)
- [Primary, legacy] **AXWW4**:
  - a medium-horizon (3–6 month) and a short-horizon (1–2 month) model
  - country factors, plus a special local factor only for **Domestic China**
  - **no India-specific local factor**
  
  — [AXWW4 factsheet](https://cdn2.hubspot.net/hubfs/2174119/Return%20Downloads/Factsheet-AXWW4-2.pdf)
- [Primary] FactSet's **MAC III** multi-asset model uses Axioma AXWW4 for equities. — [FactSet MAC III / Axioma white paper](https://advantage.factset.com/hubfs/Website/Resources%20Section/White%20Papers/mac-risk-model-axioma-white%20paper.pdf)
- [Vendor claim] Axioma's client types: asset managers, asset owners, hedge funds, wealth managers and sell-side firms. — [SimCorp Axioma Solutions](https://www.simcorp.com/solutions/axioma-solutions)
- [Vendor claim] Distribution and integration partners include Charles River, Equity Data Science, Limina and Jacobi. — [CRD–Axioma](https://info.crd.com/CRD-Axioma); [EDS](https://equitydatascience.com/company/partners/axioma-by-simcorp/); [Limina](https://www.limina.com/blog/why-we-partnered-with-qontigo-axioma-risk); [Jacobi](https://www.jacobistrategies.com/jacobi-insights/jacobi-has-announced-a-partnership-with-axioma-a-leading-global-provider-of-factor-risk-models-portfolio-construction-tools-and-enterprise-risk-solutions/)

**Northfield**
- [Vendor claim, dated] **Everything Everywhere (EE)** model: **61,000+ equities from 68 developed and emerging countries, 57 currencies**. — [Northfield EE page](https://www.northinfo.com/resource-details.php?id=1)
- [Vendor claim, dated] Global equity model: **80 countries, 69 currencies**. The two counts conflict with each other. — [Northfield Global Equity Risk page](https://www.northinfo.com/resource-details.php?id=5)
- [Vendor claim] Northfield's single-country and regional models are Asia Pacific, Australia, Brazil, Canada, China, Europe, Japan, South Africa, Switzerland, UK and US. **No India model.** India appears only as a row (rank 4, 1.09% contribution) in a factor-contribution table in a workshop deck. — [Northfield product listing](https://www.northinfo.com/searchreg.php?keywords=asset); [Northfield XRD equity models](https://www.northinfo.com/resource-details.php?id=20); [Northfield Global Equity Risk Models workshop (PDF)](https://www.northinfo.com/Documents/1009.pdf)
- [Vendor claim] Northfield analytics are available inside Charles River IMS. — [CRD–Northfield](https://info.crd.com/CRD-Northfield)

**Bloomberg, FactSet and newer entrants**
- [Vendor claim] **Bloomberg MAC3** has the MAC3 Global Equity Model plus **13 local equity models, including India**. PORT uses these models for ex-ante tracking error and VaR, and for factor-based attribution that splits returns into factor and selection effects. — [Bloomberg MAC3 page](https://www.bloomberg.com/professional/products/risk/mac3); [Bloomberg insight on MAC3 satellite factors](https://www.bloomberg.com/professional/insights/data/the-benefits-and-impact-of-including-satellite-factors-in-mac3-equity-models/); [PORT brochure](https://data.bloomberglp.com/professional/sites/4/Portfolio_and_Risk_Analytics_Brochure4.pdf)
- [Vendor claim] FactSet Portfolio Analytics hosts Barra, MSCI and Axioma models, plus Quant Insight's macro-factor equity model. No FactSet-built India model was found. — [Quant Insight](https://www.quant-insight.com/insight/quant-insight-brings-macro-factor-equity-risk-to-factset-portfolio-analytics)
- [Vendor claim] Low-cost entrants market themselves as Barra/Axioma alternatives (e.g., "equity risk decomposition by API"). — [riskmodels.app](https://riskmodels.app/compare/barra-axioma); [Genesis RM blog (2026)](https://genesis-rm.com/blog/affordable-barra-risk-metrics-alternatives)

**India-local factor data (relevant to a self-built tracker)**
- [Primary] The **IIM Ahmedabad "Fama French and Momentum Factors" data library**:
  - built by IIMA from **CMIE Prowess DX**
  - "New Series" launched **Dec 2021**, with history from **Oct 1993**
  - **three releases a year** (March, September, December)
  - covers BSE and NSE listings
  - **drops micro-cap and penny stocks** with market-cap and price filters
  - returns are **corrected for survivorship bias** (delisted companies)
  
  The archive lists releases from 2021-03 to 2025-03. — [IIMA data library](https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/); [archive](https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/archive.php)
- [Primary] The legacy series was suspended in 2020 and ends in 2019. Standard citation: Agarwalla, Jacob & Varma (2013), "Four factor model in Indian equities market", IIMA WP 2013-09-05. — [IIMA legacy page](https://web.iima.ac.in/~iffm/legacy/); [IIMA working paper](https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/four-factors-India-90s-onwards-IIM-WP-Version.pdf); [J.R. Varma's page](https://www.jrvarma.in/fama-french.html)
- [Secondary] Academic work tests four- and five-factor models on Indian equities. — [Rajan Raju, SSRN 4054146](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4054146)

### Inferences
- An India-only manager has three practical India-specific commercial models: **MSCI INE2, Bloomberg MAC3 India, and possibly custom Axioma models** built through the 2026 "bespoke risk model" capability. Everyone else (Axioma WW, Northfield, Barra GEMLT) treats India as one country inside a global model.
- Bloomberg's India model is probably the cheapest add-on for AMCs that already pay for Bloomberg terminals; it comes bundled with PORT. This is inference from bundling; I have no price data.
- IIMA factor returns show India's factor premia, but they are not a risk model. They have no factor covariance forecasts, no stock-specific risk and no industry structure. A self-built tracker using them would still lack the ex-ante risk machinery that the commercial models provide.

### Gaps
- Axioma's emerging-markets or Asia-Pacific regional models and their India coverage (security counts, any local India factors): not found. Whether an Axioma India single-country model exists: not found.
- Northfield's current ownership and status in 2026: not found.
- Bloomberg MAC3 India: factor list, estimation universe and update frequency not retrieved.
- India-local commercial factor-risk-model vendors (e.g., from CMIE, NSE data services, CRISIL or ICRA analytics): **none found**. Absence of search evidence is not proof that none exist.
- Other global vendors not covered: S&P Global, Confluence/Style Analytics, Morningstar risk models.

## Q6. Pricing: licence costs for BarraOne, Barra models, MSCI ESG data and index licences

### Takeaway
MSCI, SimCorp/Axioma and Northfield publish **no list prices**. The only figures are third-party estimates (2026):
- **BarraOne:** about **$50k–$150k+ a year** from a competitor, or **$100k–$250k a year** "starting" from a finance blog, scaling with AUM, users and modules
- **Axioma:** described as modular, with a **lower entry cost** than BarraOne

At company level, MSCI's run rates at 31 Dec 2025 were **$757.4m** for Analytics (risk models, BarraOne and similar) and **$378.1m** for Sustainability & Climate. No public figures exist for ESG-data or index-licence fees.

### Cited Findings
- [Primary/aggregator] No official BarraOne price. G2 says the vendor "has not provided pricing information"; Capterra lists "Contact vendor". — [G2](https://www.g2.com/products/barraone/pricing); [Capterra (2026)](https://www.capterra.com/p/59716/BarraOne/)
- [Estimate; competitor's blog] Enterprise BarraOne/RiskMetrics licences "typically ranging from **$50,000 to $150,000+ per year**" depending on asset classes and number of users. — [Genesis RM, 2026](https://genesis-rm.com/blog/affordable-barra-risk-metrics-alternatives)
- [Estimate; secondary] BarraOne enterprise licensing "typically starts at **$100,000 to $250,000 annually**", scaling with AUM, number of users and data modules. Axioma is described as having "modular pricing, lower entry cost than BarraOne". Undated page. — [FatFire: MSCI BarraOne](https://fatfire.com/msci-barraone/)
- [Primary] **MSCI FY2025 results** (as of 31 Dec 2025):

  | Segment | Run rate | Growth | Organic growth | FY retention |
  |---|---|---|---|---|
  | Analytics | $757.4m | +8.4% | 7.0% (recurring subscription) | 94.3% |
  | Sustainability & Climate (renamed from "ESG and Climate" in 2025) | $378.1m | +10.0% | 4.9% | 93.2% |

  Company-wide Q4 2025 retention was 93.4%. — [MSCI Q4/FY2025 results release](https://ir.msci.com/news-releases/news-release-details/msci-reports-financial-results-fourth-quarter-and-full-year-2025)
- [Primary] At Q3 2025, Analytics run rate was $742.4m (+7.4%) and Sustainability & Climate $370.8m (+7.8%). — [MSCI Q3 2025 results release](https://ir.msci.com/news-releases/news-release-details/msci-reports-financial-results-third-quarter-and-nine-months-10)
- [Estimate] In Burton-Taylor's 2022 research-analyst data-spend share chart: FactSet 19.3%, Bloomberg 17.8%, **MSCI/Barra 2.3%**. This is a data-spend view, not risk-analytics market share. — [Burton-Taylor: Research Analysts' Data Usage (2023)](https://tpicap.com/burtontaylor/sites/g/files/escbpb181/files/burton-taylor/reports/2023-09/Research%20Analysts%20Data%20Usage.pdf)
- [Estimate] Index-licensing market context: MSCI held 24.9% of index-provider revenue in 2024; the industry total was $7.2bn in 2025 (see Q4). — [Burton-Taylor 2025](https://tpicap.com/burtontaylor/sites/g/files/escbpb181/files/burton-taylor/reports/2025-04/Index%20Industry%20Benchmark%20Report%20-%20Burton%20Taylor_2025_FULL%20YEAR%202024_1.pdf); [Burton-Taylor 2026](https://tpicap.com/burtontaylor/reports/2026index-industry-benchmark-report)

### Inferences
- **Rupee terms.** At an *assumed* ~₹90/USD (my assumption, not sourced), the third-party BarraOne range is roughly **₹45 lakh to ₹2.25 crore a year**. That is affordable for large AMCs and insurers but heavy for small PMS firms or boutique AMCs. A single-model data licence (e.g., INE2 flat files) or a terminal-bundled tool (Bloomberg PORT) would likely cost less. That is directional inference with no figures found.
- **Bias in the estimates.** Both price sources benefit from making BarraOne look expensive: one is a competitor, the other an affiliate-style blog. The figures are probably neither lower nor upper bounds, only order-of-magnitude.

### Gaps
- Actual quotes or contract values for BarraOne, BPM, single Barra models (INE2, GEMLT), RiskManager or LiquidityMetrics: none public. Same for Axioma and Northfield.
- MSCI ESG Ratings data-feed pricing for Indian coverage; subscriber-pays ERP fee levels: not found.
- MSCI index licence fees (benchmark data, ETF/derivative licences in bp of AUM): not found.
- Chartis RiskTech100 and Celent rankings and pricing commentary for MSCI, SimCorp/Axioma or Bloomberg: not researched within the tool-call budget.

## Q7. Adoption in India: which Indian AMCs, insurers or PMS firms use MSCI Barra, Axioma or similar

### Takeaway
Public evidence naming Indian users is **very thin**. The datapoints found:
- an academic case study comparing **BarraOne and Bloomberg** tracking-error measures for **SBI Mutual Fund**
- MSCI's **SEBI-registered Indian ESG ratings entity** and a December 2025 India client event
- IIM Indore's academic access to MSCI ESG data
- risk-analytics hiring by global managers' Mumbai offices (e.g., Russell Investments)

No vendor press release or Indian press report naming an Indian AMC, insurer or PMS as a BarraOne, BPM, Axioma or Northfield client was found.

### Cited Findings
- [Secondary, academic] "Tracking Error Performance – A case study on SBI Mutual Fund" by Maheen M and Dr. Resia Beegam S. It examines how well **Bloomberg and BarraOne** measure ex-ante and ex-post tracking error for **SBI Mutual Fund**. One search summary said the study found BarraOne's ex-ante tracking error diverging from Bloomberg's, with both converging towards ex-post over time. A second search could not confirm the conclusions, so treat them as **unverified**. — [SSRN 3635138](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3635138); [ResearchGate](https://www.researchgate.net/publication/362468473_Tracking_Error_Performance_-A_case_study_on_SBI_Mutual_Fund)
- [Primary] MSCI ESG Ratings and Research Private Limited is a SEBI-registered ERP (Aug 2024, subscriber-pays; see Q3). This shows MSCI operating a regulated ESG-ratings business in India. — [SEBI board memo, Dec 2024](https://www.sebi.gov.in/sebi_data/meetingfiles/dec-2024/1735215341884_1.pdf)
- [Primary] IIM Indore's library provides access to the MSCI ESG Ratings Time Series (user guide uploaded Oct 2025). — [IIM Indore user guide](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-MSCI-ESG-Ratings-Time.pdf)
- [Primary] MSCI held an India-market event in December 2025 ("MSCI India Presents"). — [MSCI event deck](https://www.msci.com/downloads/web/msci-com/discover-msci/events/event-assets/2025/december/msci-india-presents-%E2%80%93-decoding-the-new-dna-of-indian-markets/MSCI%20Index%20Inclusion_A%20Roadmap%20to%20International%20Capital%20and%20Investor%20Access.pdf)
- [Secondary] Built In lists an **Investment Risk Analyst role at Russell Investments in Mumbai (Goregaon East)**: developing and maintaining the Enterprise Risk Management System, implementing risk models and automating reporting. The excerpt did not name Barra or Axioma. This is a global manager's India captive, not an Indian AMC. — [Built In job listing](https://builtin.com/job/investment-risk-analyst/3141250)
- [Secondary] Job-board aggregations of 2026 postings (mostly US) list Barra, Axioma or BarraOne as desired skills, often alongside Bloomberg, FactSet and Aladdin. — [ZipRecruiter: Barra Factor jobs](https://www.ziprecruiter.com/Jobs/Barra-Factor)
- [Estimate, low quality] A third-party technographics site estimates BarraOne's customer mix: financial services 40%, investment management 9%, banking 7%, insurance 5%. It shows no India breakdown. — [Enlyft](https://enlyft.com/tech/products/msci-barraone)
- [Secondary] Public customer announcements that do exist are non-Indian:
  - Wurts & Associates selected BarraOne (US, 2012)
  - BNP Paribas AM Netherlands implemented BarraOne (2017, per a third-party customer database)
  - Natixis/Mirova chose Axioma
  
  — [MSCI press release: Wurts & Associates](https://www.msci.com/documents/10199/52df8cae-d5ce-485e-adb1-ea5330b0ef96); [Apps Run The World: BarraOne customers](https://www.appsruntheworld.com/customers-database/products/view/msci-barraone); [FactSet/Axioma–Natixis release](https://investor.factset.com/news-releases/news-release-details/axioma-and-factset-deliver-market-risk-solutions-mirova-and-natixis-asset-management)

### Inferences
- The SBI MF study suggests that, around its writing, SBI Funds Management (India's largest AMC) had access to BarraOne alongside Bloomberg. This is inference from the study design, not a vendor-confirmed contract, and may be dated.
- The near-absence of announcements fits two things: vendors generally don't publicise Indian buy-side wins, and Indian AMCs rarely disclose their analytics vendors. Adoption is most likely concentrated in three groups:
  - large AMCs and insurers
  - foreign-parented AMCs, which inherit global stacks
  - global managers' Indian captive centres in Mumbai, Pune and Bengaluru
  
  This is inference. A useful check would be AMC risk-management-policy disclosures and LinkedIn job posts at specific AMCs, which were not reachable in this session.
- Bloomberg PORT is plausibly the most widespread factor-risk tool at Indian AMCs, given terminal penetration and the India MAC3 model. This is inference; there is no survey data.

### Gaps
- No named Indian AMC, insurer or PMS user of BarraOne, BPM, Barra models, Axioma or Northfield was found in press, vendor releases or job postings.
- No Indian industry survey (AMFI, CFA Society India, consultancies) on risk-system usage was found.
- The SBI MF study's date, scope and conclusions were not verified (full text not retrieved).

## Q8. Known limitations for India-focused managers (small/micro-cap coverage, small-cap liquidity, model fit, cost)

### Takeaway
For an India-only manager:
- **Global models are a weak fit.** They reduce India to one country factor plus global styles and industries. AXWW4, for example, gave a special local factor only to China A-shares.
- **Only a few India-specific models were found:** MSCI INE2 and Bloomberg MAC3 India. Their estimation universes, and so their small- and micro-cap coverage, could not be verified.
- **Index-anchored universes are narrow.** MSCI India IMI has ~626 names.
- **Small-cap liquidity is now a regulated disclosure.** SEBI/AMFI stress tests show 25–59 days to liquidate half of large small-cap portfolios, and that measure follows India-specific rules rather than vendor models.
- **Cost:** order-of-magnitude six-figure USD licences (estimates).
- **ESG:** relevance is now set by SEBI's ERP and BRSR Core regime rather than by global ratings alone.

### Cited Findings
- [Primary] In global Barra models the commonality in returns is captured by country, industry and style factors. GEM3 listed India as one of 77 country factors, and GEMLT spans 87 countries with one set of 16 global style factors. — [GEM3 brochure](https://www.msci.com/documents/10199/242721/Barra_Global_Equity_Model_GEM3.pdf); [GEMLT factsheet](https://www.msci.com/documents/10199/242721/GEMLT_FactSheet.pdf)
- [Primary] Axioma's AXWW4 added a local market factor only for **Domestic China**, not India. — [AXWW4 factsheet](https://cdn2.hubspot.net/hubfs/2174119/Return%20Downloads/Factsheet-AXWW4-2.pdf)
- [Primary] Index-anchored universes are narrow: MSCI India IMI had **626 constituents** (Aug 2026). The IIMA factor library deliberately **drops micro-cap and penny stocks** as outside most investors' investable universe. — [MSCI India IMI page](https://www.msci.com/indexes/index/664231/msci-india-imi-index); [IIMA data library](https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/)
- [Secondary] Small-cap illiquidity:
  - 25–57 days to liquidate 50% of high-risk small-cap MF portfolios (Mar 2025)
  - 59 days for SBI Small Cap (May 2026)
  - one ₹25,500 crore fund would need a month for 25% and 60 days for 50% (Business Standard editorial, Mar 2024)
  
  — [BusinessToday](https://www.businesstoday.in/personal-finance/investment/story/mf-investors-exiting-small-cap-funds-may-take-weeks-in-a-crisis-stress-test-shows-472692-2025-04-19); [Bajaj Broking](https://www.bajajbroking.in/share-market-news/midcap-and-smallcap-fund-stress-test-may-2026-data); [Business Standard editorial: Redemption risks](https://www.business-standard.com/opinion/editorial/redemption-risks-124031901084_1.html)
- [Primary] MSCI's liquidity product is framed around UCITS, AIFMD, SEC 22e-4 and Form PF, not SEBI or AMFI methods. — [LiquidityMetrics factsheet](https://www.msci.com/documents/1296102/8335426/MSCI_LiquidityMetrics_Factsheet.pdf/1ef81401-d1d4-6e84-834c-f03d3225c318)
- [Primary] FOL and foreign-room rules make MSCI's FPI-oriented India indices diverge from the domestic investable universe, which is why MSCI runs separate India Domestic indices based on the DIF. — [MSCI GIMI methodology (India Domestic), 2015](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Feb15_GIMIMethod_with_India_Dom_Final.pdf); [MSCI India Domestic Index factsheet](https://www.msci.com/documents/10199/af0a5885-9cfd-441f-9071-e8de1b0ef4e7)
- [Estimate] Cost: BarraOne at roughly $50k–$250k+ a year (see Q6). — [Genesis RM](https://genesis-rm.com/blog/affordable-barra-risk-metrics-alternatives); [FatFire](https://fatfire.com/msci-barraone/)
- [Secondary, unverified conclusion] Ex-ante tracking error for the same Indian MF portfolio may differ between vendors (BarraOne vs Bloomberg). — [SSRN 3635138](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3635138)
- [Primary] For SEBI ESG schemes, the regulatory test is **BRSR Core assurance** plus disclosure of scores from SEBI-registered ERPs, not a particular global rating. — [SEBI ESG circular, 20 Jul 2023 (copy)](https://www.skylinerta.com/pdf_file/51_671021621_SEBICircular-ESG-DisclosurebyMutualFund-20.07.2023.pdf)

### Inferences
- **Model fit.** Without INE2 or MAC3 India, an Indian portfolio's risk is mostly "India country factor + stock-specific". Two things go unmodelled:
  - local style and industry effects that India's market structure may produce, such as PSU/state-ownership, promoter-holding concentration, and retail- or F&O-driven momentum and volatility
  - Indian trading frictions: circuit limits, F&O ban lists and periodic call auctions
  
  This is inference; no vendor document found addresses these features.
- **Small and micro caps.** If a model's estimation universe follows MSCI India IMI (~626 names), stocks outside it get covered only by mapping, through industry/style proxies and specific-risk estimates. Exposure and risk numbers for micro caps, SME-platform stocks and recent IPOs should be treated cautiously. This is inference, and the universe sizes are unverified.
- **Liquidity.** Indian managers' binding liquidity measure is the SEBI/AMFI days-to-liquidate test. Vendor liquidity models add market-impact and cost estimates but don't replace it. A self-built tracker can compute the SEBI-style measure directly.
- **Benchmark mismatch.** Global vendors' India indices are FPI-oriented, with FOL and foreign-room effects, while domestic funds benchmark to Nifty/BSE indices. Any factor-risk tool needs the domestic benchmark constituents loaded, which is a data-licensing issue: NSE/BSE index data licences are separate from MSCI's.
- **Cost against alternatives.** For small AMCs and PMS firms, a six-figure USD licence competes with Bloomberg PORT (bundled), FactSet-hosted models and in-house models built on IIMA factor data plus exchange data. The self-built route gives up forecast-quality covariance, stock-specific risk and optimiser integration in exchange for cost and India-specific flexibility.

### Gaps
- **Empirical comparisons:** none found of Barra or Axioma model fit on Indian equities (bias statistics, R² of country/industry/style factors for India, forecast vs realised tracking error).
- **India security coverage counts** for Barra GEMLT, INE2, Axioma WW5.1 and Bloomberg MAC3 India: not found.
- **Practitioner critiques** (Indian press, CFA Society India) of vendor risk models for Indian small caps: not found.
