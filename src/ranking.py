from __future__ import annotations

import math
from typing import Any


def _norm(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def rank_candidates(backtest_rows: list[dict[str, Any]], robust_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    robust_map = {r["family_id"]: r for r in robust_rows}
    rows = []
    for b in backtest_rows:
        rows.append({**b, **robust_map.get(b["family_id"], {})})

    oos_quality = _norm([r.get("oos_expectancy", 0.0) + 0.5 * r.get("oos_net_pnl", 0.0) for r in rows])
    val_consistency = _norm([
        -abs(r.get("train_net_pnl", 0.0) - r.get("validation_net_pnl", 0.0))
        -abs(r.get("validation_net_pnl", 0.0) - r.get("oos_net_pnl", 0.0))
        for r in rows
    ])
    drawdown = _norm([r.get("max_drawdown", 0.0) for r in rows])
    trade_count = _norm([math.log1p(max(0.0, r.get("trade_count", 0.0))) for r in rows])
    profit_factor = _norm([r.get("oos_profit_factor", 0.0) for r in rows])
    fee_slip = _norm([r.get("fee_stress_pnl_delta", -1e9) + r.get("slippage_stress_pnl_delta", -1e9) for r in rows])
    param_stability = _norm([r.get("parameter_stability", 0.0) for r in rows])
    overfit_pen = _norm([max(0.0, r.get("train_net_pnl", 0.0) - r.get("oos_net_pnl", 0.0)) for r in rows])
    outlier_pen = _norm([r.get("outlier_dependence", 1.0) for r in rows])

    for i, r in enumerate(rows):
        r["robustness_score"] = (
            0.30 * oos_quality[i]
            + 0.20 * val_consistency[i]
            + 0.15 * (1 - drawdown[i])
            + 0.10 * trade_count[i]
            + 0.10 * profit_factor[i]
            + 0.10 * fee_slip[i]
            + 0.05 * param_stability[i]
            - 0.10 * overfit_pen[i]
            - 0.05 * outlier_pen[i]
        )
    return sorted(rows, key=lambda x: x["robustness_score"], reverse=True)
