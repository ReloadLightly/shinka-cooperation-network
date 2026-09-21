#!/usr/bin/env python3
"""Step 3C: nine new fixed-vector diagnostics, plus the preserved Step 3B pilot.
No estimator, forecast scorer or evolutionary controller is called.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import convergence_preflight as pre
from scripts import convergence_pilot as pilot

POLICY = 'configs/convergence-repeatability-v1.json'
PLAN_SHA = '0f0b987240b0880148791531eea7e1bd1484e60009c5836b0891369d5fa91214'
OUT = 'results/diagnostics/convergence-repeatability-v1'
NEW = [('attempt3', s) for s in range(2009302, 2009306)] + [('attempt4', s) for s in range(2009401, 2009406)]
REQUIRED = {'request.json','summary.json','guard-audit.json','raw-phase3.rds','native-diagnostic.rds',
            'moment-deviations.csv','moment-covariance.csv','parameter-diagnostics.csv','native.log','resources.txt','session-info.txt'}
IMPLEMENTATION = ('R/convergence_repeatability.R','scripts/convergence_repeatability.py',POLICY)


def plan(root=ROOT):
    if pre.sha(root/POLICY) != PLAN_SHA:
        raise ValueError('Frozen Step 3C plan changed')
    return pre.read(root/POLICY)


def inspect(root=ROOT, native=False):
    p = plan(root)
    # The existing pilot must remain complete and hash-verified, never rerun.
    pilot.verify_artifacts(root/p['pilot']['path'])
    if pre.sha(root/p['pilot']['path']/'summary.json') != p['pilot']['summary_sha256']:
        raise ValueError('Pilot reference changed')
    for name,h in p['original_implementation_sha256'].items():
        if pre.sha(root/name) != h:
            raise ValueError('Prior implementation changed: '+name)
    for meta in p['fits'].values():
        if pre.sha(root/meta['path']) != meta['sha256']:
            raise ValueError('Saved coefficient-vector file changed')
    return {'plan_sha256':PLAN_SHA,'original_inputs':pre.inspect(root,require_native=native),
            'fit_hashes':{k:v['sha256'] for k,v in p['fits'].items()},
            'implementation':{n:pre.sha(root/n) for n in IMPLEMENTATION},
            'pilot_commitment':pre.sha(root/p['pilot']['path']/'commitment.json')}


def validate_summary(s, label, seed):
    if (label,seed) not in NEW:
        raise ValueError('Undeclared cell or attempted pilot replay')
    expected={'status':'completed','stage':'3C','fit':label,'seed':seed,'draws':3000,
              'replications':1,'nsub':0,'simOnly':False,'parameters':58,'actors':161,
              'training_years':list(range(1990,2009)),'coefficients_identical':True,
              'original_fixed_flags_preserved':True,'historical_attempt_accepted':label=='attempt4',
              'new_refits':0,'new_forecasts':0,'target_packets_read':0,'raw_archives_read':0,'step4_started':False}
    for k,v in expected.items():
        if s.get(k)!=v or type(s.get(k)) is not type(v):
            raise ValueError('Wrong cell scope: '+k)
    g=s['guard']
    for k,v in {'phase3_entries':1,'simulator_entries':3000,'simulator_exits':3000,
                'forbidden_entries':0,'potential_nr_calls':1,'postprocessing_entries':1,
                'checked_every_simulator_call':True,'seed':seed,'nsub':0,'n3':3000,'simOnly':False}.items():
        if g.get(k)!=v or type(g.get(k)) is not type(v):
            raise ValueError('Wrong guard result: '+k)
    for key,n in [('fresh_first_1000',1000),('fresh_full_3000',3000)]:
        d=s[key]
        if d['draws']!=n:
            raise ValueError('Wrong draw count')
        for metric,threshold,flag in [('maximum_absolute_t',0.1,'individual_pass'),('overall',0.25,'overall_pass')]:
            v=d[metric]
            if type(v) not in (float,int) or not math.isfinite(v) or v<0 or d[flag] is not (v<threshold):
                raise ValueError('Invalid diagnostic or changed cutoff')
    d=s['native_diagnostics']
    if type(d.get('valid')) is not bool or not d['phase3_complete'] or d['phase3_iterations']!=3000:
        raise ValueError('Native diagnostic incomplete')
    for a,b in [('maximum_absolute_t_ratio','maximum_absolute_t'),('overall_maximum_convergence','overall')]:
        if not math.isclose(d[a],s['fresh_full_3000'][b],abs_tol=1e-12,rel_tol=0):
            raise ValueError('Native/reconstructed discrepancy')
    if d['valid'] and not (s['fresh_full_3000']['individual_pass'] and s['fresh_full_3000']['overall_pass']):
        raise ValueError('False native pass')


def verify_cell(folder,label,seed):
    c=pre.read(folder/'commitment.json')
    if c.get('stage')!='3C' or c.get('plan_sha256')!=PLAN_SHA or not REQUIRED.issubset(c['artifacts']):
        raise ValueError('Incomplete/wrong study commitment')
    for name,h in c['artifacts'].items():
        if Path(name).name!=name or pre.sha(folder/name)!=h:
            raise ValueError('Changed cell artifact: '+name)
    req=pre.read(folder/'request.json')
    if req['fit']!=label or req['seed']!=seed or req['plan_sha256']!=PLAN_SHA:
        raise ValueError('Cell request changed')
    s=pre.read(folder/'summary.json');validate_summary(s,label,seed)
    return s


def run_cell(label,seed,root=ROOT,runner=pilot.native_process,preflight=False):
    if (label,seed) not in NEW:
        raise ValueError('Undeclared cell; the original pilot cannot be replayed')
    if int(os.environ.get('GITHUB_RUN_ATTEMPT','1'))!=1:
        raise ValueError('Workflow reruns are not new scientific replications')
    folder=root/OUT/('preflight-'+label if preflight else label)/str(seed)
    if folder.exists():
        raise FileExistsError('Evidence already exists; inspect rather than overwrite/retry')
    inputs=inspect(root,native=True)
    folder.mkdir(parents=True)
    pre.write_new(folder/'request.json',{**inputs,'fit':label,'seed':seed,
        'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'mode':'preflight' if preflight else 'simulate'})
    packet=folder/'training-packet.rds'
    packet.write_bytes(pre.training_bytes(root/pre.BUNDLE))
    try:
        with (folder/'native.log').open('x') as log:
            runner(['/usr/bin/time','-v','-o',str(folder/'resources.txt'),str(root/'environment/run-r'),
                    str(root/'R/convergence_repeatability.R'),
                    '--preflight-only' if preflight else '--execute-cell',str(root),str(folder),label,str(seed)],
                   cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300 if preflight else 3600)
        if pre.sha(packet)!=pre.PACKET_SHA or inspect(root,native=True)!=inputs:
            raise ValueError('Original inputs changed during native operation')
        if preflight:
            s=pre.read(folder/'preflight.json')
            if s['status']!='verified_no_simulation' or s['initialization']['simulator_entered'] is not False:
                raise ValueError('Preflight entered simulation')
        else:
            s=pre.read(folder/'summary.json');validate_summary(s,label,seed)
    except Exception as e:
        pre.write_new(folder/'failure.json',{'status':'stopped','fit':label,'seed':seed,
            'error_type':type(e).__name__,'message':str(e),'automatic_retry':False})
        raise
    finally:
        packet.unlink(missing_ok=True)
    artifacts={p.name:pre.sha(p) for p in sorted(folder.iterdir()) if p.is_file()}
    pre.write_new(folder/'commitment.json',{'stage':'3C-preflight' if preflight else '3C',
        'plan_sha256':PLAN_SHA,'artifacts':artifacts})
    if not preflight:
        verify_cell(folder,label,seed)
    return s


def stats(values):
    return {'n':len(values),'mean':statistics.mean(values) if values else None,
            'sample_sd':statistics.stdev(values) if len(values)>1 else None,
            'minimum':min(values) if values else None,'maximum':max(values) if values else None}


def describe(rows):
    result={'n':len(rows)}
    for prefix in ('prefix1000','full3000'):
        result[prefix]={m:stats([r[prefix+'_'+m] for r in rows]) for m in ('maximum_t','overall')}
        result[prefix]['joint_threshold_passes']=sum(r[prefix+'_pass'] for r in rows)
    result['full_native_valid']=sum(r['native_valid'] for r in rows)
    result['prefix_fail_full_pass']=sum(not r['prefix1000_pass'] and r['full3000_pass'] for r in rows)
    result['prefix_pass_full_fail']=sum(r['prefix1000_pass'] and not r['full3000_pass'] for r in rows)
    return result


def row(s,label,reused):
    r={'fit':label,'seed':s['seed'],'reused_pilot':reused,'native_valid':s['native_diagnostics']['valid'],
       'warnings':len(s['guard']['warnings']), 'elapsed_seconds':s['guard']['elapsed_seconds']}
    for prefix,key in [('prefix1000','fresh_first_1000'),('full3000','fresh_full_3000')]:
        d=s[key];r.update({prefix+'_maximum_t':d['maximum_absolute_t'],prefix+'_overall':d['overall'],
                         prefix+'_pass':d['individual_pass'] and d['overall_pass']})
    return r


def summarize(rows,failures):
    keys=[(r['fit'],r['seed']) for r in rows]
    if len(set(keys))!=len(keys) or set(keys)-set(NEW+[('attempt3',2009301)]):
        raise ValueError('Duplicate/undeclared result')
    a=[r for r in rows if r['fit']=='attempt3'];b=[r for r in rows if r['fit']=='attempt4']
    fresh=[r for r in a if not r['reused_pilot']]
    complete=len(rows)==10 and not failures
    return {'stage':'3C','status':'complete' if complete else 'partial','plan_sha256':PLAN_SHA,
       'total_cells':len(rows),'new_completed_cells':len(rows)-sum(r['reused_pilot'] for r in rows),
       'reused_pilot_cells':sum(r['reused_pilot'] for r in rows),'planned_new_cells':9,'new_refits':0,
       'new_forecasts':0,'step4_started':False,'failures':failures,'cells':rows,
       'attempt3_new_only':describe(fresh),'attempt3_including_seen_pilot':describe(a),'attempt4_new_only':describe(b),
       'new_guarded_seconds':sum(r['elapsed_seconds'] for r in rows if not r['reused_pilot']),
       'interpretation':'Conditional diagnostic repeatability for two fixed historical coefficient vectors. Five is a small sample; the seen pilot is excluded from attempt3_new_only. Prefix/full samples are nested. Counts are descriptive, not a validated pass probability or proof of production-policy suitability. No fitting variation, prediction quality, stronger identification or evolutionary improvement was measured.'}


def aggregate(root=ROOT):
    p=plan(root);pilot.verify_artifacts(root/p['pilot']['path'])
    if pre.sha(root/p['pilot']['path']/'summary.json')!=p['pilot']['summary_sha256']:
        raise ValueError('Pilot changed')
    rows=[row(pre.read(root/p['pilot']['path']/'summary.json'),'attempt3',True)];failures=[]
    for label,seed in NEW:
        folder=root/OUT/label/str(seed)
        try:
            s=verify_cell(folder,label,seed);rows.append(row(s,label,False))
        except (OSError,ValueError,KeyError) as e:
            failures.append({'fit':label,'seed':seed,'error':str(e)})
    summary=summarize(rows,failures)
    out=root/OUT;out.mkdir(parents=True,exist_ok=True)
    pre.write_new(out/'summary.json',summary)
    with (out/'cell_metrics.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    text=['# Step 3C: fixed-coefficient convergence repeatability','',f"Status: **{summary['status']}**. {summary['new_completed_cells']}/9 new cells, plus the verified prior pilot. Zero refits or forecasts.",'',
      '| Vector | Seed | Origin | max t: first 1000 | Overall: first 1000 | max t: all 3000 | Overall: all 3000 | Native valid |',
      '|---|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        text.append(f"| {r['fit']} | {r['seed']} | {'reused pilot' if r['reused_pilot'] else 'new'} | {r['prefix1000_maximum_t']:.9f} | {r['prefix1000_overall']:.9f} | {r['full3000_maximum_t']:.9f} | {r['full3000_overall']:.9f} | {r['native_valid']} |")
    text+=['','## Descriptive results','', '| Group | n | Overall first 1000: mean (SD) | Overall full 3000: mean (SD) | Joint cutoff pass counts: first/full |', '|---|---:|---:|---:|---:|']
    for k in ['attempt3_new_only','attempt3_including_seen_pilot','attempt4_new_only']:
        d=summary[k]
        if not d['n']: continue
        def fmt(v):return 'unavailable' if v is None else f'{v:.9f}'
        a=d['prefix1000']['overall'];b=d['full3000']['overall']
        text.append(f"| {k} | {d['n']} | {fmt(a['mean'])} ({fmt(a['sample_sd'])}) | {fmt(b['mean'])} ({fmt(b['sample_sd'])}) | {d['prefix1000']['joint_threshold_passes']}/{d['n']} vs {d['full3000']['joint_threshold_passes']}/{d['n']} |")
    text+=['',summary['interpretation'],'', 'All thresholds are unchanged: individual <0.1, overall <0.25. A threshold pass is distinct from full native validity. Historical accepted/rejected records remain unchanged.', '',
      'See `cell_metrics.csv`, `summary.json`, each cell directory and `configs/convergence-repeatability-v1.json`. Every completed cell retains raw moment/score arrays and compact native covariance/derivative results, plus coefficient guards and source commitments. The prior 3B pilot is referenced, not duplicated or rerun.']
    if failures:text+=['','## Incomplete cells',json.dumps(failures,indent=2)]
    (out/'REPORT.md').write_text('\n'.join(text)+'\n')
    pre.write_new(out/'study-commitment.json',{'plan_sha256':PLAN_SHA,
        'artifacts':{str(f.relative_to(out)):pre.sha(f) for f in sorted(out.rglob('*')) if f.is_file()}})
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['check','preflight','run','aggregate','verify-cell'])
    p.add_argument('--fit',choices=['attempt3','attempt4']);p.add_argument('--seed',type=int)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.action in ('run','preflight') and not a.execute:
        print('Dry request: no input reads or simulations. Add --execute for the declared cell.');return 0
    try:
        if a.action=='check':r=inspect()
        elif a.action=='aggregate':r=aggregate()
        elif a.action=='verify-cell':r=verify_cell(ROOT/OUT/a.fit/str(a.seed),a.fit,a.seed)
        else:r=run_cell(a.fit,a.seed,preflight=a.action=='preflight')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as e:
        print('Step 3C stopped: '+str(e),file=sys.stderr);return 1
    print(json.dumps(r,indent=2,allow_nan=False));return 0

if __name__=='__main__':raise SystemExit(main())
