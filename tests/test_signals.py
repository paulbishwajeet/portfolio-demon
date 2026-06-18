import pytest
from tests.fixtures.mock_portfolio import MOCK_HOLDINGS, MOCK_CONFIG
from src.signals.tier1_macro import check_rotation_signals
from src.signals.tier2_rebalance import check_rebalance_signals
from src.signals.tier3_speculative import (
    check_deployment_signals,
    check_stop_loss_signals,
    check_take_profit_signals,
)
from src.portfolio.calculator import get_portfolio_breakdown
from src.portfolio.analyzer import analyze_health


def test_rotation_signals_late_cycle():
    signals = check_rotation_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    # PL is trim_exit with value > 0, so rotation should fire if > 5% of total
    # PL value is 2734 / 1023521 = 0.27% — below 5%, so no signal
    # This is expected given our small test data
    assert isinstance(signals, list)


def test_rotation_signals_recession():
    config = dict(MOCK_CONFIG)
    config["CYCLE_PHASE"] = "RECESSION"
    signals = check_rotation_signals(MOCK_HOLDINGS, config)
    assert isinstance(signals, list)


def test_rebalance_signals():
    breakdown = get_portfolio_breakdown(MOCK_HOLDINGS, MOCK_CONFIG)
    health = analyze_health(MOCK_HOLDINGS, MOCK_CONFIG, breakdown)
    signals = check_rebalance_signals(MOCK_HOLDINGS, MOCK_CONFIG, breakdown, health)
    assert isinstance(signals, list)


def test_deployment_signals():
    # XLP has dip_score=-9.0 and headroom=30000 — should fire
    signals = check_deployment_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    xlp_signal = [s for s in signals if s["symbol"] == "XLP"]
    assert len(xlp_signal) == 1
    assert xlp_signal[0]["type"] == "deployment_opportunity"
    assert xlp_signal[0]["pct_below_ma"] == -9.0


def test_deployment_signals_respects_status():
    # PL has status=exit — should be excluded
    signals = check_deployment_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    pl_signals = [s for s in signals if s["symbol"] == "PL"]
    assert len(pl_signals) == 0


def test_stop_loss_signals():
    # IONQ: cost=58.0, price=30.0 → -48.3%, stop=40% → should fire
    signals = check_stop_loss_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    ionq = [s for s in signals if s["symbol"] == "IONQ"]
    assert len(ionq) == 1
    assert ionq[0]["severity"] == "red"


def test_stop_loss_skips_core_funds():
    signals = check_stop_loss_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    core = [s for s in signals if s["symbol"] == "FXAIX"]
    assert len(core) == 0


def test_take_profit_signals():
    signals = check_take_profit_signals(MOCK_HOLDINGS)
    # CRDO is at +58.6% but target is 100% — should not fire
    crdo = [s for s in signals if s["symbol"] == "CRDO"]
    assert len(crdo) == 0


def test_deployment_priority_sorting():
    signals = check_deployment_signals(MOCK_HOLDINGS, MOCK_CONFIG)
    if len(signals) > 1:
        for i in range(len(signals) - 1):
            assert signals[i]["priority_score"] >= signals[i + 1]["priority_score"]
