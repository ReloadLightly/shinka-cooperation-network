# Step 5C: bounded launch-path repair and host handoff

This step changes failure bookkeeping, startup checks and launch documentation,
not the experiment. The current protocol is **multiobjective-replicated-v1**;
the dedicated entry point is **scripts/run_shinka_replicated.py**.

## Scope and evidence

The terminal-failure regression checks a first numerical-policy exhaustion and a
second encounter with the same canonical model. Both must remain invalid with
null fitness. The second encounter must not start R, change evidence, or consume
another admission. Terminal failures are bound to the request and saved diagnostic
files. Untyped historical failures, missing/corrupted commitments and interruptions
remain paused, without automatic retries.

The host checks verify the local pinned checkout/patch, API import, installed
executables, local model directory, and (when requested) R/RSiena/PRROC versions
and the existing isolation/login-status self-check. Credential contents are not
included in reports. No downloads, authentication migration, paid-provider fallback,
model inference, new fits or new forecasts are performed by these checks.

Before constructing the native runner, the launcher refuses occupied ports and
waits for its own embedding/WebUI child processes and HTTP health responses. The
embedding port comes from the configured endpoint rather than a hidden default.
A failed service prevents the runner from starting. Cleanup is restricted to
process groups started by this launcher; other projects are not stopped.

Fresh validation records belong under
`results/diagnostics/step5c-handoff-v1/`. Distinguish deterministic fixtures,
saved-evidence native scheduler checks, stopped R initialization, and actual live
inference. Only records actually present establish execution; this document is
not a claim that a particular host has passed. The first real Shinka mutation
belongs to the experiment, not a throwaway readiness run.

## Run on the intended authenticated local host

Do not pull this repair beneath an active controller. It changes implementation
fingerprints while retaining the scientific policy. Preserve old bound campaigns
on their original source; do not delete or rewrite their SQLite database, pending
queue, source binding or admission ledger to make an incompatible resume succeed.
A fresh replicated campaign may reuse the verified Step 4 evidence. Continuing
that campaign thereafter uses the same results directory and cumulative budget.

Hydrate the immutable Step 4 result only when it is not already available. The
destination must be empty; existing evidence is never overwritten:

```bash
.venv-shinka/bin/python scripts/hydrate_replicated_evidence.py \
  --destination "$HOME/shinka-evidence/step4-v1" --fetch
export SHINKA_REPLICATED_EVIDENCE_ROOT="$HOME/shinka-evidence/step4-v1"
```

Check the actual host and replay both saved specifications:

```bash
.venv-shinka/bin/python scripts/replicated_host.py \
  --check-runtime --check-isolation
```

Exit 75 means an unmet or unverified local prerequisite; inspect the named checks.
Exit 0 establishes local prerequisites only. `model_inference_verified` remains
false because no inference request was made. The first live request may still
fail because a configured model alias or subscription allowance is unavailable.
No alternate route is selected automatically. This command does not create a
campaign or start the embedding/WebUI servers; the execute path starts and checks
them immediately before constructing the native runner.

Resolve the configuration without execution:

```bash
.venv-shinka/bin/python scripts/run_shinka_replicated.py \
  --results-dir runs/evolution_replicated
```

Actual execution requires the chosen window and cumulative new-model allowance:

```bash
: "${WINDOW_HOURS:?Set the authorized execution window}"
: "${NEW_SPEC_LIMIT:?Set the cumulative new-specification limit}"
R_GC_MEM_GROW=0 .venv-shinka/bin/python scripts/run_shinka_replicated.py \
  --results-dir runs/evolution_replicated \
  --window-hours "$WINDOW_HOURS" \
  --max-new-specs "$NEW_SPEC_LIMIT" \
  --execute
```

The window is an admission/cooperative-boundary window, not a promise to kill an
atomic R call exactly at that hour. Existing numerical caps remain unchanged.
`NEW_SPEC_LIMIT` counts unique new canonical admissions, including terminal
numerical failures. It is not a generation count, per-session allowance, or total
LLM-call cap. Raising it is not supported implicitly: preserve the ledger and
obtain a separate explicit budget update rather than resetting the campaign.

## Three-phase loop retained

The native Shinka controller still owns parent/inspiration context, diff/full/
crossover proposals, embedding and LLM novelty assessment, scheduling and feedback,
islands/migration, the UCB model bandit, meta-memory and prompt evolution. The
project's already declared replicated MC-resolved selection extension is unchanged.
No alternate evolutionary loop or manually selected first offspring is introduced.

A completed empirical cycle means a genuinely new canonical Shinka proposal has
recorded ancestry, a complete four-year evaluation, persisted feedback and use of
that feedback in subsequent search. Imported comparisons and fixture nodes do not
count as discoveries. Report unique admissions, completed valid models, terminal
failures, duplicate source variants and paused work separately.

## Unchanged scientific contract and remaining boundary

Native equations, controls, spending structure, joint coefficient estimation,
2006–2009 targets, convergence thresholds, precision policy, seeds, five batches,
integer-count pooling, three objectives, selection policy and existing measured
artifacts are unchanged. No 2010 evaluator is enabled by this repair.

GitHub's numerical validation host is not the user's WSL host. Passing CI does not
supply subscription authentication or establish live model access there. Do not
copy credentials into Actions, commits, logs or artifacts. The selected execution
host and explicit launch budget remain necessary before actual proposals begin.
