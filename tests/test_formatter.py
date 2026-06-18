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
    subject, plain, html = format_weekly_digest(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health, signals)
    assert "IRA" in subject
    assert "WEEKLY DIGEST" in plain
    assert "PORTFOLIO HEALTH" in plain
    assert "DEPLOYMENT OPPORTUNITIES" in plain
    assert "XLP" in plain
    assert len(plain) > 100
    assert "<html>" in html or "<div" in html


def test_weekly_digest_no_signals():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    subject, plain, html = format_weekly_digest(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health, [])
    assert "No qualifying dips" in plain
    assert "within bands" in plain


def test_correction_alert_format():
    opps = [
        {"symbol": "XLP", "pct_below_ma": -9.0, "headroom_amount": 30000.0},
    ]
    subject, plain, html = format_correction_alert(-3.5, 833637.12, opps)
    assert "CORRECTION ALERT" in plain
    assert "3.5%" in plain
    assert "833,637" in plain
    assert "XLP" in plain
    assert "SPY" in subject


def test_correction_alert_no_opportunities():
    subject, plain, html = format_correction_alert(-4.0, 500000.0, [])
    assert "No positions currently below threshold" in plain


def test_stop_loss_alert_format():
    signal = {
        "symbol": "IONQ", "company_name": "IonQ Inc",
        "avg_cost": 58.0, "current_price": 30.0,
        "pl_pct": -48.3, "pl_dollar": -1946,
        "stop_loss_pct": 40.0, "category": "speculative",
        "status": "active", "notes": "Quantum computing leader.",
    }
    subject, plain, html = format_stop_loss_alert(signal)
    assert "STOP LOSS ALERT" in plain
    assert "IONQ" in plain
    assert "48.3%" in plain
    assert "IONQ" in subject


def test_weekly_digest_includes_correction_threshold():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    subject, plain, html = format_weekly_digest(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health, [])
    assert "CORRECTION ALERT THRESHOLD" in plain
    assert "3%" in plain
