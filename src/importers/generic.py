"""Generic CSV importer for any broker.

Tries to auto-detect columns by matching common header names.
Works with any CSV that has at least: symbol, quantity, and cost basis.
"""
from src.importers.base import BrokerImporter
from src.importers.fidelity import CASH_SYMBOLS, _guess_category
from src.utils.logger import get_logger

logger = get_logger("importers.generic")

SYMBOL_NAMES = {"Symbol", "symbol", "SYMBOL", "Ticker", "ticker", "TICKER"}
DESC_NAMES = {"Description", "description", "Name", "name", "Security Description",
              "Investment Name", "Company", "Security Name", "Security"}
QTY_NAMES = {"Quantity", "quantity", "Shares", "shares", "QUANTITY", "SHARES", "Units"}
COST_NAMES = {"Cost Basis Total", "Cost Basis", "cost_basis", "Total Cost",
              "Cost basis total", "CostBasis", "Book Cost", "Average Cost Basis"}
COST_PER_SHARE_NAMES = {"Cost Basis Per Share", "Cost Per Share", "Avg Cost",
                        "Average Cost", "Unit Cost", "Book Price"}


class GenericImporter(BrokerImporter):
    name = "generic"

    def _find_col(self, row: dict, candidates: set) -> str | None:
        for key in row:
            if key.strip() in candidates:
                return key
        return None

    def parse_row(self, row: dict) -> dict | None:
        sym_key = self._find_col(row, SYMBOL_NAMES)
        if not sym_key or not row[sym_key].strip():
            return None

        symbol = row[sym_key].strip().upper()
        if symbol in CASH_SYMBOLS or symbol in ("", "--", "TOTAL", "TOTALS", "ACCOUNT TOTAL"):
            return None

        desc_key = self._find_col(row, DESC_NAMES)
        description = row[desc_key].strip() if desc_key and row.get(desc_key) else ""

        qty_key = self._find_col(row, QTY_NAMES)
        quantity = self.clean_number(row[qty_key]) if qty_key and row.get(qty_key) else 0.0

        cost_key = self._find_col(row, COST_NAMES)
        cost_basis = self.clean_number(row[cost_key]) if cost_key and row.get(cost_key) else 0.0

        if cost_basis == 0:
            cps_key = self._find_col(row, COST_PER_SHARE_NAMES)
            if cps_key and row.get(cps_key):
                per_share = self.clean_number(row[cps_key])
                if per_share > 0:
                    cost_basis = round(per_share * quantity, 2)

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
