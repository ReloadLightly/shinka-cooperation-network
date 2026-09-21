"""Exercise orchestration with synthetic bytes and a fake native worker.

These fixtures test ordering/recovery, NOT RSiena validity or predictive results.
"""
from __future__ import annotations

from contextlib import ExitStack, nullcontext, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import finalist_set as final
from scripts import multiobjective_evaluation as evaluator
from scripts import scientific_contract as contract
from scripts import conventional_search as conventional
from scripts.network_specification_v2 import read_program, spec_hash


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class FixedSetWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.stack = ExitStack()
        self.stack.enter_context(mock.patch.object(final, 'ROOT', self.root))
        self.stack.enter_context(mock.patch.object(final, 'scientific_identity', return_value={'sha256': 'test-fingerprint'}))
        self.stack.enter_context(mock.patch.object(final, 'prediction_layers', side_effect=lambda root, spec, year, settings, protocol:
            {'fit_sha256': contract.digest([spec, year]), 'forecast': settings['forecast']}))
        self.stack.enter_context(mock.patch.object(evaluator, 'deadline_reached', return_value=False))
        self.stack.enter_context(mock.patch.object(evaluator.legacy, 'run_r', side_effect=self.fake_native))
        self.stack.enter_context(mock.patch.object(evaluator, 'score_saved', side_effect=self.fake_score))
        self.calls = []; self.fail_final_alt = False
        for name in ('configs/evaluator-v2.json', 'configs/multiobjective-v1.json', 'configs/finalist-reporting-v1.json', 'candidates/initial_multiobjective.py', 'R/score.R'):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / name).read_bytes())
        self.settings = json.loads((self.root / 'configs/evaluator-v2.json').read_text())
        self.protocol = json.loads((self.root / 'configs/multiobjective-v1.json').read_text())
        for year in (2006, 2007, 2008, 2009, 2010):
            for kind in ('past', 'targets'):
                path = self.root / f'data/{kind}/{year}.rds'; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic fixture only')
        self.reference, _ = read_program(self.root / 'candidates/initial_multiobjective.py')
        self.alternative = {'schema_version': 2, 'network_effects': [{'effect': 'gwesp', 'parameter': 69}]}
        self.basekey, self.altkey = spec_hash(self.reference), spec_hash(self.alternative)
        for spec in (self.reference, self.alternative):
            for year in final.YEARS:
                folder = self.root / 'results/cache' / spec_hash(spec) / str(year)
                self.make_forecast(folder, spec, year, self.settings)
                self.fake_score(folder, year, self.settings, spec)
        self.stack.enter_context(mock.patch.object(evaluator, 'saved_forecast_folder', side_effect=lambda spec, year, settings, protocol:
            self.root / 'results/cache' / spec_hash(spec) / str(year)))
        baseline = final.require_development(self.reference, self.settings, self.protocol)
        alternate = final.require_development(self.alternative, self.settings, self.protocol)
        comparison = final.differences(alternate, baseline)
        path = self.root / 'results/evaluations/multiobjective-v1' / self.altkey
        write(path / 'metrics.json', {'combined_score': comparison['combined_score'], 'public': {
            'valid': True, 'protocol': 'multiobjective-v1', 'scientific_fingerprint': 'test-fingerprint', 'canonical_sha256': self.altkey,
            **{key: comparison[key] for key in final.OBJECTIVES}}})
        write(path / 'correct.json', {'correct': True})
        (path / 'candidate.py').write_text('def build_network_spec(allowed_schema):\n    return ' + repr(self.alternative) + '\n')

    def tearDown(self):
        self.stack.close(); self.tmp.cleanup()

    def make_forecast(self, folder, spec, year, settings):
        folder.mkdir(parents=True, exist_ok=True)
        seed = settings['forecast'].get('seed_override', year * 1000 + 1)
        for name, content in [('accepted_fit.rds', b'synthetic accepted fit'), ('predictions.rds', f'{spec_hash(spec)}:{year}:{seed}'.encode()), ('simulations.rds', b'synthetic endpoints')]:
            if name != 'accepted_fit.rds' or not (folder / name).exists(): (folder / name).write_bytes(content)
        write(folder / 'fit_diagnostics.json', [{'valid': True}])
        write(folder / 'forecast_audit.json', {'target_outcomes_accessed': False, 'requested_simulations': 1000, 'returned_simulations': 1000,
            'seed': seed, 'conditional': False, 'simOnly': True, 'allowOnly': False})
        if not (folder / 'provenance.json').exists(): write(folder / 'provenance.json', {'fixture': True})
        write(folder / 'prediction_commit.json', {'sha256': contract.file_sha(folder / 'predictions.rds'), 'target': year})

    def fake_native(self, arguments, folder, stage, timeout):
        spec = json.loads((folder / 'specification.json').read_text())
        settings = json.loads((folder / 'settings.json').read_text())
        year = int(arguments[arguments.index('--target') + 1])
        self.calls.append((year, spec_hash(spec), settings['forecast'].get('seed_override', year * 1000 + 1)))
        if self.fail_final_alt and year == 2010 and spec_hash(spec) == self.altkey:
            raise RuntimeError('Synthetic nonconvergence fixture')
        self.make_forecast(folder, spec, year, settings)

    def fake_score(self, folder, year, settings, spec):
        if year == 2010:
            self.assertTrue((final.final_root() / 'outcome_access.json').exists())
            final.verify_commitments(self.plan, json.loads((final.final_root() / 'reservation.json').read_text())['forecasts'])
        alternate = spec_hash(spec) != self.basekey
        # Deliberate final loss: final reporting must include it, not reselect.
        improvement = (.01 if year != 2010 else -.02) if alternate else 0
        score = {'target': year, 'seed': settings['forecast'].get('seed_override', year * 1000 + 1), 'simulations': 1000,
            'primary': {'pr_auc': .8 + improvement, 'brier': .01 + (.001 if alternate else 0)},
            'spending': {'n': 2, 'rmse': .4 - (.01 if alternate else 0)}}
        write(folder / 'scores.json', score)
        write(folder / 'score_provenance.json', {'predictions': contract.file_sha(folder / 'predictions.rds'),
            'target': contract.file_sha(self.root / f'data/targets/{year}.rds'), 'scorer': contract.file_sha(self.root / 'R/score.R'), 'PRROC': '1.3.1'})
        (folder / 'eligibility_mask.rds').write_bytes(b'common synthetic mask')
        return score

    def prepare_lock(self):
        self.plan = final.build_plan()
        contract.immutable_json(final.selection_root() / 'plan.json', self.plan)
        final.sensitivity(self.plan)
        final.lock(self.plan)

    def test_complete_plan_sensitivity_lock_final_and_idempotent_resume(self):
        self.prepare_lock()
        self.assertEqual(len(self.calls), 40)  # 2 models x 4 years x 5 forecast repetitions.
        self.assertTrue(all(year != 2010 for year, _, _ in self.calls))
        result = final.run_final(self.plan)
        self.assertEqual(len(self.calls), 42)
        self.assertLess(result['comparisons'][self.altkey]['J1'], 0)
        before = contract.file_sha(final.final_root() / 'comparison.json')
        self.assertEqual(final.run_final(self.plan), result)
        self.assertEqual(len(self.calls), 42)
        self.assertEqual(contract.file_sha(final.final_root() / 'comparison.json'), before)

    def test_invalid_final_forecast_is_null_and_not_retried_after_access(self):
        self.prepare_lock(); self.fail_final_alt = True
        result = final.run_final(self.plan)
        self.assertIsNone(result['comparisons'][self.altkey])
        self.assertEqual(result['forecasts'][self.altkey]['status'], 'invalid_forecast')
        count = len(self.calls); final.run_final(self.plan); self.assertEqual(len(self.calls), count)

    def test_changed_commitment_refuses_refit(self):
        self.prepare_lock(); final.run_final(self.plan)
        (final.final_root() / 'forecasts' / self.altkey / 'predictions.rds').write_bytes(b'tampered')
        count = len(self.calls)
        with self.assertRaises(RuntimeError): final.run_final(self.plan)
        self.assertEqual(len(self.calls), count)

    def test_incomplete_sensitivity_cannot_lock(self):
        self.plan = final.build_plan(); contract.immutable_json(final.selection_root() / 'plan.json', self.plan)
        value = final.sensitivity(self.plan); value['repetitions'].pop()
        write(final.selection_root() / 'sensitivity.json', value)
        with self.assertRaises(RuntimeError): final.lock(self.plan)
        self.assertFalse((final.selection_root() / 'selected.json').exists())

    def test_selection_rejects_changed_scientific_identity(self):
        plan = final.build_plan()
        with mock.patch.object(final, 'scientific_identity', return_value={'sha256': 'different'}):
            with self.assertRaises(RuntimeError): final.validate_plan(plan)


class ConventionalIntegrationTests(unittest.TestCase):
    def test_unbounded_runner_completes_synthetic_reference(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            for name in ('configs/evaluator-v2.json', 'shinka/native_multiobjective_config.json'):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / name).read_bytes())
            stack.enter_context(mock.patch.object(conventional, 'ROOT', root))
            stack.enter_context(mock.patch.object(conventional, 'execution_lock', side_effect=nullcontext))
            stack.enter_context(mock.patch.object(contract, 'scientific_identity', return_value={'sha256': 'fixture'}))
            stack.enter_context(mock.patch.object(conventional, 'multiobjective_work_snapshot', return_value={'events': {}, 'fits': {}}))
            stack.enter_context(mock.patch.object(evaluator, 'deadline_reached', return_value=False))
            stack.enter_context(mock.patch.dict(os.environ, {}, clear=True))
            def evaluate(program, folder):
                spec, _ = read_program(program)
                write(folder / 'correct.json', {'correct': True})
                write(folder / 'metrics.json', {'combined_score': 2, 'public': {'valid': True, 'status': 'complete', 'protocol': 'multiobjective-v1',
                    'scientific_fingerprint': 'fixture', 'canonical_sha256': spec_hash(spec), 'J1': 0, 'J2': 0, 'J3': 0,
                    'years': {str(year): {} for year in final.YEARS}}})
                return 0
            stack.enter_context(mock.patch.object(evaluator, 'evaluate', side_effect=evaluate))
            args = types.SimpleNamespace(limit=1, native_results_dir=None, results_dir=root / 'results/comparison', execute=True, window_hours=None, search_rule='pareto-local')
            with redirect_stdout(io.StringIO()): self.assertEqual(conventional.run_multiobjective(args), 0)
            state = json.loads((args.results_dir / 'results.json').read_text())
            self.assertTrue(state['complete']); self.assertEqual(state['search_rule'], 'pareto-local')
            self.assertNotIn('SHINKA_EXECUTION_DEADLINE', os.environ)

    def test_pareto_parent_order_keeps_lower_scalar_tradeoff(self):
        rows = [{'canonical_sha256': 'a', 'valid': True, 'J1': .2, 'J2': 0, 'J3': 0},
                {'canonical_sha256': 'b', 'valid': True, 'J1': 0, 'J2': .01, 'J3': 0}]
        state = {'evaluations': rows, 'incumbent': 'a', 'parent_cursor': 1}
        self.assertEqual([r['canonical_sha256'] for r in conventional.multiobjective_parent_order(state, 'pareto-local')], ['b', 'a'])
        self.assertEqual([r['canonical_sha256'] for r in conventional.multiobjective_parent_order(state, 'scalar-local')], ['a'])


if __name__ == '__main__':
    unittest.main()
