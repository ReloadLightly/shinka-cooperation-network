#!/usr/bin/env python3
"""Resolve/preflight, then launch the native Shinka runner; never an evolution loop."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import socket
import time
import urllib.request
import fcntl
import signal

ROOT = Path(__file__).resolve().parents[1]


def run_multiobjective(args, config):
    """Use the native runner with scientific Pareto/deadline integration.

    This branch does no readiness campaign, administrative model call or browser
    check. It preserves the existing subscription isolation and local services.
    The native runner owns all proposals, adaptation, scheduling and resumption.
    """
    import importlib.util

    if args.native_worker or args.supervisor_only:
        raise ValueError("multiobjective-v1 uses the native runner, not the legacy terminating supervisor")
    hours = args.window_hours
    if hours is not None and not positive_number(hours):
        raise ValueError("--window-hours must be finite and positive")
    # The user superseded the former session deadline. Publication checkpoints
    # do not limit scientific admission. An explicit future --window-hours is
    # still supported; stale inherited deadlines must not stop this campaign.
    deadline = time.time() + hours * 3600 if hours is not None else None
    if deadline is None:
        os.environ.pop("SHINKA_EXECUTION_DEADLINE", None)
    else:
        os.environ["SHINKA_EXECUTION_DEADLINE"] = str(deadline)
    os.environ["SHINKA_PRICING_MODE"] = "offline"
    os.environ["SHINKA_HEADLESS_COMMAND"] = f"{sys.executable} {ROOT / 'shinka/headless_isolated.py'}"
    os.environ["SHINKA_HEADLESS_TIMEOUT"] = "1800"
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for name in list(os.environ):
        if name.endswith("API_KEY") or name in {"OPENAI_ACCESS_TOKEN", "ANTHROPIC_AUTH_TOKEN"}:
            os.environ.pop(name, None)
    from shinka.core import EvolutionConfig, ShinkaEvolveRunner
    from shinka.database import DatabaseConfig
    from shinka.launch import LocalJobConfig
    from shinka.llm.providers.headless import parse_headless_model

    evo = config["evolution"].copy()
    evo["execution_window_seconds"] = max(0.001, deadline - time.time()) if deadline is not None else None
    for key in ("llm_models", "meta_llm_models", "novelty_llm_models", "prompt_llm_models"):
        for model in evo[key]:
            if not model.startswith("headless/codex@"):
                raise ValueError(f"Unauthorized model route: {model}")
            parse_headless_model(model)
    if not evo["embedding_model"].startswith("local/potion-base-8M@http://127.0.0.1:"):
        raise ValueError("Use the existing pinned local embeddings; no paid fallback")
    public_workdir = ROOT / "runs/public_mutation" / args.results_dir.name
    public_workdir.mkdir(parents=True, exist_ok=True)
    for key in ("llm_kwargs", "meta_llm_kwargs", "novelty_llm_kwargs", "prompt_llm_kwargs"):
        evo[key] = {**evo.get(key, {}), "headless_work_dir": str(public_workdir)}
    task = (ROOT / "shinka/task_prompt_multiobjective.md").read_text()
    task += "\n\nNative mathematical operators and compatibility:\n" + (ROOT / "configs/effect-catalog-v2.json").read_text()
    initial = args.initial.resolve()
    if initial == (ROOT / "candidates/initial.py").resolve():
        initial = ROOT / "candidates/initial_multiobjective.py"
    evo.update(task_sys_msg=task, init_program_path=str(initial), results_dir=str(args.results_dir))
    policy = json.loads((ROOT / "configs/multiobjective-v1.json").read_text())
    settings = json.loads((ROOT / policy["prediction_settings"]).read_text())
    annual_cap = settings["estimation"]["timeout_seconds"] * settings["estimation"]["max_attempts"] + settings["forecast"]["timeout_seconds"] + 300
    timeout = len(settings["development_years"]) * annual_cap + 600
    job = LocalJobConfig(eval_program_path=str(ROOT / "scripts/multiobjective_evaluation.py"), python_executable=sys.executable,
                         extra_cmd_args={"protocol": "multiobjective-v1"},
                         time=f"{timeout // 3600:02d}:{timeout % 3600 // 60:02d}:{timeout % 60:02d}", **config["job"])
    db = DatabaseConfig(db_path=str(args.results_dir / "programs.sqlite"), **config["database"])
    evolution = EvolutionConfig(**evo)
    resolved = {"protocol": policy, "evolution": dataclasses.asdict(evolution),
                "database": dataclasses.asdict(db), "job": dataclasses.asdict(job),
                "runner": config["runner"], "upstream_commit": config["upstream_commit"],
                "model_routing": json.loads((ROOT / "shinka/model-routing-multiobjective.json").read_text()),
                "resource_policy": config["resource_policy"], "execution_deadline_unix": deadline,
                "pareto_extension": "shinka/pareto_selection.py", "native_extension": "shinka/multiobjective_native.patch",
                "overall_generation_ceiling": None, "paid_api_fallback": False}
    with (args.results_dir / "campaign_supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write_json(args.results_dir / "resolved_config.json", resolved)
        if not args.execute:
            print(json.dumps({"resolved_config": str(args.results_dir / "resolved_config.json"),
                              "execution_deadline_unix": deadline, "launched": False}))
            return 0
        module_spec = importlib.util.spec_from_file_location("project_scientific_pareto", ROOT / "shinka/pareto_selection.py")
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        module.install_native_pareto()
        os.chdir(ROOT)
        streams, services = [], []
        try:
            for name, command in (
                ("embedding", [sys.executable, str(ROOT / "shinka/embedding_server.py"),
                               "--log", str(args.results_dir / "embedding_calls.jsonl")]),
                ("webui", [str(Path(sys.executable).parent / "shinka_visualize"),
                           str(args.results_dir), "--port", str(args.webui_port)]),
            ):
                stream = (args.results_dir / f"{name}.log").open("a")
                streams.append(stream)
                service = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                services.append(service)
                (args.results_dir / f"{name}.pid").write_text(str(service.pid) + "\n")
            boundary = f"explicit admission deadline {deadline:.0f}" if deadline is not None else "continuing campaign; publication checkpoints do not stop admission"
            print(f"Native WebUI: http://localhost:{args.webui_port}; {boundary}", flush=True)
            runner = ShinkaEvolveRunner(evo_config=evolution, db_config=db, job_config=job,
                                        **config["runner"], verbose=True)
            runner.run()
        finally:
            # Numerical jobs are drained/checkpointed by the native runner. Only
            # this launcher's visualization/embedding services are stopped here.
            for service in services:
                if service.poll() is None:
                    service.terminate()
                    service.wait(timeout=10)
            for stream in streams:
                stream.close()
    return 75 if deadline is not None and time.time() >= deadline else 0


def positive_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def terminate_owned_tree(process: subprocess.Popen, grace_seconds: float) -> None:
    """Terminate this invocation's descendants, including separate R sessions."""
    import psutil
    if process.poll() is not None:
        return
    try:
        parent = psutil.Process(process.pid)
        descendants = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    for child in reversed(descendants):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    try:
        parent.send_signal(signal.SIGINT)
    except psutil.NoSuchProcess:
        pass
    _, alive = psutil.wait_procs([*descendants, parent], timeout=grace_seconds)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    process.wait(timeout=10)


def supervise_native(command: list[str], folder: Path, budget: float,
                     cleanup_grace: float, heartbeat: float) -> int:
    """Bound native execution time without controlling evolution or scoring."""
    state_path = folder / "campaign_process.json"
    with (folder / "campaign_supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(state_path.read_text()) if state_path.exists() else {
            "budget_seconds": budget, "accumulated_walltime_seconds": 0.0, "invocations": []}
        if state["budget_seconds"] != budget:
            raise RuntimeError("Changing the cumulative campaign budget requires a newly versioned campaign directory")
        if state.get("status") == "running":
            raise RuntimeError("Previous supervisor did not record a clean stop; inspect its PID/logs before resuming")
        consumed = float(state["accumulated_walltime_seconds"])
        if consumed >= budget:
            print("Native campaign walltime budget exhausted; no additional calls launched")
            return 75
        invocation = {"command": command, "started_unix": time.time(), "status": "running"}
        state["invocations"].append(invocation)
        started = time.monotonic()
        with (folder / "campaign.stdout.log").open("a") as stdout, (folder / "campaign.stderr.log").open("a") as stderr:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
            invocation["pid"] = process.pid
            state.update(status="running", native_worker_pid=process.pid)
            write_json(state_path, state)
            old_handler = signal.getsignal(signal.SIGTERM)
            def interrupted(signum, frame):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, interrupted)
            try:
                while True:
                    remaining = budget - consumed - (time.monotonic() - started)
                    if remaining <= 0:
                        invocation["status"] = "campaign_walltime_exhausted"
                        invocation["interrupted_evaluation_is_invalid"] = True
                        terminate_owned_tree(process, cleanup_grace)
                        returncode = 75
                        break
                    try:
                        returncode = process.wait(timeout=min(heartbeat, remaining))
                        invocation["status"] = "native_runner_exited" if returncode == 0 else "native_runner_failed"
                        break
                    except subprocess.TimeoutExpired:
                        state["accumulated_walltime_seconds"] = consumed + time.monotonic() - started
                        write_json(state_path, state)
            except KeyboardInterrupt:
                invocation["status"] = "interrupted"
                invocation["interrupted_evaluation_is_invalid"] = True
                terminate_owned_tree(process, cleanup_grace)
                returncode = 130
            finally:
                signal.signal(signal.SIGTERM, old_handler)
                elapsed = time.monotonic() - started
                invocation.update(elapsed_seconds=elapsed, stopped_unix=time.time(),
                                  native_exit_code=process.returncode)
                state.update(status=invocation["status"], accumulated_walltime_seconds=consumed + elapsed,
                             native_worker_pid=None, cleanup_grace_seconds=cleanup_grace)
                write_json(state_path, state)
        return returncode


def evaluation_timeout(config: dict, ready: dict, problems: list[str]) -> tuple[str | None, dict]:
    policy = config["evaluation_timeout"]
    settings_path = ROOT / policy["scientific_settings_path"]
    settings = json.loads(settings_path.read_text())
    seconds = ready.get(policy["readiness_seconds_field"])
    margin = ready.get(policy["readiness_margin_field"])
    annual_cap = (settings["estimation"]["timeout_seconds"] * settings["estimation"]["max_attempts"]
                  + settings["forecast"]["timeout_seconds"] + policy["annual_scoring_timeout_seconds"])
    scientific_cap = len(settings["development_years"]) * annual_cap
    summary = {"scientific_upper_bound_seconds": scientific_cap, "annual_upper_bound_seconds": annual_cap,
               "requested_timeout_seconds": seconds, "requested_margin_seconds": margin,
               "basis": "four uncached candidate years; all development baselines must already be cached",
               "settings_sha256": hashlib.sha256(settings_path.read_bytes()).hexdigest()}
    if not positive_number(seconds) or int(seconds) != seconds:
        problems.append(f"positive integer {policy['readiness_seconds_field']} is required")
    if not positive_number(margin):
        problems.append(f"positive {policy['readiness_margin_field']} is required")
    if positive_number(seconds) and positive_number(margin) and seconds < scientific_cap + margin:
        problems.append("native evaluation timeout is shorter than the full scientific upper bound plus declared margin")
    if ready.get("evaluator_settings_sha256") != summary["settings_sha256"]:
        problems.append("readiness evaluator_settings_sha256 must match current frozen scientific settings")
    if not positive_number(seconds) or int(seconds) != seconds:
        return None, summary
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}", summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "shinka/native_config.json")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "runs/evolution_native")
    parser.add_argument("--initial", type=Path, default=ROOT / "candidates/initial.py")
    parser.add_argument("--webui-port", type=int, default=8899)
    parser.add_argument("--window-hours", type=float, help="Optional explicit admission window; omitted for the continuing multiobjective campaign")
    parser.add_argument("--execute", action="store_true", help="Launch only after all measured scientific gates pass")
    parser.add_argument("--native-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--supervisor-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    args.results_dir = args.results_dir.resolve()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    if config.get("protocol") == "multiobjective-v1":
        return run_multiobjective(args, config)
    if args.supervisor_only:
        # Re-execution discards heavy scientific imports from preflight. Keep a
        # lightweight supervisor alongside the one native worker on this host.
        ready = json.loads((ROOT / config["readiness_manifest"]).read_text())
        budget = ready.get("campaign_walltime_budget_seconds")
        if not positive_number(budget):
            raise RuntimeError("A finite positive campaign budget is required")
        command = [sys.executable, str(Path(__file__).resolve()),
                   "--config", str(args.config.resolve()), "--results-dir", str(args.results_dir),
                   "--initial", str(args.initial.resolve()), "--webui-port", str(args.webui_port),
                   "--execute", "--native-worker"]
        return supervise_native(command, args.results_dir, budget,
                                 config["campaign_supervisor"]["cleanup_grace_seconds"],
                                 config["campaign_supervisor"]["heartbeat_seconds"])
    os.environ["SHINKA_PRICING_MODE"] = "offline"
    os.environ["SHINKA_HEADLESS_COMMAND"] = f"{sys.executable} {ROOT / 'shinka/headless_isolated.py'}"
    os.environ["SHINKA_HEADLESS_TIMEOUT"] = "1800"
    # Prevent dotenv loading from reintroducing an API-key route on import.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for name in list(os.environ):
        if name.endswith("API_KEY") or name in {"OPENAI_ACCESS_TOKEN", "ANTHROPIC_AUTH_TOKEN"}:
            os.environ.pop(name, None)
    from shinka.core import EvolutionConfig, ShinkaEvolveRunner
    from shinka.database import DatabaseConfig
    from shinka.launch import LocalJobConfig
    from shinka.llm.providers.headless import parse_headless_model

    evo = config["evolution"].copy()
    problems = []
    security_path = ROOT / config["infrastructure_readiness_manifest"]
    security = json.loads(security_path.read_text()) if security_path.exists() else {}
    if security.get("mutation_network_isolation_verified") is not True:
        problems.append("mutation_network_isolation_verified: host network/loopback access remains unresolved")
    security_bindings = security.get("bound_files_sha256", {})
    if not security_bindings:
        problems.append("infrastructure review must bind its inspected implementation files")
    for name, expected in security_bindings.items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            problems.append(f"infrastructure security review is stale for {name}")
    for key in ["llm_models", "meta_llm_models", "novelty_llm_models", "prompt_llm_models"]:
        for model in evo.get(key, []):
            if not model.startswith("headless/codex@"):
                raise ValueError(f"Unauthorized paid/non-Codex route in {key}: {model}")
            parse_headless_model(model)
    if not evo["embedding_model"].startswith("local/") or "@http://127.0.0.1:" not in evo["embedding_model"]:
        raise ValueError("Embedding endpoint must be local loopback")
    public_workdir = ROOT / "runs/public_mutation" / args.results_dir.name
    public_workdir.mkdir(parents=True, exist_ok=True)
    for key in ["llm_kwargs", "meta_llm_kwargs", "novelty_llm_kwargs", "prompt_llm_kwargs"]:
        evo[key] = {**evo.get(key, {}), "headless_work_dir": str(public_workdir)}
    task_context = (ROOT / "shinka/task_prompt.md").read_text()
    catalog = ROOT / "configs/effect-catalog-v1.json"
    if catalog.exists():
        task_context += "\n\n# Allowed schema and executable effect catalog\n" + catalog.read_text()
    else:
        problems.append("Executable effect catalog is missing")
    evo.update(task_sys_msg=task_context,
               init_program_path=str(args.initial.resolve()), results_dir=str(args.results_dir))
    readiness_path = ROOT / config["readiness_manifest"]
    ready = json.loads(readiness_path.read_text()) if readiness_path.exists() else {}
    for check in config["required_readiness_checks"]:
        if ready.get(check) is not True:
            problems.append(check)
    estimate_seconds = ready.get("measured_seconds_per_candidate")
    budget_seconds = ready.get("campaign_walltime_budget_seconds")
    if not positive_number(estimate_seconds):
        problems.append("positive measured_seconds_per_candidate is required")
    if not positive_number(budget_seconds):
        problems.append("positive campaign_walltime_budget_seconds is required")
    if not args.initial.exists():
        problems.append(f"initial candidate missing: {args.initial}")
    if positive_number(estimate_seconds) and positive_number(budget_seconds):
        if evo["num_generations"] * estimate_seconds > budget_seconds:
            problems.append("configured generation count exceeds measured walltime budget")
    native_timeout, timeout_summary = evaluation_timeout(config, ready, problems)
    job_values = {**config["job"], "time": native_timeout}
    job = LocalJobConfig(eval_program_path=str(ROOT / "evaluate.py"),
                         python_executable=sys.executable, **job_values)
    db = DatabaseConfig(db_path=str(args.results_dir / "evolution_db.sqlite"), **config["database"])
    evolution = EvolutionConfig(**evo)
    resolved = {"evolution": dataclasses.asdict(evolution), "database": dataclasses.asdict(db),
                "job": dataclasses.asdict(job), "runner": config["runner"],
                "scientific_readiness": ready, "unmet_gates": problems,
                "infrastructure_readiness": security,
                "evaluation_timeout_policy": timeout_summary,
                "campaign_supervisor": config["campaign_supervisor"],
                "upstream_commit": config["upstream_commit"],
                "adapter_patch_sha256": hashlib.sha256((ROOT / "shinka/patches/astra-ultra-and-no-web.patch").read_bytes()).hexdigest(),
                "process_cleanup_patch_sha256": hashlib.sha256((ROOT / "shinka/patches/local-evaluation-process-tree.patch").read_bytes()).hexdigest(),
                "subscription_only": True, "multimodel_bandit": len(evo["llm_models"]) > 1}
    output = args.results_dir / "resolved_config.json"
    output.write_text(json.dumps(resolved, indent=2) + "\n")
    print(json.dumps({"resolved_config": str(output), "unmet_gates": problems}, indent=2), flush=True)
    if not args.execute:
        return 0
    if problems:
        raise RuntimeError("Evolution is blocked by scientific readiness gates; see resolved_config.json")
    if not args.native_worker:
        command = [sys.executable, str(Path(__file__).resolve()),
                   "--config", str(args.config.resolve()), "--results-dir", str(args.results_dir),
                   "--initial", str(args.initial.resolve()), "--webui-port", str(args.webui_port),
                   "--execute", "--supervisor-only"]
        os.execv(sys.executable, command)
    os.chdir(ROOT)
    subprocess.run([sys.executable, str(ROOT / "shinka/headless_isolated.py"), "--self-check"], check=True)
    with urllib.request.urlopen("http://127.0.0.1:8766/health", timeout=5) as response:
        embedding_health = json.load(response)
    if embedding_health.get("revision") != "bf8b056651a2c21b8d2565580b8569da283cab23":
        raise RuntimeError("Wrong local embedding model revision")
    # Keep native WebUI alive for the full run. This is not a replacement dashboard.
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", args.webui_port))
    webui_log = (args.results_dir / "webui.log").open("a")
    webui = subprocess.Popen([str(Path(sys.executable).parent / "shinka_visualize"),
        str(args.results_dir), "--port", str(args.webui_port)], stdout=webui_log, stderr=subprocess.STDOUT)
    (args.results_dir / "webui.pid").write_text(str(webui.pid) + "\n")
    print(f"Native WebUI: http://localhost:{args.webui_port}")
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{args.webui_port}/", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if webui.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Native WebUI failed to become reachable; see webui.log")
                time.sleep(0.5)
        runner = ShinkaEvolveRunner(evo_config=evolution, db_config=db, job_config=job,
                                    **config["runner"], verbose=True)
        runner.run()
    finally:
        webui.terminate()
        webui.wait(timeout=10)
        webui_log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
