# Precision before continuation, v1

This is an **opt-in estimator policy**, implemented in preparation for Step 4.
It is not a new network specification, a changed fitness function, or a new
experiment result. Historical evaluators, configurations and results stay intact.
The implementation uses the existing structured model builder and native runner.

## Evidence and scope

The frozen Step 3C study at `7972dc9cac17ef62f78c774b1b8186d18ce9d1e1`
reported nine new fixed-vector diagnostics plus one reused pilot. All ten
1,000-draw prefixes failed the overall cutoff, while all ten complete
3,000-draw assessments passed. The prefixes are correlated subsets of the
full samples. Two vectors and five seeds per vector do not certify a universal
pass probability. This policy is a prospective design choice informed by that
study, not a statistical guarantee derived from it.

The external review's convergence-gate concern motivated the measurement. We
**do not** adopt its alternative thresholds `c*sqrt(k/n3)` or 0.20. The original
strict individual `<0.1` and overall `<0.25` requirements, plus all existing
native validity requirements, are retained. No historical acceptance is revised.

## Versioned decision rule

Policy: `configs/convergence-assessment-v1.json`, version
`precision-before-continuation-v1`. Explicit fit settings:
`configs/precision-fit-v1.json`. These copy the historical settings and change
only the version and an explicit estimator-policy selector. Legacy fitness
and complexity fields in that copied settings file are inert in this fit-only
entry point; they do not create a three-effect cap or an alternative score.

| Original completed optimization result | Action |
|---|---|
| Valid at its scheduled diagnostic budget | Accept that original result, including a valid 1,000-draw result. |
| 1,000 draws; all non-ratio checks pass; either convergence ratio fails | Assess this unchanged vector once with exactly 3,000 fresh draws. |
| Supplemental 3,000-draw assessment passes all native checks | Accept the same coefficient vector with its new diagnostic object and covariance/derivative evidence. |
| Supplemental assessment completes but fails | Continue from the **original optimization checkpoint**, not the supplemental diagnostic object. |
| Original native/identification/completion checks fail | No precision reassessment; retain the historical continuation/exhaustion behavior. |
| Scheduled 3,000-draw result fails | No second assessment of the unchanged vector; continue or exhaust the unchanged schedule. |
| Interrupted or corrupted operation | Preserve the operation and stop. Do not automatically rerun an unchanged seed or treat interruption as a scientific loss. |

This is a **supplemental gate**, not universal 3,000-draw certification. A short
fit that already passes is accepted without extra work. Consequently the policy
has two prespecified opportunities for eligible short failures; it is not the
same statistical decision rule as checking every fit exactly once at 3,000.
Its false-pass/false-fail probabilities have not been established. Uniform
3,000-draw certification would be a separately reviewed policy, not an implied
property of this implementation.

The original maximum of four optimization attempts is unchanged: attempts 1–3
use `nsub=3,n3=1000`, and the fourth uses `nsub=5,n3=3000`. There are at most
three extra assessments, one per eligible short-attempt vector. If precisely
the same vector/model identity recurs in a later attempt of the bound fit,
the original assessment is reused instead of awarding it another seed.

## Seeds and native invariance

The supplemental seed is fixed before execution:

`52000000 + 10 * forecast_target_year + optimization_attempt`

For example, target 2009 / attempt 3 maps to `52020093`. The mapping does not
depend on the candidate role, observed diagnostic outcome, or a user-chosen
retry counter. The same mapping and decision rule apply to reference and
candidate specifications. Changing model structure can change how a random
stream is consumed; this is not a claim of common-random-number variance reduction.

The algorithm is copied from the original fit; only the diagnostic budget,
`nsub=0`, the declared seed, output prefix and callback representation change.
`simOnly=FALSE`, original parameter fixed/test flags and the final `fit$theta`
are retained. Full period/group-aware parameter identities bind coefficients.
The native runner checks coefficient equality at phase-3 entry, every simulator
entry/exit and completion. Optimization phases and actual Newton steps are
blocked. Finite-difference perturbations are not allowed. The checks use the
supplied model's actual parameter count and wave count, not a hard-coded
58-parameter ceiling.

The raw moment/score arrays are preserved before native postprocessing.
A complete diagnostic failing the convergence criteria is an observed result,
not grounds for changing the seed. The historical native validity checker is
reused rather than weakened or replaced by ratio-only acceptance.

## Provenance, restart and compatibility

`scripts/precision_fit.py` binds each request to canonical specification,
training-packet bytes, settings, policy, implementation and native-source hashes.
It reads only the selected development past packet from the preserved ZIP.
Results are restricted to a separate `results/precision-fits-v1/` directory.
The final-test selection lock is respected. No target packet is opened.

A process lock serializes access to a fit directory. Each admitted optimization
or diagnostic writes its started marker before native work and a completion
receipt afterwards. Completed operations can be reused by their commitments;
started but uncompleted operations are not automatically restarted. Existing
cooperative execution-window boundaries are checked before admitting new
operations. A failed supplemental diagnostic is never used as `prevAns`.

The accepted record carries `convergence_policy`, `accepted_attempt`,
`authoritative_n3` and the authoritative diagnostics. Consumers must use the
**actual diagnostic budget**, not infer it from the optimization attempt number.
After precision rescue on attempt 1, for example, the authoritative budget is
3,000 even though that optimization attempt originally used 1,000.

**Do not pass this settings file to the historical forecast/evaluator entry
points.** They remain historical implementations and do not implement the new
policy. The new interface is intentionally fit-only. Step 4 must explicitly
use the new acceptance receipt and define its forecast/evaluation protocol.
No native Shinka campaign is silently switched over by this change.

Old checkpoints, acceptance labels and prediction caches are not automatically
copied or grandfathered into the new namespace. A separately audited import
may reuse immutable historical optimization checkpoints while replaying this
policy in attempt order; that importer is not implemented here. This does not
delete old results or force existing campaigns to refit. It prevents a new
reference from quietly using more permissive reuse rules than a new candidate.

## Explicit interface (not executed by this implementation task)

A reviewed Step 4 caller may use:

```bash
python scripts/precision_fit.py \
  --spec candidate.py --target 2006 \
  --output results/precision-fits-v1/example
```

Without `--execute`, this is a dry request and does not open research inputs.
Adding `--execute` explicitly starts the fit-only estimator; **it does not**
forecast, score, propose models, select finalists, or launch evolution. Use
`--verify-only` with the same required arguments to verify an existing committed
result without native execution. The current entry point is development-only
(2006–2009); final-year use requires a separately sealed integration.

## Validation scope

Python contracts test settings isolation, native acceptance requirements,
no-outcome boundaries, safe output routing and changed-request refusal.
`R/test_precision_policy.R` uses the real pinned runtime and saved native
fixtures to exercise accept/rescue/continue paths, unchanged-vector reuse,
interruption and tampering refusal, seed mapping, and strict cutoffs. The
optimizer and assessor calls in those state-machine tests are mocked callbacks
returning saved or explicitly synthetic fixtures: they are **not new model fits
or new diagnostic results at the new seed**.

Two real native initializations rebuild the original training setup and stop
before phase 3. They check original third/fourth vector identity through the
structured native adapter at the new seed, with zero simulator calls. The
updated production assessor's full 3,000-draw path is not rerun in this task;
its guarded design is based on the completed Step 3B/3C path. Its first live
use remains an observable part of the separately authorized Step 4 experiment.

Actual test counts, pass/failure records and limitations belong in
`results/diagnostics/precision-policy-v1/`. No empirical experiment should be
inferred from a green software test or replay of already-seen diagnostics.
