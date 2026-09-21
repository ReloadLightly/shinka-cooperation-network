import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import replicated_evaluation as e
from scripts import replicated_metrics as m
from scripts import run_shinka_replicated as launch
from scripts.network_specification_v2 import validate_spec,spec_hash
sp=importlib.util.spec_from_file_location('replicated_selection_test',ROOT/'shinka/replicated_selection.py')
s=importlib.util.module_from_spec(sp);sys.modules[sp.name]=s;sp.loader.exec_module(s)
FIX=json.loads((ROOT/'tests/fixtures/step4-replicated-scores.json').read_text())['models']
REG=json.loads((ROOT/e.REGISTRY).read_text())
SPECS={row['label']:row['specification'] for row in REG['specifications'].values()}

def rows(label):
    return {y:{**copy.deepcopy(FIX[label][str(y)]),'year':y,'cell_path':'fixture/'+label+'/'+str(y),'replayed':True} for y in m.YEARS}

def public(label='gwesp69'):
    return e.build_metrics(SPECS[label],rows(label),rows('reference'),{'sha256':'f'*64})['public']

class ReplicatedMetrics(unittest.TestCase):
    def test_saved_vector(self):
        p=public();self.assertAlmostEqual(p['J1'],-.0026707754342265855,places=15)
        self.assertAlmostEqual(p['J2'],1.1269955188679295e-5,places=17)
        self.assertAlmostEqual(p['J3'],-.00021712129519249612,places=15)
    def test_saved_uncertainty(self):
        p=public();self.assertAlmostEqual(p['mc_standard_errors'][0],.0010334343773870489,places=15)
        self.assertAlmostEqual(p['mc_intervals'][0][0],-.005540049252865992,places=15)
    def test_reference_is_exact_zero(self):
        p=public('reference');self.assertEqual([p[k] for k in m.KEYS],[0,0,0])
        self.assertEqual(p['mc_standard_errors'],[0,0,0]);self.assertEqual(p['operational']['combined_score'],2)
    def test_point_not_average_auc(self):
        p=public();batch=statistics.mean(x[0] for x in p['batch_vectors'])
        self.assertAlmostEqual(batch,-.00040189951043776985,places=15)
        self.assertNotAlmostEqual(batch,p['J1'],places=5)
    def test_missing_year_rejected(self):
        c={y:r['metrics'] for y,r in rows('gwesp69').items()};r={y:x['metrics'] for y,x in rows('reference').items()};c.pop(2009)
        with self.assertRaises(ValueError):m.aggregate(c,r)
    def test_different_masks_rejected(self):
        c={y:r['metrics'] for y,r in rows('gwesp69').items()};r={y:x['metrics'] for y,x in rows('reference').items()};c[2008]['eligibility_sha256']='x'
        with self.assertRaises(ValueError):m.aggregate(c,r)
    def test_missing_replication(self):
        c=copy.deepcopy(FIX['reference']['2006']['metrics']);c['batches'].pop()
        with self.assertRaises(ValueError):m.validate_cell_metrics(c)
    def test_nonfinite(self):
        with self.assertRaises(ValueError):m.jackknife([0,0,math.nan,0,0])
    def test_scales_reference_only(self):
        a,b=public(),public('reference');self.assertEqual(a['selection_scales'],b['selection_scales'])
    def test_operational_not_old_raw_scalar(self):
        p=public();old=2+(p['J1']+p['J2']+p['J3']/10)/3
        self.assertNotAlmostEqual(old,p['operational']['combined_score'],places=5)
        self.assertTrue(1<=p['operational']['combined_score']<=3)
    def test_tradeoff_is_retained(self):
        a,b=public(),public('reference');self.assertFalse(m.resolved_dominance(a,b));self.assertFalse(m.resolved_dominance(b,a))
    def test_shared_reference_required(self):
        a,b=public(),public('reference');b['reference_identity']='c'*64
        with self.assertRaises(ValueError):m.resolved_dominance(a,b)
    def test_resolved_dominance(self):
        a,b=public('reference'),public('reference')
        for k in m.KEYS:a[k]=.1
        a['delete_one_vectors']=[[.1,.1,.1] for _ in range(5)]
        self.assertTrue(m.resolved_dominance(a,b));self.assertFalse(m.resolved_dominance(b,a))
    def test_uncertain_small_gain_not_resolved(self):
        a,b=public('reference'),public('reference')
        for k in m.KEYS:a[k]=.001
        a['delete_one_vectors']=[[v]*3 for v in (-.05,.05,-.05,.05,0)]
        self.assertFalse(m.resolved_dominance(a,b))
    def test_shared_baseline_noise_cancels(self):
        a,b=public('reference'),public('reference')
        for k in m.KEYS:a[k]=.1
        b['delete_one_vectors']=[[v]*3 for v in (-.5,.5,-.5,.5,0)]
        a['delete_one_vectors']=[[v+.1 for v in row] for row in b['delete_one_vectors']]
        self.assertTrue(m.resolved_dominance(a,b))

class SelectionValidation(unittest.TestCase):
    def test_valid_payload(self):
        p=public();self.assertIsNone(s.validate_metrics(p,p['operational']['combined_score']))
    def test_old_protocol_rejected(self):
        p=public();p['protocol']='multiobjective-v1';self.assertIsNotNone(s.validate_metrics(p,2))
    def test_tampered_vector(self):
        p=public();p['J1']+=.01;self.assertIsNotNone(s.validate_metrics(p,p['operational']['combined_score']))
    def test_tampered_scalar(self):
        p=public();self.assertIsNotNone(s.validate_metrics(p,999))
    def test_tampered_scale(self):
        p=public();p['selection_scales'][1]*=10;self.assertIsNotNone(s.validate_metrics(p,2))
    def test_tampered_uncertainty(self):
        p=public();p['mc_standard_errors'][0]=0;self.assertIsNotNone(s.validate_metrics(p,p['operational']['combined_score']))
    def test_controller_fingerprint(self):
        p=public()
        with patch.dict(os.environ,{'SHINKA_SCIENTIFIC_FINGERPRINT':'a'*64}):self.assertIsNotNone(s.validate_metrics(p,p['operational']['combined_score']))
    def test_null_scientific_fitness_rejected(self):
        self.assertIsNotNone(s.validate_metrics({'protocol':m.PROTOCOL,'valid':False},None))
    def test_entry_replacement_keeps_uncertainty(self):
        from dataclasses import replace
        p=public();a=s.Entry('a','c',0,1,0,tuple(p[k] for k in m.KEYS),tuple(map(tuple,p['delete_one_vectors'])),tuple(p['selection_scales']),p['reference_identity'])
        b=replace(a,island=1);self.assertEqual(a.deletes,b.deletes);self.assertEqual(a.z,b.z)

class Boundaries(unittest.TestCase):
    def test_known_seeds_preserved(self):
        self.assertEqual(e.seeds(SPECS['reference'],2009),[61200901,61200902,61200903,61200904,61200905])
        self.assertEqual(e.seeds(SPECS['gwesp69'],2009),[61200911,61200912,61200913,61200914,61200915])
    def test_alias_identity_same_seeds(self):
        spec={'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':3}]}
        other={'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':2}]}
        self.assertEqual(e.seeds(spec,2006),e.seeds(other,2006))
    def test_general_spec_not_two_name_restriction(self):
        spec=validate_spec({'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':2},{'effect':'gwesp','parameter':40},{'effect':'outInv','parameter':1}]})
        request=e.numerical_request(spec,2008)
        self.assertEqual(request['specification'],spec);self.assertEqual(len(request['forecast_seeds']),5)
        self.assertTrue(all(0<x<2147483647 for x in request['forecast_seeds']))
    def test_unique_twenty_seeds(self):
        spec={'schema_version':2,'network_effects':[{'effect':'gwesp','parameter':40}]}
        self.assertEqual(len({s for y in m.YEARS for s in e.seeds(spec,y)}),20)
    def test_reserved_seed(self):
        with self.assertRaises(ValueError):e.seeds(SPECS['reference'],2010)
    def test_replay_unknown_does_not_execute(self):
        spec={'schema_version':2,'network_effects':[{'effect':'gwesp','parameter':40}]}
        with patch.object(e,'run_new_cell',side_effect=AssertionError('NO native work')):
            with self.assertRaises(e.Paused):e.result_for(spec,Path('/missing'))
    def test_missing_known_evidence_does_not_execute(self):
        with patch.object(e,'run_new_cell',side_effect=AssertionError('NO native work')):
            with self.assertRaises(e.Paused):e.result_for(SPECS['reference'],Path('/missing'),allow_new=True,campaign='/tmp/no',admission_limit=1)
    def test_hash_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'x').write_text('x');e.commit(p,'commitment.json',('x',));e.verify_manifest(p,'commitment.json')
            (p/'x').write_text('y')
            with self.assertRaises(e.IntegrityError):e.verify_manifest(p,'commitment.json')
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'c.json').write_text(json.dumps({'files':{'../escape':'bad'}}))
            with self.assertRaises(e.IntegrityError):e.verify_manifest(p,'c.json')
    def test_budget_counts_canonical_not_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=validate_spec({'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':2}]})
            b=validate_spec({'schema_version':2,'network_effects':[{'effect':'gwesp','parameter':40}]})
            self.assertTrue(e.admit(a,Path(tmp),1,'f'*64));self.assertFalse(e.admit(a,Path(tmp),1,'f'*64))
            with self.assertRaises(e.Paused):e.admit(b,Path(tmp),1,'f'*64)
    def test_budget_cannot_silently_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            e.admit(SPECS['reference'],Path(tmp),1,'f'*64)
            with self.assertRaises(RuntimeError):e.admit(SPECS['gwesp69'],Path(tmp),2,'f'*64)
    def test_bad_code_null_not_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'candidate.py').write_text('import os\nos.system("false")\n')
            with patch.object(e,'run_new_cell',side_effect=AssertionError('NO native work')):
                code=e.evaluate(p/'candidate.py',p/'out')
            self.assertEqual(code,1);self.assertIsNone(json.loads((p/'out/metrics.json').read_text())['combined_score'])
    def test_cli_requires_protocol(self):
        import subprocess
        p=subprocess.run([sys.executable,str(ROOT/'scripts/replicated_evaluation.py'),'--program_path','not-used','--results_dir','not-used'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('--protocol',p.stderr)
    def test_launch_is_dry(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'not_created';r=launch.resolve(p)
            self.assertFalse(r['executed']);self.assertFalse(p.exists());self.assertEqual(r['extra_cmd_args'],{'protocol':m.PROTOCOL})
    def test_launch_bad_budget(self):
        with self.assertRaises(ValueError):launch.resolve('/tmp/no',1,0)
    def test_launch_bad_window(self):
        with self.assertRaises(ValueError):launch.resolve('/tmp/no',math.inf,1)

if __name__=='__main__':unittest.main()
