"""Source-only contracts. Native initialization is verified separately in R."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import convergence_preflight as p

ROOT = Path(__file__).resolve().parents[1]


def report_fixture():
    return {"status":"verified_no_simulation","stage":"3A","new_simulations":0,
      "new_fits":0,"new_forecasts":0,"target_packets_read":0,"raw_archives_read":0,
      "dry_initialization":{"coefficients_identical":True,"parameter_order_identical":True,
        "fixed_flags_identical":True,"observed_targets_equal":True,"period_targets_equal":True,
        "optimization_iterations":0,"phase3_body_entered":False,"simulator_entered":False,
        "free_coordinates":58,"nsub":0,"n3":3000,"simOnly":False,"seed":2009301},
      "pilot":{"status":"prepared_not_executed"},
      "original_diagnostics":{"full_original_acceptance":False}}


class ConvergencePreflightTests(unittest.TestCase):
    def test_declared_policy(self):
        p.validate_policy(p.read(ROOT/p.POLICY))

    def test_scope_changes_refused(self):
        source=p.read(ROOT/p.POLICY)
        changes={"stage":"3B","packet_member":"data/targets/2010.rds",
                 "new_simulations_allowed":True,"training_years":list(range(1990,2010)),
                 "thresholds":{"individual_strictly_below":0.1,"overall_strictly_below":0.3}}
        for key,value in changes.items():
            with self.subTest(key=key),self.assertRaises(ValueError):
                data=copy.deepcopy(source);data[key]=value;p.validate_policy(data)

    def test_next_pilot_changes_refused(self):
        for key,value in {"simOnly":True,"nsub":3,"n3":1000,"seed":12347,"preserve_original_fixed_flags":False}.items():
            with self.subTest(key=key),self.assertRaises(ValueError):
                data=p.read(ROOT/p.POLICY);data['next_pilot'][key]=value;p.validate_policy(data)

    def make_bundle(self,directory,extra=None,duplicate=False):
        path=Path(directory)/'packets.zip'
        with zipfile.ZipFile(path,'w') as z:
            for name in p.EXPECTED_MEMBERS:z.writestr(name,b'training' if name==p.PACKET else b'UNREAD')
            if extra:z.writestr(extra,b'UNREAD')
            if duplicate:z.writestr(p.PACKET,b'training')
        return path

    def test_only_training_member_is_read(self):
        with tempfile.TemporaryDirectory() as t:
            path=self.make_bundle(t);seen=[];original=zipfile.ZipFile.read
            def tracked(z,name,*args,**kwargs):
                seen.append(name);return original(z,name,*args,**kwargs)
            with patch.object(p,'PACKET_SHA',hashlib.sha256(b'training').hexdigest()),patch.object(zipfile.ZipFile,'read',tracked):
                self.assertEqual(p.training_bytes(path),b'training')
            self.assertEqual(seen,[p.PACKET])

    def test_wrong_packet_hash_refused(self):
        with tempfile.TemporaryDirectory() as t,self.assertRaises(ValueError):
            p.training_bytes(self.make_bundle(t))

    def test_extra_or_unsafe_member_refused(self):
        for name in ('data/targets/2010.rds','../outside'):
            with tempfile.TemporaryDirectory() as t,self.subTest(name=name),self.assertRaises(ValueError):
                p.training_bytes(self.make_bundle(t,extra=name))

    def test_duplicate_member_refused(self):
        with tempfile.TemporaryDirectory() as t,self.assertRaises(ValueError):
            p.training_bytes(self.make_bundle(t,duplicate=True))

    def test_native_report_valid(self):
        p.validate_report(report_fixture())

    def test_native_scope_violation_refused(self):
        for key in ('new_simulations','new_fits','new_forecasts','target_packets_read','raw_archives_read'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                r=report_fixture();r[key]=1;p.validate_report(r)

    def test_native_mismatch_refused(self):
        for key in ('coefficients_identical','parameter_order_identical','fixed_flags_identical','observed_targets_equal','period_targets_equal'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                r=report_fixture();r['dry_initialization'][key]=False;p.validate_report(r)

    def test_wrong_route_refused(self):
        for key,value in {'nsub':3,'n3':1000,'simOnly':True,'seed':12347,
                          'phase3_body_entered':True,'free_coordinates':0}.items():
            with self.subTest(key=key),self.assertRaises(ValueError):
                r=report_fixture();r['dry_initialization'][key]=value;p.validate_report(r)

    def test_historical_acceptance_cannot_be_rewritten(self):
        r=report_fixture();r['original_diagnostics']['full_original_acceptance']=True
        with self.assertRaises(ValueError):p.validate_report(r)

    def test_output_outside_diagnostics_refused_before_read(self):
        with tempfile.TemporaryDirectory() as t,patch.object(p,'inspect') as reader,self.assertRaises(ValueError):
            p.verify(Path(t)/'outside',root=Path(t)/'repo')
        reader.assert_not_called()

    def test_help_and_unexecuted_request_do_not_read_inputs(self):
        for args in (['--help'],['verify']):
            r=subprocess.run([sys.executable,str(ROOT/'scripts/convergence_preflight.py'),*args],cwd='/tmp',capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_guarded_r_route_is_present(self):
        code=(ROOT/'R/convergence_preflight.R').read_text()
        self.assertIn('x$nsub <- 0L',code)
        self.assertIn('prevAns=NULL',code)
        self.assertIn('step3a_expected_stop',code)
        self.assertIn('"phase1.1","phase1.2","phase2.1","proc2subphase","simstats0c","maxlikec"',code)
        self.assertNotIn('fit_model(',code)
        self.assertNotIn('source("R/forecast',code)
        self.assertNotIn('source("R/score',code)

    def test_artifact_tampering_refused(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            names={'inputs.json','verification.json','parameter-map.csv','saved-moment-covariance.csv',
                   'saved-moment-means.csv','native.log','session-info.txt'}
            for n in names:(out/n).write_text('{}')
            (out/'verification.json').write_text(json.dumps(report_fixture()))
            p.write_new(out/'commitment.json',{'stage':'3A','pilot_executed':False,'artifacts':{n:p.sha(out/n) for n in names}})
            self.assertEqual(p.verify_artifacts(out)['status'],'committed_preflight_verified')
            (out/'parameter-map.csv').write_text('modified')
            with self.assertRaises(ValueError):p.verify_artifacts(out)


if __name__=='__main__':unittest.main()
