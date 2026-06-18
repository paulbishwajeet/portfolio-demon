"""Charles Schwab CSV importer.

Schwab export: Positions → Export → CSV
Typical columns:
  Symbol, Description, Quantity, Price, Price Change $, Price Change %,
  Market Value, Day Change $, Day Change %, Cost Basis,
  Gain/Loss $, Gain/Loss %, Ratings, Reinvest Dividends?,
  Capital Gains?, % of Account

The CSV often has a header line like "Positions for account..." before
the actual column headers, and a trailing "Totals" row.
"""
from src.importers.base import BrokerImporter
from src.importers.fidelity import CASH_SYMBOLS, _guess_category
from src.utils.logger import get_logger

logger = get_logger("importers.schwab")

SCHWAB_CASH = {"SWVXX", "SNVXX", "SNAXX"} | CASH_SYMBOLS


class SchwabImporter(BrokerImporter):
    name = "schwab"
    SKIP_LINES = 1  # Schwab has an account info header line

    def parse_row(self, row: dict) -> dict | None:
        symbol = ""
        for key in ("Symbol", "symbol"):
            if key in row and row[key]:
                symbol = row[key].strip()
                break

        if not symbol or symbol in ("", "--", "Account Total", "Totals"):
            return None

        if symbol.upper() in SCHWAB_CASH:
            for key in ("Market Value", "Market value"):
                if key in row:
                    val = self.clean_number(row[key])
                    if val > 0:
                        logger.info("Cash position: %s = $%.2f", symbol, val)
            return None

        description = ""
        for key in ("Description", "Name", "Security Description"):
            if key in row and row[key]:
                description = row[key].strip()
                break

        quantity = 0.0
        for key in ("Quantity", "Shares"):
            if key in row and row[key]:
                quantity = self.clean_number(row[key])
                break

        cost_basis = 0.0
        for key in ("Cost Basis", "Cost Basis Total"):
            if key in row and row[key]:
                cost_basis = self.clean_number(row[key])
                break

        if quantity == 0 and cost_basis == 0:
            return None

        category = _guess_category(symbol, description)

        return self._make_holding(
            symbol=symbol,
            company_name=description,
            deployed_amount=cost_basis,
            deployed_shares=quantity,
            category=category,
        )
