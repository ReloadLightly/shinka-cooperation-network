"""Source-only regressions. No native estimation, target data, or model calls."""
from __future__ import annotations

from contextlib import closing
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import execution_windows as windows
from scripts import scientific_contract as contract
from scripts import evaluation_feedback as feedback
from scripts import network_specification_v2 as grammar
from scripts import multiobjective_evaluation as evaluator
from scripts import finalist_set as final
from scripts import conventional_search as conventional

module_spec = importlib.util.spec_from_file_location("contract_test_pareto", ROOT / "shinka/pareto_selection.py")
pareto = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = pareto
module_spec.loader.exec_module(pareto)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def spec(*effects):
    return grammar.validate_spec({"schema_version": 2, "network_effects": list(effects)})


def atom(name, parameter=0, **kw):
    return {"effect": name, "parameter": parameter, **kw}


def metric(j=(0., 0., 0.), canonical="a" * 64):
    return {"protocol": "multiobjective-v1", "valid": True, "canonical_sha256": canonical, "complexity": 2,
            **dict(zip(pareto.OBJECTIVES, j)),
            "years": {year: {"valid": True, **dict(zip(pareto.OBJECTIVES, j))} for year in pareto.YEARS}}


class WindowTests(unittest.TestCase):
    def test_unbounded_default(self):
        self.assertIsNone(windows.resolve_deadline())
    def test_numeric_deadline(self):
        self.assertEqual(windows.resolve_deadline(2, now=100), 7300)
    def test_existing_earlier_deadline(self):
        self.assertEqual(windows.resolve_deadline(2, now=100, inherited="200"), 200)
    def test_inherited_without_window(self):
        self.assertEqual(windows.resolve_deadline(inherited="200"), 200)
    def test_invalid_hours(self):
        for value in (0, -1, True, "2", math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                windows.resolve_deadline(value)
    def test_invalid_inherited(self):
        for value in (True, 0, "NaN", "-1", "garbage"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                windows.resolve_deadline(inherited=value)
    def test_remove_stale_env(self):
        with mock.patch.dict(os.environ, {windows.ENVIRONMENT_KEY: "10"}):
            windows.set_deadline(None)
            self.assertNotIn(windows.ENVIRONMENT_KEY, os.environ)
    def test_actual_conventional_config_none(self):
        config = json.loads((ROOT / 'shinka/native_multiobjective_config.json').read_text())
        self.assertIsNone(windows.resolve_deadline(config['resource_policy']['default_session_hours']))


class GrammarTests(unittest.TestCase):
    def test_reference_decodes(self):
        value, _ = grammar.read_program(ROOT / 'candidates/initial_multiobjective.py')
        self.assertEqual(value, spec(atom('degPlus', 1), atom('transTriads')))
    def test_literal_only(self):
        sources = ["import os\ndef build_network_spec(allowed_schema):\n return {}\n",
                   "def build_network_spec(allowed_schema):\n return open('/etc/passwd').read()\n",
                   "def build_network_spec(allowed_schema):\n x=1\n return {}\n",
                   "@print('bad')\ndef build_network_spec(allowed_schema):\n return {}\n",
                   "def build_network_spec(allowed_schema=print('bad')):\n return {}\n"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'candidate.py'
            for source in sources:
                path.write_text(source)
                with self.subTest(source=source), self.assertRaises(grammar.InvalidSpecification):
                    grammar.read_program(path)
    def test_canonical_order(self):
        self.assertEqual(grammar.spec_hash(spec(atom('degPlus', 1), atom('gwesp', 69))),
                         grammar.spec_hash(spec(atom('gwesp', 69), atom('degPlus', 1))))
    def test_root_alias(self):
        self.assertEqual(spec(atom('degPlus', 2)), spec(atom('degPlus', 120)))
    def test_parameter_instances_differ(self):
        self.assertNotEqual(grammar.spec_hash(spec(atom('gwesp', 69))), grammar.spec_hash(spec(atom('gwesp', 70))))
    def test_more_than_three_terms_allowed(self):
        self.assertEqual(len(spec(atom('degPlus', 1), atom('gwesp', 69), atom('outInv', 1), atom('between'))['network_effects']), 4)
    def test_raw_moments_excluded(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec(atom('degPlus', 1), atom('inPop'))
    def test_closure_moments_excluded(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec(atom('gwesp', 0), atom('transTies'))
    def test_product_order(self):
        x, y = atom('gwesp', 69), atom('egoX', covariate='milex.beh')
        self.assertEqual(spec({'product': [x, y]}), spec({'product': [y, x]}))
    def test_native_product_compatibility(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec({'product': [atom('degPlus', 1), atom('transTriads')]})
    def test_zero_gwesp_idempotence(self):
        self.assertEqual(spec({'product': [atom('gwesp'), atom('gwesp')]}), spec(atom('gwesp')))
    def test_duplicate_aliases_rejected(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec(atom('degPlus', 2), atom('degPlus', 3))
    def test_boolean_parameter_rejected(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec(atom('gwesp', True))
    def test_degenerate_knot_rejected(self):
        with self.assertRaises(grammar.InvalidSpecification):
            spec(atom('outTrunc', 160))


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = json.loads((ROOT / 'configs/evaluator-v2.json').read_text())
        self.protocol = json.loads((ROOT / 'configs/multiobjective-v1.json').read_text())
        for name in contract.SCIENTIFIC_FILES:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name)
        for year in (2006, 2007, 2008, 2009):
            path = self.root / f'data/past/{year}.rds'; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic past packet')
        write(self.root / 'environment/versions.json', {'R': 'fixture', 'platform': 'fixture', 'packages': []})
        write(self.root / 'configs/evaluator-v2.json', self.settings)
        write(self.root / 'configs/multiobjective-v1.json', self.protocol)
        write(self.root / 'configs/effect-catalog-v2.json', json.loads((ROOT / 'configs/effect-catalog-v2.json').read_text()))
    def tearDown(self):
        self.tmp.cleanup()
    def layers(self, settings=None):
        return contract.prediction_layers(self.root, spec(atom('gwesp', 69)), 2006, settings or self.settings, self.protocol)
    def test_forecast_seed_does_not_invalidate_fit(self):
        settings = copy.deepcopy(self.settings); settings['forecast']['seed_override'] = 2006002
        a, b = self.layers(), self.layers(settings)
        self.assertEqual(a['fit_sha256'], b['fit_sha256']); self.assertNotEqual(a['forecast_sha256'], b['forecast_sha256'])
    def test_estimator_change_invalidates_both(self):
        a = self.layers(); (self.root / 'R/empirical.R').write_text('changed')
        b = self.layers()
        self.assertNotEqual(a['fit_sha256'], b['fit_sha256']); self.assertNotEqual(a['forecast_sha256'], b['forecast_sha256'])
    def test_forward_change_does_not_invalidate_fit(self):
        a = self.layers(); (self.root / 'R/forecast.R').write_text('changed'); b = self.layers()
        self.assertEqual(a['fit_sha256'], b['fit_sha256']); self.assertNotEqual(a['forecast_sha256'], b['forecast_sha256'])
    def test_score_change_leaves_predictions_alone(self):
        a = self.layers(); (self.root / 'R/score.R').write_text('changed')
        self.assertEqual(a, self.layers())
    def test_science_never_reads_target_or_2010(self):
        # Neither path exists. Fingerprinting still succeeds.
        self.assertEqual(len(contract.scientific_identity(self.root)['sha256']), 64)
        self.assertFalse((self.root / 'data/targets').exists())
    def test_catalog_prose_ignored(self):
        a = contract.scientific_identity(self.root)
        path = self.root / 'configs/effect-catalog-v2.json'; catalog = json.loads(path.read_text())
        catalog['effects']['gwesp']['meaning'] = 'prose only'; write(path, catalog)
        self.assertEqual(a, contract.scientific_identity(self.root))
    def test_catalog_math_bound(self):
        a = contract.scientific_identity(self.root)
        path = self.root / 'configs/effect-catalog-v2.json'; catalog = json.loads(path.read_text())
        catalog['effects']['gwesp']['parameter_rule'] = {'kind': 'ignored', 'canonical': 69}; write(path, catalog)
        self.assertNotEqual(a, contract.scientific_identity(self.root))
    def test_write_once_idempotent(self):
        path = self.root / 'lock.json'; contract.immutable_json(path, {'a': 1}); stamp = path.stat().st_mtime_ns
        contract.immutable_json(path, {'a': 1}); self.assertEqual(stamp, path.stat().st_mtime_ns)
        with self.assertRaises(RuntimeError): contract.immutable_json(path, {'a': 2})
    def test_campaign_mismatch(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            contract.bind_campaign(self.root, {'sha256': 'a'}, {'models': ['one']})
            with self.assertRaises(RuntimeError): contract.bind_campaign(self.root, {'sha256': 'b'}, {'models': ['one']})
    def test_unbound_population_not_relabelled(self):
        with closing(sqlite3.connect(self.root / 'programs.sqlite')) as db, db:
            db.execute('CREATE TABLE programs (id TEXT)'); db.execute("INSERT INTO programs VALUES ('existing')")
        with self.assertRaises(RuntimeError): contract.bind_campaign(self.root, {'sha256': 'a'}, {})
    def test_pending_population_preserved(self):
        with closing(sqlite3.connect(self.root / 'programs.sqlite')) as db, db:
            db.execute('CREATE TABLE project_pending_evaluations (generation INTEGER)'); db.execute('INSERT INTO project_pending_evaluations VALUES (1)')
        with self.assertRaises(RuntimeError): contract.bind_campaign(self.root, {'sha256': 'a'}, {})
    def test_search_stops_after_explicit_plan(self):
        write(self.root / 'results/selection/multiobjective-v1/plan.json', {})
        with self.assertRaises(RuntimeError): contract.require_search_open(self.root)


class ParetoTests(unittest.TestCase):
    def entry(self, name, j, generation=1, canonical=None):
        return pareto.Entry(name, canonical or name, 0, generation, float(generation), j)
    def test_tradeoff_retained_despite_lower_scalar(self):
        a, b = self.entry('a', (.1, 0., 0.)), self.entry('b', (0., .001, 0.))
        keep, _, _ = pareto.retained([a, b], 1)
        self.assertEqual({r.id for r in keep}, {'a', 'b'})
    def test_dominated_removed_at_soft_target(self):
        a, b = self.entry('a', (.1, .1, 1.)), self.entry('b', (0., 0., 0.))
        self.assertEqual([r.id for r in pareto.retained([a, b], 1)[0]], ['a'])
    def test_duplicate_earliest_not_best(self):
        a, b = self.entry('a', (0., 0., 0.), 0, 'same'), self.entry('b', (1., 1., 1.), 1, 'same')
        self.assertEqual([r.id for r in pareto.representatives([b, a])], ['a'])
    def test_invalid_never_admitted(self):
        m = metric(); m['valid'] = False
        self.assertIsNotNone(pareto.validate_metrics(m, None))
    def test_paused_never_admitted(self):
        m = metric(); m.update(valid=False, status='paused_execution_window', J1=None, J2=None, J3=None)
        self.assertIsNotNone(pareto.validate_metrics(m, None))
    def test_incomplete_years_rejected(self):
        m = metric(); del m['years']['2009']; self.assertIsNotNone(pareto.validate_metrics(m, 2))
    def test_wrong_fingerprint_rejected(self):
        with mock.patch.dict(os.environ, {contract.FINGERPRINT_ENV: 'expected'}):
            self.assertIsNotNone(pareto.validate_metrics(metric(), 2))
            m = metric(); m['scientific_fingerprint'] = 'expected'; self.assertIsNone(pareto.validate_metrics(m, 2))
    def test_sql_invalid_and_duplicate_population(self):
        with closing(sqlite3.connect(':memory:')) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('CREATE TABLE programs (id TEXT, correct INTEGER, public_metrics TEXT, combined_score REAL, island_idx INTEGER, generation INTEGER, timestamp REAL)')
            for name, correct in [('good', 1), ('bad', 0)]:
                db.execute('INSERT INTO programs VALUES (?,?,?,?,?,?,?)', (name, correct, json.dumps(metric()), 2 if correct else None, 0, 0, 0))
            with mock.patch.dict(os.environ, {}, clear=True):
                entries, excluded = pareto.read_entries(db.cursor(), types.SimpleNamespace(num_islands=2))
            self.assertEqual([e.id for e in entries], ['good']); self.assertIn('bad', excluded)


class FeedbackTests(unittest.TestCase):
    def test_native_failure_exposes_worst_effect_not_private_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write(folder / 'fit_diagnostics.json', [{'attempt': 1, 'valid': False, 't_ratios': [.1, .6], 'overall_maximum_convergence': .7}])
            (folder / 'training_effects.csv').write_text('name,shortName,parm\ndv.net,density,0\ndv.net,gwesp,69\n')
            value = feedback.failure_summary(folder, 2006, RuntimeError('/private/secret/path'))
            self.assertEqual(value['classification'], 'estimation_not_accepted')
            self.assertEqual(value['attempts'][0]['worst_t_ratios'][0]['effect'], 'gwesp')
            self.assertNotIn('/private', json.dumps(value)); self.assertIsNone(value['scientific_fitness'])
    def test_signal_does_not_claim_oom(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); write(folder / 'process.json', {'exit_code': 137})
            self.assertEqual(feedback.failure_summary(folder, 2006, RuntimeError())['classification'], 'execution_interruption')
    def test_hypothesis_does_not_invent_rationale(self):
        value = spec(atom('gwesp', 69)); h = feedback.hypothesis_record('def f(): pass', value, value, grammar.spec_hash(value), 'fingerprint')
        self.assertFalse(h['rationale_available']); self.assertEqual(h['added_terms'], [])
    def test_effect_mapping_missing_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); write(folder / 'fit_diagnostics.json', [{'t_ratios': [.4]}])
            value = feedback.failure_summary(folder, 2006, RuntimeError())
            self.assertEqual(value['attempts'][0]['worst_t_ratios'][0]['mapping'], 'unavailable')


class FinalistTests(unittest.TestCase):
    def row(self, key, j, c=2):
        return {'canonical_sha256': key, 'complexity': c, **dict(zip(final.OBJECTIVES, j)),
                'combined_score': 2 + (j[0] + j[1] + j[2] / 10) / 3}
    def test_champions_and_reference_are_deduplicated(self):
        rows = [self.row('base', (0, 0, 0)), self.row('a', (.2, 0, 0)), self.row('b', (0, .1, 0)), self.row('c', (0, 0, 2))]
        champions, selected = final.choose_representatives(rows, 'base')
        self.assertEqual(set(champions.values()), {'a', 'b', 'c'})
        self.assertEqual({r['canonical_sha256'] for r in selected}, {'a', 'b', 'c', 'base'})
    def test_ties_use_complexity_then_identity(self):
        rows = [self.row('base', (0, 0, 0)), self.row('a', (1, 1, 1), 2), self.row('b', (1, 1, 1), 1), self.row('c', (1, 1, 1), 1)]
        champions, _ = final.choose_representatives(rows, 'base'); self.assertEqual(set(champions.values()), {'b'})
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): final.choose_representatives([self.row('base', (math.nan, 0, 0))], 'base')
    def test_every_finalist_required_before_access(self):
        plan = {'reference': 'base', 'finalists': [{'canonical_sha256': 'base'}, {'canonical_sha256': 'other'}]}
        with self.assertRaises(RuntimeError): final.verify_commitments(plan, {'base': {'status': 'committed'}})
    def test_dry_final_run_reads_nothing(self):
        with mock.patch.object(sys, 'argv', ['finalist_set.py', 'run']), mock.patch.object(final, 'read_json', side_effect=AssertionError('Unexpected read')):
            self.assertEqual(final.main(), 0)
    def test_five_prespecified_repetitions(self):
        value = final.reporting_policy(); self.assertEqual(value['development_seed_offsets'], [2, 3, 4, 5, 6])
    def test_structured_forecast_not_legacy_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); (folder / 'predictions.rds').write_bytes(b'synthetic')
            settings = {'forecast': {'timeout_seconds': 10}, 'estimation': {'timeout_seconds': 10, 'max_attempts': 4}}
            with mock.patch.object(final, 'prediction_layers', return_value={}), mock.patch.object(final, 'validate_prediction'), mock.patch.object(evaluator, 'deadline_reached', return_value=False), mock.patch.object(evaluator.legacy, 'run_r') as run:
                final.forecast({}, 2010, settings, {}, folder)
            self.assertEqual(Path(run.call_args.args[0][0]).name, 'forecast_multiobjective.R')
    def test_committed_missing_prediction_never_regenerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); write(folder / 'prediction_commit.json', {'sha256': 'missing'})
            with mock.patch.object(final, 'prediction_layers', return_value={}), mock.patch.object(evaluator.legacy, 'run_r') as run:
                with self.assertRaises(RuntimeError): final.forecast({}, 2010, {}, {}, folder)
            run.assert_not_called()
    def test_native_pause_is_not_terminal_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); write(folder / 'checkpoint.json', {'status': 'paused_execution_window'})
            settings = {'forecast': {'timeout_seconds': 10}, 'estimation': {'timeout_seconds': 10, 'max_attempts': 4}}
            with mock.patch.object(final, 'prediction_layers', return_value={}), mock.patch.object(evaluator, 'deadline_reached', return_value=False), mock.patch.object(evaluator.legacy, 'run_r', side_effect=RuntimeError('exit 75')):
                with self.assertRaises(evaluator.ExecutionWindowPaused): final.forecast({}, 2010, settings, {}, folder)


if __name__ == '__main__':
    unittest.main()
