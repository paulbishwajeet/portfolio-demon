# IRA Portfolio Monitor — Claude Code Build Specification
# CLAUDE.md

## READ THIS FIRST

This document is the complete specification for an **IRA Portfolio Monitor** application.
Build every component described here. Do not skip sections. Do not simplify the schema.
When in doubt, build it — this is a long-term project and the foundation must be solid.

---

## 1. PROJECT OVERVIEW & PHILOSOPHY

### What this is
A Python-based portfolio monitoring system for a **Traditional IRA account** held at
Fidelity Investments. The account holder is 50 years old, targeting retirement at 65,
with $1,000,000 rolled over from a 401k. The system monitors ~33 holdings, tracks
deployment of remaining cash, and sends strategic alerts via Telegram.

### What this is NOT
- Not a trading bot — it never places orders
- Not a day-trading signal engine — it ignores small daily fluctuations
- Not a panic machine — it uses wide thresholds appropriate for a 15-year horizon
- Not a replacement for human judgment — every alert ends with information, not commands

### Core philosophy
This is a **long-term retirement account**. The monitor must reflect that:
- Signal thresholds are deliberately wide (7-10% corrections, not 1-2%)
- Primary alert cadence is **weekly** (Sunday 8pm ET), not daily
- One exception: **immediate alert** if S&P 500 drops >3% in a single trading day
- Sell signals are rare and only for significant events (stop-loss breach, major
  overweight, sector rotation driven by business cycle phase change)
- The 80/20 (funds/equity) balance is the single most important portfolio metric

### Portfolio target balance
- **80% Core Funds** (index funds, bond funds, TIPS)
- **20% Equity** (quality stocks + speculative positions)
- Tolerance band: ±5% (alert if outside 75/25 or 85/15)
- Speculative positions capped at 8% of total portfolio combined

---

## 2. TECHNOLOGY STACK

### Language & runtime
- Python 3.11+
- All dependencies pinned in `requirements.txt`

### Data source
- **Google Sheets** — single source of truth for portfolio state
  - Library: `gspread` with service account authentication
  - Sheet is manually updated by the user after each trade
- **Yahoo Finance** — live price data, historical data, moving averages
  - Library: `yfinance` (free, no API key required)
  - Fallback: `requests` to Yahoo Finance JSON endpoint if yfinance fails

### Notifications
- **Telegram Bot API** — primary notification channel
  - Library: `python-telegram-bot` (async)
  - Format: Markdown messages with emoji, sections, and tables
  - One bot, one chat ID (personal account)

### Scheduling & CI/CD
- **GitHub Actions** — runs the monitor on schedule and on demand
  - Schedule: Every trading day at 9:00 AM ET (14:00 UTC) — pre-market overview
  - Schedule: Every Sunday at 8:00 PM ET (01:00 UTC Monday) — weekly digest
  - On demand: Manual workflow dispatch with optional `mode` input
  - Secrets stored in GitHub repository secrets (never in code)

### Secret management
- All secrets in environment variables only
- Local development: `.env` file (gitignored)
- Production: GitHub Actions secrets
- Never hardcode any token, key, or credential

---

## 3. REPOSITORY STRUCTURE

Build exactly this structure:

```
ira-monitor/
├── CLAUDE.md                    # This file
├── README.md                    # Setup guide (generate from this spec)
├── requirements.txt             # All dependencies pinned
├── .env.example                 # Template for local secrets (no real values)
├── .gitignore                   # Includes .env, *.pyc, __pycache__, etc.
│
├── .github/
│   └── workflows/
│       ├── daily_monitor.yml    # Runs at 9am ET weekdays
│       ├── weekly_digest.yml    # Runs Sunday 8pm ET
│       └── manual_trigger.yml   # On-demand with mode selector
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # All configuration, reads from env vars
│   └── constants.py             # Thresholds, tickers, cycle phases etc.
│
├── src/
│   ├── __init__.py
│   ├── sheets/
│   │   ├── __init__.py
│   │   ├── client.py            # Google Sheets auth and connection
│   │   ├── reader.py            # Read portfolio state from sheet
│   │   └── writer.py            # Write back computed fields (optional)
│   │
│   ├── market/
│   │   ├── __init__.py
│   │   ├── prices.py            # Fetch live + historical prices via yfinance
│   │   ├── indicators.py        # Moving averages, % from MA, 52w high/low
│   │   └── market_status.py     # Is market open? Is today a trading day?
│   │
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── tier1_macro.py       # Business cycle + sector rotation signals
│   │   ├── tier2_rebalance.py   # 80/20 drift, portfolio band breach
│   │   ├── tier3_speculative.py # Deployment opportunities, stop-loss
│   │   └── correction.py        # S&P 500 single-day drop >3% alert
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── calculator.py        # Portfolio weights, P&L, headroom math
│   │   └── analyzer.py          # Aggregate portfolio health metrics
│   │
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py      # Telegram API wrapper
│   │   ├── formatter.py         # Build formatted Telegram message strings
│   │   └── dispatcher.py        # Decide what to send and when
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Structured logging
│       ├── retry.py             # Retry decorator for API calls
│       └── date_utils.py        # Trading day helpers, ET timezone
│
├── scripts/
│   ├── run_daily.py             # Entrypoint: daily pre-market check
│   ├── run_weekly.py            # Entrypoint: weekly digest
│   ├── run_correction.py        # Entrypoint: correction check (runs intraday)
│   ├── run_manual.py            # Entrypoint: manual trigger with mode arg
│   └── seed_sheet.py            # One-time: seed Google Sheet with portfolio data
│
└── tests/
    ├── __init__.py
    ├── test_calculator.py
    ├── test_signals.py
    ├── test_formatter.py
    └── fixtures/
        └── mock_portfolio.py    # Test data matching real portfolio structure
```

---

## 4. GOOGLE SHEETS SCHEMA

### Workbook name
`IRA Portfolio Monitor`

### Tab 1: `Holdings`
Primary tab. User manually updates `deployed_amount` and `deployed_shares`
after each trade. All other calculated fields are computed by Python.

**Columns (exact names, case-sensitive):**

| Column | Field Name            | Type   | Description                                              |
|--------|-----------------------|--------|----------------------------------------------------------|
| A      | symbol                | string | Ticker symbol e.g. FXAIX                                |
| B      | company_name          | string | Full company/fund name                                   |
| C      | sector_theme          | string | Sector / investment theme                                |
| D      | category              | string | core_fund / quality_stock / speculative /                |
|        |                       |        | new_defensive / existing_addition / trim_exit            |
| E      | planned_pct           | float  | Target allocation % of $1M (e.g. 30.0 for 30%)          |
| F      | planned_amount        | float  | planned_pct / 100 * 1000000                              |
| G      | deployed_amount       | float  | USER INPUT — total $ deployed so far                     |
| H      | deployed_shares       | float  | USER INPUT — total shares held                           |
| I      | avg_cost_per_share    | float  | deployed_amount / deployed_shares (computed)             |
| J      | stop_loss_pct         | float  | Stop loss % below cost basis (e.g. 35 = -35%)           |
| K      | take_profit_pct       | float  | Take profit % above cost basis (e.g. 75 = +75%)         |
| L      | max_portfolio_pct     | float  | Hard cap % of total portfolio (overweight alert)         |
| M      | status                | string | active / watch / trim / exit / new                       |
| N      | cycle_alignment       | string | positive / negative / neutral                            |
| O      | notes                 | string | Free text investment thesis notes                        |
| P      | current_price         | float  | COMPUTED — live price from yfinance                      |
| Q      | current_value         | float  | COMPUTED — current_price * deployed_shares               |
| R      | pl_dollar             | float  | COMPUTED — current_value - deployed_amount               |
| S      | pl_pct                | float  | COMPUTED — pl_dollar / deployed_amount * 100             |
| T      | portfolio_weight_pct  | float  | COMPUTED — current_value / total_portfolio * 100         |
| U      | headroom_amount       | float  | COMPUTED — planned_amount - deployed_amount              |
| V      | headroom_pct          | float  | COMPUTED — headroom_amount / planned_amount * 100        |
| W      | vs_plan_pct           | float  | COMPUTED — portfolio_weight_pct - planned_pct (drift)    |
| X      | dip_score             | float  | COMPUTED — % below 50-day MA (negative = below)          |
| Y      | last_updated          | string | COMPUTED — ISO timestamp of last Python update           |

---

### Tab 2: `Portfolio_Config`
Key-value configuration. User edits values in column B. Python reads column A for
key names and column B for values.

| Key                          | Default Value  | Description                                    |
|------------------------------|---------------|------------------------------------------------|
| TOTAL_IRA_VALUE              | 1023521.66    | Current total IRA value including cash         |
| CASH_REMAINING               | 833637.12     | Uninvested cash in SPAXX money market          |
| EQUITY_TARGET_PCT            | 20.0          | Target equity % (the "20" in 80/20)            |
| FUND_TARGET_PCT              | 80.0          | Target fund % (the "80" in 80/20)              |
| BAND_TOLERANCE_PCT           | 5.0           | Alert if drift exceeds this %                  |
| CYCLE_PHASE                  | LATE          | EARLY / MID / LATE / RECESSION (user-set)      |
| SP500_CORRECTION_THRESHOLD   | 3.0           | Immediate alert if S&P drops this % in one day |
| DIP_SIGNAL_THRESHOLD_PCT     | 7.0           | Min % below 50d MA to flag as opportunity      |
| STOP_LOSS_DEFAULT_PCT        | 35.0          | Default stop loss if not set per-symbol        |
| TAKE_PROFIT_DEFAULT_PCT      | 75.0          | Default take profit if not set per-symbol      |
| ALERT_MIN_HEADROOM           | 2000.0        | Min $ headroom to include in deployment alerts |
| OWNER_NAME                   | Portfolio Owner| Used in Telegram message header               |

---

### Tab 3: `Transactions`
Append-only trade log. User fills this manually after each trade.

| Column | Field Name           | Description                                          |
|--------|---------------------|------------------------------------------------------|
| A      | date                | Trade date YYYY-MM-DD                                |
| B      | symbol              | Ticker                                               |
| C      | action              | BUY / SELL / TRIM                                    |
| D      | shares              | Number of shares traded                              |
| E      | price_per_share     | Execution price                                      |
| F      | total_amount        | shares * price_per_share                             |
| G      | reason              | dip buy / rebalance / rotation / stop-loss / other  |
| H      | cycle_phase_at_trade| Cycle phase when trade was made                     |

---

### Tab 4: `Signal_Log`
Python appends one row per run. Never manually edited.

| Column | Field Name          | Description                                          |
|--------|--------------------|----------------------------------------------------|
| A      | run_timestamp       | ISO timestamp                                       |
| B      | run_type            | daily / weekly / correction / manual                |
| C      | signals_fired       | JSON string of all signals that fired               |
| D      | telegram_sent       | true / false                                        |
| E      | sp500_change_pct    | S&P 500 daily change % at time of run               |
| F      | portfolio_equity_pct| Equity % of total portfolio at run time             |
| G      | portfolio_fund_pct  | Fund % of total portfolio at run time               |
| H      | notes               | Errors or notable conditions                        |

---

## 5. SEED DATA — COMPLETE PORTFOLIO

Use this data to seed the Holdings tab via `scripts/seed_sheet.py`.

### Account snapshot as of Jun 12, 2026
- Total Account Value: $1,023,521.66
- Cash (SPAXX): $833,637.12
- Total Invested (cost basis): $185,576.92
- Total Current Value (equities): $189,884.54
- Overall P&L: +$4,307.62 (+2.32%)

### HOLDINGS_SEED — paste this into `scripts/seed_sheet.py`

```python
HOLDINGS_SEED = [
    # ── CORE FUNDS ──────────────────────────────────────────────────────────
    {
        "symbol": "FXAIX", "company_name": "Fidelity 500 Index Fund",
        "sector_theme": "Core Fund — US Large Cap", "category": "core_fund",
        "planned_pct": 30.0, "planned_amount": 300000.0,
        "deployed_amount": 35130.62, "deployed_shares": 136.472,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 35.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "Bedrock S&P 500 holding. Largest single allocation. Never exit — rebalance only.",
    },
    {
        "symbol": "FSPSX", "company_name": "Fidelity International Index Fund",
        "sector_theme": "Core Fund — International Developed", "category": "core_fund",
        "planned_pct": 12.0, "planned_amount": 120000.0,
        "deployed_amount": 21618.53, "deployed_shares": 326.416,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 15.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "International diversification. Developed markets Europe/Japan.",
    },
    {
        "symbol": "FDGFX", "company_name": "Fidelity Dividend Growth Fund",
        "sector_theme": "Core Fund — Dividend Growth", "category": "core_fund",
        "planned_pct": 13.0, "planned_amount": 130000.0,
        "deployed_amount": 16448.66, "deployed_shares": 339.008,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 16.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "Quality tilt via dividend growers. Less volatile than pure growth.",
    },
    {
        "symbol": "FXNAX", "company_name": "Fidelity US Bond Index Fund",
        "sector_theme": "Core Fund — US Bonds", "category": "core_fund",
        "planned_pct": 18.0, "planned_amount": 180000.0,
        "deployed_amount": 21191.26, "deployed_shares": 2027.872,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 22.0,
        "status": "active", "cycle_alignment": "positive",
        "notes": "Primary stability anchor. INCREASE in late cycle. Severely underweight.",
    },
    {
        "symbol": "FIPDX", "company_name": "Fidelity Inflation-Protected Bond Index",
        "sector_theme": "Core Fund — TIPS / Inflation", "category": "core_fund",
        "planned_pct": 5.0, "planned_amount": 50000.0,
        "deployed_amount": 5891.58, "deployed_shares": 637.617,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 8.0,
        "status": "active", "cycle_alignment": "positive",
        "notes": "Inflation hedge. Critical in late cycle. Only 0.58% of IRA — underweight.",
    },
    {
        "symbol": "FZILX", "company_name": "Fidelity Zero International Index",
        "sector_theme": "Core Fund — Intl Zero Fee", "category": "core_fund",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 9118.91, "deployed_shares": 544.088,
        "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_portfolio_pct": 5.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "Zero expense ratio intl index. Good FSPSX complement. Hold.",
    },
    # ── QUALITY STOCKS ───────────────────────────────────────────────────────
    {
        "symbol": "COHR", "company_name": "Coherent Corp",
        "sector_theme": "Quality Stock — AI Photonics", "category": "quality_stock",
        "planned_pct": 5.0, "planned_amount": 50000.0,
        "deployed_amount": 3115.88, "deployed_shares": 8.570,
        "stop_loss_pct": 35.0, "take_profit_pct": 100.0, "max_portfolio_pct": 8.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "AI datacenter optical components. Real revenue $1.69B/qtr. Secular AI theme.",
    },
    {
        "symbol": "CRDO", "company_name": "Credo Technology Group",
        "sector_theme": "Quality Stock — AI Networking Chips", "category": "quality_stock",
        "planned_pct": 4.0, "planned_amount": 40000.0,
        "deployed_amount": 3750.32, "deployed_shares": 14.165,
        "stop_loss_pct": 35.0, "take_profit_pct": 100.0, "max_portfolio_pct": 6.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "Best performer +59%. AI high-speed connectivity chips. Secular AI theme.",
    },
    {
        "symbol": "RKLB", "company_name": "Rocket Lab USA",
        "sector_theme": "Quality Stock — Space Launch", "category": "quality_stock",
        "planned_pct": 3.0, "planned_amount": 30000.0,
        "deployed_amount": 7346.03, "deployed_shares": 64.001,
        "stop_loss_pct": 35.0, "take_profit_pct": 75.0, "max_portfolio_pct": 5.0,
        "status": "active", "cycle_alignment": "negative",
        "notes": "Space launch leader. Real launches and government contracts.",
    },
    {
        "symbol": "IBM", "company_name": "International Business Machines",
        "sector_theme": "Quality Stock — AI / Hybrid Cloud", "category": "quality_stock",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 13742.50, "deployed_shares": 50.0,
        "stop_loss_pct": 25.0, "take_profit_pct": 50.0, "max_portfolio_pct": 4.0,
        "status": "active", "cycle_alignment": "neutral",
        "notes": "Profitable AI/quantum hybrid. 28 consecutive years dividend increases.",
    },
    # ── NEW DEFENSIVE ADDITIONS ──────────────────────────────────────────────
    {
        "symbol": "XLP", "company_name": "Consumer Staples Select SPDR ETF",
        "sector_theme": "NEW Defensive — Consumer Staples ETF", "category": "new_defensive",
        "planned_pct": 3.0, "planned_amount": 30000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 0.0, "max_portfolio_pct": 5.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "MISSING SECTOR. Outperforms in late cycle AND recession. Initiate.",
    },
    {
        "symbol": "XLV", "company_name": "Health Care Select SPDR ETF",
        "sector_theme": "NEW Defensive — Health Care ETF", "category": "new_defensive",
        "planned_pct": 3.0, "planned_amount": 30000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 0.0, "max_portfolio_pct": 5.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "MISSING SECTOR. Defensive. Outperforms in recession per Fidelity data.",
    },
    {
        "symbol": "XLU", "company_name": "Utilities Select SPDR ETF",
        "sector_theme": "NEW Defensive — Utilities ETF", "category": "new_defensive",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 0.0, "max_portfolio_pct": 4.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "MISSING SECTOR. High yield defensive. Late cycle winner. AI power demand.",
    },
    {
        "symbol": "JNJ", "company_name": "Johnson & Johnson",
        "sector_theme": "NEW Defensive — Health Care Stock", "category": "new_defensive",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 50.0, "max_portfolio_pct": 4.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "AAA-rated. 62 consecutive dividend increases. Recession-proof.",
    },
    {
        "symbol": "NEE", "company_name": "NextEra Energy",
        "sector_theme": "NEW Defensive — Utilities / Clean Energy", "category": "new_defensive",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 50.0, "max_portfolio_pct": 4.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "Largest US utility. Renewable energy leader. 29 years dividend growth.",
    },
    {
        "symbol": "KO", "company_name": "Coca-Cola Co",
        "sector_theme": "NEW Defensive — Consumer Staples Stock", "category": "new_defensive",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 0.0, "deployed_shares": 0.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 50.0, "max_portfolio_pct": 4.0,
        "status": "new", "cycle_alignment": "positive",
        "notes": "Recession-proof brand. Buffett's core holding. 62 years dividend increases.",
    },
    # ── SPECULATIVE ──────────────────────────────────────────────────────────
    {
        "symbol": "IONQ", "company_name": "IonQ Inc",
        "sector_theme": "Speculative — Quantum Computing", "category": "speculative",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 4032.62, "deployed_shares": 69.54,
        "stop_loss_pct": 40.0, "take_profit_pct": 100.0, "max_portfolio_pct": 3.0,
        "status": "active", "cycle_alignment": "negative",
        "notes": "Quantum computing leader. 10-20 year secular theme. Keep at 2% max.",
    },
    {
        "symbol": "QBTS", "company_name": "D-Wave Quantum Inc",
        "sector_theme": "Speculative — Quantum Computing", "category": "speculative",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 6300.84, "deployed_shares": 264.519,
        "stop_loss_pct": 40.0, "take_profit_pct": 100.0, "max_portfolio_pct": 3.0,
        "status": "active", "cycle_alignment": "negative",
        "notes": "Quantum annealing. Commercial use cases in optimization. Keep small.",
    },
    {
        "symbol": "SMR", "company_name": "NuScale Power Corp",
        "sector_theme": "Speculative — Nuclear SMR", "category": "speculative",
        "planned_pct": 2.0, "planned_amount": 20000.0,
        "deployed_amount": 2659.24, "deployed_shares": 277.873,
        "stop_loss_pct": 40.0, "take_profit_pct": 100.0, "max_portfolio_pct": 3.0,
        "status": "watch", "cycle_alignment": "positive",
        "notes": "Nuclear SMR for AI data center power. Energy sector late-cycle positive.",
    },
    {
        "symbol": "ONDS", "company_name": "Ondas Holdings",
        "sector_theme": "Speculative — Drone / Rail Tech", "category": "speculative",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 1080.88, "deployed_shares": 109.958,
        "stop_loss_pct": 30.0, "take_profit_pct": 50.0, "max_portfolio_pct": 1.0,
        "status": "trim", "cycle_alignment": "negative",
        "notes": "Micro-cap. EXIT recommended. Wrong phase, minimal revenue.",
    },
    # ── EXISTING ADDITIONS ───────────────────────────────────────────────────
    {
        "symbol": "ARKQ", "company_name": "ARK Autonomous Tech ETF",
        "sector_theme": "AI / Robotics ETF", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 6512.00, "deployed_shares": 50.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 30.0, "max_portfolio_pct": 1.5,
        "status": "trim", "cycle_alignment": "negative",
        "notes": "High-beta tech ETF. Trim on rallies. Wrong cycle phase.",
    },
    {
        "symbol": "BOTZ", "company_name": "Global X Robotics & AI ETF",
        "sector_theme": "Robotics / AI ETF", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 3726.00, "deployed_shares": 100.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 30.0, "max_portfolio_pct": 1.0,
        "status": "watch", "cycle_alignment": "negative",
        "notes": "Robotics ETF. Hold at current level. No new additions.",
    },
    {
        "symbol": "HUMN", "company_name": "Roundhill Human Robot ETF",
        "sector_theme": "Robotics ETF", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 3490.00, "deployed_shares": 100.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 50.0, "max_portfolio_pct": 1.0,
        "status": "watch", "cycle_alignment": "negative",
        "notes": "Humanoid robotics theme. Small position — hold, do not add.",
    },
    {
        "symbol": "KOID", "company_name": "KraneShares Humanoid AI ETF",
        "sector_theme": "Humanoid AI ETF", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 4102.00, "deployed_shares": 100.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 50.0, "max_portfolio_pct": 1.0,
        "status": "watch", "cycle_alignment": "negative",
        "notes": "Physical AI index ETF. Consider consolidating with HUMN.",
    },
    {
        "symbol": "NASA", "company_name": "Tema Space Innovation ETF",
        "sector_theme": "Space ETF", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 3524.00, "deployed_shares": 100.0,
        "stop_loss_pct": 25.0, "take_profit_pct": 40.0, "max_portfolio_pct": 1.0,
        "status": "watch", "cycle_alignment": "negative",
        "notes": "Space ETF. Diversified space exposure. Hold at current level.",
    },
    {
        "symbol": "RDW", "company_name": "Redwire Corporation",
        "sector_theme": "Space Infrastructure", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 1709.00, "deployed_shares": 100.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 30.0, "max_portfolio_pct": 0.5,
        "status": "trim", "cycle_alignment": "negative",
        "notes": "Up +23%. TRIM to lock gains. Space infrastructure play.",
    },
    {
        "symbol": "BE", "company_name": "Bloom Energy Corp",
        "sector_theme": "Clean Energy / Utilities", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 2488.80, "deployed_shares": 10.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 50.0, "max_portfolio_pct": 1.0,
        "status": "watch", "cycle_alignment": "positive",
        "notes": "Hydrogen fuel cells. Energy sector late-cycle positive. Hold.",
    },
    {
        "symbol": "GSAT", "company_name": "Globalstar Inc",
        "sector_theme": "Satellite Communications", "category": "existing_addition",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 1378.87, "deployed_shares": 17.0,
        "stop_loss_pct": 30.0, "take_profit_pct": 50.0, "max_portfolio_pct": 0.5,
        "status": "watch", "cycle_alignment": "neutral",
        "notes": "Apple iPhone satellite partnership. Small position. Hold.",
    },
    # ── EXIT / TRIM ──────────────────────────────────────────────────────────
    {
        "symbol": "PL", "company_name": "Planet Labs PBC",
        "sector_theme": "Satellite Imaging", "category": "trim_exit",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 3417.00, "deployed_shares": 100.0,
        "stop_loss_pct": 25.0, "take_profit_pct": 0.0, "max_portfolio_pct": 0.5,
        "status": "exit", "cycle_alignment": "negative",
        "notes": "DOWN -20%. EXIT. Wrong cycle phase. Weak fundamentals.",
    },
    {
        "symbol": "SATL", "company_name": "Satellogic Inc",
        "sector_theme": "Satellite / Spec", "category": "trim_exit",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 752.00, "deployed_shares": 100.0,
        "stop_loss_pct": 25.0, "take_profit_pct": 0.0, "max_portfolio_pct": 0.3,
        "status": "exit", "cycle_alignment": "negative",
        "notes": "DOWN -23%. EXIT. Micro-cap, high risk, wrong phase.",
    },
    {
        "symbol": "LUNR", "company_name": "Intuitive Machines",
        "sector_theme": "Space / Lunar", "category": "trim_exit",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 1532.00, "deployed_shares": 50.0,
        "stop_loss_pct": 25.0, "take_profit_pct": 0.0, "max_portfolio_pct": 0.5,
        "status": "trim", "cycle_alignment": "negative",
        "notes": "DOWN -14%. TRIM to 50% or EXIT. Wrong phase.",
    },
    {
        "symbol": "UMAC", "company_name": "Unusual Machines",
        "sector_theme": "Drone Delivery", "category": "trim_exit",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 2572.00, "deployed_shares": 100.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 0.0, "max_portfolio_pct": 0.3,
        "status": "exit", "cycle_alignment": "negative",
        "notes": "DOWN -12%. TRIM or EXIT. No moat, wrong phase.",
    },
    {
        "symbol": "BOT", "company_name": "RoboStrategy Inc",
        "sector_theme": "Robotics / Spec", "category": "trim_exit",
        "planned_pct": 0.0, "planned_amount": 0.0,
        "deployed_amount": 3253.00, "deployed_shares": 100.0,
        "stop_loss_pct": 20.0, "take_profit_pct": 0.0, "max_portfolio_pct": 0.3,
        "status": "exit", "cycle_alignment": "negative",
        "notes": "DOWN -7%. EXIT. No clear thesis.",
    },
]
```

---

## 6. SIGNAL LOGIC — COMPLETE SPECIFICATION

### Tier 1: Macro / Business Cycle Signals
Cadence: Checked every run. Fires in weekly digest.
Data source: CYCLE_PHASE from Portfolio_Config (user-set manually).

```python
# Sector rotation logic by cycle phase
CYCLE_ROTATION = {
    "EARLY": {
        "favor":  ["core_fund", "quality_stock"],
        "reduce": ["trim_exit"],
        "message": "Early cycle: favor growth and rate-sensitive sectors",
    },
    "MID": {
        "favor":  ["core_fund", "quality_stock"],
        "reduce": ["trim_exit"],
        "message": "Mid cycle: broad growth, reduce laggards",
    },
    "LATE": {
        "favor":  ["core_fund", "new_defensive"],
        "reduce": ["existing_addition", "trim_exit"],
        "message": "Late cycle: shift to defensive. Energy, staples, healthcare favored.",
    },
    "RECESSION": {
        "favor":  ["core_fund", "new_defensive"],
        "reduce": ["existing_addition", "trim_exit", "speculative"],
        "message": "Recession: maximum defensive positioning. Staples, utilities, healthcare.",
    },
}

# Rotation alert fires when:
# - Holdings in "reduce" categories exceed 5% of total portfolio value
# - AND cycle_phase is LATE or RECESSION
# Message lists: which categories to reduce, which to increase, specific symbols
```

### Tier 2: Portfolio Rebalance / 80/20 Band Breach
Cadence: Every run.

```python
# Category groupings for 80/20 calculation
FUND_CATEGORIES = ["core_fund"]
EQUITY_CATEGORIES = [
    "quality_stock", "speculative", "new_defensive",
    "existing_addition", "trim_exit"
]

total_portfolio = sum(current_values) + cash_remaining
equity_value = sum(current_value for cat in EQUITY_CATEGORIES)
fund_value   = sum(current_value for cat in FUND_CATEGORIES)
equity_pct   = equity_value / total_portfolio * 100
fund_pct     = fund_value   / total_portfolio * 100

# Note: Cash (~81.4%) is neither equity nor fund — it's neutral
# The alert must acknowledge this context and frame cash as "to be deployed"
# Do NOT alarm about fund/equity ratio being off because cash hasn't been deployed yet
# Instead: show what the ratio WILL be when cash is fully deployed per the plan

target_equity = config["EQUITY_TARGET_PCT"]   # 20.0
band          = config["BAND_TOLERANCE_PCT"]   # 5.0

if equity_pct > target_equity + band:  # > 25% without cash effect
    fire TRIM alert listing overweight equity positions

# Overweight per-symbol check
for each holding:
    if portfolio_weight_pct > max_portfolio_pct:
        include in weekly digest as OVERWEIGHT WARNING
```

### Tier 3: Deployment Opportunity Signals
Cadence: Every run.
Only fires if: pct below 50d MA >= threshold AND headroom >= min_headroom.

```python
for holding in holdings:
    if holding.status not in ["active", "new", "watch"]:
        continue
    if holding.headroom_amount < config["ALERT_MIN_HEADROOM"]:
        continue

    prices = yfinance.download(symbol, period="60d", interval="1d")
    ma_50  = prices["Close"].tail(50).mean()
    current_price = prices["Close"].iloc[-1]
    pct_below_ma  = (current_price - ma_50) / ma_50 * 100  # negative = below MA

    if pct_below_ma <= -config["DIP_SIGNAL_THRESHOLD_PCT"]:
        signal = {
            "symbol": symbol,
            "pct_below_ma": pct_below_ma,
            "headroom_amount": holding.headroom_amount,
            "headroom_pct": holding.headroom_pct,
            "current_portfolio_weight": holding.portfolio_weight_pct,
            "planned_weight": holding.planned_pct,
            "priority_score": abs(pct_below_ma) * (holding.headroom_amount / 1000),
        }
        deployment_signals.append(signal)

# Sort by priority_score descending — best opportunity first
deployment_signals.sort(key=lambda x: x["priority_score"], reverse=True)
```

### Stop-Loss Signal (immediate, any run type)
```python
# NEVER applies to core_fund category
for holding in holdings:
    if holding.category == "core_fund":
        continue
    if holding.deployed_shares == 0:
        continue
    if holding.stop_loss_pct == 0:
        continue

    pl_pct = (current_price - holding.avg_cost_per_share) / holding.avg_cost_per_share * 100

    if pl_pct <= -holding.stop_loss_pct:
        fire IMMEDIATE stop-loss alert via Telegram
        # This is the only alert that fires outside the weekly digest
        # during a normal daily run (no S&P correction needed)
```

### Take-Profit Signal (weekly digest only, not urgent)
```python
for holding in holdings:
    if holding.take_profit_pct == 0 or holding.deployed_shares == 0:
        continue

    pl_pct = (current_price - holding.avg_cost_per_share) / holding.avg_cost_per_share * 100

    if pl_pct >= holding.take_profit_pct:
        # Add to weekly digest ONLY — not an immediate alert
        include in "CONSIDER TRIMMING" section of weekly digest
```

### S&P 500 Correction Alert (immediate)
```python
spy = yfinance.download("SPY", period="2d", interval="1d")
today_change = (spy["Close"].iloc[-1] - spy["Close"].iloc[-2]) / spy["Close"].iloc[-2] * 100

if today_change <= -config["SP500_CORRECTION_THRESHOLD"]:  # -3.0
    fire IMMEDIATE Telegram alert
    include: SPY change %, cash available, top 5 deployment opportunities
    do NOT include stop-loss or take-profit in this alert — focus on opportunity
```

---

## 7. TELEGRAM MESSAGE FORMAT

### Alert priority rules
- 🔴 Red alerts: stop-loss breach, S&P correction >3%
- 🟡 Yellow alerts: take-profit reached, overweight warning
- 🟢 Green alerts: deployment opportunity (dip + headroom)
- 📊 Gray/neutral: weekly digest sections with no action needed

### Weekly digest template
```
📊 *IRA PORTFOLIO — WEEKLY DIGEST*
{date_string} | {OWNER_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━

💼 *PORTFOLIO HEALTH*
Total Value:       ${total_value:>12,.0f}
  Cash (SPAXX):   ${cash:>12,.0f}  ({cash_pct:.1f}%)
  Core Funds:     ${fund_value:>12,.0f}  ({fund_pct:.1f}%)
  Equities:       ${equity_value:>12,.0f}  ({equity_pct:.1f}%)
Overall P&L:       ${total_pl:>+12,.0f}  ({total_pl_pct:+.1f}%)
80/20 Status:      {band_status_emoji} {band_status_text}
Business Cycle:    {cycle_phase}

━━━━━━━━━━━━━━━━━━━━━━━━
🛒 *DEPLOYMENT OPPORTUNITIES*
(Positions >7% below 50d MA with remaining headroom)
{deployment_section or "✓ No qualifying dips this week"}

━━━━━━━━━━━━━━━━━━━━━━━━
🔄 *SECTOR ROTATION WATCH*
Cycle: {cycle_phase}
{rotation_section}

━━━━━━━━━━━━━━━━━━━━━━━━
📌 *SPECULATIVE WATCHLIST*
(Wide thresholds — long-term holds)
{speculative_section}

━━━━━━━━━━━━━━━━━━━━━━━━
🟡 *TAKE PROFIT CONSIDERATIONS*
{take_profit_section or "✓ No positions at take-profit threshold"}

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  *PENDING ACTIONS*
(Positions marked exit or trim)
{pending_section or "✓ No pending actions"}

━━━━━━━━━━━━━━━━━━━━━━━━
_Your call — no action required._
```

### Correction alert template
```
🔴 *MARKET CORRECTION ALERT*
S&P 500 (SPY) down *{change_pct:.1f}%* today

💵 *Cash available to deploy: ${cash:,.0f}*

Top underweight positions with headroom:
{top_5_opportunities}

This is an opportunistic moment — your decision.
_No action required._
```

### Stop-loss alert template
```
🚨 *STOP LOSS ALERT — {symbol}*
{company_name}

Cost basis:   ${avg_cost:.2f} per share
Current:      ${current_price:.2f} per share
Loss:         *{pl_pct:.1f}%*  (${pl_dollar:,.0f} total)
Your floor:   -{stop_loss_pct:.0f}%

Category: {category} | Status: {status}
Thesis reminder: {notes}

Review thesis carefully before acting.
_No action required — your decision._
```

### Message rules
- Telegram Markdown: `*bold*`, `_italic_`, monospace with backticks
- Maximum message length: 4096 characters — split into multiple messages if exceeded
- Always end every message with: `_No action required — your decision._`
- Never use words: "must", "should", "urgent", "immediately" (except stop-loss)
- For speculative positions — use language: "thesis intact", "watch", "long-term hold"
- Daily run (non-Sunday): send only if stop-loss fires OR correction alert fires
  - If neither: log to Signal_Log but send NO Telegram message (avoid noise)
- Weekly run (Sunday): always send the full digest regardless

---

## 8. GITHUB ACTIONS WORKFLOWS

### `daily_monitor.yml`
```yaml
name: Daily IRA Monitor
on:
  schedule:
    - cron: '0 14 * * 1-5'  # 9:00 AM ET weekdays (14:00 UTC)
  workflow_dispatch:
jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run daily monitor
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scripts/run_daily.py
```

### `weekly_digest.yml`
```yaml
name: Weekly IRA Digest
on:
  schedule:
    - cron: '0 1 * * 1'  # Sunday 8pm ET = Monday 01:00 UTC
  workflow_dispatch:
jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run weekly digest
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scripts/run_weekly.py
```

### `manual_trigger.yml`
```yaml
name: Manual IRA Monitor Run
on:
  workflow_dispatch:
    inputs:
      mode:
        description: 'What to run'
        required: true
        type: choice
        options: [daily, weekly, correction_check, full_report, seed_sheet]
      dry_run:
        description: 'Dry run — print but do not send Telegram'
        required: false
        type: boolean
        default: false
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run selected mode
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          DRY_RUN: ${{ inputs.dry_run }}
          RUN_MODE: ${{ inputs.mode }}
        run: python scripts/run_manual.py
```

---

## 9. DEPENDENCIES — `requirements.txt`

```
yfinance==0.2.54
pandas==2.2.3
numpy==1.26.4
gspread==6.1.4
google-auth==2.35.0
google-auth-oauthlib==1.2.1
python-telegram-bot==21.9
python-dotenv==1.0.1
pytz==2024.2
tenacity==9.0.0
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

---

## 10. ERROR HANDLING

- Wrap ALL yfinance calls in try/except with tenacity retry (max 3, 5s backoff)
- Fidelity mutual funds (FXAIX, FSPSX, FDGFX, FXNAX, FIPDX, FZILX) may have
  limited yfinance data. Try as-is first, then try with "MUTF_US:" prefix.
  If both fail: skip MA calculation, show P&L from sheet data only, note in message.
- If Google Sheets unreachable: retry 3 times, then send Telegram error alert and exit
- If Telegram fails: log full message to stdout (GitHub Actions captures it)
- Each signal tier runs in its own try/except — one tier failing must not stop others
- Every run appends a row to Signal_Log tab regardless of success/failure
- Graceful degradation: partial data is better than no message at all

---

## 11. IMPLEMENTATION ORDER

Build in this exact sequence:

1.  `config/settings.py` + `config/constants.py`
2.  `src/utils/` — logger, retry, date_utils
3.  `src/sheets/client.py` — Google Sheets auth
4.  `src/sheets/reader.py` — read all 4 tabs
5.  `src/sheets/writer.py` — write computed fields back
6.  `scripts/seed_sheet.py` — seed Holdings + Portfolio_Config
7.  `src/market/prices.py` — yfinance integration with fallback
8.  `src/market/indicators.py` — 50d MA, dip score
9.  `src/market/market_status.py` — trading day check, ET timezone
10. `src/portfolio/calculator.py` — all portfolio math
11. `src/portfolio/analyzer.py` — aggregate health metrics
12. `src/signals/tier2_rebalance.py`
13. `src/signals/tier3_speculative.py`
14. `src/signals/correction.py`
15. `src/signals/tier1_macro.py`
16. `src/alerts/telegram_bot.py`
17. `src/alerts/formatter.py`
18. `src/alerts/dispatcher.py`
19. `scripts/run_daily.py`
20. `scripts/run_weekly.py`
21. `scripts/run_manual.py`
22. `.github/workflows/` — all 3 files
23. `tests/` — full test suite
24. `README.md` — complete setup guide

---

## 12. README.md MUST INCLUDE

These sections with complete step-by-step instructions:

### Prerequisites
- Python 3.11+
- Google account
- GitHub account (free)
- Telegram account (free)

### Google Cloud Setup
- Create project at console.cloud.google.com
- Enable Google Sheets API
- Create service account + download JSON key
- The JSON key goes into GitHub secret GOOGLE_SERVICE_ACCOUNT_JSON (all on one line)

### Google Sheets Setup
- Create new sheet named "IRA Portfolio Monitor"
- Share with service account email (Editor access)
- Create 4 tabs: Holdings, Portfolio_Config, Transactions, Signal_Log
- Copy Sheet ID from URL: docs.google.com/spreadsheets/d/[THIS_PART]/edit
- Run: python scripts/seed_sheet.py (one-time, populates all initial data)

### Telegram Bot Setup
- Message @BotFather on Telegram → /newbot
- Name it "IRA Monitor Bot" → receive token
- Start conversation with your bot
- Message @userinfobot to get your personal chat ID
- Both go into GitHub secrets

### GitHub Setup
- Fork this repository
- Settings → Secrets and variables → Actions → New repository secret
- Add: GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- Actions tab → Enable workflows
- Test: Actions → Manual IRA Monitor Run → Run workflow → mode: weekly, dry_run: true

### Updating Portfolio After a Trade
- Open Google Sheet → Holdings tab
- Find symbol row → update deployed_amount and deployed_shares columns
- Optionally log in Transactions tab
- Next scheduled run recalculates everything automatically

### Changing Cycle Phase
- Open Google Sheet → Portfolio_Config tab
- Find CYCLE_PHASE row → change value to EARLY / MID / LATE / RECESSION
- Next run uses the new phase for rotation signals

### Adding a New Symbol
- Add new row to Holdings tab
- Required: symbol, company_name, category, planned_pct, deployed_amount, deployed_shares
- Set stop_loss_pct (0 for core funds, 25-40 for everything else)
- Set status: active / new / watch
- Script picks it up automatically on next run

---

## 13. KEY CONTEXT FOR CLAUDE CODE

- **Traditional IRA** — all gains tax-deferred. No tax-loss harvesting.
- **50 years old, 15-year horizon** — never be alarmist about short-term moves.
- **Business cycle: LATE** — defensive positions not yet initiated (XLP, XLV, XLU,
  JNJ, NEE, KO). These always appear as high-priority deployment opportunities.
- **80/20 target** — when cash deployed per plan, 80% lands in core_fund category.
- **Never suggest selling core funds** — rebalance signals only, never exit signals.
- **Speculative positions are tiny by design** — wide stop-losses are intentional.
  Do not alert on normal daily volatility for IONQ, QBTS, SMR, ONDS.
- **Daily run = silent unless emergency** — no Telegram unless stop-loss or SPY -3%.
- **Weekly digest = always sends** — comprehensive Sunday evening summary.
- **Simplicity over cleverness** — code will be maintained by a non-developer.
  Every function should be readable without deep Python knowledge.
- **Fidelity mutual fund tickers** — yfinance support is inconsistent for FXAIX etc.
  Build robust fallback. Never crash the run because one ticker has no MA data.
- **Cash context** — $833,637 (81.4%) is in SPAXX money market. This is not a
  problem — it's undeployed capital earning ~5%. Frame deployment alerts as
  "opportunity to deploy" not "you're holding too much cash."

---

*End of specification.*
*Build all components. Ask no clarifying questions — all decisions are above.*
*If something is ambiguous, choose the simpler implementation.*
