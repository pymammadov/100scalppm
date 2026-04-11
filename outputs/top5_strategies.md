# Top 5 Robust Strategies

## 1. FAM_0108 (short_only_bear_regime)
- Name: short_only_bear_regime_range_breakout_fixed_stop_fixed_tp_0108
- Rules: short_only_bear_regime using range_breakout, confirmed by range_percentile, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5283, OOS pnl=4120.90, validation pnl=2900.55, trades=1059.

## 2. FAM_0084 (liquidity_sweep_reclaim)
- Name: liquidity_sweep_reclaim_range_breakout_fixed_stop_fixed_tp_0084
- Rules: liquidity_sweep_reclaim using range_breakout, confirmed by range_percentile, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5192, OOS pnl=10123.84, validation pnl=9053.68, trades=929.

## 3. FAM_0043 (vwap_reversion)
- Name: vwap_reversion_range_breakout_fixed_stop_fixed_tp_0043
- Rules: vwap_reversion using range_breakout, confirmed by vwap_distance, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5040, OOS pnl=3292.38, validation pnl=3148.08, trades=875.

## 4. FAM_0077 (trend_reentry_scalp)
- Name: trend_reentry_scalp_range_breakout_fixed_stop_fixed_tp_0077
- Rules: trend_reentry_scalp using range_breakout, confirmed by session_filter, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5036, OOS pnl=3188.00, validation pnl=3307.51, trades=300.

## 5. FAM_0067 (session_open_impulse)
- Name: session_open_impulse_range_breakout_fixed_stop_fixed_tp_0067
- Rules: session_open_impulse using range_breakout, confirmed by vwap_distance, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5025, OOS pnl=4309.28, validation pnl=4131.30, trades=829.
