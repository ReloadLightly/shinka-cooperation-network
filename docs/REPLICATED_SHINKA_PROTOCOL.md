# Step 5A: generalized replicated native Shinka evaluator

## Scientific scope and implementation status

This is `multiobjective-replicated-v1`, a separately versioned development-only
interface. It generalizes the demonstrated Step 4 mechanism comparison, not the
research question. Candidate ASTs describe admissible native network-selection
statistics, functional parameters and interactions. Original density, controls,
spending-equation structure and joint statistical estimation remain unchanged.
It is predictive specification discovery grounded in Model 3, not policy control,
a complete paper reproduction or independent identification of efficiency/free riding.

The legacy evaluators, launcher, settings, score archives and frozen campaigns
are not changed. Do not give this configuration to the old launcher. New entry
points are `scripts/replicated_evaluation.py` and `scripts/run_shinka_replicated.py`.
No model call, fit or forecast is required by Step 5A validation. A genuinely new
candidate requires an explicit execution window and canonical-admission budget.

## Evidence reuse and the newly identified tie defect

The original eight cells are pinned at commit
`104ba59d81a92f1c98b77c89178fad9178b6ccb4`, with the exact cell commitment hashes
in `configs/replicated-evidence-v1.json`. Import verifies every committed file,
all four years, source-code compatibility, policy receipts, fit hashes, fixed
forecast guards, seeds, masks, and the complete five-batch replication set.
A renamed/reformatted specification cannot get different numerical evidence.
Missing or altered evidence stops replay; it does not trigger a new fit.

Step 5A additionally detected that averaging five floating-point probabilities
can split mathematically identical pooled counts by about machine precision.
PRROC distinguishes those slightly different scores, so this is relevant even
when absolute probability differences are tiny. The original Step 4 result is
preserved and reproduced, not overwritten or relabelled. The new protocol sums
INTEGER simulated network successes and divides by total endpoints once.
Every batch must first lie on its declared 1/1000 probability grid.

`R/replicated_score_view.R` reads saved native predictions and the already saved
scored labels/masks, reproduces original batch and pooled metrics with the
pinned PRROC, and records corrected pooled and delete-one network metrics. It
never reads a target packet or generates new predictions. Spending batch means
and RMSE calculations are unchanged. The separately committed score views bind
the source cell, correction source and returned metrics. The integer-count
operation is also used for future candidates by `R/replicated_evaluation.R`.
Replaying original scores and using corrected scores are different recorded
checks; neither is falsely reported as fresh experimental replication.

## Cross-session diagnostic comparison

Read-only native replay exposed tiny CPU/BLAS roundoff differences in the two
report-only covariance spectral summaries (minimum eigenvalue and condition
number). The new consumer still requires exact agreement of EVERY acceptance
field, convergence ratio, coefficient and standard error, with valid status both
recorded and recomputed. Only those two reporting summaries use a fixed 1e-8
relative comparison. The covariance matrix and accepted-fit file remain hash-bound
and unchanged. This is portability for derived reporting, not a relaxed acceptance
criterion or rewritten fit. The diagnostic difference record is preserved.

## Evaluation and numerical execution

Every candidate uses targets 2006–2009, training 1990 through target-1. The
approved precision-before-continuation policy retains strict 0.1/0.25 thresholds,
non-ratio native validity, fixed supplemental seeds and the unchanged optimizer
schedule. The forecast consumer verifies authoritative_n3, including successful
3,000-draw reassessments on originally short optimization attempts.

Every accepted model/year receives five independent 1,000-endpoint batches.
Probabilities are pooled before PRROC, Brier and ordinal-spending RMSE are
computed. No partial-year fitness, averaging of batch AUCs as the primary point,
complexity bonus, runtime bonus or low-spending reward is introduced. Formation,
dissolution and structural diagnostics remain visible but are not extra objectives.

Known reference/GWESP specifications retain their declared Step 4 seed sets.
Other canonical specifications deterministically receive a reserved block of 20
seeds from their canonical SHA256. A persistent ledger detects cross-specification
collisions and refuses them; it never chooses a better-performing replacement
seed. Optimization and supplemental diagnostic seeds follow the existing policy.

Future novel evaluations use one local serial numerical worker. At most four
optimization attempts, three supplemental assessments and five forecast batches
per model/year are allowed, with a cumulative four-hour native wall budget per
cell. All probabilities are committed before that year's outcome packet opens.
Completed operations resume by commitment. An explicitly recorded cooperative
boundary may restart the outer fit call using completed native checkpoints;
incomplete atomic R operations cannot be rerun automatically. Source drift,
interruption and missing inputs are pauses, not learned predictive losses.

## Declared selection rule

The three reported objectives remain raw equally weighted annual improvements:
J1 = candidate PR-AUC minus reference; J2 = reference Brier minus candidate;
J3 = reference spending RMSE minus candidate. The five-block delete-one jackknife
and t(4,0.975)=2.7764451051977987 remain explicitly approximate conditional
Monte Carlo diagnostics. They omit fitting uncertainty, temporal generalization,
causal identification and selective/multiple-comparison coverage.

An MC-resolved dominance comparison must FIRST be strict point Pareto dominance.
For every objective its point difference minus t4 times the jackknife SE of the
PAIRWISE difference must be nonnegative, with at least one strictly positive.
The common reference cancels before calculating the pairwise SE; its noise is not
counted twice. Because this relation is a subset of point dominance, its directed
graph cannot cycle, although it need not be transitive. Nondominated sorting
retains every candidate not resolved-dominated (archive size remains a soft target).
A two-candidate parent tournament selects the resolved-dominant model; otherwise
it chooses uniformly. Inconclusive intermediate models can therefore reproduce.
This is an exploratory selection heuristic, not a statistical certification.

Operational scales are frozen from the reference ALONE: 1 minus its mean PR-AUC,
its mean Brier, and its mean spending RMSE. They measure fractional reductions
in reference deficits. Zero/invalid reference deficits cause refusal, not adaptive
rescaling. Diversity uses tanh(J_j/scale_j), bounding each coordinate. Bandit and
prompt credit use `2+tanh(mean(J/scale)-t4*SE(mean(J/scale)))`. This is a declared
uncertainty-averse operational preference; raw predictive objectives remain
separate. Equal fractional improvements are a design preference, not a scientific
fact about the relative importance of agreements and spending.

The rule was chosen after inspecting the development studies; it is not an
untouched confirmatory test. It does not eliminate winner's curse or make five
blocks adequate for every model. A full archive of original evidence is retained.

## Native machinery and duplicate accounting

The original pinned Shinka controller owns proposals, patch application,
inspirations, islands, migrations, prompt evolution, bandit and meta-memory.
The project replaces the parent/archive selection policy explicitly; it does
not claim to use Shinka's original parent strategy unchanged. Configured two
islands, diff/full/cross mixture, UCB model selection, novelty checks, prompt
archive and meta-memory remain enabled. Configuration is not proof that each
mechanism has already been used in live evolution.

Canonical duplicates remain correct measured models and retain their ancestry,
but do not count as new evaluated structures. Three narrowly checked AST changes
in the pinned native post-persistence method skip duplicate prompt/meta credit
and submit no predictive bandit reward for duplicates or preexisting Step 4
measurements. Native bandit completion/cost accounting remains active; a missing reward uses
the pinned bandit's native worst-reward imputation, not a positive predictive gain. This
process-local compatibility hook does not rewrite native source or scientific
scores. It fails closed if the expected native code structure has changed.

The new pause status is recognized by the existing native pending-evaluation
queue. Population, archive and pending lineage stay in the same SQLite database;
meta, bandit and prompt state use native persistence. A publication checkpoint is
not a reason to reset the search. Progress reports must distinguish imported
measurements, unique new admissions, completed valid canonical models, invalid
models, duplicate source variants and paused work.

## Execution handoff and remaining live boundary

First hydrate the exact preserved evidence when it is not already in the checkout:

```bash
python3 scripts/hydrate_replicated_evidence.py --destination /tmp/step4-evidence --fetch
export SHINKA_REPLICATED_EVIDENCE_ROOT=/tmp/step4-evidence
```

The dedicated launcher defaults to a dry resolution:

```bash
python3 scripts/run_shinka_replicated.py --results-dir results/evolution_replicated
```

An actual launch must explicitly supply `--window-hours`, `--max-new-specs` and
`--execute`. No default model-call or compute budget is silently selected here.
The numerical budget is a cumulative canonical-admission limit, including failed
new models. Repeated sources and cached models do not consume another admission.
It cannot be silently reset or raised on resumption; further authorization requires
an explicit budget change. A resumed campaign retains its scientific/search binding.

The configured headless model aliases and subscription access must be available
in the execution environment. Step 5A does not authenticate them, consume tokens,
upload credentials, or claim that GitHub's numerical jobs provide LLM inference.
The local runtime must have the pinned R and Shinka installations and existing
isolated headless/embedding services. There is no automatic remote GitHub job
backend or paid provider fallback in this version. The selected machine, actual
model routes and an explicit resource authorization remain launch prerequisites,
not another model-reconstruction study.

No final-year evaluator is enabled by this change. Finalist locking and the
reserved-year reporting protocol must be reviewed before that later phase.


## Step 5C operational handoff

See `docs/STEP5C_HANDOFF.md`. The dedicated launcher now checks the pinned local
runtime and isolation before constructing a campaign, derives the embedding port
from configuration, refuses occupied service ports, and waits for owned embedding
and WebUI services to answer health probes before constructing the native runner.
Only its own process groups are cleaned up. No inference is performed by preflight.

A new typed, hash-bound numerical-policy-exhaustion record replays as the same
invalid evaluation, including in read-only mode and without another admission.
Uncommitted legacy failures, interrupted operations and corrupt evidence remain
pauses. Native statistical settings and scientific metric/selection definitions
are unchanged. Source fingerprints change: do not pull this repair beneath an
active old controller or rewrite an existing campaign's binding. The preserved
Step 4 evidence remains compatible and is not refitted for this repair.
