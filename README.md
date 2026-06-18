# Portfolio Demon

A Python-based portfolio monitoring system that tracks your brokerage holdings via Google Sheets and sends strategic alerts via email. Designed for long-term retirement accounts with wide signal thresholds and weekly cadence.

**This is a monitoring tool, not a trading bot.** It never places orders. Every alert ends with "No action required — your decision."

## What It Does

- **Weekly digest** (Sunday 8pm ET) — full portfolio health, deployment opportunities, rotation signals
- **Daily silent check** (9am ET weekdays) — only alerts on stop-loss breaches
- **Correction alert** — immediate notification if S&P 500 drops >3% in a single day
- **80/20 balance tracking** — monitors core funds vs equity allocation with ±5% tolerance band
- **Dip scoring** — flags positions >7% below 50-day moving average with remaining headroom
- **Business cycle rotation** — adjusts signal priorities based on EARLY/MID/LATE/RECESSION phase
- **Live prices** — GOOGLEFINANCE via Apps Script (auto-refreshes daily) + yfinance for moving averages
- **Trade processing** — enter trades in the sheet, run a script, everything updates automatically

---

## End-to-End Setup

### Prerequisites

- Python 3.11+
- A brokerage account (Fidelity, Schwab, Vanguard, or any broker with CSV export)
- A Google account
- A Gmail account (for sending alerts via SMTP)
- A GitHub account (optional — for scheduled runs via GitHub Actions)

---

### Step 1: Clone the Repository

```bash
git clone <this-repo-url>
cd portfolio-demon
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 2: Google Cloud Service Account

The app reads and writes to a Google Sheet using a service account.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown → **New Project** → name it `portfolio-demon` → **Create**
3. Select the new project from the dropdown
4. Go to **APIs & Services → Library** → search **"Google Sheets API"** → **Enable**
5. Go to **APIs & Services → Credentials** → **Create Credentials → Service Account**
6. Name it `portfolio-demon-bot` → **Create and Continue** → skip optional steps → **Done**
7. Click the service account you just created → **Keys** tab → **Add Key → Create new key → JSON → Create**
8. A JSON file downloads — save it somewhere safe (e.g., `~/keys/portfolio-demon.json`)

---

### Step 3: Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → create a **new blank spreadsheet**
2. Name it whatever you like (e.g., "Portfolio Demon")
3. Open the JSON key file from Step 2 — find the `"client_email"` field (looks like `portfolio-demon-bot@portfolio-demon-XXXXX.iam.gserviceaccount.com`)
4. In the spreadsheet, click **Share** → paste that email → give **Editor** access → **Send**
5. Copy the **Sheet ID** from the URL bar:
   ```
   https://docs.google.com/spreadsheets/d/[COPY_THIS_PART]/edit
   ```

---

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
GOOGLE_SERVICE_ACCOUNT_JSON=<paste entire JSON key content on one line>
GOOGLE_SHEET_ID=<your sheet ID from step 3>
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
EMAIL_RECIPIENT=your-email@gmail.com
DRY_RUN=true
```

Alternatively, set `GOOGLE_SERVICE_ACCOUNT_JSON` to the **file path** of your JSON key:

```
GOOGLE_SERVICE_ACCOUNT_JSON=/Users/you/keys/portfolio-demon.json
```

---

### Step 5: Import Your Portfolio

Export your positions from your broker as CSV, then run the seed script.

**Fidelity:**
Log in → Positions → click **Download** (top right) → save the CSV

```bash
python scripts/seed_sheet.py --broker fidelity --csv ~/Downloads/Portfolio_Positions.csv
```

**Schwab:**
Log in → Positions → **Export** → CSV

```bash
python scripts/seed_sheet.py --broker schwab --csv ~/Downloads/Positions.csv
```

**Vanguard:**
Log in → My Accounts → Holdings → **Download** → CSV

```bash
python scripts/seed_sheet.py --broker vanguard --csv ~/Downloads/Holdings.csv
```

**Any other broker:**
Export positions as CSV (must have Symbol, Quantity, and Cost Basis columns)

```bash
python scripts/seed_sheet.py --broker generic --csv ~/Downloads/positions.csv
```

**Optional flags:**

```bash
# Override total account value and cash balance
python scripts/seed_sheet.py --broker fidelity --csv positions.csv --total 500000 --cash 200000

# Empty template (no CSV — add holdings manually in the sheet)
python scripts/seed_sheet.py
```

The script automatically:
- Imports holdings with cost basis from the CSV
- Detects cash/money market balance (SPAXX, SWVXX, VMFXX)
- Calculates total account value
- Sets up computed-column formulas (P&L, weights, headroom, avg cost)
- Adds dropdown validations on restricted columns
- Adds date pickers on date columns
- Adds GOOGLEFINANCE live price formulas

---

### Step 6: Review and Customize Your Sheet

After import, open the Google Sheet and review these columns in the **Holdings** tab:

| Column | What to set | Notes |
|--------|-------------|-------|
| **D** (category) | core_fund / quality_stock / speculative / new_defensive / existing_addition / trim_exit | Auto-guessed — verify each |
| **E** (planned_pct) | Target allocation % | e.g., 30 for 30% of total portfolio |
| **J** (stop_loss_pct) | Stop loss % below cost | 0 for core funds, 25-40 for stocks |
| **K** (take_profit_pct) | Take profit % above cost | 0 to disable |
| **L** (max_portfolio_pct) | Hard cap % of total portfolio | Overweight alert if exceeded |
| **M** (status) | active / new / watch / trim / exit | Dropdown |
| **N** (cycle_alignment) | positive / negative / neutral | Dropdown |
| **O** (notes) | Your investment thesis | Free text |

Also check the **Portfolio_Config** tab:

| Key | What it controls |
|-----|-----------------|
| TOTAL_IRA_VALUE | Total account value including cash |
| CASH_REMAINING | Uninvested cash (SPAXX/money market) |
| CYCLE_PHASE | EARLY / MID / LATE / RECESSION (dropdown) |
| EQUITY_TARGET_PCT | Target equity % (the "20" in 80/20) |
| FUND_TARGET_PCT | Target fund % (the "80" in 80/20) |

---

### Step 7: Set Up Automatic Price Refresh (Google Apps Script)

GOOGLEFINANCE formulas only refresh when the sheet is open in a browser. This Apps Script runs server-side — the Python job triggers it via HTTP before reading prices, so everything stays in one run.

1. Open your Google Sheet → **Extensions → Apps Script**
2. Delete the default code in the editor
3. Copy the entire contents of `scripts/google_apps_script.js` from this repo and paste it in
4. Click **Save** (disk icon)
5. Click **Deploy → New deployment**
6. Click the gear icon → select **Web app**
   - **Execute as**: Me
   - **Who has access**: Anyone
7. Click **Deploy** → **Authorize access** when prompted
8. Copy the **Web app URL** (looks like `https://script.google.com/macros/s/AKfyc.../exec`)
9. Add it as a GitHub secret: `APPS_SCRIPT_URL`

**Test it:** Open the Web app URL in your browser — you should see a JSON response like `{"status":"ok","updated":34,"failed":[],...}`. Check your Holdings tab — `current_price` should have fresh values.

**How it works:** Each Python run calls this URL first → Apps Script fetches GOOGLEFINANCE prices for every symbol → writes them as plain values to the sheet → Python reads the fresh prices. No stale data, no yfinance needed for prices.

---

### Step 8: Test Run

```bash
# Weekly digest in dry-run mode (prints message, doesn't send email)
DRY_RUN=true python scripts/run_weekly.py
```

You should see a formatted portfolio digest printed to the terminal.

---

### Step 9: Email Setup

Alerts are sent via Gmail SMTP. You need a **Gmail App Password** (not your regular password).

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security) — make sure **2-Step Verification** is ON
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select app: **Mail**, device: **Other** → name it `Portfolio Demon` → **Generate**
4. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

Update `.env`:

```
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
EMAIL_RECIPIENT=your-email@gmail.com
DRY_RUN=false
```

Test:

```bash
python scripts/run_weekly.py
```

You should receive the weekly digest email.

---

### Step 10: GitHub Actions

For automated scheduled runs without keeping your computer on.

1. Push the repository to GitHub
2. Go to **Settings → Secrets and variables → Actions → New repository secret**
3. Add these 5 secrets:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — the entire JSON key file content (paste all on one line)
   - `GOOGLE_SHEET_ID` — your sheet ID
   - `EMAIL_SENDER` — your Gmail address
   - `EMAIL_PASSWORD` — the 16-char App Password from Step 9
   - `EMAIL_RECIPIENT` — where to receive alerts
4. Go to the **Actions** tab → **Enable workflows**
5. Test: **Actions → Manual Portfolio Demon Run → Run workflow** → mode: `weekly`, dry_run: `true`

**Scheduled runs:**
- **Daily**: 9:00 AM ET weekdays (pre-market) — silent unless stop-loss or SPY correction
- **Weekly**: Sunday 8:00 PM ET — always sends full digest

---

## Day-to-Day Usage

### Recording a Trade

1. Open Google Sheet → **Trade_Entry** tab
2. Fill in a row:
   - **date**: pick from date picker
   - **symbol**: select from dropdown (pulls from Holdings)
   - **action**: BUY / SELL / TRIM
   - **shares**: number of shares
   - **price_per_share**: price you paid/received
   - **total_amount**: auto-calculated
   - **reason**: select from dropdown
3. Run:
   ```bash
   python scripts/process_trades.py
   ```
4. The script updates:
   - `deployed_amount` and `deployed_shares` in Holdings
   - `CASH_REMAINING` in Portfolio_Config (BUY decreases, SELL increases)
   - Logs the trade in the Transactions tab
   - Marks the Trade_Entry row as `processed`
   - All formula columns recalculate automatically

You can enter multiple trades at once — the script processes all `pending` rows.

### Changing Business Cycle Phase

Open the Google Sheet → **Portfolio_Config** tab → click the **CYCLE_PHASE** cell → select from dropdown: EARLY / MID / LATE / RECESSION

### Re-importing from Broker

Export a fresh CSV from your broker and re-run the seed script. This **replaces** all holdings — use it for a full refresh, not for incremental updates (use Trade_Entry for those).

### Running Locally

```bash
# Daily check (silent unless stop-loss or correction)
python scripts/run_daily.py

# Weekly digest (always sends full report)
python scripts/run_weekly.py

# Correction check only
python scripts/run_correction.py

# Manual with mode selection
RUN_MODE=weekly python scripts/run_manual.py

# Dry run
DRY_RUN=true python scripts/run_weekly.py
```

### Running Tests

```bash
pytest tests/ -v
```

---

## Architecture

```
scripts/            → Entrypoints and setup tools
  seed_sheet.py     → Import from broker CSV or create empty template
  process_trades.py → Process Trade_Entry tab → update Holdings + cash
  setup_formulas.py → Set computed-column formulas in Holdings
  setup_dropdowns.py→ Add dropdown validations across all tabs
  setup_dates_and_prices.py → Date pickers + GOOGLEFINANCE live prices
  run_daily.py      → Daily pre-market check
  run_weekly.py     → Weekly digest
  run_correction.py → SPY correction check
  run_manual.py     → Manual trigger with mode selection

src/sheets/         → Google Sheets auth, read, write
src/market/         → Yahoo Finance prices, indicators, market status
src/portfolio/      → Portfolio math (weights, P&L, headroom)
src/signals/        → Signal logic (macro rotation, rebalance, deployment, stop-loss)
src/alerts/         → Email sender, message formatting, dispatch logic
src/importers/      → Broker CSV parsers (Fidelity, Schwab, Vanguard, generic)
config/             → Settings (env vars) and constants (thresholds, categories)
```

## Signal Tiers

| Tier | Signal | Cadence | Alert |
|------|--------|---------|-------|
| 1 | Business cycle rotation | Weekly digest | Yellow |
| 2 | 80/20 band breach | Weekly digest | Yellow |
| 2 | Position overweight | Weekly digest | Yellow |
| 3 | Deployment opportunity (dip + headroom) | Weekly digest | Green |
| 3 | Stop-loss breach | Immediate | Red |
| 3 | Take-profit reached | Weekly digest | Yellow |
| — | S&P 500 correction >3% | Immediate | Red |

## Google Sheet Tabs

| Tab | Purpose |
|-----|---------|
| **Holdings** | All positions with live prices and computed metrics |
| **Portfolio_Config** | Key-value settings (total value, cash, cycle phase, thresholds) |
| **Trade_Entry** | Enter new trades here → run process_trades.py |
| **Transactions** | Append-only trade log (auto-populated by process_trades.py) |
| **Signal_Log** | One row per monitor run (auto-populated by Python) |
