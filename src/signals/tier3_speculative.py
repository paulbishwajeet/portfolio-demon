from src.utils.logger import get_logger

logger = get_logger("signals.tier3_speculative")


def check_deployment_signals(holdings: list[dict], config: dict) -> list[dict]:
    threshold = config["DIP_SIGNAL_THRESHOLD_PCT"]
    min_headroom = config["ALERT_MIN_HEADROOM"]
    signals = []

    for h in holdings:
        if h["status"] not in ("active", "new", "watch"):
            continue
        if h["headroom_amount"] < min_headroom:
            continue
        if h["dip_score"] >= -threshold:
            continue

        signals.append({
            "type": "deployment_opportunity",
            "severity": "green",
            "symbol": h["symbol"],
            "company_name": h["company_name"],
            "pct_below_ma": round(h["dip_score"], 1),
            "headroom_amount": h["headroom_amount"],
            "headroom_pct": h["headroom_pct"],
            "current_weight": h["portfolio_weight_pct"],
            "planned_weight": h["planned_pct"],
            "current_price": h["current_price"],
            "priority_score": round(abs(h["dip_score"]) * (h["headroom_amount"] / 1000), 1),
            "message": f"{h['symbol']} is {h['dip_score']:.1f}% below 50d MA — ${h['headroom_amount']:,.0f} headroom",
        })

    signals.sort(key=lambda x: x["priority_score"], reverse=True)
    return signals


def check_stop_loss_signals(holdings: list[dict], config: dict) -> list[dict]:
    signals = []

    for h in holdings:
        if h["category"] == "core_fund":
            continue
        if h["deployed_shares"] == 0 or h["stop_loss_pct"] == 0:
            continue
        if h["avg_cost_per_share"] == 0:
            continue

        pl_pct = (h["current_price"] - h["avg_cost_per_share"]) / h["avg_cost_per_share"] * 100

        if pl_pct <= -h["stop_loss_pct"]:
            signals.append({
                "type": "stop_loss",
                "severity": "red",
                "symbol": h["symbol"],
                "company_name": h["company_name"],
                "avg_cost": h["avg_cost_per_share"],
                "current_price": h["current_price"],
                "pl_pct": round(pl_pct, 1),
                "pl_dollar": h["pl_dollar"],
                "stop_loss_pct": h["stop_loss_pct"],
                "category": h["category"],
                "status": h["status"],
                "notes": h["notes"],
                "message": f"STOP LOSS: {h['symbol']} at {pl_pct:.1f}% loss (floor: -{h['stop_loss_pct']:.0f}%)",
            })

    return signals


def check_take_profit_signals(holdings: list[dict]) -> list[dict]:
    signals = []

    for h in holdings:
        if h["take_profit_pct"] == 0 or h["deployed_shares"] == 0:
            continue
        if h["avg_cost_per_share"] == 0:
            continue

        pl_pct = (h["current_price"] - h["avg_cost_per_share"]) / h["avg_cost_per_share"] * 100

        if pl_pct >= h["take_profit_pct"]:
            signals.append({
                "type": "take_profit",
                "severity": "yellow",
                "symbol": h["symbol"],
                "company_name": h["company_name"],
                "pl_pct": round(pl_pct, 1),
                "take_profit_pct": h["take_profit_pct"],
                "current_value": h["current_value"],
                "message": f"{h['symbol']} at +{pl_pct:.1f}% gain (target: +{h['take_profit_pct']:.0f}%)",
            })

    return signals
