# Indian equity data, research and analytics vendors used by institutional managers (state as of October 2026)

> **Method and source-access note (read first).** Research date: 2026-10-10.
> - **No page could be opened directly.** The session's egress proxy answered HTTP 403 to CONNECT for www.nseindia.com, nsearchives.nseindia.com, taxmann.com, help.trendlyne.com, screener.in, entrackr.com, outlookbusiness.com and crisil.com. Per instructions, none of these was retried or worked around. The WebFetch tool also failed DNS resolution for every host.
> - **What the findings rest on.** Every finding below comes from web-search extracts of the cited pages, meaning the search tool's own reading of each page. The cited URL is the page the extract describes.
> - **NSE tariff figures need checking.** The search tool flagged that the tables in NSE's tariff PDFs extracted in a "garbled" form. Verify those figures against the PDFs before quoting them externally.
> - **The search budget ran out early.** The session's shared web-search budget was used up before several planned checks. These are listed under Gaps: Screener.in's terms of use and data source, Tickertape's estimate source, Tijori's data sourcing, CRISIL Coalition, Capitaline and CMIE list prices, NSE Indices licensing, and the primary SEBI circular texts.
> - **Labels.**
>   - *(vendor claim)*: the vendor describing itself.
>   - *(aggregator)*: an estimate from a third-party company database (Tracxn, Company Check, CB Insights and similar).
>   - *(third-party)*: a reviewer, consultancy or comparison site.
>   - *(dated)*: a fact older than 2025.
>   - Untagged: a statement taken from the cited document itself.

## 1. Institutional data vendors: CMOTS, Capitaline, ACE (Accord Fintech), CMIE Prowess, CRISIL, ICRA Analytics, NSE and BSE data products

### Takeaway
- **Fundamentals databases.** A handful of long-standing domestic database vendors sell standardised Indian fundamentals for roughly 35,000–60,000 listed and unlisted companies:
  - CMIE Prowess, with history since 1989-90/1990;
  - Capitaline and its apparent sister firm C-MOTS;
  - Accord Fintech's ACE Equity;
  - CRISIL Quantix.
- **How they sell.** They sell by quote through terminal or desktop software, Excel export and API or datafeed. Their only public price anchors are professional-association discounts, for example ₹25,000 per login per year for a Capitaline product.
- **Exchange data.** Exchange data is licensed separately. NSE Data & Analytics publishes tariffs, such as ₹1 lakh a year for end-of-day data and ₹10.6 lakh a year for the corporate-data feed. BSE also publishes a tariff sheet. Redistributing exchange data to clients requires written consent from the exchange.

### Cited Findings

#### C-MOTS / CMOTS (CMOTS Internet Technologies Pvt Ltd, "CMOTS Infotech")
- **Company basics (aggregator).** Mumbai-based. Tracxn says it was founded in 1997 by Ruby Anand, is unfunded and had 260 staff as of 31 Jul 2025 — [Tracxn](https://tracxn.com/d/companies/cmots-infotech/__KXgCMqPDl7PUoHa6d9RLap1S4Rmdgv3RhG2LGaFY0BA). LinkedIn lists 201–500 employees — [LinkedIn](https://in.linkedin.com/company/cmots-internet-technologies).
- **Products (company profiles; vendor claim).**
  - APIs covering equities, mutual funds, commodities, currencies, company information, announcements and derivatives.
  - Custom software, mobile-app and website development and hosting.
  - Fintech modules: eKYC, CRM, portfolio tracking, IPO processing.
  - Claims ISO 9001:2015 certification.
  - Sources: [Tracxn legal-entity profile](https://tracxn.com/d/legal-entities/india/cmots-internet-technologies-private-limited/__z4Azg2QgkuXosScB3dH4EdCnxslDBWTQUM321QEKW0s); [Crunchbase](https://www.crunchbase.com/organization/cmots-internet-technologies).
- **Brands (aggregator).** Tracxn lists Capitaline, APIDataFeed and Chartink as brands associated with CMOTS Internet Technologies Pvt Ltd — [Tracxn legal-entity profile](https://tracxn.com/d/legal-entities/india/cmots-internet-technologies-private-limited/__z4Azg2QgkuXosScB3dH4EdCnxslDBWTQUM321QEKW0s).
- **Website footprint.** BuiltWith tracks 84 live websites using CMOTS Infotech, plus 80 that used it historically. No client names were captured — [BuiltWith](https://trends.builtwith.com/agency/CMOTS-Infotech).
- **"CMOTS Market Data API" (third-party).** A consultancy page markets it for live stock prices, indices, forex and commodity data through customisable feeds into apps, dashboards and trading platforms — [FintegrationFS](https://www.fintegrationfs.com/fintechapis/cmots-market-data-feed).
- **ICAI arrangement (dated).** In 2016 the Institute of Chartered Accountants of India (ICAI) arranged C-MOTS's online transfer-pricing (TP) database for members at ₹12,000 per login. This comes from a search-extract summary of ICAI and press pages; which page holds which figure was not pinned down — [ICAI](https://www.icai.org/post/10431&c_id=278); [Taxscan](https://www.taxscan.in/?p=14635).

#### Capitaline (Capital Market Publishers India Pvt Ltd)
- **Company and database (vendor claim).**
  - Formed in 1986; says it "pioneered corporate databases and stock market publishing in India".
  - Capitaline covers 35,000+ listed and unlisted companies, and has expanded into economic data, sector data, mutual funds, commodities and news.
  - Sister product NAV India covers 5,000+ mutual fund schemes: NAVs, performance, rankings and portfolios.
  - The fortnightly *Capital Market* magazine gives individual investors database data through its "Corporate Scoreboard".
  - Sources: [CFA Society India member-offer document](https://cfasocietyindia.org/wp-content/uploads/Media-Uploads-Membership/Member-offers/Member-Offer-Document_for-Society_Capitalin2.pdf); [ICAI post](https://www.icai.org/post/16361).
- **Capitaline AWS TP.** A cloud-based browser version with financial and non-financial data on 35,000+ companies, "updated every day".
  - Under an ICAI agreement dated 5 Apr 2023 (three years), practising CAs could license it at ₹25,000 per login per year + GST, or ₹55,000 per login for three years paid upfront + GST — [ICAI](https://www.icai.org/post/16361); [ICAI (alt URL)](https://icai.org/post/tpcdcs).
  - Earlier ICAI deals: December 2019, ₹15,000 per login (online) and ₹65,000 (desktop) per year plus taxes; 2010, ₹10,000 plus taxes (dated) — [CAclubindia](https://caclubindia.com/news/icai-enters-into-an-arrangement-for-tp-corporate-database-at-a-concessional-rate-18089.asp); [ABCAUS](https://abcaus.in/icai/capitaline-tp-discounted-corporate-database-for-chartered-accountants.html).
- **Distribution.** Widely licensed to university libraries — [BITS Pilani library](https://library.bits-pilani.ac.in/databases/mumbai); [IIM Calcutta library](https://library-2.iimcal.ac.in/?p=14151).
- **Buy-side use.** A buy-side equity research job posting asks for "working knowledge of databases such as Bloomberg, Reuters, and Capitaline", and for attribution analysis in Bloomberg — [Green Lane Talent / Weekday job listing](https://jobs.weekday.works/bfsi-equity-research-analyst-buyside-at-green-lane-talent-management-wkdyo9npws).

#### ACE Equity, ACE Analyser, ACE MF and ACE Datafeed (Accord Fintech Pvt Ltd, Mumbai)
- **ACE Equity.** A corporate database of listed and unlisted companies with financial and non-financial data, updated daily over the internet — [IIM Calcutta library](https://library.iimcal.ac.in/ace-equity-business-knowledge-portal/).
- **ACE Equity Nxt.**
  - A Windows application with data hosted in the cloud, covering about 40,000 Indian companies and 1,750 financial data fields.
  - Non-financial data includes board members, shareholding patterns and corporate actions — [IIM Trichy library](https://library.iimtrichy.ac.in/ace-equity/).
  - A web version exists: an "ACE Equity Nxt Web" manual dated August 2026 is hosted by IIM Sambalpur — [IIM Sambalpur manual](https://library.iimsambalpur.ac.in/uploads/usermanuals/20260803161310_179ef2c6_ACE_Equity_Nxt_Web.pdf).
- **Older ACE Equity manual.** Lists Excel integration, a query module and corporate actions — [IIM Indore guide](https://iimidr.ac.in/wp-content/uploads/2021/04/AlphabeticalList-Ace_Equity_User_Guide.pdf).
- **ACE Knowledge and Research Portal.** A separate product; its user guide is dated October 2025 — [IIM Indore guide](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-ACE-Knowledge-and-Research-Portal.pdf).
- **ACE Analyser.** Listed as a product by a university library; no detail was captured — [JGU library](https://library.jgu.edu.in/content/ace-analyser/).
- **ACE Datafeed.**
  - Accord describes itself as an "Authorized data feed vendor of BSE/NSE/MCX/NCDEX exchange for their products" — [Accord Fintech](https://www.accordfintech.com/market-data-feed).
  - A third-party page says it delivers over FTP and API, covering equities, derivatives, IPOs, mutual funds and corporate announcements, with historical, real-time and end-of-day (EOD) data (third-party) — [FintegrationFS](https://www.fintegrationfs.com/fintechapis/accord-fintech).
- **Pricing.** No public price. The Indiamart listing shows only "Get Latest Price" — [Indiamart](https://m.indiamart.com/accordfintech/application-products.html).
- **CFA Society India.** Accord ran a member offer in 2021 (offer document) — [CFA Society India](https://cfasocietyindia.org/wp-content/uploads/2021/06/Accord-offer-document.pdf).

#### Prowess (CMIE: ProwessIQ and Prowess dx)
- **ProwessIQ.** A web-based interactive query system over the Prowess database.
  - Company counts in library guides vary from 37,780 to more than 51,500.
  - Access is tied to an institutional registration, and one ID works across all CMIE databases an institution subscribes to — [IIM Calcutta library](https://library.iimcal.ac.in/cmie-prowessiq/); [IIM Indore guide](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-CMIE-prowess-IQ.pdf); [JGU library](https://library.jgu.edu.in/content/prowessiq).
- **Prowess dx (bulk data delivery).**
  - Time-series data since 1990.
  - Covers all NSE- and BSE-listed companies plus unlisted public and private companies — [IIM Indore Prowess dx guide](https://iimidr.ac.in/wp-content/uploads/2024/08/CMIE-Prowess-dx.pdf); [IIM Calcutta library](https://library.iimcal.ac.in/cmie-prowessdx/).
  - Company counts range from 34,000 to 51,262 depending on the guide and its vintage — [IIM Libraries Consortium](https://www.iimlibrariesconsortium.in/eresources.html); [IIM Ahmedabad library](https://library.iima.ac.in/popular-databases.html).
- **Sources and history.** Prowess compiles data from annual reports, stock exchanges and other public sources, with time series since 1989-90 (dated tutorial) — [Scribd tutorial](https://www.scribd.com/doc/150672398/Prowess-Resource-Tutorial). M&A data runs from 1989 — [IIM Bangalore library](https://library.iimb.ac.in/database/ma).
- **Pricing.** No public price was found; access is negotiated institution by institution (search extracts from library pages above).

#### CRISIL (S&P Global company): Quantix, i360, research
- **Quantix (vendor claim).**
  - Crisil's "integrated data and analytics platform", built on Crisil's proprietary data.
  - Aimed at banking, financial services and insurance (BFSI) firms, corporates and consultants, for business strategy, loan origination, credit underwriting, risk monitoring and treasury or investment management.
  - Covers 60,000+ companies, including 20,000+ unrated ones, classified by GICS.
  - Web access by individual user ID, with Excel and PDF export and "flexible subscription options".
  - Sources: [Crisil Quantix](https://crisil.com/en/home/our-businesses/quantix.html); [Crisil data-as-a-service](https://intelligence.crisil.com/en/homepage/what-we-do/research/data-as-a-service.html).
- **Quantix on S&P Global Marketplace.** Modules are sold there, including "Company Financials" and a "Financial Sensitivity Model" — [S&P Marketplace: Company Financials](https://marketplace.spglobal.com/en/solutions/company-financials-quantix-(3081b719-fecf-419f-9641-639dabb576e8)); [S&P Marketplace: Financial Sensitivity Model](https://marketplace.spglobal.com/en/solutions/financial-sensitivity-model-quantix-(687a90ff-572b-4beb-9d80-1f3d16138f2c)).
- **i360.** In February 2026 Crisil launched i360, a "unified, GenAI-led research, data and analytics platform". It bundles Quantix with Cutting Edge, Navigator and a new impact-analytics engine called ForeSight (press release) — [LatestLY/PR Newswire](https://www.latestly.com/agency-news/business-news-crisil-launches-i360-a-unified-genai-led-research-data-and-analytics-platform-7330957.html/amp).
- **Fund research.** Crisil's mutual fund, alternative investment fund (AIF) and portfolio management service (PMS) data and ranking products are covered in section 4.

#### ICRA Analytics
- **Positioning (vendor claim).** Describes itself as a provider of "data, research and analytics on mutual fund, fixed income and other asset classes to fund managers, investors, lenders and intermediaries".
  - Also calls itself a "leading provider of valuation and information services to Indian mutual fund industry".
  - Maintains a proprietary database of mutual fund schemes going back to the industry's inception.
  - Clients include regulators, industry bodies, fund managers, government bodies and BFSI firms.
  - Sources: [ICRA](https://icra.in); [Craft.co](https://craft.co/icra-analytics).
- **MFI 360.** See section 4.

#### NSE data products (NSE Data & Analytics Ltd, NDAL)
- **Structure and coverage.** NSE's data and info-vending services are provided by NSE Data & Analytics Ltd, formerly DotEx International Ltd.
  - Segments covered: capital market (CM), F&O, currency derivatives, wholesale debt market (WDM), corporate data, corporate bond market data and securities lending and borrowing (SLBM).
  - Delivery is mainly by point-to-point leased line, with EOD and historical files over SFTP and cloud — [NSE Data & Analytics page](https://www.nseindia.com/nsedataandanalytics).
- **Product families** (from NSE feed specifications, May–August 2026):
  - Real-time products: Real Time Data, Snapshot Data, Corporate Data, Analytical Products data and Indicative NAV Data.
  - Historical products: End of Day and Historical Data.
  - Market depth: Level 1 is best bid and ask; Level 2 is up to 5 levels; Level 3 is up to 20 levels, over TCP/IP.
  - Sources: [Realtime Index Feed spec v1.29, May 2026](https://nsearchives.nseindia.com//web/mediaattachment/2026-05/Realtime_Index_Feed_Data_v1.29.pdf); [v1.30, Aug 2026](https://nsearchives.nseindia.com//web/mediaattachment/2026-08/Realtime_Index_Feed_Data_v1.30.pdf).
  - Snapshot products come at 1-, 2- and 5-minute intervals — [F&O L1/L2 spec v1.9, Jul 2026](https://nsearchives.nseindia.com//web/mediaattachment/2026-07/Real_time-FO-L1L2-V1.9.pdf).
- **Corporate data feed.**
  - Content: corporate announcements and quick results, company financial results, segment-wise results, and shareholding details (main, promoter, public and locked-in).
  - Delivery: a dedicated leased line. A separate "EOD Corporate Announcements" product arrives by SFTP after 8:00 PM IST daily.
  - Sources: [NSE corporate data technical spec](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Download_Technical_Specification_Corporate_Data.pdf); [NSE EOD corporate spec v1.1](https://nsearchives.nseindia.com/content/press/EOD_DATA-Corporate_EODv1.1.pdf); [NSE paid corporate data page](https://www.nseindia.com/static/market-data/corporate-data-subscription).
- **Other products.** NSE also publishes paid EOD and historical data and "analytical products" — [NSE paid EOD/historical](https://www.nseindia.com/static/market-data/eod-historical-data-subscription); [NSE analytical products](https://www.nseindia.com/static/market-data/analytical-products).
- **Non-display policy.** NSE has a separate Non-Display Policy; its content was not retrieved — [NSE Non-Display Policy PDF](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Non_Display_Policy.pdf).
- **Tariffs and licence rules.** See sections 5 and 6. Key points:
  - NSE says its pricing is effective 1 April 2026, with separate domestic and international tariffs — [NSE data & info vending](https://www.nseindia.com/static/nse-data-and-analytics/data-information-vending).
  - Delivering data to a vendor's clients as feeds needs written consent and a prior licence from NDAL — [NSE domestic pricing file, 9 Mar 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf).
- **Authorised vendors.** Licensed retail and SME channels include TrueData, Global Datafeeds, Accelpix and Accord. TrueData says per-user exchange fees "are levied as per the prevailing exchange tariff" and are included in its subscription price — [TrueData pricing](https://www.truedata.in/price); [Global Datafeeds](https://globaldatafeeds.in/global-datafeeds-nsebse-mcx-authorized-data-vendor/); [Accelpix pricing](https://accelpix.com/pricing/).

#### BSE data products
- **Domestic tariff.** BSE publishes an "Information Products Domestic Tariff Sheet", labelled February 2025.
  - It covers real-time, intraday and delayed feeds for indices and exchange-traded instruments, plus corporate data such as announcements, financial results and board meetings.
  - Prices exclude taxes and apply to datafeed customers in India who take data directly from BSE or through BSE-authorised vendors. Some items are marked free of charge.
  - The fee amounts were not captured — [BSE tariff sheet PDF](https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf).
- **Distribution.** BSE distributes real-time data directly over leased lines and through listed real-time and delayed-feed vendors — [BSE market data products](https://beta.bseindia.com/market_data_products.html?flag=real).
- **International customers.**
  - Deutsche Börse is the exclusive licensor of BSE India information products to international customers — [Deutsche Börse MDS](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/asian-markets/BSE-India-Index-and-Equity-Derivatives-1340710).
  - Deutsche Börse's price list shows "BSE India Spot Market Ultra" at €1,456 a month real-time and €728 delayed. Another version of the list, described in the extract as older, shows €1,870 and €935.
  - "BSE India Index and Equity Derivatives Ultra" is at no charge "until further notice" — [DB MDDA price list v10.1](https://mds.deutsche-boerse.com/resource/blob/2106722/5cdbe2f49af79af62ad8c7e1712e820d/data/MDDA_Price_List_10_1.pdf); [DB MDDA price list v10.8](https://mds.deutsche-boerse.com/resource/blob/2106704/0a84d6a16719420b0a2f8c7bf66698e7/data/MDDA_Price_List_10_8.pdf).
- **Data-quality and fairness case: SEBI order of 25 Jun 2025.**
  - SEBI fined BSE ₹25 lakh after finding that BSE's listing-compliance team and paying subscribers to a premium feed could see corporate filings before they appeared on BSE's public website.
  - Inspection period: Feb 2021–Sep 2022; show-cause notice: Sep 2024.
  - SEBI held this breached Regulation 39(3) of the Securities Contracts (Regulation) (Stock Exchanges and Clearing Corporations) Regulations, 2018 (SECC Regulations), which require "unrestricted, transparent and fair access". It also noted BSE never set up an RSS feed.
  - Sources: [Business Today](https://www.businesstoday.in/amp/markets/stocks/story/sebi-imposes-rs-25-lakh-fine-on-bse-for-unequal-data-access-oversight-failures-481863-2025-06-26); [Storyboard18](https://www.storyboard18.com/amp/how-it-works/sebi-slaps-rs-25-lakh-penalty-on-bse-for-granting-early-access-to-corporate-disclosures-71985.htm); [The Week/PTI](https://www.theweek.in/wire-updates/business/2025/06/26/dcm7-biz-stocks-bse.html).
  - Commentary says the premium feed "may have delivered announcements seconds before" public release (commentary/interpretation) — [Finshots](https://finshots.in/archive/the-bse-blip-sebi-couldnt-ignore/); [Basis Point Insight](https://basispointinsight.com/Story/Topic/sebi-catches-bse-red-handed--but-penalty-barely-scratches-the-surface_2287f81068cf.html).

#### Evidence of which institutions use these tools
- **Buy-side postings.** Indian buy-side and AIF/PMS-style job postings name Bloomberg, Reuters, Capitaline, Capital IQ and Refinitiv. In the sample, postings named Capitaline but not ACE Equity or Prowess — [Green Lane Talent listing](https://jobs.weekday.works/bfsi-equity-research-analyst-buyside-at-green-lane-talent-management-wkdyo9npws); [IIMJobs listing](https://www.iimjobs.com/j/investment-research-analyst-1638422?jobPos=11).
- **Academia.** ACE Equity, ACE MF, Prowess and Capitaline are standard IIM and university library subscriptions — [IIM Ahmedabad subject guide](https://subjectguide.iima.ac.in/subjects/databases.php?letter=All); [IIM Libraries Consortium](https://www.iimlibrariesconsortium.in/eresources.html).

### Inferences
- **CMOTS and Capitaline look like one group.** Tracxn lists Capitaline as a CMOTS brand, and ICAI's transfer-pricing database deal passed from C-MOTS (2016) to Capital Market Publishers (2019, 2023). This is unverified; confirm through Ministry of Corporate Affairs (MCA) filings.
- **Value lies in standardisation, not exclusive data.** The underlying data comes from public filings: annual reports and exchange submissions, as the Prowess documentation states. Vendors add standardisation, long history (Prowess from 1989-90) and unlisted-company coverage, which no free retail site matches.
- **Public price anchors understate institutional cost.** The ₹25,000 per-login figures are discounted single-user association rates (ICAI for Capitaline TP; CFA Society India for ICRA MFI 360). Institutional multi-user or redistribution licences are likely priced higher; no source confirms this.
- **Small users go through vendors.** A direct NSE real-time licence carries six- to seven-figure fixed fees (₹24 lakh a year for Level 1 in 2025). Small users therefore buy through authorised vendors such as TrueData, Global Datafeeds or Accord, which pass through per-user exchange fees.
- **Feed timing has a fairness dimension.** The BSE order shows paid feeds could lead the public website by seconds. A tracker that reads exchange websites can lag paid feeds, which matters only for intraday event alerts.

### Gaps
- **Client lists.** No named list of CMOTS clients was found. Whether Screener.in or other retail sites source fundamentals from C-MOTS could not be confirmed: a search for a "Data provided by C-MOTS" credit line returned nothing.
- **ACE.** ACE Analyser features, any ACE consensus or estimates module, and any Accord or ACE price were not found.
- **Point-in-time data.** No source said whether any Indian vendor (Prowess, ACE, Capitaline, CMOTS, Quantix) offers point-in-time, as-first-reported fundamentals or only restated history. This needs vendor confirmation and is critical for backtests.
- **Data types not traced per vendor.** Bulk and block deals, corporate actions history depth and estimates coverage per vendor were not captured.
- **CRISIL.** CRISIL Coalition (Coalition Greenwich) was not researched before the search budget ran out. It is believed to be a global investment-banking and institutional benchmarking business rather than an Indian equity data product, but this is unverified. CRISIL's equity research products were also not researched.
- **ICRA.** ICRA Analytics' "MFI Explorer" product name was not found in search.
- **Exchange fees.** NSE Indices' index-data licensing terms and fees were not found; the NSE Level 1 2026 fee was not extracted; BSE's domestic fee amounts were not extracted.
- **Prices.** No CMIE, CMOTS, Quantix or Accord list prices were found.

## 2. Newer platforms used by professionals: Trendlyne, Tijori, Screener.in, MarketsMojo, Ticker/Finology, StockEdge, smallcase, Sensibull and India-built portfolio tools

### Takeaway
- **Retail-priced tools.** These platforms are priced for individuals, at about ₹2,000–12,000 a year (Screener Premium ₹4,999; Trendlyne ₹1,890–11,900; Finology ONE ₹5,999; Sensibull ₹800 a month).
- **Unknown sourcing and rights.** Their upstream data sources are largely undisclosed, and no source found grants redistribution rights.
- **Thin PMS/AIF evidence.** Evidence of PMS/AIF adoption is indirect. Trendlyne's core B2B business is supplying brokers, and Tijori, backed by Zerodha in November 2025, is re-orienting about 70% of its roadmap to institutional users with AI earnings-call tools.

### Cited Findings

#### Trendlyne (Bengaluru)
- **Plans (third-party; prices conflict).** Basic tier GuruQ/Pro and advanced tier StratQ/Pro Plus. Reported prices:
  - GuruQ: ₹1,890 a year on one comparison site, ₹2,190 on another.
  - StratQ: ₹5,900 a year.
  - Pro (Global): ₹8,900 a year.
  - Pro Plus (Global): ₹11,900 a year.
  - Sources: [FindMyMoat comparison](https://www.findmymoat.com/vs/stock-events-vs-trendlyne); [FindMyMoat review](https://www.findmymoat.com/tools/trendlyne).
- **Plan limits.**
  - GuruQ/Pro: daily alerts on up to 75 screener strategies; downloads of 60 parameters for up to 2,000 stocks.
  - StratQ/Pro Plus: 15-minute alerts on up to 300 strategies; no download limits.
  - Sources: [Trendlyne help: what a subscription includes](https://help.trendlyne.com/support/solutions/articles/84000352548-what-do-i-get-with-a-trendlyne-subscription-); [FindMyMoat](https://www.findmymoat.com/vs/marketbeat-vs-trendlyne).
- **B2B business.** Customers are mainly brokerages.
  - A company profile surfaced in search reports 21 large B2B clients and about 800 million pages and API calls a month. The specific source page was not pinned down — [Entrepreneur India profile](https://india.entrepreneur.com/technology/simplifying-investments/441792); [Interview Query](https://www.interviewquery.com/interview-guides/trendlyne).
  - A 2023 interview cites 700 million+ API calls a month and names 5Paisa, IIFL, ICICI Securities, HDFC Securities and SBI Securities, plus about 20 other brokerages (vendor claim) — [CXOToday](https://cxotoday.com/corner-office/trendlynes-remarkable-journey-growth-expansion-and-innovations-in-the-fintech-landscape/).
- **Funding and revenue (aggregators).**
  - CB Insights: about $2M over four rounds, the latest a $1.8M Series A on 11 Oct 2022 — [CB Insights](https://www.cbinsights.com/company/trendlyne/financials).
  - Inc42: about $1.8M from IIFL Finance, IIFL Securities and ISME ACE, and FY24 revenue of ₹12.2 crore+ — [Inc42](https://inc42.com/company/trendlyne/funding/).
  - PitchBook: $2.44M — [PitchBook](https://pitchbook.com/profiles/company/171222-76).
- **Forecaster.** See section 3.

#### Tijori Finance (Bengaluru)
- **Zerodha investment.** Zerodha invested about $5M in November 2025 to fund new tools, server scaling and hiring, as Tijori builds enterprise products and courts institutional investors — [Entrepreneur India](https://india.entrepreneur.com/en-in/news-and-trends/zerodha-invests-usd-5-mn-in-tijori-finance/500188); [Entrackr](https://entrackr.com/news/zerodha-invests-5-mn-in-tijori-10817854).
- **Retail pricing and subscribers.** Retail-facing since its 2016 launch, at about ₹500 a month. Enterprise subscriptions go "up to ₹5,000" (billing period not stated). The founder cited 15,000 paid subscribers — [Entrackr](https://entrackr.com/news/zerodha-invests-5-mn-in-tijori-10817854).
- **Institutional pivot.** About 70% of the product roadmap is aimed at institutional users. The main enterprise product is "Call Monitor", an AI tool that summarises earnings calls. The funds go to LLM queries, GPUs and staff — [Venture Intelligence](https://news.ventureintelligence.com/private-equity/online-brokerage-zerodha-invests-%245-m-in-data-engine-tijori-finance); [Entrackr](https://entrackr.com/news/zerodha-invests-5-mn-in-tijori-10817854).
- **Consumer price listing (third-party).** One site lists an entry consumer plan at about $43 a year, or $4 a month billed monthly — [FindMyMoat](https://www.findmymoat.com/vs/fintel-vs-tijori-finance-ideas-dashboard).
- **Related press.** An Outlook Business feature on "who pays for clean stock market data" covers this space; its content was not captured — [Outlook Business](https://www.outlookbusiness.com/enterprise/big-idea/clean-stock-market-data-the-question-is-who-pays-for-it-5940).

#### Screener.in (operated by Mittal Analytics)
- **Pricing.** Premium ("Active Investor") costs ₹4,999 a year; the free "Hobby Investor" tier costs ₹0 — [Screener pricing page](https://screener.in/gold); [Strike review, 2026 (third-party)](https://www.strike.money/reviews/screener-in).
- **Premium features.**
  - Export of screen results is premium-only, and premium users can add up to 50 columns — [Screener support](https://support.screener.in/article/28-export-screen-results).
  - Other premium features include shareholder search, latest announcements and priority support — [Strike review](https://www.strike.money/reviews/screener-in).
- **Operator (aggregator).** Mittal Analytics is a Lucknow company founded in 2015. Its products are listed as Screener.in and "Portfolio Management Services". Reported FY24 revenue is about $2.9M and net profit about $1.95M — [The Company Check](https://www.thecompanycheck.com/company/b/mittal-analytics/35680bb9b0c041d2b).

#### MarketsMojo
- **Origins.** Started by Moneycontrol's founding team in 2016 — [YourStory](https://yourstory.com/2016/11/marketsmojo/).
- **Founder interview (late 2022, per the URL date).** CEO Mohit Batra describes the platform as covering all listed companies, with portfolio advisories, model portfolios and equity market data. He calls it profitable and bootstrapped, says the topline grows 2–3x a year, and says the aim is to go public within three years (vendor claim) — [Business Standard](https://www.business-standard.com/article/markets/our-goal-will-be-to-go-public-within-the-next-three-years-mohit-batra-122113000240_1.html).
- **Size (aggregator).** FY24 revenue about $2.98M; 2025 headcount 17 — [The Company Check](https://www.thecompanycheck.com/company/b/marketsmojo/41yimn992iasdqigb).
- **Users (dated, 2017).** About 1,40,000 registered users and about 50,000 daily visitors — [Business Today](https://www.businesstoday.in/magazine/features/story/the-new-disruptor-80364-2017-04-27).

#### Ticker (Finology)
- **Pricing.** Finology ONE bundles Quest, Ticker and Recipe premium articles for ₹599 a month or ₹5,999 a year, including GST. No separate "Ticker Pro" tier was found — [Finology ONE](https://finology.in/one).

#### StockEdge (Kredent InfoEdge Pvt Ltd: StockEdge, Elearnmarkets, StockEdge Club)
- **Kotak investment (dated).** Kotak Securities invested ₹10 crore in July 2021, its first deal under its startup investment programme — [BW Disrupt](https://bwdisrupt.com/article/kredent-infoedge-private-limited-raises-inr-10-crores-from-kotak-securities-limited-396675); [Crowdfund Insider](https://www.crowdfundinsider.com/2021/07/177794-kredent-infoedge-private-ltd-operator-of-indias-stockedge-and-elearmarkets-secures-1-34m-from-kotak-securities-others/).
- **Users and plans (dated 2021–22).** Reports cite 2 million+ users across products, and StockEdge Club as an "analysts-as-a-service" membership with 2,500+ members. Plans are StockEdge Premium, Pro and Club; prices were not captured — [Money9](https://www.money9.com/news/investment-planning/vivek-bajaj-of-stockedge-is-on-a-mission-to-financial-literacy-55551.html); [StockEdge media page](https://www.stockedge.com/media?page=11).

#### smallcase (and Tickertape)
- **Series D.** A $50M Series D in March 2025, led by Elev8 Venture Partners with State Street Global Advisors and Niveshaay, mixing primary and secondary capital — [YourStory](https://yourstory.com/2025/03/smallcase-raises-series-d-round-led-by-elev8); [Avendus](https://www.avendus.com/india/newsroom-download-pdf/avendus-capital-advises-smallcase-on-its-usd-50-million-series-d-fundraise-led-by-elev8-venture-partners-with-participation-from-state-street-global-advisors-niveshaay-and-existing-investors).
- **Financials and users.**
  - FY25 operating revenue ₹106 crore, up from ₹67.4 crore in FY24; EBITDA loss ₹9 crore; net loss ₹34 crore — [Angel One, citing Entrackr](https://www.angelone.in/news/market-updates/smallcase-surpasses-100-crore-revenue-milestone-in-fy25-with-strong-growth).
  - Revenue is mostly transaction fees charged to brokers (same source).
  - Claims 10M+ users and ₹1.2 lakh crore of transactions facilitated (vendor claim) — same source.
- **Unofficial Tickertape API wrapper.** An open-source Python library wraps Tickertape's API (api.tickertape.in), which shows third parties programmatically consume these retail platforms. The upstream fundamentals vendor is not named — [bharat-sm-data docs](https://bharat-sm-data.readthedocs.io/en/latest/_modules/Fundamentals/TickerTape.html).

#### Sensibull (options analytics)
- **Pricing (third-party; conflicting).**
  - 5paisa: Pro ₹800 + 18% GST a month, ₹3,840 + GST for six months; Lite ₹590 + GST a month — [5paisa KB](https://forum.5paisa.com/portal/en/kb/articles/what-are-the-subscription-and-brokerage-charges-for-sensibull).
  - Older Alice Blue figures: Lite ₹480 and Pro ₹780 a month (dated) — [Investorgain](https://www.investorgain.com/topic/alice-blue-sensibull/220/).
- **Zerodha.** Zerodha reportedly covers the subscription for its own customers — [Lapaas](https://voice.lapaas.com/startup/sensibull/business-model/).
- **Pro features.** Strategy builder, trade analysis, an advanced option chain and "advanced data tools" — [Techjockey](https://techjockey.com/detail/sensibull).

#### India-built portfolio analytics and risk tools for professionals
- **Valuefy (vendor claim).** Mumbai wealthtech founded in 2010. Sells B2B to banks, AMCs and family offices, covering accounting, consolidated reporting, CRM, portfolio and risk management, and performance attribution. Its current focus includes private-market analytics — [YourStory](https://yourstory.com/companies/valuefy/amp); [Hubbis](https://hubbis.com/article/data-intelligence-and-scale-srutaban-mukhopadhyay-on-valuefy-s-wealth-technology-proposition).
- **Finalyca (vendor claim).** Shows PMS, AIF, mutual fund and ULIP data on one screen, with risk, return, volatility, sector-exposure and diversification analysis — [Finalyca](https://finalyca.com).
- **InferEdge (vendor claim).** Mumbai startup from Y Combinator's 2022 batch with about 20 staff. Builds "agentic AI for the buy-side" across research, portfolio management and risk, for equity and fixed income — [Y Combinator India AI list](https://www.ycombinator.com/companies/industry/ai/india).
- **PMS/AIF marketplaces.** PMS Bazaar, Altport and PMSAIFWORLD are investor-facing comparison and distribution platforms, not manager tools — [PMS Bazaar](https://pmsbazaar.com/); [Altport](https://www.altportfunds.com/); [PMSAIFWORLD](https://www.pmsaifworld.com/).
- **Benchmarking.** CRISIL publishes AIF benchmarks for Categories I, II and III — [Crisil PMS/AIF products](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/investment-products-pms-aif-and-insurance.html).

### Inferences
- **Individual-use licences.** Retail tiers (₹2,000–12,000 a year) are individual-use subscriptions. A PMS or AIF can use them as analyst seats, but nothing found suggests they permit redistribution or programmatic reuse. Bulk export is an explicit premium feature at Screener and Trendlyne.
- **Trendlyne likely has supply arrangements.** Its B2B business (APIs to 20+ brokers) suggests it holds supply agreements that allow white-labelled distribution. Those terms are not public.
- **A 2025–26 trend upmarket.** Retail research platforms are moving into institutional AI tooling (Tijori's Call Monitor, InferEdge, Crisil i360 at the incumbent end). This is the likely competitive frame for a self-built tracker that already uses LLM reading.
- **Low relevance for a fundamentals tracker.**
  - Sensibull is an options front-end (free for Zerodha clients).
  - smallcase is model-portfolio distribution and execution infrastructure, earning mostly broker transaction fees.

### Gaps
- **Screener.in.** Its upstream data source and its terms on scraping and automated access were not verified; the search budget ran out. This is directly relevant because the tracker scrapes Screener.in.
- **Terms of use.** Trendlyne's, Tijori's and MarketsMojo's terms on commercial use and data reuse were not captured.
- **Prices not found.** MarketsMojo, StockEdge, Tickertape Pro and smallcase products for PMS and RIA managers (if any).
- **Not researched.** MarketSmith India.
- **Adoption.** No direct evidence (surveys, job postings) was found of PMS/AIF managers using Trendlyne, Tijori, Screener or MarketsMojo.

## 3. Consensus estimates in India: who aggregates broker estimates, broker counts, terms

### Takeaway
- **Trendlyne Forecaster is the only documented domestic product.** It covers about 900 companies. Example analyst counts run from 8 for Data Patterns to 36 for Nestlé India.
- **No broker list.** Trendlyne publishes no list or count of contributing brokers.
- **Nothing found for others.** No consensus product was evidenced for ACE, Capitaline, CMOTS or Moneycontrol. Global sources (LSEG/Refinitiv I/B/E/S, Bloomberg), with 900+ contributors globally, remain the institutional reference.

### Cited Findings
- **Coverage.** Trendlyne's Forecaster "aggregates earnings estimates from analysts for approximately 900 companies". Smaller companies are typically excluded because they lack analyst consensus — [Trendlyne help: Forecaster](https://help.trendlyne.com/support/solutions/articles/84000385838-what-are-forecaster-or-analyst-estimates-).
- **Fields.** Target prices, EPS and consensus recommendations, plus current and historical estimates for revenue, net profit, EPS, dividends, cash flow, capex and interest expense. Trendlyne calls it "India's most detailed analyst estimates" (vendor claim) — [Trendlyne on X](https://x.com/Trendlyne/status/1777223326521307492); [Trendlyne consensus explainer](https://trendlyne.com/equity/consensus-estimates/what-is/modal/).
- **Analysts per stock, from page titles.** Nestlé India shows estimates "from 36 analysts" and Data Patterns "from 8 analysts" — [Trendlyne Nestlé](https://trendlyne.com/equity/consensus-estimates/930/NESTLEIND/nestle-india-ltd/); [Trendlyne Data Patterns](https://trendlyne.com/equity/consensus-estimates/755079/DATAPATTNS/data-patterns-india-ltd/).
- **Launch.** Trendlyne announced "Forecaster is now live" on X; the post ID dates to about January 2022 (inferred from the ID) — [Trendlyne on X](https://x.com/Trendlyne/status/1484145637289791493).
- **Broker count (third-party).** A review describes the dashboard as aggregating "consensus estimates from dozens of brokerages". No official broker list or count was found — [FindMyMoat review](https://www.findmymoat.com/tools/trendlyne).
- **Plan access.** Consensus estimates also work as screener filters, which ties them to paid plan limits — [FindMyMoat](https://www.findmymoat.com/vs/stock-events-vs-trendlyne).
- **Global benchmark.** Refinitiv (LSEG) estimates draw on "more than 900 contributing analyst and brokerage firms" globally and compute both mean and median consensus — [Stockopedia: about our estimates data](https://learn.stockopedia.com/en/articles/3513191-about-our-estimates-data).
- **Domestic contributors and depth (informal glossary).**
  - Domestic brokers (Kotak Institutional Equities, Motilal Oswal, ICICI Securities, Edelweiss) feed global consensus databases.
  - A Nifty 50 stock may have 20+ analysts; a Nifty Midcap 150 stock may have only 3–5.
  - Consensus differs across providers because of timing and weighting.
  - Sources: [EquitiesIndia: analyst consensus](https://equitiesindia.com/glossary/analyst-consensus); [EquitiesIndia: consensus estimate](https://equitiesindia.com/glossary/consensus-estimate).
- **Accord.** Search found no evidence that ACE Equity Nxt or Accord's datafeed includes consensus estimates. The ACE Equity Nxt library descriptions list only financial and non-financial data — [IIM Trichy library](https://library.iimtrichy.ac.in/ace-equity/).

### Inferences
- **Small caps are thin.** Coverage of about 900 companies roughly matches the sell-side-covered universe. For a small/mid-cap PMS universe, consensus will be thin (3–5 analysts) or absent. Estimates are least available exactly where a small-cap tracker most needs them.
- **Not auditable.** Without a published contributor list, Trendlyne consensus cannot be checked for broker inclusion or stale estimates. Institutional users would keep Bloomberg, LSEG or Capital IQ as the reference; the job postings above name these tools.

### Gaps
- **Missing basics.** Trendlyne's broker count, contributor list, estimate-revision timestamps and terms of use for estimates (including any redistribution limits) were not found.
- **Other sources unconfirmed.** Moneycontrol's and Tickertape's estimate sources could not be confirmed; the planned search was cut off by the budget limit.
- **Other vendors.** Whether Capitaline, CMOTS or CRISIL offer broker-estimate aggregation was not found.

## 4. Mutual fund and portfolio data: AMFI, Value Research, Morningstar India, CRISIL fund research, ACE MF (plus ICRA Analytics and Capitaline NAV India)

### Takeaway
- **Free AMFI base.** AMFI's NAV data is free but licensed for personal, non-commercial use only.
- **Commercial layer.** Commercial MF analytics sits with CRISIL (rankings, database and AIF benchmarks), ICRA Analytics (database since inception; MFI 360 at ₹25,000 a year member price), Accord ACE MF (month-by-month holdings with Excel export), Capitaline NAV India, Value Research and Morningstar India.
- **Prices.** Institutional prices are undisclosed; only retail or member prices surfaced.

### Cited Findings
- **AMFI terms.**
  - Grants a "non-exclusive, personal, non-transferable, non-sublicensable, limited and revocable right to access, use and display" the site, for personal non-commercial use.
  - Bars public display, transmission, publication and derivative works, and storing "any significant portion" of the site.
  - Reverse engineering or modification needs written approval.
  - Source: [AMFI terms of use](https://www.amfiindia.com/terms-of-use).
- **AMFI NAV history.** Downloads are capped at 90 days per request — [AMFI NAV download](https://www.amfiindia.com/net-asset-value/nav-download).
- **AMFI SIF page.** AMFI also hosts NAV history for Specialised Investment Funds (SIF) — [AMFI SIF NAV history](https://www.amfiindia.com/sif/latest-nav/nav-history).
- **SEBI NAV disclosure.** SEBI requires AMCs to disclose all scheme NAVs on their own websites and on AMFI's website. This is a disclosure duty, not a reuse right — [SEBI 2018 document](https://www.sebi.gov.in/sebi_data/attachdocs/jun-2018/1528207366367.pdf).
- **AMFI distributor data.** AMFI discloses distributor AUM annually: 1,017 distributors in FY18 and 1,037 in FY19 (dated) — [Morningstar India](https://morningstar.in/posts/53507/top-20-distributors-manage-40-total-industry-assets.aspx).
- **CRISIL Mutual Fund Ranking (CMFR).**
  - Launched June 2000; covers equity, debt and hybrid categories.
  - Combines NAV data with portfolio attributes: risk-adjusted returns, concentration, liquidity and asset quality. Ranks run 1–5, with Rank 1 meaning "very good performance".
  - Customised rankings are delivered monthly or quarterly.
  - CRISIL also has data on ULIPs, PMS and AIFs, a Mutual Fund Database for AMCs and distributors, and outsourced factsheets. It calls itself the "largest valuation agency for fixed income securities in India" (vendor claim).
  - Sources: [Crisil MF research](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/mutual-fund-research.html); [Crisil MF ranking](https://intelligence.crisil.com/content/crisilcom/en/home/what-we-do/financial-products/mf-ranking.html).
- **CRISIL AIF benchmarks.** Cover Categories I, II and III and compare an AIF with its category average — [Crisil PMS/AIF products](https://intelligence.crisil.com/en/homepage/what-we-do/research/investment-research-product/investment-products-pms-aif-and-insurance.html).
- **ACE MF Nxt (Accord).**
  - Portfolio tab shows the latest or month-selected holdings, with Excel download and multi-scheme portfolio comparison.
  - Holdings are broken down by company, asset, industry, rating and maturity profile, with NAV and dividend data.
  - Also has ratio analysis, fund-manager history and AND/OR formula screening.
  - Coverage is cited as 42+ AMCs and 12,000+ schemes in one source, 50+ AMCs in another.
  - Sources: [IIM Indore ACE MF Nxt guide](https://iimidr.ac.in/wp-content/uploads/2025/10/User-Guide-ACE-MF-Nxt.pdf); [IIM Trichy library](https://library.iimtrichy.ac.in/?p=726).
  - Accord's own 2021 document describes ACE MF Nxt as a Windows desktop application whose data sits centrally on Amazon AWS and is "served … through APIs". Newer library material describes a browser version (IIM Sambalpur, Aug 2026) — [Accord/CFA Society offer document](https://cfasocietyindia.org/wp-content/uploads/2021/06/Accord-offer-document.pdf); [IIM Sambalpur ACE MF Nxt Web manual](https://library.iimsambalpur.ac.in/uploads/usermanuals/20260803161229_e29f4b30_ACE_MF_Nxt_Web-compressed.pdf).
- **ICRA Analytics MFI 360.**
  - A cloud research tool for MF distributors and RIAs, launched in 2018 (reported as an "ICRA Online" launch) — [Cafemutual](https://cafemutual.com/news/industry/14787-icra-online-launches-research-and-analysis-tool-for-distributors).
  - Features include a fund screener and a portfolio scanner for overlap between funds. The CFA Society India member price was ₹25,000 a year excluding GST; the offer is undated — [CFA Society India MFI 360 offer](https://cfasocietyindia.org/wp-content/uploads/Media-Uploads-Membership/Member-offers/Member-Offer-Document_ICRA-A_MFI360.pdf).
  - ICRA Analytics also claims a scheme database from the industry's inception — [ICRA](https://icra.in).
- **Capitaline NAV India.** Covers 5,000+ schemes: NAVs, performance, rankings and portfolios (vendor claim) — [CFA Society India Capitaline offer](https://cfasocietyindia.org/wp-content/uploads/Media-Uploads-Membership/Member-offers/Member-Offer-Document_for-Society_Capitalin2.pdf).
- **Value Research.**
  - Retail annual subscription ₹5,841 including taxes (third-party review, undated) — [Finology Ticker review](https://ticker.finology.in/discover/solutions/value-research-review).
  - Says it supplies data to "millions of investors, advisors and media companies" and that Bloomberg uses its data (vendor claim) — [Value Research about us](https://www.valueresearchonline.com/about-us/).
  - No institutional feed price was found.
- **Morningstar India.**
  - Started India operations in April 2009 (dated) — [Business Standard](https://www.business-standard.com/amp/article/markets/morningstar-starts-india-operations-109041600070_1.html).
  - A roughly 2010 interview says its offerings run "from a data feed to investment consulting", with an India version of Morningstar Direct carrying star ratings and Indian MF data. It also says AMCs cannot commission its ratings (vendor claim, dated) — [Cafemutual](https://cafemutual.com/news/industry/9518-use-star-ratings-as-a-first-level-check-but-dont-blindly-follow-them-aditya-agarwal-morningstar).

### Inferences
- **Holdings come from AMC disclosures.** AMC monthly portfolio disclosures are the raw source for holdings analysis. ACE MF, CRISIL, ICRA, Capitaline, Value Research and Morningstar standardise them across AMCs.
- **Commercial reuse needs a licence.** AMFI's terms bar commercial reuse of its site data. A commercial or institutional tool showing MF holdings or NAV-based peer comparisons should license a vendor database or rely on each AMC's own disclosure terms (not checked).
- **PMS/AIF peer comparison.** Here the relevant domestic tools are CRISIL AIF benchmarks and Finalyca (section 2), not the MF databases.

### Gaps
- **Prices.** Institutional and feed prices for Value Research, Morningstar India, CRISIL's MF database, ACE MF and Capitaline NAV India were not found.
- **Morningstar India status.** Its 2026 product line-up and status in India were not verified; the sources found date from about 2009–2010.
- **AMFI portfolios and API.** Whether AMFI itself publishes consolidated portfolio holdings, and on what terms, was not found; nor was whether AMFI offers any API.

## 5. Legal and licensing constraints on using NSE/BSE data: redistribution policies and fees, anti-scraping rules, what a small user must license

### Takeaway
- **Scraping.** NSE's website terms expressly prohibit "systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting)", and users report IP blocking.
- **Redistribution.** NSE data is licensed through NSE Data & Analytics under published tariffs; passing feeds or EOD data to clients needs NDAL's written consent.
- **SEBI.** SEBI's 2024–2026 framework bars exchanges and other market infrastructure institutions (MIIs), and registered intermediaries, from sharing real-time price data except for specified purposes. Since May 2026 there is a uniform 30-day lag for education uses.
- **Equal access.** BSE was penalised in 2025 for giving paid subscribers earlier access to announcements.

### Cited Findings
- **NSE Terms of Use.**
  - "User is prohibited to conduct any systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting) on or in relation to our Website / Mobile Application."
  - Copying content is barred unless it is offered for download, and unauthorised use "may violate copyright, trademark and other applicable laws".
  - Source: [NSE Terms of Use](https://www.nseindia.com/static/nse-terms-of-use).
- **NSE Data portal terms.** Subscribers may use data "solely for the purposes as expressly permitted by NSE Data" — [NSE Data (DotEx) terms](https://dotexdata.nseindia.com/TermsAndConditions/TermsofUse.pdf).
- **NSE analytics (FIXEDIN) terms.** Repeat the scraping ban and require express written consent — [FIXEDIN terms](https://analytics.nseindia.com/assets/images/FIXEDIN-Terms-of-Use.pdf).
- **Enforcement in practice (anecdotal).** Developer forums report HTTP 403 responses and IP bans when scraping NSE, including from cloud servers — [Unofficed forum](https://forum.unofficed.com/t/nsepython-not-working-in-aws-google-cloud-and-webservers/670); [TradingQnA](https://tradingqna.com/t/need-api-for-nse-data/104916).
- **NSE Data Usage and Sharing Policy.**
  - Issued 3 Oct 2024 (notification NSE/MSD/64333) — [TeamLease RegTech](https://teamleaseregtech.com/updates/article/35757/nse-issued-the-data-usage-and-data-sharing-policy).
  - All data usage, sharing and distribution is handled by NSE and its 100% subsidiary NSE Data & Analytics on an arm's-length basis. Fees for all subscribers are "fixed on an arm's length basis".
  - NSE Data's board "may consider introducing reduced fee arrangements or waivers for Non-Commercial Users".
  - Section 10 covers "Non-Commercial Users, Research Entities and Analysts"; its text was not captured.
  - Sources: [NSE policy PDF](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/NSE_Data_Sharing%26Usage_Policy.pdf); [NSE data policy page](https://www.nseindia.com/static/market-data/nse-data-policy).
- **NSE tariff licence rules (2026 domestic pricing file).**
  - Feeds to a vendor's clients need written consent and a prior licence or agreement from NDAL.
  - A vendor's mobile app cannot be sold on its own; it must come with a terminal or software subscription.
  - Each additional delivery channel adds 50% of the product's fixed fee.
  - Where several real-time levels are taken, the highest is charged in full and lower levels at 25%.
  - Fees exclude taxes.
  - Sources: [NSE domestic pricing, 9 Mar 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf); [NSE RT tariff 2023 (25% rule)](https://nsearchives.nseindia.com/s3fs-public/inline-files/Download_Real_Time_Tariff_Domestic_01042023.pdf).
- **NSE EOD rule.** Real-time vendors may display EOD data on their own terminals at no extra fee. Supplying EOD or previous-day EOD data "to vendor's clients for any type of usage" needs NDAL's written consent — [NSE EOD tariff, Apr 2026](https://nsearchives.nseindia.com//web/mediaattachment/2026-04/Download_End_of_the_Day_Data_Tariff_20260424120810.pdf); [older NSE EOD document](https://archives.nseindia.com/content/press/EOD_data.pdf).
- **SEBI real-time price-data framework.**
  - **Circular of 24 May 2024.** Applies to MIIs (exchanges, clearing corporations, depositories) and registered intermediaries. Real-time price data may be shared with third parties only for market functioning or regulatory purposes. Price data could be shared with a one-day lag, "without any incentive", only for investor education and awareness — [Taxmann analysis](https://www.taxmann.com/post/blog/analysis-sebi-guidelines-on-real-time-price-data-sharing-ensuring-market-integrity/); [KS&K](https://ksandk.com/newsletter/sebi-real-time-price-data-protect-investors/); [MediaNama (context: gaming/virtual-trading platforms)](https://www.medianama.com/2024/05/223-sebi-guidelines-sharing-stock-exchange-data-gaming-platforms/).
  - **January 2025.** Entities solely in education may use price data only with a three-month lag — [Taxguru](https://taxguru.in/sebi/norms-sharing-usage-price-data-educational-purposes.html); [Outlook Money](https://www.outlookmoney.com/amp/story/invest/sebi-revises-norms-for-sharing-and-usage-of-price-data-for-educational-purposes).
  - **Circular of 8 May 2026.** Sets a uniform 30-day lag for sharing and using stock price data for education and investor-awareness, replacing the one-day/three-month split. NISM may get one-day-lagged data only for its simulation lab — [Taxmann](https://www.taxmann.com/post/blog/sebi-revises-time-lag-norms-for-stock-price-data-sharing/); [Taxguru](https://taxguru.in/?p=1042309).
  - A licensed vendor's summary of the norms (vendor) — [TrueData blog](https://truedata.in/blog/sebi-norms-on-sharing-real-time-price-data).
- **Equal access to announcements: SEBI's BSE order of 25 Jun 2025.** ₹25 lakh penalty under SECC Regulation 39(3) for giving paid subscribers and internal staff earlier sight of announcements. SEBI also noted BSE had no RSS feed — [Business Today](https://www.businesstoday.in/amp/markets/stocks/story/sebi-imposes-rs-25-lakh-fine-on-bse-for-unequal-data-access-oversight-failures-481863-2025-06-26). NSE publishes RSS feeds; their reuse terms were not captured — [NSE RSS](https://www.nseindia.com/rss-feed).
- **BSE licensing scope.**
  - BSE's tariff applies to Indian datafeed customers whether direct or through BSE-authorised vendors, and corporate data (announcements, results, board meetings) is a priced product — [BSE tariff sheet](https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf).
  - International licensing runs exclusively through Deutsche Börse — [Deutsche Börse MDS](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/asian-markets/BSE-India-Index-and-Equity-Derivatives-1340710).
- **Unofficial resale exists.** An Apify actor sells scraped NSE/BSE announcement records with PDF links at about $50 per 1,000 records. This is not an official channel (third-party) — [Apify](https://apify.com/nexgendata/nse-bse-announcements).
- **AMFI.** Website data is for personal non-commercial use only (see section 4) — [AMFI terms](https://www.amfiindia.com/terms-of-use).

### Inferences
These are not legal advice.
- **The tracker's NSE reads.** Reading NSE's website JSON "public APIs" from a script falls, on the plain text of the terms, within "systematic or automated data collection … on or in relation to our Website". Any commercial or institutional use of that data has no licence behind it. The sanctioned routes are below.
- **Cheapest licensed NSE routes (2026 tariffs).**
  - EOD market data: ₹1 lakh a year per medium of display.
  - EOD corporate announcements by SFTP: ₹5 lakh a year.
  - Full corporate data feed (announcements, results, shareholding) over a leased line: ₹10.6 lakh a year.
  - 15-minute delayed CM data: about ₹1.4 lakh a year per site (garbled extraction; verify).
  - Real-time prices: in practice through an authorised vendor (TrueData, Global Datafeeds, Accord), which bundles NDAL per-user fees.
- **Fundamentals have no exchange-level shortcut.** Standardised fundamentals require a vendor licence (CMOTS, Accord, Capitaline, CMIE, CRISIL). Alternatively, building from NSE's own corporate data feed (financial results and shareholding) brings NSE's consent requirements for any onward display.
- **SEBI rules if the user is regulated.** If the institution running the tracker is a SEBI-registered intermediary (for example a portfolio manager), sharing real-time price data from the tool with third parties (clients, a public page) could fall under the SEBI framework. Purely internal use is less clearly covered. This needs legal confirmation.
- **Scraped retail sites carry no redistribution rights.** Data scraped from retail sites such as Screener.in sits under those sites' own terms and their upstream vendor licences (not verified), so it should not be redistributed.

### Gaps
- **Primary texts.** The SEBI circulars of May 2024, January 2025 and 8 May 2026 were not read; only secondary summaries were. Section 10 of NSE's policy and any NSE fee waiver for non-commercial users were not read.
- **Other sites' terms.** BSE website terms (scraping), Screener.in terms, and NSE RSS reuse terms were not retrieved.
- **Enforcement.** No court case or enforcement action against a scraper of NSE or BSE data was found. Whether NSE has pursued redistributors beyond technical blocking is unknown.
- **Non-display use.** NSE's licensing of non-display use (internal computation such as a tracker computing signals) is set out in its Non-Display Policy, which was not read.

## 6. Pricing: published or reported prices, institutional and retail tiers, dated

### Takeaway
- **Where prices are public.** Published prices exist mainly for exchange data (NSE's 2025 and 2026 tariffs; Deutsche Börse's list for BSE) and for retail tiers.
- **Where they are not.** Institutional database vendors (CMIE, Accord ACE, CMOTS, CRISIL, ICRA, Value Research and Morningstar institutional) sell by quote. The only public anchors are association-discount single-login rates of about ₹25,000 a year.

### Cited Findings
Prices exclude taxes unless stated. "Search extract" means the figure was read by the search tool, not directly; verify before use.

| Product | Price | Date / vintage | Source |
|---|---|---|---|
| NSE real-time Level 1 CM, fixed fee (domestic vendor) | ₹24,00,000/yr | Tariff effective 1 Apr 2025 | [NSE RT tariff 2025](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Real_Time_Tariff_Domestic_01042025_.pdf) |
| NSE real-time Level 1 CM, per end user | ₹1,075/month (domestic users); ₹1,775 (international users) | 1 Apr 2025 | [NSE RT tariff 2025](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Real_Time_Tariff_Domestic_01042025_.pdf) |
| NSE real-time Level 2 CM, fixed fee | ₹37,50,000/yr (2025) → ₹40,00,000/yr (2026) | 2025 tariff; 2026 file dated 9 Mar 2026, effective 1 Apr 2026 | [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) (garbled extraction) |
| NSE real-time Level 2 CM, per end user | ₹1,700/month domestic; ₹2,700 international | 2026 | [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) |
| NSE 15-minute delayed CM data | ₹1,40,000/yr per site | 2026 | [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) (garbled extraction) |
| NSE corporate data feed (announcements, results, shareholding; leased line) | ₹10,60,000/yr or US$17,500 | Page marked updated 11/06/2026 | [NSE paid corporate data](https://www.nseindia.com/static/market-data/corporate-data-subscription) |
| NSE corporate data feed (previous) | ₹10,00,000/yr or US$16,000 | April 2025 tariff | [NSE corporate data (older page)](https://www.nseindia.com/market-data/corporate-data-subscription) |
| NSE EOD corporate announcements (SFTP, after 8 pm) | ₹5,00,000/yr or US$8,000 | 2025–2026 | [NSE paid corporate data](https://www.nseindia.com/static/market-data/corporate-data-subscription) |
| NSE corporate bond market data | ₹3,40,000/yr | 2026 | [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) |
| NSE backup link | ₹2,12,000 per link per year | 2026 | [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf) |
| NSE EOD data, CM and F&O | ₹1,00,000/yr (US$5,500) per medium of display | Tariff file dated 24 Apr 2026 | [NSE EOD tariff 2026](https://nsearchives.nseindia.com//web/mediaattachment/2026-04/Download_End_of_the_Day_Data_Tariff_20260424120810.pdf) |
| NSE EOD WDM; 15-minute delayed snapshot CM + F&O | ₹10,000/yr; ₹3,75,000/yr | 1 Apr 2022 (dated) | [NSE product tariff 2022](https://archives.nseindia.com/content/press/Other_Data_Product_Pricing_effective_Apr012022.pdf) |
| NSE 2-minute snapshot/delayed CM | ₹7,50,000 | 1 Apr 2020 (dated) | [NSE product tariff 2020](https://archives.nseindia.com/content/press/Other_product_pricing_01042020.pdf) |
| BSE India Spot Market Ultra via Deutsche Börse (international) | €1,456/month real-time, €728 delayed (an older version: €1,870 / €935) | Price-list versions undated in extract | [DB MDDA v10.1](https://mds.deutsche-boerse.com/resource/blob/2106722/5cdbe2f49af79af62ad8c7e1712e820d/data/MDDA_Price_List_10_1.pdf); [DB MDDA v10.8](https://mds.deutsche-boerse.com/resource/blob/2106704/0a84d6a16719420b0a2f8c7bf66698e7/data/MDDA_Price_List_10_8.pdf) |
| Capitaline AWS TP (ICAI practising-CA rate) | ₹25,000 per login per year + GST, or ₹55,000 per login for 3 years + GST | Agreement dated 5 Apr 2023, 3 years (term likely ended about Apr 2026) | [ICAI](https://www.icai.org/post/16361) |
| Capitaline TP (ICAI rate); C-MOTS TP (ICAI rate) | ₹15,000 online and ₹65,000 desktop per year (Dec 2019); ₹12,000 per login (2016) | Dated | [CAclubindia](https://caclubindia.com/news/icai-enters-into-an-arrangement-for-tp-corporate-database-at-a-concessional-rate-18089.asp); [Taxscan](https://www.taxscan.in/?p=14635) |
| ICRA Analytics MFI 360 (CFA Society India member rate) | ₹25,000/yr + GST | Undated offer | [CFA Society India](https://cfasocietyindia.org/wp-content/uploads/Media-Uploads-Membership/Member-offers/Member-Offer-Document_ICRA-A_MFI360.pdf) |
| Screener.in Premium | ₹4,999/yr (free tier ₹0) | 2026 | [Screener](https://screener.in/gold); [Strike review](https://www.strike.money/reviews/screener-in) |
| Trendlyne GuruQ / StratQ / Pro (Global) / Pro Plus (Global) | ₹1,890 or ₹2,190 / ₹5,900 / ₹8,900 / ₹11,900 per year (third-party; conflicting) | 2026 comparisons | [FindMyMoat](https://www.findmymoat.com/vs/stock-events-vs-trendlyne) |
| Tijori Finance | About ₹500/month retail; enterprise "up to ₹5,000" | November 2025 press | [Entrackr](https://entrackr.com/news/zerodha-invests-5-mn-in-tijori-10817854) |
| Finology ONE (includes Ticker) | ₹599/month or ₹5,999/yr including GST | Undated | [Finology ONE](https://finology.in/one) |
| Sensibull Pro / Lite | ₹800 + GST/month (₹3,840 + GST for 6 months) / ₹590 + GST/month; free for Zerodha clients | Undated (5paisa KB) | [5paisa](https://forum.5paisa.com/portal/en/kb/articles/what-are-the-subscription-and-brokerage-charges-for-sensibull); [Lapaas](https://voice.lapaas.com/startup/sensibull/business-model/) |
| Value Research (retail premium) | ₹5,841/yr including taxes | Undated review | [Finology Ticker review](https://ticker.finology.in/discover/solutions/value-research-review) |

- **NSE price rises, 2025 to 2026** (arithmetic from the figures above).
  - Corporate data fixed fee: +6% in INR (₹10.0 → ₹10.6 lakh) and +9.4% in USD ($16,000 → $17,500).
  - Level 2 CM fixed fee: +6.7% (₹37.5 → ₹40 lakh).
  - Sources: [NSE corporate data](https://www.nseindia.com/static/market-data/corporate-data-subscription); [NSE domestic pricing 2026](https://nsearchives.nseindia.com/web/mediaattachment/2026-03/NSE_Pricing_file_-_Domestic_clients_20260309171343.pdf).
- **Vendor bundling.** Authorised NSE/BSE data vendors publish retail API price plans that include exchange per-user fees. The amounts were not captured — [TrueData pricing](https://www.truedata.in/price); [Accelpix pricing](https://accelpix.com/pricing/).

### Inferences
- **Order of magnitude for a small institution's compliant stack.**
  - Licensed exchange data: ₹1–15 lakh a year (EOD ₹1 lakh; EOD corporate announcements ₹5 lakh; or the full corporate-data feed ₹10.6 lakh).
  - Optional delayed or real-time data through an authorised vendor: amount not captured.
  - A quote-based fundamentals licence: likely the largest variable cost, with only ₹25,000 per-seat association rates as a public floor.
  - Retail seats such as Screener at ₹4,999 or Trendlyne at up to ₹11,900 are cheap but carry no redistribution rights.
- **NSE pricing trend.** Exchange tariffs are revised each 1 April; the 2026 increases were about 6–9%. Budget for annual escalation.

### Gaps
- **Prices not found.** CMIE (ProwessIQ, Prowess dx), Accord (ACE Equity, ACE MF, ACE Datafeed), CMOTS APIs, CRISIL (Quantix, i360, MF database, CMFR), ICRA Analytics institutional products, Morningstar India, Value Research institutional feed, MarketsMojo, StockEdge, and smallcase or Tickertape plans.
- **Exchange fees not extracted.** BSE's domestic tariff amounts and NSE's 2026 Level 1 fixed and per-user fees.
- **Global vendor prices.** Prices of global terminals (Bloomberg, LSEG, Capital IQ) in India were out of scope and not researched.
