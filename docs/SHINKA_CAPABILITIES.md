# Shinka capability matrix

Recorded 2026-09-20. Infrastructure is installed and checked; **no native
evolutionary campaign or mutation call has run**. Two public-arithmetic subscription
route checks ran, including one through the final network namespace. A configuration is not execution
evidence. See [contract and commands](SHINKA_CONTRACT.md) and
`shinka/provenance.json` for exact source and artifact pins.

| Capability | Configured | Observed in execution | Status / evidence or limitation |
|---|---|---|---|
| Pinned native runner | Yes | Import and dataclass resolution | Shinka 0.0.7, commit 9912af1; `.venv-shinka`, `runs/evolution_native/resolved_config.json` |
| Evaluator files and CLI | Yes | **Yes**, native scheduler invoked actual evaluator with rejected candidate | Null score and actionable invalidity were loaded; no candidate execution, R, or model call; scientific campaign still gated |
| Population/archive | Yes | No population created | Two islands, archive 12; deferred until scientific readiness |
| Weighted parent sampling | Yes | Source inspected | MAD-scaled sigmoid; actual draws deferred |
| Executable archive/top-k inspirations | Yes | Synthetic native prompt check only | One each; real descendant evidence absent |
| Diff/full/crossover mutation | Yes | No | Probabilities 0.5/0.3/0.2; actual operator counts must be reported |
| Nonzero migration | Yes | No | Two islands; every 3 generations, rate 0.25; no migration claimed |
| Local embedding backend | Yes | **Yes** | Native EmbeddingClient received 256-dimensional genuine pretrained vectors over loopback |
| Native novelty adjudication | Yes | No | Subscription route configured; LLM adjudication calls deferred, threshold 0.98 |
| Mathematical specification novelty | Yes in trusted evaluator | Initial/candidate canonicalization separate | Native code novelty does not guarantee mathematical novelty |
| Model-selection bandit | UCB selected | No | Only one explicitly selected model; multi-model comparison deferred. No claim of a meaningful one-arm bandit experiment |
| `use_text_feedback=True` | Yes | Synthetic native prompt check only | Fine precision feedback preserved; real descendant prompt absent |
| Meta-recommendations | Every 3 generations | No | Native path configured; no meta call claimed |
| Prompt co-evolution | Every 3 generations | No | Archive 6, top-k 2; no evolved prompt claimed |
| SQLite lineage/resumption | Native | Invalid fixture ingested; no campaign lineage | Native DB preserved null score and excluded invalid fixture from archive/best. Campaign resumption still unobserved |
| Native WebUI | Launcher-managed | Own loopback port returned HTTP 200 | Browser visual check aborted to release memory; no campaign evidence; temporary server stopped |
| Subscription authentication | Yes | **Yes** | `codex login status` reports ChatGPT inside isolated namespace |
| Astra Ultra mutation route | Yes with disclosed patch | Two public-arithmetic subscription route checks | Final check ran through isolated egress; returned model gpt-6-astra; ultra requested/forwarded, achieved effort not echoed. Not evolution |
| Requested coding-session model | Astra Ultra requested | Not independently verified | Do not infer active effort from local defaults or mutation config |
| Candidate filesystem isolation | Yes | **Yes** | Bubblewrap hides protected research checkout and prior Codex sessions; real login/access self-check passed |
| Candidate network isolation | Yes | **Yes**, socket tests and actual subscription smoke | Separate network namespace; host loopback/direct networking denied; only exact subscription-host CONNECT through a mounted Unix socket. Implementation hashes bound in `shinka/security_review.json` |
| Restricted candidate execution | Trusted AST interface | Owned by evaluator | Literal specification only; no import/exec of candidate source |
| Mutation/novelty/meta/prompt/repair accounting | Native metadata + complete adapter logs | Zero such calls; two route smoke calls | `runs/shinka_adapter_logs/calls.jsonl` includes admin checks; distinguish checks from model calls |
| Paid API/embedding fallback | Forbidden | Zero | Launcher rejects paid routes and removes API keys; local embeddings only |
| Measured finite campaign | Gate implemented | Not yet | Provisional 12-generation config cannot launch before measured baseline/candidate cost |
| Explicit per-evaluation timeout | Readiness-derived | Harmless native runtime-method check | Overrides cached-seed EWMA; current scientific upper cap 96h20m plus declared margin, not an expected runtime |
| Detached evaluator-child cleanup | Versioned native patch | **Yes**, harmless separate-session child | Stops owned descendants even across sessions; no scientific run was interrupted by this test |
| Cumulative campaign walltime | Thin lifecycle supervisor | **Yes**, harmless subprocess tests | Accumulates clean resumptions; deadline stops descendants; exhausted budget launches nothing; native evolution logic unchanged |
| Actual descendant prompt audit | Required | No | Synthetic prompt exercise is explicitly not a real descendant |

At this review, `runs/evolution_forecast/readiness.json` reports source-reference,
independent bridge parity, exact PRROC, leakage, frozen catalog/convergence, and
final-year reservation gates passed. Remaining scientific gates are seed-zero
evidence, all four accepted temporal baselines, a valid structural candidate, and
a measured finite campaign budget. The native configuration enables the available
requested machinery, but real migration, meta/prompt evolution, lineage
resumption, descendant prompts, and multi-model bandit execution remain unobserved.
The matrix must be updated from native database/log evidence after execution.
