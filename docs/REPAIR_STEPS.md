# Bounded repairs after the external review

Steps 1 and 2 are complete. Step 2 measured 20 native fixed-fit forecast batches,
with zero refits, and now includes an exact development-input bundle restored
from GitHub. See [forecast repeatability](FORECAST_REPEATABILITY.md). Later steps
require their own bounded task, measured result and decision; no evolutionary
campaign starts automatically.

| Step | Question or defect | Boundary / stopping condition |
|---|---|---|
| **1. Explicit protocol routing** | Omitted selectors silently choose a legacy evaluator or launcher. | Require an explicit selector, preserve explicit legacy/current routes, pass routing regressions and stop. |
| **2. Fixed-fit variability measured** | How variable are scores at fixed accepted coefficients? | Completed 20/20 development forecast batches; four-year PR-AUC sample SD 0.001075374. Zero refits or reserved-year scoring. The trusted recovery loaded the mixed-year archive, but only verified development packets enter forecasts. Stop before step 3. |
| 3. Convergence diagnostic precision | Does a more precise diagnostic resolve borderline convergence without more optimization? | Verify a fixed-coefficient native diagnostic path before changing any acceptance policy. Preserve thresholds and prior accept/reject records unless a separately reviewed protocol changes them. |
| 4. A changed-specification comparison | Is an actual mechanism difference distinguishable from numerical variability? | Select and evaluate a motivated alternative under a declared bounded comparison. Do not infer search impossibility or publication readiness from one result. |
| 5. Selection uncertainty and operational scales | What selection rule and objective scales are justified by the measurements? | Freeze a separately versioned rule before sustained search. Do not silently replace objectives, use reserved outcomes, or expand the spending grammar as a bug fix. |

## Step 1 — explicit CLI routing

**Basis:** public `main` at `dad46685e7d86a8dee60bce1a0a7db233694d6e5`.
The evaluator defaulted to `pr-only-v2`, the native launcher to
`shinka/native_config.json`, and conventional search to `legacy-pr`. The intended
multiobjective launcher already passed `multiobjective-v1` to its evaluator.
The defect was ambiguous omitted-selector invocations, not evidence that the
recorded reference scores used the wrong protocol.

The general entry points now require:

- `evaluate.py --protocol multiobjective-v1` or `--protocol pr-only-v2`.
- `scripts/run_shinka.py --config shinka/native_multiobjective_config.json` or an explicitly chosen legacy configuration.
- `scripts/conventional_search.py --protocol multiobjective-v1` or `--protocol legacy-pr`.

Missing selectors cause argparse exit code 2 **before** scientific evaluation,
preflight, results-directory creation or native-engine imports. Help remains
available without a selector. Explicit evaluator dispatch preserves the selected
function's exit code, including null-fitness failure and pause codes.

The legacy native job profile and native invalid-evaluator fixture explicitly
pass `pr-only-v2` through `LocalJobConfig.extra_cmd_args`. The current native
launcher's explicit `multiobjective-v1` route is unchanged. Maintained command
examples now name the applicable protocol/configuration; the historical scalar
contract is labelled as historical rather than describing current vector fitness.
No new wrapper, custom evolutionary controller or scientific readiness gate is added.

### What was verified

The original 62 source-only tests passed before the repair. Twelve additional
tests cover omitted/unknown selectors, side-effect-free help, explicit evaluator
dispatch and exit codes, native job argument declarations, and maintained shell
examples. All **74 tests pass locally** after the repair. The original code failed
the new routing suite before the change; omitted native-launcher selection also
created the requested directory before failing to import the unavailable engine.

```bash
python -m unittest discover -s tests -v
python -m compileall -q evaluate.py scripts shinka tests
python scripts/update_readme_status.py --check
git diff --check
```

Tests use actual subprocess CLI parsing and mocked evaluator dispatch; inspecting
native job arguments is a source contract, **not an executed native Shinka test**.
No R/RSiena simulation, empirical fit, LLM call, reference recomputation, finalist
selection, or real target-data access was performed. CI executes the same Python
suite; its actual run status, rather than this document, records remote success.

### Preserved settings and compatibility

All files under `configs/`, all original R model/evaluator files and all existing
scientific results remain unchanged. The only job-profile edit is the explicit
legacy routing argument in `shinka/native_config.json`. Historical complexity and
score-offset fields remain intact: current schema-v2 semantics do not acquire the
retired three-effect ceiling or scalar offset from those fields.

The existing campaign fingerprint includes evaluator/launcher source, so this
CLI-only edit still changes that fingerprint. Do not pull beneath an active local
controller or overwrite its saved contract. Finish such work on its bound revision
or deliberately use a separately named campaign; compatible fit/forecast caches
remain reusable under their existing checks. This step introduces no automatic
migration and does not require refitting unchanged reference models.

**Not resolved by step 1:** forecast/refit uncertainty, finite-draw convergence
precision, objective scaling, or whether changed models improve prediction.
Step 2 now reports fixed-fit forecast variability; the remaining questions
belong to the separately bounded later steps, not an automatic Shinka launch.
