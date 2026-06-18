"""Base class for broker CSV importers."""
import csv
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("importers.base")


class BrokerImporter:
    """Override parse_row() and COLUMN_MAP in subclasses."""

    name = "generic"

    # Map broker CSV column names -> our schema field names
    # Subclasses override this
    COLUMN_MAP = {}

    # Broker CSVs often have junk header rows before the actual data
    SKIP_LINES = 0

    def read_csv(self, filepath: str) -> list[dict]:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {filepath}")

        with open(path, "r", encoding="utf-8-sig") as f:
            # Skip broker-specific header lines
            for _ in range(self.SKIP_LINES):
                f.readline()

            reader = csv.DictReader(f)
            raw_rows = []
            for r in reader:
                # Flatten any list values (caused by trailing commas)
                cleaned = {}
                for k, v in r.items():
                    if isinstance(v, list):
                        v = v[0] if v else ""
                    cleaned[k] = v if v else ""
                # Skip blank/footer rows
                values = [v.strip() for v in cleaned.values() if isinstance(v, str) and v.strip()]
                if not values:
                    continue
                raw_rows.append(cleaned)

        logger.info("Read %d rows from %s", len(raw_rows), path.name)
        return raw_rows

    def clean_number(self, val: str) -> float:
        if not val or val.strip() in ("", "--", "n/a", "N/A"):
            return 0.0
        cleaned = val.strip().replace(",", "").replace("$", "").replace("%", "").replace("+", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def parse_row(self, row: dict) -> dict | None:
        """Convert a broker CSV row to our Holdings schema. Override in subclass."""
        raise NotImplementedError

    def import_holdings(self, filepath: str) -> list[dict]:
        raw_rows = self.read_csv(filepath)
        holdings = []
        for row in raw_rows:
            parsed = self.parse_row(row)
            if parsed and parsed.get("symbol"):
                holdings.append(parsed)
        logger.info("Parsed %d valid holdings from %s", len(holdings), self.name)
        return holdings

    def _make_holding(
        self,
        symbol: str,
        company_name: str = "",
        deployed_amount: float = 0.0,
        deployed_shares: float = 0.0,
        category: str = "quality_stock",
        status: str = "active",
        **overrides,
    ) -> dict:
        """Build a holding dict with defaults for fields the broker doesn't provide."""
        h = {
            "symbol": symbol.strip().upper(),
            "company_name": company_name.strip(),
            "sector_theme": "",
            "category": category,
            "planned_pct": 0.0,
            "planned_amount": 0.0,
            "deployed_amount": round(deployed_amount, 2),
            "deployed_shares": round(deployed_shares, 6),
            "avg_cost_per_share": "",  # formula handles this
            "stop_loss_pct": 0.0 if category == "core_fund" else 30.0,
            "take_profit_pct": 0.0,
            "max_portfolio_pct": 0.0,
            "status": status,
            "cycle_alignment": "neutral",
            "notes": "",
            "current_price": "",   # GOOGLEFINANCE handles this
            "current_value": "",   # formula handles this
            "pl_dollar": "",       # formula
            "pl_pct": "",          # formula
            "portfolio_weight_pct": "",  # formula
            "headroom_amount": "",       # formula
            "headroom_pct": "",          # formula
            "vs_plan_pct": "",           # formula
            "dip_score": "",
            "last_updated": "",
        }
        h.update(overrides)
        return h
