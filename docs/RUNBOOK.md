# Execution runbook

This is the command reference for the scientific report in [README.md](../README.md).
The current version-1 baseline retry policy is exhausted; the original ABM drivers
are paused at completed-call checkpoints. No scientific job is currently running.

## Environment, checks and execution

```bash
# Exact scientific environment (public downloads required on a fresh host)
python3 scripts/fetch_sources.py
bash scripts/bootstrap_environment.sh
environment/run-r environment/verify.R

# Trusted data preparation and independent audits
environment/run-r R/audit_data.R
environment/run-r R/source_parity.R
environment/run-r R/audit_forward.R
environment/run-r scripts/check_metrics.R
python3 scripts/check_contract.py

# Serial baseline campaign; current v1 records an exhausted 2006 fit policy
# With unchanged cache identity, this preserves failure; see portability below
python3 scripts/research.py baselines
python3 scripts/research.py status
python3 scripts/update_manifests.py

# Original ABM: one additional full-settings cell, checkpointed; exit75=resume
python3 scripts/paper_reproduction.py --profile full --max-new-calls 1
# Independent original equilibrium cells (six measured cells completed)
python3 scripts/paper_reproduction.py --profile full --stage equilibria --max-new-calls 1
# Reduced grid and S=4, explicitly diagnostic only
python3 scripts/paper_reproduction.py --profile reduced --max-new-calls 21

# Exact native evaluator contract; gates fail closed until audits pass
python3 evaluate.py --program_path candidates/initial.py \
  --results_dir results/evolution_forecast/initial
python3 evaluate.py --program_path candidates/replace_degree.py \
  --results_dir results/evolution_forecast/replace_degree

# Native infrastructure and resolved config; --execute remains readiness-gated
python3 shinka/bootstrap.py
.venv-shinka/bin/python scripts/run_shinka.py
```

Once the substantive candidate has a valid full development evaluation, run:

```bash
python3 scripts/readiness.py --candidate candidates/replace_degree.py --campaign-hours HOURS
```

This derives readiness from artifacts and checks the chosen finite walltime
against measured costs. `HOURS` must be chosen after measurement;
no campaign budget or scientific success is implied by the provisional config.
Conventional search, fresh finalist randomness, selection locking and final-year
commands are documented in [`docs/SELECTION.md`](SELECTION.md).

Run large R tasks serially on this 3.7GiB host. The original two-worker ABM needs
local socket access; restricted execution environments may require an execution
permission exception. See the per-run `process.json`, `stdout.log`, `stderr.log`,
`events.jsonl`, `resources.txt`, and ABM `calls.jsonl` for exact process state,
commands and costs. Repeating an identical cached forecast does not refit on
future data. Protocol/code/environment hashes determine cache identity.

Full setup details: [`environment/README.md`](../environment/README.md) and
[`docs/SHINKA_CONTRACT.md`](SHINKA_CONTRACT.md). Chronological checkpoints:
[`RESEARCH_LOG.md`](../RESEARCH_LOG.md). Every unresolved discrepancy and departure:
[`DEVIATIONS.md`](../DEVIATIONS.md).


## Checkpoint portability

Automatic checkpoint reuse currently requires the original ABM checkout/run
paths and unchanged empirical provenance files. ABM keys include absolute script
paths. Running `environment/verify.R` refreshes a timestamp in
`environment/versions.json`, whose full bytes enter empirical cache identity.
A fresh clone or environment verification can therefore trigger recomputation
rather than resume the published checkpoints. Inspect cache provenance before
launching. The published RDS files are inspectable evidence, not a guarantee of
portable automatic resumption. Fixing these incidental key dependencies remains
implementation work; it must preserve all scientifically relevant cache inputs.
