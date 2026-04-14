# Test Gap Analysis

## What is currently tested
- Smoke execution and minimum-trade filtering (`tests/test_strategy_factory_smoke.py`).
- Capital sizing/leverage cap behaviors (`tests/test_capital_realism.py`).
- MT4 section 6 rendering uniqueness and recomputed metric consistency (`tests/test_mt4_section6_rendering.py`, `tests/test_mt4_section6_consistency.py`).

## What is missing
1. Deterministic rerun test: same seed+data must reproduce identical family catalog/backtest/ranking.
2. Artifact integrity test: stale files from prior run must be rejected.
3. Failure-path tests: malformed CSV values, missing columns, timestamp parse anomalies.
4. Contract test: every generated parameter dimension must affect execution or be absent from schema.
5. Report strictness tests: required artifacts missing should hard-fail, not silently degrade.
6. Ranking invariance tests against known fixture datasets.
7. End-to-end lineage test asserting manifest consistency across all generated artifacts.

## What should be tested first (highest priority)
1. **Reproducibility snapshot test** (blocking trust).
2. **Silent failure prevention test** for evaluation loop.
3. **Stale artifact contamination test** for report builders.
4. **Parameter-consumption contract test** across generator/evaluator boundary.

## Mandatory tests for audit-grade trust
- `test_deterministic_family_generation_with_seed`
- `test_full_pipeline_replay_bitwise_equivalent_outputs`
- `test_report_generation_fails_on_missing_required_artifacts`
- `test_report_generation_rejects_cross_run_mixed_artifacts`
- `test_generated_parameter_schema_matches_evaluator_consumption`
- `test_run_manifest_matches_all_artifact_hashes`
