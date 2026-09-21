#!/usr/bin/env python3
"""Fixed Step 4 mechanism comparison; explicit run, no evolutionary search.

New policy receipts are not accepted by historical forecast entry points.
This module binds the planned receipt-aware wrapper, source files, seeds and
compatible optimization history. Scoring is a separate, post-commit process.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, math, os, statistics, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import precision_fit as pf
from scripts.network_specification_v2 import validate_spec, read_program
from scripts.scientific_contract import immutable_json, require_search_open, digest
from scripts.convergence_pilot import native_process
VERSION='step4-closure-comparison-v1'
PLAN='configs/step4-comparison-v1.json'
YEARS=(2006,2007,2008,2009)
MODELS=('reference','gwesp69')
BASE='2a7a8f5000dacfcc9e56f865e2d720e1b446ee53'
RESULTS='results/step4-closure-comparison-v1'
TARGET_HASHES={2006:'a2b9edb5f8c98a6b0b937dce5b8be9345e64cb2f225506115974a247fc3e434a',2007:'d0d1c97414d39550096e69fcd36c5e14dc5e28aea1fca0b34f6de6ed76d0c936',2008:'973e54b1b7fd764889584cf1a25e429a6ebd3de7fa83a91684464c2d1b2850d2',2009:'a7bd4d561517e93c318e4f71dc7d6fbd3ddda827a55e214431f4b47837865c2c'}
EXTRA=('scripts/step4_compare.py','R/step4_compare.R','R/test_step4_compare.R',PLAN,'R/score.R','candidates/step4_reference.py','candidates/step4_gwesp69.py')
METRICS=('pr_auc','brier','spending_rmse','formation_pr_auc','dissolution_pr_auc')
DIRECTION={'pr_auc':1,'brier':-1,'spending_rmse':-1,'formation_pr_auc':1,'dissolution_pr_auc':1}

def read(path): return json.loads(Path(path).read_text())
def sha(path): return pf.sha(Path(path))
def seed(year,model,batch):
    if type(year) is not int or year not in YEARS or model not in MODELS or type(batch) is not int or batch not in range(1,6):
        raise ValueError('Undeclared forecast cell')
    return 61000000+100*year+10*MODELS.index(model)+batch

def plan(root=ROOT):
    p=read(root/PLAN)
    if p['version']!=VERSION or p['evidence_base_commit']!=BASE or p['development_years']!=list(YEARS) or p['reserved_year_access'] is not False:
        raise ValueError('Changed comparison identity or temporal scope')
    want={'reference':{'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':1},{'effect':'transTriads','parameter':0}]},'gwesp69':{'schema_version':2,'network_effects':[{'effect':'degPlus','parameter':1},{'effect':'gwesp','parameter':69}]}}
    if p['models']!=want: raise ValueError('Undeclared model or decay search')
    for m in MODELS:
        decoded,_=read_program(root/f'candidates/step4_{m}.py')
        if decoded!=validate_spec(want[m]): raise ValueError('Candidate differs from frozen specification')
    f=p['forecast']
    if (f['batches_per_model_year'],f['endpoints_per_batch'],f['point_estimate_endpoints'],f['max_new_batches'],f['seed_base'])!=(5,1000,5000,40,61000000):
        raise ValueError('Changed forecast budget')
    if p['convergence_policy']!=pf.VERSION or p['fitting_seed_repetitions']!=1 or not p['no_shinka_search'] or not p['no_automatic_winner']:
        raise ValueError('Changed experiment purpose')
    return p

def git_bound(root,path):
    wanted=subprocess.check_output(['git','rev-parse',f'{BASE}:{path}'],cwd=root,text=True).strip()
    actual=subprocess.check_output(['git','hash-object','--',path],cwd=root,text=True).strip()
    if wanted!=actual: raise ValueError(f'Original committed input changed: {path}')
    return sha(root/path)

def import_history(root,spec,year,p):
    # Eligibility depends on exact specification/data/settings identity, not role.
    if validate_spec(spec)!=validate_spec(p['models']['reference']):
        return {'source_commit':BASE,'attempts':{},'reason':'No predeclared exact-specification history'}
    folder=p['baseline_cache_folders'][str(year)]
    provpath=f'{folder}/provenance.json'; prov=read(root/provpath)
    hashes={provpath:git_bound(root,provpath)}
    if (prov['target']!=year or prov['training']!=[1990,year-1] or validate_spec(prov['specification'])!=spec or
        prov['files'][f'data/past/{year}.rds']!=pf.PACKET_HASHES[year] or prov['settings']!=read(root/'configs/evaluator-v2.json')):
        raise ValueError('Archived data, settings or specification mismatch')
    for name in ('R/empirical.R','environment/versions.json','environment/conda-linux-64.explicit.txt'):
        if sha(root/name)!=prov['files'][name]: raise ValueError('Archived fitting implementation mismatch')
    attempts={}; gap=False
    for i in range(1,5):
        name=f'{folder}/fit-attempt-{i}.rds'
        exists=subprocess.run(['git','cat-file','-e',f'{BASE}:{name}'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
        if not exists: gap=True; continue
        if gap: raise ValueError('Noncontiguous archived optimization history')
        h=git_bound(root,name)
        attempts[str(i)]={'path':name,'sha256':h,'previous_path':f'{folder}/fit-attempt-{i-1}.rds' if i>1 else None}
    if not attempts: raise ValueError('Missing declared historical optimization inputs')
    return {'source_commit':BASE,'provenance_sha256':hashes,'attempts':attempts,'historical_acceptance_imported':False}

def make_request(root,model,year):
    if model not in MODELS or type(year) is not int or year not in YEARS: raise ValueError('Undeclared cell')
    p=plan(root);spec=validate_spec(p['models'][model]);r=pf.request(root,spec,year)
    r.update(version=VERSION,estimator_version=pf.VERSION,model=model,comparison=p,
        import_history=import_history(root,spec,year,p),historical_imports='optimization-only audited replay',
        source_sha256={n:sha(root/n) for n in dict.fromkeys((*pf.SOURCE_FILES,*EXTRA))},
        forecast_seeds=[seed(year,model,b) for b in range(1,6)])
    return r

def commit(folder,name,required=()):
    files={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name not in ('run.lock',name)}
    if not set(required).issubset(files): raise ValueError('Required evidence missing')
    immutable_json(folder/name,{'version':VERSION,'files':files})

def verify(folder,name,required=()):
    c=read(folder/name)
    if c.get('version')!=VERSION or not set(required).issubset(c['files']): raise ValueError('Wrong or incomplete commitment')
    for n,h in c['files'].items():
        path=(folder/n).resolve();path.relative_to(folder.resolve())
        if sha(path)!=h: raise ValueError(f'Changed evidence: {n}')
    return c

def verify_fit(cell):
    verify(cell/'fit','commitment.json',('accepted_fit.rds','accepted.json','request.json'))
    req=read(cell/'request.json'); proxy=dict(req,version=pf.VERSION)
    pf.validate_acceptance(read(cell/'fit/accepted.json'),proxy)

def target_bytes(root,year):
    if year not in YEARS: raise ValueError('Reserved target forbidden')
    member=f'data/targets/{year}.rds'
    with zipfile.ZipFile(root/pf.BUNDLE) as z:
        expected={f'data/{k}/{y}.rds' for k in ('past','targets') for y in YEARS}
        if len(z.namelist())!=8 or set(z.namelist())!=expected: raise ValueError('Unsafe packet bundle')
        data=z.read(member)
    if hashlib.sha256(data).hexdigest()!=TARGET_HASHES[year]: raise ValueError('Target packet hash mismatch')
    return data

def invoke(root,output,args,timeout):
    deadline=os.environ.get('STEP4_CELL_DEADLINE')
    if deadline:
        timeout=min(timeout,max(0,int(float(deadline)-time.time())))
    if timeout<=0: raise TimeoutError('Declared total cell compute window expired; no new operation admitted')
    output.mkdir(parents=True,exist_ok=True)
    if (output/'started.json').exists(): raise RuntimeError(f'Incomplete operation preserved, no automatic repeat: {output}')
    immutable_json(output/'started.json',{'args':args,'timeout_seconds':timeout,'version':VERSION})
    command=['/usr/bin/time','-v','-o',str(output/'resources.txt'),str(root/'environment/run-r'),*args]
    with (output/'native.log').open('x') as log:
        native_process(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout)

def run_cell(model,year,root=ROOT):
    require_search_open(root);req=make_request(root,model,year);past=pf.packet_bytes(root,year)
    cell=root/RESULTS/model/str(year);cell.mkdir(parents=True,exist_ok=True)
    with (cell/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        immutable_json(cell/'request.json',req);immutable_json(cell/'specification.json',req['specification'])
        if (cell/'cell-commitment.json').exists():return verify_cell(cell)
        os.environ['STEP4_CELL_DEADLINE']=str(time.time()+req['comparison']['budget']['cell_native_seconds'])
        # An incomplete native operation may not be retried automatically.
        try:
            with tempfile.TemporaryDirectory(prefix='step4-past-') as tmp:
                packet=Path(tmp)/'past.rds';packet.write_bytes(past)
                fit=cell/'fit'
                if not (fit/'commitment.json').exists():
                    invoke(root,cell/'fit-invocation',['R/step4_compare.R','fit',str(cell),str(packet),model,str(year)],req['comparison']['budget']['cell_native_seconds'])
                    commit(fit,'commitment.json',('accepted_fit.rds','accepted.json','request.json'))
                verify_fit(cell)
                for b in range(1,6):
                    f=cell/'forecasts'/str(b)
                    if (f/'prediction-commitment.json').exists(): verify(f,'prediction-commitment.json',('predictions.rds','simulations.rds','receipt-audit.json'))
                    else:
                        invoke(root,f,['R/step4_compare.R','forecast',str(cell),str(packet),model,str(year),str(b)],1800)
                        a=read(f/'receipt-audit.json')
                        if a['seed']!=seed(year,model,b) or a['authoritative_n3']!=read(fit/'accepted.json')['authoritative_n3'] or a['target_reads']!=0:
                            raise ValueError('Forecast receipt audit differs')
                        commit(f,'prediction-commitment.json',('predictions.rds','simulations.rds','receipt-audit.json'))
                pooled=cell/'pooled'
                if not (pooled/'prediction-commitment.json').exists():
                    invoke(root,cell/'pool-invocation',['R/step4_compare.R','pool',str(cell)],900)
                    commit(pooled,'prediction-commitment.json',('predictions.rds',*[f'delete-{b}.rds' for b in range(1,6)]))
                verify(pooled,'prediction-commitment.json')
            # Every probability file is committed before the target is opened.
            for b in range(1,6):verify(cell/'forecasts'/str(b),'prediction-commitment.json')
            verify(cell/'pooled','prediction-commitment.json')
            with tempfile.TemporaryDirectory(prefix='step4-target-') as tmp:
                target=Path(tmp)/'target.rds';target.write_bytes(target_bytes(root,year))
                if not (cell/'scores/comparison-metrics.json').exists():
                    invoke(root,cell/'score-invocation',['R/step4_compare.R','score',str(cell),str(target)],1800)
            if req!=make_request(root,model,year): raise ValueError('Scientific inputs changed during cell execution')
            immutable_json(cell/'execution.json',{'status':'complete','model':model,'year':year,'new_forecast_batches':5,'endpoints':5000,'reserved_outcomes':0,'step5_started':False})
            commit(cell,'cell-commitment.json',('scores/comparison-metrics.json','execution.json','request.json'))
            return verify_cell(cell)
        except Exception as e:
            immutable_json(cell/'failure.json',{'error':type(e).__name__,'message':str(e),'automatic_retry':False,'fitness':None})
            raise

def verify_cell(cell):
    verify(cell,'cell-commitment.json',('scores/comparison-metrics.json','request.json','execution.json'))
    verify_fit(cell);r=read(cell/'request.json');s=read(cell/'scores/comparison-metrics.json')
    if s['status']!='complete' or s['primary_endpoints']!=5000 or len(s['batches'])!=5 or len(s['delete_one_batch'])!=5:
        raise ValueError('Incomplete replication set')
    return {'model':r['model'],'year':r['target'],'metrics':s,'accepted':read(cell/'fit/accepted.json')}

def finite(v):
    if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('Nonfinite comparison value')
    return float(v)

def compare(rows):
    lookup={}
    for r in rows:
        key=(r['model'],r['year'])
        if key in lookup or key[0] not in MODELS or key[1] not in YEARS:raise ValueError('Duplicate or undeclared cell')
        lookup[key]=r
    missing=[f'{m}/{y}' for m in MODELS for y in YEARS if (m,y) not in lookup]
    if missing:return {'version':VERSION,'status':'incomplete','missing_cells':missing,'four_year_comparison':None}
    for y in YEARS:
        a,b=(lookup[(m,y)]['metrics'] for m in MODELS)
        if a['eligibility_sha256']!=b['eligibility_sha256'] or a['spending_countries']!=b['spending_countries']:
            raise ValueError('Models use different evaluation masks')
    metrics={}
    for metric in METRICS:
        direction=DIRECTION[metric]
        def delta(year,field,index=None):
            vals=[]
            for model in MODELS:
                block=lookup[(model,year)]['metrics'][field]
                if index is not None:block=block[index]
                vals.append(finite(block[metric]))
            return direction*(vals[1]-vals[0])
        annual={str(y):delta(y,'pooled') for y in YEARS}
        point=statistics.mean(annual.values())
        deletes=[statistics.mean(delta(y,'delete_one_batch',i) for y in YEARS) for i in range(5)]
        center=statistics.mean(deletes)
        jkse=math.sqrt(4/5*sum((v-center)**2 for v in deletes))
        batches=[statistics.mean(delta(y,'batches',i) for y in YEARS) for i in range(5)]
        metrics[metric]={'pooled_5000_point':point,'annual_pooled_differences':annual,
            'delete_one_batch_four_year_points':deletes,'approximate_block_jackknife_se':jkse,
            'approximate_mc_interval_t4':[point-2.7764451051977987*jkse,point+2.7764451051977987*jkse],
            'batch_1000_contrasts':batches,'batch_1000_mean':statistics.mean(batches),
            'batch_1000_sample_sd':statistics.stdev(batches),'positive_means':'candidate better'}
    return {'version':VERSION,'status':'complete','complete_model_year_cells':8,'forecast_batches':40,
        'metrics':metrics,'automatic_winner':False,'uncertainty_scope':'Conditional on eight selected fitted vectors; approximate 5-block jackknife for pooled metrics, not fitting, generalization or causal uncertainty.',
        'shinka_result':False,'step5_started':False}

def report(root=ROOT):
    rows=[];failures={}
    for m in MODELS:
        for y in YEARS:
            folder=root/RESULTS/m/str(y)
            if (folder/'cell-commitment.json').exists():rows.append(verify_cell(folder))
            elif (folder/'failure.json').exists():failures[f'{m}/{y}']=read(folder/'failure.json')
    s=compare(rows);s['failures']=failures
    out=root/RESULTS;out.mkdir(parents=True,exist_ok=True)
    immutable_json(out/'summary.json',s)
    text=['# Step 4: one closure-specification comparison','',f"Status: **{s['status']}**.",'',
        'Reference: degPlus(1) + transTriads(0). Candidate: degPlus(1) + gwesp(69).',
        'All original empirical controls and spending-equation structure retained; coefficients jointly estimated.',
        'No Shinka proposals, decay search, reserved-year scores, or fit-seed replications.','']
    if s['status']=='complete':
        text+=['| Metric (positive = candidate better) | Pooled 5,000 point | Approx. conditional MC interval |','|---|---:|---|']
        for m,d in s['metrics'].items():text.append(f"| {m} | {d['pooled_5000_point']:.9f} | [{d['approximate_mc_interval_t4'][0]:.9f}, {d['approximate_mc_interval_t4'][1]:.9f}] |")
        text+=['','The interval is a five-block jackknife approximation with t(4) scaling. It is fragile for PR-AUC ties and does not include fitting or historical sampling uncertainty. The independently repeated 1,000-endpoint contrasts are retained separately, not mistaken for pooled-endpoint scores.']
    else:text+=['No complete four-year comparison is reported. Missing/failed cells remain explicit in summary.json.']
    text+=['','This is a development comparison motivated in part by already inspected 2007 forecast misfit, not untouched confirmatory evidence. A favorable result does not prove a causal mechanism or a Shinka advantage; an unfavorable result does not invalidate the entire search grammar.']
    (out/'REPORT.md').write_text('\n'.join(text)+'\n');return s

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','cell','report'))
    p.add_argument('--model',choices=MODELS);p.add_argument('--year',type=int,choices=YEARS);p.add_argument('--execute',action='store_true');a=p.parse_args(argv)
    if a.command=='cell' and (a.model is None or a.year is None):p.error('cell requires --model and --year')
    if a.command=='cell' and not a.execute:print('Dry run: no fits, forecasts or outcomes accessed.');return 0
    try:
        if a.command=='check':
            result={'plan':plan(),'requests':[make_request(ROOT,m,y) for m in MODELS for y in YEARS]}
        elif a.command=='cell':result=run_cell(a.model,a.year)
        else:result=report()
    except Exception as e:print(f'Step 4 stopped: {e}',file=sys.stderr);return 1
    print(json.dumps(result,indent=2,allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
