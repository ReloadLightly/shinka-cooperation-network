"""Training-only descriptive comparison of the three saved 2009 fits.

No fitting, simulation, target-outcome access or independence-based inference.
Changes in SE units describe displacement, not a test statistic: these fits are
successive continuations from the same training data and are dependent.
"""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'results/cache/ed64802bacb0fbdd1ae1bc45746e29795f85bc0f92ceedf427660ea0c40efc99'
OUT = Path(__file__).resolve().parent
snapshot = OUT / 'saved_attempts_1_to_3_diagnostics.json'
if not snapshot.exists():
    snapshot.write_bytes((SOURCE / 'fit_diagnostics.json').read_bytes())
fits = json.loads(snapshot.read_text())[:3]
with (SOURCE / 'training_effects.csv').open(newline='') as stream:
    effects = list(csv.DictReader(stream))
if len(fits) != 3 or any(len(fit['estimates']) != len(effects) for fit in fits):
    raise RuntimeError('Expected three saved fits with the exported native effect order.')
rows = []
for i, effect in enumerate(effects):
    row = {key: effect[key] for key in ('name','effectName','shortName','interaction1','interaction2','type','period','parm','effectNumber')}
    for fit in fits:
        attempt = fit['attempt']
        row[f'estimate_{attempt}'] = fit['estimates'][i]
        row[f'se_{attempt}'] = fit['standard_errors'][i]
        row[f't_ratio_{attempt}'] = fit['t_ratios'][i]
    for a,b in ((1,2),(2,3),(1,3)):
        change = row[f'estimate_{b}'] - row[f'estimate_{a}']
        row[f'change_{a}_{b}'] = change
        row[f'change_{a}_{b}_in_previous_se'] = change / row[f'se_{a}']
        row[f'change_{a}_{b}_in_latest_se'] = change / row[f'se_{b}']
    row['update_sign_reversal'] = row['change_1_2'] * row['change_2_3'] < 0
    rows.append(row)
with (OUT / 'coefficient_comparison.csv').open('w',newline='') as stream:
    writer = csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
summary = {'computed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
           'training_observations': [1990,2008], 'target_outcomes_accessed': False,
           'scope': 'Saved attempts1–3 only; attempt4 remains active and unchanged.',
           'interpretation': 'Changes measured in marginal native SE units are descriptive displacements, not independent-fit significance tests.',
           'source_files': {'saved_attempts_1_to_3_diagnostics.json': hashlib.sha256(snapshot.read_bytes()).hexdigest(), **{name: hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ('training_effects.csv','fit-attempt-1.rds','fit-attempt-2.rds','fit-attempt-3.rds')}},
           'parameter_count': len(rows), 'groups': {}}
for label, subset in [('all',rows),('network_objective',[r for r in rows if r['name']=='dv.net' and r['type']=='eval']),('spending_objective',[r for r in rows if r['name']=='milex.beh' and r['type']=='eval']),('rates',[r for r in rows if r['type']=='rate'])]:
    group = {'n': len(subset), 'steps': {}}
    for a,b in ((1,2),(2,3),(1,3)):
        key = f'change_{a}_{b}_in_latest_se'
        values = [abs(row[key]) for row in subset]
        group['steps'][f'{a}_to_{b}'] = {'maximum_absolute_change_in_latest_se':max(values),'median_absolute_change_in_latest_se':statistics.median(values),
            'largest_named_changes':[{'name':r['name'],'effect':r['effectName'],'change':r[f'change_{a}_{b}'],'change_in_latest_se':r[key]} for r in sorted(subset,key=lambda r:abs(r[key]),reverse=True)[:5]]}
    group['update_sign_reversals'] = sum(r['update_sign_reversal'] for r in subset)
    group['reversals_with_both_steps_above_0_1_latest_se'] = [{'name':r['name'],'effect':r['effectName'],'step12':r['change_1_2_in_latest_se'],'step23':r['change_2_3_in_latest_se']} for r in subset if r['update_sign_reversal'] and abs(r['change_1_2_in_latest_se'])>.1 and abs(r['change_2_3_in_latest_se'])>.1]
    summary['groups'][label] = group
summary['native_diagnostics'] = [{key:f.get(key) for key in ('attempt','nsub','n3','seed','elapsed_seconds','valid','maximum_absolute_t_ratio','overall_maximum_convergence','native_ok','termination','phase3_complete','covariance_all_finite','divergence','fixed_parameters','newly_fixed_parameters','covariance_minimum_eigenvalue','covariance_condition_number','finite_identified')} for f in fits]
(OUT/'coefficient_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'groups':summary['groups']},indent=2))
