# Architecture Refactor Plan

## Immediate fixes (0–2 weeks)
1. **Fail-loud execution contract**
   - Replace broad exception swallow in `run_strategy_factory` with typed exception handling.
   - Emit `evaluation_errors.csv/jsonl` with family_id, stage, traceback hash, message.
   - Stop run when error rate exceeds threshold.

2. **Deterministic generation contract**
   - Remove `hash()`-derived seeds; use stable hash or explicit `--seed`.
   - Persist effective seed and family parameter digest in run manifest.

3. **Run namespace isolation**
   - Output to `outputs/<run_id>/...` only.
   - Require report scripts to consume one run directory + manifest.

4. **Artifact validation gate**
   - Validate required files/columns before report generation.
   - Hard-fail if mandatory artifacts missing/incompatible.

5. **Packaging/test hygiene**
   - Add `pyproject.toml` and installable package config.
   - Ensure `pytest -q` works without custom `PYTHONPATH`.

## Medium-term refactors (2–6 weeks)
1. **Isolate strategy layers**
   - `signal_engine.py`
   - `position_sizing.py`
   - `execution_simulator.py`
   - `metrics_aggregator.py`

2. **Configuration standardization**
   - Central typed config object (Pydantic/dataclasses) for split ratios, costs, ranking weights, filters.
   - Version config schema and embed version in artifacts.

3. **Structured metrics outputs**
   - Replace stringified dict buckets with JSON fields or normalized tables.
   - Add explicit schemas for backtest/robustness/reporting inputs.

4. **Report source-of-truth tightening**
   - Require journal-derived recomputation for candidate comparison and headline KPIs.
   - Allow aggregate CSV only as cache with checksum equivalence checks.

5. **Observability + lineage**
   - Add run manifest with data hash, git SHA, config hash, timestamps, environment summary.

## What to isolate
- Backtest simulation logic from feature engineering.
- Ranking calculation from I/O normalization.
- Report rendering templates from data assembly/validation.

## What to delete
- Legacy permissive file-reading patterns that default to empty without error for required inputs.
- Hardcoded family targets in deep-dive workflow (`TARGET_FAMILIES`).

## What to rewrite
- `src/family_evaluator.py` into layered components.
- Report loader/assembler in both HTML scripts to enforce strict contracts.

## What to standardize
- Run directory structure.
- CLI/config schema.
- Exception/error taxonomy.
- Metric definitions and naming.
- Test data fixtures + deterministic snapshots.
