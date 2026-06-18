"""Fidelity Investments CSV importer.

Fidelity export: Positions page → Download → CSV
Typical columns:
  Account Number/Name, Symbol, Description, Quantity, Last Price,
  Last Price Change, Current Value, Today's Gain/Loss Dollar,
  Today's Gain/Loss Percent, Total Gain/Loss Dollar,
  Total Gain/Loss Percent, Cost Basis Total, Cost Basis Per Share,
  Type

The CSV has a trailing summary row and sometimes blank lines.
Money market positions (SPAXX, FCASH, etc.) are included — we extract
the cash balance from these and skip them as holdings.
"""
from src.importers.base import BrokerImporter
from src.utils.logger import get_logger

logger = get_logger("importers.fidelity")

# Fidelity mutual fund symbols → treat as core_fund
FIDELITY_FUND_SYMBOLS = {
    "FXAIX", "FSPSX", "FDGFX", "FXNAX", "FIPDX", "FZILX",
    "FSKAX", "FTIHX", "FBNDX", "FBALX", "FBIIX", "FXILX",
    "FNILX", "FZROX", "FZILX", "FUAMX", "FLCSX",
}

# Money market / cash positions to skip as holdings
CASH_SYMBOLS = {"SPAXX", "FCASH", "FDRXX", "FZFXX", "SPRXX", "CORE"}

# Common ETF prefixes that suggest fund-like behavior
BOND_ETFS = {"BND", "AGG", "TLT", "IEF", "SHY", "TIPS", "SCHZ", "VGIT"}
INTL_ETFS = {"VXUS", "IXUS", "EFA", "VEA", "VWO", "IEMG"}
SP500_ETFS = {"VOO", "IVV", "SPY", "SPLG"}


def _guess_category(symbol: str, description: str) -> str:
    sym = symbol.upper()
    desc = description.upper()

    if sym in FIDELITY_FUND_SYMBOLS:
        return "core_fund"
    if sym in SP500_ETFS or sym in BOND_ETFS or sym in INTL_ETFS:
        return "core_fund"
    if "INDEX" in desc or "BOND" in desc or "TREASURY" in desc:
        return "core_fund"
    if "ETF" in desc:
        return "existing_addition"
    return "quality_stock"


class FidelityImporter(BrokerImporter):
    name = "fidelity"
    cash_balance = 0.0

    def _get(self, row: dict, *keys) -> str:
        for key in keys:
            if key in row and row[key] and row[key].strip() not in ("", "--"):
                return row[key].strip()
        return ""

    def parse_row(self, row: dict) -> dict | None:
        symbol = self._get(row, "Symbol", "symbol", "SYMBOL")

        # Skip blank rows and disclaimer text at bottom
        if not symbol:
            return None

        # Skip cash positions but capture the balance
        if symbol.upper() in CASH_SYMBOLS:
            val = self.clean_number(self._get(row, "Current Value", "current_value"))
            if val > 0:
                self.cash_balance = val
                logger.info("Cash position: %s = $%.2f", symbol, val)
            return None

        description = self._get(row, "Description", "description", "Security Description")
        quantity = self.clean_number(self._get(row, "Quantity", "quantity", "Shares"))

        cost_basis = self.clean_number(
            self._get(row, "Cost Basis Total", "Cost Basis", "cost_basis_total")
        )

        # Fidelity uses "Average Cost Basis" for per-share cost
        if cost_basis == 0:
            per_share = self.clean_number(
                self._get(row, "Average Cost Basis", "Cost Basis Per Share")
            )
            if per_share > 0 and quantity > 0:
                cost_basis = round(per_share * quantity, 2)

        if quantity == 0 and cost_basis == 0:
            logger.info("Skipping %s — no quantity or cost basis", symbol)
            return None

        category = _guess_category(symbol, description)

        return self._make_holding(
            symbol=symbol,
            company_name=description,
            deployed_amount=cost_basis,
            deployed_shares=quantity,
            category=category,
        )

    def import_holdings(self, filepath: str) -> list[dict]:
        self.cash_balance = 0.0
        holdings = super().import_holdings(filepath)
        if self.cash_balance > 0:
            logger.info("Total cash detected: $%.2f — use --cash %.2f or set CASH_REMAINING in Portfolio_Config",
                        self.cash_balance, self.cash_balance)
        return holdings
