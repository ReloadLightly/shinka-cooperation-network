"""Protocol-specific Shinka hooks using replicated, MC-resolved comparisons.

Reuse the project's tested native hook installation, database persistence,
canonical deduplication and inspiration plumbing. Replace only the scientific
admission, pairwise relation, diversity coordinates, tournaments and migration
copying needed by this version. No alternative evolution loop is implemented.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import importlib.util
import ast
import inspect
import textwrap
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import sys
from scripts.replicated_metrics import PROTOCOL, KEYS, YEARS, T4, finite, jackknife, operational, resolved_dominance
from scripts.network_specification_v2 import validate_spec, spec_hash, complexity

ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location('_replicated_native_hook_base',ROOT/'shinka/pareto_selection.py')
base=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=base;_spec.loader.exec_module(base)
base.PROTOCOL=PROTOCOL


def validate_metrics(metrics, score):
    try:
        if not isinstance(metrics,dict) or metrics.get('protocol')!=PROTOCOL or metrics.get('valid') is not True:
            return 'Replicated protocol and complete validity required'
        expected=os.environ.get('SHINKA_SCIENTIFIC_FINGERPRINT')
        if expected and metrics.get('scientific_fingerprint')!=expected:
            return 'Scientific fingerprint differs from bound campaign'
        if metrics.get('forecast_batches_per_year')!=5 or metrics.get('pooled_endpoints_per_year')!=5000:
            return 'Incomplete replicated evaluation'
        canonical=spec_hash(validate_spec(metrics['canonical_specification']))
        if canonical!=metrics['canonical_sha256'] or metrics['complexity']!=complexity(metrics['canonical_specification'])['estimated_network_terms']:
            return 'Canonical identity or structural complexity mismatch'
        if not re.fullmatch(r'[0-9a-f]{64}',metrics.get('reference_identity','')):
            return 'Missing shared-reference identity'
        reference_expected=os.environ.get('SHINKA_REPLICATED_REFERENCE_ID')
        if reference_expected and metrics['reference_identity']!=reference_expected:
            return 'Reference identity differs from bound campaign'
        years=metrics['years']
        if set(years)!={str(y) for y in YEARS}:
            return 'All four years required'
        for year in years.values():
            if year.get('valid') is not True:return 'Incomplete annual evaluation'
            for key,name,sign in zip(KEYS,('pr_auc','brier','spending_rmse'),(1,-1,-1)):
                a,b=finite(year['candidate'][name]),finite(year['reference'][name])
                if not 0<=a<=(10 if name=='spending_rmse' else 1) or not 0<=b<=(10 if name=='spending_rmse' else 1):
                    return 'Out-of-range raw metric'
                if abs(finite(year[key])-sign*(a-b))>1e-12:return 'Annual objective mismatch'
        for key in KEYS:
            if abs(finite(metrics[key])-statistics.mean(years[str(y)][key] for y in YEARS))>1e-12:
                return 'Four-year aggregation differs'
        refmeans=[statistics.mean(years[str(y)]['reference'][name] for y in YEARS) for name in ('pr_auc','brier','spending_rmse')]
        scales=[1-refmeans[0],refmeans[1],refmeans[2]]
        if any(abs(finite(a)-b)>1e-15 for a,b in zip(metrics['selection_scales'],scales)) or len(metrics['selection_scales'])!=3:
            return 'Scale differs from fixed reference deficits'
        point=[metrics[k] for k in KEYS];deletes=metrics['delete_one_vectors']
        op=operational(point,deletes,scales)
        if abs(finite(score)-op['combined_score'])>1e-12:return 'Auxiliary score differs from declared uncertainty-averse rule'
        for j in range(3):
            se=jackknife([d[j] for d in deletes])
            if abs(finite(metrics['mc_standard_errors'][j])-se)>1e-12:return 'MC uncertainty inconsistent'
            expected_interval=[point[j]-T4*se,point[j]+T4*se]
            if len(metrics['mc_intervals'][j])!=2 or any(abs(finite(a)-b)>1e-12 for a,b in zip(metrics['mc_intervals'][j],expected_interval)):
                return 'MC interval inconsistent'
        return None
    except (ValueError,KeyError,TypeError,IndexError):
        return 'Malformed replicated scientific metrics'


@dataclass(frozen=True)
class Entry:
    id: str
    canonical: str
    island: int
    generation: int
    timestamp: float
    objectives: tuple
    deletes: tuple
    scales: tuple
    reference: str

    @property
    def z(self):
        return tuple(math.tanh(x/s) for x,s in zip(self.objectives,self.scales))

    def comparison(self):
        return {**dict(zip(KEYS,self.objectives)),'delete_one_vectors':self.deletes,
                'selection_scales':self.scales,'reference_identity':self.reference}


def dominates(a,b):
    return resolved_dominance(a.comparison(),b.comparison())


def read_entries(cursor,config):
    cursor.execute('SELECT id,correct,public_metrics,combined_score,island_idx,generation,timestamp FROM programs')
    entries=[];excluded={};shared=set()
    for row in cursor.fetchall():
        r=dict(row);pid=r['id']
        if r['correct']!=1:excluded[pid]='native_correct_false';continue
        try:m=json.loads(r['public_metrics'] or '{}')
        except (TypeError,json.JSONDecodeError):excluded[pid]='malformed_metrics';continue
        error=validate_metrics(m,r['combined_score'])
        if error:excluded[pid]=error;continue
        island=r['island_idx']
        if type(island) is not int or not 0<=island<config.num_islands:
            excluded[pid]='invalid_island';continue
        shared.add((m['reference_identity'],tuple(m['selection_scales']),m.get('scientific_fingerprint')))
        entries.append(Entry(pid,m['canonical_sha256'],island,int(r['generation']),float(r['timestamp']),
                     tuple(m[k] for k in KEYS),tuple(tuple(d) for d in m['delete_one_vectors']),
                     tuple(m['selection_scales']),m['reference_identity']))
    if len(shared)>1:
        raise ValueError('Mixed scientific/reference identities in native population')
    return entries,excluded


def sample_parent(selector,island_idx):
    entries,_=read_entries(selector.cursor,selector.config)
    pool,_,_=base.retained([e for e in entries if island_idx is None or e.island==island_idx],selector.config.archive_size//selector.config.num_islands)
    if not pool:raise ValueError('No admitted replicated parent')
    contestants=random.sample(pool,min(2,len(pool)))
    winner=contestants[0];reason='single_parent'
    if len(contestants)==2:
        a,b=contestants
        if dominates(a,b):winner=a;reason='MC_resolved_dominance'
        elif dominates(b,a):winner=b;reason='MC_resolved_dominance'
        else:winner=random.choice(contestants);reason='unresolved_or_tradeoff_uniform'
    base.logger.info('REPLICATED_PARENT %s',json.dumps({'id':winner.id,'reason':reason,'tournament':[e.id for e in contestants]}))
    p=selector.get_program(winner.id)
    if p is None:raise RuntimeError('Selected native parent disappeared')
    return p


def migrate(strategy,generation):
    cfg=strategy.config
    if cfg.num_islands<2 or cfg.migration_rate<=0:return False
    entries,_=read_entries(strategy.cursor,cfg)
    populations={i:base.representatives(e for e in entries if e.island==i) for i in range(cfg.num_islands)}
    moved=set();events=[]
    order=list(populations);random.shuffle(order)
    for src in order:
        local=populations[src];ranks,crowding=base.rank_and_crowding(local)
        front=[e for e in local if ranks[e.id]==0]
        if len(front)<2:continue
        anchors=[e for e in front if e.generation==0]
        anchor=min(anchors or front,key=base._origin)
        available=[e for e in front if e.id!=anchor.id and e.generation>0 and e.canonical not in moved]
        quota=min(len(available),max(1,math.floor(len(local)*cfg.migration_rate)))
        for _ in range(quota):
            options=[]
            for e in available:
                for dst,others in populations.items():
                    if src==dst or any(o.canonical==e.canonical or dominates(o,e) for o in others):continue
                    gap=min((base._distance(e,o) for o in others),default=math.sqrt(12))
                    if gap>0:options.append((e,dst,gap))
            if not options:break
            e,dst,gap=base._choose_max(options,key=lambda x:(x[2],crowding[x[0].id]))
            strategy._migrate_program(e.id,src,dst,generation)
            populations[src].remove(e);populations[dst].append(replace(e,island=dst));available.remove(e);moved.add(e.canonical)
            events.append({'id':e.id,'from':src,'to':dst,'objective_gap':gap})
    base.refresh_archive(strategy.cursor,strategy.conn,cfg,{'kind':'replicated_move_migration','generation':generation,'moves':events})
    return bool(events)


base.validate_metrics=validate_metrics
base.Entry=Entry
base.read_entries=read_entries
base.dominates=dominates
base._sample_parent=sample_parent
base._perform_migration=migrate


def no_new_evidence(program):
    return bool((program.metadata or {}).get('replicated_canonical_duplicate_of') or
                (program.public_metrics or {}).get('preexisting_step4_evidence'))


def credit_guard(original):
    """Three checked AST guards; retain the pinned native side-effect body.

    A duplicate remains a correct scientific result and a lineage node, but it
    is not fresh evidence for predictive bandit reward, prompt credit or meta updates.
    The bandit receives a missing reward so native completion/cost accounting continues.
    No temporarily shared mutable runner flags or asynchronous race is used.
    """
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    counts={'prompt':0,'meta':0,'reward':0}
    class Guard(ast.NodeTransformer):
        def visit_If(self,node):
            self.generic_visit(node)
            text=ast.unparse(node.test)
            kind=('prompt' if text=='system_prompt_id and self.evo_config.evolve_prompts' else
                  'meta' if text=='self.meta_summarizer' else None)
            if kind:
                counts[kind]+=1
                node.test=ast.BoolOp(op=ast.And(),values=[node.test,ast.UnaryOp(op=ast.Not(),operand=
                    ast.Call(func=ast.Name(id='_replicated_no_new_evidence',ctx=ast.Load()),args=[ast.Name(id='program',ctx=ast.Load())],keywords=[]))])
            return node
        def visit_Assign(self,node):
            self.generic_visit(node)
            if (len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='reward'
                and ast.unparse(node.value)=='program.combined_score if program.correct else None'):
                counts['reward']+=1
                node.value=ast.IfExp(test=ast.Call(func=ast.Name(id='_replicated_no_new_evidence',ctx=ast.Load()),
                    args=[ast.Name(id='program',ctx=ast.Load())],keywords=[]),body=ast.Constant(value=None),orelse=node.value)
            return node
    tree=Guard().visit(tree);ast.fix_missing_locations(tree)
    if counts!={'prompt':1,'meta':1,'reward':1}:
        raise RuntimeError('Pinned native side-effect structure changed; refuse ambiguous credit patch')
    namespace={**original.__globals__,'_replicated_no_new_evidence':no_new_evidence}
    exec(compile(tree,'<replicated-native-credit-guards>','exec'),namespace)
    fn=namespace[original.__name__];fn.__doc__=original.__doc__
    return fn


def install():
    """Process-local hooks; original on-disk implementation and old runs untouched."""
    base.install_native_pareto()
    from shinka.core.async_runner import ShinkaEvolveRunner
    if getattr(ShinkaEvolveRunner,'_replicated_pause_installed',False):return
    from shinka.database.dbase import ProgramDatabase
    previous_add=ProgramDatabase.add
    def add(database,program,*args,**kwargs):
        if program.correct and program.public_metrics.get('protocol')==PROTOCOL:
            entries,_=read_entries(database.cursor,database.config)
            same=[e for e in entries if e.canonical==program.public_metrics.get('canonical_sha256')]
            if same:
                program.metadata=dict(program.metadata or {})
                program.metadata['replicated_canonical_duplicate_of']=min(same,key=base._origin).id
        return previous_add(database,program,*args,**kwargs)
    ProgramDatabase.add=add
    ShinkaEvolveRunner._apply_persisted_program_side_effects=credit_guard(ShinkaEvolveRunner._apply_persisted_program_side_effects)
    previous=ShinkaEvolveRunner._project_results_paused
    def paused(results):
        if isinstance(results,dict):
            m=results.get('metrics',{});p=m.get('public',{})
            if (p.get('protocol')==PROTOCOL and p.get('status')=='paused_execution_window'
                and p.get('valid') is False and all(p.get(k) is None for k in KEYS)
                and m.get('combined_score') is None and results.get('correct',{}).get('correct') is False):
                return True
        return previous(results)
    ShinkaEvolveRunner._project_results_paused=staticmethod(paused)
    ShinkaEvolveRunner._replicated_pause_installed=True


def snapshot(database):
    entries,excluded=read_entries(database.cursor,database.config)
    unique=base.representatives(entries)
    return {'unique_evaluated_canonical_specifications':len(unique),'valid_lineage_rows':len(entries),
            'excluded_rows':excluded,'canonical_sha256':sorted(e.canonical for e in unique)}
