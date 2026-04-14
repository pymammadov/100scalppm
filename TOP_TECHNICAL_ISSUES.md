# Top 20 Technical Issues

1. **Issue:** Silent exception swallowing in family evaluation loop  
   **File/module:** `src/strategy_factory.py`  
   **Severity:** Critical  
   **Category:** audit-blocking issue  
   **Why it matters:** Failed strategies disappear from outputs without diagnostics; rankings can look valid while logic is broken.  
   **Recommended fix:** Catch specific exceptions, emit structured per-family error logs with traceback, and fail run if failure ratio exceeds threshold.  
   **Effort estimate:** 1–2 days  
   **Blocks trust:** Yes

2. **Issue:** Non-deterministic generation using Python `hash()` seeds  
   **File/module:** `src/family_generator.py`  
   **Severity:** Critical  
   **Category:** reproducibility issue  
   **Why it matters:** Same nominal config can yield different strategy params across processes/machines.  
   **Recommended fix:** Replace with stable hash (e.g., SHA-256) or explicit seeded RNG stream.  
   **Effort estimate:** <1 day  
   **Blocks trust:** Yes

3. **Issue:** Generated parameters not actually consumed by evaluator (`exit_block`, etc.)  
   **File/module:** `src/family_generator.py`, `src/family_evaluator.py`  
   **Severity:** High  
   **Category:** correctness issue  
   **Why it matters:** Search-space appears broad but execution semantics are narrow; misleads performance interpretation.  
   **Recommended fix:** Implement all generated parameter dimensions or remove unsupported fields from generation/catalog.  
   **Effort estimate:** 3–7 days  
   **Blocks trust:** Yes

4. **Issue:** Shared mutable `outputs/` namespace without run isolation  
   **File/module:** `scripts/*.py`, `src/strategy_factory.py`  
   **Severity:** High  
   **Category:** reproducibility issue  
   **Why it matters:** Fresh and stale artifacts can mix, contaminating report conclusions.  
   **Recommended fix:** Mandatory run-id directory and manifest pointer to exact input/output lineage.  
   **Effort estimate:** 1–2 days  
   **Blocks trust:** Yes

5. **Issue:** Soft-fail file readers hide missing/invalid inputs  
   **File/module:** `scripts/build_html_report.py`, `scripts/build_mt4_html_report.py`  
   **Severity:** High  
   **Category:** failure-mode issue  
   **Why it matters:** Reports can be silently incomplete with no hard error.  
   **Recommended fix:** Fail hard on required artifacts; distinguish optional sections explicitly in report metadata.  
   **Effort estimate:** 1 day  
   **Blocks trust:** Yes

6. **Issue:** Test suite fails in default invocation (`pytest -q`) due to import path assumptions  
   **File/module:** `tests/`, project packaging  
   **Severity:** Medium  
   **Category:** environment robustness issue  
   **Why it matters:** Fresh environments fail quickly; weak dev ergonomics and CI stability.  
   **Recommended fix:** Add package config (`pyproject.toml`) and editable install or pytest path config.  
   **Effort estimate:** <1 day  
   **Blocks trust:** No

7. **Issue:** Stringified dict metrics (`pnl_by_*`)  
   **File/module:** `src/family_evaluator.py`, `scripts/run_deep_dive_candidates.py`  
   **Severity:** Medium  
   **Category:** maintainability issue  
   **Why it matters:** Parsing is brittle and type-unsafe across modules.  
   **Recommended fix:** Store JSON-encoded objects or normalized child tables.  
   **Effort estimate:** 1–2 days  
   **Blocks trust:** No

8. **Issue:** Ranking weights hardcoded with no config/versioning  
   **File/module:** `src/ranking.py`  
   **Severity:** Medium  
   **Category:** auditability issue  
   **Why it matters:** Score behavior changes are hard to govern and compare historically.  
   **Recommended fix:** Externalize score config and persist ranking formula version in outputs.  
   **Effort estimate:** 1 day  
   **Blocks trust:** No

9. **Issue:** Split logic hardcoded 60/20/20 without validation safeguards  
   **File/module:** `src/family_evaluator.py`  
   **Severity:** Medium  
   **Category:** correctness issue  
   **Why it matters:** Small datasets can create weak splits and unstable metrics.  
   **Recommended fix:** Configurable splits with minimum sample guards and leakage checks.  
   **Effort estimate:** 1 day  
   **Blocks trust:** No

10. **Issue:** Broad `sys.path.append` script import pattern  
    **File/module:** `scripts/*.py`  
    **Severity:** Medium  
    **Category:** environment robustness issue  
    **Why it matters:** Execution depends on cwd/script path context rather than package install semantics.  
    **Recommended fix:** Package project and run via console entry points/module execution.  
    **Effort estimate:** 1 day  
    **Blocks trust:** No

11. **Issue:** Partial artifact cleanup only for top5 folders  
    **File/module:** `src/strategy_factory.py`  
    **Severity:** Medium  
    **Category:** reproducibility issue  
    **Why it matters:** Old summary/deep-dive files may persist and be misread as current.  
    **Recommended fix:** Write to new run directory or implement full output snapshot replacement.  
    **Effort estimate:** <1 day  
    **Blocks trust:** Yes

12. **Issue:** No explicit schema validation for loaded CSV numeric fields beyond coercion  
    **File/module:** report scripts  
    **Severity:** Medium  
    **Category:** correctness issue  
    **Why it matters:** Bad data coerces to defaults and can mask corruption.  
    **Recommended fix:** Introduce pydantic/dataclass schema validation with strict mode.  
    **Effort estimate:** 2–3 days  
    **Blocks trust:** Yes

13. **Issue:** No dependency lockfile / constraints  
    **File/module:** repository root  
    **Severity:** Medium  
    **Category:** reproducibility issue  
    **Why it matters:** Environment drift can change results or break execution.  
    **Recommended fix:** Add pinned lock (pip-tools/uv/poetry) and CI verification.  
    **Effort estimate:** 1 day  
    **Blocks trust:** No

14. **Issue:** Evaluator module complexity too high (signals + execution + metrics together)  
    **File/module:** `src/family_evaluator.py`  
    **Severity:** Medium  
    **Category:** maintainability issue  
    **Why it matters:** Modifying one concern risks regressions in others.  
    **Recommended fix:** Split into signal engine, execution simulator, risk sizing, and analytics modules.  
    **Effort estimate:** 3–5 days  
    **Blocks trust:** No

15. **Issue:** No run-level provenance metadata (code revision, input digest, params)  
    **File/module:** orchestration layer  
    **Severity:** High  
    **Category:** auditability issue  
    **Why it matters:** Impossible to prove which exact code/data generated a report.  
    **Recommended fix:** Emit `run_manifest.json` with git SHA, config hash, input checksums, timestamps.  
    **Effort estimate:** 1 day  
    **Blocks trust:** Yes

16. **Issue:** Assertions in production report generation paths  
    **File/module:** `scripts/build_html_report.py`  
    **Severity:** Low  
    **Category:** maintainability issue  
    **Why it matters:** `python -O` can disable assertions; behavior changes silently.  
    **Recommended fix:** Replace with explicit validation exceptions.  
    **Effort estimate:** <1 day  
    **Blocks trust:** No

17. **Issue:** Deep-dive script hardcodes target family IDs  
    **File/module:** `scripts/run_deep_dive_candidates.py`  
    **Severity:** Medium  
    **Category:** scalability issue  
    **Why it matters:** Not generalizable; brittle when family universe changes.  
    **Recommended fix:** Choose targets from ranking output via CLI selectors.  
    **Effort estimate:** <1 day  
    **Blocks trust:** No

18. **Issue:** Default sample generation in production script context  
    **File/module:** `scripts/run_strategy_factory.py`  
    **Severity:** Low  
    **Category:** operability issue  
    **Why it matters:** Synthetic data path can blur line between real and demo runs.  
    **Recommended fix:** Separate demo workflow and force explicit flagging in manifests/reports.  
    **Effort estimate:** <1 day  
    **Blocks trust:** No

19. **Issue:** Lack of CI-visible static typing/lint checks  
    **File/module:** repository-wide  
    **Severity:** Low  
    **Category:** maintainability issue  
    **Why it matters:** Type regressions and style drift accumulate.  
    **Recommended fix:** Add `ruff` + `mypy/pyright` + CI gates.  
    **Effort estimate:** 1 day  
    **Blocks trust:** No

20. **Issue:** No explicit stale-artifact detection in report generation  
    **File/module:** report scripts  
    **Severity:** High  
    **Category:** audit-blocking issue  
    **Why it matters:** Report may blend mismatched run epochs undetected.  
    **Recommended fix:** Verify all source artifacts share same run-id + manifest hash before rendering.  
    **Effort estimate:** 1–2 days  
    **Blocks trust:** Yes
