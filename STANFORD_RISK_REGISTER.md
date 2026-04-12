# STANFORD Risk Register

| Rank | Risk | Severity | Probability | Business Impact | Mitigation |
|---:|---|---|---|---|---|
| 1 | OOS leakage in ranking (OOS metrics used for selection) | Critical | High | Inflated expected alpha; live underperformance | Rank only on train/validation; reserve OOS for final lockbox. |
| 2 | Non-deterministic strategy identity from `hash()` seeding | Critical | High | Same family_id can represent different strategies across runs | Replace with stable seed (`sha256`/fixed RNG seed), persist run manifest. |
| 3 | Capital misrepresentation (fixed 1 BTC vs 10k account) | Critical | High | Return claims economically misleading | Enforce equity/risk-based sizing with leverage caps. |
| 4 | MT4 top-5 inconsistency and incorrect win-rate rendering | High | High | Investor misreporting risk | Build all table metrics from same source-truth journal basis. |
| 5 | HTML report path bug with relative output dir | High | Medium | Pipeline/report failures | Normalize paths to absolute before `relative_to`. |
| 6 | Weak multiple-testing controls | High | High | False discovery / overfit deployment | Add reality check / deflated Sharpe / bootstrap FDR guardrails. |
| 7 | Idealized fills and spot shorting assumptions | Medium | Medium | Live slippage/borrow mismatch | Add realistic execution simulator and venue constraints. |
| 8 | Stale artifact reuse risk | Medium | Medium | Silent contamination of results | Add run_id namespacing + clean-room output policy. |
