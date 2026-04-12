# AUDIT_REPORT — 100scalppm Investor-Grade Due Diligence

Date: 2026-04-12 (UTC)
Branch: `investor-audit`
Auditor stance: skeptical, evidence-first, investor-protective.

## Executive Summary

**Verdict:** This repository is a **promising but immature prototype** and should be treated as **research-only**, not capital-ready.

The project demonstrates a coherent strategy-factory workflow (generation → backtest → robustness checks → ranking → reporting), but key constraints prevent investor-grade credibility today:

1. **Data realism is weak**: bundled datasets are synthetic and very short-horizon; conclusions are not grounded in true BTCUSDT exchange data.
2. **Selection-risk is high**: many variants are tested, but there is no explicit multiple-testing correction / false-discovery control.
3. **Top candidates are not diverse**: current top-5 are mostly parameter tweaks on one breakout skeleton, creating concentration risk.
4. **Execution realism is incomplete**: simple bps fee/slippage model is directionally useful but does not capture queue position, latency, partial fills, spread state, or impact.
5. **Reporting consistency is mixed across artifact sets**: current top-5 ranking is internally consistent, but deep-dive recommendation files can point to families outside the live top list.

**Recommendation:** **Conditional further research** (strictly non-investment) with a mandatory hardening plan before any paper-trading promotion.

---

## 1) What the repository is

This is a **hybrid strategy-factory research repo**. It programmatically generates strategy families, runs split backtests, applies lightweight robustness stress tests, ranks candidates with a composite score, and exports top-5 artifacts plus HTML reporting.

- Core factory and orchestration: `src/strategy_factory.py`.
- Strategy simulation and feature engineering: `src/family_evaluator.py`.
- Candidate generator and family taxonomy: `src/family_generator.py`, `src/family_definitions.py`.
- Ranking logic: `src/ranking.py`.
- Robustness stress module: `src/robustness.py`.
- Outputs and report builder: `src/reporting.py`, `scripts/build_html_report.py`.

## 2) Reproducibility assessment

### What reproduced successfully
- Unit smoke tests run and pass when explicitly targeted.
- End-to-end factory run reproduces 120 generated/evaluated families.
- Deep-dive candidate script runs and outputs comparison artifacts.
- HTML report regeneration succeeds.

### Reproducibility caveats
- Plain `python -m unittest -v` discovers **0 tests**, so default test execution gives a false sense of test coverage.
- Results are tied to synthetic sample generators and local CSV artifacts, not institutional-grade market datasets.

## 3) Ranking engine and top-candidate consistency (priority audit)

### Formula and gating
Ranking is a normalized composite over OOS quality, split consistency, drawdown, trade count, OOS PF, fee/slippage stress, parameter stability, plus penalties for overfit gap and outlier dependence.

**Critical observation:** min-trade gating is applied on **total trades across train+validation+OOS**, not strictly OOS trades. This can admit candidates with acceptable aggregate activity but weaker OOS evidence in other datasets.

### Consistency findings
- For current `outputs/`, recomputed ranking top-5 IDs exactly match `top5_strategies.json`.
- HTML builder includes explicit assertions to enforce top-card vs leaderboard consistency.

### Artifact inconsistency risk
- `fam_comparison.md` recommends FAM_0039 vs FAM_0053 from a separate deep-dive path, while top-5 production cards are FAM_0108/FAM_0084/etc. This is not necessarily wrong, but can mislead investor audiences if not clearly versioned by run context.

## 4) Statistical validity assessment

### Strengths
- Proper chronological split function (`60/20/20`) exists and is consistently used.
- Basic perturbation and stress tests are present.

### Weaknesses
1. **Multiple testing / data-mining risk not addressed**:
   - 120 families are screened and the best are promoted without formal deflation (e.g., PBO/White Reality Check/FDR controls).
2. **No uncertainty quantification**:
   - No confidence intervals, bootstrapped stability ranges, or post-selection inference.
3. **Outlier sensitivity is only lightly penalized**:
   - Outlier dependence metric exists, but no robust inferential threshold is enforced.
4. **Sample adequacy is weak for intraday BTC claims**:
   - Included sample data spans only days/weeks; not enough regime breadth for robust inference.

## 5) Economic and execution validity assessment

### Plausibility
The hypotheses (breakout, reversion, VWAP reclaim, session effects) are economically plausible at a high level.

### Execution realism gaps
- Cost model uses fixed fee/slippage bps and unit size, but omits:
  - spread-state conditional fills,
  - queue priority/latency,
  - partial fills,
  - market impact nonlinearities,
  - exchange/mode specific fee tiers and funding nuances.

### Friction sensitivity (important)
Top candidates show large no-cost vs cost differences, indicating edge is fragile to frictions. Elevated-fee and elevated-slippage stress often remove substantial OOS PnL, highlighting thin margin of safety.

## 6) Candidate diversity assessment

Current top-5 are heavily concentrated in the same structural template:
- `range_breakout` entry,
- `fixed_stop_fixed_tp` exit,
- `uptrend_only` gating,
with only parameter/confirmation variations.

This is **not broad hypothesis diversification**; it is largely local parameter clustering around a single motif.

## 7) Software and engineering validity

### Positives
- Modular architecture, readable separation by concerns.
- Deterministic family IDs and organized artifact output.
- Self-contained report generation.

### Concerns
- Exception swallowing in family evaluation loop can hide critical failures (`except Exception: ...`).
- Test discovery ergonomics are weak (`unittest` default run finds none).
- No explicit dependency lock / environment spec for institutional reproducibility.
- Report layer combines artifacts from potentially different runs unless provenance is tightly controlled.

## 8) Answers to primary investor questions

1. **Economic plausibility?**
   - Plausible motifs exist, but current evidence could still be parameterized noise-mining.
2. **Backtests sound?**
   - Mechanically coherent, but not institutionally sufficient; missing execution realism and inference rigor.
3. **Train/val/OOS genuine?**
   - Chronological split is genuine in code, yes.
4. **Fees/slippage realistic for BTC scalp?**
   - Too simplified for deployment decisions.
5. **Ranking robust or lucky survivor?**
   - Better than naive ranking, but still exposed to survivor bias and data-mining risk.
6. **Top candidates differentiated?**
   - Mostly minor variants of same skeleton.
7. **Edge before costs vs after frictions?**
   - Appears materially reduced by costs; robustness margin is not convincing.
8. **Software architecture reproducible?**
   - Adequate for research iteration, not yet institutional-grade reproducibility.
9. **Investor-presentable today?**
   - Presentable only as exploratory R&D, not as allocatable strategy product.
10. **Blocks to allocation now?**
   - Synthetic/limited data, weak inferential controls, execution realism gaps, and concentration of purported edge.

## 9) Scoring (0–10 each)

- Economic plausibility: **5.0**
- Statistical rigor: **3.0**
- Backtest integrity: **5.5**
- OOS credibility: **3.5**
- Cost realism: **3.0**
- Software quality: **6.0**
- Reproducibility: **6.0**
- Reporting integrity: **5.5**
- Investor readiness: **2.5**
- Research asset value: **6.0**

**Overall weighted score:** **46/100**

Confidence: **Medium** (high confidence on current code/artifact limitations; lower confidence on latent alpha because data realism is insufficient).

## 10) Final recommendation

**Recommendation category: `Conditional further research`**

Not capital-ready. Do not allocate pilot capital yet. Permit controlled additional research budget only if the next milestones are met.

## 11) Next 3 most important paid research steps

1. **Data and execution realism hardening**
   - Replace synthetic sample inference with real BTCUSDT L2/L1 data, exchange-specific fees, spread regime model, and latency-aware execution simulator.
2. **Statistical defense against false discovery**
   - Add multiple-testing corrections, post-selection validation, block bootstrap CIs, and walk-forward / rolling OOS.
3. **Diversity and robustness governance**
   - Enforce hypothesis-class diversification quotas in shortlist, add cross-regime stability gates, and require OOS trade-count minimums independent of train/val.
