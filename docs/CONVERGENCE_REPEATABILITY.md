# Step 3C — conditional convergence-diagnostic repeatability

## Evidence reviewed before design

The completed Step 3B pilot is preserved at commit
`87b679c4a08171c50c083ea64ed88f83d3a833c5`. All twelve native-artifact commitments
were checked in the review container. An independent NumPy calculation from the
3,000 x 58 CSV reproduced both convergence summaries to <1e-12:

| Same saved third-attempt vector | Maximum absolute individual ratio | Overall ratio |
|---|---:|---:|
| First 1,000 fresh draws | 0.094229644281 | 0.262082693272 |
| All 3,000 fresh draws | 0.050915035190 | 0.190819382708 |

Native execution completed with all 58 coefficients unchanged at every guarded
simulator entry/exit and after termination. No optimization, refit, forecast or
outcome scoring was performed. No warnings were captured during the guarded
native call. The recorded native process wall time was 826 seconds and maximum
RSS 545,352 KiB. The guarded interval was 819.886 seconds; these are different
measurements, not contradictory runtime claims.

This establishes that an unchanged vector can fail a 1,000-draw check and pass
its nested 3,000-draw check. It does not establish repeatability, a true moment
root, a causal effect of precision across independent replications, or a suitable
production policy. The original third-attempt rejection remains unchanged.

The external review's convergence-lottery concern motivates this study, but its
claims that different historical fits have the same true convergence state or
that candidate signal-to-noise is approximately one are not assumed here. The
paper's substantive burden-sharing hypotheses are not tested by this diagnostic.

## Frozen finite design

`configs/convergence-repeatability-v1.json` is committed before new simulation.
The two coefficient vectors are the third saved 2009 attempt and the accepted
fourth attempt (both fitted on 1990–2008, 161 actors, 58 parameters). The latter
is a comparison vector, not ground truth or a newly optimized fit.

| Vector | Seeds | New runs |
|---|---|---:|
| Third attempt | 2009301–2009305 | 4: reuse the completed 2009301 pilot |
| Fourth attempt | 2009401–2009405 | 5 |

Exactly nine new cells, 3,000 draws each (27,000 new draws), are authorized.
Each cell retains the native serial route, `nsub=0`, `simOnly=FALSE`, original
fixed/test flags and all other saved scientific settings. The vectors use
disjoint seed sets; they are not treated as paired random-number experiments.
The first 1,000 and full 3,000 draws within each cell are nested and correlated.
All cutoffs stay strictly <0.1 individual and <0.25 overall.

The old pilot has already been observed. Accordingly, the **four new third-vector
repetitions are reported separately** as the unobserved-at-design confirmation
set. The five-repetition third-vector summary includes and labels the pilot as
an additional descriptive view. All five fourth-vector repetitions are new.
The decision to continue was informed by the pilot and is disclosed here.

## Execution and resource boundaries

A real stopped initialization of the fourth vector must pass before numerical
cells start; it uses the same source-verified no-simulation procedure as Step 3A.
The closed nine-cell matrix has at most nine isolated standard `ubuntu-22.04`
GitHub jobs concurrently. Each R process remains serial and single-threaded;
parallel scheduling does not change the random stream within any cell.

Each native process has a 3,600-second limit and each GitHub cell job a 75-minute
limit including setup. At the measured pilot cost, nine new diagnostics suggest
about 123 minutes of aggregate guarded native time, not a guaranteed duration.
No additional compute is authorized by a publication checkpoint or numerical
failure. The branch-level run claim and attempt-number checks reject duplicate
workflow attempts. The matrix retains all declared cells even if a separate
cell fails; it never replaces a seed or retries a result to obtain a pass.

Standard hosted computation in this public repository falls under GitHub's free
public-repository runner policy. Artifact/cache storage is separate. The workflow
reuses the existing native-runtime cache without writing nine new caches and sets
new artifact retention to **one day**. Full scientific evidence is published to
the study branch for longer-term preservation. It does not inspect or change the
user's billing settings, private repositories, local workers, or original results.

## Evidence and reporting

Each completed cell retains XZ-compressed raw statistic and score arrays
(`sf`, `ssc`, `sf2`), coefficient and target vectors, full native moment covariance,
derivative and coefficient covariance, warnings, source hashes, native logs,
resource usage and coefficient guard records. A compact native-diagnostic list
replaces duplicative serialization of the full sienaFit object and traced
closures; no original saved fit or raw scientific array is altered. The prior
pilot is referenced rather than stored or computed again.

Report every cell, including threshold failures and native-validity warnings.
Report means, sample standard deviations, extrema, threshold pass counts and
1,000-to-3,000 threshold-status changes. A joint ratio-threshold pass is not
necessarily full native validity. Count only complete seed-level runs as
replications; do not count 58 coordinates, 18 periods, or nested prefixes as
independent sample sizes. Incomplete cells remain explicit and prevent a
complete-study label. Five seeds provide a rough descriptive characterization,
not a reliable population pass probability or evidence of global identification.

No production convergence gate, forecast budget, objective scale, finalist set,
evolutionary archive or historical acceptance decision is changed. The study
cannot measure fitting-randomness uncertainty, forecast quality, historical
generalization, causal burden-sharing effects, or ShinkaEvolve improvement.
Step 4 and any production-policy change require a separate decision.

## Reproduction and verification

With the pinned runtime available, `check` verifies inputs without simulation.
A fresh cell needs an explicit closed-grid fit and seed plus `--execute`:

```bash
python scripts/convergence_repeatability.py check
python scripts/convergence_repeatability.py run --fit attempt3 --seed 2009302 --execute
python scripts/convergence_repeatability.py verify-cell --fit attempt3 --seed 2009302
```

An existing output is refused. Do not run an already completed cell in a clean
checkout to get a different outcome. The 2009301 pilot is never an allowed new
cell. The exact preflight and pilot implementations stay hash-bound; changes
require a reviewed protocol revision rather than silently accepting source drift.
