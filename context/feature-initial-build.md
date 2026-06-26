# Feature: Initial Build — Portfolio Demon

## Progress Log

**2026-06-18 (session 1):**
Built the entire Portfolio Demon application from scratch in a single session. Started from an empty directory with only CLAUDE.md spec. Delivered: full Python monitoring system (config, sheets, market, portfolio, signals, alerts, utils — 7 src modules), 5 script entrypoints (daily, weekly, correction, manual, seed), 3 GitHub Actions workflows, 18 passing unit tests, broker CSV importers (Fidelity, Schwab, Vanguard, generic), Google Sheet setup pipeline (formulas, dropdowns, date pickers, GOOGLEFINANCE live prices), trade processing with automatic SPAXX/cash tracking, and a complete README with end-to-end setup guide. Successfully imported real Fidelity CSV export and ran a live weekly digest against real market data. Renamed project from "IRA Portfolio Monitor" to "Portfolio Demon". Created context directory for AI session continuity.

**2026-06-18 (session 2):**
Deployed to GitHub and switched notification channel from Telegram to email. Initialized git repo, created develop branch, pushed to `paulbishwajeet/portfolio-demon`, created and merged PR #1. Replaced `python-telegram-bot` with Python `smtplib` (Gmail SMTP + App Password). Rewrote digest format to match user's exact spec (monospace layout with portfolio health, deployment opportunities, rotation watch, speculative watchlist, correction threshold). Resolved multiple deployment issues: missing `EMAIL_RECIPIENT` secret, Gmail rejecting regular password (needed App Password), yfinance rate limiting on GitHub Actions shared IPs. Iteratively eliminated yfinance dependency — first batched downloads, then replaced entirely with a Google Apps Script web app that refreshes prices via GOOGLEFINANCE and computes 50d moving averages server-side. Added data quality warnings to the digest (shows when price refresh fails or specific symbols error). Final state: zero yfinance API calls, all market data from Google Apps Script, 19 tests passing, 7 PRs merged to main.

**2026-06-27 (session 3):**
Wire-up, data fixes, and daily alert redesign. (1) Integrated `process_trades.py` into the daily run — it now executes first, before price refresh, so Holdings reflects latest trades before signals are computed. Manually processed 23 pending trades ($160,376 deployed, SPAXX $807,963 → $647,588). Fixed `ValueError` from dollar-sign-prefixed values in deployed_amount cells. (2) Fixed two sheet data errors: XLU and JNJ `planned_pct` were 0.02 instead of 2.0 (data entry error cascaded into wrong `planned_amount`); `portfolio_weight_pct` formula for rows 12–17 used relative `Portfolio_Config!B2` reference that had drifted to B3–B8, causing KO (row 16) to divide by SP500_CORRECTION_THRESHOLD (3.0) instead of TOTAL_IRA_VALUE, producing 85,642% weight. Fixed to `$B$2` absolute reference. (3) Replaced all static current_price values with live `=IFERROR(GOOGLEFINANCE("TICKER","price"),GOOGLEFINANCE("MUTF:TICKER","price"))` formulas for all 34 symbols; updated Apps Script to set the formula rather than overwriting with setValue. (4) Redesigned daily alert: removed per-symbol stop-loss emails, replaced with a single always-send deployment watchlist email showing every underdeployed symbol with current price, previous close, and day-over-day % change. Apps Script now also fetches and returns `prev_prices` (closeyest) in its JSON response.

## Current State

**`develop` branch has 4 new commits (ab19a58 → 15e901c) not yet merged to `main`. The Apps Script in the Google Sheet must be redeployed before the daily email shows previous-close prices.**

- Repo: `develop` branch is ahead of `main` by 4 commits. Changes cover: process_trades integration, sheet data fixes, GOOGLEFINANCE live price formulas, and daily watchlist email redesign.
- Google Sheet `ira-deploymon-1mfidelity`: All 34 `current_price` cells now have live `GOOGLEFINANCE` formulas. Holdings reflect 23 processed trades. `planned_pct` for XLU and JNJ corrected to 2.0. `portfolio_weight_pct` formula fixed for rows 12–17 (absolute `$B$2` reference).
- Daily email: Now always sends a deployment watchlist (underdeployed symbols + current/prev price + day% change). Stop-loss individual emails removed from daily cadence; stop-loss section remains in weekly digest.
- Apps Script: Code updated in `scripts/google_apps_script.js` (added `getPrevClose()`, returns `prev_prices` in response, sets GOOGLEFINANCE formulas instead of static setValue) but **not yet redeployed**. Until redeployed, the daily watchlist email shows `n/a` for previous-close prices.

**Single next action:** Redeploy the Apps Script — open Google Sheet → Extensions → Apps Script → paste latest `scripts/google_apps_script.js` → Deploy → Manage deployments → edit → New version → Deploy. Then create a PR from `develop` to `main`.

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
- `src/alerts/formatter.py` — weekly digest (with data warnings), correction alert, stop-loss alert templates; added `format_daily_watchlist()` — table of underdeployed symbols with current price, prev close, day % change, deployed amount, headroom
- `src/alerts/dispatcher.py` — daily now always sends deployment watchlist (removed stop-loss loop); weekly always sends full digest; correction alert fires separately on SPY drop
- `src/sheets/price_refresh.py` — now stores `_prev_prices` dict and exposes `get_prev_price(symbol)`
- `src/alerts/email_sender.py` — Gmail SMTP sender with TLS, retry, and dry-run support

**Scripts:**
- `scripts/google_apps_script.js` — Apps Script web app: now sets GOOGLEFINANCE formulas (not static values) for current_price, fetches `prev_prices` (closeyest) for all symbols via scratch sheet, returns `prev_prices` + `moving_averages` + `spy_daily_change_pct`. Removed `getPrice()` helper. **Needs redeployment.**
- `scripts/seed_sheet.py` — broker CSV import or empty template creation
- `scripts/process_trades.py` — Trade_Entry → Holdings + SPAXX cash updates. Now accepts optional `sheet` param (avoids double connection when called from run_daily). Strips `$` from deployed_amount/deployed_shares before float conversion.
- `scripts/run_daily.py` — now calls `process_trades(sheet)` first (before price refresh), then signals; stop-loss signal collection removed from daily flow.
- `scripts/run_weekly.py`, `run_correction.py`, `run_manual.py` — entrypoints (unchanged)

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
11. **process_trades runs before price refresh** — Ensures Holdings deployed_amount/deployed_shares reflect latest trades before signals and P&L are computed. Order in run_daily: process_trades → price_refresh → read_holdings → compute.
12. **current_price uses permanent GOOGLEFINANCE formula** — Sheet cells stay live at all times. Apps Script no longer overwrites with static setValue; instead sets `=IFERROR(GOOGLEFINANCE("TICKER","price"),GOOGLEFINANCE("MUTF:TICKER","price"))` formula so mutual funds fall back automatically.
13. **Daily email always sends** — Changed from "silent unless stop-loss or correction" to always sending a deployment watchlist. Rationale: user wants to see price movement daily and decide on dip buying themselves. Stop-loss individual emails removed from daily; they appear in weekly digest only.
14. **prev_prices via Apps Script closeyest** — Apps Script fetches previous close for all symbols via scratch sheet and returns as `prev_prices` dict. Python uses this for day-over-day % change in the daily watchlist email.

## Open Questions

1. **Apps Script redeployment pending** — `scripts/google_apps_script.js` updated locally but not yet deployed to the live web app. Until redeployed: daily watchlist shows `n/a` for prev close prices; current_price cells may revert to static values on next Apps Script run. Also increases execution time: `getPrevClose()` adds ~200ms × 34 symbols ≈ 7s extra. Still within 6-min limit.
2. **develop not merged to main** — 4 commits on `develop` since last PR. Production workflows run from `main`, so current changes are not live yet.
3. **portfolio_weight_pct formula fragility** — Rows 12–17 had drifted relative references. Fixed with `$B$2` but only for those rows. If new rows are added to Holdings, the same drift could recur. Consider locking all portfolio_weight_pct formulas to `$B$2` via a sheet setup script.
4. **UMAC and XLV** — These two tickers occasionally fail GOOGLEFINANCE lookup. May need ticker format investigation (UMAC is very small-cap, XLV may need "NYSEARCA:XLV" format).
5. **yfinance cleanup** — `src/market/prices.py` and `src/market/indicators.py` are no longer called by the main flow. Dead code; could be removed.
6. **No integration tests** — all 19 tests use mock data. No tests that hit the real Google Sheet, Apps Script, or email.
7. **TOTAL_IRA_VALUE in Portfolio_Config** — should reflect current market value (~$1,019,214 based on sheet formulas) but may be stale if not manually updated after each run.
