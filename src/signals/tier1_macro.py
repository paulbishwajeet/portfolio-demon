from config.constants import CYCLE_ROTATION, EQUITY_CATEGORIES
from src.utils.logger import get_logger

logger = get_logger("signals.tier1_macro")


def check_rotation_signals(holdings: list[dict], config: dict) -> list[dict]:
    cycle_phase = config.get("CYCLE_PHASE", "LATE")
    rotation = CYCLE_ROTATION.get(cycle_phase)
    if not rotation:
        return []

    reduce_categories = rotation["reduce"]
    favor_categories = rotation["favor"]

    # Calculate total value of holdings in "reduce" categories
    reduce_value = sum(
        h["current_value"] for h in holdings if h["category"] in reduce_categories
    )
    total_value = config["TOTAL_IRA_VALUE"]

    if total_value == 0:
        return []

    reduce_pct = reduce_value / total_value * 100
    signals = []

    # Fire rotation alert if reduce categories exceed 5% of total portfolio in LATE/RECESSION
    if cycle_phase in ("LATE", "RECESSION") and reduce_pct > 5.0:
        reduce_holdings = [
            h for h in holdings
            if h["category"] in reduce_categories and h["current_value"] > 0
        ]
        favor_holdings = [
            h for h in holdings
            if h["category"] in favor_categories
            and h["headroom_amount"] > 0
            and h["status"] in ("active", "new")
        ]
        signals.append({
            "type": "rotation",
            "severity": "yellow",
            "cycle_phase": cycle_phase,
            "message": rotation["message"],
            "reduce_pct": round(reduce_pct, 1),
            "reduce_symbols": [
                {"symbol": h["symbol"], "value": h["current_value"], "category": h["category"]}
                for h in reduce_holdings
            ],
            "favor_symbols": [
                {"symbol": h["symbol"], "headroom": h["headroom_amount"], "category": h["category"]}
                for h in favor_holdings
            ],
        })

    return signals
