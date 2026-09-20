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
