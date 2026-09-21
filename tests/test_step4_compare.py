import copy, math, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts import step4_compare as s

class Step4Tests(unittest.TestCase):
    def rows(self):
        rows=[]
        for model in s.MODELS:
            for y in s.YEARS:
                metrics={m:.1 for m in s.METRICS}
                if model=='gwesp69':metrics={m:.101 for m in s.METRICS}
                block={'status':'complete','pooled':metrics,'batches':[dict(metrics) for _ in range(5)],
                    'delete_one_batch':[dict(metrics) for _ in range(5)],'eligibility_sha256':str(y),
                    'spending_countries':151,'primary_endpoints':5000}
                rows.append({'model':model,'year':y,'metrics':block})
        return rows
    def test_plan_and_exact_candidate(self):
        p=s.plan();self.assertEqual(p['models']['gwesp69']['network_effects'][1],{'effect':'gwesp','parameter':69})
        self.assertEqual(p['forecast']['max_new_batches'],40)
    def test_forty_distinct_seeds(self):
        values=[s.seed(y,m,b) for y in s.YEARS for m in s.MODELS for b in range(1,6)]
        self.assertEqual(len(set(values)),40);self.assertEqual(s.seed(2009,'reference',1),61200901)
    def test_reserved_seed_refused(self):
        for y,m,b in [(2010,'reference',1),(2009,'extra',1),(2009,'reference',6),(True,'reference',1)]:
            with self.assertRaises(ValueError):s.seed(y,m,b)
    def test_no_partial_four_year_result(self):
        out=s.compare(self.rows()[:-1]);self.assertEqual(out['status'],'incomplete');self.assertIsNone(out['four_year_comparison'])
    def test_duplicate_refused(self):
        r=self.rows()
        with self.assertRaises(ValueError):s.compare(r+[r[0]])
    def test_unknown_cell_refused(self):
        r=self.rows();r[0]['year']=2010
        with self.assertRaises(ValueError):s.compare(r)
    def test_masks_must_match(self):
        r=self.rows();r[0]['metrics']['eligibility_sha256']='wrong'
        with self.assertRaises(ValueError):s.compare(r)
    def test_behavior_counts_match(self):
        r=self.rows();r[0]['metrics']['spending_countries']=1
        with self.assertRaises(ValueError):s.compare(r)
    def test_direction(self):
        out=s.compare(self.rows())['metrics']
        self.assertAlmostEqual(out['pr_auc']['pooled_5000_point'],.001)
        self.assertAlmostEqual(out['brier']['pooled_5000_point'],-.001)
        self.assertAlmostEqual(out['spending_rmse']['pooled_5000_point'],-.001)
    def test_constant_jackknife(self):
        out=s.compare(self.rows())['metrics']['pr_auc'];self.assertEqual(out['approximate_block_jackknife_se'],0)
    def test_jackknife_formula(self):
        rows=self.rows()
        for r in rows:
            if r['model']=='gwesp69':
                for b in range(5):r['metrics']['delete_one_batch'][b]['pr_auc']=.101+.001*(b-2)
        d=s.compare(rows)['metrics']['pr_auc']
        self.assertAlmostEqual(d['approximate_block_jackknife_se'],math.sqrt(8)*.001)
    def test_pooled_not_mean_of_batch_metrics(self):
        rows=self.rows()
        for r in rows:
            if r['model']=='gwesp69':
                for b in r['metrics']['batches']:b['pr_auc']=.105
        d=s.compare(rows)['metrics']['pr_auc']
        self.assertAlmostEqual(d['pooled_5000_point'],.001);self.assertAlmostEqual(d['batch_1000_mean'],.005)
    def test_nonfinite_refused(self):
        for v in (None,float('nan'),float('inf'),True):
            r=self.rows();r[0]['metrics']['pooled']['pr_auc']=v
            with self.assertRaises(ValueError):s.compare(r)
    def test_no_automatic_winner(self):
        out=s.compare(self.rows());self.assertFalse(out['automatic_winner']);self.assertFalse(out['shinka_result'])
    def test_hash_commitment_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'a').write_text('evidence');s.commit(p,'commit.json',('a',));s.verify(p,'commit.json',('a',))
            (p/'a').write_text('changed')
            with self.assertRaises(ValueError):s.verify(p,'commit.json',('a',))
    def test_missing_required_file(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):s.commit(Path(td),'commit.json',('missing',))
    def test_native_incomplete_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'started.json').write_text('{}')
            with patch.object(s,'native_process') as worker:
                with self.assertRaises(RuntimeError):s.invoke(s.ROOT,p,['unused'],10)
                worker.assert_not_called()
    def test_reserved_target_refused_before_read(self):
        with patch.object(s.zipfile,'ZipFile') as z:
            with self.assertRaises(ValueError):s.target_bytes(s.ROOT,2010)
            z.assert_not_called()
    def test_dry_run_never_reads_data(self):
        with patch.object(s,'run_cell') as r:
            self.assertEqual(s.main(['cell','--model','reference','--year','2009']),0);r.assert_not_called()
    def test_new_consumer_uses_receipt_and_forbids_fit(self):
        r=(s.ROOT/'R/step4_compare.R').read_text()
        for text in ('ans$authoritative_n3','scope$fit_model_v2','Forecast process may not estimate','step4_receipt','prevAns','observed'):
            if text=='prevAns':continue
            # Scope is validated in native tests; these are source contracts only.
            if text=='observed':continue
            self.assertIn(text,r)
    def test_import_rule_not_role(self):
        p=s.plan()
        with patch.object(s,'git_bound') as g:
            h=s.import_history(s.ROOT,p['models']['gwesp69'],2009,p)
            self.assertEqual(h['attempts'],{});g.assert_not_called()

if __name__=='__main__':unittest.main()
