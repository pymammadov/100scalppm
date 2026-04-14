from __future__ import annotations

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from src.family_evaluator import CostModel, backtest_family, summarize_trades


def _mk_row(ts: datetime, open_: float, high: float, low: float, close: float, atr: float) -> dict:
    return {
        "timestamp": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1.0,
        "ema_fast": close + 1.0,
        "ema_slow": close - 1.0,
        "atr": atr,
        "range_high": close - 0.5,
        "range_low": close - 5.0,
        "vwap": close - 0.2,
        "rsi": 50.0,
        "hour": ts.hour,
        "vol_regime": "high_vol",
        "trend_regime": "uptrend",
    }


def _family(stop_atr: float, risk_per_trade: float = 0.01):
    return SimpleNamespace(
        family_id="FAM_TEST",
        family_name="test_family",
        parameters={
            "entry_block": "range_breakout",
            "exit_block": "fixed_stop_fixed_tp",
            "regime_block": "uptrend_only",
            "confirmation": "ema_alignment",
            "position_mode": "long_only",
            "stop_atr": stop_atr,
            "tp_r": 1.0,
            "time_stop_bars": 2,
            "throttle_bars": 0,
            "risk_per_trade": risk_per_trade,
        },
    )


def test_equity_sizing_uses_risk_budget() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        _mk_row(ts, 100.0, 101.0, 99.0, 100.0, atr=2.0),
        _mk_row(ts + timedelta(minutes=1), 100.0, 103.0, 99.0, 102.0, atr=2.0),
        _mk_row(ts + timedelta(minutes=2), 102.0, 104.0, 100.0, 103.0, atr=2.0),
    ]
    trades, metrics = backtest_family(rows, _family(stop_atr=1.0), CostModel(fee_bps=0.0, slippage_bps=0.0), "oos", initial_capital=10_000.0)

    assert len(trades) == 1
    trade = trades[0]
    # risk budget = 10000 * 1% = 100; per-unit risk = 2.0 => qty 50
    assert abs(trade["qty"] - 50.0) < 1e-9
    assert trade["entry_notional"] <= trade["notional_cap"] + 1e-9
    assert abs(metrics["ending_equity"] - (10_000.0 + trade["net_pnl"])) < 1e-9


def test_notional_cap_limits_leverage() -> None:
    ts = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = [
        _mk_row(ts, 100.0, 101.0, 99.0, 100.0, atr=0.02),
        _mk_row(ts + timedelta(minutes=1), 100.0, 100.5, 99.5, 101.0, atr=0.02),
        _mk_row(ts + timedelta(minutes=2), 101.0, 101.5, 100.0, 101.2, atr=0.02),
    ]
    trades, _ = backtest_family(rows, _family(stop_atr=1.0), CostModel(fee_bps=0.0, slippage_bps=0.0), "oos", initial_capital=10_000.0)

    assert len(trades) == 1
    trade = trades[0]
    # Tiny stop implies huge risk-based qty, so cap should bind at 1x initial capital.
    assert abs(trade["entry_notional"] - 10_000.0) < 1e-6
    assert trade["leverage_used"] <= 1.0 + 1e-9


def test_invalid_sizing_inputs_skip_trade() -> None:
    ts = datetime(2026, 1, 3, tzinfo=timezone.utc)
    rows = [
        _mk_row(ts, 100.0, 101.0, 99.0, 100.0, atr=2.0),
        _mk_row(ts + timedelta(minutes=1), 100.0, 103.0, 99.0, 102.0, atr=float("nan")),
        _mk_row(ts + timedelta(minutes=2), 102.0, 104.0, 100.0, 103.0, atr=2.0),
    ]
    trades, metrics = backtest_family(rows, _family(stop_atr=1.0), CostModel(fee_bps=0.0, slippage_bps=0.0), "oos", initial_capital=10_000.0)
    assert trades == []
    assert metrics["ending_equity"] == 10_000.0


def test_summarize_trades_reports_capital_usage_fields() -> None:
    metrics = summarize_trades(
        [
            {"net_pnl": 100.0, "holding_time_minutes": 10.0, "side": "long", "setup_type": "x", "timestamp_entry": "2026-01-01T00:00:00+00:00", "trend_regime": "uptrend", "vol_regime": "high_vol", "entry_price": 100.0, "qty": 10.0, "entry_notional": 1000.0, "leverage_used": 0.1},
            {"net_pnl": -50.0, "holding_time_minutes": 5.0, "side": "short", "setup_type": "y", "timestamp_entry": "2026-01-01T00:05:00+00:00", "trend_regime": "downtrend", "vol_regime": "low_vol", "entry_price": 200.0, "qty": 5.0, "entry_notional": 1000.0, "leverage_used": 0.11},
        ],
        initial_capital=10_000.0,
    )

    assert metrics["average_entry_notional"] == 1000.0
    assert metrics["max_entry_notional"] == 1000.0
    assert abs(metrics["average_leverage_used"] - 0.105) < 1e-9
    assert metrics["max_leverage_used"] == 0.11


def test_trade_journal_has_required_capital_fields() -> None:
    ts = datetime(2026, 1, 4, tzinfo=timezone.utc)
    rows = [
        _mk_row(ts, 100.0, 101.0, 99.0, 100.0, atr=2.0),
        _mk_row(ts + timedelta(minutes=1), 100.0, 103.0, 99.0, 102.0, atr=2.0),
        _mk_row(ts + timedelta(minutes=2), 102.0, 104.0, 100.0, 103.0, atr=2.0),
    ]
    trades, _ = backtest_family(rows, _family(stop_atr=1.0), CostModel(fee_bps=0.0, slippage_bps=0.0), "oos", initial_capital=10_000.0)
    trade = trades[0]
    for key in [
        "entry_time",
        "exit_time",
        "quantity",
        "entry_notional",
        "exit_notional",
        "starting_equity_before_trade",
        "ending_equity_after_trade",
        "leverage_used_or_gross_exposure",
    ]:
        assert key in trade
