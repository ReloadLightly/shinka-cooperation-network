# Fixed temporal evaluator, version 1

Status: implemented; source parity, metric and native target-independence diagnostics
have passed. Accepted full-development fits, seed-zero evidence and structural
candidate results remain separate launch gates.
The machine-readable specification is `configs/evaluator-v1.json`.

For target t in {2006, 2007, 2008, 2009}, fit the candidate and original predictive
Model 3 independently on annual observations 1990,...,t−1. Start a single annual
unconditional RSiena interval at the observed t−1 state. Use the last estimable
training rate for each process (all intervals one year). Future covariates and
composition follow information at the origin. Never use target state, change
counts, rates, centering, imputation or realized future covariates to predict.

The original engine and controls, defense spending objective and sample rules
remain fixed. The evolutionary program returns a catalog-validated structural
specification. Coefficients are estimated, not supplied by the program. Candidates
are interpreted using a strict literal AST, without Python execution or imports.

Generate exactly S=1000 endpoints per model/year with a common seed schedule.
First average binary endpoint ties into p(i,j,t), then score eligible i<j pairs:

```r
PRROC::pr.curve(scores.class0=p[y == 1],
                scores.class1=p[y == 0], curve=FALSE)$auc.integral
```

`scores.class0` is the positive class. PRROC is pinned to 1.3.1. The package's
integral is not sklearn average precision. Masks are fixed from target presence,
origin sample and valid observations, independently of predictions; exclusions
must be saved and the same mask used across specifications. A missing class
makes a subset AUC unavailable, not zero.

Define delta_t = AUC(C,t)−AUC(B_t,t), F=mean(delta_2006,...,delta_2009), equally
weighted. Native `combined_score=1+F` works around the pinned upstream exact-zero
archive bug; raw F and all annual quantities are public. There is no other reward.
Every year must succeed. Invalid specifications, nonconvergence, timeouts and
malformed outputs produce `correct=false`, an actionable error and no valid F.

Accept finite identified fits only when every absolute convergence t ratio is
below 0.1 and overall maximum convergence ratio is below 0.25. Use nsub=3,
n3=1000 and up to three identical-policy attempts, continuing with prevAns.
Retain attempts and diagnostics; validate this policy against pinned RSiena docs
before launch. Baseline and candidates use the same policy.

Cache identity includes the canonical specification, source/preprocessing hashes,
training split, software versions, full evaluator settings, budget and seeds.
Save predictions before a separate scoring process opens labels. Baseline seed
identity is tested independently of cache identity and source effects are checked
against the authors' actual effect construction.

Secondary diagnostics: ROC-AUC, Brier score, ordinal spending RMSE, formation and
dissolution conditional performance, persistence benchmark, network degree and
triangle diagnostics, runtime and memory. These never enter F. Do not use dyad
independence for inferential claims. Conventional structural search receives the
same space and comparable number of full evaluations. Fresh-randomness finalist
checks precede the locked final 2010 comparison. Only then may 2010 labels be read
for final scoring. 2010 is held out from this search, not historically unexamined.

## Recorded implementation and execution details

The extension runs one native R process because of host memory limits; the
paper reproduction retains the original two-worker setting. Training seeds are
12345, 12346 and 12347 for the three attempts. A complete fit also requires
native successful termination, all 1,000 phase-3 iterations, a finite full
covariance matrix, positive finite standard errors and no unexpected native
parameter fixing or divergence. Covariance eigenvalues are reported without an
arbitrary scale-dependent cutoff.

Each target's combined fit/forecast process has a ceiling of 86,400 seconds,
computed from three 21,600-second estimation allowances plus a 21,600-second
forecast allowance. The allowances are summed into a process deadline; they are
not separately enforced deadlines for individual R attempts. Scores have a
300-second stage limit. Native candidate evaluation additionally has a declared
600-second margin, giving 347,400 seconds for all four years. The native campaign
has a separate, measured, finite cumulative walltime budget.

The corrected forward schema explicitly sets origin-inactive native activity
flags and native structural-zero code 10 only on dyads involving those inactive
actors. This prevents an RSiena 1.3.10 receiver-activity edge case while retaining
the complete training-country universe. Eligible dyads remain unrestricted.
The native diagnostic verifies binary endpoint ties, inactive zero ties and
unchanged inactive spending, both active tie formations/dissolutions, unchanged
predictions after inaccessible target perturbations and behavior support 1–11.
Old forward schemas cannot be scored. Details and original-versus-extension
composition distinctions are in `SOURCE_MODEL_MAP.md`.
