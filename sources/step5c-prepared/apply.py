"""One-off, exact-base Step 5C assembly; retained only on execution branch."""
from pathlib import Path
import hashlib

EXPECTED = {
 'scripts/replicated_evaluation.py': '3f574b88391b9cd230beef4071022d53244145c4',
 'scripts/run_shinka_replicated.py': '676964de656b18d86eb42d6d6d1a7173b866a103',
 'README.md': '3c98199786ed8e52d71c652640aaff1e572e51b5',
 'docs/RUNBOOK.md': '3f246cce1f5dca74382a453bb4d0cd37c225a7c9',
 'docs/REPLICATED_SHINKA_PROTOCOL.md': 'd70a157b86191be92fa4d6ed889f1bae06631ced',
}
texts = {}
for name, expected in EXPECTED.items():
 data = Path(name).read_bytes()
 actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert actual == expected, (name, actual, expected)
 texts[name] = data.decode()

def change(name, old, new):
 assert texts[name].count(old) == 1, (name, 'replacement count', old[:100])
 texts[name] = texts[name].replace(old, new, 1)

name = 'scripts/replicated_evaluation.py'
change(name, '\n\ndef read(path):', '''

class NumericalPolicyExhausted(ValueError):
    """A terminal inadmissible fit, distinct from infrastructure interruption."""


def read(path):''')
change(name, '\n\ndef run_new_cell(spec, year, cell, root=ROOT):', '''

FAILURE_VERSION = 'replicated-failure-v1'


def save_failure(cell, exc):
    """Bind terminal failures to their complete evidence; never assign a loss."""
    terminal = isinstance(exc, NumericalPolicyExhausted)
    record = {'version': FAILURE_VERSION,
              'kind': 'numerical_policy_exhausted' if terminal else 'interrupted_or_unverified',
              'error': type(exc).__name__, 'message': str(exc),
              'request_sha256': sha(cell/'request.json'),
              'automatic_retry': False, 'fitness': None}
    immutable_json(cell/'failure.json', record)
    if terminal:
        detail = read(cell/'last-native-error.json')
        if detail.get('kind') != 'numerical_policy_exhausted':
            raise IntegrityError('Terminal failure lacks matching native diagnostics')
        commit(cell, 'failure-commitment.json',
               ('failure.json', 'request.json', 'last-native-error.json', 'fit-invocation/native.log'))


def replay_failure(cell, request):
    """Replay an established failure without R, admission, or evidence mutation.

    Legacy untyped, incomplete and altered records remain pauses. Do not infer a
    terminal scientific status merely from an exception message or a directory.
    """
    try:
        record = read(cell/'failure.json')
        if (record.get('version') != FAILURE_VERSION
                or record.get('kind') != 'numerical_policy_exhausted'
                or record.get('error') != 'NumericalPolicyExhausted'
                or record.get('automatic_retry') is not False
                or record.get('fitness') is not None
                or not isinstance(record.get('message'), str)):
            raise IntegrityError('Preserved interrupted/untyped failure requires inspection, not retry')
        verify_manifest(cell, 'failure-commitment.json', version=PROTOCOL)
        if (read(cell/'request.json') != request
                or record['request_sha256'] != sha(cell/'request.json')
                or read(cell/'last-native-error.json').get('kind') != 'numerical_policy_exhausted'):
            raise IntegrityError('Terminal failure identity or native evidence changed')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise IntegrityError('Terminal failure evidence is missing or malformed; preserve and inspect') from exc
    raise NumericalPolicyExhausted(record['message'])


def run_new_cell(spec, year, cell, root=ROOT):''')
change(name, "    # Verify actual pinned source files before invoking a native executable.\n    pf.request(root, spec, year)\n", '')
change(name, "        if (cell / 'failure.json').exists():\n            raise IntegrityError('Preserved failed/interrupted cell must be inspected, not retried')", "        if (cell / 'failure.json').exists():\n            replay_failure(cell, req)\n        # Native source availability is needed only for genuinely new operations.\n        pf.request(root, spec, year)")
change(name, "raise ValueError('Native estimation policy exhausted; complete diagnostics retained')", "raise NumericalPolicyExhausted('Native estimation policy exhausted; complete diagnostics retained')")
change(name, "            immutable_json(cell / 'failure.json', {'error': type(exc).__name__, 'message': str(exc), 'automatic_retry': False, 'fitness': None})", "            save_failure(cell, exc)")
change(name, "        if not allow_new:\n            raise Paused('No compatible saved result for this specification; replay-only mode forbids numerical work')", "        if (cell / 'failure.json').exists():\n            replay_failure(cell, numerical_request(spec, year, root))\n        if not allow_new:\n            raise Paused('No compatible saved result for this specification; replay-only mode forbids numerical work')")

name = 'scripts/run_shinka_replicated.py'
change(name, 'from scripts.execution_windows import resolve_deadline, set_deadline', '''from scripts.execution_windows import resolve_deadline, set_deadline
from scripts.replicated_host import (HostUnavailable, require_runtime, service_ports,
                                     require_free_ports, wait_services, stop_services)''')
change(name, '    require_search_open(ROOT)\n', '''    require_search_open(ROOT)
    ports = service_ports(resolved['settings'], args.webui_port)
    require_free_ports(ports)
    host_report = require_runtime(ROOT)
''')
change(name, "'shinka/multiobjective_native.patch'))}", "'shinka/multiobjective_native.patch','scripts/replicated_host.py'))}")
change(name, "'deadline':deadline,'resolved':resolved", "'deadline':deadline,'resolved':resolved,'local_runtime':host_report")
change(name, '        streams=[];services=[]', '        streams=[];services={}')
change(name, "str(ROOT/'shinka/embedding_server.py'),'--log'", "str(ROOT/'shinka/embedding_server.py'),'--port',str(ports['embedding']),'--log'")
change(name, "                services.append(subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT))", "                services[name]=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)\n            wait_services(services, ports)")
change(name, "            for svc in services:\n                if svc.poll() is None:svc.terminate();svc.wait(timeout=10)\n            for stream in streams:stream.close()", "            try:\n                stop_services(services.values())\n            finally:\n                for stream in streams:stream.close()")
change(name, '    return launch(p.parse_args())', "    try:\n        return launch(p.parse_args())\n    except HostUnavailable as exc:\n        print(str(exc), file=sys.stderr)\n        return 75")

current = '''## Abstract

This project reconstructs Kinne and Kang's Model 3 and studies a separate temporal
forecasting extension: can native ShinkaEvolve discover interpretable network-selection
specifications with improved predictive performance? The current development protocol is
**multiobjective-replicated-v1**. Original controls and spending-equation structure stay
fixed; all coefficients are jointly estimated. Targets are 2006–2009, with five
1,000-endpoint forecast batches per accepted model/year and integer network-count pooling
before PRROC PR-AUC, Brier error and ordinal-spending RMSE are scored.

**Measured starting evidence is complete for two specifications:** reference
`degPlus(1)+transTriads(0)` and the manually specified `degPlus(1)+gwesp(69)` alternative.
The eight model/year cells contain 40 forecast batches. The corrected GWESP objective
vector is **(-0.0027068271812663025, +0.000011269955188679295,
-0.00021712129519249612)**, a predictive trade-off, not a Shinka discovery or overall
improvement. The original floating-point-pooling scores are retained separately.
Original-source reproduction remains partial: seven settings and 86 endpoints.

| Current milestone | Evidence |
|---|---|
| Reference and manually specified alternative | 2 specifications; 8 complete model/year cells |
| Replicated forecasting | 40 batches; 5,000 endpoints per model/year |
| Native Shinka integration | Saved-evidence scheduler, selection and persistence checks recorded |
| Genuine Shinka-generated evaluated descendants | **None established by this handoff** |
| Live inference and execution host | Must be established on the selected authenticated host |

## Current execution route — Step 5C

Use **`scripts/run_shinka_replicated.py`**, not the historical `scripts/run_shinka.py`
commands below. [Step 5C handoff](docs/STEP5C_HANDOFF.md) gives the local checks,
evidence hydration and explicit-budget invocation. [Current scientific protocol](docs/REPLICATED_SHINKA_PROTOCOL.md)
defines replicated evaluation and MC-resolved selection. [Corrected saved comparison](results/diagnostics/replicated-replay-v1/native-shinka/job-gwesp69/metrics.json)
and the [original Step 4 study](https://github.com/ReloadLightly/shinka-cooperation-network/tree/104ba59d81a92f1c98b77c89178fad9178b6ccb4/results/step4-closure-comparison-v1)
are distinct records.

Step 5C repairs terminal numerical-failure replay and adds host/service startup checks.
It does not alter native equations, convergence thresholds, objectives, seeds or measured
predictions. An exhausted estimation policy stays invalid on replay; interruptions and
corrupted evidence remain paused. No host check makes an LLM inference call. A successful
GitHub validation run is not authentication of the user's WSL host, and no new campaign
budget is selected automatically.

The detailed 1,000-endpoint tables and `multiobjective-v1` material below are **historical
protocol/results**, retained for audit rather than instructions to launch the current run.
The current operational scalar is the reference-scaled uncertainty-aware expression in
`docs/REPLICATED_SHINKA_PROTOCOL.md`, not the historical raw-unit scalar in section 3.

'''
name = 'README.md'
start = texts[name].index('## Abstract\n')
end = texts[name].index('## 1. Research question\n')
texts[name] = texts[name][:start]+current+texts[name][end:]
change(name, '## 3. Prespecified evolution and evaluation', '## 3. Historical multiobjective-v1 evolution and evaluation')
change(name, '## 4. Results', '## 4. Historical reproduction and 1,000-endpoint reference results')
old_command = '''R_GC_MEM_GROW=0 .venv-shinka/bin/python scripts/run_shinka.py \\
  --config shinka/native_multiobjective_config.json \\
  --results-dir runs/evolution_multiobjective --execute'''
new_command = '''# Current replicated workflow: check the intended host without new model calls.
.venv-shinka/bin/python scripts/replicated_host.py --check-runtime --check-isolation
# Resolve configuration only (does not create a campaign or perform inference).
.venv-shinka/bin/python scripts/run_shinka_replicated.py --results-dir runs/evolution_replicated
# The explicit-budget execute command is in docs/STEP5C_HANDOFF.md.'''
change(name, old_command, new_command)
change(name, 'The command above starts or resumes the same native campaign.', 'The commands above check the host and resolve configuration only; neither starts evolution.')
change(name, 'The complete reference now permits native multiobjective evolution to propose alternatives directly.', 'The complete replicated starting evidence supports the dedicated launcher after the Step 5C host checks; live model access and a new evaluated descendant remain unestablished.')
change(name, 'The expanded grammar, coefficient-transfer corrections and project Pareto integration are implemented but have not produced an evaluated descendant.', 'The expanded grammar, coefficient-transfer corrections and replicated MC-resolved selection are implemented. The manual GWESP comparison is complete; no Shinka-generated evaluated descendant is established.')

name = 'docs/RUNBOOK.md'
change(name, '# Execution runbook\n', '''# Execution runbook

## Current route: multiobjective-replicated-v1

Use [Step 5C handoff](STEP5C_HANDOFF.md) for the current launcher, host checks,
saved-evidence hydration and explicit cumulative budget. `scripts/run_shinka_replicated.py`
is the current entry point; `scripts/run_shinka.py` below is historical.
The local check does not authenticate model inference or launch a campaign.

```bash
.venv-shinka/bin/python scripts/replicated_host.py --check-runtime --check-isolation
.venv-shinka/bin/python scripts/run_shinka_replicated.py --results-dir runs/evolution_replicated
```

The remaining instructions preserve older protocols and setup history, not the
current replicated launch. Do not execute a historical evaluator to test Step 5C.
''')
change(name, '## Explicit protocol selection (repair step 1)', '## Historical explicit protocol selection (repair step 1)')
change(name, 'Current-protocol examples on the prepared checkout:', 'Historical multiobjective-v1 examples on the prepared checkout:')

name = 'docs/REPLICATED_SHINKA_PROTOCOL.md'
texts[name] += '''

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
'''

for name, text in texts.items():
 Path(name).write_text(text)
 print(name, hashlib.sha256(text.encode()).hexdigest())
