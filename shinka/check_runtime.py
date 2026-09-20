#!/usr/bin/env python3
"""Harmless timeout/descendant cleanup checks. No R, services, or model calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    import psutil
    from scripts.run_shinka import evaluation_timeout, supervise_native
    from shinka.launch.local import ProcessWithLogging
    from shinka.core.async_runner import ShinkaEvolveRunner

    folder = ROOT / "runs/shinka_runtime_checks" / str(time.time_ns())
    folder.mkdir(parents=True)
    child_code = (
        "import subprocess,sys,time,json,os; from pathlib import Path; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True); "
        "Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid,'sid':os.getsid(p.pid),'parent_sid':os.getsid(0)})); "
        "p.wait()"
    )
    first_pidfile = folder / "native-child.json"
    first = subprocess.Popen([sys.executable, "-c", child_code, str(first_pidfile)])
    for _ in range(100):
        if first_pidfile.exists():
            break
        time.sleep(0.02)
    child = json.loads(first_pidfile.read_text())
    assert child["sid"] != child["parent_sid"], "fixture child did not use a separate session"
    wrapped = ProcessWithLogging(first, (), ())
    wrapped.kill()
    assert first.poll() is not None
    assert not psutil.pid_exists(child["pid"]), "native kill left its detached child alive"

    supervisor_dir = folder / "supervisor"
    supervisor_dir.mkdir()
    second_pidfile = folder / "supervised-child.json"
    command = [sys.executable, "-c", child_code, str(second_pidfile)]
    exit_code = supervise_native(command, supervisor_dir, 0.8, 1.0, 0.05)
    assert exit_code == 75
    second_child = json.loads(second_pidfile.read_text())
    assert not psutil.pid_exists(second_child["pid"]), "supervisor left detached child alive"
    before = (supervisor_dir / "campaign_process.json").read_text()
    assert supervise_native(command, supervisor_dir, 0.8, 1.0, 0.05) == 75
    assert before == (supervisor_dir / "campaign_process.json").read_text(), "exhausted resume launched work"

    resume_dir = folder / "resume"
    resume_dir.mkdir()
    quick = [sys.executable, "-c", "import time;time.sleep(0.03)"]
    assert supervise_native(quick, resume_dir, 5, 1, 0.05) == 0
    first_elapsed = json.loads((resume_dir / "campaign_process.json").read_text())["accumulated_walltime_seconds"]
    assert supervise_native(quick, resume_dir, 5, 1, 0.05) == 0
    resumed = json.loads((resume_dir / "campaign_process.json").read_text())
    assert resumed["accumulated_walltime_seconds"] > first_elapsed
    assert len(resumed["invocations"]) == 2

    config = json.loads((ROOT / "shinka/native_config.json").read_text())
    problems = []
    missing, summary = evaluation_timeout(config, {}, problems)
    assert missing is None and problems
    ready = {"native_evaluation_timeout_seconds": summary["scientific_upper_bound_seconds"] + 120,
             "native_evaluation_timeout_margin_seconds": 120,
             "evaluator_settings_sha256": summary["settings_sha256"]}
    problems = []
    formatted, _ = evaluation_timeout(config, ready, problems)
    assert not problems
    fake = SimpleNamespace(job_config=SimpleNamespace(time=formatted),
                           scheduler=SimpleNamespace(job_type="local"), _evaluation_seconds_ewma=0.001)
    actual_limit = ShinkaEvolveRunner._get_evaluation_runtime_limit_seconds(fake)
    assert actual_limit == ready["native_evaluation_timeout_seconds"]
    ready["native_evaluation_timeout_seconds"] = 600
    problems = []
    evaluation_timeout(config, ready, problems)
    assert any("shorter" in message for message in problems)
    result = {"native_detached_descendant_cleanup": True, "supervisor_detached_descendant_cleanup": True,
              "cumulative_resume_accounting": True, "exhausted_budget_launches_nothing": True,
              "explicit_timeout_overrides_cached_seed_ewma": True, "short_timeout_rejected": True,
              "scientific_upper_bound_seconds": summary["scientific_upper_bound_seconds"],
              "test_timeout_format": formatted, "no_R_or_model_calls": True,
              "output_directory": str(folder)}
    (folder / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
