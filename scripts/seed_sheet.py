"""Seed the Google Sheet — either as an empty template or from a broker CSV.

Usage:
  # Empty template (headers, config defaults, formulas, dropdowns, live prices)
  python scripts/seed_sheet.py

  # Import from Fidelity CSV
  python scripts/seed_sheet.py --broker fidelity --csv ~/Downloads/Portfolio_Positions.csv

  # Import from Schwab CSV
  python scripts/seed_sheet.py --broker schwab --csv ~/Downloads/Positions.csv

  # Import from Vanguard CSV
  python scripts/seed_sheet.py --broker vanguard --csv ~/Downloads/Holdings.csv

  # Import from any broker (auto-detect columns)
  python scripts/seed_sheet.py --broker generic --csv ~/Downloads/positions.csv

  # Set total account value and cash (optional, detected from CSV when possible)
  python scripts/seed_sheet.py --broker fidelity --csv positions.csv --total 500000 --cash 200000

After seeding, the script automatically runs:
  - setup_formulas.py   (computed column formulas)
  - setup_dropdowns.py  (data validation dropdowns)
  - setup_dates_and_prices.py (date pickers + GOOGLEFINANCE live prices)
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from config.constants import HOLDINGS_COLUMNS, SIGNAL_LOG_COLUMNS
from src.sheets.client import get_sheet
from src.utils.logger import get_logger

logger = get_logger("seed_sheet")

BROKERS = {
    "fidelity": "src.importers.fidelity.FidelityImporter",
    "schwab": "src.importers.schwab.SchwabImporter",
    "vanguard": "src.importers.vanguard.VanguardImporter",
    "generic": "src.importers.generic.GenericImporter",
}

CONFIG_DEFAULTS = [
    ["TOTAL_IRA_VALUE", "0"],
    ["CASH_REMAINING", "0"],
    ["EQUITY_TARGET_PCT", "20.0"],
    ["FUND_TARGET_PCT", "80.0"],
    ["BAND_TOLERANCE_PCT", "5.0"],
    ["CYCLE_PHASE", "LATE"],
    ["SP500_CORRECTION_THRESHOLD", "3.0"],
    ["DIP_SIGNAL_THRESHOLD_PCT", "7.0"],
    ["STOP_LOSS_DEFAULT_PCT", "35.0"],
    ["TAKE_PROFIT_DEFAULT_PCT", "75.0"],
    ["ALERT_MIN_HEADROOM", "2000.0"],
    ["OWNER_NAME", "Portfolio Owner"],
]


def _get_importer(broker_name: str):
    path = BROKERS.get(broker_name)
    if not path:
        logger.error("Unknown broker: %s. Supported: %s", broker_name, ", ".join(BROKERS))
        sys.exit(1)
    module_path, class_name = path.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)()


def seed_template(sheet: gspread.Spreadsheet):
    """Create empty sheet with headers and config defaults."""
    logger.info("Seeding empty template...")

    # Holdings tab
    try:
        ws = sheet.worksheet("Holdings")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Holdings", rows=50, cols=25)
    ws.clear()
    ws.append_row(HOLDINGS_COLUMNS)
    logger.info("Holdings tab: headers set (add your positions here)")

    _seed_config_and_log_tabs(sheet)


def seed_from_csv(sheet: gspread.Spreadsheet, broker: str, csv_path: str,
                  total_override: float = None, cash_override: float = None):
    """Import holdings from broker CSV."""
    importer = _get_importer(broker)
    holdings = importer.import_holdings(csv_path)

    if not holdings:
        logger.error("No holdings parsed from CSV. Check the file format.")
        sys.exit(1)

    # Holdings tab
    try:
        ws = sheet.worksheet("Holdings")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Holdings", rows=50, cols=25)
    ws.clear()
    all_rows = [HOLDINGS_COLUMNS]
    for h in holdings:
        row = [h.get(col, "") for col in HOLDINGS_COLUMNS]
        all_rows.append(row)

    ws.update(range_name=f"A1:Y{len(all_rows)}", values=all_rows)
    logger.info("Imported %d holdings from %s CSV", len(holdings), broker)

    # Calculate totals for config
    total_deployed = sum(h["deployed_amount"] for h in holdings)
    logger.info("Total deployed (cost basis): $%.2f", total_deployed)

    # Auto-detect cash from broker importer (Fidelity captures SPAXX balance)
    detected_cash = getattr(importer, "cash_balance", 0.0)

    # Seed config with calculated or overridden values
    cash_value = cash_override if cash_override else detected_cash
    total_value = total_override if total_override else (total_deployed + cash_value)

    _seed_config_and_log_tabs(sheet, total_value=total_value, cash_value=cash_value)

    # Print summary
    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"Broker:           {broker}")
    print(f"Holdings imported: {len(holdings)}")
    print(f"Total deployed:    ${total_deployed:,.2f}")
    if total_override:
        print(f"Total account value:   ${total_value:,.2f} (from --total)")
    else:
        print(f"Total account value:   ${total_value:,.2f} (deployed + cash)")
    if cash_override:
        print(f"Cash (SPAXX):      ${cash_value:,.2f} (from --cash)")
    elif detected_cash > 0:
        print(f"Cash (SPAXX):      ${cash_value:,.2f} (auto-detected from CSV)")
    else:
        print(f"Cash (SPAXX):      $0.00 (update CASH_REMAINING in Portfolio_Config)")
    print()
    print("REVIEW THESE COLUMNS in the Holdings tab:")
    print("  D (category)       — auto-guessed, verify each one")
    print("  E (planned_pct)    — set your target allocation % for each")
    print("  J (stop_loss_pct)  — set per-position (0 for core funds)")
    print("  K (take_profit_pct)— set per-position")
    print("  L (max_portfolio_pct) — set hard cap %")
    print("  M (status)         — active / new / watch / trim / exit")
    print("  N (cycle_alignment)— positive / negative / neutral")
    print("  O (notes)          — your investment thesis")
    print("=" * 50)


def _seed_config_and_log_tabs(sheet: gspread.Spreadsheet,
                               total_value: float = 0, cash_value: float = 0):
    """Create Portfolio_Config, Transactions, Signal_Log, Trade_Entry tabs."""

    # Portfolio_Config
    try:
        ws = sheet.worksheet("Portfolio_Config")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Portfolio_Config", rows=20, cols=2)
    ws.clear()
    config = list(CONFIG_DEFAULTS)
    if total_value:
        config[0] = ["TOTAL_IRA_VALUE", str(round(total_value, 2))]
    if cash_value:
        config[1] = ["CASH_REMAINING", str(round(cash_value, 2))]
    all_rows = [["Key", "Value"]] + config
    ws.update(range_name=f"A1:B{len(all_rows)}", values=all_rows)
    logger.info("Portfolio_Config: %d keys set", len(config))

    # Transactions
    try:
        sheet.worksheet("Transactions")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Transactions", rows=100, cols=8)
        ws.append_row(["date", "symbol", "action", "shares",
                       "price_per_share", "total_amount", "reason",
                       "cycle_phase_at_trade"])
    logger.info("Transactions tab ready")

    # Signal_Log
    try:
        sheet.worksheet("Signal_Log")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Signal_Log", rows=500, cols=8)
        ws.append_row(SIGNAL_LOG_COLUMNS)
    logger.info("Signal_Log tab ready")

    # Trade_Entry
    try:
        ws = sheet.worksheet("Trade_Entry")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="Trade_Entry", rows=50, cols=8)
        ws.append_row(["date", "symbol", "action", "shares",
                       "price_per_share", "total_amount", "reason", "status"])
        cells = []
        for row in range(2, 21):
            cells.append(gspread.Cell(row, 6,
                         f'=IF(AND(D{row}<>"", E{row}<>""), D{row}*E{row}, "")'))
            cells.append(gspread.Cell(row, 8,
                         f'=IF(B{row}<>"", "pending", "")'))
        ws.update_cells(cells, value_input_option='USER_ENTERED')
    logger.info("Trade_Entry tab ready")


def run_setup_scripts():
    """Run all sheet setup scripts (formulas, dropdowns, dates/prices)."""
    logger.info("Running setup scripts...")

    from scripts.setup_formulas import setup_formulas
    setup_formulas()

    from scripts.setup_dropdowns import setup_dropdowns
    setup_dropdowns()

    from scripts.setup_dates_and_prices import setup
    setup()

    logger.info("All setup scripts complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Seed the Portfolio Demon Google Sheet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Empty template
  python scripts/seed_sheet.py

  # Import from Fidelity
  python scripts/seed_sheet.py --broker fidelity --csv ~/Downloads/Portfolio_Positions.csv

  # Import with known account totals
  python scripts/seed_sheet.py --broker fidelity --csv positions.csv --total 500000 --cash 200000

  # Import from any broker CSV (auto-detect columns)
  python scripts/seed_sheet.py --broker generic --csv positions.csv

Supported brokers: fidelity, schwab, vanguard, generic
        """,
    )
    parser.add_argument("--broker", "-b", choices=list(BROKERS.keys()),
                        help="Broker name for CSV import")
    parser.add_argument("--csv", "-c", help="Path to broker CSV export file")
    parser.add_argument("--total", "-t", type=float,
                        help="Total account value (overrides CSV calculation)")
    parser.add_argument("--cash", type=float,
                        help="Cash/money market balance")
    parser.add_argument("--skip-setup", action="store_true",
                        help="Skip running formula/dropdown/price setup scripts")
    args = parser.parse_args()

    if args.csv and not args.broker:
        args.broker = "generic"
        logger.info("No broker specified — using generic auto-detect")

    if args.broker and not args.csv:
        parser.error("--broker requires --csv")

    sheet = get_sheet()

    if args.csv:
        seed_from_csv(sheet, args.broker, args.csv, args.total, args.cash)
    else:
        seed_template(sheet)

    if not args.skip_setup:
        run_setup_scripts()

    logger.info("Sheet seeding complete!")


if __name__ == "__main__":
    main()
