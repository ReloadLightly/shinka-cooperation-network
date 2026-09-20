# Original-source reproduction audit and coverage

Audit checkpoint: 2026-09-20. Source inspection, exact-version installation and
software diagnostics have been executed. No completed reproduction of Figures
5–7, the full equilibrium diagnostic, or the published empirical prediction
scores is established by this audit. Ongoing run state and measured outputs are
reported separately in `results/paper_reproduction/` and the research log.

## Two scientific modes

`paper_reproduction` follows the shipped R/RSiena source, including documented
text/code discrepancies. Its illustrative ABM uses assigned coefficients and
generated covariates; these are not statistically fitted contemporary-country
preferences. The empirical SAOM estimates coefficients on observed data.

`evolution_forecast` is our separately specified extension. It changes eligible
network-objective structure, retains the spending objective and empirical
controls, estimates coefficients from the same training observations as its
baseline, and evaluates one-year predictions with the fixed PRROC fitness.
Its development targets are 2006–2009; 2010 is reserved from evolutionary
selection. It does not reproduce the authors' exact validation protocol. Better
predictive discrimination would not establish improved national security or
optimal national policy.

## Published reference values and actual protocol

The [appendix](https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S0020818322000315/resource/name/S0020818322000315sup001.pdf)
reports these references on printed page 11:

| Published outcome | Reference | Location |
|---|---:|---|
| DCA-network PR-AUC | 0.927 | Figure A4, SAOM PR curve |
| DCA-network ROC-AUC | 0.985 | Figure A4, SAOM ROC curve |
| Defense-effort RMSE | 0.397 | Figure A3 note; ordinal category units |

These numbers are reference values, not hard-coded success criteria or results
obtained here. The appendix page 10 describes training Model 3 on 1990–2009 and
predicting 2010. The shipped implementation differs in several consequential ways:

| Issue | Source evidence | Required treatment |
|---|---|---|
| Training endpoint | `02.appendix.R:89–97` sets `yr <- seq(1990,2008,1)` before rebuilding and fitting. `00.gof.predict:117–124` rebuilds 2009–2010 validation observations. | Preserve this in source reproduction; disclose the text/code mismatch. |
| Validation-derived rates | `00.gof.predict:210–226` saves initialization values from the validation data, imports training coefficients with `updateTheta`, then restores network and spending rates. Saved density/linear starts are not subsequently restored. | Preserve for reproduction. Our forecast uses the last estimable training rate, with a fixed duration rule. |
| Validation data object | `00.gof.predict:126–159` includes both observed validation dependent-variable waves. The validation algorithm has `nsub=0,n3=1000` and leaves `cond`/`simOnly` at their native defaults. | Do not describe this as the extension's explicitly unconditional, target-inaccessible construction. |
| Symmetric dyads | `00.gof.predict:253–286` first averages simulated adjacency matrices, sets diagonal entries missing, flattens both matrix directions, omits missing rows and scores. Its logit comparison instead filters `ccode1 < ccode2` at line 546. | Preserve the source scoring in reproduction; score each eligible unordered pair exactly once in the extension. |
| Spending scoring | `00.gof.predict:307–322,358–368` computes mean simulated category by actor and RMSE on that unrounded mean. Rounded values are used separately for category accuracy. | Report RMSE in categories, not currency or percent GDP. |
| Conventional regression comparison | `00.gof.predict:327–355` rebuilds the full span including the final year for covariates and predicts from target-year regression rows. | This original comparator is not our origin-information-only conventional specification search. |

The original network PR computation already averages binary simulated ties before
calling PRROC; the extension retains that aggregation. Its use of all scores with
binary `weights.class0` is an alternative supported PRROC interface to passing
positive and negative scores separately. The pinned package help confirms their
class semantics.

## Model identity and executable mechanisms

The predictive model is **empirical Model 3**. The authoritative effects are
constructed in `00.gof.predict:48–101`, using `ds=1:5`, `ms1=c(1,7)` and
`ms2=c(1,2,3,4,5,6,8)` from the appendix caller. The network objective has density,
`degPlus`, `transTriads`, five dyadic controls (alliance, distance, UN voting
distance, trade, NATO), and alter effects for democracy, capabilities and defense
effort. The spending objective has its linear/quadratic shapes, seven monadic
controls, network outdegree and `behDenseTriads(parameter=6)`. Empirical Model 4
adds the `totAlt × behDenseTriads` spending interaction; it must not be substituted
for the predictive baseline. The fuller bridge/effect map is in
[SOURCE_MODEL_MAP.md](SOURCE_MODEL_MAP.md).

The main paper's equations (3)–(4) define linear combinations of network and
behavior statistics; equations (9)–(10) are their empirically estimated versions.
Native RSiena simulates the continuous-time process and stochastic actor choices.
`modelType=c(dv.net=3)` retains unilateral initiative with partner confirmation;
`behModelType=c(milex.beh=1)` retains ordinal spending changes. Appendix A1
equations A1–A3 and its page-4 algorithm describe the choice process and its
one-unit behavior microsteps. Our implementation must use the native engine,
not an invented utility-function simulator.

## Illustrative ABM and Figures 5–7

`03.ABM.R` initializes seed 12345 and sources `ABM/00.getData`, `00.simulate`,
`00.equilibria` and `00.makeFigures`. The calibration script constructs a
2000–2001 two-wave object, initializes from 2000, retains countries represented
in both years with some observed defense effort, discretizes spending using
left-closed bins `[0,.01), …, [.09,.10), [.10,1)`, and imputes remaining missing
categories with the calibration object's median. It generates exponential
monadic and symmetric dyadic covariates using the specified random stream.
The observed calibration run records **159 actors**, with no sample reduction.

| Figure / mechanism | Original executable experiment | Requested budget |
|---|---|---:|
| 5(a,b): public-goods versus positive bilateral influence, equation (5) | `outdeg` spending coefficient γ from −0.05 to +0.05 by 0.0025; other network coefficients zero; behavior linear −0.5, exogenous effect 0.75; both process rates 200. | 41 settings × 25 endpoints |
| 6(a): triangle efficiency with network coevolution, equations (6)–(7) | ψ from −0.005 to +0.005 by 0.00025; γ=0.025; network density −4, degree 0.1, transitivity 0.5, alter spending 0.025 and generated covariate coefficients 0.1; rates 100. | 41 settings × 100 endpoints |
| 6(b): preferential attachment alternative | Same ψ grid and spending objective; density −6, transitivity −0.75, `degPlus` removed, `inPop` added at 0.35; rates 100. | 41 settings × 100 endpoints |
| 7: efficiency versus conditional free riding, equation (8) | ψ from −0.005 to 0 by 0.00025 and η from −0.0001 to 0 by 0.000005; η enters `totAlt × behDenseTriads`; regular coevolution network profile and rates 100. | 21 × 21 settings × 25 endpoints |
| A1: statistical equilibrium diagnostic | Both rates at 1, then 5 through 500 by 5; γ=0.01, generated monadic behavior effect 0.75, linear −0.5, other objective effects zero. | 101 settings × 10 endpoints |

All original ABM calls use `cond=FALSE`, `simOnly=TRUE`, `nsub=0`,
`useStdInits=FALSE`, `maxlike=FALSE`, two cluster workers, and the seed-bearing
algorithm objects. Native network and behavior dependent objects set
`allowOnly=FALSE`. Figures 5–6 summarize simulated mean ordinal spending;
Figure 7 aggregates each grid cell and caps its plotting values to [2,3]
(`00.makeFigures:94–119`). That plotting cap must not overwrite archived raw
simulation summaries. Equilibrium plots report mean behavior, network density,
global transitivity and eigenvector centralization with 99% simulation-mean
intervals. These intervals concern simulation variability, not independent-dyad
empirical uncertainty.

The exact requested workload is
`41*25 + 82*100 + 441*25 + 101*10 = 21,260` endpoints in **665 calls**.
RSiena 1.3.10 `R/phase3.r:26–35` rounds `n3` upward to a multiple of its
iteration-worker count. With the source's two workers and default `clusterIter`,
`n3=25` becomes 26. Consequently the expected returned count for a successful
full campaign is **21,742**, not 21,260. Each actual result still requires an
explicit `length(sims)` check. The extension's 1,000 endpoints divide evenly by
two and must be checked independently.

Two further text/code details are preserved explicitly. Appendix Table A1 prints
the degree statistic using raw degrees, whereas the ABM sets `degPlus`'s internal
parameter to **2**, activating square-root degree activity/popularity in
`BothDegreesEffect.cpp`. The empirical predictive code uses default parameter
**1**. Also, appendix equation A7 prints the monadic network term using `c_i`,
while main-paper equation (6), Table A1 and the executable `altX` effect use the
alter's `c_j`. The executable settings are the reproduction reference; these
differences are not silently corrected.

## Estimation and remaining coverage

The main empirical estimates use `nsub=5,n3=3000`; the prediction fit uses
`nsub=3,n3=1000`; the source structural-zero GOF fit uses `nsub=5,n3=1000`.
All use seed 12345 and two workers. These are distinct scientific workloads.
`00.gof` replaces absent-country network rows/columns by structural zeros for
its GOF fit; this treatment is not interchangeable with the main composition
object or the extension's prospective origin-eligibility rules.

RSiena 1.3.10 [`man/siena07.Rd`](../vendor/RSiena/man/siena07.Rd), lines 101–107,
recommends absolute convergence t-ratios below 0.1 and overall maximum
convergence below 0.25, and recommends restarting from the previous estimates
with `prevAns` if needed. These concern convergence statistics, not coefficient
significance tests. The extension's predeclared finite-estimate, positive-SE and
three-attempt policy is an additional project requirement, not a claim about an
automatic acceptance/retry loop in the authors' scripts.

| Coverage item | Audit checkpoint status |
|---|---|
| Primary archive, provenance and untouched source | Verified |
| Exact R/RSiena environment and fixed PRROC | Executed and version-checked |
| ABM calibration and complete workload definition | Executed calibration; full grid identified |
| Complete Figures 5, 6 and 7 | Not yet reproduced |
| Complete equilibrium Figure A1 | Not yet reproduced |
| Four main empirical models and main-paper post-estimation figures | Not yet reproduced |
| Original Model 3 prediction and published PR/ROC/RMSE | Not yet reproduced |
| Original network/behavior GOF Figure A2 | Not yet reproduced |
| Appendix robustness and sensitivity battery | Not yet reproduced |
| Extension leakage/metric/software diagnostics | Separate verification evidence; not article reproduction |

A bounded run completing one original grid point establishes execution of that
point. A reduced diagnostic establishes only its labelled diagnostic result.
Neither establishes full-figure coverage, equilibrium across the rate grid,
valid empirical forecasting, nor evolutionary improvement.

## Executable original empirical callers

`scripts/paper_empirical.py` prepares two independent original-source runs:

```bash
# Safe preparation only: verifies/copies the archive files and writes callers.
# Neither command starts R or evaluates 2010 outcomes.
python3 scripts/paper_empirical.py --analysis main_paper
python3 scripts/paper_empirical.py --analysis appendix_prediction
```

Both work copies and `prepared.json` manifests have been materialized. Each
contains all 27 untouched archive files, with every hash checked against the
source manifest. A separate generated caller supplies the local working
directory. For `main_paper`, it is the entire original `01.mainPaper.R` with
only `YourDirectoryHere` replaced. This includes descriptive/hive figures, all
four empirical model fits and the original post-estimation routines. It does
not run the separate illustrative ABM caller.

For `appendix_prediction`, the generated caller copies original `02.appendix.R`
lines 1–68 and 82–99, again replacing only the directory placeholder within
those statements. This explicitly scoped entry point skips the earlier
distribution plots, robustness/sensitivity fits and structural-zero GOF block.
It then executes the **complete untouched** `scripts/00.gof.predict`, including
its ordered/binary-logit comparisons and ancillary importance outputs. It
preserves the original 1990–2008 training span, 2009–2010 validation object,
validation-derived rate resets, full symmetric-matrix scoring, Model 3 effects,
seeds, original estimator/simulation budgets and two-worker execution. Omitting
earlier appendix analyses is a scope decision; this is not an execution of the
whole appendix or a proof that any hidden session-state effects are identical.

The Python orchestrator starts a fresh standalone R process. No R wrapper state
is placed in the authors' global environment, so their `rm(list=ls(all=TRUE))`
and `gdata::keep()` calls cannot erase orchestration or change its control flow.

Both empirical callers consume 2010 observations. **Their execution is blocked
until our sealed final-test comparison is complete**, even if only the main
paper's descriptive section would run first. This protects 2010 from informing
our evolutionary search. Once `scripts/final_test.py run` has completed:

```bash
python3 scripts/paper_empirical.py --analysis main_paper --execute
python3 scripts/paper_empirical.py --analysis appendix_prediction --execute
```

The wrapper verifies the locked selection/completed comparison, obtains the
shared scientific execution lock, and invokes the exact R command recorded in
`prepared.json`. The default seven-day outer timeout changes no R scientific
settings; set `--timeout-seconds` explicitly if a different outer scheduling
limit is needed. Complete stdout, stderr, process status, resource measurements
and command events are saved beside `execution.json`. Authors' model objects,
figures and tables stay under the run's `work/output/`,
`work/figures_tables_main/` and `work/figures_tables_appendix/` directories.

For inspection, the prepared main command is:

```bash
# Underlying R invocation, AFTER the same completed-final-test gate.
# Prefer the guarded Python --execute command above.
environment/run-r results/paper_reproduction/original-main_paper/work/run_original_main_paper.R
environment/run-r results/paper_reproduction/original-appendix_prediction/work/run_original_appendix_prediction.R
```

These callers currently have **no per-call or within-fit checkpoint wrapper**.
They preserve the original source sequence and RNG handling; they do not inject
an unverified substitute fit cache. Original intermediate `save()` outputs are
retained, but the shipped callers re-estimate on restart. An interrupted or
failed attempt therefore cannot resume in the same directory. Preserve that
attempt and explicitly start another, for example:

```bash
python3 scripts/paper_empirical.py --analysis appendix_prediction \
  --run-dir results/paper_reproduction/original-appendix_prediction-attempt2 --execute
```

Repeating a successfully completed command only verifies its saved output
hashes and reports completion; it does not rerun the analysis. Successful R exit
is recorded separately from scientific reproduction verification. These
empirical callers have been materialized and statically checked, **not run** at
this checkpoint; no published metric is claimed as reproduced by preparing them.
