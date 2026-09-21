"""Source-only tests; synthetic results are not empirical convergence evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import convergence_pilot as p

ROOT=Path(__file__).resolve().parents[1]


def fixture(overall=0.3):
    def d(x,n):return dict(draws=n,maximum_absolute_t=0.08,overall=x,individual_pass=True,overall_pass=x<0.25)
    return dict(status='completed',stage='3B',draws=3000,parameters=58,actors=161,
      seed=2009301,nsub=0,simOnly=False,simulator_calls=3000,phase3_entries=1,
      optimization_entries=0,newton_checks=1,coefficients_identical_at_every_simulator_call=True,
      coefficients_identical_after=True,fixed_flags_identical=True,observed_targets_identical=True,
      historical_fit_accepted=False,new_refits=0,new_forecasts=0,target_packets_read=0,
      raw_archives_read=0,training_years=list(range(1990,2009)),
      original=d(0.26134400479858994,1000),fresh_prefix=d(0.27,1000),fresh_full=d(overall,3000),
      fresh_native_diagnostics=dict(native_ok=True,phase3_complete=True,valid=overall<0.25),
      reconstruction=dict(max_t_error=0,max_covariance_error=0,overall_error=0))


class PilotTests(unittest.TestCase):
    def test_policy(self):p.validate_policy(p.pre.read(ROOT/p.POLICY))

    def test_changed_design_rejected(self):
        for k,v in dict(seed=12348,nsub=3,n3=1000,simOnly=True,allow_refit=True,
                        allow_outcomes=True,maximum_native_calls=2,automatic_retries=1).items():
            with self.subTest(k=k),self.assertRaises(ValueError):
                d=p.pre.read(ROOT/p.POLICY);d[k]=v;p.validate_policy(d)

    def test_original_thresholds_required(self):
        d=p.pre.read(ROOT/p.POLICY);d['thresholds']['overall_strictly_below']=0.3
        with self.assertRaises(ValueError):p.validate_policy(d)

    def test_both_pass_and_fail_are_completed_measurements(self):
        for x in (0.2,0.3):p.validate_result(fixture(x))

    def test_guard_violations_rejected(self):
        for k,v in dict(simulator_calls=3001,optimization_entries=1,coefficients_identical_after=False,
                       coefficients_identical_at_every_simulator_call=False,fixed_flags_identical=False,
                       new_refits=1,target_packets_read=1,historical_fit_accepted=True).items():
            with self.subTest(k=k),self.assertRaises(ValueError):
                r=fixture();r[k]=v;p.validate_result(r)

    def test_nan_rejected(self):
        r=fixture();r['fresh_full']['overall']=float('nan')
        with self.assertRaises(ValueError):p.validate_result(r)

    def test_false_acceptance_label_rejected(self):
        r=fixture();r['fresh_full']['overall_pass']=True
        with self.assertRaises(ValueError):p.validate_result(r)

    def test_original_diagnostic_preserved(self):
        r=fixture();r['original']['overall']=0.26
        with self.assertRaises(ValueError):p.validate_result(r)

    def test_reconstruction_error_rejected(self):
        r=fixture();r['reconstruction']['overall_error']=0.01
        with self.assertRaises(ValueError):p.validate_result(r)

    def test_native_completion_required(self):
        r=fixture();r['fresh_native_diagnostics']['phase3_complete']=False
        with self.assertRaises(ValueError):p.validate_result(r)

    def test_cli_dry_no_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/convergence_pilot.py'),'run','--output',t+'/missing'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(list(Path(t).iterdir()),[])

    def test_output_scope_before_inspection(self):
        with tempfile.TemporaryDirectory() as t,patch.object(p,'inspect') as inspect:
            with self.assertRaises(ValueError):p.run(Path(t)/'elsewhere',Path(t))
            inspect.assert_not_called()

    def make_commitment(self,out):
        out.mkdir(parents=True)
        for name in p.REQUIRED:(out/name).write_text('{}')
        p.pre.write_new(out/'extra.json',{})
        (out/'result.json').write_text(json.dumps(fixture()))
        files={f.name:p.pre.sha(f) for f in out.iterdir()}
        p.pre.write_new(out/'commitment.json',dict(stage='3B',status='completed',artifacts=files))

    def test_complete_run_is_idempotent_no_native_execution(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/p.OUTPUT;self.make_commitment(out)
            with patch.object(p,'inspect') as inspect:
                def worker(*args):raise AssertionError('No rerun allowed')
                self.assertEqual(p.run(out,root,worker=worker)['status'],'completed')
                inspect.assert_not_called()

    def test_partial_run_cannot_restart(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/p.OUTPUT;out.mkdir(parents=True)
            with self.assertRaises(OSError):p.run(out,root,worker=lambda *a: self.fail('No retry'))

    def test_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);self.make_commitment(out/'evidence');out=out/'evidence'
            (out/'moment-deviations.rds').write_text('changed')
            with self.assertRaises(ValueError):p.verify_artifacts(out)

    def test_r_guards_and_single_call_present(self):
        code=(ROOT/'R/convergence_pilot.R').read_text()
        self.assertEqual(code.count('siena07('),1)
        for text in ('state$simulator_calls<=3000L','identical(MakeStep,FALSE)',
                     'prevAns=NULL','useCluster=FALSE','check_simulation_state(z,theta,fromFiniteDiff)'):
            self.assertIn(text,code)

    def test_worker_failure_does_not_retry_and_preserves_record(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/p.OUTPUT;calls=[]
            def worker(*args):calls.append(args);return 7
            with patch.object(p,'inspect',return_value={'test':'synthetic'}),patch.object(p.pre,'training_bytes',return_value=b'fixture'):
                with self.assertRaises(RuntimeError):p.run(out,root,worker=worker)
            self.assertEqual(len(calls),1)
            self.assertEqual(p.pre.read(out/'failure.json')['automatic_retries'],0)
            self.assertFalse((out/'training-packet.rds').exists())
            self.assertFalse((out/'commitment.json').exists())


if __name__=='__main__':unittest.main()
