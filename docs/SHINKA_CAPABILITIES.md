# Shinka capability matrix

Updated 2026-09-20 for **multiobjective-v1**. The expanded scientific integration is implemented. The PR-only evaluator ended with invalid fitness after the kernel killed the fourth 2009 continuation during global host memory exhaustion; no fourth fit was saved. **No native evolutionary proposal or evolutionary-role model call has occurred in this window.** Historical setup checks in commit `13021e2` are not evidence that the revised campaign ran. They were not repeated.

| Capability | Configured / implemented | Observed in this scientific campaign | Limitation or evidence |
|---|---|---|---|
| Pinned native runner | Shinka 0.0.7, commit `9912af1` | Not yet launched | Native proposal generation, SQLite and persistence retained; project patches versioned |
| Fixed three-objective evaluator | `evaluate.py --protocol multiobjective-v1`, trusted helper, versioned protocol | Three original reference forecasts saved; no full objective vector yet | Same forecasts supply all objectives; all four years required |
| Pareto population/archive | Project database hooks; preserve all canonical nondominated alternatives | No population yet | Rank and objective-space diversity; archive quota is soft for nondominated models; not an upstream-native feature |
| Parent selection | Project rank/crowding tournaments within native sampler | No draws | Scalar compatibility score does not replace Pareto selection |
| Executable inspirations | Diverse Pareto archive alternatives; native executable prompt inclusion | No real descendant prompt | One archive and one top inspiration configured; no synthetic demonstration claimed |
| Diff/full/crossover | Native probabilities 0.5/0.3/0.2 | None | Actual operator counts will be reported from lineage |
| Islands/migration | Two islands; every three generations, rate 0.25 | None | Same objective definitions; project migration retains scientific trade-offs |
| Local embeddings | Existing Model2Vec potion-base-8M, 256 dimensions | No new campaign embedding | Earlier native embedding execution remains historical evidence; no paid embedding fallback |
| Novelty adjudication | Native threshold 0.98; Luna low | No calls | Code novelty and canonical mathematical identity are separate |
| Mathematical identity | Parameter/operand grammar and confirmed native aliases | Reference identity preserved in implementation | Proportional symmetric moments excluded from joint estimation; not a claim of exhaustive equivalence detection |
| Adaptive mutation-model choice | Native UCB; Luna/Sol/Terra low as distinct arms | No arm draw or credit update | Identifiers come from local Codex installation metadata; actual routed model/effort must be reported after calls |
| Scientific text feedback | Annual objective deltas at 12 decimals, diagnostics, fitted native coefficients/SEs | Saved reference scores; no descendant receiving feedback | Failed fits have invalid fitness; no partial-year average |
| Meta-recommendations | Native, every three generations; Luna low | None | No extra calls to demonstrate capability |
| Prompt co-evolution | Native, every three generations; archive six; Luna low | None | No evolved prompt claimed |
| SQLite lineage/resumption | Native storage plus project pending-evaluation records | No campaign lineage yet | Pending numerical work retains its candidate and generation; paused work receives no bandit credit |
| Native WebUI | Existing launcher-managed service for actual evolution | Not started this window | No browser checks or redesign |
| Subscription routing | Exact headless Codex route; local identifiers recorded | Zero scientific calls | Prior two administrative checks used Astra; they do not verify new arms in execution |
| Requested builder | Astra Ultra | Requested session role | Do not infer actual mutation effort from builder identity |
| Role accounting | Existing adapter/native call logs | Zero mutation/novelty/meta/prompt/repair calls this window | API-dollar zero does not mean zero subscription consumption; historical account quota is not campaign usage |
| Paid fallback | Forbidden | None | Paid API keys removed by existing launcher; local embeddings retained |
| Restricted candidate interface | Literal AST data; existing isolated subscription route | New decoder implemented | No arbitrary candidate execution or access to reserved outcomes |
| Publication and numerical checkpoints | Continuing admission, no default session deadline or overall generation cap | Current legacy evaluation preserved unchanged | Former stopping instruction superseded; optional future explicit windows retain resumable native/R hooks. Actual scientific timeouts remain |
| Same-space conventional search | Existing search adapted to native grammar and three objectives | No conventional candidate evaluated | Match distinct evaluation attempts and report cache reuse/failures/runtime; no Shinka superiority claim |
| Finalist reporting | Development Pareto J1/J2/J3/aux champions, exact tie rule, dedup + reference | No finalists selected; 2010 unopened | Fresh development repetition then frozen set; legacy final-test execution still needs multiobjective-set adaptation |

Current configuration: [`native_multiobjective_config.json`](../shinka/native_multiobjective_config.json). Scientific operators and interpretation: [`task_prompt_multiobjective.md`](../shinka/task_prompt_multiobjective.md), [`effect-catalog-v2.json`](../configs/effect-catalog-v2.json). Project extensions: [`pareto_selection.py`](../shinka/pareto_selection.py), [`multiobjective_native.patch`](../shinka/multiobjective_native.patch).

The four-proposal pilot, fifteen-specification catalog, three-effect cap and twelve-generation overall limit are withdrawn. A manual successful modified model is not a precondition for native proposals. The unresolved dependency is recovery of the same interrupted fourth reference attempt under adequate memory, followed by the complete reference comparison. This campaign remains recoverable across execution windows; setup completion alone is not a substantive evolutionary result.
