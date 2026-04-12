# STANFORD Institutional Red-Team Audit Report

## Executive Verdict
**FAIL CRITICAL — results not trustworthy.**

Primary objective classification: **B/C (leaning C)**. Some arithmetic pathways are internally coherent, but investor-facing performance claims are materially compromised by accounting semantics, reporting inconsistency, OOS contamination, and reproducibility failures.

## Critical Findings
1. **Capital story is economically misleading (Critical).**
   - Engine labels starting capital as 10,000 USD but trades fixed `qty=1.0` BTC per position, independent of equity and independent of `risk_per_trade`.
   - On the selected top-candidate journal, average entry notional is about 39.6k USD, i.e., ~3.96x the stated capital baseline.
2. **Report consistency defects (Critical).**
   - MT4 section 6 mixes OOS PnL with all-split trade counts from `family_backtest_results.csv`.
   - MT4 section 6 win-rate is `0.00%` for non-selected top-5 candidates due to report logic, despite positive real win-rates in journals.
3. **Deep-dive contradictions for same family IDs (Critical).**
   - `FAM_0039` and `FAM_0053` deep-dive OOS results disagree with strategy-factory outputs for same IDs.
   - Root cause: family generation seeds random from Python `hash(...)`, which is process-randomized.
4. **OOS governance failure (Critical).**
   - Ranking score directly uses OOS metrics (`oos_expectancy`, `oos_net_pnl`), contaminating OOS as a selection target.
5. **Reproducibility fragility (High).**
   - `build_html_report.py` fails for relative output paths (`Path(tf).relative_to(ROOT)` on relative paths).
   - Family IDs are not stable across processes due to hash-seeded randomization.
6. **Economic realism is idealized (High).**
   - Simplified bar-based fill logic, no intrabar sequence disambiguation, no venue-level borrow constraints while shorting may be present.

## Priority-by-Priority Assessment

### PRIORITY 1 — Capital and Accounting Integrity
- **Did the repo really turn 10,000 into reported ending equity?**
  - **Arithmetic answer:** yes, selected-journal ending equity equals `10000 + net_pnl`.
  - **Economic answer:** **no**, because PnL is generated with fixed 1 BTC sizing regardless of account size, so the 10k anchor is not an enforced capital constraint.
- `ending_equity = starting_capital + net_pnl` is mathematically consistent in core summarization and selected-journal MT4 header.
- Drawdown calculations vary by artifact/sign convention and split basis.

### PRIORITY 2 — Report Consistency Audit
- Consistency matrix produced: `STANFORD_CONSISTENCY_MATRIX.csv`.
- Explicit mismatches:
  - Top-5 trade counts: all-split counts shown next to OOS-only net profits.
  - Top-5 win-rate: non-selected rows incorrectly rendered as 0.00%.
  - Deep-dive and strategy-factory metrics conflict for same family IDs.

### PRIORITY 3 — Data and Split Governance
- Split method is chronological 60/20/20.
- **OOS is not clean** because OOS metrics are inputs to ranking score.
- Leakage risk: **High**.
- “Top candidate” is top-ranked under implemented rules, but those rules are contaminated.

### PRIORITY 4 — Multiple Testing / Selection Bias
- Broad hypothesis search across many generated families.
- No formal multiple-testing corrections (e.g., deflated Sharpe / White reality check / FDR controls).
- Controls assessment: **effectively none**.

### PRIORITY 5 — Trade Journal Reality Check
- Recomputed from raw journals for top-5 candidates:
  - Net PnL, gross profit/loss, PF, ending equity generally match OOS fields.
  - MT4 comparison table still contains structural inconsistencies (trade counts and win-rate column logic).

### PRIORITY 6 — Economic Plausibility
- Backtest is only plausible under idealized execution and unconstrained synthetic leverage assumptions.
- For live deployment on BTCUSDT spot, current assumptions are not sufficiently realistic.

### PRIORITY 7 — Software Engineering / Reproducibility
- Non-deterministic family IDs across processes.
- Relative-path bug in HTML builder.
- Risk of stale artifact mixing if output directories are reused.

## Scoring (0–100)
- Mathematical correctness: 68
- Accounting correctness: 22
- Report consistency: 28
- OOS cleanliness: 18
- Anti-overfitting discipline: 10
- Economic realism: 24
- Reproducibility: 20
- Investor readiness: 12

Overall weighted score: **25.26 / 100**.

## Final Recommendation
- **No capital allocation.**
- If continued: remediation sprint, then independent re-audit before even paper-trade escalation.

## BOTTOM-LINE TRUTH
1. **What is actually true here?** Core trade-level arithmetic can be internally consistent for a fixed-qty toy simulation.
2. **What is likely exaggerated or broken?** The “10,000 USD turned into X” narrative is economically overstated by implicit leverage; OOS governance is contaminated; reporting has contradictions and outright incorrect fields.
3. **Would a serious investor put money into this today?** **No.**
