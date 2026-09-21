"""Synthetic/CLI contracts only. These tests do not execute R or network simulation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import convergence_pilot as p

ROOT=Path(__file__).resolve().parents[1]

def fixture(passes=True):
    overall=0.15 if passes else 0.3
    ratio=0.06 if passes else 0.12
    return {"status":"completed","stage":"3B","seed":2009301,"draws":3000,"replications":1,
      "nsub":0,"simOnly":False,"parameters":58,"actors":161,"coefficients_identical":True,
      "original_fixed_flags_preserved":True,"historical_attempt_accepted":False,"new_refits":0,
      "new_forecasts":0,"target_packets_read":0,"raw_archives_read":0,"step3c_started":False,
      "training_years":list(range(1990,2009)),
      "guard":{"status":"completed","phase3_entries":1,"simulator_entries":3000,"simulator_exits":3000,
        "forbidden_entries":0,"potential_nr_calls":1,"postprocessing_entries":1,"checked_every_simulator_call":True},
      "fresh_first_1000":{"draws":1000,"maximum_absolute_t":0.12,"overall":0.3,"individual_pass":False,"overall_pass":False},
      "fresh_full_3000":{"draws":3000,"maximum_absolute_t":ratio,"overall":overall,"individual_pass":passes,"overall_pass":passes},
      "native_diagnostics":{"valid":passes,"phase3_iterations":3000,"phase3_complete":True,
        "maximum_absolute_t_ratio":ratio,"overall_maximum_convergence":overall}}

class PilotTests(unittest.TestCase):
    def test_declared_plan(self):
        self.assertEqual((p.PLAN['n3'],p.PLAN['seed'],p.PLAN['nsub']), (3000,2009301,0))
        self.assertFalse(p.PLAN['simOnly']);self.assertEqual(p.PLAN['replications'],1)
        self.assertEqual(p.PLAN['fit_sha256'],p.pre.FIT_SHA)

    def test_hash_bound_preflight_sources(self):
        for name,value in p.PREFLIGHT_HASHES.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),value)

    def test_success_and_failed_convergence_both_valid_results(self):
        p.validate_summary(fixture(True));p.validate_summary(fixture(False))

    def test_scope_mutations_rejected(self):
        for key,value in {'seed':1,'draws':1000,'replications':5,'new_refits':1,'nsub':3,
                          'simOnly':True,'historical_attempt_accepted':True,'step3c_started':True}.items():
            with self.subTest(key=key),self.assertRaises(ValueError):
                s=fixture();s[key]=value;p.validate_summary(s)

    def test_coefficient_mutation_rejected(self):
        s=fixture();s['coefficients_identical']=False
        with self.assertRaises(ValueError):p.validate_summary(s)

    def test_missed_guard_rejected(self):
        s=fixture();s['guard']['simulator_exits']=2999
        with self.assertRaises(ValueError):p.validate_summary(s)

    def test_nonfinite_metric_rejected(self):
        for value in (float('nan'),float('inf'),None,True):
            with self.subTest(value=value),self.assertRaises(ValueError):
                s=fixture();s['fresh_full_3000']['overall']=value;p.validate_summary(s)

    def test_false_pass_flag_rejected(self):
        s=fixture(False);s['fresh_full_3000']['overall_pass']=True
        with self.assertRaises(ValueError):p.validate_summary(s)

    def test_native_reconstruction_difference_rejected(self):
        s=fixture();s['native_diagnostics']['overall_maximum_convergence']=0.16
        with self.assertRaises(ValueError):p.validate_summary(s)

    def test_no_overwrite_or_automatic_retry(self):
        with tempfile.TemporaryDirectory() as t,patch.object(p,'inspect') as inspect:
            root=Path(t);out=root/'results/diagnostics/existing';out.mkdir(parents=True)
            with self.assertRaises(FileExistsError):p.run(out,root)
            inspect.assert_not_called()

    def test_outside_diagnostic_output_refused(self):
        with tempfile.TemporaryDirectory() as t,patch.object(p,'inspect') as inspect:
            with self.assertRaises(ValueError):p.run(Path(t)/'outside',Path(t))
            inspect.assert_not_called()

    def test_dry_cli_and_help_need_no_real_data(self):
        for args in (['--help'],['run']):
            r=subprocess.run([sys.executable,str(ROOT/'scripts/convergence_pilot.py'),*args],cwd='/tmp',capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_artifact_verification_and_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            for name in p.REQUIRED:(out/name).write_text('{}')
            (out/'request.json').write_text(json.dumps({'plan':p.PLAN}))
            (out/'summary.json').write_text(json.dumps(fixture(False)))
            p.pre.write_new(out/'commitment.json',{'stage':'3B','artifacts':{n:p.pre.sha(out/n) for n in p.REQUIRED}})
            self.assertFalse(p.verify_artifacts(out)['diagnostic_pass'])
            (out/'raw-phase3.rds').write_text('changed')
            with self.assertRaises(ValueError):p.verify_artifacts(out)

    def test_process_timeout_has_no_lingering_worker(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);marker=root/'should-not-exist'
            code='import time;from pathlib import Path;time.sleep(1);Path('+repr(str(marker))+').write_text("bad")'
            with (root/'log').open('w') as log,self.assertRaises(subprocess.TimeoutExpired):
                p.native_process([sys.executable,'-c',code],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=0.05)
            self.assertFalse(marker.exists())

    def test_r_guards_and_original_sources_not_modified(self):
        code=(ROOT/'R/convergence_pilot.R').read_text()
        for token in ('check_simulation_state','check_phase3_state','MakeStep,FALSE','st$sim_entries<=3000L','prevAns=NULL'):
            self.assertIn(token,code)
        self.assertNotIn('fit_model(',code)
        self.assertNotIn('R/forecast',code)
        self.assertNotIn('R/score',code)

if __name__=='__main__':unittest.main()
