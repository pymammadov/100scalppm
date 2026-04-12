# STANFORD Investor Memo (Red-Team)

## What is real
- Selected-candidate journal arithmetic ties out mechanically (`ending_equity = 10,000 + net_pnl`).
- Several top-5 OOS journals are profitable on the sample used.

## What is uncertain
- OOS credibility is weak because OOS metrics are used directly in candidate ranking.
- Statistical significance is uncertain under large hypothesis search without strong false-discovery controls.

## What is broken
- 10,000 USD capital narrative is economically misleading: engine uses fixed 1 BTC position sizing regardless of equity.
- MT4 section 6 contains inconsistent fields (mixed trade-count basis) and incorrect win rates for non-selected candidates.
- Deep-dive outputs can disagree with strategy-factory outputs for same family IDs due to non-deterministic generation.

## Allocation Recommendation
**Do not allocate capital now.**

Status: **FAIL CRITICAL — results not trustworthy for institutional deployment.**
