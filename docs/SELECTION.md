# Conventional search, finalist sensitivity and reserved final test

These entry points are implemented but have not produced a conventional-search,
fresh-finalist or final-year scientific result at this checkpoint. They refuse
to substitute partial-year results, failed fits or reduced simulation budgets.
Candidate programs are parsed as restricted literal specifications; these trusted
scripts do not execute candidate Python.

## Conventional specification search

`scripts/conventional_search.py` enumerates every subset of the four native
catalog effects having size zero through three: **15 mathematical models**,
including the original baseline. Density, empirical controls and the spending
objective remain fixed. Its deterministic order is the baseline, each single
deletion, each replacement, each addition, then remaining subsets by size and
name. There is no adaptation of that order to observed scores and no custom
evolutionary controller.

Every specification calls the same `evaluate.py` with all four development
years, the fixed estimator/retry policy, 1,000 endpoint networks per year, the
same seeds, the same eligibility rules and the same unweighted mean PR-AUC
improvement. Invalid evaluations remain invalid and consume one attempt slot;
they receive no numerical loss. The best valid model is determined by raw F.
Exact ties are reported using fewer mutable effects and then canonical hash;
this tie rule does not add a complexity bonus to fitness.

The script requires accepted baseline evidence in all four current-protocol
development caches before even publishing a plan. It verifies the source/metric
preflight, forecast audits, estimator diagnostics, prediction commitments and
score provenance. It does not start missing baseline fits implicitly.

```bash
# Save the complete 15-model plan after baseline evidence is available.
python3 scripts/conventional_search.py

# Execute/resume that complete plan with the unchanged full evaluation budget.
python3 scripts/conventional_search.py --execute

# Alternatively freeze a separate comparison budget from actual native outputs.
python3 scripts/conventional_search.py \
  --native-results-dir runs/evolution_native \
  --results-dir results/conventional_matched --execute
```

The optional native cap is the number of unique valid canonical specifications
plus all failed evaluator attempts observed in native `*/results/correct.json`
outputs, including its seed when observed. It is capped at 15; `--limit N`
can impose an additional fixed cap. Configured generations, duplicate successful
programs and unexecuted proposals do not enlarge this budget. The observed native
records and hashes are frozen in the conventional plan. A later larger native
campaign requires a separately named conventional run, not a silent plan change.
Resuming the same conventional command reuses that original snapshot even if
additional native generations have completed. It verifies the snapshotted
programs, metrics and correctness records and retains the original attempt cap.

This compares mathematical search under an explicit attempt-count budget.
It does not assert equal wall time: failures can terminate early and shared
validated caches can save fitting cost. Report actual runtime, failed attempts,
unique specifications and cache reuse for both methods. All conventional
programs, native-format metrics/correctness outputs, plan and rankings remain
under `results/conventional*`, outside the candidate mutation workspace.
Resume with the same `--native-results-dir`, `--results-dir` and `--limit`
options. Completed invalid evaluations are retained, not retried as new models.
Previously measured evaluator and driver runtime are preserved on resumption;
an unavailable interrupted driver duration is reported as missing rather than
replaced by the near-zero time required to read its cached result.

## Fresh simulation randomness before selection is sealed

After primary evaluation, re-evaluate any prospective finalist with:

```bash
python3 scripts/final_test.py sensitivity --program-path candidates/FINALIST.py
```

The name `FINALIST.py` is a placeholder for an actually evaluated program.
The script requires complete current-protocol development evidence for it and
the baseline. It reuses only the corresponding accepted training fits, recording
the source fit and its hash. It changes only forecast randomness from
`target_year*1000+1` to the already declared `target_year*1000+2`, retaining 1,000
endpoints and every other scientific setting. It assesses all four years and
compares fresh candidate-minus-baseline deltas with the primary deltas. Identical
canonical models share one forecast, so an unchanged baseline cannot acquire a
spurious difference from unrelated randomness.

Artifacts are written to `results/selection/sensitivity/<identity>/`, including
fits, predictions, masks, scores, native logs and `sensitivity.json`. This is one
paired Monte Carlo replicate; it is neither a dyad-independent significance test
nor a replacement fitness definition. No 2010 outcome file is opened or hashed.
Repeat the identical `sensitivity --program-path ...` command to resume an
interruption. Completed sensitivity artifacts are validated and returned without
changing their completion timestamp. Every expected baseline/candidate/year
cache is reconstructed and checked, including the copied training-fit hash,
forecast seed, score provenance and mask; a supplied list of a few evidence
files cannot satisfy this gate.

## Sealing one selected structure

Choose the structure using development evidence, record the reason, and seal it:

```bash
python3 scripts/final_test.py lock \
  --program-path candidates/FINALIST.py \
  --sensitivity results/selection/sensitivity/IDENTITY/sensitivity.json \
  --selection-reason 'Selected using the fixed four-year development score; comparison and Monte Carlo sensitivity recorded.'
```

The lock requires all four original development scores, accepted baseline and
candidate fits, and a complete matching fresh-randomness artifact. It records
the canonical specification and hash, original baseline, all annual PR-AUCs and
deltas, raw F, selection timestamp, artifact hashes, and the protocol hash.
The latter includes trusted code, settings, effect catalog, software locks,
source provenance and training packets. The 2010 training packet contains only
observations through 2009. No final outcome hash enters preselection evidence.

The script creates read-only `results/selection/selected.json` and a separate
`results/final_test/reservation.json`. It refuses to overwrite an existing lock,
change sensitivity evidence after sealing, or proceed with altered evidence.
Repeating the identical `lock` command is idempotent. If interrupted between
writing the selected manifest and writing its reservation, that exact command
can finish the seal only after all evidence is revalidated; the selected
timestamp and structure are retained. A different model, reason, sensitivity
artifact or protocol cannot replace it.
These are controls in a trusted research workflow, not a claim that a filesystem
owner cannot deliberately alter files. Candidate access is restricted separately
by the declarative interface and native mutation isolation.

## Held-out comparison

```bash
python3 scripts/final_test.py run
```

This command validates the sealed structure, full protocol and all selection
evidence. It invokes the same trusted `R/forecast.R` adapter separately for the
baseline and selected model, fitting through 2009 and forecasting 2010. The
estimator, acceptance policy, origin initialization, carried-forward rates and
covariates, centering corrections, 1,000 simulations and common seed 2010001 are
unchanged. Canonically identical structures are deduplicated. The evolution
evaluator's prohibition on target 2010 remains intact.

**Both prediction sets must exist, pass their native audits and have prediction
hash commitments before this script even hashes the 2010 outcome file.** It then
records permanent first-access time, records the outcome hash, and invokes the
same trusted R scorer. The final eligibility masks must match. Changed outcomes,
changed selected models, changed protocol or changed selection evidence cause
failure. Resumption may finish interrupted scoring for the same sealed
comparison; it does not permit a new selection.
Resume with exactly `python3 scripts/final_test.py run`. Both reserved prediction
commitments are verified again before any scoring or target access. An
uncommitted prediction left without its native audit is archived under
`incomplete_publications/` and regenerated with the same fixed seed and retained
fit. A missing or altered **committed** prediction is not regenerated; its
original artifacts must be restored. Incomplete score/mask publication can be
repeated from the unchanged committed predictions and reserved target hash.
An already completed comparison is verified and preserved without rewriting its
completion timestamp.

The complete comparison and secondary diagnostics are published only under
`results/final_test/comparison.json` and its protected artifact directories,
never into native mutation feedback or inspirations. A fitting or scoring
failure is preserved as an execution failure, without a scientific score.
All stages acquire the project's reentrant serial R execution lock before any
per-cache lock. Nested trusted evaluator calls reuse it, preventing deadlock
between workflows that share scientific caches.

2010 is held out from **our evolutionary search**, not historically untouched:
the original study already evaluated that year. Once its outcomes are accessed,
any subsequent model revision is exploratory. Report the observed final PR-AUC
difference, including zero or negative values, separately from development
fitness and reproduction coverage.

Implementation verification covered Python compilation and CLI argument parsing,
15 unique enumerated specifications, interrupted uncommitted publication
recovery, immutable prediction commitments, refusal to regenerate missing
committed artifacts, incomplete scorer-output recovery and cache reuse. Recovery
checks used temporary synthetic Python fixtures with the R runner replaced;
they did not launch R, access actual target outcomes or establish scientific
forecast validity.
