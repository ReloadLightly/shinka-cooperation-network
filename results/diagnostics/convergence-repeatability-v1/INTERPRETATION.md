# Reviewed interpretation of Steps 3B and 3C

## What the repeated evidence establishes

All nine newly declared diagnostics completed, with 27,000 new draws and no
refitting. The earlier 3,000-draw pilot is reused, not rerun. Every 1,000-draw
prefix failed the overall cutoff of 0.25; every complete 3,000-draw assessment
passed both unchanged ratio cutoffs and the existing native-validity checks.
This applies separately to the four new third-vector repetitions and the five
new fourth-vector repetitions. All coefficient vectors stayed exactly equal to
their own saved original values, with no optimization phase entered.

For these two fixed historical vectors, diagnostic simulation budget therefore
changed the observed pass/fail classification without coefficient adjustment.
The concern that a 1,000-draw gate can exclude near-solution vectors is supported
by actual repeated simulation, not only a square-root noise heuristic.

## What it does not establish

The four new third-vector full diagnostics average 0.203803089; the five
fourth-vector diagnostics average 0.152850276. The fourth vector has lower
observed ratios here. The study does NOT establish that the two vectors have
the same true residual, that optimization was useless, or that every past
continuation was unnecessary. It does not test the 2008 vector or every model
in the search grammar. It does not establish an exact moment root or strong
global identification.

The first 1,000 and full 3,000 draws are nested and correlated. Five seeds are
a small descriptive sample. Do not interpret 5/5 as a guaranteed pass rate,
combine coordinates/periods as independent replications, or apply an arbitrary
new threshold inferred from favorable outcomes. The already-seen pilot is
excluded from the four-new-repetition third-vector summary. The decision to
continue was informed by the pilot and is disclosed in the frozen design.

These are training-diagnostic measurements, not forecast scores. No candidate
signal-to-noise ratio, prediction improvement, causal burden-sharing effect,
or ShinkaEvolve advantage has been measured. Step 2's forecast Monte Carlo
uncertainty and later selection-uncertainty questions remain distinct.

## Verification and operational record

The frozen plan was committed before new simulations. All 153 Python contracts
and 13 deterministic R guard tests passed after the envelope-reader repair.
The initial attempt stopped before simulation because the accepted fourth-fit
file wraps the native fit in list(fit, diagnostics). The reader now verifies
that exact envelope and extracts the unchanged fit. The error, its cause and
the unchanged plan hash remain in prior-attempts/fit-envelope.json. No numerical
run, seed, failed result or threshold was replaced.

A separate read-only job verified all nine full cell commitments and the prior
pilot, all ten raw moment/score arrays, exact original coefficients and targets,
native parameter ordering/flags, and CSV/native diagnostic agreement. NumPy
independently reconstructed every prefix/full ratio and all descriptive
summaries, with maximum overall-ratio discrepancy below 1.1e-15.

The nine guarded intervals sum to 7,109.280 seconds (118.488 minutes). Individual
intervals range from 471.937 to 943.658 seconds; maximum observed RSS is
675,316 KiB (about 660 MiB). Parallel scheduling on separate standard hosted
runners reduces wall time, not aggregate computation. These timings include
guarded native processing and evidence handling, not full workflow setup.
No warning was captured during any of the nine guarded native calls; the
existing jsonlite-built-under-R-4.2.3 load warning remains visible in logs.

Standard public-repository runner compute is free under GitHub's documented
policy; storage remains separate. This workflow restored rather than expanded
runtime caches, publishes compressed full scientific evidence to Git, and uses
one-day retention for compact or fallback Actions artifacts. Account billing
settings were not inspected or changed.

## Recommended next decision (not executed)

Before sustained search, prospectively specify a precision-aware convergence
assessment: retain the substantive 0.1/0.25 criteria and consider a fixed
3,000-draw diagnostic at unchanged theta before paying for another optimization
continuation. It must be a versioned rule, applied consistently to reference
and candidates, not seed shopping or retroactive relabelling. These two-vector
results motivate that rule; they do not certify it for every specification.

Then proceed to Step 4's bounded comparison of an actual interpretable changed
specification, preserving a meaningful forecast-uncertainty assessment. Do not
spend another open-ended cycle merely repeating reference checks. Production
estimation/fitness settings remain untouched in this commit; no Step 4,
refitting campaign, forecast scoring, or ShinkaEvolve launch has begun.

Evidence: REPORT.md, summary.json, cell_metrics.csv, evidence-review.json,
native-evidence-verification.json, independent-moment-review.json and the
per-fit/per-seed folders. Study and review commitments remain unchanged.
