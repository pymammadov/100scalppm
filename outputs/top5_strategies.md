# Top 5 Robust Strategies

## 1. FAM_0032 (failed_breakdown_fade)
- Name: failed_breakdown_fade_range_breakout_fixed_stop_fixed_tp_0032
- Rules: failed_breakdown_fade using range_breakout, confirmed by range_percentile, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.6686, OOS pnl=282.59, validation pnl=137.18, trades=27.

## 2. FAM_0088 (short_only_bear_regime)
- Name: short_only_bear_regime_range_breakout_fixed_stop_fixed_tp_0088
- Rules: short_only_bear_regime using range_breakout, confirmed by rsi_filter, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.6158, OOS pnl=236.71, validation pnl=241.02, trades=17.

## 3. FAM_0007 (breakdown_scalp)
- Name: breakdown_scalp_range_breakout_fixed_stop_fixed_tp_0007
- Rules: breakdown_scalp using range_breakout, confirmed by rsi_filter, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5463, OOS pnl=361.77, validation pnl=-3.22, trades=50.

## 4. FAM_0056 (session_open_impulse)
- Name: session_open_impulse_range_breakout_fixed_stop_fixed_tp_0056
- Rules: session_open_impulse using range_breakout, confirmed by rsi_filter, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5237, OOS pnl=138.18, validation pnl=-3.22, trades=51.

## 5. FAM_0009 (breakdown_scalp)
- Name: breakdown_scalp_range_breakout_fixed_stop_fixed_tp_0009
- Rules: breakdown_scalp using range_breakout, confirmed by atr_filter, gated by uptrend_only, exited via fixed_stop_fixed_tp.
- Rationale: Robust score=0.5204, OOS pnl=1327.74, validation pnl=981.80, trades=85.
