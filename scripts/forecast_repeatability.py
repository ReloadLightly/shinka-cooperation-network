#!/usr/bin/env python3
"""Bounded fixed-fit reference repeatability; independent of finalist selection.

check is read-only. export-inputs copies exactly eight validated development
packets. run --execute admits at most twenty new forecast batches and never
refits or prepares data from the mixed-year archive. Missing inputs fail closed.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import shutil
import statistics
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import evaluate as native
from scripts.network_specification_v2 import read_program, validate_spec
from scripts.scientific_contract import immutable_json
from scripts.resources import scientific_execution

YEARS = (2006, 2007, 2008, 2009)
OFFSETS = (101, 102, 103, 104, 105)
METRICS = {"pr_auc": ("primary", "pr_auc"), "brier": ("primary", "brier"),
           "spending_rmse": ("spending", "rmse"),
           "formation_pr_auc": ("formation", "pr_auc"),
           "dissolution_pr_auc": ("dissolution", "pr_auc")}
BOUND_SOURCES = ("R/empirical.R", "R/forecast.R", "R/score.R",
                 "R/forecast_repeatability.R", "scripts/forecast_repeatability.py",
                 "configs/forecast-repeatability-v1.json", "environment/versions.json",
                 "environment/conda-linux-64.explicit.txt", "evaluate.py",
                 "scripts/resources.py", "scripts/scientific_contract.py",
                 "scripts/network_specification_v2.py", "configs/effect-catalog-v2.json",
                 "configs/evaluator-v2.json", "candidates/initial_multiobjective.py")
INPUT_RECORDS = ("accepted_fit.rds", "fit_diagnostics.json", "predictions.rds",
                 "prediction_commit.json", "forecast_audit.json", "scores.json",
                 "score_provenance.json", "eligibility_mask.rds", "provenance.json",
                 "settings.json", "specification.json", "forecast_effects.csv")
BATCH_RECORDS = ("accepted_fit.rds", "fit_diagnostics.json", "predictions.rds",
                 "simulations.rds", "forecast_audit.json", "fixed_coefficient_audit.json",
                 "scores.json", "eligibility_mask.rds", "settings.json", "specification.json", "prediction_commit.json")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def metric_values(scores):
    values = {name: scores[group][key] for name,(group,key) in METRICS.items()}
    for name,value in values.items():
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError(f"Unavailable or nonfinite diagnostic metric: {name}")
    return values


def packet_paths():
    return [f"data/{kind}/{year}.rds" for year in YEARS for kind in ("past","targets")]


def inspect_inputs(root=ROOT):
    """Bind the published baseline caches without opening any reserved packet."""
    root = Path(root)
    policy = read(root / "configs/forecast-repeatability-v1.json")
    if (policy["targets"] != list(YEARS) or policy["seed_offsets"] != list(OFFSETS)
        or policy["simulations_per_batch"] != 1000 or policy["maximum_new_batches"] != 20
        or policy["refitting_allowed"] is not False or policy["finalist_selection"] is not False):
        raise ValueError("The bounded repeatability design changed; declare a separate study")
    manifest = read(root / "results/evolution_manifest.json")
    reference, _ = read_program(root / "candidates/initial_multiobjective.py")
    settings = read(root / "configs/evaluator-v2.json")
    records, missing, packets = {}, [], {}
    for year in YEARS:
        relative = manifest["baseline_years"][str(year)]["cache_directory"]
        folder = (root / relative).resolve()
        folder.relative_to((root / "results/cache").resolve())
        saved_settings, spec = read(folder/"settings.json"),read(folder/"specification.json")
        if saved_settings != settings or validate_spec(spec) != reference:
            raise ValueError(f"Reference settings/specification differ for {year}")
        diagnostics = read(folder/"fit_diagnostics.json")
        scores, audit = read(folder/"scores.json"), read(folder/"forecast_audit.json")
        if (not diagnostics or diagnostics[-1].get("valid") is not True
            or scores.get("target") != year or scores.get("seed") != year*1000+1
            or scores.get("simulations") != 1000 or audit.get("returned_simulations") != 1000
            or audit.get("target_outcomes_accessed") is not False):
            raise ValueError(f"No accepted published reference for {year}")
        commitment = read(folder/"prediction_commit.json")
        if commitment.get("sha256") != sha(folder/"predictions.rds"):
            raise ValueError(f"Published prediction commitment changed for {year}")
        score_identity = read(folder/"score_provenance.json")
        if (score_identity.get("predictions") != commitment["sha256"]
            or score_identity.get("scorer") != sha(root/"R/score.R")
            or score_identity.get("PRROC") != "1.3.1"):
            raise ValueError(f"Published score provenance differs for {year}")
        provenance = read(folder/"provenance.json")
        for name in ("R/empirical.R", "R/forecast.R"):
            if provenance["files"].get(name) != sha(root/name):
                raise ValueError(f"Published reference adapter changed: {name}")
        past = f"data/past/{year}.rds"; target = f"data/targets/{year}.rds"
        expected = {past: provenance["files"][past],
                    target: score_identity["target"]}
        for name,value in expected.items():
            packets[name] = value
            if not (root/name).is_file():
                missing.append({"path": name, "expected_sha256": value})
            elif sha(root/name) != value:
                raise ValueError(f"Input packet differs from the published baseline: {name}")
        records[str(year)] = {"folder": relative, "specification": spec,
            "metrics": metric_values(scores),
            "spending_countries": scores["spending"]["n"],
            "evidence": {name: sha(folder/name) for name in INPUT_RECORDS}}
    return {"version": policy["version"], "ready": not missing, "missing_inputs": missing,
            "policy": policy, "settings": settings, "reference": records, "packets": packets,
            "implementation": {name: sha(root/name) for name in BOUND_SOURCES}}


def require_ready(plan):
    if not plan["ready"]:
        raise FileNotFoundError("Missing published development packets: " +
                                ", ".join(item["path"] for item in plan["missing_inputs"]))


def export_inputs(output, root=ROOT):
    plan = inspect_inputs(root); require_ready(plan)
    output = Path(output)
    if output.exists():
        raise FileExistsError("Input export already exists; it will not be overwritten")
    # Exactly these files: no glob, raw archive, runtime, credentials or reserved year.
    with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED) as archive:
        for name in packet_paths():
            archive.write(Path(root)/name,name)
    return {"path": str(output),"sha256":sha(output),"files":plan["packets"]}


def distribution(values):
    if not values or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError("Finite diagnostic values are required")
    return {"n":len(values),"mean":statistics.mean(values),
            "sample_sd":statistics.stdev(values) if len(values)>1 else None,
            "minimum":min(values),"maximum":max(values),"range":max(values)-min(values)}


def summarize(rows, reference):
    """Only fresh batches estimate variability; primary reference stays fixed."""
    seen = set()
    for row in rows:
        key = (row["year"],row["offset"])
        if key in seen or key[0] not in YEARS or key[1] not in OFFSETS:
            raise ValueError("Duplicate or undeclared repeatability cell")
        seen.add(key)
    annual = {}
    for year in YEARS:
        selected = [r for r in rows if r["year"]==year]
        if selected:
            annual[str(year)] = {k:{**distribution([r["metrics"][k] for r in selected]),
                                    "published_reference":reference[str(year)]["metrics"][k]}
                                 for k in METRICS}
    groups = []
    for offset in OFFSETS:
        group = {r["year"]:r for r in rows if r["offset"]==offset}
        if set(group)==set(YEARS):
            means = {k:math.fsum(group[y]["metrics"][k] for y in YEARS)/4 for k in METRICS}
            contrast = {"pr_auc":1,"brier":-1,"spending_rmse":-1}
            deltas = {k:sign*(means[k]-math.fsum(reference[str(y)]["metrics"][k] for y in YEARS)/4)
                      for k,sign in contrast.items()}
            groups.append({"offset":offset,"four_year_means":means,
                           "same_model_signed_differences_from_published":deltas})
    return {"status":"complete" if len(rows)==20 else "partial", "completed_batches":len(rows),
        "planned_batches":20,"annual":annual,"complete_four_year_repetitions":groups,
        "four_year_mean_variability":{k:distribution([g["four_year_means"][k] for g in groups])
                                      for k in METRICS} if groups else {},
        "interpretation":"Conditional forecast Monte Carlo variability for fixed accepted reference coefficients. Five repetitions give a rough SD estimate. Differences from the original finite-simulation reference are NOT candidate improvements. No refitting variance, generalization uncertainty, signal-to-noise ratio or evolutionary fitness is established.",
        "aggregation":"Score each batch after averaging its 1000 endpoints. Means of batch metrics are not scores of pooled-endpoint probabilities."}


def verify_batch(folder, plan, year, offset):
    record = read(folder/"batch_commit.json")
    if (record["plan_sha256"] != digest(plan) or record["year"]!=year or record["offset"]!=offset):
        raise ValueError("Batch belongs to different declared inputs or seed")
    if set(record["artifacts"]) != set(BATCH_RECORDS):
        raise ValueError("Batch commitment has incomplete artifacts")
    for name,value in record["artifacts"].items():
        if sha(folder/name) != value:
            raise ValueError("Committed batch changed; do not silently regenerate: "+name)
    if record["artifacts"]["accepted_fit.rds"] != plan["reference"][str(year)]["evidence"]["accepted_fit.rds"]:
        raise ValueError("Accepted coefficients changed")
    scores = read(folder/"scores.json")
    if (scores.get("target")!=year or scores.get("seed")!=year*1000+offset or scores.get("simulations")!=1000):
        raise ValueError("Scored batch target, seed or endpoint budget changed")
    if scores["spending"]["n"]!=plan["reference"][str(year)]["spending_countries"]:
        raise ValueError("Spending comparison count changed")
    if record["artifacts"]["eligibility_mask.rds"]!=plan["reference"][str(year)]["evidence"]["eligibility_mask.rds"]:
        raise ValueError("Eligibility mask changed")
    audit = read(folder/"forecast_audit.json")
    if audit.get("seed")!=year*1000+offset or audit.get("returned_simulations")!=1000 or audit.get("target_outcomes_accessed") is not False:
        raise ValueError("Native endpoint/seed/outcome-access audit differs")
    fixed = read(folder/"fixed_coefficient_audit.json")
    if not all(fixed.get(k) is True for k in ("simOnly","all_coefficients_fixed","coefficients_unchanged","published_forward_coefficients_verified")):
        raise ValueError("Native fixed-coefficient audit incomplete")
    return {"year":year,"offset":offset,"seed":year*1000+offset,"metrics":metric_values(scores)}


def execute(output, max_new_batches=20, *, root=ROOT, runner=None):
    if type(max_new_batches) is not int or not 1<=max_new_batches<=20:
        raise ValueError("--max-new-batches must be an integer in 1..20")
    root=Path(root); output=Path(output).resolve()
    output.relative_to((root/"results/diagnostics").resolve())
    plan=inspect_inputs(root); require_ready(plan)  # Before R or output creation.
    runner=runner or native.run_r
    with scientific_execution():
        immutable_json(output/"plan.json",plan)
        rows=[]; new=0; started=time.monotonic(); stopped=False
        for offset in OFFSETS:
            for year in YEARS:
                folder=output/str(year)/str(offset)
                if (folder/"batch_commit.json").exists():
                    rows.append(verify_batch(folder,plan,year,offset)); continue
                if new>=max_new_batches or time.monotonic()-started>=plan["policy"]["invocation_admission_seconds"]:
                    stopped=True; continue
                if (folder/"batch_state.json").exists():
                    raise RuntimeError("Incomplete started batch requires review; no implicit retry or new seed: "+str(folder))
                folder.mkdir(parents=True,exist_ok=True)
                source=root/plan["reference"][str(year)]["folder"]
                for name in ("accepted_fit.rds","fit_diagnostics.json"):
                    shutil.copy2(source/name,folder/name)
                settings=copy.deepcopy(plan["settings"])
                settings["forecast"]["seed_override"]=year*1000+offset
                immutable_json(folder/"settings.json",settings)
                immutable_json(folder/"specification.json",plan["reference"][str(year)]["specification"])
                native.save_json(folder/"batch_state.json",{"status":"started","started_utc":now()})
                new+=1
                try:
                    runner([root/"R/forecast_repeatability.R",folder/"specification.json",year,folder,
                            folder/"settings.json",root/f"data/past/{year}.rds",source/"forecast_effects.csv"],folder,"forecast",plan["policy"]["batch_timeout_seconds"])
                    if sha(folder/"accepted_fit.rds")!=plan["reference"][str(year)]["evidence"]["accepted_fit.rds"]:
                        raise ValueError("Fit bytes changed during forecast")
                    immutable_json(folder/"prediction_commit.json",{"sha256":sha(folder/"predictions.rds"),
                                    "target":year,"seed":year*1000+offset,"committed_utc":now()})
                    # Open only the matching development outcome packet after commitment.
                    runner([root/"R/score.R",folder/"predictions.rds",root/f"data/targets/{year}.rds",folder],folder,"score",300)
                    commitment={"plan_sha256":digest(plan),"year":year,"offset":offset,
                                "artifacts":{name:sha(folder/name) for name in BATCH_RECORDS}}
                    immutable_json(folder/"batch_commit.json",commitment)
                    rows.append(verify_batch(folder,plan,year,offset))
                    native.save_json(folder/"batch_state.json",{"status":"completed","completed_utc":now()})
                except BaseException as exc:
                    native.save_json(folder/"batch_state.json",{"status":"failed_or_interrupted","error":str(exc),"recorded_utc":now()})
                    raise
        # Recheck all source inputs; no changed originals get blessed in the summary.
        if inspect_inputs(root)!=plan:
            raise ValueError("Published reference/input changed during diagnostic")
        native.save_json(output/"summary.json",summarize(rows,plan["reference"]))
        print(json.dumps({"summary":str(output/"summary.json"),"new_batches":new,
                          "completed_batches":len(rows),"status":"paused" if stopped else "complete"}))
        return 75 if stopped else 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    commands.add_parser("check",help="Read-only input/provenance check; zero R calls")
    export=commands.add_parser("export-inputs",help="Export exactly eight hash-verified development packets")
    export.add_argument("--output",type=Path,required=True)
    run=commands.add_parser("run",help="Execute/resume this diagnostic, never a finalist plan")
    run.add_argument("--execute",action="store_true")
    run.add_argument("--results-dir",type=Path,default=ROOT/"results/diagnostics/forecast-repeatability-v1")
    run.add_argument("--max-new-batches",type=int,default=20)
    args=parser.parse_args(argv)
    if args.command=="check":
        plan=inspect_inputs()
        print(json.dumps(plan,indent=2,allow_nan=False)); return 0 if plan["ready"] else 2
    if args.command=="export-inputs":
        print(json.dumps(export_inputs(args.output),indent=2)); return 0
    if not args.execute:
        print("Dry run; add --execute. No input packets, R jobs or outcome data accessed."); return 0
    return execute(args.results_dir,args.max_new_batches)


if __name__=="__main__":
    raise SystemExit(main())
