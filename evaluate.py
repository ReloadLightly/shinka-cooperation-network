#!/usr/bin/env python3
"""Fixed trusted predictive fitness for native ShinkaEvolve.

Candidates specify RSiena network structure; they never implement the metric.
Native invocation: evaluate.py --protocol PROTOCOL --program_path PROGRAM --results_dir DIRECTORY.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import signal
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from scripts.specification import read_program, spec_hash, canonical_bytes
from scripts.resources import scientific_execution

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "configs/evaluator-v2.json"
BASELINE = ROOT / "candidates/initial.py"
CACHE = ROOT / "results/cache"


def read_json(path):
    return json.loads(Path(path).read_text())


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(spec, year, settings):
    # Target outcomes are deliberately absent from the prediction cache identity.
    # They are hashed separately for scoring after prediction has been published.
    files = [ROOT/"R/empirical.R", ROOT/"R/forecast.R", ROOT/"R/audit_data.R",
             ROOT/"configs/effect-catalog-v1.json", ROOT/"environment/versions.json",
             ROOT/"environment/conda-linux-64.explicit.txt", ROOT/"sources/manifest.json",
             ROOT/f"data/past/{year}.rds"]
    value = {"specification": spec, "target": year, "training": [1990, year-1],
             "settings": settings, "files": {str(p.relative_to(ROOT)): sha(p) for p in files}}
    key = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return key, value


def run_r(arguments, folder, stage, timeout):
    with scientific_execution():
        return _run_r_locked(arguments,folder,stage,timeout)


def stop_process_group(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def _run_r_locked(arguments, folder, stage, timeout):
    folder.mkdir(parents=True, exist_ok=True)
    cmd = [str(ROOT/"environment/run-r"), *map(str, arguments)]
    invocation = str(time.time_ns())
    resources = folder/f"{stage}.resources-{invocation}.txt"
    previous_resources = folder/f"{stage}.resources.txt"
    if previous_resources.exists():
        preserved = folder/f"{stage}.resources-preserved-{previous_resources.stat().st_mtime_ns}.txt"
        if not preserved.exists():
            shutil.copy2(previous_resources,preserved)
    event = {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "stage": stage, "command": cmd,
             "invocation_id": invocation,"resources_file": str(resources)}
    start = time.monotonic()
    with (folder/f"{stage}.stdout.log").open("a") as stdout, (folder/f"{stage}.stderr.log").open("a") as stderr:
        process = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(resources), *cmd],
                                   cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        event.update(pid=process.pid,status="running")
        save_json(folder/"process.json",event)
        with (folder/"events.jsonl").open("a") as log:
            log.write(json.dumps(event)+"\n")
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_process_group(process)
            event.update(status="timeout",elapsed_seconds=time.monotonic()-start)
            if resources.exists():
                shutil.copy2(resources,previous_resources)
            save_json(folder/"process.json",event)
            with (folder/"events.jsonl").open("a") as log:
                log.write(json.dumps(event)+"\n")
            raise RuntimeError(f"{stage} exceeded its fixed {timeout}s budget; process group stopped, diagnostics preserved at {folder}")
        except BaseException as exc:
            # Release the shared memory lock only after our child R group stops.
            # This also covers an interactive Ctrl-C while waiting on a fit.
            stop_process_group(process)
            event.update(status="interrupted",elapsed_seconds=time.monotonic()-start,
                         error=type(exc).__name__,exit_code=process.returncode)
            if resources.exists():
                shutil.copy2(resources,previous_resources)
            save_json(folder/"process.json",event)
            with (folder/"events.jsonl").open("a") as log:
                log.write(json.dumps(event)+"\n")
            raise
    if resources.exists():
        shutil.copy2(resources,previous_resources)
    event.update(elapsed_seconds=time.monotonic()-start, exit_code=returncode,
                 status="completed" if returncode==0 else "failed")
    save_json(folder/"process.json",event)
    with (folder/"events.jsonl").open("a") as log:
        log.write(json.dumps(event)+"\n")
    if returncode:
        tail = (folder/f"{stage}.stderr.log").read_text()[-2500:]
        raise RuntimeError(f"{stage} failed (exit {returncode}); diagnostics: {folder}. {tail}")


def forecast_year(spec, year, settings):
    # Acquire the shared memory-resource lock BEFORE a cache lock so concurrent
    # baseline/candidate workflows cannot deadlock with opposite lock ordering.
    with scientific_execution():
        return _forecast_year_locked(spec,year,settings)


def _forecast_year_locked(spec, year, settings):
    if year not in settings["development_years"]:
        raise ValueError("Evolution evaluator cannot access the reserved final year.")
    key, provenance = identity(spec, year, settings)
    folder = CACHE/key
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/"evaluation.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        save_json(folder/"provenance.json", provenance)
        save_json(folder/"specification.json", spec)
        save_json(folder/"settings.json", settings)
        if not ((folder/"predictions.rds").exists() and (folder/"forecast_audit.json").exists()):
            run_r([ROOT/"R/forecast.R", "--spec", folder/"specification.json",
                   "--target", year, "--output", folder, "--settings", folder/"settings.json"],
                  folder, "fit_and_forecast",
                  settings["estimation"]["timeout_seconds"]*settings["estimation"]["max_attempts"]
                  + settings["forecast"]["timeout_seconds"])
        if not (folder/"forecast_audit.json").exists():
            raise RuntimeError("Incomplete forecast publication: predictions exist without native forecast audit.")
        audit = read_json(folder/"forecast_audit.json")
        if audit["returned_simulations"] != settings["forecast"]["simulations"] or audit["target_outcomes_accessed"] is not False:
            raise RuntimeError("Invalid endpoint count or target-access audit.")
        # Prediction hash/timestamp are committed before labels are opened below.
        commitment = {"sha256": sha(folder/"predictions.rds"), "target": year}
        commit_path = folder/"prediction_commit.json"
        if commit_path.exists():
            previous = read_json(commit_path)
            if any(previous.get(k) != v for k,v in commitment.items()):
                raise RuntimeError("Published predictions changed after commitment; do not silently rescore.")
        else:
            save_json(commit_path, {**commitment,"committed_utc":dt.datetime.now(dt.timezone.utc).isoformat()})
        target = ROOT/f"data/targets/{year}.rds"
        scoring_identity = {"predictions": sha(folder/"predictions.rds"), "target": sha(target),
                            "scorer": sha(ROOT/"R/score.R"), "PRROC": settings["software"]["PRROC"]}
        if not (folder/"scores.json").exists() or not (folder/"score_provenance.json").exists() or read_json(folder/"score_provenance.json") != scoring_identity:
            run_r([ROOT/"R/score.R", folder/"predictions.rds", target, folder], folder,"score",300)
            save_json(folder/"score_provenance.json", scoring_identity)
        result = read_json(folder/"scores.json")
        auc = result["primary"]["pr_auc"]
        if not isinstance(auc, (float,int)) or not math.isfinite(auc) or not 0 <= auc <= 1:
            raise ValueError("Nonfinite/out-of-range PRROC result.")
        result["cache_directory"] = str(folder)
        result["fit_diagnostics"] = read_json(folder/"fit_diagnostics.json")
        return result


def preflight():
    required = {ROOT/"results/audits/source_parity.json": "passed",
                ROOT/"results/audits/forward_verification.json": "passed"}
    for path, field in required.items():
        if not path.exists() or read_json(path).get(field) is not True:
            raise RuntimeError(f"Scientific launch gate incomplete: {path.relative_to(ROOT)} must report {field}=true.")
        for name, expected in read_json(path).get("bound_file_md5", {}).items():
            actual = hashlib.md5((ROOT/name).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Scientific audit is stale for {name}; rerun {path.name}.")
    checks = ROOT/"results/verification/metric_checks.json"
    if not checks.exists() or read_json(checks).get("status") != "passed":
        raise RuntimeError("Pinned PRROC metric checks have not passed.")


def evaluate(program_path, results_dir):
    out = Path(results_dir).resolve()
    # The native results directory may contain candidate code; only publish
    # development metrics here, never fits, target labels or final-year artifacts.
    out.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    try:
        spec, source = read_program(program_path)
        # Reuse the completed source/metric work. The revised fitting schedule
        # is judged by native scientific diagnostics below, without rerunning
        # the earlier audit campaign or its source-hash readiness gate.
        settings = read_json(SETTINGS)
        baseline_spec, _ = read_program(BASELINE)
        annual = {}
        for year in settings["development_years"]:
            baseline = forecast_year(baseline_spec, year, settings)
            candidate = forecast_year(spec, year, settings)
            # A common mask must be byte-identical, independently of predictions.
            if sha(Path(baseline["cache_directory"])/"eligibility_mask.rds") != sha(Path(candidate["cache_directory"])/"eligibility_mask.rds"):
                raise RuntimeError(f"Eligibility mask mismatch for target {year}.")
            delta = candidate["primary"]["pr_auc"] - baseline["primary"]["pr_auc"]
            annual[str(year)] = {"pr_auc": candidate["primary"]["pr_auc"],
                                "baseline_pr_auc": baseline["primary"]["pr_auc"], "delta": delta,
                                "candidate": candidate, "baseline": baseline}
        if len(annual) != 4:
            raise RuntimeError("A valid candidate requires all four development years.")
        fitness = math.fsum(x["delta"] for x in annual.values())/4
        score = settings["fitness"]["combined_score_offset"] + fitness
        if not math.isfinite(fitness) or not math.isfinite(score):
            raise RuntimeError("Nonfinite fitness is invalid.")
        baseline_terms = set(baseline_spec["network_effects"])
        terms = set(spec["network_effects"])
        changes = f"Added {sorted(terms-baseline_terms)}; removed {sorted(baseline_terms-terms)}."
        feedback = (f"{changes} Raw F={fitness:+.12f}; combined_score=1+F={score:.12f}. "
                    + " ".join(f"{year}: PR-AUC={x['pr_auc']:.12f}, baseline={x['baseline_pr_auc']:.12f}, delta={x['delta']:+.12f}." for year,x in annual.items())
                    + " All years passed fixed estimation and forecast checks. Monte Carlo sensitivity has not yet been assessed with fresh seeds; dependent dyads are not independent replicates. No final-year outcomes were scored.")
        public = {"raw_F": fitness, "years": annual, "complexity": len(terms),
                  "canonical_specification": spec, "canonical_sha256": spec_hash(spec),
                  "runtime_seconds": time.monotonic()-start}
        # Absolute private artifact paths are not useful mutation inspirations.
        private = {"artifacts": {y:{role:annual[y][role].pop("cache_directory") for role in ("candidate","baseline")} for y in annual}}
        save_json(out/"metrics.json", {"combined_score": score, "public": public,
                                      "private": private, "text_feedback": feedback})
        save_json(out/"correct.json", {"correct": True, "error": ""})
        save_json(out/"canonical_specification.json", spec)
        archive = ROOT/"results/evaluations"/spec_hash(spec)
        archive.mkdir(parents=True,exist_ok=True)
        (archive/"candidate.py").write_text(source)
        for name in ("metrics.json","correct.json","canonical_specification.json"):
            shutil.copy2(out/name,archive/name)
        return 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        # No numeric surrogate: estimation failure is not negative improvement.
        save_json(out/"metrics.json", {"combined_score": None,
                  "public": {"valid": False, "raw_F": None, "runtime_seconds": time.monotonic()-start},
                  "private": {}, "text_feedback": "INVALID evaluation; no scientific fitness. "+error})
        save_json(out/"correct.json", {"correct": False, "error": error})
        (out/"error.log").write_text(traceback.format_exc())
        print(error, file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Require deliberate protocol choice before any evaluator can do work."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True, type=Path)
    parser.add_argument("--results_dir", required=True, type=Path)
    parser.add_argument("--protocol", choices=("pr-only-v2", "multiobjective-v1"), required=True,
                        help="Required: multiobjective-v1 is current; pr-only-v2 explicitly selects the legacy evaluator.")
    options = parser.parse_args(argv)
    if options.protocol == "multiobjective-v1":
        from scripts.multiobjective_evaluation import evaluate as evaluate_multiobjective
        return evaluate_multiobjective(options.program_path, options.results_dir)
    return evaluate(options.program_path, options.results_dir)


if __name__ == "__main__":
    raise SystemExit(main())
