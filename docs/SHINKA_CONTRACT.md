# Native evaluator and launch contract

Inspected native source: ShinkaEvolve 0.0.7, commit
`9912af12d423504b8d580f4179fd15f5f88b8c50`. The distribution is `shinka-evolve`,
the Python import is `shinka`, and the runner is `ShinkaEvolveRunner`.

## Explicit protocol routing

The scheduler must pass `--protocol` through `LocalJobConfig.extra_cmd_args`.
The current launcher passes `multiobjective-v1`; the explicitly selected legacy
profile and legacy invalid-evaluator fixture pass `pr-only-v2`. An omitted
protocol is a command-line error, not a failed scientific evaluation, and creates
no metrics or results directory. General launchers also require their selector:
`run_shinka.py --config ...` and `conventional_search.py --protocol ...`.

The current scheduler invocation is:

```bash
python evaluate.py --protocol multiobjective-v1 --program_path /absolute/candidate.py --results_dir /absolute/evaluation-directory
```

Current vector/score semantics are in the README and `configs/multiobjective-v1.json`.

## Historical PR-only contract

The remainder records the legacy integration, including its `1 + F` scalar and
historical readiness gates; it does not redefine the current Pareto campaign.
The legacy local scheduler explicitly invokes:

```bash
python evaluate.py --protocol pr-only-v2 --program_path /absolute/candidate.py --results_dir /absolute/evaluation-directory
```

The evaluator writes `metrics.json` with numeric `combined_score`, `public` and
`private` objects, and a **string** `text_feedback`; and `correct.json` with
`{"correct": true, "error": ""}` or an actionable error and `correct: false`.
These files are loaded by `shinka.utils.load_results`; native
`shinka/core/async_runner.py` transfers the fields into the SQLite program record.
Execution failures are `correct: false` with `combined_score: null`; they are not
scientific losses or valid F. The initial native seed is gated until all baseline
years are accepted, preventing an invalid seed from starting an empty campaign.

`combined_score = 1 + F` is a declared compatibility offset. The weighted parent
sampler itself supports signed scores, but `shinka/database/dbase.py:1615` sorts
with `combined_score or -inf`, demoting the exact-zero original baseline below
negative improvements. The offset preserves the ordering and magnitude of every
improvement, while raw F remains in public metrics and precise feedback. No
complexity, runtime, spending or subjective criterion enters the score.

`use_text_feedback=True` is mandatory. Native `PromptSampler.sample` includes the
parent source, scores, text feedback, executable archive and top-k inspirations,
and meta-recommendations. A synthetic contract check exercised this source path
and is saved under `runs/shinka_infrastructure`; it is explicitly **not** an
observed evolutionary descendant. After evolution starts, inspect the actual
`runs/public_mutation/<campaign>/headless_prompts/` files and match them to native
lineage and evaluator artifacts. Only then record descendant-prompt verification.

The engine is native; `scripts/run_shinka.py` only builds its dataclasses, checks
scientific readiness, supervises its process lifetime, starts its own WebUI and
calls `runner.run()`. Resumption uses the same result directory and native SQLite
state. No custom evolutionary controller or LLM fitness judge is supplied.

## Runtime limits and cleanup

The pinned native `LocalJobConfig.time` default is **None**, not a fixed 600-second
limit. However, the async runner then derives an evaluation limit from
`max(60, 5 * evaluation_EWMA + 60)`. A cached seed could consequently impose a
very short limit on the first uncached structural candidate. Launch now requires
an explicit `native_evaluation_timeout_seconds` from the evidence-based readiness
manifest, overriding that heuristic.

For the current frozen protocol, the four-year candidate upper allowance is
`4 * (3 * 21600 + 21600 + 300) = 346800` seconds (96 hours 20 minutes), plus an
explicit positive `native_evaluation_timeout_margin_seconds`. This is a worst-case
execution allowance, **not a measured expected runtime**. All four baseline caches
must already be valid. The readiness builder currently declares a 600-second
operational margin, yielding `96:30:00`. `evaluator_settings_sha256` must match the
current frozen evaluator settings; neither null, nonfinite, nor shorter limits
are launchable. Measured candidate cost and the finite campaign budget are
separate readiness fields.

`shinka/patches/local-evaluation-process-tree.patch` fixes native local job cleanup:
the original `Popen.kill()` killed only the Python evaluator, leaving an R child
started in a separate session alive. The patch snapshots and terminates all
owned descendants, escalates remaining children after ten seconds, and lets the
trusted evaluator write invalidity diagnostics before stopping its parent.
A harmless test executed that native method against a separate-session child and
verified that the child was gone; no R or model call was involved.

The launcher uses a lightweight subprocess supervisor around the unchanged native
runner. It re-executes after configuration checks to avoid retaining a duplicate
180MB native import alongside the worker. `campaign_process.json` records the
worker PID, elapsed time, exit status and cumulative walltime across clean
resumptions; complete output is appended to `campaign.stdout.log` and
`campaign.stderr.log`. On walltime exhaustion, owned descendants are terminated,
SQLite/log/cache artifacts remain, and the command returns 75. An interrupted
evaluation has no valid scientific fitness. Cleanup may use the separately
declared 20-second grace period after the deadline. An exhausted campaign cannot
silently reset its budget on resume; changing its budget requires a newly
versioned campaign directory. A hard-killed supervisor without a clean final
state requires process/log inspection before resumption.

Native local submission inherits its parent cwd; it does not itself change into
the generation directory. The launcher fixes its worker cwd to the project root
and supplies absolute evaluator/program/result paths. Independently,
`evaluate.py` derives ROOT from its own file and starts R with `cwd=ROOT`.
An actual native scheduler check invoked a rejected candidate from a generation
directory without running its Python, R, or any model.

## Access boundary

The candidate evaluator AST-interprets a literal specification and never imports
or executes candidate Python. Mutation calls additionally run through
`shinka/headless_isolated.py` in a bubblewrap user/mount/PID/network namespace. Only the
public mutation directory, runtime binaries/libraries, minimal DNS/certificate
files, and subscription authentication/model metadata are mounted. The research
checkout, evaluator, data, evaluation results, and original Codex conversation
history are absent. A real self-check verifies absence of protected paths and
the subscription login. A plain read-only sandbox or a different cwd would not
have been sufficient.

The pinned Headless launcher originally enabled web search even for read-only
calls; the explicit patch disables web search and the shell tool. No API-key
environment variables enter mutation subprocesses; cached authentication must
declare ChatGPT with subscription tokens and no API key. The trusted runner
disables dotenv loading and accepts only `headless/codex@...` model routes and
loopback embedding routes.

The mutation namespace has no host network or host-loopback access. Its temporary
TCP-to-Unix bridge connects to one explicitly mounted socket. The invocation-local
host proxy permits only `CONNECT chatgpt.com:443` or `CONNECT auth.openai.com:443`;
it rejects URLs, other ports/hosts, IP literals, private DNS resolutions and
non-CONNECT requests. Validated public DNS addresses are used directly, avoiding
a second resolution. It logs connection metadata, never TLS plaintext or tokens.
No research filesystem or service socket is exposed. Host-side native WebUI and
embedding services remain available to the trusted runner and local user.

Socket tests actually verified a separate namespace, an unreachable live host
loopback listener, blocked direct networking, denied proxy destinations, protected
paths absent, and working public HTTPS to both allowed hosts. Public HEAD requests
returned HTTP 403, which proves TLS reachability but is not an authenticated model
test. A separate authorized Astra subscription arithmetic call then succeeded
through this exact boundary. `shinka/security_review.json` binds the checks to
implementation hashes; the launcher fails closed if the evidence is missing or
stale. TLS application paths/content are not inspected. No model-internal
guarantee against historically known facts is claimed.

## Versioned compatibility patch

`shinka/patches/astra-ultra-and-no-web.patch` modifies both native Shinka's effort
whitelist and local Headless 0.6.1's CLI/config parsers to accept `max` and `ultra`.
Headless already passes the chosen value verbatim through
`codex ... -c model_reasoning_effort="..."`; it does not translate Ultra to xhigh.
Upstream unmodified archives and artifact hashes are preserved in
`shinka/provenance.json`. This is a disclosed adapter compatibility change, not a
change to native population, scoring, sampling, novelty or lineage logic. The same
patch binds the native WebUI only to loopback instead of all interfaces.

The requested **coding session** is Astra Ultra. The local Codex model cache
advertises Astra with `ultra`, but local defaults do not independently prove the
active coding session's effort. The configured **mutation model** is separately
`headless/codex@gpt-6-astra?effort=ultra`. Two actual subscription route checks with
public arithmetic returned usage model `gpt-6-astra`. Ultra was requested and
forwarded unchanged; the backend did not echo its achieved reasoning setting.
This was route verification, not mutation or evolutionary selection. No substitute
model or lower effort was used. Complete output is retained under
`runs/shinka_adapter_logs`; a harmless read-only model-cache write warning occurred.
The initial check reported 14,293 tokens and an API-list-price **estimate** of
$0.03533; that number is not a paid API charge or subscription marginal billing
measurement. The final namespace check took 9.28 seconds and reported 14,278
tokens. Its pricing estimate is null because external pricing endpoints are
outside the allowlist; this does not affect fitness or token accounting. Total
administrative smoke usage is 28,571 reported tokens. Evolutionary mutation,
novelty, meta, prompt-evolution and repair call counts remain zero.
The complete adapter usage JSON is authoritative for token accounting: the pinned
native parser omits Headless's separate cache-read count and maps missing prices
to zero. Native cost fields are therefore not billing measurements. Adapter
`events.jsonl` commits invocation starts before launch; stdout/stderr stream to
protected files so a killed attempt remains inspectable even without a completion
record or returned usage.

## Local embeddings

Model2Vec 0.7.0 loads the genuine pretrained MIT-licensed
`minishlab/potion-base-8M` at revision
`bf8b056651a2c21b8d2565580b8569da283cab23`. Files and SHA256 values are preserved.
The local server exposes the native supported OpenAI-compatible embedding
endpoint; native `EmbeddingClient` successfully returned 256 dimensions with
zero recorded API cost. This is a general-text static embedding model, not a
code-specific semantic model. It supports a novelty heuristic; canonical
specification hashes remain the independent mathematical novelty record.

## Commands

```bash
# Recreate package/runtime assets. Downloads only; no paid model calls.
python3 shinka/bootstrap.py

# Bounded infrastructure checks; no R or model calls.
.venv-shinka/bin/python shinka/check_runtime.py
.venv-shinka/bin/python shinka/check_native_evaluator.py

# Socket/HTTPS/login access checks; no model request or paid call.
python3 shinka/check_network_isolation.py

# Resolve the native configuration and list unmet scientific gates.
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/shinka-matplotlib .venv-shinka/bin/python scripts/run_shinka.py --config shinka/native_config.json

# In a separate terminal when a scientifically ready campaign is to run:
OPENBLAS_NUM_THREADS=1 .venv-shinka/bin/python shinka/embedding_server.py

# Launch/resume; refuses to run until every readiness check and budget passes.
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/shinka-matplotlib .venv-shinka/bin/python scripts/run_shinka.py --config shinka/native_config.json --execute --results-dir runs/evolution_native
```

The native WebUI is automatically kept alive at `http://localhost:8899` during
an actual run. Restricted tool sandboxes may require permission for loopback
binding; local terminal execution does not ordinarily impose that restriction.
The provisional 12 generations are **not** a measured campaign choice. The gate
requires measured candidate cost and a finite walltime budget before execution.
Port 8888 was already occupied by another service during inspection; this project
uses 8899 and refuses to reuse a busy port. Its own native WebUI returned HTTP 200
with the correct HTML. The browser visual check was aborted to release memory
during the R workload, so browser rendering remains unverified. Temporary WebUI,
browser and embedding-server processes were stopped after infrastructure checks.
Intervals of three are configured so migration, meta and prompt evolution can
occur in the proposed finite run, but execution records must prove those events.

References: [native documentation](https://sakanaai.github.io/ShinkaEvolve/),
[native source](https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50),
[official Codex model documentation](https://learn.chatgpt.com/docs/models),
[official Codex authentication](https://learn.chatgpt.com/docs/auth),
[official Codex permissions](https://learn.chatgpt.com/docs/permissions),
[pinned embedding model card](https://huggingface.co/minishlab/potion-base-8M/blob/bf8b056651a2c21b8d2565580b8569da283cab23/README.md).
