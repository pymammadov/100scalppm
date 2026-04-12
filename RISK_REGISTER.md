# RISK_REGISTER

| risk | category | severity | evidence | mitigation | status |
|---|---|---:|---|---|---|
| Synthetic / short-horizon data drives conclusions | Data validity | High | Sample files are generated-style and span only days/weeks | Use real exchange historical + forward feeds, expand regimes | Later |
| Multiple-testing false discovery | Statistical inference | High | 120 families ranked, no formal post-selection correction | Add FDR/PBO/Reality Check + nested walk-forward | Later |
| Top-5 concentration in one strategy skeleton | Portfolio construction | High | Top candidates share breakout/uptrend/fixed-stop structure | Enforce hypothesis diversification constraints in shortlist | Later |
| Execution model under-specification | Market microstructure | High | Fixed bps model only; no queue/latency/partial fills/impact | Build event-driven execution simulator with spread/latency states | Later |
| OOS evidence gate tied to total trade count | Methodology | Medium | `min_trades` uses aggregated train+val+OOS count | Add separate OOS minimum trade-count gate | Later |
| Silent failure masking in evaluation loop | Software reliability | Medium | broad exception capture increments counter only | Log and surface stack traces, fail fast on repeated errors | Now |
| Test discoverability weak | Engineering process | Medium | default unittest run reports 0 tests | standardize test runner (pytest or explicit discovery config) | Now |
| Report narrative drift across artifacts | Reporting integrity | Medium | deep-dive recommendation can diverge from top5 artifacts | Add run-id provenance and consistency checks across all outputs | Now |
| No dependency lockfile | Reproducibility | Medium | No pinned environment file in repo root | Add requirements/poetry/uv lock and CI reproducibility job | Now |
| Cost-sensitive edge may collapse | Investment risk | High | top families lose large PnL under higher fees/slippage | require robust profitability under conservative friction bands | Later |
