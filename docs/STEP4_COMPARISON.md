# Step 4 — one changed closure mechanism

## Declared comparison, not an evolutionary campaign

Design base: `2a7a8f5000dacfcc9e56f865e2d720e1b446ee53`.
Plan: `configs/step4-comparison-v1.json`, version `step4-closure-comparison-v1`.
This task tests one human-motivated change. It neither launches ShinkaEvolve nor
selects a champion, and does not search decay parameters or expand the spending
objective. A negative result does not invalidate every specification in the
search grammar. A positive result is not a Shinka achievement or a causal result.

Reference network terms: **degPlus(1) + transTriads(0)**.
Alternative: **degPlus(1) + gwesp(69)**. Both retain density, the original empirical
controls, and Model 3's spending-equation structure. Every included coefficient
is jointly estimated; the spending coefficients are not held at baseline values.

The native `GwespFunction.cpp` implementation uses alpha = parameter/100. For m
shared partners its weight is exp(alpha) * (1 - (1-exp(-alpha))^m). Thus parameter
69 means alpha=0.69, not 69, and supplies diminishing marginal closure weight.
It is the preexisting native/default catalog choice, not a decay selected against
outcomes. The exact native actor-choice implementation is used; no hand-written
Python utility replaces it. The alternative does not guarantee fewer triangles:
its coefficient and all other included coefficients are estimated jointly.

The original paper's Table 1 and network equation (6) motivate studying closure
as a partner-selection mechanism. The observed 2007 forecast triangle excess
motivates this particular alternative but does not identify its cause. This is
an explicitly **development-stage, data-informed comparison**, not untouched
confirmatory evidence. It does not repeat the paper's Model 4 efficiency/free-riding
test or demonstrate that reduced spending improves security.

Sources: Kinne & Kang (2023), DOI 10.1017/S0020818322000315, Table 1 and pp. 420–422;
RSiena v1.3.10 `src/model/effects/generic/GwespFunction.cpp`; repository
`configs/effect-catalog-v2.json`; the external review's motivated-hypothesis
suggestion is treated as a proposal, not proof that transTriads causes the misfit.

## Estimation and audited reuse

Both models use the same opt-in `precision-before-continuation-v1` policy.
Keep the four original optimization attempts, strict 0.1/0.25 cutoffs, non-ratio
native validity requirements, deterministic supplemental seeds, and no repeat
assessment of an unchanged vector within its bound fit. No fitting seed sweep.

The new historical-checkpoint importer is **optimization-only**. It permits any
exactly matching model/data/settings history, independent of reference/candidate
role. Each source checkpoint and provenance file must match its Git object at
the fixed design-base commit; packet and fitting-source hashes must match;
native parameter identities, algorithm mode, schedule and seeds are checked.
Only descriptive structured-identity columns can be added to an in-memory copy.
Original files, coefficients, covariance/derivative arrays and history stay intact.

The precision state machine processes checkpoints in attempt order. A newly
eligible old short result receives the declared new-policy assessment, and may
be accepted before the historically accepted later attempt. Otherwise the next
original optimization checkpoint may be reused only when the continuation input's
theta, dfra, dinv, sf, regrCoef/regrCor, fixed and maxlike fields match the archived
previous input. No old acceptance label or forecast is imported. The reference
has an eligible history; no matching GWESP history is declared, so its fit starts
from the original native initialization, not a cross-model warm start.

This avoids paying to reproduce identical old optimization without giving the
reference a more permissive acceptance rule. Imported optimization cost must be
reported separately from new numerical work; cache reuse is not zero scientific
estimation effort. New fits and diagnostics are preserved in a new namespace.

## Receipt-aware forecast consumer

The forecast wrapper first verifies the new receipt's policy, accepted attempt,
`authoritative_n3`, reconstructed native diagnostics, and structured identities.
A private lexical copy of the unchanged `run_forecast_multiobjective` reuses its
forward data construction, coefficient reparameterization, native simulation,
endpoint checks and probability aggregation. Its acceptance-check schedule is
bound to the actual receipt's diagnostic n3, not inferred from the original
optimizer attempt number. Missing-fit estimation is forbidden in this process.
The receipt is read in place and not copied or rewritten as a historical fit.

The forecast call is checked for simOnly=TRUE, nsub=0, 1000 endpoints and all
forward parameters fixed; coefficients are checked at initialization, every
native simulation entry/exit and completion. Training coefficients remain unchanged;
the original exact centering transformation defines the forward coefficients.

## Forecast budget and metrics

The four development targets remain 2006–2009. Each model/year has exactly five
fresh batches of 1000 endpoints: **40 batches, 40,000 endpoints**, contingent on
all eight fitted models being accepted. Forecast seeds are distinct between
models and batches: 61000000 + 100*year + 10*model_index + batch, with indices
reference=0, gwesp69=1 and batches 1–5. This is not a common-random-number claim.

The primary point is the mean of four annual candidate-minus-reference PR-AUC
values, calculated from probabilities averaged over all 5000 endpoints BEFORE
scoring. The same original PRROC integral and eligible dyad mask are used.
Brier, ordinal-spending RMSE, formation and dissolution PR-AUC remain visible;
there is no new scalar fitness or hidden trade-off weight. The original per-batch
scorer also produces ties, triangles, clustering and degree-variance envelopes.

Every batch and pooled prediction is committed before a separate scoring process
opens its development outcome packet. All five predictions for a model/year are
completed before that cell's scoring. There is no adaptive model, seed or budget
choice based on those scores. Both models must have identical eligibility masks.
No 2010 packet or mixed-year raw archive is opened. A missing/failed model/year
prevents reporting a complete four-year comparison; partial-year means are not fitness.

## Meaningful but limited Monte Carlo uncertainty

Preserve the five independent 1000-endpoint contrasts separately from pooled
scores: a mean of PR-AUCs is not PR-AUC of pooled endpoint probabilities.
For the pooled four-year point, compute five delete-one-batch estimates using
4000 endpoints per model/year, then SE = sqrt((4/5)*sum((leave_one-mean)^2)).
The predeclared blocks group the same batch index across independent models and
years. Report a descriptive point +/- t(4,0.975)*SE interval. This is a small-block
jackknife approximation, fragile for rank ties/nonsmooth metrics, not an exact
confidence guarantee, statistical superiority decision, or correction for model
selection. Display every metric, per-year difference and raw batch contrast.

No dyads are resampled independently. The resampling units contain whole native
networks. There is only one optimization-seed history per model/year. These
intervals therefore omit fitting uncertainty, uncertainty across genuinely new
historical cases, substantive causal identification, and theory selection.

## Execution bounds and failure policy

Eight declared model/year cells; no more than four optimization attempts and
three supplemental assessments per cell; no more than five forecasts per cell.
A first-invocation total native wall budget of four hours per cell is an explicit
resource bound, not a scientific failure criterion. A timeout preserves available
checkpoints with no score or automatic retry. Standard public-repository Linux
runners are used, each numerical process serial, with at most eight cells in
parallel. Parallelism reduces wall time, not aggregate compute. Runtime caches
are restored, not expanded; compact/fallback Actions evidence uses one-day
retention, and full results are preserved on unique result branches.

A separate preflight validates all inputs/import identities and both short and
rescued receipt forecast initializations, stopping before simulation. Its saved
fixtures are not new policy acceptances or forecast observations. After successful
preflight the declared eight-cell workflow may run once; a reservation branch
blocks accidental relaunch. New empirical work is not counted until observed.

Entry point: `python scripts/step4_compare.py cell --model reference --year 2009
--execute` (from the pinned checkout with its verified runtime). Ordinary calls
without `--execute` are dry. Full orchestration and immutable source hashes are
recorded on the execution branch. No requirement to update a frozen local campaign.
