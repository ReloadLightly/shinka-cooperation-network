> **Current status:** Step 3B completed in workflow `35609438242`; Step 3C reused it without rerunning it. See [current repair status](REPAIR_STEPS.md). The original authoring-session handoff below is retained as historical context.

# Step 3B: one fixed-coefficient native diagnostic

**Prepared, not executed by the authoring session.** The authoring session has
GitHub read/artifact access but no exposed repository-write or workflow-dispatch
action. It has not pushed these files or obtained a new native diagnostic.

## Fixed scope

Use the exact third saved Model 3 fit associated with forecast year 2009 and
its 1990–2008 training packet, verified in Step 3A at commit
`0ea19d8ac6cf4092c51372d66c8c09a9e68485b0`.

- Exactly one call yielding 3,000 phase-3 rows, seed **2009301**.
- `nsub=0`, `simOnly=FALSE`, original free/fixed flags and other model settings.
- Rebuild from the exact training packet and bind final `fit$theta` through the
  verified period/group-aware keys. Do not reuse serialized native pointers.
- Serial execution; a **3,600-second native process limit**, with process-group
  termination on timeout. The GitHub job limit is 75 minutes including setup.
- Zero optimization phases, refits, forecasts, scoring calls, candidate proposals
  or Step 3C repetitions. No target packet or mixed-year raw archive is loaded.

This is a diagnostic of an existing coefficient vector, not a continuation fit.
All prior acceptance decisions and scientific thresholds stay unchanged.

## Checks and evidence

The Python wrapper verifies the archived 3A commitments, original inputs, pinned
native sources, and unmodified 3A helper implementations before execution. The R
runner imports those helper definitions without invoking the 3A command-line code.
It verifies the loaded native bodies before tracing. It then guards phase-3 entry,
every simulator entry and exit, postprocessing, and the proposed Newton step.
Unexpected coefficient changes, optimization, finite-difference perturbations,
extra simulation calls or altered training targets stop the run.

The raw phase-3 statistics/scores are saved before native diagnostic postprocessing.
The complete returned object, moment matrix, moment covariance, per-parameter
results, warnings, native report, resource record and hash commitments are retained.
The same native acceptance checker reports a pass or fail. A **failed convergence
criterion is a valid pilot outcome**, not grounds to retry or switch random seeds.

The report includes diagnostics for the first 1,000 rows and all 3,000 rows. These
are nested, correlated subsets, not independent repetitions. Compared with the
historical diagnostic, both the seed and draw budget differ. One pilot cannot
establish repeatability, a pass probability, a pure precision effect, or an
appropriate production convergence policy.

## Browser-only execution

The standalone file `step3b-pilot.yml` embeds the R/Python runner, tests and this
plan. Add it as `.github/workflows/step3b-pilot.yml` on the repository's default
branch (merge an upload pull request first if necessary), then use the GitHub
Actions tab to manually dispatch **Step 3B - single fixed-coefficient pilot**.
Uploading the file does not trigger the numerical pilot; there is no push,
schedule or pull-request experiment trigger.

The workflow checks out the approved **3A commit**, not a moving scientific base.
It creates `repairs/step3b-pilot-2009301` before native execution and publishes its
source/plan there. Creation refuses an existing branch, which prevents an
accidental second dispatch or rerun from silently repeating the study. Do not
delete that branch just to bypass a failed attempt. Review any failure first.

The runtime installation uses the existing explicit conda lock and the pinned
RSiena 1.3.10 source archive with its SHA-256 check. The diagnostic runs on GitHub,
not on the user's WSL machine, and requires no user-supplied API key or data ZIP.
The standard temporary GitHub Actions token is used only for repository operations.

Result or partial-failure evidence is saved to:

`results/diagnostics/convergence-pilot-v1/`

The workflow uploads an artifact and pushes evidence to its dedicated branch;
it **does not merge the experiment into main**. A later review can verify the
artifact and decide on integration without rerunning simulations.

The code refuses to overwrite an existing local output directory. Artifact
verification itself performs no simulations:

```bash
python scripts/convergence_pilot.py verify-artifacts
```

## Authoring-session checks and limits

The existing 117 Python tests plus 15 new tests passed locally (**132 total**).
New checks cover fixed scope, failed-convergence outcomes, coefficient-audit
failures, altered artifacts, dry commands, output protection and process timeout.
These are synthetic/CLI/source tests, not native numerical tests. Eight additional
R guard self-tests are included and run by the workflow **before** any empirical
simulation. R is not available in the authoring container, so those R tests and
the real 3,000-draw pilot have not yet been executed here. The workflow was parsed
and its shell blocks were syntax-checked locally, not executed on GitHub.
