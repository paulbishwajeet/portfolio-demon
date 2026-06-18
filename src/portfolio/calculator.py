from config.constants import FUND_CATEGORIES, EQUITY_CATEGORIES
from src.market.prices import prefetch_all
from src.market.indicators import get_moving_average, get_dip_score
from src.utils.logger import get_logger

logger = get_logger("portfolio.calculator")


def compute_holdings(holdings: list[dict], config: dict) -> list[dict]:
    total_portfolio = config["TOTAL_IRA_VALUE"]

    # Phase 1: compute portfolio math using sheet prices (GOOGLEFINANCE)
    for h in holdings:
        if h["current_price"] > 0:
            logger.info("Using sheet price for %s: $%.2f", h["symbol"], h["current_price"])
        else:
            logger.warning("No price for %s — skipping", h["symbol"])

        shares = h["deployed_shares"]
        deployed = h["deployed_amount"]

        if shares > 0 and deployed > 0:
            h["avg_cost_per_share"] = round(deployed / shares, 4)
        else:
            h["avg_cost_per_share"] = 0.0

        if h["current_price"] > 0 and shares > 0:
            h["current_value"] = round(h["current_price"] * shares, 2)
        else:
            h["current_value"] = 0.0

        if deployed > 0:
            h["pl_dollar"] = round(h["current_value"] - deployed, 2)
            h["pl_pct"] = round(h["pl_dollar"] / deployed * 100, 2)
        else:
            h["pl_dollar"] = 0.0
            h["pl_pct"] = 0.0

        if total_portfolio > 0:
            h["portfolio_weight_pct"] = round(h["current_value"] / total_portfolio * 100, 2)
        else:
            h["portfolio_weight_pct"] = 0.0

        h["headroom_amount"] = round(h["planned_amount"] - deployed, 2)
        if h["planned_amount"] > 0:
            h["headroom_pct"] = round(h["headroom_amount"] / h["planned_amount"] * 100, 2)
        else:
            h["headroom_pct"] = 0.0

        h["vs_plan_pct"] = round(h["portfolio_weight_pct"] - h["planned_pct"], 2)

    # Phase 2: fetch historical data from yfinance for dip scores (50d MA)
    # This is the ONLY yfinance usage — prices come from the Google Sheet
    symbols_for_ma = [h["symbol"] for h in holdings if h["current_price"] > 0]
    prefetch_all(symbols_for_ma)

    for h in holdings:
        if h["current_price"] > 0:
            try:
                ma = get_moving_average(h["symbol"])
                if ma:
                    h["dip_score"] = round(get_dip_score(h["current_price"], ma), 2)
                else:
                    h["dip_score"] = 0.0
            except Exception as e:
                logger.warning("Dip score failed for %s: %s", h["symbol"], e)
                h["dip_score"] = 0.0
        else:
            h["dip_score"] = 0.0

    return holdings


def get_portfolio_breakdown(holdings: list[dict], config: dict) -> dict:
    cash = config["CASH_REMAINING"]
    total = config["TOTAL_IRA_VALUE"]

    fund_value = sum(
        h["current_value"] for h in holdings if h["category"] in FUND_CATEGORIES
    )
    equity_value = sum(
        h["current_value"] for h in holdings if h["category"] in EQUITY_CATEGORIES
    )

    invested = fund_value + equity_value
    total_pl = sum(h["pl_dollar"] for h in holdings)
    total_deployed = sum(h["deployed_amount"] for h in holdings)

    return {
        "total_value": total,
        "cash": cash,
        "cash_pct": round(cash / total * 100, 1) if total > 0 else 0,
        "fund_value": round(fund_value, 2),
        "fund_pct": round(fund_value / total * 100, 1) if total > 0 else 0,
        "equity_value": round(equity_value, 2),
        "equity_pct": round(equity_value / total * 100, 1) if total > 0 else 0,
        "invested_value": round(invested, 2),
        "total_deployed": round(total_deployed, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_pct": round(total_pl / total_deployed * 100, 1) if total_deployed > 0 else 0,
    }
