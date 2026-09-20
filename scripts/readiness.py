#!/usr/bin/env python3
"""Derive native campaign readiness from executed scientific evidence."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluate import BASELINE, SETTINGS, preflight, read_json, save_json, sha
from scripts.specification import CATALOG, read_program, spec_hash
from scripts.final_test import require_development


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--candidate",type=Path,default=ROOT/"candidates/replace_degree.py")
    parser.add_argument("--campaign-hours",type=float,help="Finite walltime budget fixed using measured full-candidate cost")
    args=parser.parse_args()
    config=read_json(ROOT/"shinka/native_config.json")
    settings=read_json(SETTINGS)
    state={key:False for key in config["required_readiness_checks"]}
    errors={}
    base,_=read_program(BASELINE)
    spec,_=read_program(args.candidate)
    try:
        preflight()
        state.update(bridge_parity_passed=True,metric_correctness_passed=True,target_leakage_passed=True)
    except Exception as exc:
        errors["audits"]=str(exc)
    summary=ROOT/"results/paper_reproduction/abm-full-equilibria/endpoint_summary.json"
    if summary.exists():
        state["source_reference_executed"]=read_json(summary).get("checkpoints",0)>0
    for key, candidate in (("all_development_baselines_valid",base),("structural_candidate_valid",spec)):
        try:
            annual=require_development(candidate,settings)
            if key=="structural_candidate_valid" and candidate==base:
                raise ValueError("A distinct structural candidate must be evaluated before evolution.")
            state[key]=True
            if key=="structural_candidate_valid":
                seconds=0.0
                for row in annual.values():
                    directory=Path(row["cache_directory"])
                    diagnostics=read_json(directory/"fit_diagnostics.json")
                    seconds+=sum(x["elapsed_seconds"] for x in diagnostics)
                    seconds+=read_json(directory/"forecast_audit.json")["elapsed_seconds"]
                if not math.isfinite(seconds) or seconds<=0:
                    raise ValueError("Candidate fitting/simulation cost has not been measured.")
                state["measured_seconds_per_candidate"]=seconds
        except Exception as exc:
            state[key]=False
            errors[key]=str(exc)
    seed_dir=ROOT/"results/evolution_forecast/initial"
    if (seed_dir/"correct.json").exists() and read_json(seed_dir/"correct.json").get("correct") is True:
        metrics=read_json(seed_dir/"metrics.json")["public"]
        tolerance=settings["fitness"]["numerical_tolerance"]
        state["baseline_zero_passed"]=(metrics.get("canonical_sha256")==spec_hash(base)
             and abs(metrics["raw_F"])<=tolerance and set(metrics["years"])==set(map(str,settings["development_years"]))
             and all(abs(x["delta"])<=tolerance for x in metrics["years"].values()))
    reservation=ROOT/"results/final_test/reservation.json"
    state["final_year_reserved"]=not reservation.exists() or read_json(reservation).get("outcomes_accessed") is False
    state["catalog_frozen"]=state["bridge_parity_passed"] and state["target_leakage_passed"]
    state["convergence_policy_frozen"]=state["catalog_frozen"]
    if args.campaign_hours is not None:
        budget=args.campaign_hours*3600
        if not math.isfinite(budget) or budget<=0:
            raise ValueError("Campaign budget must be finite and positive.")
        state["campaign_walltime_budget_seconds"]=budget
        measured=state.get("measured_seconds_per_candidate")
        if measured and measured*config["evolution"]["num_generations"]<=budget:
            state["measured_campaign_budget_fixed"]=True
        else:
            errors["campaign_budget"]="No measured complete candidate or provisional generations exceed the finite budget."
    # Separate scientific timeout ceiling from the finite cumulative campaign
    # walltime; cached-seed EWMA must not silently shorten later evaluations.
    per_year=(settings["estimation"]["max_attempts"]*settings["estimation"]["timeout_seconds"]
              +settings["forecast"]["timeout_seconds"]+300)
    state["native_evaluation_timeout_seconds"]=len(settings["development_years"])*per_year+600
    state["native_evaluation_timeout_margin_seconds"]=600
    state["evaluator_settings_sha256"]=sha(SETTINGS)
    state["protocol_sha256"]=sha(SETTINGS)
    state["catalog_sha256"]=sha(CATALOG)
    state["structural_candidate_sha256"]=spec_hash(spec)
    state["errors"]=errors
    state["ready"]=all(state[x] is True for x in config["required_readiness_checks"])
    output=ROOT/config["readiness_manifest"]
    save_json(output,state)
    print(json.dumps(state,indent=2))
    return 0 if state["ready"] else 2


if __name__=="__main__":
    raise SystemExit(main())
