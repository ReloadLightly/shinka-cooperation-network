"""Policy/profile and file-boundary tests; no native fitting or forecasting."""
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
from scripts import precision_fit as p

ROOT=Path(__file__).resolve().parents[1]

class PrecisionTests(unittest.TestCase):
    def profiles(self):
        return tuple(json.loads((ROOT/n).read_text()) for n in
                     (p.SETTINGS,'configs/evaluator-v2.json',p.POLICY))

    def test_profile_changes_only_version_and_selector(self):
        p.validate_profile(*self.profiles())

    def test_old_default_evaluator_stays_unchanged(self):
        protocol=json.loads((ROOT/'configs/multiobjective-v1.json').read_text())
        self.assertEqual(protocol['prediction_settings'],'configs/evaluator-v2.json')
        self.assertNotIn('convergence_assessment',self.profiles()[1]['estimation'])

    def test_threshold_changes_rejected(self):
        for key in ('individual_strictly_below','overall_strictly_below'):
            new,old,policy=self.profiles();policy[key]=0.9
            with self.assertRaises(ValueError):p.validate_profile(new,old,policy)

    def test_budget_seed_role_and_native_mode_changes_rejected(self):
        for key,value in {'diagnostic_draws':1000,'seed_base':123,'nsub':1,'simOnly':True,
                          'maximum_assessments_per_unchanged_vector':2,'role_specific_rules':True}.items():
            new,old,policy=self.profiles();policy[key]=value
            with self.assertRaises(ValueError):p.validate_profile(new,old,policy)

    def test_forecast_and_estimation_changes_rejected(self):
        for section,key in [('forecast','simulations'),('estimation','max_attempts'),('estimation','seed')]:
            new,old,policy=self.profiles();new[section][key]+=1
            with self.assertRaises(ValueError):p.validate_profile(new,old,policy)

    def test_development_only(self):
        for year in (2005,2010,2026):
            with self.assertRaises(ValueError):p.packet_bytes(Path('/missing'),year)

    def test_only_selected_past_packet_read(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);bundle=root/p.BUNDLE;bundle.parent.mkdir(parents=True)
            data=b'synthetic-only'
            with zipfile.ZipFile(bundle,'w') as z:
                for kind in ('past','targets'):
                    for year in p.PACKET_HASHES:z.writestr(f'data/{kind}/{year}.rds',data)
            actual=zipfile.ZipFile.read;seen=[]
            def traced(z,n,*a,**kw):seen.append(n);return actual(z,n,*a,**kw)
            hashes={**p.PACKET_HASHES,2007:hashlib.sha256(data).hexdigest()}
            with patch.object(p,'PACKET_HASHES',hashes),patch.object(zipfile.ZipFile,'read',traced):
                self.assertEqual(p.packet_bytes(root,2007),data)
            self.assertEqual(seen,['data/past/2007.rds'])

    def test_changed_input_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);bundle=root/p.BUNDLE;bundle.parent.mkdir(parents=True)
            with zipfile.ZipFile(bundle,'w') as z:
                for kind in ('past','targets'):
                    for year in p.PACKET_HASHES:z.writestr(f'data/{kind}/{year}.rds',b'changed')
            with self.assertRaises(ValueError):p.packet_bytes(root,2006)

    def test_dry_command_needs_no_inputs(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/precision_fit.py'),'--spec','missing.py',
                          '--target','2006','--output','missing'],cwd='/tmp',capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('Dry request',r.stdout)

    def test_reserved_cli_refused(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/precision_fit.py'),'--spec','missing.py',
                          '--target','2010','--output','missing','--execute'],capture_output=True,text=True)
        self.assertEqual(r.returncode,2)

    def test_output_outside_policy_directory_refused_before_read(self):
        with tempfile.TemporaryDirectory() as t,patch.object(p,'request') as request:
            with self.assertRaises(ValueError):p.run(Path('no.py'),2006,Path(t)/'other',Path(t))
            request.assert_not_called()

    def test_resume_refuses_changed_contract_without_worker(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/'results/precision-fits-v1/demo';out.mkdir(parents=True)
            (out/'request.json').write_text('{"old":true}')
            with patch.object(p,'require_search_open'),patch.object(p,'read_program',return_value=({},'')),\
                 patch.object(p,'request',return_value={'new':True}),patch.object(p,'packet_bytes',return_value=b'x'),\
                 patch.object(p,'native_process') as worker:
                with self.assertRaises(RuntimeError):p.run(Path('fixture'),2006,out,root,runner=worker)
                worker.assert_not_called()

    def test_legacy_directory_refused_without_worker(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/'results/precision-fits-v1/demo';out.mkdir(parents=True)
            (out/'accepted_fit.rds').write_bytes(b'legacy')
            with patch.object(p,'require_search_open'),patch.object(p,'read_program',return_value=({},'')),\
                 patch.object(p,'request',return_value={}),patch.object(p,'packet_bytes',return_value=b'x'),\
                 patch.object(p,'native_process') as worker:
                with self.assertRaises(ValueError):p.run(Path('fixture'),2006,out,root,runner=worker)
                worker.assert_not_called()

    def test_r_policy_does_not_call_scoring_or_forecast(self):
        source=(ROOT/'R/precision_convergence.R').read_text()
        for bad in ('run_forecast(', 'run_forecast_multiobjective(', 'R/score.R', 'data/targets/'):
            self.assertNotIn(bad,source)
        for required in ('previous<-fit','precision_assess_once','verify_only=FALSE','MakeStep,FALSE'):
            self.assertIn(required,source)

    def test_source_identity_includes_new_policy_and_native_helpers(self):
        for name in (p.POLICY,p.SETTINGS,'R/precision_convergence.R','R/network_specification_v2.R'):
            self.assertIn(name,p.SOURCE_FILES)

    def test_acceptance_requires_native_not_only_ratio_pass(self):
        summary = {"version":p.VERSION,"status":"accepted","target":2006,"accepted_attempt":1,
            "authoritative_n3":3000,"new_forecasts":0,"targets_read":0,"diagnostics":{
            "valid":True,"native_ok":True,"phase3_complete":True,"covariance_all_finite":True,
            "finite_identified":True,"termination":"OK","covariance_message":"","phase3_iterations":3000,
            "maximum_absolute_t_ratio":.05,"overall_maximum_convergence":.19,
            **{k:{"shape_valid":True,"any":False} for k in ("divergence","fixed_parameters","newly_fixed_parameters")}}}
        req={"version":p.VERSION,"target":2006}
        p.validate_acceptance(summary,req)
        for key,value in {"native_ok":False,"covariance_message":"warning","phase3_iterations":1000,
                          "overall_maximum_convergence":float("nan")}.items():
            bad=copy.deepcopy(summary);bad["diagnostics"][key]=value
            with self.assertRaises(ValueError):p.validate_acceptance(bad,req)
        with self.assertRaises(ValueError):p.validate_acceptance(summary,{**req,"target":2009})

    def test_legacy_core_hashes_unchanged(self):
        expected=json.loads((ROOT/'configs/convergence-preflight-v1.json').read_text())['preserved_source_sha256']
        for name,sha in expected.items():self.assertEqual(p.sha(ROOT/name),sha,name)

if __name__=='__main__':unittest.main()
