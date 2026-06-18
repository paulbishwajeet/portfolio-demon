CYCLE_ROTATION = {
    "EARLY": {
        "favor": ["core_fund", "quality_stock"],
        "reduce": ["trim_exit"],
        "message": "Early cycle: favor growth and rate-sensitive sectors",
    },
    "MID": {
        "favor": ["core_fund", "quality_stock"],
        "reduce": ["trim_exit"],
        "message": "Mid cycle: broad growth, reduce laggards",
    },
    "LATE": {
        "favor": ["core_fund", "new_defensive"],
        "reduce": ["existing_addition", "trim_exit"],
        "message": "Late cycle: shift to defensive. Energy, staples, healthcare favored.",
    },
    "RECESSION": {
        "favor": ["core_fund", "new_defensive"],
        "reduce": ["existing_addition", "trim_exit", "speculative"],
        "message": "Recession: maximum defensive positioning. Staples, utilities, healthcare.",
    },
}

FUND_CATEGORIES = ["core_fund"]
EQUITY_CATEGORIES = [
    "quality_stock",
    "speculative",
    "new_defensive",
    "existing_addition",
    "trim_exit",
]

DEFAULT_CONFIG = {
    "TOTAL_IRA_VALUE": 1023521.66,
    "CASH_REMAINING": 833637.12,
    "EQUITY_TARGET_PCT": 20.0,
    "FUND_TARGET_PCT": 80.0,
    "BAND_TOLERANCE_PCT": 5.0,
    "CYCLE_PHASE": "LATE",
    "SP500_CORRECTION_THRESHOLD": 3.0,
    "DIP_SIGNAL_THRESHOLD_PCT": 7.0,
    "STOP_LOSS_DEFAULT_PCT": 35.0,
    "TAKE_PROFIT_DEFAULT_PCT": 75.0,
    "ALERT_MIN_HEADROOM": 2000.0,
    "OWNER_NAME": "Portfolio Owner",
}

FLOAT_CONFIG_KEYS = {
    "TOTAL_IRA_VALUE",
    "CASH_REMAINING",
    "EQUITY_TARGET_PCT",
    "FUND_TARGET_PCT",
    "BAND_TOLERANCE_PCT",
    "SP500_CORRECTION_THRESHOLD",
    "DIP_SIGNAL_THRESHOLD_PCT",
    "STOP_LOSS_DEFAULT_PCT",
    "TAKE_PROFIT_DEFAULT_PCT",
    "ALERT_MIN_HEADROOM",
}

HOLDINGS_COLUMNS = [
    "symbol", "company_name", "sector_theme", "category",
    "planned_pct", "planned_amount", "deployed_amount", "deployed_shares",
    "avg_cost_per_share", "stop_loss_pct", "take_profit_pct", "max_portfolio_pct",
    "status", "cycle_alignment", "notes",
    "current_price", "current_value", "pl_dollar", "pl_pct",
    "portfolio_weight_pct", "headroom_amount", "headroom_pct", "vs_plan_pct",
    "dip_score", "last_updated",
]

SIGNAL_LOG_COLUMNS = [
    "run_timestamp", "run_type", "signals_fired", "telegram_sent",
    "sp500_change_pct", "portfolio_equity_pct", "portfolio_fund_pct", "notes",
]
