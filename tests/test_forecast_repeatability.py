"""Source/synthetic workflow contracts, never empirical forecast evidence."""
import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import forecast_repeatability as r


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(root):
    for name in (*r.BOUND_SOURCES,'configs/evaluator-v2.json','configs/effect-catalog-v2.json','candidates/initial_multiobjective.py'):
        dst=root/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(r.ROOT/name,dst)
    settings=r.read(root/'configs/evaluator-v2.json')
    manifest={'baseline_years':{}}
    for year in r.YEARS:
        folder=root/f'results/cache/fixture-{year}'; folder.mkdir(parents=True)
        manifest['baseline_years'][str(year)]={'cache_directory':str(folder.relative_to(root))}
        for name in r.INPUT_RECORDS:
            (folder/name).write_bytes(b'synthetic fixture: not RDS')
        save(folder/'settings.json',settings)
        save(folder/'specification.json',{'schema_version':1,'network_effects':['degPlus','transTriads']})
        save(folder/'fit_diagnostics.json',[{'valid':True}])
        save(folder/'prediction_commit.json',{'sha256':r.sha(folder/'predictions.rds'),'target':year})
        save(folder/'forecast_audit.json',{'returned_simulations':1000,'target_outcomes_accessed':False})
        score={'target':year,'seed':year*1000+1,'simulations':1000,
               'primary':{'pr_auc':.9,'brier':.01},'spending':{'rmse':.4,'n':151},
               'formation':{'pr_auc':.02},'dissolution':{'pr_auc':.03}}
        save(folder/'scores.json',score)
        for kind in ('past','targets'):
            p=root/f'data/{kind}/{year}.rds';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fake packet'+str(year).encode()+kind.encode())
        save(folder/'provenance.json',{'files':{f'data/past/{year}.rds':r.sha(root/f'data/past/{year}.rds'), **{name:r.sha(root/name) for name in ('R/empirical.R','R/forecast.R')}}})
        save(folder/'score_provenance.json',{'predictions':r.sha(folder/'predictions.rds'),
             'target':r.sha(root/f'data/targets/{year}.rds'),'scorer':r.sha(root/'R/score.R'),'PRROC':'1.3.1'})
    save(root/'results/evolution_manifest.json',manifest)


class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);fixture(self.root)
    def test_exact_eight_development_packets(self):
        p=r.inspect_inputs(self.root)
        self.assertTrue(p['ready']);self.assertEqual(len(p['packets']),8)
        self.assertFalse(any('2010' in name for name in p['packets']))
    def test_missing_all_packets_no_worker_or_output(self):
        shutil.rmtree(self.root/'data')
        p=r.inspect_inputs(self.root);self.assertEqual(len(p['missing_inputs']),8)
        output=self.root/'results/diagnostics/repeat'
        with patch.object(r.native,'run_r') as call:
            with self.assertRaises(FileNotFoundError):r.execute(output,root=self.root)
            call.assert_not_called()
        self.assertFalse(output.exists())
    def test_changed_packet_refused(self):
        (self.root/'data/past/2006.rds').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Input packet differs'):r.inspect_inputs(self.root)
    def test_changed_score_commitment_refused(self):
        (self.root/'results/cache/fixture-2006/predictions.rds').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'commitment changed'):r.inspect_inputs(self.root)
    def test_no_future_file_reads(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            self.assertNotIn('2010',path.name)
            self.assertNotIn('sources/original',str(path))
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):self.assertTrue(r.inspect_inputs(self.root)['ready'])
    def test_export_exact_packets_and_no_overwrite(self):
        out=self.root/'input.zip';value=r.export_inputs(out,self.root)
        with zipfile.ZipFile(out) as z:self.assertEqual(z.namelist(),r.packet_paths())
        self.assertEqual(value['sha256'],r.sha(out))
        with self.assertRaises(FileExistsError):r.export_inputs(out,self.root)
    def test_rejected_new_target_or_budget(self):
        path=self.root/'configs/forecast-repeatability-v1.json';p=r.read(path);p['targets'].append(2010);save(path,p)
        with self.assertRaises(ValueError):r.inspect_inputs(self.root)


class SummaryTests(unittest.TestCase):
    def rows(self):
        rows=[]
        for offset in r.OFFSETS:
            for year in r.YEARS:
                rows.append({'year':year,'offset':offset,'metrics':{k:(offset-100)*.001 for k in r.METRICS}})
        return rows
    def reference(self):return {str(y):{'metrics':{k:0 for k in r.METRICS}} for y in r.YEARS}
    def test_known_sample_sd_and_four_year_groups(self):
        result=r.summarize(self.rows(),self.reference())
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(result['complete_four_year_repetitions']),5)
        self.assertAlmostEqual(result['annual']['2006']['pr_auc']['sample_sd'],math.sqrt(2.5)*.001)
        self.assertAlmostEqual(result['four_year_mean_variability']['pr_auc']['sample_sd'],math.sqrt(2.5)*.001)
    def test_partial_not_fitness_or_generalization(self):
        result=r.summarize(self.rows()[:2],self.reference())
        self.assertEqual(result['status'],'partial');self.assertEqual(result['four_year_mean_variability'],{})
        self.assertNotIn('combined_score',result);self.assertNotIn('J1',result)
    def test_duplicate_and_nonfinite_refused(self):
        rows=self.rows()
        with self.assertRaises(ValueError):r.summarize(rows+[rows[0]],self.reference())
        with self.assertRaises(ValueError):r.distribution([1,float('nan')])
    def test_signed_same_model_difference_is_not_improvement(self):
        p=r.summarize(self.rows(),self.reference())['complete_four_year_repetitions'][0]
        self.assertAlmostEqual(p['same_model_signed_differences_from_published']['pr_auc'],.001)
        self.assertAlmostEqual(p['same_model_signed_differences_from_published']['brier'],-.001)


class WorkflowTests(unittest.TestCase):
    setUp = InputTests.setUp
    def worker(self,args,folder,stage,timeout):
        self.calls.append((args,stage))
        self.assertNotIn('2010',str(args));self.assertNotIn('finalist',str(args))
        settings=r.read(folder/'settings.json');seed=settings['forecast']['seed_override'];year=seed//1000
        if stage=='forecast':
            self.assertEqual(Path(args[0]).name,'forecast_repeatability.R')
            self.assertEqual((folder/'accepted_fit.rds').read_bytes(),b'synthetic fixture: not RDS')
            (folder/'predictions.rds').write_bytes(str(seed).encode())
            (folder/'simulations.rds').write_bytes(b'synthetic endpoint fixture')
            save(folder/'forecast_audit.json',{'seed':seed,'returned_simulations':1000,'target_outcomes_accessed':False})
            save(folder/'fixed_coefficient_audit.json',{k:True for k in ('simOnly','all_coefficients_fixed','coefficients_unchanged','published_forward_coefficients_verified')})
        else:
            self.assertTrue((folder/'prediction_commit.json').exists())
            scores=r.read(self.root/f'results/cache/fixture-{year}/scores.json')
            scores['seed']=seed;scores['primary']['pr_auc']+=(seed%1000-100)*.001
            save(folder/'scores.json',scores)
            shutil.copy2(self.root/f'results/cache/fixture-{year}/eligibility_mask.rds',folder/'eligibility_mask.rds')
    def test_finite_twenty_batches_and_resume_zero_calls(self):
        self.calls=[];output=self.root/'results/diagnostics/repeat'
        with patch.object(r,'scientific_execution',__import__('contextlib').nullcontext):
            self.assertEqual(r.execute(output,root=self.root,runner=self.worker),0)
            self.assertEqual(len(self.calls),40)
            self.assertEqual(r.execute(output,root=self.root,runner=self.worker),0)
            self.assertEqual(len(self.calls),40)
        self.assertFalse((self.root/'results/selection').exists())
        self.assertEqual(r.read(output/'summary.json')['completed_batches'],20)
    def test_one_batch_pause_then_resume(self):
        self.calls=[];output=self.root/'results/diagnostics/repeat'
        with patch.object(r,'scientific_execution',__import__('contextlib').nullcontext):
            self.assertEqual(r.execute(output,1,root=self.root,runner=self.worker),75)
            self.assertEqual(len(self.calls),2)
            self.assertEqual(r.execute(output,1,root=self.root,runner=self.worker),75)
            self.assertEqual(len(self.calls),4)
    def test_tampered_committed_forecast_never_regenerated(self):
        self.calls=[];output=self.root/'results/diagnostics/repeat'
        with patch.object(r,'scientific_execution',__import__('contextlib').nullcontext):
            r.execute(output,1,root=self.root,runner=self.worker)
            (output/'2006/101/predictions.rds').unlink()
            with self.assertRaises(FileNotFoundError):r.execute(output,root=self.root,runner=self.worker)
            self.assertEqual(len(self.calls),2)
    def test_failed_worker_stops_no_substitute_or_retry(self):
        output=self.root/'results/diagnostics/repeat'
        with patch.object(r,'scientific_execution',__import__('contextlib').nullcontext):
            with patch.object(r.native,'run_r',side_effect=RuntimeError('fixture failure')) as call:
                with self.assertRaises(RuntimeError):r.execute(output,root=self.root)
                self.assertEqual(call.call_count,1)
                with self.assertRaisesRegex(RuntimeError,'Incomplete started batch'):r.execute(output,root=self.root)
                self.assertEqual(call.call_count,1)
        self.assertFalse((output/'summary.json').exists())
    def test_mutated_fixed_fit_refused(self):
        output=self.root/'results/diagnostics/repeat';self.calls=[]
        def bad(*args):
            self.worker(*args)
            if args[2]=='forecast':(args[1]/'accepted_fit.rds').write_bytes(b'changed')
        with patch.object(r,'scientific_execution',__import__('contextlib').nullcontext):
            with self.assertRaisesRegex(ValueError,'Fit bytes changed'):r.execute(output,root=self.root,runner=bad)
        self.assertEqual(len(self.calls),1)


class CliTests(unittest.TestCase):
    def test_dry_run_needs_no_packets(self):
        completed=subprocess.run([sys.executable,str(r.ROOT/'scripts/forecast_repeatability.py'),'run'],text=True,capture_output=True)
        self.assertEqual(completed.returncode,0);self.assertIn('Dry run',completed.stdout)
    def test_r_guard_source_prohibits_refit(self):
        source=(r.ROOT/'R/forecast_repeatability.R').read_text()
        self.assertIn('scope$fit_model <- function(...) stop(',source)
        self.assertIn('RSiena::siena07(x, data=data, effects=effects',source)
        self.assertIn('all(effects$fix[effects$include])',source)
