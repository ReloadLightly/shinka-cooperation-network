# Step 3A: verified convergence-diagnostic initialization

**Status: complete; Step 3B has not run.** This step reconstructs the old
convergence statistics and verifies the native setup of a phase-3-only
assessment. It does not generate new simulations or estimate new coefficients.
It neither resolves the convergence-precision question nor changes acceptance.

## Scope and exact inputs

The target is the **third saved Model 3 attempt associated with forecast year
2009**, fitted on **1990–2008** only. This is not an assessment of 2009 outcomes.
The model has 161 actors, 19 observed waves, 18 intervals and 58 parameters:
18 network rates, 18 spending rates, 11 network-objective coefficients and
11 spending-objective coefficients.

The [preflight configuration](../configs/convergence-preflight-v1.json) binds:

- `results/cache/ed64802bacb0fbdd1ae1bc45746e29795f85bc0f92ceedf427660ea0c40efc99/fit-attempt-3.rds`, SHA-256 `5c122ed7a1e061d8d23f50c73a22baa4b80884ad74be49ab7a56bdb80dfe0e5c`.
- Only `data/past/2009.rds` from `sources/archive/step2-development-inputs.zip`, SHA-256 `f8aea6ff84f4a82c43cce7cd6bc12fcd0a4fc36e0db0f6aeb4618381fc1771e4`.
- R 4.2.1, RSiena 1.3.10, the original empirical adapter and environment lock,
  and thirteen pinned native source/help/package files.

Both hashes are checked against the pre-existing published provenance, not
newly invented equivalence criteria. The ZIP directory is inspected to reject
unexpected or duplicate members; only the specified training member is
decompressed. No target-data packet or raw replication archive is opened.

## Why the native data are rebuilt

The saved fit retains native external pointers and metadata, not a reusable
copy of its original training data. Serialized pointers are not a valid basis
for restoring a native model in a fresh process. The preflight uses the
unchanged `make_training_data()` and `model_effects()` on the exact training
packet. It does not reuse the saved pointers or pass `prevAns`.

The actual native initialization reproduces **both aggregate and per-period
observed target statistics exactly**, with maximum absolute differences of zero.
Actor ordering, model types and all 58 parameter identities are retained.

## Coefficients are identified by complete native identity

The general `effect_key()` used by the original forecast adapter is not a
complete key for historical rate parameters: it does not include rate period.
The scoped preflight binder therefore includes period and group, along with
name, type, short name, interaction operands, internal parameter and other
native identity fields. A duplicated or missing identity is an error.

The values supplied are the **final `fit$theta` values**, not potentially stale
`requestedEffects$initialValue` entries. Original fixed and test flags remain
unchanged. A deterministic fixture verifies correct binding even when rate rows
are reversed. This is a new diagnostic-specific binder, not a modification of
the original forecast estimator.

## Native control-flow audit

The pinned source is available at
[`stocnet/rsiena` tag `v1.3.10`](https://github.com/stocnet/rsiena/tree/v1.3.10).
The actual loaded bodies and argument lists of nine relevant functions were
compared with that source before any tracing was installed.

| Native component | Relevant behavior | Preflight consequence |
|---|---|---|
| `R/robmon.r` | `x$nsub == 0` selects the phase-3-only branch and bypasses phases 1 and 2. | Preserve all original flags and disable estimation through `nsub=0`. |
| `R/initializeFRAN.r` | Standard initialization or `prevAns` can change incoming values. | Keep `useStdInits=FALSE`, pass `prevAns=NULL`, explicitly bind final theta. |
| `R/phase3.r`, `phase3.2` | The `nsub=0, simOnly=TRUE` route skips the ordinary convergence block. Fixed coordinates are excluded from the overall convergence norm. | Use `simOnly=FALSE` and preserve the original free-parameter flags; do not mark everything fixed. |
| `CalculateDerivative3` | Convergence uses raw `sf` and `cov(sf)`. Dolby adjustments affect other quantities. | Do not substitute adjusted means or simulation-mean standard errors. |
| `PotentialNR` | Phase 3 calls it with `MakeStep=FALSE`. | Do not apply a proposed Newton adjustment. Actual phase-3 invariance remains a pilot check. |

The algorithm is copied from the saved fit, changing only `nsub`, `n3`, the seed,
output prefix and the callback representation. The callback is resolved by its
pinned namespace name instead of reusing a serialized function closure. The
source constructor defaults do not silently replace the original settings.

## What actually ran

The code called the real `siena07()` and native data/model initialization,
including observed-statistic calculation, under the pinned runtime. Hard-stop
traces guarded optimization functions and simulator entry points. A separate
trace checked the initialized state at the entrance to `phase3()` and raised a
specific expected-stop condition **before the phase-3 body**.

The dry run verified exact coefficient equality, exact native parameter ordering,
unchanged fixed flags (all 58 coordinates remain free for diagnosis), zero
optimization iterations and the exact observed targets. There was one guarded
phase-3 entry and no simulator entry. These are actual native initialization
checks, not mocked worker results. They are not a completed 3,000-draw run.

## Reconstructed historical diagnostics

From the saved 1,000-row moment-deviation matrix, let `m=colMeans(sf)` and
`V=cov(sf)`. Individual ratios are `m/sqrt(diag(V))`; the overall ratio is
`sqrt(t(m) %*% solve(V,m))` for this all-free, ordinary method-of-moments fit.
No covariance regularization, pseudoinverse, SE denominator or changed threshold
is used.

| Quantity | Recomputed old value | Agreement with saved native value |
|---|---:|---:|
| Maximum absolute individual ratio | 0.07587932310910743 | Maximum ratio difference 0 |
| Overall convergence ratio | 0.2613440047985899 | Absolute error below 4e-16 |
| Moment covariance | 58 × 58 | Maximum elementwise error 0 |

The historical overall criterion remains **failed** (`0.261344... >= 0.25`).
No new acceptance decision is made. These are the same old diagnostic draws,
not new evidence that a higher-precision check will pass.

## Tests, resources and evidence

The Python suite grew from 101 to **117 passing tests**, with 16 source-only
preflight tests. These use synthetic fixtures or source/CLI checks and are not
empirical results. Eleven deterministic R self-checks passed without RNG-based
simulations. The separate native initialization verification used the real fit
and real training packet. Original scientific files were hash-checked before
and after; tracked original files remained unchanged.

The verified command took **8.86 seconds** and peaked at **442,740 KiB** resident
memory on its GitHub runner. This measures the stopped preflight, not the cost
of the future 3,000-draw assessment. The runtime's existing warning that
`jsonlite` was built under R 4.2.3 remains visible in the log; the running R
version was verified as 4.2.1.

Evidence: [report](../results/diagnostics/convergence-preflight-v1/REPORT.md),
[verification](../results/diagnostics/convergence-preflight-v1/verification.json),
[parameter map](../results/diagnostics/convergence-preflight-v1/parameter-map.csv),
[input fingerprints](../results/diagnostics/convergence-preflight-v1/inputs.json),
[native log](../results/diagnostics/convergence-preflight-v1/native.log),
and [execution/publication record](../results/diagnostics/convergence-preflight-v1/execution.json).

The first workflow's native verification succeeded, then a publication helper
failed because it incorrectly expected `OK` to be the final line of merged
Python-test output. Buffered fixture output followed the successful unittest
status. Publication uses the standalone status line and preserves the existing
committed evidence; no native work was rerun to repair publication.

## Reproduce the bounded check

From a checkout with the pinned native runtime installed:

```bash
python scripts/convergence_preflight.py check
python scripts/convergence_preflight.py verify --execute \
  --output results/diagnostics/convergence-preflight-local
```

An existing output directory is refused, so published evidence cannot be
silently overwritten. `verify` without `--execute` is a dry request. The command
has no actual-simulation mode. Committed evidence can be checked without R:

```bash
python scripts/convergence_preflight.py verify-artifacts
```

## Next step, separately authorized

Step 3B would run **one** native phase-3-only pilot using this verified setup:
`nsub=0`, `simOnly=FALSE`, `n3=3000`, seed **2009301**, original fixed flags,
serial execution, and the exact saved third-attempt theta. The configuration's
`pilot_is_separately_authorized` marker means that a separate user decision is
required; it is not an assertion that execution has already been authorized.

That pilot still needs explicit execution controls, checks of theta at simulator
entry and after termination, complete 3,000-draw output, raw moment/covariance
preservation, native warning reporting and measured time/memory. A success or
failure must be retained without seed shopping or automatic continuation. No
3B runner is activated by the preflight commands or by ordinary main-branch CI.
No training inputs remain missing for this initial pilot. Its actual runtime,
completion, numerical warnings and fresh convergence diagnostics remain unknown.

Step 3C's larger repetition study, any revised convergence policy, new candidate
comparisons and evolutionary search remain separate decisions.
