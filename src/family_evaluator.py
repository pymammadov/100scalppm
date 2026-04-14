from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

DEFAULT_INITIAL_CAPITAL = 10_000.0
DEFAULT_MAX_LEVERAGE = 1.0
DEFAULT_RISK_PER_TRADE_PCT = 0.01


@dataclass
class CostModel:
    fee_bps: float = 4.0
    slippage_bps: float = 1.5


@dataclass
class CapitalConfig:
    initial_capital_usd: float = DEFAULT_INITIAL_CAPITAL
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT
    max_leverage: float = DEFAULT_MAX_LEVERAGE
    max_gross_exposure_pct: float | None = None

    def effective_max_notional(self, equity: float) -> float:
        max_equity = max(0.0, equity)
        leverage_cap = max_equity * max(0.0, self.max_leverage)
        if self.max_gross_exposure_pct is None:
            return leverage_cap
        gross_cap = max_equity * max(0.0, self.max_gross_exposure_pct) / 100.0
        return min(leverage_cap, gross_cap)


def _ema(values: list[float], span: int) -> list[float]:
    alpha = 2 / (span + 1)
    out = []
    prev = values[0]
    for v in values:
        prev = alpha * v + (1 - alpha) * prev
        out.append(prev)
    return out


def _rolling_max(vals: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(vals)):
        lo = max(0, i - window)
        out.append(max(vals[lo:i]) if i > 0 else vals[0])
    return out


def _rolling_min(vals: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(vals)):
        lo = max(0, i - window)
        out.append(min(vals[lo:i]) if i > 0 else vals[0])
    return out


def _rolling_mean(vals: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(vals)):
        lo = max(0, i - window + 1)
        chunk = vals[lo : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def prepare_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda x: x["timestamp"])
    close = [r["close"] for r in rows]
    high = [r["high"] for r in rows]
    low = [r["low"] for r in rows]
    vol = [r["volume"] for r in rows]
    ema_fast = _ema(close, 12)
    ema_slow = _ema(close, 55)

    tr = []
    for i in range(len(rows)):
        prev_close = close[i - 1] if i > 0 else close[i]
        tr.append(max(high[i] - low[i], abs(high[i] - prev_close), abs(low[i] - prev_close)))
    atr = _rolling_mean(tr, 14)
    range_high = _rolling_max(high, 20)
    range_low = _rolling_min(low, 20)

    tp = [(high[i] + low[i] + close[i]) / 3 for i in range(len(rows))]
    vwap = []
    c_pv = 0.0
    c_v = 0.0
    for i in range(len(rows)):
        c_pv += tp[i] * vol[i]
        c_v += vol[i]
        vwap.append(c_pv / c_v if c_v else close[i])

    delta = [0.0] + [close[i] - close[i - 1] for i in range(1, len(close))]
    gains = [max(0.0, d) for d in delta]
    losses = [max(0.0, -d) for d in delta]
    avg_gain = _rolling_mean(gains, 14)
    avg_loss = _rolling_mean(losses, 14)
    rsi = []
    for g, loss in zip(avg_gain, avg_loss):
        if loss == 0:
            rsi.append(50.0)
        else:
            rs = g / loss
            rsi.append(100 - (100 / (1 + rs)))

    atr_med = _rolling_mean(atr, 50)
    out = []
    for i, r in enumerate(rows):
        ts = datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00"))
        out.append(
            {
                **r,
                "timestamp": ts,
                "ema_fast": ema_fast[i],
                "ema_slow": ema_slow[i],
                "atr": atr[i],
                "range_high": range_high[i],
                "range_low": range_low[i],
                "vwap": vwap[i],
                "rsi": rsi[i],
                "hour": ts.hour,
                "vol_regime": "high_vol" if atr[i] > atr_med[i] else "low_vol",
                "trend_regime": "uptrend" if ema_fast[i] > ema_slow[i] else "downtrend",
            }
        )
    return out


def split_dataset(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    n = len(rows)
    i1 = int(n * 0.6)
    i2 = int(n * 0.8)
    return {"train": rows[:i1], "validation": rows[i1:i2], "oos": rows[i2:]}


def _regime_pass(row: dict[str, Any], regime_block: str) -> bool:
    if regime_block == "uptrend_only":
        return row["trend_regime"] == "uptrend"
    if regime_block == "downtrend_only":
        return row["trend_regime"] == "downtrend"
    if regime_block == "high_vol_only":
        return row["vol_regime"] == "high_vol"
    if regime_block == "low_vol_only":
        return row["vol_regime"] == "low_vol"
    if regime_block == "sideways_disabled":
        return abs(row["ema_fast"] - row["ema_slow"]) / row["close"] > 0.0006
    return True


def _entry_signal(prev_row: dict[str, Any], row: dict[str, Any], params: dict[str, Any]) -> int:
    entry = params["entry_block"]
    long_sig = short_sig = False
    if entry in {"range_breakout", "compression_breakout", "session_open_burst", "range_breakdown"}:
        long_sig = row["close"] > row["range_high"]
        short_sig = row["close"] < row["range_low"]
    elif entry in {"pullback_reentry", "momentum_continuation"}:
        long_sig = row["trend_regime"] == "uptrend" and row["close"] > row["ema_fast"] > prev_row["close"]
        short_sig = row["trend_regime"] == "downtrend" and row["close"] < row["ema_fast"] < prev_row["close"]
    elif entry in {"failed_breakout_fade", "failed_breakdown_fade", "overextension_revert"}:
        long_sig = (prev_row["high"] > prev_row["range_high"]) and row["rsi"] < 45
        short_sig = (prev_row["low"] < prev_row["range_low"]) and row["rsi"] > 55
    elif entry in {"vwap_reclaim", "liquidity_sweep_reclaim"}:
        long_sig = prev_row["close"] < prev_row["vwap"] and row["close"] > row["vwap"]
        short_sig = prev_row["close"] > prev_row["vwap"] and row["close"] < row["vwap"]
    elif entry == "vwap_rejection":
        long_sig = row["close"] > row["vwap"] and row["low"] <= row["vwap"]
        short_sig = row["close"] < row["vwap"] and row["high"] >= row["vwap"]

    conf = params["confirmation"]
    if conf == "rsi_filter":
        long_sig = long_sig and row["rsi"] < 65
        short_sig = short_sig and row["rsi"] > 35
    elif conf == "ema_alignment":
        long_sig = long_sig and row["ema_fast"] > row["ema_slow"]
        short_sig = short_sig and row["ema_fast"] < row["ema_slow"]
    elif conf == "vwap_distance":
        long_sig = long_sig and abs(row["close"] - row["vwap"]) / row["close"] > 0.0007
        short_sig = short_sig and abs(row["close"] - row["vwap"]) / row["close"] > 0.0007
    elif conf == "session_filter":
        long_sig = long_sig and row["hour"] in {0, 1, 7, 8, 12, 13, 14}
        short_sig = short_sig and row["hour"] in {0, 1, 7, 8, 12, 13, 14}

    if params["position_mode"] == "long_only":
        short_sig = False
    elif params["position_mode"] == "short_only":
        long_sig = False
    return 1 if long_sig else -1 if short_sig else 0


def to_float_safe(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except Exception:
        return default


def backtest_family(
    rows: list[dict[str, Any]],
    family: Any,
    cost: CostModel,
    split_name: str,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    p = family.parameters
    cap_cfg = CapitalConfig(
        initial_capital_usd=initial_capital,
        risk_per_trade_pct=max(0.0, float(p.get("risk_per_trade", DEFAULT_RISK_PER_TRADE_PCT))),
        max_leverage=DEFAULT_MAX_LEVERAGE,
        max_gross_exposure_pct=None,
    )
    trades: list[dict[str, Any]] = []
    in_pos = 0
    entry_price = stop = tp = None
    entry_ts = None
    entry_idx = 0
    throttle_until = -1
    cash = initial_capital
    realized_pnl = 0.0
    equity = initial_capital
    qty = 0.0
    risk_budget = 0.0
    notional_cap = 0.0

    def _is_finite_positive(value: float) -> bool:
        return math.isfinite(value) and value > 0.0

    def _size_position(entry_px: float, stop_px: float) -> tuple[float, float, float]:
        if equity <= 0.0:
            return 0.0, 0.0, 0.0
        if not _is_finite_positive(entry_px) or not math.isfinite(stop_px):
            return 0.0, 0.0, 0.0
        risk_per_unit = abs(entry_px - stop_px)
        if not _is_finite_positive(risk_per_unit):
            return 0.0, 0.0, 0.0
        risk_budget_local = max(0.0, equity) * max(0.0, cap_cfg.risk_per_trade_pct)
        notional_cap_local = cap_cfg.effective_max_notional(equity)
        if risk_budget_local <= 0.0 or notional_cap_local <= 0.0:
            return 0.0, risk_budget_local, notional_cap_local
        qty_risk = risk_budget_local / risk_per_unit
        qty_notional = notional_cap_local / abs(entry_px)
        qty_local = min(qty_risk, qty_notional)
        if not _is_finite_positive(qty_local):
            return 0.0, risk_budget_local, notional_cap_local
        return qty_local, risk_budget_local, notional_cap_local

    for i in range(1, len(rows)):
        row = rows[i]
        prev = rows[i - 1]
        if in_pos == 0 and i <= throttle_until:
            continue
        if in_pos == 0:
            equity = cash
            if equity <= 0.0:
                continue
            if not _regime_pass(row, p["regime_block"]):
                continue
            sig = _entry_signal(prev, row, p)
            if sig == 0:
                continue
            in_pos = sig
            entry_price = row["open"] * (1 + (cost.slippage_bps / 10000) * sig)
            risk = row["atr"] * p["stop_atr"]
            stop = entry_price - risk if sig == 1 else entry_price + risk
            tp = entry_price + risk * p["tp_r"] if sig == 1 else entry_price - risk * p["tp_r"]
            qty, risk_budget, notional_cap = _size_position(entry_price, stop)
            if qty <= 0.0:
                in_pos = 0
                continue
            if (qty * abs(entry_price)) > (equity * cap_cfg.max_leverage + 1e-9):
                in_pos = 0
                continue
            entry_ts = row["timestamp"]
            entry_idx = i
            continue

        hit_stop = row["low"] <= stop if in_pos == 1 else row["high"] >= stop
        hit_tp = row["high"] >= tp if in_pos == 1 else row["low"] <= tp
        timeout = i - entry_idx >= p["time_stop_bars"]
        if not (hit_stop or hit_tp or timeout):
            continue
        if hit_stop:
            exit_price = stop * (1 - (cost.slippage_bps / 10000) * in_pos)
            exit_reason = "stop"
        elif hit_tp:
            exit_price = tp * (1 - (cost.slippage_bps / 10000) * in_pos)
            exit_reason = "tp"
        else:
            exit_price = row["close"] * (1 - (cost.slippage_bps / 10000) * in_pos)
            exit_reason = "time"
        gross = (exit_price - entry_price) * in_pos * qty
        fees = (abs(entry_price) + abs(exit_price)) * qty * cost.fee_bps / 10000
        slip_cost = (abs(entry_price) + abs(exit_price)) * qty * cost.slippage_bps / 10000
        net = gross - fees - slip_cost
        equity_before = equity
        realized_pnl += net
        cash = max(0.0, cap_cfg.initial_capital_usd + realized_pnl)
        equity = cash
        ts_exit = row["timestamp"]
        hold_mins = (ts_exit - entry_ts).total_seconds() / 60
        history = rows[entry_idx : i + 1]
        mfe = (max(x["high"] for x in history) - entry_price) * in_pos * qty
        mae = (min(x["low"] for x in history) - entry_price) * in_pos * qty
        entry_notional = abs(entry_price) * qty
        exit_notional = abs(exit_price) * qty
        leverage_used = (entry_notional / equity_before) if equity_before > 0 else 0.0
        trades.append(
            {
                "trade_id": f"{family.family_id}_{split_name}_{len(trades):05d}",
                "timestamp_entry": entry_ts.isoformat(),
                "timestamp_exit": ts_exit.isoformat(),
                "entry_time": entry_ts.isoformat(),
                "exit_time": ts_exit.isoformat(),
                "side": "long" if in_pos == 1 else "short",
                "setup_type": p["entry_block"],
                "family_id": family.family_id,
                "family_name": family.family_name,
                "entry_reason": p["entry_block"],
                "exit_reason": exit_reason,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "qty": qty,
                "quantity": qty,
                "gross_pnl": gross,
                "net_pnl": net,
                "fees": fees,
                "slippage_cost": slip_cost,
                "R_multiple": gross / (rows[entry_idx]["atr"] + 1e-9),
                "risk_budget": risk_budget,
                "notional_cap": notional_cap,
                "entry_notional": entry_notional,
                "exit_notional": exit_notional,
                "leverage_used": leverage_used,
                "leverage_used_or_gross_exposure": leverage_used,
                "equity_before": equity_before,
                "equity_after": equity,
                "starting_equity_before_trade": equity_before,
                "ending_equity_after_trade": equity,
                "holding_time": str(ts_exit - entry_ts),
                "holding_time_minutes": hold_mins,
                "MFE": mfe,
                "MAE": mae,
                "trend_regime": rows[entry_idx]["trend_regime"],
                "vol_regime": rows[entry_idx]["vol_regime"],
                "pre_rsi": rows[entry_idx]["rsi"],
                "pre_atr": rows[entry_idx]["atr"],
                "pre_vwap_distance": abs(rows[entry_idx]["close"] - rows[entry_idx]["vwap"]) / rows[entry_idx]["close"],
            }
        )
        in_pos = 0
        throttle_until = i + p["throttle_bars"]
    return trades, summarize_trades(trades, initial_capital=initial_capital)


def summarize_trades(trades: list[dict[str, Any]], initial_capital: float = DEFAULT_INITIAL_CAPITAL) -> dict[str, Any]:
    if not trades:
        return {k: 0.0 for k in ["net_pnl", "profit_factor", "expectancy", "max_drawdown", "max_drawdown_pct", "trade_count", "average_trade_pnl", "average_win", "average_loss", "win_rate", "average_holding_time", "return_pct"]} | {
            "starting_capital": initial_capital,
            "ending_equity": initial_capital,
            "average_entry_notional": 0.0,
            "max_entry_notional": 0.0,
            "average_leverage_used": 0.0,
            "max_leverage_used": 0.0,
            "pnl_by_side": "{}",
            "pnl_by_setup": "{}",
            "pnl_by_hour": "{}",
            "pnl_by_regime": "{}",
        }
    pnls = [t["net_pnl"] for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    eq_abs = [to_float_safe(t.get("ending_equity_after_trade"), initial_capital + sum(pnls[: i + 1])) for i, t in enumerate(trades)]
    peak = eq_abs[0]
    mdd = 0.0
    mdd_pct = 0.0
    for e in eq_abs:
        peak = max(peak, e)
        mdd = min(mdd, e - peak)
        if peak > 0:
            mdd_pct = min(mdd_pct, ((e - peak) / peak) * 100.0)

    def group_sum(key_fn):
        d = {}
        for t in trades:
            k = key_fn(t)
            d[k] = d.get(k, 0.0) + t["net_pnl"]
        return str(d)

    entry_notionals = [t.get("entry_notional", abs(t["entry_price"]) * t.get("qty", 0.0)) for t in trades]
    leverages = [t.get("leverage_used", 0.0) for t in trades]
    avg_notional = sum(entry_notionals) / len(entry_notionals)
    avg_leverage = sum(leverages) / len(leverages)

    return {
        "starting_capital": initial_capital,
        "ending_equity": eq_abs[-1] if eq_abs else initial_capital,
        "net_pnl": sum(pnls),
        "return_pct": (((eq_abs[-1] / initial_capital) - 1.0) * 100.0) if initial_capital and eq_abs else 0.0,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses else sum(wins),
        "expectancy": sum(pnls) / len(pnls),
        "max_drawdown": mdd,
        "max_drawdown_pct": mdd_pct,
        "trade_count": len(trades),
        "average_trade_pnl": sum(pnls) / len(pnls),
        "average_win": sum(wins) / len(wins) if wins else 0.0,
        "average_loss": sum(losses) / len(losses) if losses else 0.0,
        "win_rate": len(wins) / len(pnls),
        "average_holding_time": sum(t["holding_time_minutes"] for t in trades) / len(trades),
        "average_entry_notional": avg_notional,
        "max_entry_notional": max(entry_notionals),
        "average_leverage_used": avg_leverage,
        "max_leverage_used": max(leverages),
        "pnl_by_side": group_sum(lambda t: t["side"]),
        "pnl_by_setup": group_sum(lambda t: t["setup_type"]),
        "pnl_by_hour": group_sum(lambda t: t["timestamp_entry"][11:13]),
        "pnl_by_regime": group_sum(lambda t: f"{t['trend_regime']}|{t['vol_regime']}"),
    }
