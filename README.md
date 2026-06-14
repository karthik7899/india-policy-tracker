# 🇮🇳 India Policy & Sector Impact Tracker

An automated, cloud-based platform that tracks Indian government policy announcements, evaluates their sector-wise impact, and maps them to a watchlist of high-growth beneficiary stocks. 

This platform runs entirely in the cloud for free using **GitHub Actions** and **Python**, sending daily and weekly summaries directly to your email. It also auto-publishes updates to an interactive, glassmorphic archive dashboard hosted on **GitHub Pages**.

---

## 🚀 Key Features

* **Daily & Weekly Email Digests:** Delivers beautifully formatted HTML emails highlighting positive, negative, and neutral policy impacts.
* **Official Data Aggregator:** Scrapes the Press Information Bureau (PIB) of India daily releases and financial news feeds via Google News RSS indexes concurrently.
* **Pre-Seeded Portfolios:** Curated stocks mapped to specific policies across 13 high-growth sectors:
  * **Clean Energy:** Solar, wind, and green hydrogen plays (Tata Power, Suzlon, Adani Green).
  * **Data Center Support:** Electrical grids and fiber infrastructure (Schneider, STL, Anant Raj).
  * **Cybersecurity:** Digital security and secure cloud consulting (TCS, Quick Heal).
  * **Surveillance & CCTV:** IP cameras, safe cities, and UAV defense (CPPLUS, Dixon, Allied Digital, IdeaForge).
  * **Manufacturing & Electronics:** Semiconductor fabrication and electronics assembly PLI plays (Dixon, Kaynes, CG Power).
  * **FMCG & Consumption:** Rural recovery and consumer brand scaling (Varun Beverages, Tata Consumer, ITC).
  * **Sports & Athleisure:** Athletic footwear and brand franchising (Metro Brands, Campus, Page Industries).
  * **Big Cap Industries:** National infrastructure, energy transition, and conglomerates (L&T, Reliance).
  * **Textiles & Apparel:** Apparel manufacturing, export parks, and production-linked schemes (Welspun Living, Arvind, Gokaldas Exports).
  * **Logistics & Heavy Capital:** Cargo handling, corridor connectivity, and freight transit infrastructure (Container Corporation, BHEL, Cummins India).
  * **Aerospace & Defence:** Precision avionics, indigenous manufacture, and military launch platforms (HAL, BEL, Astra Microwave).
  * **Semiconductors & Equipment:** Cleanroom tooling, design fabs, and machinery (SPEL Semiconductor, RIR Power, ASMPT).
  * **Macro Indicators:** Broad manufacturing benchmark index funds and sector ETFs (MANUETF, HDFCMANETF).
* **Value Investing Screeners (Graham & Buffett):**
  * **Benjamin Graham Screens:** Dynamically calculates expected growth intrinsic value, enterprising bargain NCAV net-assets status, and flags P/E screen deviations.
  * **Warren Buffett Screens:** Evaluates owner earnings (net profit + depreciation - capex), computes the $1 retained earnings test ratio, and tracks qualitative moat strength.
* **Institutional Flow Tracker:**
  * **Holding Pattern Changes:** Scrapes Screener.in to extract promoter, domestic (DII/Mutual Fund), and foreign (FII) quarterly holding shifts.
  * **Block & Bulk Deals Parser:** Scrapes and structures recent market transactions, identifying the buyer, action (BUY/SELL), target stock, transaction details, and direct media link.
  * **Thematic Fund Filings:** Scrapes SEBI mutual fund filings (Scheme Information Documents) to watch for upcoming thematic fund launches.
* **Automated Watchlist Rotation:** 
  * Checks emerging competitors discovered in news feeds.
  * Filters candidates through a strict **15% QoQ revenue growth threshold** (via Screener) and rotates weaker-performing watchlist tickers with stronger ones.
* **Self-Updating Web Dashboard:** The GitHub Action automatically commits the aggregated news log and updated watchlist into the codebase, updating the frontend pages instantly.

---

## 🛠️ Setup Instructions (Cloud Deployment)

To run this platform automatically in the cloud:

### 1. Push to GitHub
1. Create a new repository on GitHub (e.g., `india-policy-tracker`).
2. Push all the files from this directory to your new repository.

### 2. Configure GitHub Secrets
Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret** and add the following:

| Secret Name | Description | Example / Recommended Value |
|-------------|-------------|-----------------------------|
| `RECEIVER_EMAIL` | The email address that will receive the daily briefings | `yourname@gmail.com` |
| `SMTP_SERVER` | SMTP server address to send emails | `smtp.gmail.com` (for Gmail) or `smtp.resend.com` |
| `SMTP_PORT` | SMTP server port | `587` (for STARTTLS) or `465` (for SSL) |
| `SMTP_USERNAME`| Username to log in to SMTP server | `yourname@gmail.com` (Gmail) or `resend` |
| `SMTP_PASSWORD`| Password or API Token | Gmail App Password or Resend API token |

*Note: For Gmail, you must generate an **App Password** from your Google account settings under 2-Step Verification.*

### 3. Enable GitHub Pages Dashboard
1. Go to repository **Settings** -> **Pages**.
2. Under **Build and deployment** -> **Source**, select **Deploy from a branch**.
3. Choose the `main` branch and `/ (root)` folder, then click **Save**.
4. The dashboard will now be live at `https://yourusername.github.io/india-policy-tracker/`.

---

## 💻 Local Testing & Development

### 1. Installing Dependencies
Ensure you have Python installed, then install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Running the Aggregation Pipeline
To test the scrapers, value investing screeners, and institutional flows locally:
```bash
python brief.py
```
This writes the compiled JSON results to `dashboard_data.json` and outputs a local HTML briefing preview (`email_preview.html`).

### 3. Serving the Web Dashboard
Serve the directory locally using Python's lightweight web server:
```bash
python -m http.server 8000
```
Then navigate to `http://localhost:8000` in your web browser.

