# Research log

## 2026-09-20 — initial reconstruction

Started from the actual checkout at `/home/roland/actir/shinka-cooperation-network`.
The `main` branch had no commits or tracked files. Origin points to the requested
ReloadLightly repository. No ancestor `AGENTS.md` was found. R, Rscript, Fortran,
Docker and Podman were absent. Python 3.10.12 and Codex CLI 0.155.1 were present.
Host reports Ubuntu 22.04.5, 3.7 GiB physical RAM and 1 GiB swap; available RAM
was about 1 GiB. Large original jobs must be measured before scheduling.

Downloaded Harvard Dataverse file 6429192. SHA256 exactly matches the supplied
`2f4c2c02e3969437976c505098848e0ef7333466aeba3cccd807b3b44ba75308`.
Dataset version is 1.0 (released 2022-08-29); metadata declares CC0-1.0.
Preserved archive and extracted read-only source; per-file checksums and metadata
are in `sources/manifest.json` and `sources/metadata/dataverse.json`.

Independent work: local R/RSiena installation; original empirical model bridge;
native Shinka source inspection. No evolution or held-out scoring has run.

## 2026-09-20 13:38 UTC — installed core, first real executions

Exact R 4.2.1 / RSiena 1.3.10 / PRROC 1.3.1 installed; environment lock and
795-file RSiena source-integrity audit retained. Native compilation took 150.73
seconds and 219,508 KB peak RSS. Actual PRROC metric fixtures passed, including
probability-first AUC 1 versus mean hard-network AUC 2/3.

Annual coverage confirmed; first development training sample has 161 actors,
160 active at the 2005 origin. ABM calibration retains 159 countries.
Materialized past-only predictor packets separately from protected targets.
Original source audit initially ran out of memory before the final comparison;
its earlier reported pass was incorrect and withdrawn. Native forward diagnostic
used four endpoints with initial coefficients, not a fitted model or ranking
score. It produced identical endpoints when inaccessible synthetic outcomes
changed and verified mean reparameterization algebra, support 1–11 and
allowOnly=FALSE. A fitted baseline still must pass all acceptance gates.

Launched full original ABM first cell (n3=25, rates=200, two workers, seed12345),
with per-call checkpoint and call budget1. First sandbox attempt failed on PSOCK
socket creation; authorized execution outside that restriction is running.
Also started actual 2006 baseline estimation (nsub3,n3=1000); available memory
fell to ~150 MiB with swap full, so further large R jobs are deferred until one
finishes. Process logs and GNU-time resource measurements are preserved.

## 2026-09-20 13:52 UTC — measured resource limitation and serial execution

The concurrent baseline process was killed by signal9 after195.80 seconds,
peak421,968KB, before any accepted fit. The original high-rate ABM pilot was
stopped deliberately at899.03 seconds without a completed endpoint batch:
parent peak435,660KB, workers approximately137MB each. Full-workload inference
from endpoint counts alone is inadequate; this first dense-neutral rate200
cell is expensive. Preserve all logs, retry completed-call checkpoints only,
and prioritize source parity / leakage audits then a serial baseline fit.

Source audit verified 665 ABM calls /21,260 requested endpoints. Native
two-worker rounding implies21,742 returned endpoints if the full grid succeeds.
The empirical degree effect is parameter1; ABM uses parameter2 (square roots).
Catalog was corrected before any accepted fit/candidate comparison.

Shinka infrastructure: pinned native imports, genuine local Model2Vec embeddings,
OS-isolated subscription adapter, actual one-call gpt-6-astra smoke response,
synthetic prompt assembly and native WebUI HTTP check succeeded. Ultra was
requested/forwarded via disclosed compatibility patches, not independently
echoed by backend. Zero evolutionary mutations; all temporary services stopped.

## 2026-09-20 14:27 UTC — verified source reference, convergence and review corrections

The serial independent source comparison passed all 18 data/effect checks in
35.15 seconds (612,504KB peak). Pinned PRROC numerical, aggregation and complete
synthetic scorer checks passed. Original full-settings equilibrium calls at
rates 1 and 5 each returned 10 endpoints, taking 2.167 and 2.808 seconds. The
checkpointed driver resumed call1 without repeating it, completed call2 and
paused before call3. These are two diagnostic cells, not a reproduced curve.

A serial baseline fit completed attempt1 in664.205 seconds but failed convergence
(maximum absolute t0.2581983941, overall0.5610633217). Attempt2 completed in597.301
seconds and still failed (t0.1021251243, overall0.2974892948). Both native-complete
fits and diagnostics are retained; neither was scored. During independent review
we found that the first forward construction's c(1,1) composition interval was
unsafe: RSiena drops time-zero events. Correcting activeStart alone was also
insufficient: old native network code can permit ties to inactive receivers.
The stronger real-engine diagnostic caught this, rather than dropping offending
endpoints. A correction uses origin-known native structural-zero dyads together
with activity flags. No target outcome determines these constraints.

Stopped the old process group after1344.711 seconds, early in attempt3, preserving
both completed training attempts. Training source, input packet, settings and
seeds did not change. Explicit training-only checkpoint reuse verifies identical
training provenance, copies no predictions/scores, and allows the same third
attempt to resume under the corrected forward cache identity. Original failed
and interrupted logs remain intact. Acceptance thresholds and endpoint budgets
have not been relaxed. No empirical PR-AUC or evolutionary fitness exists yet.

Infrastructure review tightened incomplete-publication recovery, final selection
evidence and commitment checks, serial-lock ordering, interrupted-child cleanup,
and per-invocation resource-log retention. Native invalid-evaluator contract and
SQLite-null handling were exercised without running a scientific candidate.
A separate namespace now blocks mutation-worker access to host loopback/direct
networking, forwarding only allowlisted subscription CONNECT traffic; local
embeddings remain host-managed. This is infrastructure evidence, not evolution.

## 2026-09-20 14:44 UTC — estimation limit reached; original reproduction continues

The third 2006-target training fit completed in618.160 seconds (process wall
622.46 seconds, peak465,572KB). Native completion, phase3 and finite estimates
were insufficient for acceptance: maximum absolute convergence t was
0.09444758531255996, but overall convergence remained0.3237543662931759, exceeding
0.25. All three declared attempts are exhausted. The evaluator CLI was then run
on candidates/initial.py: it verified cached failures, returned correct=false,
combined_score=null and raw_F=null, with actionable feedback. No target prediction
or PR-AUC was scored. Years2007–2009, the structural candidate, native evolution,
conventional comparison, finalist sensitivity and final2010 remain unexecuted.
A future fitting-budget revision must be separately versioned and applied to all
models before comparison; no threshold was relaxed in this run.

Original equilibrium cells3–6 completed at rates10,15,20,25. Coverage is now
six of101settings /60native endpoints, with159countries and originalS10 percell.
Checkpoint resumption was actually observed. The standalone partial PDF/PNG
plots, native coefficients, per-endpoint data and 99%simulation-mean intervals
are archived. The plot was visually inspected and labels its incomplete scope;
no full equilibrium or published figure is claimed.

Restarted one full-settings original Figure5 native call at14:42:38UTC after
fitting and diagnostic jobs stopped. It requests25endpoints (native two-worker
rounding is expected to26 and must be verified on return), retains all159actors,
seed12345 and the original rate200/coupling setting. Its driver pauses after one
completed call; process status/call logs are under results/paper_reproduction/abm-full.
No endpoint batch from this new call has returned at this checkpoint. The earlier
899.03-second interrupted pilot remains recorded separately.

Both original empirical callers are prepared in verified working copies, with
only the supplied directory placeholder changed. Their source-based2010 work
is deferred until the sealed final comparison. They preserve original RNG/call
behavior and are explicitly not partially checkpointable.

The native capability matrix and resolved configuration are updated. Strict
subscription isolation passed14checks; the second administrative Astra route
smoke passed under that exact network boundary. Total administrative model
usage:2calls /28,571reported tokens. Evolutionary mutation, novelty, meta,
prompt-evolution and repair counts are all0. No paid model/embedding fallback
was used. NativeWebUI was checked earlier and is stopped because no campaign
has begun. The requested Ultra setting was forwarded; achieved effort is not
echoed by the backend.

## 2026-09-20 16:38 UTC — result publication and scientific README

The user requested publication of all results to the existing GitHub repository
and an arXiv-style README. Inspected the actual remote: it is private, has no
commits, and the authenticated user has administrative access. Existing private
visibility is preserved. No new estimation or model calls were made for this
publication task.

The previously running full-settings Figure 5 call completed at 14:53:09 UTC:
626.613 seconds in the native call, 630.541 seconds process wall time, 436,048KB
parent peak RSS, 26 returned endpoints for requested n3=25/two workers. The
159-country sample, both rates200 and gamma=-0.05 were retained. Mean spending
was1.0234639574262216, density0.49686453185378432 and clustering
0.49651822742620988. Driver exit75 preserves its completed-call checkpoint.
Together with six equilibrium cells, there are86 endpoints across7 original
settings. Figures5–7 coverage is1/564 and equilibrium coverage6/101. Host process
inspection at publication found no running R, evaluator or campaign jobs.

Summarized completed native endpoints, refreshed reproduction/evolution
manifests, and generated the baseline convergence figure from saved diagnostics.
All three failed baseline fits remain available; no predictive score or
improvement is claimed. Independent scientific review checked the README's
counts, coefficients, convergence values, split definitions and fitness formula.
It found nonportable incidental cache-key inputs; the runbook and deviation log
now explain that relocation or environment verification may cause recomputation.

The redesigned README presents an abstract, model, exact equations, temporal
protocol, two evidence figures, results, coverage, limitations, native capability
status, reproducibility and references. GitHub's Markdown API rendered its
mathematics successfully. A dedicated agent-browser session visually checked the
rendered markup with GitHub-like preview styles at desktop and390px widths:
both figures loaded,12 math expressions typeset, and no mobile body overflow.
This was a local preview, not a claim of custom CSS support on GitHub. The
verification browser was closed afterward.

The refreshed publication inventory contains259 artifacts /39,518,882bytes,
including the canonical CC0 archive, all fit/checkpoint RDS files, native output
logs, endpoint data, failed/interrupted-run evidence and checksums. Every
scientific artifact is below50MiB; none requires Git LFS. Generated source logs
were copied out of ignored working directories with file-level provenance.
Installed dependencies, redundant source/data working copies, credentials and
private sessions remain excluded. Pattern scans reported no credential matches.
Commands used include python3 scripts/publication_inventory.py, GitHub Markdown
rendering, staged-diff review, and the authorized initial commit/push workflow.

## 2026-09-20 — prespecified bounded scientific continuation (before execution)

Policy v2 retains the original attempts1–3 (nsub3/n3=1000; seeds12345–12347),
then allows exactly one prevAns continuation from attempt3 with nsub5/n3=3000,
seed12348. Stop on first acceptable fit; all specifications/targets receive this
same schedule. Main Model3 uses nsub5/n3=3000 in original
scripts/00.estimateSAOMsMain. More stochastic-approximation effort and phase3
simulations address the saved joint convergence obstacle (overall0.3237543663),
while all acceptance criteria remain unchanged: individual |t|<0.1, overall<0.25,
and existing native/identification requirements. Forecasts remain1000 endpoints.
The saved three2006 fits are transferred unchanged into the versioned scientific
run; no completed fitting is repeated. If the additional2006 continuation fails,
this session stops empirical search. No tests/audits/readiness work is run.

## 2026-09-20 18:06 UTC — accepted 2006 fit and actual forecast

The sole added continuation passed: max|t|0.058829200542192574, overall
0.1481894637949584, all native validity criteria satisfied. Runtime4162.92s;
13,767 native iterations (10,767 estimation +3,000 phase3). Objective estimates
changed little from attempt3 (largest change0.06265 prior standard errors).
The fit/forecast process took4209s wall, peak551,236KB RSS. Saved under
results/cache/8129f423ce5a8a407d8e5fe630fb02d145e209f6500ae34e57af32b4e4f2d829.

The unconditional origin-only forecast returned exactly1000 endpoints in33.292s,
seed2006001, before target scoring. On12,720 eligible unordered dyads (458ties),
PRROC PR-AUC=.8853079445873959, ROC-AUC=.9764983806968522,
Brier=.005488310220125786. Persistence PR-AUC=.8638806700371717 and
Brier=.005424528301886792: ranking improves but Brier is slightly worse.
Formation PR=.015180235117037194; dissolution ROC=.5194788441692466.
Spending RMSE=.3712393627751295 ordinal categories. This is an accepted baseline
forecast, not evolutionary improvement. 2010 remains reserved.

Started the original-specification evaluate.py invocation in
results/evolution_forecast/initial-v2. It reuses completed2006 predictions and
fits2007–2009 serially under the same declared policy. Four-year fitness remains
unavailable until all four years succeed. No new audit/test/model-route calls.

## 2026-09-20 20:25–21:05 UTC — second baseline and revised scientific scope

The 2007 reference completed four attempts (1174.327,1119.742,1033.407,
4884.053 seconds). Attempt4 passed max|t|=.04937219026260515 and overall
convergence=.14525483825642632; all original acceptance requirements remain.
Fit/forecast walltime was2:17:47, peak744640KB RSS. Exactly1000 endpoints
(seed2007001;44.986 seconds) gave PR-AUC=.9416616420083401,
Brier=.004086563128930818 and spending RMSE=.36381803035381066 ordinal
categories. Persistence PR=.9108377571720565 and Brier=.0037735849056603774:
better ranking is accompanied by worse probability MSE. Formation PR=.0385171845
and dissolution PR=.0226242552 remain separate diagnostics. The 2008 fit began
20:25UTC in the same original evaluator; no duplicate numerical controller ran.

User steering replaces the small specification-selection pilot with a continuing
multiobjective-v1 scientific campaign. Withdrawn: four proposals, twelve
generations as a research limit, fifteen subsets, three structural coefficients,
blanket parameter/product bans and a manually successful changed-model gate.
The fixed objectives are four-year means of PR improvement, Brier improvement
and ordinal-spending RMSE improvement. Stable scalar credit is
2+(J1+J2+J3/10)/3; strict Pareto retention/sampling is a project integration,
not an upstream configuration feature. Model3 controls, spending structure,
joint coefficient estimation, country sample and native update process remain.
Models3/4 full-period reproduction stays separate; new2010-related results
cannot enter development before finalist selection is frozen.

The latest requested execution window began around20:44UTC. Its checkpoint is
23:15UTC (01:15Berlin), not a campaign generation limit. New native work has a
cooperative deadline before each fit, continuation and forecast; admitted native
operations save to completion. The older running evaluator was launched without
that hook and its files/settings are preserved until its completed checkpoint.

Separate unused schema-v2/R/evaluator modules and Pareto selection hooks were
implemented while that calculation continued. The native compatibility patch
was applied to the pinned Shinka working source without running the engine or
rebuilding its environment. It adds pending-candidate/adaptation resumption and
deadline admission; installed RSiena and its C++ kernel are unchanged. Activation
of multiobjective evaluation waits for publication of the existing evaluator
checkpoint. No tests, audit/readiness campaigns, administrative model calls or
browser checks were performed.

Calculated descriptive ten-bin reliability from the existing committed2006/2007
predictions only (results/evolution_forecast/baseline-calibration-2006-2007.json).
The 2007 reference predicts875.948 triangles versus751 observed (native95%
simulation envelope800–958);2006's727 triangles lie within700–812.025.
This motivates investigating closure saturation across development years; it
does not establish a successful alternative, causal efficiency or security.

### 2026-09-20 21:25 UTC — third reference forecast completed

- 2008 accepted at attempt 3: max|t|=0.09340243217279035, overall=0.2308423651716375, elapsed=1166.037 s. Attempts 1/2 failed overall convergence (0.4018111172554628/0.3212258013711868); total fitting time 3559.530 s. No threshold or policy change.
- Exactly 1000 endpoints: PRROC integral=0.9145603775754418; Brier=0.004505291666666667; ordinal-spending RMSE=0.43959861050299553 (146 countries). Common tie mask: 12720 unordered pairs, 508 positive ties; 160 origin-inactive pairs excluded. Formation PR=0.022770206408522696, dissolution PR=0.030813282345479427. Persistence PR=0.9008736722460643, Brier=0.00440251572327044. Forecast elapsed35.717s; scoring9.211s.
- The existing unchanged evaluator automatically began 2009 at21:25:33UTC. No new numerical controller or candidate was launched. The checkpoint remains23:15UTC; 2006/2007 were carried into this execution window, and 2008 is newly completed within it.
- Scientific reporting now separates reconstruction from empirical reproduction, the authors' Model4 efficiency comparison from the Model3 forecasting extension, and overall agreement prediction from formation. New multiobjective feedback associates estimates/SEs with their actual native effect identity; legacy `initialValue` exports are not misreported as fitted estimates. No tests, validation campaigns, administrative model calls or final-year access were performed.

### 2026-09-20T21:58:06.622249+00:00 — continuing admission authorized; numerical checkpoint publication

- The user superseded the former2–3h stopping instruction. Roughly2–3h remains a reporting/publication interval, not a scientific admission limit. The new launcher now removes stale inherited session deadlines by default; native unlimited generation mode no longer requires a walltime window. Optional explicitly requested future windows and all numerical timeouts remain. No active evaluator file or setting was changed.
- 2009 attempt1 completed in1314.003s and failed max|t|=0.11228053001026655, overall=0.3509443797466443. This diagnoses nonconvergence, not a software defect. The existing native continuation is active under unchanged v2 policy. If that policy is exhausted, inspect saved training-only numerical diagnostics before declaring a specific remedy.
- Publishing completed2006–2008 fits/forecasts and the saved2009 attempt1, while labeling2009 ongoing. 2008 fit-and-forecast walltime1:00:07, peakRSS690224KiB. Cumulative accepted reference forecasts3; changed-model evaluations0; native proposals/role calls0. New scientific grammar/evaluator/Pareto code is implemented but unexecuted. No positive evolutionary finding or complete four-year objective vector is claimed.

### 2026-09-20T23:09:09.042850+00:00 — focused 2009 estimation diagnosis, before fourth-attempt outcome

- The running fourth continuation is unchanged. The same scheduled nsub=5/n3=3000 continuation passed for2006 (4162.920s =69m22.920s; max|t|0.058829200542192574, overall0.1481894637949584) and2007 (4884.053s =81m24.053s; max|t|0.04937219026260515, overall0.14525483825642632). Those are observed precedents, not a guarantee of2009 acceptance.
- In RSiena1.3.10, nsub controls phase2 stochastic-approximation subphases: increasing it changes optimization effort and the gain schedule. n3 controls phase3 simulations used to assess convergence and estimate derivative/covariance quantities. More phase3 simulations improve Monte Carlo precision of those diagnostics; they do not by themselves optimize a fixed coefficient vector. Our declared fourth stage changes both, so any success cannot be attributed to one component alone. Forecast endpoints remain1000, independent of n3.
- Saved2009 attempts1–3 have overall ratios0.3509443797466443,0.31907345900001255,0.26134400479859027; max individual ratios0.11228053001026655,0.09662731744696514,0.07587932310910743. Native status/termination and finite covariance checks pass; overall convergence still fails. These are58 jointly estimated parameters (36 rates,11 network-objective terms,11 spending-objective terms).
- Named coefficient movement is small relative to marginal estimation SEs: largest1→2 change0.135451SE (network rate period8), largest2→3 change0.088352SE (spending rate period14); medians0.032283/0.017969SE. Across attempts1→3, maximum displacement0.134436SE (NATO network control). Network density moves−5.521950→−5.537370→−5.537396, triads0.154312→0.157753→0.158397, total degree0.057115→0.057006→0.057236. There are31 sign reversals across58 updates, but none has both displacements above0.1SE; this gives no evidence of large coefficient oscillation. These are descriptive changes between dependent continuations, not independent-fit significance tests.
- Full named coefficient/SE/convergence comparisons and immutable input snapshot are saved in results/evolution_forecast/diagnosis-2009/. Matrix and simulated-statistic diagnosis is underway using saved fits only. No further fitting remedy is chosen or launched before the fourth result.

### 2026-09-20T23:15:12.396421+00:00 — saved-statistic and derivative diagnosis

- Installed native phase3 code defines overall convergence as sqrt(mᵀV⁻¹m), where m is the mean simulated-statistic deviation and V the covariance of individual phase3 deviations; individual ratios divide by simulation SD, not the SE of the mean. This is the maximum ratio over linear combinations. The saved sf/msf reproduce reported ratios; this is diagnosis of existing estimation output, not a new validation gate.
- Attempt3 largest individual ratio is network rate period17 (0.0758793); the largest objective-statistic ratio is0.0481008. No single covariance eigendirection explains the failure: the largest accounts for15.95% of the squared ratio and mixes spending rates15/8/16 with network rates17/13/8/6. Another9.70% direction contrasts alter capabilities(+0.641), trade(−0.577), density(−0.308) and distance(−0.308), with smaller additional loadings. Signs of eigenvectors are arbitrary; complete named combinations are archived.
- Attempt3 raw covariance condition48,442,564 and derivative condition7,323,179 largely reflect unlike units. Statistic-standardized correlation condition126.786 (minimum eigenvalue0.0428147), statistic-SD/unit-column-scaled derivative condition99.992, and statistic-SD/parameter-SE-scaled derivative condition57.855 are the interpretable comparisons. The matrices are numerically full rank. The weakest scaled derivative direction is chiefly spending degree(+0.804) versus dense triads(−0.567); density versus degree activity is another weaker direction. These correlated directions warrant caution but are not evidence of nonidentification. No native divergence, automatic parameter fixing, negative derivative diagonals or covariance warning is present.
- Saved phase3 lag1 correlations have median0.001708 and maximum absolute0.061694. Under an exact-root independent-simulation approximation, sqrt(58/1000)=0.240832 is the Monte Carlo scale of the overall ratio. Dependence-sensitive estimates using saved rows at lags10/20/50 give0.239258/0.236663/0.233161. Their squared scales0.05436–0.05724 are substantial relative to observed0.06830, but cannot be interpreted as an identified noise fraction or formal acceptance test. At n3=3000 the simple exact-root scale is0.139044; no new threshold is introduced.
- The two phase3 halves give standardized derivative estimates differing13.58% (each~6.8% from full); phase1 versus phase3 differs9.42% with parameter-SE scaling. Derivative information has Monte Carlo uncertainty, but the saved evidence does not diagnose a gross derivative failure. Combined with small shrinking coefficient displacements, the evidence favors a stable near-solution with appreciable diagnostic noise over large update oscillation or a rank defect. Residual moment mismatch cannot be ruled out from these saved simulations. Fourth-attempt results will determine whether any additional remedy is needed.
- Analysis used only saved1990–2008 fits: final lightweight R analysis2.54s, peakRSS253668KiB. No fitting, simulation, target outcomes or active-file changes. Scripts, named moment/derivative directions, dependence summaries, source provenance and full numerical outputs are preserved under results/evolution_forecast/diagnosis-2009/.

### 2026-09-21T00:10:02.232667+00:00 — actual fourth-attempt interruption: host OOM, not a convergence outcome

- The original evaluator ended with exit137/signal9. Kernel evidence identifies a GLOBAL out-of-memory kill of R PID945909 at2026-09-20T23:07:33Z. Managed RAM3836020KiB, swap1048576KiB with zero free; killed fit anonRSS686036KiB, measured stage peak717432KiB. The diagnostic reader PID1014750 was concurrently present at17446pages (~68.15MiB). MainThread invoked the failed allocator; concurrent inspection added pressure, but no unique causal allocation is inferred. All further R work will be serial.
- No fit-attempt-4.rds or accepted2009 fit was saved. Attempts1–3 and all prior forecasts remain intact. Later status statements inferred activity from an unchanged saved checkpoint; that inference was stale. The authoritative kernel termination time and invalid evaluator result correct the record. The wrapper recorded5940.343 elapsed seconds while GNU time reports1:42:00; both raw timing records are retained rather than silently reconciled.
- Archived the interrupted fit4 native text and process record, retained unique resource/stdout/stderr/event logs, and copied the invalid initial-v2 metrics/correct/error files under OOM-specific names before any recovery. This is not exhaustion of four completed statistical attempts. The appropriate recovery is the same scheduled fourth attempt, from saved3 with seed12348/nsub5/n3=3000, after memory is available. No new convergence threshold, extra seed or fifth fitting policy has been selected.
- Current memory consumers outside this project include another project’s embedding and WebUI services. They were not terminated without authorization. Asked the user to free memory or explicitly authorize stopping those services. Installed R4.2.1 help(Memory) documents R_GC_MEM_GROW=0 as less-aggressive heap growth, a possible execution-only memory measure; it does not alter coefficients, simulation settings or seeds. No recovery fit has yet started.
- With the old evaluator terminated, connected root evaluate.py --protocol multiobjective-v1 to the fixed helper and native launcher. This is a CLI connection, not an executed objective vector. There remain zero native proposals and zero changed-specification evaluations.

### 2026-09-21T00:12:41.834135+00:00 — bounded recovery of the interrupted fourth attempt

- GitHub publication succeeded at148cf96. All diagnostic R readers have exited. Host MemAvailable856724KiB at00:11:46UTC versus prior main-stage peak717432KiB; swap remains nearly exhausted. The first diagnostic reader’s exactPID/start/end were not independently preserved; its chronology is consistent with the concurrent small R process in the OOM log, so attribution is qualified.
- Recover exactly attempt4 from saved3 with unchanged seed12348/nsub5/n3=3000. The only execution adjustment is R_GC_MEM_GROW=0, documented by installed R4.2.1 help(Memory) as least aggressive heap growth (potentially more garbage-collection time). It changes no scientific setting, coefficient specification, random schedule or1000-endpoint budget. R work is strictly serial and no native evolution services are started during recovery.
- One recovery of the interrupted operation is authorized by the ongoing task; this is not a fifth statistical retry. If host OOM recurs, preserve the failure and wait for additional available memory rather than indefinite relaunch. Other projects’ processes are untouched; the optional request to free memory remains pending.

### 2026-09-21T00:17:47Z — live recovery status, observed directly

Host ps identifies R PID1010372, start00:12:53UTC, running state R, elapsed4:54, CPU5:05 (~103%), RSS438188KiB (~428MiB). Only one R process exists. Native report confirms fourth-attempt initialization with58 parameters/statistics; silent mode does not publish iteration counters, so no specific live subphase is inferred. The recovery and scientific settings remain unchanged in response to the latest steering.

### 2026-09-21T02:01:29.172419+00:00 — fourth 2009 recovery accepted; complete reference comparison

- The single unchanged recovery completed. Attempt4 nsub5/n3=3000/seed12348: max|t|0.047248223874978804, overall0.1610484454862545, native finite/identification criteria passed. Elapsed6319.522s; no fifth attempt, seed change, threshold relaxation or additional diagnostic R reader. Conservative heap growth and serial execution avoided a second OOM in this operation. They do not guarantee enough memory for every future candidate.
- Exactly1000 endpoints, seed2009001, forecast38.998s: 2009 PR-AUC0.9493615190143408, ROC0.9924785848596699, Brier0.0033978513364779873, spending RMSE0.39304969100948167 (151 ordinal observations). The same12720 undirected pairs were eligible;160 origin-inactive pairs excluded. Prediction commit preceded scoring.
- Persistence PR0.9284607164520554/Brier0.0032232704402515725. Formation PR0.01399445866412289 (26 new ties); dissolution PR0.04734086685636852 (15 dissolutions). Overall tie prediction must not be mistaken for demonstrated new-partnership prediction. Expected ties538.647 versus519 observed, below the simulation envelope523–554; expected triangles890.221 versus841, within829–964.025.
- All four reference years are complete:15 completed fits,4 accepted,11 nonconverged;4000 endpoint networks. Completed fitting time totals28537.680s (7.93h), excluding the interrupted operation. The current process GNU walltime1:46:17/peak599456KiB and native fit6319.522s differ from the wrapper elapsed6122.839s; raw records are retained. No causal runtime comparison is made between GC settings.
- Legacy PR-only evaluator returned correct=true, raw F=0 exactly and historical combined_score=1. This cache-identical reference comparison does not add an independent source-parity result. Native multiobjective seed evaluation will reuse these forecasts for vector(0,0,0), auxiliary2; no refit is needed. No 2010 data were scored.
- Proceed directly to the authorized native multiobjective campaign after this publication checkpoint. Changed-model completed evaluations0, native proposals0, evolutionary-role calls0 at this checkpoint. The reference beats persistence in PR-AUC and loses on Brier in every year; no evolutionary improvement is yet established.
