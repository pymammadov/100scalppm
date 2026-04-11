# FAM Deep Dive Comparison

- Dataset rows: 50000
- Ranking filter min_trades=20: 112 candidates survive
- Ranking filter min_trades=30: 112 candidates survive

## Candidate Scores (min_trades=20)
- FAM_0053 robustness_score: 0.436189
- FAM_0039 robustness_score: 0.442709

## Deployment Recommendation
**Stronger deployment candidate: FAM_0039**

Decision basis: higher robustness score under the stricter trade-count discipline (min_trades=20) while both families remain in-scope for deep dive.