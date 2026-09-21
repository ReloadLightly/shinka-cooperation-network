#!/usr/bin/env python3
"""Real native scheduler/SQLite/selection/persistence replay; zero LLM or R runs.

This executes actual native local evaluator subprocesses on preserved evidence.
The pending-job test drives native persistence/resubmission methods with a small
controller fixture; it is not represented as a complete live LLM evolution loop.
"""
from __future__ import annotations
import asyncio, dataclasses, importlib.util, json, os, math, pickle, sys, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
os.environ['SHINKA_PRICING_MODE']='offline'
os.environ.pop('SHINKA_REPLICATED_ALLOW_NEW',None)
from scripts import replicated_evaluation as ev
from scripts.scientific_contract import immutable_json, digest
from shinka.database import ProgramDatabase, DatabaseConfig, Program
from shinka.launch import JobScheduler, LocalJobConfig
from shinka.core.async_runner import ShinkaEvolveRunner, AsyncRunningJob
from shinka.core.summarizer import MetaSummarizer
from shinka.llm.prioritization import AsymmetricUCB
from shinka.database.prompt_dbase import SystemPrompt, SystemPromptDatabase, SystemPromptConfig

spec=importlib.util.spec_from_file_location('project_replicated_native_test',ROOT/'shinka/replicated_selection.py')
sel=importlib.util.module_from_spec(spec);sys.modules[spec.name]=sel;spec.loader.exec_module(sel)
sel.install()
OUT=Path(os.environ['STEP5A_NATIVE_PY_OUT']);OUT.mkdir(parents=True,exist_ok=True)
checks=[]
def check(value,name):
    if not value:raise AssertionError(name)
    checks.append(name)

def main():
    science=ev.identity(ROOT)
    os.environ['SHINKA_SCIENTIFIC_FINGERPRINT']=science['sha256']
    reference=ev.result_for(ev.policy()['reference'],ev.evidence_root())
    reference_id=digest({str(y):reference[y]['evidence_sha256'] for y in ev.YEARS})
    os.environ['SHINKA_REPLICATED_REFERENCE_ID']=reference_id
    scheduler=JobScheduler('local',LocalJobConfig(eval_program_path=str(ROOT/'scripts/replicated_evaluation.py'),
        python_executable=sys.executable,extra_cmd_args={'protocol':ev.PROTOCOL},time='00:10:00',numeric_threads_per_job=1),verbose=False)
    results={}
    for model in ('reference','gwesp69'):
        result,elapsed=scheduler.run(str(ROOT/f'candidates/step4_{model}.py'),str(OUT/f'job-{model}'))
        check(result['correct']['correct'] is True,'native scheduler valid '+model)
        results[model]=result['metrics']
        check(sel.validate_metrics(result['metrics']['public'],result['metrics']['combined_score']) is None,'native admission '+model)
    check([results['reference']['public'][k] for k in ev.KEYS]==[0,0,0],'reference exact zero')
    # Preserve the original Step 4 replay separately from the integer-pool view.
    originals={}
    for model in ('reference','gwesp69'):
        originals[model]={y:ev.read(ev.evidence_root()/ev.RESULT_SUBDIR/model/str(y)/'scores/comparison-metrics.json') for y in ev.YEARS}
    from scripts.replicated_metrics import aggregate
    legacy=aggregate(originals['gwesp69'],originals['reference'])
    check(abs(legacy['J1']-(-.0026707754342265855))<1e-15,'original Step 4 J1 reproduced')
    check(abs(legacy['J2']-1.1269955188679295e-5)<1e-16,'original Step 4 J2 reproduced')
    check(abs(legacy['J3']-(-.00021712129519249612))<1e-15,'original Step 4 J3 reproduced')
    duplicate=OUT/'equivalent.py'
    duplicate.write_text('# differently formatted existing model; not a proposal\n'+(ROOT/'candidates/step4_gwesp69.py').read_text())
    again,_=scheduler.run(str(duplicate),str(OUT/'job-duplicate'))
    check(again['metrics']['public']==results['gwesp69']['public'],'canonical replay returns identical evidence and seeds')
    unknown=OUT/'unevaluated.py';unknown.write_text('def build_network_spec(allowed_schema):\n    return {"schema_version":2,"network_effects":[{"effect":"gwesp","parameter":40}]}\n')
    paused,_=scheduler.run(str(unknown),str(OUT/'job-paused'))
    check(ShinkaEvolveRunner._project_results_paused(paused),'new protocol pause recognized by native runner')
    check(paused['metrics']['combined_score'] is None,'paused score null')
    invalid=OUT/'invalid.py';invalid.write_text('import os\nos.system("false")\n')
    invalid_result,_=scheduler.run(str(invalid),str(OUT/'job-invalid'))
    check(invalid_result['correct']['correct'] is False,'invalid AST rejected')
    check(invalid_result['metrics']['combined_score'] is None,'invalid fitness null')
    cfgdata=ev.read(ROOT/'shinka/native_replicated_config.json')['database']
    cfg=DatabaseConfig(db_path=str(OUT/'programs.sqlite'),**cfgdata)
    db=ProgramDatabase(cfg)
    p0=Program(id='replay-reference',code=(ROOT/'candidates/step4_reference.py').read_text(),generation=0,island_idx=0,
        correct=True,combined_score=results['reference']['combined_score'],public_metrics=results['reference']['public'],
        metadata={'fixture':'existing reference; not a new Shinka proposal'})
    db.add(p0)
    p1=Program(id='replay-gwesp69',code=(ROOT/'candidates/step4_gwesp69.py').read_text(),generation=1,island_idx=0,parent_id=p0.id,
        correct=True,combined_score=results['gwesp69']['combined_score'],public_metrics=results['gwesp69']['public'],
        metadata={'fixture':'existing manually chosen comparator; not a Shinka offspring'})
    db.add(p1)
    p2=Program(id='replay-duplicate',code=duplicate.read_text(),generation=2,island_idx=0,parent_id=p1.id,
        correct=True,combined_score=p1.combined_score,public_metrics=p1.public_metrics)
    db.add(p2)
    check(db.get(p2.id).metadata.get('replicated_canonical_duplicate_of')==p1.id,'duplicate lineage tagged without invalidating scientific score')
    check(sel.no_new_evidence(p2),'duplicate receives no bandit/prompt/meta evidence credit')
    check(sel.no_new_evidence(p1),'preexisting manual comparator not rewarded as new search evidence')
    snap=sel.snapshot(db);check(snap['unique_evaluated_canonical_specifications']==2,'unique models not lineage rows')
    parents=[]
    for _ in range(5):
        parent,archive,top=db.sample(target_generation=3)
        parents.append(parent.id)
        check(parent.correct and all(x.correct for x in archive+top),'native parent/inspiration sampling valid')
    # Native MOVE migration retains uncertainty fields and never deletes source rows.
    strategy=db.island_manager.migration_strategy if hasattr(db.island_manager,'migration_strategy') else None
    if strategy is not None:
        strategy.perform_migration(3)
        check(sel.snapshot(db)['unique_evaluated_canonical_specifications']==2,'migration preserves canonical population')
    # Save/reopen the actual SQLite population and scientific selection record.
    db.save();before=sel.snapshot(db);db.close();db=ProgramDatabase(cfg)
    check(sel.snapshot(db)==before,'native database reopen preserves scientific population')
    check(db.get(p1.id).parent_id==p0.id,'ancestry persists')
    bandit=AsymmetricUCB(arm_names=['fixture-a','fixture-b','fixture-c'],seed=71)
    bandit.set_baseline_score(2)
    bandit.update_submitted('fixture-a');bandit.update('fixture-a',reward=p1.combined_score,baseline=2)
    bandit.save_state(OUT/'bandit.pkl')
    b2=AsymmetricUCB(arm_names=['fixture-a','fixture-b','fixture-c'],seed=999);b2.load_state(OUT/'bandit.pkl')
    check(pickle.dumps(bandit.get_state())==pickle.dumps(b2.get_state()),'native bandit state roundtrip')
    meta=MetaSummarizer(meta_llm_client=None);meta.add_evaluated_program(db.get(p1.id))
    meta.meta_scratch_pad='Fixture: preserve mixed closure result; no new inference.'
    meta.save_meta_state(str(OUT/'meta.json'))
    m2=MetaSummarizer(meta_llm_client=None)
    check(m2.load_meta_state(str(OUT/'meta.json')),'native meta-state loads without LLM call')
    check(m2.meta_scratch_pad==meta.meta_scratch_pad,'native meta scratchpad preserved')
    pcfg=SystemPromptConfig(db_path=str(OUT/'prompts.sqlite'))
    pdb=SystemPromptDatabase(pcfg)
    prompt=SystemPrompt(id='fixture-prompt',prompt_text=(ROOT/'shinka/task_prompt_replicated.md').read_text())
    pdb.add(prompt);pdb.close();pdb=SystemPromptDatabase(pcfg)
    check(pdb.get(prompt.id).prompt_text==prompt.prompt_text,'native prompt archive survives reopen');pdb.close()
    # Drive the native pending queue without a proposer or a full runner constructor.
    db.conn.execute('CREATE TABLE IF NOT EXISTS project_pending_evaluations (generation INTEGER PRIMARY KEY,payload TEXT NOT NULL,updated_at REAL NOT NULL)')
    controller=ShinkaEvolveRunner.__new__(ShinkaEvolveRunner)
    controller.db=db;controller.slot_available=asyncio.Event();controller.running_jobs=[];controller.active_proposal_tasks=set()
    controller._project_window_closed=lambda:False;controller._has_persistence_work_in_progress=lambda:False
    controller.evo_config=SimpleNamespace(num_generations=math.inf)
    events=[]
    async def record(**kw):events.append(kw)
    controller._record_generation_event=record
    pending_path=OUT/'pending.py';pending_path.write_text(p1.code)
    pending_out=OUT/'pending-result';pending_out.mkdir()
    job=AsyncRunningJob(job_id=None,exec_fname=str(pending_path),results_dir=str(pending_out),start_time=0,
        proposal_started_at=0,evaluation_submitted_at=0,generation=9,parent_id=p0.id,archive_insp_ids=[p1.id],
        meta_patch_data={'fixture':True,'seed_history':'unchanged'},code_diff='fixture only')
    asyncio.run(controller._project_save_pending(job,'replay-only resource boundary'))
    saved=ev.read(OUT/'job-paused/metrics.json')
    check(db.conn.execute('SELECT COUNT(*) FROM project_pending_evaluations').fetchone()[0]==1,'native pending queue persisted')
    payload=json.loads(db.conn.execute('SELECT payload FROM project_pending_evaluations WHERE generation=9').fetchone()[0])
    check(payload['parent_id']==p0.id and payload['archive_insp_ids']==[p1.id],'pending ancestry and inspirations preserved')
    pending_path.write_text(p1.code+'\n# changed bytes\n')
    try:asyncio.run(controller._project_resume_pending());raise AssertionError('Expected changed-pending refusal')
    except RuntimeError as ex:check('changed' in str(ex),'native pending source tampering refused')
    pending_path.write_text(p1.code)
    async def submit(code,out,worker):
        j=scheduler.submit_async(code,out)
        return j,0,time.time(),time.time(),1
    controller._submit_evaluation_job_with_slot=submit
    asyncio.run(controller._project_resume_pending())
    check(len(controller.running_jobs)==1,'native pending resubmits same source without proposer')
    completed=scheduler.monitor(controller.running_jobs[0].job_id,str(pending_out))
    check(completed['correct']['correct'] is True,'resumed native local replay completes')
    check(completed['metrics']['public']==results['gwesp69']['public'],'resumed score identical, no redraw')
    scheduler.shutdown();db.close()
    report={'status':'passed','checks':checks,'check_count':len(checks),'scientific_fingerprint':science['sha256'],
        'reference_identity':reference_id,'legacy_step4_objectives':{k:legacy[k] for k in ev.KEYS},
        'replicated_integer_objectives':{k:results['gwesp69']['public'][k] for k in ev.KEYS},
        'operational_score':results['gwesp69']['combined_score'],'selection_scales':results['gwesp69']['public']['selection_scales'],
        'native_scheduler_jobs':6,'new_fits':0,'new_forecasts':0,'new_simulations':0,'llm_calls':0,
        'new_evolutionary_proposals':0,'unique_preexisting_specifications':2,'native_population_before_reopen':before,
        'scope':'Actual native local scheduler and SQLite APIs; pending methods driven by controller fixture. No full live LLM evolution loop or authentication test.'}
    immutable_json(OUT/'verification.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
