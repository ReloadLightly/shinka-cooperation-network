# Deviations, discrepancies and limitations

This file distinguishes source discrepancies from intentional forecasting changes
and execution limitations. A planned artifact is not an executed result.

## Source discrepancies verified in shipped code

* Appendix prose describes training through 2009; `02.appendix.R` instead sets
  `1990:2008`; `00.gof.predict` validates on `2009:2010`.
* The predictive specification is Model 3: it includes spending `outdeg` and
  `behDenseTriads` (parameter 6), but not Model 4's free-riding interaction.
* The predictor imports training coefficients but restores network and spending
  rates initialized from observed validation data. It averages simulated ties,
  then flattens both directions of the symmetric SAOM network; its logit
  comparison instead selects unordered pairs. Reproduction preserves these
  settings; the extension changes them explicitly.

## Prespecified extension

`evolution_forecast` uses four annual targets (2006–2009), expanding training from
1990 through the preceding year, and an untouched-by-search final target 2010.
It uses unconditional forward simulation, last training-period rates, origin
covariates and one eligible undirected pair per score. These choices are the
user's extension, not claims about the authors' validation protocol.

## Execution status

The repository began empty with no R installation. No published AUC or RMSE has
been reproduced, and no evolutionary improvement has been established.
Software/version differences and measured costs will be appended as verified.

* Exact R 4.2.1, RSiena 1.3.10 and PRROC 1.3.1 installed locally. Host Ubuntu
  22.04.5, conda compiler/OpenBLAS and ancillary package versions differ from the
  authors' environment. Many conda R packages were built under R 4.2.3; actual
  interpreter is 4.2.1. Warnings and complete package lock retained.
* The original ABM PSOCK workers cannot open sockets inside the execution
  sandbox. Retried the unchanged original two-worker settings with the required
  execution permission; did not silently switch parallelism or seeds.
* An initial source-parity audit was killed by memory pressure before emitting
  its comparison artifact. GNU time confusingly printed Exit status 0 alongside
  signal 9. The premature progress claim of parity passing was withdrawn.
  The subsequent completed serial comparison passed
  all 18 checks in 35.15 seconds, with 612,504KB peak RSS. Jobs are serialized.
* The first original ABM call (rate200, n3=25, full159-country calibration,
  two workers) was deliberately terminated after899.03 seconds wall time without
  returning an endpoint batch. Parent peak RSS was435,660KB; two workers each
  used about137MB, so the parent measurement understates aggregate memory.
  No complete full-grid call or figure is claimed. Resuming restarts this
  interrupted native call; only completed native calls are checkpointable.
* The concurrent first baseline fit was killed by signal9 after195.80 seconds,
  peak421,968KB; no accepted fit or scientific loss was produced.
* Original ABM `degPlus(parameter=2)` implements square-root degrees, whereas
  the printed total-degree equation and empirical default use raw degrees
  (`parameter=1`). Both executable settings are preserved in their respective
  modes. Appendix A7 prints an ego covariate where code/TableA1 use the alter.
* Shinka and Headless adapter whitelists did not accept Ultra despite the local
  subscription CLI advertising it. The recorded compatibility patch permits
  forwarding the actual `ultra` request, disables automatic web search and binds
  native WebUI to loopback. One subscription smoke call returned gpt-6-astra;
  achieved reasoning effort was not echoed. This is not an evolution result.
* Extension estimation runs serially to fit this host's memory, while source
  empirical scripts use two workers. The simulator and scientific settings are
  retained, but parallel random-number streams are not claimed identical. The
  original ABM reproduction retains its two workers.
* The serial 2006 baseline's first complete attempt took 664.205 seconds and
  failed convergence (maximum absolute t-ratio 0.258198; overall 0.561063).
  Native completion did not make this an accepted fit. The predeclared retry
  uses `prevAns`; acceptance thresholds are unchanged.
* Independent review found that a proposed forward composition `c(1,1)` is
  unsafe: native RSiena discards its time-zero departure. The first reduced
  diagnostic did not detect that membership error. Forward forecasts from this
  construction are invalidated; training fits are unaffected. The corrected adapter uses native inactive flags plus structural-zero code 10
  only for origin-inactive dyads, because this old native engine can still propose
  ties to an inactive receiver. The strengthened diagnostic passed: inactive ties
  remain zero, inactive behavior remains unchanged, active dyads can change, and
  inaccessible target changes leave predictions identical. Old schemas are rejected.

* Attempt2 took 597.301 seconds and narrowly failed both thresholds (maximum
  absolute t-ratio 0.1021251243; overall 0.2974892948). Stopped the old process
  early in attempt3 for the forward-only correction, then resumed the same third
  attempt from the two completed, unchanged training checkpoints. The explicit
  transfer record verifies training identity and copies no forecast or score.
* Mutation filesystem isolation alone did not block host-loopback access. The
  corrected launcher adds a separate network namespace and exact-domain
  subscription CONNECT proxy. Blocking tests and a second authorized Astra
  subscription smoke succeeded. These are administrative checks, not evolution.

* The 2006-target baseline exhausted all three declared attempts. Attempt3 took
  618.160 seconds; maximum |t|0.0944475853 passes its criterion but overall
  convergence0.3237543663 fails the0.25 criterion. No PR-AUC, seed-zero claim or
  evolutionary fitness was produced. Continuing prediction requires an explicit
  new fitting-policy version, applied equally before candidate comparisons.
* Original main-paper and appendix-validation callers are prepared, but their
  2010-based execution is deferred until after the reserved final comparison.
  These unchanged full callers do not support intermediate checkpoint recovery;
  interrupted empirical reproductions require a fresh run directory. ABM native
  calls and extension fitting attempts have their own verified checkpoints.

* Publication review found that checkpoint identities are not fully portable:
  original ABM keys contain absolute script paths, and empirical keys hash an
  environment report containing its verification timestamp. Relocation or
  verification can cause safe cache misses and recomputation. Published native
  result objects remain inspectable; automatic reuse is guaranteed only with
  unchanged provenance and paths. This limitation is documented in the runbook.

* Session scientific policy v2 adds exactly one stronger continuation after the
  three original attempts, using the authors' main-estimation nsub5/n3=3000 and
  seed12348. Thresholds, Model3 effects/controls, sample, temporal design, and
  1000 forecast endpoints are unchanged. Every candidate/baseline receives the
  same rule. At the user's direction, estimation-only code changes rely on
  saved scientific reconstruction evidence; automatic source-hash audit gates
  are not rerun. Native fit acceptance and prediction/scoring checks remain.

* User-directed multiobjective-v1 replaces future PR-only selection with equal
  annual means of PR-AUC, Brier and ordinal-spending RMSE improvement. Existing
  PR-only results retain their original protocol. Scalar credit
  2+(J1+J2+J3/10)/3 is an explicit operational preference for native bandit/prompt
  adaptation; it is neither the authors' formula nor Pareto selection. The new
  three-objective evaluator reuses unchanged baseline forecasts and scores.
* The new search grammar removes the fifteen-subset/three-effect restriction.
  It includes native integer functional parameters and compatible two/three-way
  products. Exact aliases are canonicalized; proportional symmetric degree
  moments cannot be stacked. GWESP(0) and transTies have identical estimation
  statistics but distinct native choice contributions, so they remain different
  alternative models with incompatible joint estimating equations. Truncation
  knots160 or greater collapse to density for161actors and are excluded for
  that mathematical reason. Unknown algebraic equivalences may remain; code
  embedding novelty is not a guarantee of mathematical novelty.
* Pinned native updateTheta omits internal parameters from its matching key.
  The structured adapter uses scoped copies of native R entry functions with
  parameter/operand-aware matching, exact derivative-order agreement and
  provenance for adopted unchanged legacy fits. The installed RSiena namespace,
  native kernel and original-source reproduction path are unchanged. Dynamic
  spending products receive algebraic centering corrections, including fixed
  lower-order forecast terms; these are not additional estimated coefficients.
* Pareto retention, objective-space parent/inspiration sampling and migration
  are project extensions to pinned Shinka. Native generation and SQLite remain.
  A separate compatibility patch permits deadline-bounded sessions with no
  overall generation ceiling and saves incomplete candidates without a fitness
  value or bandit/prompt credit. The older running PR-only evaluator predates
  this cooperative hook; its files and declared numerical policy are preserved.
* Source/effect parity establishes reconstruction, not reproduction of fitted
  empirical estimates or the efficiency/free-riding conclusion. The authors
  favor efficiency in their Model4 comparison; retaining Model3's spending
  structure cannot independently reproduce that comparison. All spending
  coefficients are nevertheless reestimated jointly for every candidate.
  Original full-period Models3/4 remain on the reproduction agenda with new
  2010-dependent results separated from development until final selection locks.

### Continuing campaign authorization (2026-09-20)

The latest user instruction supersedes the former session deadline. Periodic publication checkpoints no longer stop admission. The new native launcher has no default time window or overall generation ceiling and clears stale inherited session deadlines. Optional explicit future windows retain cooperative checkpoint behavior; scientific fit timeouts, finite retry policies, serial R work, strict convergence and subscription-only access remain. This change affects scheduling, not the scientific objectives, sample, accepted-fit reuse or simulation budget.

### 2009 fourth continuation interrupted by global OOM (2026-09-20T23:07:33Z)

The kernel killed the active fit while host RAM/swap were exhausted and a diagnostic R reader was also present. No fourth fit was saved. This is an execution failure, not a fourth nonconvergence finding. Saved-fit inspection and fitting will now be strictly serial. Recovery must use saved attempt3 and the unchanged scheduled fourth settings/seed; additional numerical remedies depend on an actual completed fourth result. The kernel event, interruption logs and invalid evaluator output are preserved. No forecasts or objective values were fabricated.
