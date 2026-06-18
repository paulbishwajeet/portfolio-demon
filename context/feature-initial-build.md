# Feature: Initial Build — Portfolio Demon

## Progress Log

**2026-06-18 (session 1):**
Built the entire Portfolio Demon application from scratch in a single session. Started from an empty directory with only CLAUDE.md spec. Delivered: full Python monitoring system (config, sheets, market, portfolio, signals, alerts, utils — 7 src modules), 5 script entrypoints (daily, weekly, correction, manual, seed), 3 GitHub Actions workflows, 18 passing unit tests, broker CSV importers (Fidelity, Schwab, Vanguard, generic), Google Sheet setup pipeline (formulas, dropdowns, date pickers, GOOGLEFINANCE live prices), trade processing with automatic SPAXX/cash tracking, and a complete README with end-to-end setup guide. Successfully imported real Fidelity CSV export and ran a live weekly digest against real market data. Renamed project from "IRA Portfolio Monitor" to "Portfolio Demon". Created context directory for AI session continuity.

**2026-06-18 (session 2):**
Deployed to GitHub and switched notification channel from Telegram to email. Initialized git repo, created develop branch, pushed to `paulbishwajeet/portfolio-demon`, created and merged PR #1. Replaced `python-telegram-bot` with Python `smtplib` (Gmail SMTP + App Password). Rewrote digest format to match user's exact spec (monospace layout with portfolio health, deployment opportunities, rotation watch, speculative watchlist, correction threshold). Resolved multiple deployment issues: missing `EMAIL_RECIPIENT` secret, Gmail rejecting regular password (needed App Password), yfinance rate limiting on GitHub Actions shared IPs. Iteratively eliminated yfinance dependency — first batched downloads, then replaced entirely with a Google Apps Script web app that refreshes prices via GOOGLEFINANCE and computes 50d moving averages server-side. Added data quality warnings to the digest (shows when price refresh fails or specific symbols error). Final state: zero yfinance API calls, all market data from Google Apps Script, 19 tests passing, 7 PRs merged to main.

## Current State

**The application is fully deployed on GitHub and sending email alerts. All market data comes from a Google Apps Script web app — zero yfinance dependency.**

- Repo: `https://github.com/paulbishwajeet/portfolio-demon.git` — `main` branch is production, `develop` is working branch. 7 PRs merged.
- GitHub Actions: 3 workflows configured (daily 9am ET weekdays, weekly Sunday 8pm ET, manual dispatch). All use `main` branch.
- GitHub Secrets configured: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID`, `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECIPIENT`, `APPS_SCRIPT_URL`.
- Google Sheet: `ira-deploymon-1mfidelity` with 34 holdings, live GOOGLEFINANCE prices via Apps Script web app.
- Apps Script: Deployed as web app. Returns current prices, 50d moving averages, and SPY daily change in one JSON response. Python calls it via HTTP at the start of every run.
- Email: Working end-to-end via Gmail SMTP with App Password. Weekly digest and stop-loss alerts confirmed received.
- Tests: 19 passing (4 calculator, 6 formatter, 9 signals).
- The user has already received successful digest and stop-loss emails.

**Single next action:** The user needs to update the Apps Script code in their Google Sheet (Extensions → Apps Script → paste latest `scripts/google_apps_script.js` → Deploy → Manage deployments → edit → New version → Deploy). The latest version computes 50d MAs and SPY daily change server-side, eliminating yfinance entirely. Without this update, the deployed web app only returns prices (not MAs), so dip scores will all be 0.

## Key Files

**Config:**
- `config/settings.py` — env var loading (Google, Email, APPS_SCRIPT_URL, DRY_RUN, RUN_MODE)
- `config/constants.py` — cycle rotation map, category lists, column schemas, default config values, thresholds

**Core modules:**
- `src/sheets/client.py` — Google Sheets service account auth
- `src/sheets/reader.py` — reads Holdings, Portfolio_Config, Transactions tabs
- `src/sheets/writer.py` — writes dip_score + last_updated to Holdings, appends Signal_Log
- `src/sheets/price_refresh.py` — calls Apps Script web app, caches MAs and SPY change, tracks refresh status for data quality warnings
- `src/market/prices.py` — yfinance batch download (LEGACY, no longer called by main flow)
- `src/market/indicators.py` — 50d MA and dip score calculation (LEGACY, no longer called)
- `src/portfolio/calculator.py` — compute_holdings (sheet prices → P&L → dip scores from Apps Script MA), get_portfolio_breakdown
- `src/portfolio/analyzer.py` — 80/20 band, overweight, speculative cap, pending actions
- `src/signals/tier1_macro.py` — business cycle rotation signals
- `src/signals/tier2_rebalance.py` — band breach, overweight, speculative cap signals
- `src/signals/tier3_speculative.py` — deployment opportunities, stop-loss, take-profit signals
- `src/signals/correction.py` — SPY >3% single-day drop detection (reads from price_refresh cache)
- `src/alerts/formatter.py` — weekly digest (with data warnings), correction alert, stop-loss alert templates
- `src/alerts/dispatcher.py` — daily (silent unless emergency) vs weekly (always send) logic, builds data warnings from refresh status
- `src/alerts/email_sender.py` — Gmail SMTP sender with TLS, retry, and dry-run support

**Scripts:**
- `scripts/google_apps_script.js` — Google Apps Script web app: refreshes prices via GOOGLEFINANCE, computes 50d MAs, returns SPY daily change. Must be pasted into the Google Sheet's Apps Script editor and deployed as a web app.
- `scripts/seed_sheet.py` — broker CSV import or empty template creation
- `scripts/process_trades.py` — Trade_Entry → Holdings + cash updates
- `scripts/run_daily.py`, `run_weekly.py`, `run_correction.py`, `run_manual.py` — entrypoints (all call `trigger_price_refresh()` first)

**Workflows:**
- `.github/workflows/daily_monitor.yml` — weekdays 14:00 UTC (9am ET)
- `.github/workflows/weekly_digest.yml` — Monday 01:00 UTC (Sunday 8pm ET)
- `.github/workflows/manual_trigger.yml` — on-demand with mode + dry_run inputs

**Tests:**
- `tests/test_calculator.py` — portfolio breakdown, zero-total edge case, health analysis (4 tests)
- `tests/test_signals.py` — rotation, rebalance, deployment, stop-loss, take-profit, priority sorting (9 tests)
- `tests/test_formatter.py` — weekly digest, correction, stop-loss, data warnings (6 tests)
- `tests/fixtures/mock_portfolio.py` — 5 mock holdings

## Decisions Made

1. **GOOGLEFINANCE for live prices, not yfinance** — sheet prices update automatically without Python; yfinance was originally fallback only for dip score historical data. Avoids rate limiting issues observed during testing.
2. **Sheet formulas for computed columns** — P&L, weights, headroom, avg_cost_per_share are all Google Sheets formulas. Python `writer.py` only writes `dip_score` and `last_updated`.
3. **SPAXX = CASH_REMAINING** — SPAXX money market balance tracked as `CASH_REMAINING` in Portfolio_Config.
4. **Broker CSV import replaces hardcoded seed data** — `seed_sheet.py` imports from broker CSV export.
5. **Telegram replaced with email** — User couldn't get Telegram working. Switched to Gmail SMTP with App Password. `python-telegram-bot` removed from requirements.
6. **Google Apps Script as web app** — Deployed as web app callable via HTTP. Python triggers it at the start of each run to refresh prices, compute 50d MAs, and get SPY daily change. Eliminates yfinance entirely.
7. **Inline price refresh** — No separate timer/trigger needed. The Python job calls the Apps Script URL, waits for the response (up to 300s), then reads fresh data from the sheet.
8. **Data quality warnings in digest** — When price refresh fails (partially or fully), the digest shows a 🔶 DATA QUALITY WARNINGS section at the top and the email subject gets a ⚠️ prefix.
9. **Batch size and delays for yfinance** — Before eliminating yfinance: batches of 5 with 12s delays and 20s backoff on rate limit. Now moot since Apps Script handles everything.
10. **Apps Script scratch sheet** — Uses a hidden `_scratch` tab to evaluate GOOGLEFINANCE formulas server-side, reads the result, then clears the cell.

## Open Questions

1. **Apps Script redeployment** — User needs to update the Apps Script code to the latest version that includes 50d MA and SPY change computation. Current deployed version may only return prices. Without the update, dip scores will be 0 in the digest.
2. **UMAC and XLV** — These two tickers occasionally fail GOOGLEFINANCE lookup. May need ticker format investigation (UMAC is very small-cap, XLV may need "NYSEARCA:XLV" format).
3. **Apps Script execution time** — With 34 symbols, the refresh takes ~60-75s (1.5s per symbol for price + 1.3s per symbol for MA). Google Apps Script has a 6-minute execution limit. Current 34 symbols are well within limit but adding many more could approach it.
4. **yfinance cleanup** — `src/market/prices.py` and `src/market/indicators.py` are no longer called by the main flow. Could be removed entirely or kept as fallback. Currently dead code.
5. **No integration tests** — all 19 tests use mock data. No tests that hit the real Google Sheet, Apps Script, or email.
6. **TOTAL_IRA_VALUE accuracy** — set from CSV import cost basis. User may want to update to reflect actual market value.
