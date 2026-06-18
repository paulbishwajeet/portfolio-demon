# Project Overview

**Name:** Portfolio Demon
**Stack:** Python 3.11+ (running 3.13.5 locally), Google Sheets API (gspread 6.1.4), Google Apps Script (GOOGLEFINANCE for prices + MAs), Gmail SMTP (email alerts), GitHub Actions (CI/CD scheduling)
**Package Manager:** pip — all dependencies pinned in `requirements.txt` (11 packages, no setup.py/pyproject.toml)
**Repo:** https://github.com/paulbishwajeet/portfolio-demon.git

**Key Directories:**

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `config/` | App configuration | `settings.py` (env var loading via python-dotenv), `constants.py` (thresholds, cycle rotation map, column schemas, category lists) |
| `src/sheets/` | Google Sheets I/O + price refresh | `client.py` (service account auth), `reader.py` (read Holdings/Config/Transactions), `writer.py` (write dip_score + last_updated, append Signal_Log), `price_refresh.py` (calls Apps Script web app, caches MAs + SPY change, tracks refresh status) |
| `src/market/` | Market data (LEGACY — no longer used in main flow) | `prices.py` (yfinance batch download), `indicators.py` (50d MA, dip score), `market_status.py` (trading day check) |
| `src/portfolio/` | Portfolio math | `calculator.py` (compute_holdings: sheet prices → P&L → dip scores from Apps Script MA; get_portfolio_breakdown), `analyzer.py` (80/20 band, overweight, speculative cap, pending actions) |
| `src/signals/` | Signal generation | `tier1_macro.py` (cycle rotation), `tier2_rebalance.py` (band breach, overweight, speculative cap), `tier3_speculative.py` (deployment, stop-loss, take-profit), `correction.py` (SPY >3% drop via Apps Script data) |
| `src/alerts/` | Email notifications | `email_sender.py` (Gmail SMTP with TLS + retry), `formatter.py` (weekly digest with data warnings, correction alert, stop-loss alert), `dispatcher.py` (daily vs weekly dispatch + data warning builder) |
| `src/importers/` | Broker CSV import | `base.py`, `fidelity.py`, `schwab.py`, `vanguard.py`, `generic.py` |
| `src/utils/` | Shared utilities | `logger.py`, `retry.py` (tenacity decorator), `date_utils.py` (US/Eastern timezone) |
| `scripts/` | Entrypoints + setup | `run_daily.py`, `run_weekly.py`, `run_correction.py`, `run_manual.py`; `google_apps_script.js` (web app for price refresh); `seed_sheet.py`, `process_trades.py`, `setup_formulas.py`, `setup_dropdowns.py`, `setup_dates_and_prices.py` |
| `tests/` | Test suite (19 tests) | `test_calculator.py` (4), `test_signals.py` (9), `test_formatter.py` (6), `fixtures/mock_portfolio.py` |
| `.github/workflows/` | Scheduled runs | `daily_monitor.yml`, `weekly_digest.yml`, `manual_trigger.yml` |
| `context/` | AI development context | `_active.md`, `_project.md`, `feature-initial-build.md` |

**Data Flow:**
1. Python calls Apps Script web app URL → GOOGLEFINANCE refreshes all prices, computes 50d MAs, gets SPY daily change
2. Python reads fresh prices from Google Sheet
3. Python computes portfolio math (P&L, weights, headroom, dip scores using MA data from step 1)
4. Signal engine runs (rotation, rebalance, deployment, stop-loss, take-profit, correction)
5. Email sent via Gmail SMTP (weekly: always, daily: only on stop-loss or SPY correction)

**Coding Conventions:**
- No `setup.py` — scripts use `sys.path.insert(0, ...)` to resolve imports
- Imports are absolute from project root: `from src.sheets.client import get_sheet`
- No comments unless the "why" is non-obvious
- Each signal tier wrapped in its own `try/except`
- Secrets exclusively via env vars (`.env` locally, GitHub Actions secrets in prod)
- Google Sheet is source of truth for portfolio state

**Testing:** pytest 8.3.4 — 19 tests using mock data. Run: `pytest tests/ -v`

**GitHub Secrets:**
- `GOOGLE_SERVICE_ACCOUNT_JSON` — service account JSON key (accepts raw JSON string or file path)
- `GOOGLE_SHEET_ID` — sheet ID from URL
- `EMAIL_SENDER` — Gmail address
- `EMAIL_PASSWORD` — Gmail App Password (16-char, not regular password)
- `EMAIL_RECIPIENT` — where to receive alerts
- `APPS_SCRIPT_URL` — Google Apps Script web app URL for price refresh
