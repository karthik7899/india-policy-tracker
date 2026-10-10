# Institutional portfolio, order, compliance and reporting platforms for Indian equity managers, and the SEBI requirements they must meet (as of October 2026)

*How these notes were made (10 Oct 2026): every finding comes from web-search result summaries. I could not open any primary document. The network proxy refused CONNECT with HTTP 403 for sebi.gov.in, amfiindia.com, apmiindia.org, taxmann.com, bloomberg.com, nsearchives.nseindia.com, business-standard.com, scconline.com, cafemutual.com and thetradenews.com; per instructions, I did not retry those refusals. The WebFetch tool failed DNS resolution ("getaddrinfo ENOTFOUND") for every host tried. The shared web-search budget for the turn (200 calls) ran out partway through. As a result, I could not verify vendors other than Bloomberg and KFintech, PMS/AIF concentration rules, AIF benchmarking, insurers (IRDAI), or technology spend; those are listed as gaps. "Flag" means one of these: the fact is single-source, the summary did not say which of several returned pages carried it, or sources conflict. "Vendor claim" means a statement made by a vendor or a client in a vendor press release.*

## 1. Platforms Indian AMCs, PMS, AIFs and insurers use (OMS/EMS, compliance, accounting, analytics, client reporting), with pricing and coverage

### Takeaway
Public, checkable evidence of Indian buy-side platform choices is thin. The clearest case is Bloomberg AIM, used as the order-management and trading-compliance system at four named mutual fund AMCs: Aditya Birla Sun Life, DSP, Bajaj Finserv and NJ. DSP also uses Bloomberg PORT Enterprise for analytics. KFintech, a registrar and transfer agent (RTA), moved into fund accounting and reconciliation by buying Hexagram Fintech (products: mPower, iMatch) in February 2022. I found no Indian client announcement for Charles River. I verified nothing about SS&C, FIS, SimCorp, Temenos/Multifonds or the Indian vendors named in the brief, and no pricing anywhere.

### Cited Findings
- **Aditya Birla Sun Life AMC** picked Bloomberg AIM in 2020 as its order management system (OMS) for its India and Singapore operations. In December 2022 it extended AIM to its GIFT City (IFSC) unit, which Bloomberg describes as the first asset manager in the IFSC to use AIM. — [Bloomberg press release](https://www.bloomberg.com/company/press/aditya-birla-sun-life-amc-becomes-indias-first-asset-manager-to-expand-adoption-of-bloomberg-aim-to-its-gift-city-unit)
- **DSP Investment Managers (2022)** already used Bloomberg AIM as its OMS and added Bloomberg PORT Enterprise for portfolio management and analytics. — Bloomberg press announcements returned by search; the DSP page was not isolated, so flag ([candidate 1](https://www.bloomberg.com/company/?p=28496), [candidate 2](https://www.bloomberg.com/company/?p=32442), [candidate 3](https://www.bloomberg.com/company/?p=24871))
- **Bajaj Finserv Asset Management (2023)** adopted AIM to streamline research, fund management, trading, operations and investment compliance. Its CIO called AIM "the most scalable, integrated and advanced on the market" (vendor/client claim). — [Bloomberg press release](https://www.bloomberg.com/company/press/bajaj-finserv-asset-management-adopts-bloomberg-aim-to-power-digitization-journey); [FI Desk](https://www.fi-desk.com/bajaj-finserv-asset-management-adopts-bloomberg-aim/)
- **NJ Asset Management (2023)** uses AIM for portfolio analytics, order management and trading compliance. — [The TRADE](https://www.thetradenews.com/nj-asset-management-streamlines-order-management-and-compliance-management-with-bloomberg-solutions/)
- Bloomberg says AIM is used by "nearly 15,000 professionals at over 900 client firms" worldwide. This is a 2022 vendor claim and probably out of date. — Bloomberg press announcements (flag: [candidate](https://www.bloomberg.com/company/?p=33447))
- **KFintech / Hexagram:**
  - KFintech announced on 9 Feb 2022 that it had acquired Hexagram Fintech. Hexagram became a wholly owned subsidiary, and the terms were not disclosed.
  - Hexagram's products are mPower, a fund-accounting ERP, and iMatch, a reconciliation tool. Its clients are in mutual funds, AIFs, insurance, banking and corporate treasuries.
  - The stated rationale was to extend into the asset side of investment management and into alternatives, and to add Hexagram's South-East Asian BFSI clients.
  - Sources: [KFintech press release](https://investor.kfintech.com/wp-content/uploads/2022/11/02-09-2022-KFintech-acquires-Hexagram-to-expand-into-Fund-Accounting-Press-Release.pdf); [Business Standard](https://www.business-standard.com/article/companies/kfin-buys-hexagram-to-expand-into-fund-accounting-reconciliation-solutions-122020900807_1.html); [IBS Intelligence](https://ibsintelligence.com/ibsi-news/kfintech-announces-acquisition-of-hexagram-fintech/)
- KFintech's AIF page makes these vendor claims:
  - mPower automates valuations and income recognition according to market practice, the client's chosen policies and IFRS.
  - Its RTA and fund-accounting services support hedge fund, PE, VC, real-estate and fund-of-funds strategies.
  - It offers fund accounting, automated reconciliation and PMS services to AMC, AIF and portfolio-manager clients.
  - Source: [KFintech AIF page](https://www.kfintech.com/alternate-investment-fund/)
- **Charles River:** a search for Indian AMCs choosing Charles River IMS found no Indian announcement. The Asian and emerging-market wins it did find were China AMC (2011, QDII), Nissay Asset Management (Japan) and Mexico's Operadora de Fondos Banorte (2024, cloud version). — [Asia Asset](https://www.asiaasset.com/?p=25378); [Global Custodian](https://www.globalcustodian.com/?p=36934); [CRD press releases 2024](https://www.crd.com/?p=38454)
- **Infrasoft Technologies (Mumbai)** sells the OMNIEnterprise line, which includes a Wealth Management module and an AML module aimed at banks and insurers. One profile lists LIC and UBS as investors in Infrasoft. I found no named insurer using OMNI, and the source is thin and secondary. — [CB Insights](https://www.cbinsights.com/compare/infrasoft-technologies-vs-oracle-financial-services)

### Inferences
- In public announcements (2020–2023), Bloomberg AIM is the most visible OMS-plus-compliance choice among Indian MF AMCs. Four named adopters are not market-share evidence.
- The pattern suggests Indian AMCs split the stack into separate layers:
  - OMS with pre- and post-trade compliance (AIM);
  - analytics, risk and attribution (PORT);
  - books of record, fund accounting and reconciliation, often bought from RTAs, custodians or fintechs (mPower, iMatch).
  
  Only the Bloomberg and KFintech parts of this are sourced.
- To compare a small self-built tracker against "institutional grade", check four layers: (1) order capture and routing with an audit trail; (2) a rules engine for pre-trade and post-trade compliance; (3) independent books of record reconciled to custodian, depository and broker data; (4) analytics and reporting.

### Gaps
- **Vendors not verified:** I found no sources for SS&C (Geneva/Advent/Moxy), FIS, SimCorp, Temenos/Multifonds, Charles River's Indian clients, Wealth Spectrum, Fundtec, Investwell, CAMS fund-accounting services, TCS BaNCS, Nucleus Software, 63 moons (ODIN), Omnesys NEST/Refinitiv or FlexTrade. Searching stopped when the budget ran out. Treat each as an unverified lead, not evidence of use.
- **Pricing:** none of the results gave pricing for any platform (AIM/PORT, Charles River, fund-accounting or PMS back-office software).
- **Job postings:** not searched.
- **Insurers:** they are regulated by IRDAI, not SEBI. Their investment-system requirements (for example, front-, mid- and back-office separation, or investment-risk-system audits) and vendors were not researched.

## 2. SEBI requirements a mutual fund platform must support: investment limits, breach rebalancing, small/mid-cap stress tests, risk-o-meter, portfolio disclosure, CSCRF and cloud

### Takeaway
The rulebook changed in 2026:
- The SEBI (Mutual Funds) Regulations, 2026 replaced the 1996 Regulations from 1 April 2026.
- A new Master Circular for Mutual Funds dated 20 March 2026 replaced the one of 27 June 2024.
- Investment restrictions moved from the old Seventh Schedule to a Sixth Schedule, and the single-company concentration cap is no longer a fixed number in the regulation. It is left to "prudential norms" that SEBI sets.

A platform must support:
- issuer and group exposure monitoring, with a 30-business-day clock for rebalancing passive breaches (extendable by up to 60 business days by the Investment Committee);
- monthly risk-o-meter scoring;
- monthly portfolio disclosure, plus fortnightly disclosure for debt schemes;
- AMFI's monthly liquidity stress test and risk parameters for small-cap and mid-cap schemes;
- Monthly Cumulative Report (MCR) reporting to SEBI;
- cyber and cloud controls under SEBI's Cybersecurity and Cyber Resilience Framework (CSCRF).

### Cited Findings
**Regulatory base in 2026 (what supersedes what)**
- **SEBI (Mutual Funds) Regulations, 2026:**
  - They replace the 1996 Regulations, with repeal-and-saving provisions. Most sources say they were notified on 14 Jan 2026; one paper says 10 Jan and also mentions 16 Jan (flag).
  - They took effect on 1 Apr 2026.
  - They fold the MF Lite (passive funds) and Specialized Investment Fund (SIF) frameworks into one instrument.
  - Reported changes include a restructured expense framework, more disclosure and stronger governance.
  - Sources: [iPleaders](https://blog.ipleaders.in/sebi-mutual-funds-regulations-2026/); [CNLU](https://carcil.cnlu.ac.in/?p=594); [Wright Research](https://www.wrightresearch.in/blog/sebi-mutual-fund-regulations-2026/); [NUALS Law Journal](https://nualslawjournal.com/2026/06/05/rewriting-the-rules-sebi-mutual-funds-regulations-2026-and-the-new-era-of-investing/); [ELP alert](https://elplaw.in/leadership/sebi-revamps-and-replaces-its-30-year-old-regulations-for-mutual-funds/)
- **Investment restrictions under the 2026 Regulations:**
  - They have moved from the old Seventh Schedule to a Sixth Schedule. In places, fixed numbers are replaced by SEBI-prescribed prudential limits.
  - Clause 9 of the Sixth Schedule leaves the single-company concentration limit to "prudential norms" that SEBI sets from time to time; it is "no longer hard-coded as a fixed percentage".
  - One commentary calls this "neutral to slightly tightening" because SEBI can tailor issuer limits by fund category.
  - Sources: [ELP March 2026 PDF](https://elplaw.in/wp-content/uploads/2026/03/SEBI-Revamps-and-Replaces-Its-30-Year-Old-Regulations-for-Mutual-Funds-2.pdf); [ELP part 1](https://elplaw.in/wp-content/uploads/2026/03/SEBI-Revamps-and-Replaces-Its-30-Year-Old-Regulations-for-Mutual-Funds-1.pdf)
- A NISM Series V-A study guide, updated August 2026, confirms the industry has operated under the 2026 Regulations since 1 Apr 2026. — [open-exam-prep NISM guide](https://open-exam-prep.com/study-guides/nism-series-v-a/legal-and-regulatory-framework/role-of-sebi-and-mutual-fund-regulations)
- **Master Circular for Mutual Funds, 20 Mar 2026:**
  - Reference no. HO/24/13/11(1)2026-IMD-POD-1/I/7602/2026.
  - It consolidates circulars issued up to 20 Mar 2026 and replaces the Master Circular of 27 Jun 2024.
  - Conflict (flag): Taxmann describes its coverage as circulars up to 31 Mar 2024.
  - Sources: [Taxguru](https://taxguru.in/?p=1032873); [TeamLease RegTech](https://teamleaseregtech.com/updates/article/53893/sebi-issued-the-master-circular-for-mutual-funds/); [Taxmann](https://www.taxmann.com/post/blog/sebi-issues-updated-master-circular-for-mutual-funds/); [Oquilia](https://www.oquilia.com/news/sebi-mutual-fund-master-circular-mar-2026)
- **Later changes to the 2026 Master Circular:**
  - An addendum of 25 Mar 2026 deferred the intraday-borrowing provisions (clause 5.9.1) to 15 Jul 2026. — [TeamLease RegTech](https://teamleaseregtech.com/updates/article/54011/sebi-issued-the-addendum-to-sebi-circular-on-borrowing-by-mutual-funds/)
  - A circular of 19 May 2026 revised the Monthly Cumulative Report (MCR) format from June 2026; it refers to clause 6.20 of the Master Circular. — [Taxguru](https://taxguru.in/?p=1044670) (flag: the summary did not tie this fact to a specific page)

**Legacy numeric limits (1996 Regulations; unverified whether carried into the 2026 prudential norms)**
- **Seventh Schedule, clause 10:** no scheme may invest more than 10% of NAV in the equity shares or equity-related instruments of any one company. Index funds, ETFs and sector or industry-specific schemes are exempt. — [TaxManagementIndia regulation text](https://www.taxmanagementindia.com/visitor/detail_act.asp?ID=35302); [SEBI MF Advisory Committee 1999 minutes via Mondo Visione](https://mondovisione.com/media-and-resources/news/meeting-of-the-sebi-advisory-committee-for-mutual-funds-held-on-august-12-1999-2011124/)
- **Ownership caps across all schemes:**
  - A mutual fund, across all its schemes, may not own more than 10% of any company's paid-up capital carrying voting rights.
  - The SIF rules cross-refer to this cap. If the fund already owns 10% of a company's voting capital, its SIF across all strategies may not own more than 5%.
  - Sources: [TaxManagementIndia](https://taxmanagementindia.com/visitor/detail_act.asp?ID=46256); [Mondo Visione](https://mondovisione.com/media-and-resources/news/meeting-of-the-sebi-advisory-committee-for-mutual-funds-held-on-august-12-1999-2011124/) (flag: page attribution)
- **Sponsor group:**
  - A mutual fund's total investment in listed or to-be-listed securities of its sponsor's group companies may not exceed 25% of the net assets of all its schemes.
  - The SEBI (MF) (Amendment) Regulations, 2024 amended clause 9(c) with effect from 2 Jul 2024, letting equity-oriented ETFs and index funds exceed this, subject to SEBI conditions.
  - Sources: [SCC Online](https://scconline.com/blog/post/2024/07/03/securities-and-exchange-board-of-india-mutual-funds-amendment-regulations-2024-notified/amp); [Taxmann](https://www.taxmann.com/post/blog/equity-oriented-etfs-and-index-funds-can-invest-in-listed-securities-of-sponsors-group-companies-beyond-25-sebi/)
- **Debt limits (2016-era, current status not verified):** single issuer 10% of NAV, extendable to 12% with trustee approval; a proposal to cut the sector cap from 30% to 25%. — [Taxguru](https://taxguru.in/?p=74062); [Money9](https://www.money9.com/news/mutual-funds/sebis-directive-for-mutual-funds-heres-all-you-need-to-know-15143.html) (flag)

**Breach monitoring and rebalancing**
- **SEBI circular SEBI/HO/IMD/PoD2/P/CIR/2025/92 (26 Jun 2025):**
  - It broadened clause 2.9 of the 27 Jun 2024 Master Circular. The 30-business-day rebalancing timeline used to cover only asset-allocation deviations; it now covers all passive breaches, including issuer-level, sector and group-level limits.
  - If a breach is not fixed within 30 business days, a written justification, including the efforts taken, must go to the Investment Committee.
  - The Investment Committee can extend the deadline by up to 60 business days.
  - If the portfolio is still not rebalanced, the AMC may not launch any new scheme until it is.
  - Index funds and ETFs are exempt.
  - Sources: [SCC Online](https://www.scconline.com/blog/post/2025/06/30/sebi-mutual-fund-passive-breach-rebalancing-timeline-update/); [Business Today](https://www.businesstoday.in/mutual-funds/story/sebi-clarifies-passive-breach-rules-mutual-funds-482063-2025-06-26); [HDFC Sky](https://hdfcsky.com/news/sebi-tightens-timelines-for-passive-breach-rebalancing-in-mutual-fund-portfolios); [Outlook Money](https://www.outlookmoney.com/amp/story/invest/sebi-clarifies-portfolio-rebalancing-timeline-for-passive-breaches-in-mutual-fund-schemes-know-impact-on-investors)
- The original 30-business-day rule for asset-allocation deviations dates from 2022. — [Moneylife](https://moneylife.in/article/sebi-mandates-30-days-period-for-mutual-funds-to-rebalance-schemes/66768.html)
- A 2026 Quantum AMC scheme document cites "para 3.11" of a Master Circular dated 20 Mar 2026 for this rule, so paragraph numbers changed in the 2026 consolidation. — [Quantum AMC](https://www.quantumamc.com/regulatory-document/application-form/577) (flag)

**Risk-o-meter**
- **SEBI circular SEBI/HO/IMD/DF3/CIR/P/2020/197 (5 Oct 2020), effective 1 Jan 2021:**
  - It sets six levels: Low, Low to Moderate, Moderate, Moderately High, High, Very High.
  - The rating is evaluated monthly and published on AMC and AMFI websites with the portfolio disclosure, within 10 days of month end.
  - Each year AMCs disclose the level as of 31 March, together with the history of changes during the year.
  - The rating is based on the portfolio's holdings, not the benchmark. Equity schemes are scored on market cap, volatility and impact cost; debt schemes on credit, interest-rate and liquidity risk. The scores are averaged into a "risk value" between 1 and 12.
  - Investors must be told of a change by notice-cum-addendum and by email or SMS. A change is not a change in a "fundamental attribute" of the scheme.
  - Sources: [SEBI circular PDF](https://www.sebi.gov.in/sebi_data/attachdocs/oct-2020/1602580413614.pdf); [Business Standard](https://www.business-standard.com/amp/article/markets/decoding-risk-o-meter-3-0-and-its-use-as-an-investment-tool-in-the-mf-space-120100601112_1.html); [Value Research](https://www.valueresearchonline.com/stories/48592/sebi-rejigs-the-risk-o-meter/); [StudyCafe](https://studycafe.in/sebi-product-labeling-in-mutual-fund-schemes-risk-o-meter-91715.html); [Outlook Money](https://outlookmoney.com/invest/what-is-risk-o-meter-in-mutual-fund-investment-when-does-it-change--news-286589)
- One secondary source mentions a colour-coded change to the risk-o-meter on 5 Nov 2024; unverified. — [share.market](https://www.share.market/buzz/mutual-fund/mutual-fund-riskometer/) (flag)

**Portfolio disclosure**
- Debt schemes must disclose their portfolios every fortnight, within 5 days of the fortnight's end, from 1 Oct 2020. Yield must be shown for each security, not only for the portfolio. — [Cafemutual](https://cafemutual.com/news/industry/19804-sebi-asks-mfs-to-disclose-debt-fund-portfolios-on-a-fortnightly-basis); [DSIJ](https://insights.dsij.in/dsijarticledetail/sebi-enhances-transparency-in-debt-mfs-14000)
- Monthly portfolio disclosure is due within 10 days of month end. This is inferred indirectly from the risk-o-meter rule, which is published "along with portfolio disclosure within 10 days" (flag). — [Outlook Money](https://outlookmoney.com/invest/what-is-risk-o-meter-in-mutual-fund-investment-when-does-it-change--news-286589)
- HDFC MF's 2026 notice ties its fortnightly and monthly portfolio statements to the SEBI Master Circular. — [HDFC MF notice](https://www.hdfcfund.com/information/notice-fortnightly-monthly-portfolios)

**Small-cap and mid-cap stress tests (AMFI format)**
- **Origin:**
  - At SEBI's behest, an AMFI letter dated 28 Feb 2024 told AMCs to stress-test their small-cap and mid-cap schemes and publish the results on their websites by 15 Mar 2024.
  - Results were initially published every 15 days and are also posted on AMFI's website.
  - Sources: [Business Standard, 29 Feb 2024](https://www.business-standard.com/amp/markets/mutual-fund/mfs-told-to-disclose-stress-test-reports-of-midcap-smallcap-schemes-124022901229_1.html); [Business Standard, 12 Mar 2024](https://www.business-standard.com/amp/markets/mutual-fund/investor-concentration-volatility-indicators-among-stress-test-disclosures-124031200878_1.html)
- **Current frequency:**
  - Disclosure is now monthly, by the 15th, using the previous month's data. — [Freefincal](https://freefincal.com/a-better-way-to-stress-test-small-and-mid-cap-mfs/)
  - HSBC MF was still publishing monthly "disclosure of risk parameters" files for June and July 2026. — [HSBC June 2026](https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/48da9bd6-ba7d-4dc2-a0aa-313adaf94c8f/disclosure-of-risk-parameters-june-2026.pdf); [HSBC July 2026](https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/bb98ae07-36c1-4605-8785-8cffe51a7998/disclosure-of-risk-parameters-jul-26.pdf)
- **Liquidity method:**
  - The test reports the number of days needed to sell 50% and 25% of the portfolio, pro rata, under stress conditions.
  - The 20% of the portfolio that is least liquid is excluded.
  - It assumes 10% participation in the stock's 3-month average daily traded volume on NSE and BSE combined, with that volume multiplied by 3.
  - AMFI says pro-rata selling is a modelling assumption for equal treatment of investors, not a requirement in practice.
  - One summary phrases the test as days to liquidate "80% of the portfolio", which is ambiguous (flag).
  - Sources: [PersonalFN](https://www.personalfn.com/dwl/Mutual-Funds/what-is-the-capacity-and-liquidity-of-your-small-cap-fund); [Freefincal](https://freefincal.com/a-better-way-to-stress-test-small-and-mid-cap-mfs/); [Deccan Herald](https://deccanherald.com/amp/story/business%2Fmarkets%2Fwhy-the-ongoing-mf-stress-tests-should-not-worry-you-2951143)
- **Other parameters disclosed:**
  - the share of scheme assets held by the top 10 investors;
  - portfolio turnover ratio;
  - annualised standard deviation, for the scheme and for its benchmark;
  - portfolio beta;
  - trailing 12-month P/E, for the portfolio and for the benchmark.
  - Sources: [Business Standard, 12 Mar 2024](https://www.business-standard.com/amp/markets/mutual-fund/investor-concentration-volatility-indicators-among-stress-test-disclosures-124031200878_1.html); [Cafemutual](https://cafemutual.com/news/press-news/31635-stress-tests-by-amcs-risk-metrics-of-small-midcap-funds-in-focus); [HSBC Feb 2024 disclosure](https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/9f54e684-dddb-44bc-a106-a07956c1828a/disclosure-of-risk-parameters-feb-2024.pdf)
  - The market-cap mix (large, mid and small) is also reported. — [Upstox](https://upstox.com/news/personal-finance/mutual-funds/small-cap-fund-stress-test-schemes-with-greater-midcap-exposure-fare-better-on-liquidity/article-199276/)
- **Results, early disclosures** (2024; the summaries do not give an exact date; flag):

  | Schemes | Days to sell 50% | Days to sell 25% |
  |---|---|---|
  | Small cap | 22–60 | 11–30 |
  | Mid cap | 7–34 | 6–17 |

  Sources: [Deccan Herald](https://deccanherald.com/amp/story/business%2Fmarkets%2Fwhy-the-ongoing-mf-stress-tests-should-not-worry-you-2951143); [Cafemutual round 2](https://cafemutual.com/news/press-news/31901-mf-stress-test-round-2-has-top-small-cap-funds-improved-their-liquidity-positions)
- **Results, July 2026 data:**
  - The data covered 28 small-cap funds with about ₹4.5 lakh crore in assets.
  - Samco Small Cap (22.41% in mid caps) could sell 50% of its portfolio in 0.06 days.
  - Quant Small Cap (8.81% mid caps, 65.06% small caps) needed 48 days for 50% and 24 days for 25%.
  - Source: [Upstox](https://upstox.com/news/personal-finance/mutual-funds/small-cap-fund-stress-test-schemes-with-greater-midcap-exposure-fare-better-on-liquidity/article-199276/)
- **One AMC's internal trigger:** Taurus MF's policy starts a review if days-to-liquidate rise by more than 50% over the previous month or quarter. — [Taurus MF policy](https://taurusmutualfund.com:443/sites/default/files/2024-03/Final_Policy_on_Mid-Cap_and_Small-Cap_Schemes.pdf)
- **SEBI's stance:** SEBI whole-time member Ananth Narayan G. urged AMFI and the industry to run industry-wide tests. SEBI said in August 2024 that it would release its own findings. — [Business Standard, Aug 2024](https://business-standard.com/markets/mutual-fund/market-regulator-sebi-to-release-stress-test-findings-on-equity-mfs-124082301086_1.html); [Business Today](https://www.businesstoday.in/amp/personal-finance/news/story/mutual-funds-market-regulator-sebi-to-release-stress-test-findings-on-small-cap-funds-442849-2024-08-24)
- **Formal status of equity stress tests:** I found no 2025 SEBI circular that formalises them. A secondary source says the 2026 Regulations require stress testing, with public disclosure, for all open-ended debt schemes. — [iPleaders](https://blog.ipleaders.in/sebi-mutual-funds-regulations-2026/); [Wright Research](https://www.wrightresearch.in/blog/sebi-mutual-fund-regulations-2026/) (flag: which page said it)
- **Debt-scheme stress testing and liquid assets:**
  - A SEBI circular of 6 Nov 2020 required stress testing for all open-ended debt schemes except overnight funds, from 1 Dec 2020.
  - AMFI Best Practices Circular No. 103 (Oct 2022) proposed a common method and disclosure of the NAV impact.
  - Open-ended debt schemes must hold at least 10% of net assets in liquid assets. Overnight, liquid, gilt and 10-year constant-duration gilt funds are exempt.
  - Sources: [AMFI Circular No. 103](https://www.amfiindia.com/%5CThemes%5CTheme1%5Cdownloads%5Ccirculars%5CSEBI%5CCU135-AMFI%20Best%20Practices%20Guidelines%20Circular%20No.103-%20Stress%20Testing%20by%20Debt%20schemes%20of%20MFs.pdf); [Outlook Business](https://www.outlookbusiness.com/mutual-funds/sebi-asks-debt-mf-schemes-to-hold-10-liquid-assets-mandates-stress-testing-5475)

**Cybersecurity (CSCRF), cloud and data localisation**
- **CSCRF: SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113 (20 Aug 2024)** sets a risk-based model with five categories of regulated entity: MIIs, Qualified REs, Mid-size REs, Small-size REs and Self-certification REs. — [KS&K](https://ksandk.com/newsletter/clarifications-to-cscrf-for-sebi-regulated-entities/); [APMI update](https://apmiindia.org/storagebox/images/Circulars/APMI%20Update%20on%20SEBI%20CSCRF%20Circular%20dated%2020th%20August'24.pdf); [ELP, May 2025](https://elplaw.in/leadership/changes-to-sebis-cyber-security-and-cyber-resilience-framework-for-aifs/)
- **CSCRF timelines:**
  - Original effective date: 1 Jan 2025.
  - In late December 2024, compliance for KRAs and depository participants moved to 1 Apr 2025. The data-localisation guidelines were "kept in abeyance until further notification", pending further consultation.
  - Circular …/2025/45 (28 Mar 2025) moved the deadline to 30 Jun 2025 for all regulated entities except MIIs, KRAs and qualified RTAs (QRTAs).
  - Circular …/2025/96 (30 Jun 2025) moved it to 31 Aug 2025 for the same group.
  - During the extensions SEBI would take no action against entities that could show meaningful progress.
  - Sources: [Taxmann (extension)](https://www.taxmann.com/post/blog/sebi-extends-cscrf-deadline-for-regulated-entities); [Taxmann (clarification)](https://www.taxmann.com/post/blog/sebi-clarifies-w-r-t-the-applicability-of-the-cybersecurity-and-cyber-resilience-framework-cscrf-extends-implementation-date); [Lexplosion](https://lexplosion.in/sebi-issues-extension-in-timeline-towards-adoption-and-implementation-of-cybersecurity-and-cyber-resilience-framework-for-regulated-entities/); [MSEI circular](https://www.msei.in/SX-Content/Circulars/2025/July/Circular-17462.pdf); [NSE circular](https://nsearchives.nseindia.com/content/circulars/INSP65940.pdf)
- **April 2025 clarification:** an entity's category is fixed at the start of each financial year from the previous year's data. KRAs moved from MIIs to Qualified REs. — [KS&K](https://ksandk.com/newsletter/clarifications-to-cscrf-for-sebi-regulated-entities/); [YourStory](https://yourstory.com/2025/05/sebi-categorises-entities-size-risk-level-basis-cybersecurity)
- **Other CSCRF obligations** (from vendor and consultancy blogs; flag):
  - NSE and BSE run a Market SOC (M-SOC) for smaller entities. Others may run a security operations centre in-house, through a group entity or through a third party.
  - Third-party (vendor) risk management is mandatory for MIIs, Qualified REs and Mid-size REs.
  - Entities must hold a software bill of materials (SBOM) for critical systems. Any new software or SaaS for core or critical activities must come with an SBOM at procurement.
  - Cloud and data-localisation controls are listed as mandatory for all entities except Small-size and Self-certification REs.
  - Sources: [SecurityHQ](https://www.securityhq.com/blog/new-sebi-cybersecurity-cyber-resilience-framework-what-compliance-measures-mean-for-india-based-business/); [Ampcus Cyber](https://www.ampcuscyber.com/blogs/understanding-sebi-cscrf/); [Sonatype](https://www.sonatype.com/blog/simplifying-sbom-compliance-with-sonatype-under-indias-cybersecurity-framework); [KPMG India, Dec 2025](https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2025/12/sbom-in-indias-regulatory-landscape-building-trust-hrough-transparency.pdf)
- **Cloud framework: SEBI/HO/ITD/ITD_VAPT/P/CIR/2023/033 (6 Mar 2023):**
  - It is built on nine principles, including Principle 3 (data ownership and data localisation) and Principle 9 (vendor lock-in and concentration risk).
  - It applied at once to new cloud onboarding; existing users had 12 months to comply.
  - Mutual funds and AMCs are in scope.
  - It splits responsibility for controls between the cloud provider and the regulated entity.
  - Sources: [SEBI circular page](https://www.sebi.gov.in/legal/circulars/mar-2023/framework-for-adoption-of-cloud-services-by-sebi-regulated-entities-res-_68740.html); [Taxmann](https://www.taxmann.com/post/blog/sebi-introduces-framework-for-adoption-of-cloud-services-by-regulated-entities/); [Thales one-pager](https://cpl.thalesgroup.com/sites/default/files/content/compliance_brief/field_document/2023-04/2023-india-sebi-cloud-one-pager.pdf); [NSE circular](https://nsearchives.nseindia.com/content/circulars/INSP55895.pdf)

### Inferences
- **Limits must be parameters.** Since the 2026 Regulations moved issuer concentration into SEBI "prudential norms", hard-coding 10% is fragile. The minimum rule set is:
  - issuer % of NAV, per scheme;
  - % of an issuer's voting paid-up capital, summed across all schemes of the fund house (10% under the 1996 Regulations; 5% at SIF level);
  - sponsor-group exposure summed across all schemes (25% under the 1996 Regulations, with an ETF/index-fund carve-out);
  - sector and group limits;
  - exemptions that depend on scheme type (index fund, ETF, sector fund).
- **Breach workflow** needs:
  - a split between active breaches (caused by trades) and passive breaches (caused by market movement or corporate actions);
  - a business-day calendar driving the 30-day clock;
  - a record of the Investment Committee's written justification and of any extension of up to 60 business days;
  - a flag for the "no new scheme launches" consequence.
- **Monthly production jobs:**
  - a risk-o-meter score (risk value 1–12 mapped to six levels) for every scheme, published within 10 days;
  - monthly and fortnightly holdings files;
  - the MCR in the format revised in May 2026;
  - the AMFI risk-parameter sheet by the 15th.
- **Stress-test calculation inputs:**
  - per-stock 3-month average daily traded volume from NSE and BSE;
  - a configurable participation rate (10%) and stress multiplier (3×);
  - exclusion of the least-liquid 20%;
  - pro-rata liquidation.

  Read literally, the daily capacity per stock is 10% × 3 × that average volume, roughly 30% of a normal day's volume. That arithmetic is my reading, not AMFI text. Investor-concentration metrics also need RTA (unitholder) data, which a holdings-only tool will not have.
- **Who CSCRF covers:** any third-party portfolio or OMS platform used by an AMC falls under the AMC's vendor-risk, SBOM and cloud obligations, plus localisation once the abeyance is lifted. A self-built tool used privately is not itself a SEBI regulated entity.

### Gaps
- **Single-issuer cap:** I could not confirm the numeric single-issuer equity cap now in force under the 2026 Sixth Schedule or SEBI's prudential-norms circular. I don't know whether 10% of NAV and 10% of paid-up capital still apply unchanged.
- **Other limits:** I found no equity sector, group or derivative position limits for MFs.
- **Disclosure deadlines:** the primary text for the 10-day monthly deadline was not seen, and I found nothing on half-yearly disclosure.
- **Stress test:** whether bulk and block deals are excluded from the volume base was not confirmed. The AMFI methodology document itself was not seen; amfiindia.com returned 403.
- **CSCRF:** I found no CSCRF thresholds for MFs/AMCs. I could not tell whether the data-localisation abeyance was lifted in late 2025 or 2026, or whether the 2023 cloud framework now sits inside CSCRF. I found no CSCRF changes after 31 Aug 2025.
- **Benchmark risk-o-meter:** a separate risk-o-meter for the benchmark was not found.
- **Unverified claim, not used above:** a summary said that if the AUM of the deviated portfolio is more than 10% of the main portfolio's AUM, AMCs must inform investors at once by SMS, email or letter. I could not verify it.

## 3. SEBI requirements for PMS and AIFs: performance and benchmarking, client reporting, audit and compliance, concentration

### Takeaway
Portfolio managers must report each investment approach's time-weighted rate of return (TWRR) against one of up to three APMI-prescribed benchmarks for its strategy (equity, debt, hybrid or multi-asset). Debt holdings must be valued by APMI-empanelled agencies. This comes from SEBI's circular of 16 Dec 2022, effective 1 Apr 2023. The PMS rulebook is now consolidated in the Master Circular of 16 Jul 2025. Several things could not be verified: AIF benchmarking, Category III concentration and leverage limits, PMS associate and unlisted-security limits, and the format and frequency of PMS client statements.

### Cited Findings
- **SEBI circular SEBI/HO/IMD/IMD-PoD-2/P/CIR/2022/172 (16 Dec 2022):**
  - Each investment approach is tagged to one of four strategies: equity, debt, hybrid or multi-asset.
  - APMI prescribes at most three benchmarks per strategy, and the portfolio manager picks one.
  - Performance is shown as the approach's TWRR next to the trailing return of the chosen benchmark.
  - Performance relative to other portfolio managers in the same strategy is also disclosed.
  - Debt and money-market securities must be valued by agencies empanelled by APMI.
  - Effective 1 Apr 2023.
  - Sources: [Outlook Business](https://www.outlookbusiness.com/news/sebi-issues-performance-benchmarking-guidelines-for-portfolio-managers-news-245611); [Business Standard](https://www.business-standard.com/article/markets/sebi-issues-performance-benchmarking-guidelines-for-portfolio-managers-122121600879_1.html); [SEBI circular copy (Aparajitha)](https://compfie.aparajitha.com/wp-content/uploads/2022/12/19122022_FCC_03.pdf); [GKToday](https://www.gktoday.in/sebi-new-benchmarking-norms-for-portfolio-managers/)
- APMI circular APMI/2022-23/02 (23 Mar 2023) put the benchmarking and reporting rules into effect from 1 Apr 2023 and lists the prescribed benchmarks in Annexure 1. — [APMI circular](https://www.apmiindia.org/storagebox/images/Circulars/APMI-Circular-2-BENCHMARKING.pdf)
- Smaller portfolio managers asked for an extension to 1 Jun 2023. — [Business Standard, Mar 2023](https://www.business-standard.com/article/markets/pms-benchmarking-norms-industry-players-seek-three-month-extension-123030101080_1.html)
- **Master Circular for Portfolio Managers, SEBI/HO/IMD/IMD-POD-1/P/CIR/2025/104 (16 Jul 2025):**
  - It consolidates circulars issued up to 31 Mar 2025 and replaces the 7 Jun 2024 version.
  - It covers disclosure and reporting duties to clients and to SEBI.
  - It rescinds 39 older circulars, including ones on performance disclosure.
  - Sources: [Taxguru](https://taxguru.in/sebi/sebi-updates-portfolio-managers-master-circular.html); [APMI copy](https://www.apmiindia.org/storagebox/images/Circulars/Master%20Circular%20for%20Portfolio%20Managers%20-%2016th%20July'25.pdf); [HDFC Sky](https://hdfcsky.com/news/sebi-consolidates-regulatory-framework-for-portfolio-managers-in-master); [Taxmann](https://www.taxmann.com/post/blog/sebi-issues-updated-master-circular-for-portfolio-managers)
- SEBI removed the fixed disclosure-document format from Schedule V of the Portfolio Managers Regulations, 2020. Disclosure requirements now sit in circulars, and managers must keep revising their documents to match. — [KS&K](https://ksandk.com/newsletter/sebi-circular-on-portfolio-management-services-pms/)
- **Regulatory filings to SEBI under the 2025 master circular** include a monthly portfolio-activity report and quarterly off-site inspection data. Monthly reporting by portfolio managers goes back to a June 2009 circular. — [Lawrbit compliance calendar](https://www.lawrbit.com/article/portfolio-managers-compliance-calendar-sebi-filings/); [SEBI 2009 circular](https://www.sebi.gov.in/legal/circulars/jun-2009/submission-of-monthly-report-by-portfolio-managers_5772.html)
- **CSCRF categories for portfolio managers** (clarification of 30 Apr 2025):
  - no Qualified RE category;
  - Mid-size: AUM above ₹3,000 crore;
  - Self-certification: AUM of ₹3,000 crore or less.
  - Sources: [APMI copy of clarification](https://apmiindia.org/storagebox/images/Circulars/Clarifications%20on%20CSCRF%20for%20SEBI%20Regulated%20Entities%20-%2030th%20April'25.pdf); [KS&K](https://ksandk.com/newsletter/clarifications-to-cscrf-for-sebi-regulated-entities/)
- **CSCRF categories for AIFs:**

  | Category | Aug 2024 circular: AIF AUM | From 30 Apr 2025: manager's combined corpus |
  |---|---|---|
  | Qualified RE | ₹1,000 crore and above | none (no AIF is a Qualified RE) |
  | Mid-size | ₹500–1,000 crore | above ₹10,000 crore |
  | Small-size | ₹100–500 crore | ₹3,000–10,000 crore |
  | Self-certification | below ₹100 crore | below ₹3,000 crore |

  From April 2025 the category is set at investment-manager level, using the combined corpus of all schemes. Sources: [ELP, May 2025](https://elplaw.in/leadership/changes-to-sebis-cyber-security-and-cyber-resilience-framework-for-aifs/); [Venture Intelligence](https://news.ventureintelligence.com/private-equity/sebi-allows-aifs-with-less-than-rs.3%2C000-cr-corpus-to-self-certify-under-cyber-resilience-framework); [KS&K](https://ksandk.com/newsletter/clarifications-to-cscrf-for-sebi-regulated-entities/)

### Inferences
- **What a PMS platform must compute:**
  - TWRR per investment approach, aggregated from many segregated client accounts, with returns chained across external cash flows;
  - a comparison against the one benchmark chosen from APMI's Annexure 1 list for that strategy;
  - an export in the form APMI needs for its cross-manager performance comparison;
  - for debt holdings, prices from an APMI-empanelled valuation agency rather than self-sourced prices.
- **CSCRF burden:** most boutique PMS firms (₹3,000 crore AUM or less) and AIF managers below ₹3,000 crore corpus are Self-certification REs with lighter obligations. Larger managers carry Mid-size obligations, including third-party risk management.

### Gaps
- **PMS client reporting:** I could not verify the frequency and content of client statements. They are believed to be at least quarterly but this is unconfirmed. Also unverified: the TWRR formula details, including whether returns are net of fees, and fee and high-water-mark rules.
- **PMS concentration and onboarding:** limits on investment in associates or related parties, limits on unlisted securities, model-portfolio rules and direct-onboarding rules were not verified; the search budget ran out.
- **AIFs:** I verified none of the following: the performance-benchmarking regime (benchmarking agencies, vintage-wise reporting), the date and number of the AIF Master Circular, Category III single-company concentration (10% versus a reported 20% for listed equity), the leverage cap, or the annual PPM audit.

## 4. Investment-process and governance expectations: investment committee records, audit trails, dealing-room controls, front-running and insider-trading surveillance, best execution and allocation fairness

### Takeaway
Since 2020 SEBI has required AMC dealing rooms to use recorded lines only. Personal devices are barred, internet access is restricted, and recordings are reviewed periodically and kept for at least 8 years. AMCs must also have a written trade-execution and allocation policy. Since August 2024 (effective about 1 Nov 2024, phased in through AMFI standards), AMCs must run an alert-based surveillance, internal-control and escalation mechanism against front-running and insider trading, for which the CEO/MD and the Chief Compliance Officer are accountable. The 2021 Risk Management Framework requires a Chief Risk Officer, board-approved policies and reporting to trustees.

### Cited Findings
- **September 2020 SEBI circular**, issued after the HDFC AMC front-running case:
  - AMCs must have a policy on trade execution and allocation.
  - Dealers may talk only over dedicated recorded lines, and no other communication devices are allowed in the dealing room.
  - Internet access on dealing-room devices must be restricted.
  - Designated staff must review recordings periodically and send their reports to trustees. Internal auditors' terms of reference must cover these reviews, and the reports must be available for SEBI inspection.
  - Recordings must be kept for at least 8 years.
  - Sources: [Business Standard, 17 Sep 2020](https://www.business-standard.com/amp/article/markets/sebi-asks-mfs-to-put-in-place-policy-on-trade-execution-allocation-120091701311_1.html); [SEBI circular copy (Aparajitha)](https://compfie.aparajitha.com/wp-content/uploads/2020/09/18092020_FCC_01.pdf); [Value Research](https://www.valueresearchonline.com/stories/101390/sebi-bans-phone-calls-in-dealing-rooms/); [Taxguru](https://taxguru.in/?p=32555)
- Some AMCs already went further: soundproofed dealing rooms, CCTV, and recording fund managers' calls as well as dealers'. This comes from press reporting. — [Value Research](https://www.valueresearchonline.com/stories/101390/sebi-bans-phone-calls-in-dealing-rooms/) (flag)
- **August 2024 front-running mechanism** (circular dated 5 Aug 2024; the MF Regulations were amended on about 2 Aug 2024; flag on exact dates):
  - AMCs must have enhanced surveillance systems, internal control procedures and escalation processes to identify, monitor and deal with market abuse, including front-running and insider trading, with escalation to the AMC board.
  - The CEO/MD and the Chief Compliance Officer are accountable.
  - AMFI, in consultation with SEBI, was to issue implementation standards within 15 days.
  - Possible actions include suspending or terminating employees, brokers or dealers.
  - When processing alerts, AMCs must consider recorded communications (chats, emails), dealing-room access logs and CCTV footage. Written procedures must be board-approved, and there must be a whistle-blower mechanism.
  - Sources: [Cafemutual](https://cafemutual.com/news/industry/32011-sebi-directs-amcs-to-put-in-place-a-mechanism-to-curb-front-running); [Outlook Money](https://www.outlookmoney.com/invest/equity/sebi-frames-norms-for-amcs-to-combat-insider-trading-and-market-abuse); [5paisa](https://5paisa.com/news/sebi-introduces-rules-to-stop-front-running-and-insider-trading-in-mutual-funds); [CBCL (NLIU)](https://cbcl.nliu.ac.in/capital-markets-and-securities-law/plugging-leaks-sebis-new-frontrunning-guidelines-for-amcs/); [Metalegal](https://www.metalegal.in/post/sebi-introduces-new-institutional-mechanism-to-prevent-fraudulent-transactions-in-amcs)
- **Start dates:**
  - One outlet says the rules took effect on 1 Nov 2024.
  - A single student-written article gives a phased rollout:
    - Nov 2024: equity schemes of AMCs with equity AUM above ₹10,000 crore;
    - Feb 2025: smaller equity schemes;
    - May 2025: all trades in schemes;
    - Aug 2025: debt securities.
  - Sources: [One Percent Club](https://news.onepercentclub.io/stock-market/sebi-tightens-amc-rules-front-running-insider-trading/15914/); [CBCL (NLIU)](https://cbcl.nliu.ac.in/capital-markets-and-securities-law/plugging-leaks-sebis-new-frontrunning-guidelines-for-amcs/) (flag)
- **Trigger:** SEBI's 2024 investigation of Quant MF over alleged front-running. — [Outlook Money](https://www.outlookmoney.com/invest/equity/sebi-frames-norms-for-amcs-to-combat-insider-trading-and-market-abuse)
- **Risk Management Framework: SEBI/HO/IMD/IMD-1 DOF2/P/CIR/2021/630 (27 Sep 2021):**
  - Every AMC needs a Chief Risk Officer, plus CXO-level officers who own the risks of specific functions.
  - Risks are split into scheme-specific risks (investment, credit, liquidity, governance) and AMC-specific risks (operational, outsourcing and others).
  - Elements are either "mandatory" or "recommendatory".
  - The board approves the risk, investment, credit, liquidity, operational, outsourcing, cyber-security and business-continuity policies.
  - AMCs self-assess and review annually, with the reports going to the AMC board and trustees. Trustees may pass findings to SEBI in their half-yearly reports.
  - Effective date conflict: 1 Jan 2022 per SCC Online, 1 Apr 2022 per a DSP document (flag).
  - Sources: [Business Standard](https://www.business-standard.com/amp/article/markets/sebi-beefs-up-risk-management-norms-asks-mfs-to-appoint-dedicated-officer-121092701209_1.html); [Business Today](https://businesstoday.in/top-story/story/sebi-issues-revised-risk-management-framework-for-mfs-307792-2021-09-27); [SCC Online](https://www.scconline.com/blog/post/2021/09/29/sebi-issues-risk-management-framework-for-mutual-funds/); [DSP RMF policy](https://www.dspim.com/media/pages/mandatory-disclosures/5e30fc28e8-1761847399/risk-management-framework-and-policy.pdf); [Canara Robeco CXO roles](https://www.canararobeco.com/wp-content/uploads/2025/07/Roles-Responsibilities-of-CXOs-and-CXO-level-officers.pdf)
- The 2025 passive-breach rule (see §2) requires a written justification to the Investment Committee and an IC decision on any extension. That creates a required record of IC decisions tied to each breach. — [SCC Online](https://www.scconline.com/blog/post/2025/06/30/sebi-mutual-fund-passive-breach-rebalancing-timeline-update/)

### Inferences
An institutional-grade platform in India needs:
- an unalterable, time-stamped audit trail running from the fund manager's decision and rationale, through the order and dealer, to broker placement, execution and allocation across schemes;
- pre-allocation of block orders, plus evidence that allocation followed the board-approved allocation policy;
- surveillance alerts that compare scheme orders with trading by employees, brokers and connected persons, linked to the communications archive (kept 8 years);
- regular surveillance and risk reports to the AMC board and trustees;
- Investment Committee minutes linked to breach records.

A personal tracker has none of these; this is the largest functional gap.

### Gaps
- The exact circular number of the August 2024 circular and the text of AMFI's implementation standards were not seen.
- Not verified:
  - how the SEBI (Prohibition of Insider Trading) Regulations apply to MF units;
  - any rule on recording investment-decision justifications;
  - inter-scheme transfer conditions;
  - expectations for measuring best execution (transaction cost analysis);
  - stewardship-code voting disclosures.

## 5. Risk and performance analytics Indian institutional investors, boards and trustees expect in practice

### Takeaway
The public, regulator-driven analytics for Indian equity mutual funds centre on:
- liquidity, measured as days to liquidate;
- volatility (standard deviation versus benchmark) and beta;
- valuation (trailing P/E versus benchmark);
- turnover;
- top-10 investor concentration;
- risk-o-meter inputs (market cap, volatility, impact cost).

On top of these, the 2021 Risk Management Framework requires risk metrics and reports to boards and trustees, and PMS performance must be TWRR against a benchmark. Vendor adoption shows AMCs buying analytics tools, such as Bloomberg PORT at DSP and AIM portfolio analytics at NJ. I found no surveys of attribution or risk practice.

### Cited Findings
- **AMFI's monthly risk parameters for small-cap and mid-cap schemes** are:
  - top-10 investor concentration;
  - turnover ratio;
  - annualised standard deviation for scheme and benchmark;
  - beta;
  - trailing 12-month P/E for portfolio and benchmark;
  - days to liquidate 25% and 50% of the portfolio.
  - Source: [Business Standard, 12 Mar 2024](https://www.business-standard.com/amp/markets/mutual-fund/investor-concentration-volatility-indicators-among-stress-test-disclosures-124031200878_1.html)
- The risk-o-meter scores equity schemes on market cap, volatility and impact cost. — [SEBI circular PDF](https://www.sebi.gov.in/sebi_data/attachdocs/oct-2020/1602580413614.pdf)
- The RMF classifies investment, credit, liquidity and governance risk for each scheme and requires reports to the AMC board and trustees. — [SCC Online](https://www.scconline.com/blog/post/2021/09/29/sebi-issues-risk-management-framework-for-mutual-funds/); [DSP RMF policy](https://www.dspim.com/media/pages/mandatory-disclosures/5e30fc28e8-1761847399/risk-management-framework-and-policy.pdf)
- DSP added Bloomberg PORT Enterprise, and NJ AMC uses AIM for portfolio analytics. — Bloomberg press announcements, page not isolated (flag: [candidate](https://www.bloomberg.com/company/?p=28496)); [The TRADE](https://www.thetradenews.com/nj-asset-management-streamlines-order-management-and-compliance-management-with-bloomberg-solutions/)
- One AMC, Taurus, uses a change of more than 50% in days-to-liquidate as a trigger for review. — [Taurus MF](https://taurusmutualfund.com:443/sites/default/files/2024-03/Final_Policy_on_Mid-Cap_and_Small-Cap_Schemes.pdf)
- **Practitioner critique (an opinion):** the 3× volume multiplier rests only on post-COVID trading patterns. The author suggests using 1-year average volume across NSE and BSE at half weight instead. — [Freefincal](https://freefincal.com/a-better-way-to-stress-test-small-and-mid-cap-mfs/)

### Inferences
- **A minimum analytics checklist for an "institutional" comparison:**
  - returns: TWRR and returns relative to the benchmark;
  - risk: standard deviation and beta against the scheme benchmark, impact cost, and days to liquidate under configurable assumptions;
  - valuation: P/E against the benchmark;
  - portfolio shape: turnover and market-cap buckets;
  - investor base: concentration (needs investor data);
  - stress tests.
- Performance attribution (such as Brinson) did not appear in any regulatory requirement found. It is an expected but voluntary analytic, which is how tools like PORT are positioned. That positioning is my inference, not a sourced claim.

### Gaps
- I found no surveys or industry reports on attribution, risk or liquidity-analytics practice at Indian AMCs, PMS or AIFs, from EY, PwC, KPMG, BCG, Celent, CRISIL or others; the search budget ran out.
- Not verified in this session: the market-cap classification used for buckets. It is believed to be AMFI's half-yearly list, with large caps ranked 1–100, mid caps 101–250 and small caps 251 and below, under SEBI's October 2017 categorisation circular.

## 6. Technology spending and vendor market share in Indian asset management

### Takeaway
I found no report giving technology spend or vendor market shares for Indian asset managers. The only indirect evidence is a handful of named client announcements: four Bloomberg AIM adopters, and KFintech's purchase of Hexagram to enter fund accounting. That evidence does not support any share estimate.

### Cited Findings
- Four Indian MF AMCs publicly adopted Bloomberg AIM between 2020 and 2023 (Aditya Birla Sun Life, DSP, Bajaj Finserv, NJ). — [Bloomberg (ABSLAMC)](https://www.bloomberg.com/company/press/aditya-birla-sun-life-amc-becomes-indias-first-asset-manager-to-expand-adoption-of-bloomberg-aim-to-its-gift-city-unit); [Bloomberg (Bajaj Finserv AMC)](https://www.bloomberg.com/company/press/bajaj-finserv-asset-management-adopts-bloomberg-aim-to-power-digitization-journey); [The TRADE (NJ AMC)](https://www.thetradenews.com/nj-asset-management-streamlines-order-management-and-compliance-management-with-bloomberg-solutions/)
- KFintech bought Hexagram in February 2022 to move into fund accounting and reconciliation. The terms were not disclosed. — [Business Standard](https://www.business-standard.com/article/companies/kfin-buys-hexagram-to-expand-into-fund-accounting-reconciliation-solutions-122020900807_1.html)
- CSCRF was re-categorised in April 2025: AIF managers below ₹3,000 crore and PMS firms at or below ₹3,000 crore AUM became Self-certification REs. That signals SEBI is easing compliance-technology costs for smaller managers. — [Venture Intelligence](https://news.ventureintelligence.com/private-equity/sebi-allows-aifs-with-less-than-rs.3%2C000-cr-corpus-to-self-certify-under-cyber-resilience-framework); [KS&K](https://ksandk.com/newsletter/clarifications-to-cscrf-for-sebi-regulated-entities/)

### Inferences
- Market structure seems to be shifting toward RTAs and fintechs providing outsourced fund accounting and reconciliation (KFintech/Hexagram), alongside global vendors for the front office (Bloomberg). This is directional only.

### Gaps
- No figures on technology spend, budgets or vendor market share for Indian AMCs, PMS, AIFs or insurers were found or searched beyond the above, because the search budget ran out.
- Leads not checked: AMC annual reports (IT spend lines), KFintech and CAMS investor presentations (fund-accounting client counts), and consultancy reports.
