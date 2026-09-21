# Implementation update — 21 September 2026

## Scope and preserved science

This is a code-quality and research-workflow update to the published `a6b152e`
checkpoint. It does not claim a new empirical forecast or evolutionary result.
The existing R model/estimation/forecast/scoring files, Model 3 reference,
2006–2009 development years, 2010 reservation, acceptance thresholds, estimation
schedule, primary seeds and 1,000-endpoint budget are unchanged. Existing numerical
artifacts are neither deleted nor rewritten by this change.

## Implemented changes

**Execution and feedback.** Native and conventional launchers share optional
window semantics: `None` is unbounded, not an argument to `math.isfinite`.
The multiobjective evaluator exports allowlisted saved convergence diagnostics
when a native fit fails, including the worst effect t-ratios where their identities
can be bound. It preserves null objectives for failed/paused work. It never
labels a generic kill signal as proven OOM. Each evaluation also records the
canonical structural change and proposer comments in `hypothesis.json` before
execution. Missing reasoning is not invented; comments are not scientific results.

**Identities and safe resumption.** Fit, forecast and scoring identities are
separate. A forecast-seed or scorer change does not invalidate the fit identity.
Prediction-relevant R source hashes bind new caches. Original legacy caches retain
their existing exact provenance check; pre-contract structured checkpoints can be
reused only when their scientific provenance and recorded native implementation
hashes match. An unchanged scientific label is not sufficient for reuse.
The native launcher freezes evaluator and search implementation/configuration in
`scientific_contract.json`; later launches append runtime metadata instead of
overwriting the original resolved configuration. Native Pareto admission checks
the evaluator fingerprint. Conventional results and matched native budgets must
use that same fingerprint.

A populated or pending unbound native database is **not automatically migrated**.
It is preserved. Finish that controller on its original revision, or explicitly
use a new results directory with compatible numerical-cache reuse. This prevents
silently assigning the new implementation identity to old lineage. Pull code
only after an active local controller reaches a safe stopping point. No new
arbitrary generation/effect ceiling or default execution deadline is introduced.

**Comparison.** `--search-rule scalar-local` preserves the original conventional
baseline. The optional `--search-rule pareto-local` expands observed nondominated
parents in deterministic round-robin order. Both use the same grammar, evaluator,
full annual budget and distinct-terminal-attempt accounting. The Pareto comparator
is not an otherwise-identical ablation of Shinka's population controller. Shared
caches save real computation; they do not establish a method's intrinsic speedup.

**Finalist workflow.** `scripts/finalist_set.py` implements the documented
objective-wise/auxiliary champions, exact tie-breaks, deduplication and inclusion
of Model 3. `plan` freezes membership before sensitivity. The reporting-only
policy adds four prespecified forecast-seed repetitions to the original +2
repetition (offsets 2 through 6, five repetitions total), without changing search
fitness or refitting development models. Summaries include each repetition and
per-objective mean, sample standard deviation and range; these are not independent
dyad confidence intervals or fitting-uncertainty estimates. `lock` verifies all
sensitivity evidence. `run --execute` commits all valid final forecasts and records
terminal native failures before first outcome access. Every locked model is
reported, including negative differences and null failed forecasts. Changed or
missing committed predictions cannot be silently regenerated. Final information
is never written into evolutionary feedback. A plan/lock is explicit; ordinary
session checkpoints never select finalists.

**Tests and presentation.** CI runs source compilation, the offline Python
regression suite and generated README-coverage consistency. Separate opt-in
native fixtures force the new adapter rather than accepting a cached zero-vector
seed as proof of correctness. Bootstrap/launch patch checking tests actual reverse
patch applicability, not just the presence of an old marker comment. README
coverage is generated from the published manifests; the obsolete “2009 pending”
row is removed without changing existing numerical result tables.

## Verification and limits

The Python suite exercises the actual schema-v2 decoder, optional-window logic,
scientific fingerprints, cache-layer separation, Pareto trade-offs, invalid/paused
admission, immutable records, failure summaries, conventional execution and the
full finalist plan–sensitivity–lock–final-report/resumption workflow. Numerical
workflow tests use **synthetic bytes and a fake native worker**. Their positive
and negative scores are fixtures, never research artifacts or experimental results.

No R fitting, scientific forecast, LLM mutation, subscription/API call or genuine
2010 outcome access was performed during this implementation update. The editing
container did not have R 4.2.1 / RSiena 1.3.10. Consequently these native checks are
provided but **not claimed as executed**:

```bash
# Synthetic native effect allocation, parameter/coefficient transfer, recentering,
# and four-endpoint legacy/new-entry-point equivalence; no empirical fit.
environment/run-r R/check_structured_contracts.R

# One forced structured-adapter 1,000-endpoint reference forecast, using an
# existing accepted development fit; no refitting or target scoring.
python3 scripts/check_structured_reference.py --year 2006 --execute
```

These are focused checks, not a requirement to reconstruct all paper figures or
repeat the eight-hour reference estimation. The native Pareto/controller hooks
still need observation in an actual campaign. Fitting-randomness sensitivity and
mechanism ablations remain empirical follow-up work; no superiority claim is made.
