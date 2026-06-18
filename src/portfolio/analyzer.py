from config.constants import FUND_CATEGORIES, EQUITY_CATEGORIES
from src.utils.logger import get_logger

logger = get_logger("portfolio.analyzer")


def analyze_health(holdings: list[dict], config: dict, breakdown: dict) -> dict:
    equity_target = config["EQUITY_TARGET_PCT"]
    fund_target = config["FUND_TARGET_PCT"]
    band = config["BAND_TOLERANCE_PCT"]

    # 80/20 band status (relative to invested portion, not total with cash)
    invested = breakdown["fund_value"] + breakdown["equity_value"]
    if invested > 0:
        equity_of_invested = breakdown["equity_value"] / invested * 100
        fund_of_invested = breakdown["fund_value"] / invested * 100
    else:
        equity_of_invested = 0
        fund_of_invested = 0

    band_breach = False
    band_status = "on_target"
    if equity_of_invested > equity_target + band:
        band_breach = True
        band_status = "equity_overweight"
    elif equity_of_invested < equity_target - band:
        band_breach = True
        band_status = "equity_underweight"

    # Overweight positions
    overweight = []
    for h in holdings:
        if h["max_portfolio_pct"] > 0 and h["portfolio_weight_pct"] > h["max_portfolio_pct"]:
            overweight.append({
                "symbol": h["symbol"],
                "current_weight": h["portfolio_weight_pct"],
                "max_weight": h["max_portfolio_pct"],
                "excess": round(h["portfolio_weight_pct"] - h["max_portfolio_pct"], 2),
            })

    # Positions marked for exit/trim
    pending_actions = [
        h for h in holdings if h["status"] in ("exit", "trim")
    ]

    # Speculative exposure
    spec_value = sum(
        h["current_value"] for h in holdings if h["category"] == "speculative"
    )
    spec_pct = round(spec_value / breakdown["total_value"] * 100, 2) if breakdown["total_value"] > 0 else 0
    spec_over_cap = spec_pct > 8.0

    return {
        "equity_of_invested_pct": round(equity_of_invested, 1),
        "fund_of_invested_pct": round(fund_of_invested, 1),
        "band_breach": band_breach,
        "band_status": band_status,
        "overweight_positions": overweight,
        "pending_actions": pending_actions,
        "speculative_pct": spec_pct,
        "speculative_over_cap": spec_over_cap,
        "cycle_phase": config.get("CYCLE_PHASE", "LATE"),
    }
