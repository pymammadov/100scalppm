# Technical Due Diligence Report

## Executive Technical Verdict

**Verdict: TECHNICALLY SALVAGEABLE BUT IMMATURE.**

This repository shows real engineering intent (modular Python package in `src/`, deterministic family IDs, meaningful robustness scoring, and tests for specific report consistency constraints). However, it is not yet institutional-grade. The two largest trust problems are:

1. **Silent error swallowing in core evaluation loop** (`src/strategy_factory.py`) that can hide correctness failures while still producing polished outputs.
2. **Reproducibility instability from Python hash-based randomness** (`src/family_generator.py`) that can change strategy parameters across processes/machines.

The codebase is materially better than a toy script bundle, but still fragile for high-stakes decision use without architectural hardening.

---

## A) Repository Structure Findings

### What is good
- Clear top-level split: `src/`, `scripts/`, `tests/`.
- Core logic mostly lives in `src/`; CLI/report orchestration in `scripts/`.
- Tests exist and are focused on critical output behavior (e.g., section rendering and metric recomputation).

### What is weak
- Root contains many generated-looking diligence artifacts (`AUDIT_REPORT.md`, `STANFORD_*`, scorecards, memos) without clear separation between source and derived outputs. **Maintainability issue.**
- Output namespace discipline is inconsistent: scripts default to `outputs/`, while tests also write into `outputs/` under repo root (`tests/test_strategy_factory_smoke.py`). **Reproducibility + operability issue.**
- No formal packaging metadata (`pyproject.toml` / requirements lock), causing ambiguous environment setup. **Environment robustness issue.**

### Assessment
Structure is **workable**, but not yet the shape of a controlled research platform with cleanly segregated artifacts and environment contracts.

---

## B) Core Architecture Findings

### Positive signals
- Strategy generation, evaluation, robustness, ranking, and reporting are split into separate modules (`src/family_generator.py`, `src/family_evaluator.py`, `src/robustness.py`, `src/ranking.py`, `src/reporting.py`).
- `run_strategy_factory()` orchestrates pipeline in one place, which is easier to reason about than deeply fragmented script chains.

### Critical weaknesses
1. **Overloaded evaluator responsibilities** (`src/family_evaluator.py`): indicator prep, signal logic, sizing, execution simulation, and trade summarization are all in one module with long procedural flow. **Maintainability + correctness risk.**
2. **Dead/ignored config dimensions**: parameters like `exit_block`, `lookback`, `rsi_len`, `rsi_band`, `ema_fast`, `ema_slow`, etc., are generated but largely not honored by execution logic. This creates a **false architecture of configurability** and can mislead users about search-space coverage. **Audit-blocking correctness issue.**
3. **Reporting stack mixes recomputation and artifact reads** (`scripts/build_html_report.py`, `scripts/build_mt4_html_report.py`) with broad silent fallbacks. This is presentation-oriented rather than source-of-truth constrained. **Reporting integrity issue.**

---

## C) Data and Pipeline Integrity

### Strengths
- Required OHLCV schema is validated on ingest (`_read_csv_rows` enforces mandatory columns).
- Pipeline stages are explicit: ingest → feature prep → split → backtest → robustness → rank → artifacts.

### Failures / risks
1. **Silent family drop on any exception** in main loop (`except Exception: failure_counts["evaluation_error"] += 1`), no stack trace, no per-family error log. Wrong outputs can be emitted with understated failure context. **Audit-blocking issue.**
2. **Potential stale artifact contamination**: cleaning only `top5_trade_journals` and `top5_equity_curves`, but leaving other outputs untouched, then report builders auto-read whatever exists in output dir. **Reproducibility + auditability issue.**
3. **Stringified dict metrics** (`pnl_by_*` as `str(dict)`) create lossy, parser-fragile handoff across modules. **Correctness + maintainability issue.**

Pipeline is not yet trustworthy as an immutable lineage chain.

---

## D) Reproducibility / Determinism

### Key breakpoints
1. **Non-deterministic parameter generation due to `hash()`** seed source in `_base_params()` (`src/family_generator.py`). Python hash randomization varies by process unless `PYTHONHASHSEED` fixed. **Primary reproducibility failure.**
2. **No run manifest with config+code hash+data fingerprint**; reruns cannot be proven equivalent. **Auditability failure.**
3. **No deterministic artifact namespace** (timestamp/run-id) by default; repeated runs overwrite shared `outputs/`. **Operational reproducibility failure.**
4. **Path-dependent imports** via `sys.path.append` in scripts. Works ad hoc, not robustly reproducible across execution contexts. **Environment fragility.**

Institutional reproducibility is currently **insufficient**.

---

## E) Testing Quality

### What is good
- 11 tests passing under proper path configuration.
- Specific assertions on report section consistency and journal-derived candidate metrics are meaningful and not purely superficial smoke tests.
- Capital sizing and leverage-cap logic have explicit unit-style tests.

### Gaps
1. **Test invocation not robust from clean env**: `pytest -q` fails with `ModuleNotFoundError: src` unless `PYTHONPATH=.`, indicating packaging/test harness weakness.
2. **No golden tests for full end-to-end deterministic rerun.**
3. **No failure-path tests for malformed CSV values / NaNs / timestamp anomalies.**
4. **No tests proving generated parameter fields are actually consumed by execution.**

Current suite is **targeted but narrow**; insufficient for audit-grade trust.

---

## F) Error Handling / Failure Modes

1. Broad `except Exception` patterns in report readers return empty/null silently (`scripts/build_html_report.py`, `scripts/build_mt4_html_report.py`). This can degrade reports without failing loud. **False-confidence risk.**
2. Core pipeline catches all family-level exceptions and continues without diagnostic payload. **High correctness risk.**
3. Assertions inside report scripts act as sanity checks but are not substitutes for explicit exception taxonomy + structured logs. **Operability weakness.**

The system can produce credible-looking output while hiding substantive execution failures.

---

## G) Reporting Integrity

### Positive
- MT4 report path includes explicit recomputation from trade journals for candidate metrics (`recompute_candidate_metrics_from_journal`), which is directionally correct.

### Material issues
1. HTML reporting consumes mixed artifacts (CSV, JSON, Markdown, deep-dive files) with optional presence; this enables mixed-scope summaries and stale blend risk.
2. Numerous soft-fail loaders (`read_json/read_csv/read_text` returning empty) make missing inputs appear as normal data sparsity.
3. Some fields derive from aggregate tables, while others recompute from journals, without strict source-of-truth contract.

Reporting is currently **presentation-grade with pockets of engineering-grade logic**.

---

## H) Configuration / CLI Discipline

- CLI exists for key workflows and includes core knobs (`--n-families`, `--min-trades`, `--initial-capital`).
- But important behavior remains hardcoded:
  - train/validation/oos split ratios,
  - stress multipliers,
  - ranking weights,
  - minimum trade thresholds in report scripts (`min_trades=20` embedded).
- No central schema-driven config layer.

Configuration discipline is **partial and fragmented**.

---

## I) Environment / Dependency Robustness

- No pinned dependency file or lock.
- No package install flow.
- Reliance on `sys.path.append` hacks.
- Test import behavior inconsistent without environment variable adjustments.

Another engineer can run it, but only with implicit Python path knowledge.

---

## J) Maintainability / Scalability

### Good
- Module boundaries exist and are understandable.
- Naming is mostly coherent.

### Scaling bottlenecks
1. Large procedural report scripts will become brittle with added report variants.
2. Strategy evaluator mixes concerns, making any new execution model high-risk.
3. Parameter-space inflation without true semantic use leads to deceptive complexity.

Team maintainability: **moderate in short term, poor at scale without refactor**.

---

## Major Technical Risks (Highest Priority)

1. Silent exception swallowing in core backtest loop.
2. Non-deterministic family generation from Python hash randomization.
3. Artifact contamination due to shared `outputs/` and partial cleanup.
4. Report stack permissive reads producing plausible but incomplete narratives.
5. Generated parameter schema not faithfully executed (illusion of model breadth).

---

## Final Engineering Recommendation

Proceed only with a **stabilization phase before further feature work**:
1. Deterministic run engine (stable seed, run manifest, run-scoped output dirs).
2. Hard-fail error policy for missing/invalid critical artifacts.
3. Refactor evaluator into clear layers: signal generation, risk/sizing, execution, metrics.
4. Replace stringified dict payloads with typed JSON columns or normalized tables.
5. Build audit test pack: deterministic rerun snapshot + data corruption + stale artifact checks.

Without these, this repo remains unsuitable for high-stakes reliance.

---

## BOTTOM-LINE TECHNICAL JUDGMENT

1. **Is this codebase technically primitive?**
   - Not purely primitive; it is **technically salvageable but immature**.
2. **Most dangerous flaw?**
   - **Silent exception swallowing during family evaluation** in `run_strategy_factory()` because it can mask broken logic while still producing rankings/reports.
3. **Single highest-leverage fix?**
   - Implement a **deterministic, fail-loud run contract**: stable seed mechanism + per-family structured error logs + run manifest + run-id namespaced artifacts.
4. **Can a serious team build on this or partially rebuild?**
   - A serious team can build on it, but should **partially rebuild core orchestration and reporting contracts** before scaling.
5. **Trustworthy enough today for high-stakes use?**
   - **No.** It is not currently trustworthy for high-stakes deployment or investment-grade technical confidence.
