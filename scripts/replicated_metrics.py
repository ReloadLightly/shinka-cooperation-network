"""Replicated predictive vectors and a declared, approximate selection heuristic.

Pure functions: no simulation, outcome reads, inference of fitted coefficients,
or adaptive replication. Shared-reference Monte Carlo terms cancel in pairwise
comparisons by differencing identically indexed delete-one-batch vectors.
"""
from __future__ import annotations
import math
import statistics
from typing import Sequence

PROTOCOL = 'multiobjective-replicated-v1'
KEYS = ('J1', 'J2', 'J3')
METRICS = ('pr_auc', 'brier', 'spending_rmse')
SIGNS = (1, -1, -1)
YEARS = (2006, 2007, 2008, 2009)
T4 = 2.7764451051977987


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('Expected a finite real number')
    return float(value)


def jackknife(values: Sequence[float]) -> float:
    if len(values) != 5:
        raise ValueError('Exactly five declared delete-one-batch values required')
    vals = [finite(v) for v in values]
    center = statistics.mean(vals)
    return math.sqrt(4 / 5 * math.fsum((v - center) ** 2 for v in vals))


def validate_cell_metrics(metrics):
    if metrics.get('status') != 'complete' or metrics.get('primary_endpoints') != 5000:
        raise ValueError('Complete 5,000-endpoint cell required')
    if len(metrics.get('batches', [])) != 5 or len(metrics.get('delete_one_batch', [])) != 5:
        raise ValueError('Five batches and five deletions required')
    for block in [metrics['pooled'], *metrics['batches'], *metrics['delete_one_batch']]:
        for name in (*METRICS, 'formation_pr_auc', 'dissolution_pr_auc'):
            v = finite(block[name])
            if not 0 <= v <= (10 if name == 'spending_rmse' else 1):
                raise ValueError(f'Out-of-range metric: {name}')
    for name in ('dyads', 'spending_countries'):
        if type(metrics[name]) is not int or metrics[name] <= 0:
            raise ValueError(f'Missing eligible sample: {name}')
    return metrics


def aggregate(candidate, reference):
    """Keys are integer years. No partial-year fitness or averaging batch AUCs."""
    if set(candidate) != set(YEARS) or set(reference) != set(YEARS):
        raise ValueError('Every development year required')
    annual, deletes, batches = {}, [], []
    for year in YEARS:
        c, r = validate_cell_metrics(candidate[year]), validate_cell_metrics(reference[year])
        for k in ('eligibility_sha256', 'dyads', 'spending_countries'):
            if c[k] != r[k]:
                raise ValueError(f'Different eligible population in {year}: {k}')
        annual[str(year)] = {'valid': True, 'candidate': c['pooled'], 'reference': r['pooled'],
            **{key: sign * (c['pooled'][name] - r['pooled'][name])
               for key, name, sign in zip(KEYS, METRICS, SIGNS)}}
    vector = [statistics.mean(annual[str(y)][k] for y in YEARS) for k in KEYS]
    for index in range(5):
        for field, output in (('delete_one_batch', deletes), ('batches', batches)):
            output.append([statistics.mean(sign * (candidate[y][field][index][m] - reference[y][field][index][m])
                                             for y in YEARS) for m, sign in zip(METRICS, SIGNS)])
    ref_means = [statistics.mean(reference[y]['pooled'][m] for y in YEARS) for m in METRICS]
    scales = [1 - ref_means[0], ref_means[1], ref_means[2]]
    if any(not math.isfinite(v) or v <= 0 for v in scales):
        raise ValueError('Reference deficits must be positive; no adaptive scale substitution')
    errors = [jackknife([row[j] for row in deletes]) for j in range(3)]
    result = {'years': annual, **dict(zip(KEYS, vector)), 'delete_one_vectors': deletes,
              'batch_vectors': batches, 'selection_scales': scales,
              'mc_standard_errors': errors,
              'mc_intervals': [[p - T4 * s, p + T4 * s] for p, s in zip(vector, errors)],
              'uncertainty_scope': 'Approximate five-block conditional forecast Monte Carlo uncertainty only; not fitting, generalization or simultaneous selective inference.'}
    result['operational'] = operational(vector, deletes, scales)
    return result


def operational(vector, deletes, scales):
    if len(vector) != 3 or len(scales) != 3 or len(deletes) != 5:
        raise ValueError('Wrong operational vector dimensions')
    if any(finite(x) <= 0 for x in scales) or any(len(d) != 3 for d in deletes):
        raise ValueError('Invalid operational scales or deletion dimensions')
    point = statistics.mean(finite(v) / s for v, s in zip(vector, scales))
    deleted = [statistics.mean(finite(v) / s for v, s in zip(row, scales)) for row in deletes]
    se = jackknife(deleted)
    lower = point - T4 * se
    return {'mean_scaled_improvement': point, 'mc_se': se, 'lower_heuristic': lower,
            'combined_score': 2 + math.tanh(lower),
            'interpretation': 'Fixed uncertainty-averse bandit/prompt preference; not a scientific fourth objective or a confidence guarantee.'}


def resolved_dominance(a, b):
    """Acyclic: resolution rule is a subset of strict point Pareto dominance."""
    if a['reference_identity'] != b['reference_identity'] or a['selection_scales'] != b['selection_scales']:
        raise ValueError('Cannot compare different reference/scaling protocols')
    point = [finite(a[k]) - finite(b[k]) for k in KEYS]
    if not all(d >= 0 for d in point) or not any(d > 0 for d in point):
        return False
    lower = [point[j] - T4 * jackknife([a['delete_one_vectors'][i][j] - b['delete_one_vectors'][i][j]
                                      for i in range(5)]) for j in range(3)]
    return all(v >= 0 for v in lower) and any(v > 0 for v in lower)
