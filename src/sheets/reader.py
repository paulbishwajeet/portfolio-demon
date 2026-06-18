from typing import Any
import gspread

from config.constants import DEFAULT_CONFIG, FLOAT_CONFIG_KEYS
from src.utils.logger import get_logger
from src.utils.retry import api_retry

logger = get_logger("sheets.reader")


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(str(val).replace(",", "").replace("$", "").replace("%", ""))
    except (ValueError, TypeError):
        return default


@api_retry
def read_holdings(sheet: gspread.Spreadsheet) -> list[dict]:
    ws = sheet.worksheet("Holdings")
    rows = ws.get_all_records()
    holdings = []
    for row in rows:
        if not row.get("symbol"):
            continue
        h = {
            "symbol": str(row.get("symbol", "")).strip(),
            "company_name": str(row.get("company_name", "")),
            "sector_theme": str(row.get("sector_theme", "")),
            "category": str(row.get("category", "")),
            "planned_pct": _safe_float(row.get("planned_pct")),
            "planned_amount": _safe_float(row.get("planned_amount")),
            "deployed_amount": _safe_float(row.get("deployed_amount")),
            "deployed_shares": _safe_float(row.get("deployed_shares")),
            "avg_cost_per_share": _safe_float(row.get("avg_cost_per_share")),
            "stop_loss_pct": _safe_float(row.get("stop_loss_pct")),
            "take_profit_pct": _safe_float(row.get("take_profit_pct")),
            "max_portfolio_pct": _safe_float(row.get("max_portfolio_pct")),
            "status": str(row.get("status", "")),
            "cycle_alignment": str(row.get("cycle_alignment", "")),
            "notes": str(row.get("notes", "")),
            "current_price": _safe_float(row.get("current_price")),
            "current_value": _safe_float(row.get("current_value")),
            "pl_dollar": _safe_float(row.get("pl_dollar")),
            "pl_pct": _safe_float(row.get("pl_pct")),
            "portfolio_weight_pct": _safe_float(row.get("portfolio_weight_pct")),
            "headroom_amount": _safe_float(row.get("headroom_amount")),
            "headroom_pct": _safe_float(row.get("headroom_pct")),
            "vs_plan_pct": _safe_float(row.get("vs_plan_pct")),
            "dip_score": _safe_float(row.get("dip_score")),
            "last_updated": str(row.get("last_updated", "")),
        }
        holdings.append(h)
    logger.info("Read %d holdings from sheet", len(holdings))
    return holdings


@api_retry
def read_config(sheet: gspread.Spreadsheet) -> dict:
    ws = sheet.worksheet("Portfolio_Config")
    rows = ws.get_all_values()
    config = dict(DEFAULT_CONFIG)
    for row in rows:
        if len(row) < 2 or not row[0]:
            continue
        key = row[0].strip()
        val = row[1].strip()
        if key in FLOAT_CONFIG_KEYS:
            config[key] = _safe_float(val, DEFAULT_CONFIG.get(key, 0.0))
        else:
            config[key] = val
    logger.info("Read config: cycle=%s, cash=%.0f", config.get("CYCLE_PHASE"), config.get("CASH_REMAINING", 0))
    return config


@api_retry
def read_transactions(sheet: gspread.Spreadsheet) -> list[dict]:
    ws = sheet.worksheet("Transactions")
    return ws.get_all_records()
