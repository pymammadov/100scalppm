from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.family_evaluator import CostModel, backtest_family


def _row(ts: datetime, close: float, atr: float) -> dict:
    return {
        "timestamp": ts,
        "open": close,
        "high": close + 2.0,
        "low": close - 2.0,
        "close": close,
        "volume": 1.0,
        "ema_fast": close + 1.0,
        "ema_slow": close - 1.0,
        "atr": atr,
        "range_high": close - 0.1,
        "range_low": close - 3.0,
        "vwap": close - 0.1,
        "rsi": 50.0,
        "hour": ts.hour,
        "vol_regime": "high_vol",
        "trend_regime": "uptrend",
    }


def _family() -> SimpleNamespace:
    return SimpleNamespace(
        family_id="FAM_REGRESSION",
        family_name="regression",
        parameters={
            "entry_block": "range_breakout",
            "exit_block": "fixed_stop_fixed_tp",
            "regime_block": "uptrend_only",
            "confirmation": "ema_alignment",
            "position_mode": "long_only",
            "stop_atr": 1.0,
            "tp_r": 1.0,
            "time_stop_bars": 2,
            "throttle_bars": 0,
            "risk_per_trade": 0.01,
        },
    )


def test_trade_journal_contains_capital_fields() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [_row(ts, 100.0, 2.0), _row(ts + timedelta(minutes=1), 102.0, 2.0), _row(ts + timedelta(minutes=2), 103.0, 2.0)]
    trades, metrics = backtest_family(rows, _family(), CostModel(fee_bps=0.0, slippage_bps=0.0), "oos", initial_capital=10_000.0)

    assert trades, "Expected at least one trade."
    first = trades[0]
    for key in ("qty", "entry_notional", "leverage_used", "equity_before", "equity_after"):
        assert key in first
    assert metrics["starting_capital"] == 10_000.0
