#!/usr/bin/env python3
"""Generalized replicated evaluator for native Shinka, with explicit execution.

Known Step 4 evidence is read in place and content-verified. A novel specification
uses the same numerical implementation through R/replicated_evaluation.R, but only
when the controller supplies a persistent, explicit canonical-admission budget.
Replay never falls back to fitting or forecasting. All expensive cell operations
are write-once and resumptions reuse completed evidence rather than redraw seeds.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import precision_fit as pf
from scripts import step4_compare as old
from scripts.network_specification_v2 import validate_spec, read_program, spec_hash, complexity
from scripts.scientific_contract import digest, immutable_json, require_search_open, source_hashes
from scripts.replicated_metrics import PROTOCOL, YEARS, KEYS, METRICS, aggregate, operational

CONFIG = 'configs/multiobjective-replicated-v1.json'
REGISTRY = 'configs/replicated-evidence-v1.json'
RESULT_COMMIT = '104ba59d81a92f1c98b77c89178fad9178b6ccb4'
RESULT_SUBDIR = 'results/step4-closure-comparison-v1'
NUMERICAL_FILES = tuple(dict.fromkeys((*pf.SOURCE_FILES, 'R/step4_compare.R', 'R/score.R',
    'R/replicated_evaluation.R', 'R/replicated_score_view.R', 'scripts/step4_compare.py', 'scripts/replicated_evaluation.py',
    'scripts/replicated_metrics.py', CONFIG, REGISTRY)))
COMPATIBLE_FILES = ('R/empirical.R', 'R/network_specification_v2.R', 'R/forecast.R',
    'R/forecast_multiobjective.R', 'R/precision_convergence.R', 'R/step4_compare.R', 'R/score.R',
    'configs/precision-fit-v1.json', 'configs/convergence-assessment-v1.json',
    'configs/effect-catalog-v2.json', 'environment/versions.json')


class Paused(RuntimeError):
    """Resource/unavailable-evidence boundary, never a predictive loss."""


class IntegrityError(RuntimeError):
    """Corrupt/changed committed evidence; requires inspection, not a redraw."""


class NumericalPolicyExhausted(ValueError):
    """A terminal inadmissible fit, distinct from infrastructure interruption."""


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return pf.sha(Path(path))


APPROVED_POLICY_SHA256 = '0c5badb35d87722115a50b255b2eb1e1814c8367c62ea5edee53a879acdd4ea7'


def policy(root=ROOT):
    if sha(root / CONFIG) != APPROVED_POLICY_SHA256:
        raise ValueError('Changed replicated policy requires a new reviewed version')
    p = read(root / CONFIG)
    if (p['version'] != PROTOCOL or p['development_years'] != list(YEARS)
            or p['fit_policy'] != pf.VERSION or p['fit_settings'] != pf.SETTINGS
            or (p['forecast_batches'], p['endpoints_per_batch']) != (5, 1000)
            or not p['pool_before_scoring'] or p['reserved_year_access'] is not False):
        raise ValueError('Changed replicated protocol requires a separately reviewed version')
    if p['metrics'] != list(METRICS) or p['signs'] != [1, -1, -1]:
        raise ValueError('Changed metric definitions')
    reg = read(root / REGISTRY)
    if reg['source_commit'] != RESULT_COMMIT or reg['path'] != RESULT_SUBDIR:
        raise IntegrityError('Wrong original evidence registry')
    return p


def identity(root=ROOT):
    p = policy(root)
    payload = {'version': PROTOCOL, 'policy': p, 'files': source_hashes(root, NUMERICAL_FILES),
               'past': {str(y): pf.PACKET_HASHES[y] for y in YEARS},
               'target': {str(y): old.TARGET_HASHES[y] for y in YEARS},
               'native_expected': read(root / 'configs/convergence-preflight-v1.json')['native_source_files']
                   if 'native_source_files' in read(root / 'configs/convergence-preflight-v1.json') else
                   read(root / 'configs/convergence-preflight-v1.json')}
    return {'sha256': digest(payload), 'payload': payload}


def seeds(spec, year, root=ROOT):
    if type(year) is not int or year not in YEARS:
        raise ValueError('Development years only')
    canonical = spec_hash(validate_spec(spec))
    reg = read(root / REGISTRY)['specifications']
    if canonical in reg:
        index = ('reference', 'gwesp69').index(reg[canonical]['label'])
        return [61000000 + 100 * year + 10 * index + b for b in range(1, 6)]
    # Reserve all 20 seeds as a contiguous block. Known original slots are outside
    # this range. A controller ledger detects rare cross-specification collisions.
    block = int(hashlib.sha256(('replicated-seeds-v1:' + canonical).encode()).hexdigest(), 16) % 90000000
    return [70000000 + 20 * block + 5 * (year - 2006) + b for b in range(5)]


def numerical_request(spec, year, root=ROOT):
    spec = validate_spec(spec)
    if year not in YEARS:
        raise ValueError('Development targets only')
    return {'version': PROTOCOL, 'target': year, 'model': spec_hash(spec), 'specification': spec,
            'training': [1990, year - 1], 'past_sha256': pf.PACKET_HASHES[year],
            'settings': read(root / pf.SETTINGS), 'policy': read(root / pf.POLICY),
            'scientific_fingerprint': identity(root)['sha256'],
            'forecast_seeds': seeds(spec, year, root),
            'import_history': {'attempts': {}, 'reason': 'Novel fits have no cross-model warm start'},
            'numerical_budget_seconds': policy(root)['new_evaluation_budget']['cell_seconds']}


def verify_manifest(folder, name, expected_hash=None, version=None):
    folder = Path(folder).resolve()
    manifest = folder / name
    if expected_hash and sha(manifest) != expected_hash:
        raise IntegrityError(f'Changed pinned manifest: {manifest}')
    m = read(manifest)
    if version and m.get('version') != version:
        raise IntegrityError('Wrong evidence version')
    files = m.get('files')
    if not isinstance(files, dict) or not files:
        raise IntegrityError('Empty evidence commitment')
    for relative, expected in files.items():
        path = (folder / relative).resolve()
        try:
            path.relative_to(folder)
        except ValueError as e:
            raise IntegrityError('Unsafe commitment path') from e
        if not path.is_file() or sha(path) != expected:
            raise IntegrityError(f'Changed or missing committed evidence: {relative}')
    return m


def commit(folder, name, required=()):
    files = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
             if p.is_file() and p.name not in (name, 'run.lock')}
    if not set(required).issubset(files):
        raise IntegrityError('Missing required evidence')
    immutable_json(folder / name, {'version': PROTOCOL, 'files': files})


def evidence_root():
    return Path(os.environ.get('SHINKA_REPLICATED_EVIDENCE_ROOT', str(ROOT))).resolve()


def load_imported(spec, year, evidence, root=ROOT):
    """No outcome-packet read and no native calls. Verify every committed byte."""
    spec = validate_spec(spec)
    canonical = spec_hash(spec)
    reg = read(root / REGISTRY)
    entry = reg['specifications'].get(canonical)
    if entry is None:
        return None
    if entry['specification'] != spec or type(year) is not int or year not in YEARS:
        raise IntegrityError('Wrong imported specification or target')
    cell = Path(evidence) / RESULT_SUBDIR / entry['label'] / str(year)
    if not (cell / 'cell-commitment.json').is_file():
        raise Paused(f'Pinned evidence not hydrated: {cell}. Replay may not regenerate it.')
    manifest = verify_manifest(cell, 'cell-commitment.json', entry['cells'][str(year)], old.VERSION)
    req = read(cell / 'request.json')
    if (validate_spec(req['specification']) != spec or req['target'] != year
            or req['training'] != [1990, year-1] or req['past_sha256'] != pf.PACKET_HASHES[year]
            or req['forecast_seeds'] != seeds(spec, year, root)):
        raise IntegrityError('Incompatible imported request')
    for name in COMPATIBLE_FILES:
        if req['source_sha256'].get(name) != sha(root / name):
            raise IntegrityError(f'Historical scientific implementation changed: {name}')
    accepted = read(cell / 'fit/accepted.json')
    pf.validate_acceptance(accepted, {'version': pf.VERSION, 'target': year})
    verify_manifest(cell / 'fit', 'commitment.json', version=old.VERSION)
    for batch, seed in enumerate(seeds(spec, year, root), 1):
        f = cell / 'forecasts' / str(batch)
        a = read(f / 'receipt-audit.json')
        if (a['seed'] != seed or a['target'] != year or a['simulations'] != 1000
                or a['authoritative_n3'] != accepted['authoritative_n3']
                or a['accepted_attempt'] != accepted['accepted_attempt']
                or a['fit_sha256'] != sha(cell / 'fit/accepted_fit.rds')
                or a['new_estimation_calls'] != 0 or a['target_reads'] != 0
                or a['all_forward_coefficients_fixed'] is not True):
            raise IntegrityError('Imported forecast receipt mismatch')
        verify_manifest(f, 'prediction-commitment.json', version=old.VERSION)
    verify_manifest(cell / 'pooled', 'prediction-commitment.json', version=old.VERSION)
    views = entry.get('score_views', {})
    if str(year) not in views:
        raise Paused('Read-only integer-count score view has not been validated and published')
    view = views[str(year)]
    viewpath = (root / view['path']).resolve()
    viewpath.relative_to(root.resolve())
    if sha(viewpath) != view['sha256']:
        raise IntegrityError('Changed derived score view')
    derived = read(viewpath)
    if (derived['version'] != 'integer-network-count-pooling-v1'
        or derived['source_cell_commitment'] != entry['cells'][str(year)]
        or derived['source_commit'] != RESULT_COMMIT
        or derived['correction_source_sha256'] != sha(root/'R/replicated_score_view.R')):
        raise IntegrityError('Derived score view is not bound to verified original forecasts')
    metrics = derived['metrics']
    from scripts.replicated_metrics import validate_cell_metrics
    validate_cell_metrics(metrics)
    return {'year': year, 'specification': spec, 'metrics': metrics, 'accepted': accepted,
            'cell_path': str(cell), 'evidence_sha256': digest({'original':entry['cells'][str(year)],'score_view':view['sha256']}),
            'source_commit': RESULT_COMMIT, 'replayed': True,
            'verified_files': len(manifest['files'])}


def cache_root():
    return Path(os.environ.get('SHINKA_REPLICATED_CACHE', str(ROOT / 'results/replicated-evaluations-v1'))).resolve()


def validate_new_cell(cell, spec, year, root=ROOT):
    m = verify_manifest(cell, 'cell-commitment.json', version=PROTOCOL)
    if read(cell / 'request.json') != numerical_request(spec, year, root):
        raise IntegrityError('Changed cache identity')
    pf.validate_acceptance(read(cell / 'fit/accepted.json'), {'version': pf.VERSION, 'target': year})
    verify_manifest(cell / 'fit', 'commitment.json', version=PROTOCOL)
    for b in range(1,6):
        verify_manifest(cell / 'forecasts' / str(b), 'prediction-commitment.json', version=PROTOCOL)
    verify_manifest(cell / 'pooled', 'prediction-commitment.json', version=PROTOCOL)
    return {'year': year, 'specification': spec, 'metrics': read(cell / 'scores/comparison-metrics.json'),
            'accepted': read(cell / 'fit/accepted.json'), 'cell_path': str(cell),
            'evidence_sha256': sha(cell / 'cell-commitment.json'), 'replayed': True,
            'verified_files': len(m['files'])}


def admit(spec, campaign, limit, fingerprint, root=ROOT):
    """Count unique admitted models, including failed ones. Never reset a budget."""
    if type(limit) is not int or limit < 1:
        raise Paused('New numerical work requires an explicit positive canonical admission limit')
    campaign = Path(campaign)
    campaign.mkdir(parents=True, exist_ok=True)
    with (campaign / 'numerical-admissions.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        contract = {'version': PROTOCOL, 'limit': limit, 'scientific_fingerprint': fingerprint}
        immutable_json(campaign / 'numerical-budget.json', contract)
        ledger_path = campaign / 'numerical-admissions.json'
        ledger = read(ledger_path) if ledger_path.exists() else {}
        canonical = spec_hash(spec)
        declared = [s for y in YEARS for s in seeds(spec, y, root)]
        if canonical in ledger:
            if ledger[canonical]['seeds'] != declared:
                raise IntegrityError('Admitted seed identity changed')
            return False
        if len(ledger) >= limit:
            raise Paused('Unique numerical admission budget exhausted; preserve this pending proposal')
        if any(set(declared).intersection(row['seeds']) for row in ledger.values()):
            raise IntegrityError('Deterministic seed collision; no adaptive seed replacement permitted')
        ledger[canonical] = {'seeds': declared, 'admitted_unix': time.time()}
        tmp = ledger_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(ledger, indent=2) + '\n')
        tmp.replace(ledger_path)
        return True


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


def run_new_cell(spec, year, cell, root=ROOT):
    """Explicit native path; never reached by replay-only evaluation."""
    req = numerical_request(spec, year, root)
    cell.mkdir(parents=True, exist_ok=True)
    with (cell / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        immutable_json(cell / 'request.json', req)
        immutable_json(cell / 'specification.json', spec)
        if (cell / 'cell-commitment.json').exists():
            return validate_new_cell(cell, spec, year, root)
        if (cell / 'failure.json').exists():
            replay_failure(cell, req)
        # Native source availability is needed only for genuinely new operations.
        pf.request(root, spec, year)
        # A restart at a completed phase boundary does not buy a new four hours.
        budget_path = cell / 'wall-budget.json'
        used = read(budget_path)['seconds_used'] if budget_path.exists() else 0.0
        start = time.monotonic()
        def invoke(out, args, cap):
            remaining = int(req['numerical_budget_seconds'] - used - (time.monotonic() - start))
            if remaining <= 0:
                raise Paused('Cell native wall budget exhausted')
            deadline = os.environ.get('SHINKA_EXECUTION_DEADLINE')
            if deadline and time.time() >= float(deadline):
                raise Paused('Controller admission window closed at completed operation boundary')
            # An already-started operation is never implicitly repeated.
            if (out / 'started.json').exists():
                if not (out/'boundary-paused.json').is_file():
                    raise IntegrityError(f'Uncompleted operation preserved: {out}')
                # Only an explicitly recorded cooperative boundary can resume.
                # Every admitted native atomic operation must have completed.
                for startfile in (cell/'fit').rglob('started.rds'):
                    if not (startfile.parent/'complete.rds').exists():
                        raise IntegrityError('Interrupted atomic R operation cannot be restarted')
                history=out/'execution_windows'/str(time.time_ns());history.mkdir(parents=True)
                for name in ('started.json','native.log','resources.txt','boundary-paused.json'):
                    path=out/name
                    if path.exists():shutil.move(str(path),str(history/name))
            out.mkdir(parents=True, exist_ok=True)
            immutable_json(out / 'started.json', {'args': args, 'version': PROTOCOL, 'cap': min(cap, remaining)})
            with (out / 'native.log').open('x') as log:
                try:
                    old.native_process(['/usr/bin/time', '-v', '-o', str(out / 'resources.txt'),
                        str(root / 'environment/run-r'), 'R/replicated_evaluation.R', *args],
                        cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=min(cap, remaining))
                except subprocess.CalledProcessError as exc:
                    errorfile=cell/'last-native-error.json'
                    detail=read(errorfile) if errorfile.exists() else {}
                    if exc.returncode==75 and detail.get('kind')=='boundary_paused':
                        immutable_json(out/'boundary-paused.json',{'version':PROTOCOL,'boundary':detail})
                        raise Paused('Cooperative R boundary; resume from completed native checkpoints') from exc
                    if detail.get('kind')=='numerical_policy_exhausted':
                        raise NumericalPolicyExhausted('Native estimation policy exhausted; complete diagnostics retained') from exc
                    raise IntegrityError('Native execution error; inspect saved log/diagnostics rather than scoring it as bad prediction') from exc
        try:
            with tempfile.TemporaryDirectory(prefix='replicated-past-') as tmp:
                past = Path(tmp) / 'past.rds'; past.write_bytes(pf.packet_bytes(root, year))
                fit = cell / 'fit'
                if not (fit / 'commitment.json').exists():
                    invoke(cell / 'fit-invocation', ['fit', str(cell), str(past), spec_hash(spec), str(year)], req['numerical_budget_seconds'])
                    pf.validate_acceptance(read(fit / 'accepted.json'), {'version': pf.VERSION, 'target': year})
                    commit(fit, 'commitment.json', ('accepted_fit.rds','accepted.json','request.json'))
                verify_manifest(fit, 'commitment.json', version=PROTOCOL)
                for b in range(1,6):
                    out = cell / 'forecasts' / str(b)
                    if not (out / 'prediction-commitment.json').exists():
                        invoke(out, ['forecast', str(cell), str(past), spec_hash(spec), str(year), str(b)], 1800)
                        a = read(out / 'receipt-audit.json')
                        if a['seed'] != req['forecast_seeds'][b-1] or a['target_reads'] != 0:
                            raise IntegrityError('Forward call disagrees with frozen seeds or visibility')
                        commit(out, 'prediction-commitment.json', ('predictions.rds','simulations.rds','receipt-audit.json'))
                    verify_manifest(out, 'prediction-commitment.json', version=PROTOCOL)
                pool = cell / 'pooled'
                if not (pool / 'prediction-commitment.json').exists():
                    invoke(cell / 'pool-invocation', ['pool', str(cell)], 900)
                    commit(pool, 'prediction-commitment.json', ('predictions.rds',*[f'delete-{b}.rds' for b in range(1,6)]))
                verify_manifest(pool, 'prediction-commitment.json', version=PROTOCOL)
            # Only after ALL probability commitments are verified open this year's outcome.
            with tempfile.TemporaryDirectory(prefix='replicated-outcome-') as tmp:
                target = Path(tmp) / 'target.rds'; target.write_bytes(old.target_bytes(root, year))
                if not (cell / 'scores/comparison-metrics.json').exists():
                    invoke(cell / 'score-invocation', ['score', str(cell), str(target)], 1800)
            immutable_json(cell / 'execution.json', {'status':'complete','new_forecasts':5,'new_endpoints':5000,'reserved_year_access':False})
            # Persist budget before binding the complete cell.
            (cell / 'wall-budget.json').write_text(json.dumps({'seconds_used': used + time.monotonic()-start})+'\n')
            commit(cell, 'cell-commitment.json', ('scores/comparison-metrics.json','execution.json','request.json'))
            result = validate_new_cell(cell, spec, year, root)
            result['replayed'] = False
            return result
        except Paused:
            (cell / 'wall-budget.json').write_text(json.dumps({'seconds_used': used + time.monotonic()-start})+'\n')
            raise
        except Exception as exc:
            (cell / 'wall-budget.json').write_text(json.dumps({'seconds_used': used + time.monotonic()-start})+'\n')
            save_failure(cell, exc)
            raise


def result_for(spec, evidence, root=ROOT, allow_new=False, campaign=None, admission_limit=None):
    spec = validate_spec(spec)
    rows = {}
    admitted = False
    for year in YEARS:
        imported = load_imported(spec, year, evidence, root)
        if imported:
            rows[year] = imported
            continue
        cell = cache_root() / identity(root)['sha256'] / spec_hash(spec) / str(year)
        if (cell / 'cell-commitment.json').is_file():
            rows[year] = validate_new_cell(cell, spec, year, root)
            continue
        if (cell / 'failure.json').exists():
            replay_failure(cell, numerical_request(spec, year, root))
        if not allow_new:
            raise Paused('No compatible saved result for this specification; replay-only mode forbids numerical work')
        if not admitted:
            if campaign is None:
                raise Paused('Explicit persistent campaign directory required before numerical admission')
            admit(spec, campaign, admission_limit, identity(root)['sha256'], root)
            admitted = True
        rows[year] = run_new_cell(spec, year, cell, root)
    return rows


def build_metrics(spec, candidates, reference, science):
    values = aggregate({y:r['metrics'] for y,r in candidates.items()}, {y:r['metrics'] for y,r in reference.items()})
    reference_id = digest({str(y):reference[y]['evidence_sha256'] for y in YEARS})
    public = {'protocol':PROTOCOL,'status':'complete','valid':True,'canonical_sha256':spec_hash(spec),
        'canonical_specification':spec,'scientific_fingerprint':science['sha256'],
        'reference_identity':reference_id,'complexity':complexity(spec)['estimated_network_terms'],
        'forecast_batches_per_year':5,'pooled_endpoints_per_year':5000,**values,
        'replayed_all_years':all(r['replayed'] for r in candidates.values()),
        'preexisting_step4_evidence':all(r.get('source_commit')==RESULT_COMMIT for r in candidates.values()),
        'native_fit_receipts':{str(y):{'accepted_attempt':r['accepted']['accepted_attempt'],
            'authoritative_n3':r['accepted']['authoritative_n3'], 'diagnostics':{k:r['accepted']['diagnostics'][k] for k in ('maximum_absolute_t_ratio','overall_maximum_convergence','native_ok','termination','phase3_complete','finite_identified')}} for y,r in candidates.items()},
        'structural_feedback':{str(y):r['metrics'].get('structural_checks',[]) for y,r in candidates.items()}}
    # Mean structural summaries keep mutation context concise; full arrays stay private.
    raw_structure = public.pop('structural_feedback')
    public['structural_feedback'] = {}
    for y, blocks in raw_structure.items():
        if blocks:
            public['structural_feedback'][y] = {'observed':blocks[0]['observed'],
                'simulated_means':{item['statistic']:statistics.mean(next(i['mean'] for i in b['simulated'] if i['statistic']==item['statistic']) for b in blocks)
                                   for item in blocks[0]['simulated']}}
    feedback = ('Replicated predictive model comparison: ' + '; '.join(f'{k}={public[k]:+.12g}' for k in KEYS)
        + '. Coefficients statistically estimated; controls and Model 3 spending structure protected. '
        + 'Every year has five forecast batches; score pooled probabilities, not mean AUC. '
        + 'Monte Carlo intervals are approximate, conditional on selected fits; not causal or fitting/generalization uncertainty. '
        + 'Archive and parents use the declared MC-resolved heuristic; unresolved models remain eligible. '
        + ('This result reuses preexisting measured evidence, not a new discovery.' if public['replayed_all_years'] else 'New numerical evidence is recorded separately from reuse.'))
    return {'combined_score':public['operational']['combined_score'],'public':public,
            'private':{'candidate_cells':{str(y):r['cell_path'] for y,r in candidates.items()},
                       'reference_cells':{str(y):r['cell_path'] for y,r in reference.items()}},'text_feedback':feedback}


def evaluate(program, output, *, root=ROOT, evidence=None, allow_new=False, campaign=None, admission_limit=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    spec=None; science=None
    try:
        require_search_open(root)
        if (root/'results/selection/multiobjective-replicated-v1/plan.json').exists():
            raise IntegrityError('Replicated finalist lock prevents further search')
        spec, source = read_program(Path(program))
        science=identity(root)
        expected=os.environ.get('SHINKA_SCIENTIFIC_FINGERPRINT')
        if expected and expected!=science['sha256']:
            raise IntegrityError('Controller and evaluator scientific identities differ')
        immutable_json(output/'evaluation-request.json', {'protocol':PROTOCOL,'canonical_sha256':spec_hash(spec),
            'specification':spec,'scientific_fingerprint':science['sha256']})
        evidence=Path(evidence) if evidence is not None else evidence_root()
        refspec=validate_spec(policy(root)['reference'])
        reference=result_for(refspec,evidence,root,allow_new=False)
        candidates=reference if spec==refspec else result_for(spec,evidence,root,allow_new=allow_new,campaign=campaign,admission_limit=admission_limit)
        result=build_metrics(spec,candidates,reference,science)
        (output/'metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        (output/'correct.json').write_text(json.dumps({'correct':True,'error':''})+'\n')
        immutable_json(output/'canonical_specification.json',spec)
        return 0
    except Exception as exc:
        # Missing inputs, changed evidence and resource pauses must not be learned as a bad model.
        paused=isinstance(exc,(Paused,IntegrityError,TimeoutError,subprocess.TimeoutExpired,FileNotFoundError))
        public={'protocol':PROTOCOL,'status':'paused_execution_window' if paused else 'invalid_evaluation',
                'valid':False,**{k:None for k in KEYS},'reason':f'{type(exc).__name__}: {exc}'}
        if spec is not None: public.update(canonical_sha256=spec_hash(spec),canonical_specification=spec)
        if science: public['scientific_fingerprint']=science['sha256']
        if spec is not None and science is not None:
            failures={}
            for y in YEARS:
                errorfile=cache_root()/science['sha256']/spec_hash(spec)/str(y)/'last-native-error.json'
                if errorfile.is_file():
                    detail=read(errorfile)
                    summaries=[]
                    for item in detail.get('completed_fit_diagnostics',[]):
                        d=item.get('diagnostics',{})
                        summaries.append({k:d.get(k) for k in ('valid','maximum_absolute_t_ratio','overall_maximum_convergence','native_ok','termination','phase3_complete','finite_identified','t_ratios')})
                    failures[str(y)]={'kind':detail.get('kind'),'message':detail.get('message'),'completed_fit_diagnostics':summaries}
            if failures:public['failure_diagnostics']=failures
        (output/'metrics.json').write_text(json.dumps({'combined_score':None,'public':public,'private':{},
            'text_feedback':('PAUSED; preserve same candidate and inspect boundary. ' if paused else 'INVALID specification/evaluation; no scientific loss assigned. ')+str(exc)},indent=2)+'\n')
        (output/'correct.json').write_text(json.dumps({'correct':False,'error':str(exc)})+'\n')
        (output/'error.log').write_text(traceback.format_exc())
        return 75 if paused else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program_path',type=Path,required=True);p.add_argument('--results_dir',type=Path,required=True)
    p.add_argument('--protocol',choices=[PROTOCOL],required=True)
    a=p.parse_args()
    allow=os.environ.get('SHINKA_REPLICATED_ALLOW_NEW')=='1'
    limit=os.environ.get('SHINKA_REPLICATED_ADMISSION_LIMIT')
    return evaluate(a.program_path,a.results_dir,allow_new=allow,
                    campaign=os.environ.get('SHINKA_REPLICATED_CAMPAIGN'),
                    admission_limit=int(limit) if limit else None)

if __name__=='__main__':
    raise SystemExit(main())
