"""Vanguard CSV importer.

Vanguard export: My Accounts → Holdings → Download (CSV)
Typical columns:
  Account Number, Investment Name, Symbol, Shares, Share Price,
  Total Value, Total Cost, Gain/Loss Dollar, Gain/Loss Percent
"""
from src.importers.base import BrokerImporter
from src.importers.fidelity import CASH_SYMBOLS, _guess_category
from src.utils.logger import get_logger

logger = get_logger("importers.vanguard")

VANGUARD_CASH = {"VMFXX", "VMMXX", "VMRXX"} | CASH_SYMBOLS
VANGUARD_FUNDS = {
    "VFIAX", "VTSAX", "VTIAX", "VBTLX", "VGSLX", "VTBLX",
    "VEXAX", "VEMIX", "VSMPX", "VIMAX", "VSMAX",
}


class VanguardImporter(BrokerImporter):
    name = "vanguard"

    def parse_row(self, row: dict) -> dict | None:
        symbol = ""
        for key in ("Symbol", "symbol", "Ticker"):
            if key in row and row[key]:
                symbol = row[key].strip()
                break

        if not symbol or symbol in ("", "--"):
            return None

        if symbol.upper() in VANGUARD_CASH:
            for key in ("Total Value", "Market Value"):
                if key in row:
                    val = self.clean_number(row[key])
                    if val > 0:
                        logger.info("Cash position: %s = $%.2f", symbol, val)
            return None

        description = ""
        for key in ("Investment Name", "Description", "Name"):
            if key in row and row[key]:
                description = row[key].strip()
                break

        quantity = 0.0
        for key in ("Shares", "Quantity"):
            if key in row and row[key]:
                quantity = self.clean_number(row[key])
                break

        cost_basis = 0.0
        for key in ("Total Cost", "Cost Basis", "Cost Basis Total"):
            if key in row and row[key]:
                cost_basis = self.clean_number(row[key])
                break

        if quantity == 0 and cost_basis == 0:
            return None

        category = _guess_category(symbol, description)
        if symbol.upper() in VANGUARD_FUNDS:
            category = "core_fund"

        return self._make_holding(
            symbol=symbol,
            company_name=description,
            deployed_amount=cost_basis,
            deployed_shares=quantity,
            category=category,
        )
