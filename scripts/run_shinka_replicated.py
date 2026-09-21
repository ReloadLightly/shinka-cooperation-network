#!/usr/bin/env python3
"""Explicit native Shinka handoff to the generalized replicated evaluator.

Default is a pure configuration resolution, not a proposal or a numerical run.
Execution requires both a bounded admission window and a persistent numerical
admission budget. Local authenticated headless proposal routing is preserved;
this script does not turn GitHub Actions into a remote evaluator automatically.
"""
from __future__ import annotations
import argparse
import dataclasses
import fcntl
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import replicated_evaluation as ev
from scripts.scientific_contract import bind_campaign, immutable_json, source_hashes, digest, require_search_open
from scripts.execution_windows import resolve_deadline, set_deadline
from scripts.replicated_host import (HostUnavailable, require_runtime, service_ports,
                                     require_free_ports, wait_services, stop_services)
CONFIG='shinka/native_replicated_config.json'
UPSTREAM='9912af12d423504b8d580f4179fd15f5f88b8c50'


def resolve(folder,window_hours=None,max_new_specs=None,root=ROOT):
    c=json.loads((root/CONFIG).read_text())
    if c['protocol']!=ev.PROTOCOL or c['upstream_commit']!=UPSTREAM:
        raise ValueError('Wrong explicit native scientific protocol')
    if window_hours is not None and (not math.isfinite(window_hours) or window_hours<=0):
        raise ValueError('Positive admission window required')
    if max_new_specs is not None and (type(max_new_specs) is not int or max_new_specs<=0):
        raise ValueError('Positive canonical numerical-admission limit required')
    if c['evolution']['job_type']!='local' or c['runner']['max_evaluation_jobs']!=1:
        raise ValueError('This version explicitly uses one local evaluator; no implicit remote backend')
    for key in ('llm_models','meta_llm_models','prompt_llm_models','novelty_llm_models'):
        if not c['evolution'][key] or any(not m.startswith('headless/codex@') for m in c['evolution'][key]):
            raise ValueError('No paid proposal fallback or silent provider substitution')
    result={'protocol':ev.PROTOCOL,'scientific_fingerprint':ev.identity(root)['sha256'],
        'evaluator':str(root/'scripts/replicated_evaluation.py'),'extra_cmd_args':{'protocol':ev.PROTOCOL},
        'results_dir':str(Path(folder).resolve()),'execution_backend':'local','window_hours':window_hours,
        'max_new_canonical_admissions':max_new_specs,'settings':c,'executed':False,
        'model_availability':'not established by this configuration resolution','reserved_year_access':False}
    return result


def launch(args):
    folder=args.results_dir.resolve();resolved=resolve(folder,args.window_hours,args.max_new_specs)
    if not args.execute:
        print(json.dumps(resolved,indent=2));return 0
    if args.window_hours is None or args.max_new_specs is None:
        raise ValueError('Execution requires explicit --window-hours and --max-new-specs; no default compute commitment')
    require_search_open(ROOT)
    ports = service_ports(resolved['settings'], args.webui_port)
    require_free_ports(ports)
    host_report = require_runtime(ROOT)
    if (ROOT/'results/selection/multiobjective-replicated-v1/plan.json').exists():raise ValueError('Finalist set frozen')
    from scripts.check_native_patch import verify_patch
    verify_patch()
    source=ROOT/'vendor/ShinkaEvolve'
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=UPSTREAM:
        raise ValueError('Wrong pinned upstream commit')
    from shinka.core import EvolutionConfig, ShinkaEvolveRunner
    from shinka.database import DatabaseConfig
    from shinka.launch import LocalJobConfig
    from shinka.llm.providers.headless import parse_headless_model
    c=resolved['settings'];evo=c['evolution'].copy()
    for key in ('llm_models','meta_llm_models','prompt_llm_models','novelty_llm_models'):
        for model in evo[key]:parse_headless_model(model)
    if not evo['embedding_model'].startswith('local/potion-base-8M@http://127.0.0.1:'):
        raise ValueError('Only pinned local embeddings allowed')
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'campaign_supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        science=ev.identity(ROOT)
        search={'config':c,'sources':source_hashes(ROOT,(CONFIG,'shinka/replicated_selection.py',
            'shinka/pareto_selection.py','shinka/task_prompt_replicated.md','scripts/run_shinka_replicated.py',
            'shinka/multiobjective_native.patch','scripts/replicated_host.py'))}
        bind_campaign(folder,science,search)
        # Verify the actual shared reference before constructing a model client.
        ref=ev.result_for(ev.policy()['reference'],ev.evidence_root())
        reference_id=digest({str(y):ref[y]['evidence_sha256'] for y in ev.YEARS})
        immutable_json(folder/'reference-identity.json',{'sha256':reference_id})
        os.environ.update(SHINKA_REPLICATED_REFERENCE_ID=reference_id,
            SHINKA_REPLICATED_ALLOW_NEW='1',SHINKA_REPLICATED_CAMPAIGN=str(folder),
            SHINKA_REPLICATED_ADMISSION_LIMIT=str(args.max_new_specs),SHINKA_PRICING_MODE='offline',
            SHINKA_HEADLESS_COMMAND=f'{sys.executable} {ROOT / "shinka/headless_isolated.py"}',
            SHINKA_HEADLESS_TIMEOUT='1800',PYTHON_DOTENV_DISABLED='1')
        # Bind budget now, without consuming an admission.
        immutable_json(folder/'numerical-budget.json',{'version':ev.PROTOCOL,'limit':args.max_new_specs,
                       'scientific_fingerprint':science['sha256']})
        for key in list(os.environ):
            if key.endswith('API_KEY') or key in ('OPENAI_ACCESS_TOKEN','ANTHROPIC_AUTH_TOKEN'):
                os.environ.pop(key,None)
        deadline=resolve_deadline(args.window_hours);set_deadline(deadline)
        evo['execution_window_seconds']=max(.001,deadline-time.time())
        public=ROOT/'runs/public_mutation'/folder.name;public.mkdir(parents=True,exist_ok=True)
        for key in ('llm_kwargs','meta_llm_kwargs','prompt_llm_kwargs','novelty_llm_kwargs'):
            evo[key]={**evo[key],'headless_work_dir':str(public)}
        evo.update(task_sys_msg=(ROOT/'shinka/task_prompt_replicated.md').read_text()+'\n\nNative grammar:\n'+
            (ROOT/'configs/effect-catalog-v2.json').read_text(),init_program_path=str(ROOT/'candidates/initial_multiobjective.py'),results_dir=str(folder))
        # Four serial cells, each with a 4h cumulative native cap. This is a hard
        # protection, not the admission-window duration or a new scientific loss.
        job=LocalJobConfig(eval_program_path=str(ROOT/'scripts/replicated_evaluation.py'),python_executable=sys.executable,
            extra_cmd_args={'protocol':ev.PROTOCOL},time='16:30:00',**c['job'])
        db=DatabaseConfig(db_path=str(folder/'programs.sqlite'),**c['database'])
        module_spec=importlib.util.spec_from_file_location('project_replicated_selection',ROOT/'shinka/replicated_selection.py')
        module=importlib.util.module_from_spec(module_spec);sys.modules[module_spec.name]=module;module_spec.loader.exec_module(module);module.install()
        if not (folder/'resolved_config.json').exists():immutable_json(folder/'resolved_config.json',resolved)
        with (folder/'launch_history.jsonl').open('a') as stream:stream.write(json.dumps({'started_unix':time.time(),'deadline':deadline,'resolved':resolved,'local_runtime':host_report})+'\n')
        streams=[];services={}
        try:
            for name,cmd in (
                ('embedding',[sys.executable,str(ROOT/'shinka/embedding_server.py'),'--port',str(ports['embedding']),'--log',str(folder/'embedding_calls.jsonl')]),
                ('webui',[str(Path(sys.executable).parent/'shinka_visualize'),str(folder),'--port',str(args.webui_port)])):
                log=(folder/f'{name}.log').open('a');streams.append(log)
                services[name]=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            wait_services(services, ports)
            print(f'Replicated evaluator; WebUI http://localhost:{args.webui_port}; native state retained in {folder}',flush=True)
            runner=ShinkaEvolveRunner(evo_config=EvolutionConfig(**evo),db_config=db,job_config=job,**c['runner'],verbose=True)
            runner.run()
        finally:
            try:
                stop_services(services.values())
            finally:
                for stream in streams:stream.close()
    return 75 if time.time()>=deadline else 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results-dir',type=Path,required=True)
    p.add_argument('--window-hours',type=float)
    p.add_argument('--max-new-specs',type=int)
    p.add_argument('--webui-port',type=int,default=8765)
    p.add_argument('--execute',action='store_true')
    try:
        return launch(p.parse_args())
    except HostUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 75

if __name__=='__main__':raise SystemExit(main())
