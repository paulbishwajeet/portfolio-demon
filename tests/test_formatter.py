import pytest
from tests.fixtures.mock_portfolio import MOCK_HOLDINGS, MOCK_CONFIG
from src.portfolio.calculator import get_portfolio_breakdown
from src.portfolio.analyzer import analyze_health
from src.alerts.formatter import (
    format_weekly_digest,
    format_correction_alert,
    format_stop_loss_alert,
)


def test_weekly_digest_format():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    signals = [
        {
            "type": "deployment_opportunity", "severity": "green",
            "symbol": "XLP", "company_name": "Consumer Staples ETF",
            "pct_below_ma": -9.0, "headroom_amount": 30000.0,
            "headroom_pct": 100.0, "current_weight": 0.0,
            "planned_weight": 3.0, "current_price": 82.0,
            "priority_score": 270.0, "message": "test",
        },
    ]
    msg = format_weekly_digest(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health, signals)
    assert "WEEKLY DIGEST" in msg
    assert "PORTFOLIO HEALTH" in msg
    assert "DEPLOYMENT OPPORTUNITIES" in msg
    assert "XLP" in msg
    assert "no action required" in msg
    assert len(msg) > 100


def test_correction_alert_format():
    opps = [
        {"symbol": "XLP", "pct_below_ma": -9.0, "headroom_amount": 30000.0},
    ]
    msg = format_correction_alert(-3.5, 833637.12, opps)
    assert "CORRECTION ALERT" in msg
    assert "3.5%" in msg
    assert "833,637" in msg
    assert "XLP" in msg
    assert "No action required" in msg


def test_correction_alert_no_opportunities():
    msg = format_correction_alert(-4.0, 500000.0, [])
    assert "No positions currently below threshold" in msg


def test_stop_loss_alert_format():
    signal = {
        "symbol": "IONQ", "company_name": "IonQ Inc",
        "avg_cost": 58.0, "current_price": 30.0,
        "pl_pct": -48.3, "pl_dollar": -1946,
        "stop_loss_pct": 40.0, "category": "speculative",
        "status": "active", "notes": "Quantum computing leader.",
    }
    msg = format_stop_loss_alert(signal)
    assert "STOP LOSS ALERT" in msg
    assert "IONQ" in msg
    assert "48.3%" in msg
    assert "No action required" in msg


def test_weekly_digest_max_length():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    msg = format_weekly_digest(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health, [])
    # Should be well under Telegram's 4096 limit with test data
    assert len(msg) < 4096
