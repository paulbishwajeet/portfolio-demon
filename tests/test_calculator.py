import pytest
from unittest.mock import patch
from tests.fixtures.mock_portfolio import MOCK_HOLDINGS, MOCK_CONFIG
from src.portfolio.calculator import get_portfolio_breakdown
from src.portfolio.analyzer import analyze_health


def test_portfolio_breakdown():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    assert breakdown["total_value"] == MOCK_CONFIG["TOTAL_IRA_VALUE"]
    assert breakdown["cash"] == MOCK_CONFIG["CASH_REMAINING"]
    assert breakdown["fund_value"] == 35482.72  # only FXAIX is core_fund
    assert breakdown["equity_value"] > 0
    assert breakdown["total_pl"] == pytest.approx(
        sum(h["pl_dollar"] for h in MOCK_HOLDINGS), abs=0.01
    )


def test_portfolio_breakdown_zero_total():
    config = dict(MOCK_CONFIG)
    config["TOTAL_IRA_VALUE"] = 0
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, config)
    assert breakdown["cash_pct"] == 0
    assert breakdown["fund_pct"] == 0


def test_analyze_health_pending_actions():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    pending = health["pending_actions"]
    assert any(h["symbol"] == "PL" for h in pending)
    assert health["cycle_phase"] == "LATE"


def test_analyze_health_speculative():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    assert health["speculative_pct"] < 8.0
    assert health["speculative_over_cap"] is False
