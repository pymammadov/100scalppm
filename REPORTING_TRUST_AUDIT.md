# Reporting Trust Audit

## Trustworthy sections/components
1. **MT4 candidate metric recomputation from journals** (`recompute_candidate_metrics_from_journal`) is directionally correct and preferable to trusting aggregate summaries.
2. **Section 6-focused tests** validate row uniqueness and metric consistency against journals.

## Mixed-scope / stale-artifact-prone sections
1. `scripts/build_html_report.py` ingests many optional artifacts (`top5`, summaries, deep dives, comparison markdown) with soft fallbacks.
2. Report can proceed with partial dataset availability, increasing risk of incoherent narrative.
3. Ranking is recomputed in report layer from CSV artifacts that may not align with top5/journal snapshot when outputs are stale/mixed.

## What must be journal-derived
- Candidate-level trade count, win rate, net PnL, return %, drawdown, fee/slippage totals.
- Any "top strategy" claims and per-candidate KPI rows.

## What must never be sourced only from aggregate summaries
- Section-level winner/loser declarations.
- Risk-adjusted metrics if journal exists.
- Trade-behavior metrics (setup/hour/regime performance).

## Required hardening steps
1. Mandatory `run_manifest.json` and run-id consistency check across all consumed artifacts.
2. Fail report build when required journal files for referenced candidates are missing.
3. Add explicit source provenance tag per KPI (`journal`, `backtest_csv`, `derived`).
4. Emit report integrity warnings section with machine-readable validation outcomes.
