import json
import gspread

from config.constants import HOLDINGS_COLUMNS, SIGNAL_LOG_COLUMNS
from src.utils.logger import get_logger
from src.utils.retry import api_retry
from src.utils.date_utils import iso_now

logger = get_logger("sheets.writer")


@api_retry
def update_holdings(sheet: gspread.Spreadsheet, holdings: list[dict]) -> None:
    ws = sheet.worksheet("Holdings")
    header = ws.row_values(1)

    col_map = {}
    for i, col_name in enumerate(header):
        col_name_clean = col_name.strip()
        if col_name_clean in HOLDINGS_COLUMNS:
            col_map[col_name_clean] = i + 1

    # Only write fields not handled by sheet formulas or GOOGLEFINANCE
    # current_price → GOOGLEFINANCE formula (don't overwrite)
    # current_value, pl_dollar, pl_pct, portfolio_weight_pct → sheet formulas
    # headroom_amount, headroom_pct, vs_plan_pct, avg_cost_per_share → sheet formulas
    computed_fields = [
        "dip_score", "last_updated",
    ]

    updates = []
    for row_idx, holding in enumerate(holdings, start=2):
        for field in computed_fields:
            if field not in col_map:
                continue
            val = holding.get(field, "")
            if field == "last_updated":
                val = iso_now()
            col = col_map[field]
            updates.append(gspread.Cell(row_idx, col, val))

    if updates:
        ws.update_cells(updates)
        logger.info("Updated %d cells in Holdings", len(updates))


@api_retry
def append_signal_log(
    sheet: gspread.Spreadsheet,
    run_type: str,
    signals_fired: list[dict],
    email_sent: bool,
    sp500_change_pct: float,
    portfolio_equity_pct: float,
    portfolio_fund_pct: float,
    notes: str = "",
) -> None:
    ws = sheet.worksheet("Signal_Log")
    row = [
        iso_now(),
        run_type,
        json.dumps(signals_fired),
        str(email_sent).lower(),
        round(sp500_change_pct, 2),
        round(portfolio_equity_pct, 2),
        round(portfolio_fund_pct, 2),
        notes,
    ]
    ws.append_row(row)
    logger.info("Appended signal log: type=%s, signals=%d", run_type, len(signals_fired))
