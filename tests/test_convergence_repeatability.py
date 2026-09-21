"""Deterministic and synthetic contracts; no native simulation is performed."""
import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import convergence_repeatability as r
from test_convergence_pilot import fixture

ROOT=Path(__file__).resolve().parents[1]

def cell(label='attempt3',seed=2009302,passes=True):
    s=fixture(passes)
    s.update(stage='3C',fit=label,seed=seed,historical_attempt_accepted=label=='attempt4',step4_started=False)
    s.pop('step3c_started')
    s['guard'].update(seed=seed,nsub=0,n3=3000,simOnly=False,warnings=[],elapsed_seconds=800.0)
    return s

class RepeatabilityTests(unittest.TestCase):
    def test_frozen_plan(self):
        p=r.plan();self.assertEqual(p['new_cells'],9);self.assertEqual(p['new_draws'],27000)
        self.assertEqual(len(r.NEW),9);self.assertNotIn(('attempt3',2009301),r.NEW)
    def test_original_helpers_unchanged(self):
        for n,h in r.plan()['original_implementation_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h)
    def test_disjoint_seeds(self):
        p=r.plan();self.assertFalse(set(p['fits']['attempt3']['seeds'])&set(p['fits']['attempt4']['seeds']))
    def test_both_fit_vectors_and_numerical_outcomes(self):
        for label,seed in r.NEW:
            r.validate_summary(cell(label,seed),label,seed)
            r.validate_summary(cell(label,seed,False),label,seed)
    def test_pilot_never_replayed(self):
        with patch.object(r,'inspect') as i,self.assertRaises(ValueError):r.run_cell('attempt3',2009301)
        i.assert_not_called()
    def test_unknown_cell_never_dispatched(self):
        with patch.object(r,'inspect') as i,self.assertRaises(ValueError):r.run_cell('attempt4',42)
        i.assert_not_called()
    def test_scope_change_refused(self):
        for k,v in {'seed':2009402,'new_refits':1,'draws':1000,'nsub':1,'simOnly':True,'target_packets_read':1,'historical_attempt_accepted':True,'step4_started':True}.items():
            with self.subTest(k=k),self.assertRaises(ValueError):
                s=cell();s[k]=v;r.validate_summary(s,'attempt3',2009302)
    def test_coefficient_guard_refused(self):
        s=cell();s['coefficients_identical']=False
        with self.assertRaises(ValueError):r.validate_summary(s,'attempt3',2009302)
    def test_wrong_guard_seed_refused(self):
        s=cell();s['guard']['seed']=1
        with self.assertRaises(ValueError):r.validate_summary(s,'attempt3',2009302)
    def test_wrong_guard_count_refused(self):
        s=cell();s['guard']['simulator_exits']=2999
        with self.assertRaises(ValueError):r.validate_summary(s,'attempt3',2009302)
    def test_nonfinite_refused(self):
        for v in (None,float('nan'),float('inf'),True):
            s=cell();s['fresh_full_3000']['overall']=v
            with self.assertRaises(ValueError):r.validate_summary(s,'attempt3',2009302)
    def test_exact_cutoff_is_failure(self):
        s=cell(passes=False);s['fresh_full_3000'].update(overall=.25,maximum_absolute_t=.1)
        s['native_diagnostics'].update(overall_maximum_convergence=.25,maximum_absolute_t_ratio=.1)
        r.validate_summary(s,'attempt3',2009302)
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t,patch.object(r,'inspect') as i:
            root=Path(t);(root/r.OUT/'attempt3'/'2009302').mkdir(parents=True)
            with self.assertRaises(FileExistsError):r.run_cell('attempt3',2009302,root)
            i.assert_not_called()
    def test_workflow_rerun_refused(self):
        with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'}),self.assertRaises(ValueError):r.run_cell('attempt3',2009302)
    def test_seen_pilot_separate(self):
        rows=[r.row(cell('attempt3',2009301),'attempt3',True)]
        rows += [r.row(cell(a,s),a,False) for a,s in r.NEW]
        x=r.summarize(rows,[])
        self.assertEqual(x['attempt3_new_only']['n'],4)
        self.assertEqual(x['attempt3_including_seen_pilot']['n'],5)
        self.assertEqual(x['attempt4_new_only']['n'],5)
        self.assertEqual(x['new_completed_cells'],9);self.assertEqual(x['status'],'complete')
    def test_incomplete_is_not_full_study(self):
        x=r.summarize([r.row(cell('attempt3',2009301),'attempt3',True)],[{'seed':2009302}])
        self.assertEqual(x['status'],'partial');self.assertEqual(x['new_completed_cells'],0)
    def test_duplicate_rejected(self):
        x=r.row(cell(),'attempt3',False)
        with self.assertRaises(ValueError):r.summarize([x,x],[])
    def test_native_valid_distinct_from_thresholds(self):
        s=cell();s['native_diagnostics']['valid']=False
        r.validate_summary(s,'attempt3',2009302)
        d=r.describe([r.row(s,'attempt3',False)])
        self.assertEqual(d['full_native_valid'],0);self.assertEqual(d['full3000']['joint_threshold_passes'],1)
    def test_sample_sd(self):
        self.assertEqual(r.stats([1.,2.,3.])['sample_sd'],1.)
        self.assertIsNone(r.stats([1.])['sample_sd'])
    def test_cli_dry_and_help(self):
        for args in [['--help'],['run','--fit','attempt3','--seed','2009302']]:
            p=subprocess.run([sys.executable,str(ROOT/'scripts/convergence_repeatability.py'),*args],cwd='/tmp',capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
    def test_no_scoring_estimator_calls(self):
        code=(ROOT/'R/convergence_repeatability.R').read_text()
        for forbidden in ('fit_model(', 'R/score', 'R/forecast'):
            self.assertNotIn(forbidden,code)
        for required in ('st$sim_entries<=3000L','MakeStep,FALSE','prevAns=NULL','compress="xz"'):
            self.assertIn(required,code)

if __name__=='__main__':unittest.main()
