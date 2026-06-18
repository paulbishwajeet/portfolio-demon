from src.utils.logger import get_logger

logger = get_logger("signals.tier2_rebalance")


def check_rebalance_signals(holdings: list[dict], config: dict, breakdown: dict, health: dict) -> list[dict]:
    signals = []

    # 80/20 band breach
    if health["band_breach"]:
        signals.append({
            "type": "band_breach",
            "severity": "yellow",
            "status": health["band_status"],
            "equity_of_invested_pct": health["equity_of_invested_pct"],
            "fund_of_invested_pct": health["fund_of_invested_pct"],
            "message": f"Portfolio balance outside target band: equity {health['equity_of_invested_pct']:.1f}% of invested (target {config['EQUITY_TARGET_PCT']}% ± {config['BAND_TOLERANCE_PCT']}%)",
        })

    # Overweight positions
    for ow in health["overweight_positions"]:
        signals.append({
            "type": "overweight",
            "severity": "yellow",
            "symbol": ow["symbol"],
            "current_weight": ow["current_weight"],
            "max_weight": ow["max_weight"],
            "excess": ow["excess"],
            "message": f"{ow['symbol']} overweight: {ow['current_weight']:.1f}% vs {ow['max_weight']:.1f}% cap",
        })

    # Speculative over 8% cap
    if health["speculative_over_cap"]:
        signals.append({
            "type": "speculative_cap",
            "severity": "yellow",
            "speculative_pct": health["speculative_pct"],
            "message": f"Speculative positions at {health['speculative_pct']:.1f}% — exceeds 8% cap",
        })

    return signals
