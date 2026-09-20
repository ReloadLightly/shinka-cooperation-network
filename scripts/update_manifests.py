#!/usr/bin/env python3
"""Refresh evidence-based result manifests; performs no fitting or scoring."""
import datetime as dt
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluate import BASELINE,CACHE,SETTINGS,identity,read_json,save_json
from scripts.specification import read_program


def optional(path):
    return read_json(path) if path.exists() else None


def main():
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    settings=read_json(SETTINGS)
    baseline,_=read_program(BASELINE)
    years={}
    for year in settings["development_years"]:
        key,_=identity(baseline,year,settings);folder=CACHE/key
        diagnostics=optional(folder/"fit_diagnostics.json") or []
        score=optional(folder/"scores.json")
        years[str(year)]={
            "cache_directory":str(folder.relative_to(ROOT)),
            "process":optional(folder/"process.json"),
            "completed_fit_attempts":[{k:x.get(k) for k in
                ("attempt","elapsed_seconds","valid","maximum_absolute_t_ratio","overall_maximum_convergence")}
                for x in diagnostics],
            "accepted_training_fit_present":(folder/"accepted_fit.rds").exists(),
            "forecast_audit":optional(folder/"forecast_audit.json"),
            "baseline_primary_metrics":score.get("primary") if score else None,
        }
    evolution={"updated_utc":stamp,"mode":"evolution_forecast",
        "protocol":str(SETTINGS.relative_to(ROOT)),"baseline_years":years,
        "initial_evaluator_correctness":optional(ROOT/"results/evolution_forecast/initial/correct.json"),
        "initial_evaluator_metrics":optional(ROOT/"results/evolution_forecast/initial/metrics.json"),
        "readiness":optional(ROOT/"runs/evolution_forecast/readiness.json"),
        "native_capability_matrix":"docs/SHINKA_CAPABILITIES.md",
        "baseline_convergence_figure":optional(ROOT/"results/evolution_forecast/convergence/baseline_convergence_manifest.json"),
        "final_test_comparison":optional(ROOT/"results/final_test/comparison.json"),
        "interpretation":"Fit completion is not convergence; partial annual results are not fitness. Refer to validated evaluator metrics for any scientific improvement claim."}
    save_json(ROOT/"results/evolution_manifest.json",evolution)
    reproduction_path=ROOT/"results/reproduction_manifest.json"
    reproduction=read_json(reproduction_path)
    reproduction["updated_utc"]=stamp
    summary=optional(ROOT/"results/paper_reproduction/abm-full-equilibria/endpoint_summary.json")
    reproduction["completed_cell_summary"]=summary
    for number,rate in enumerate((1,5,10,15,20,25),start=1):
        rows=[v for k,v in (summary or {}).get("results",{}).items() if k.startswith(f"call-{number:04d}-")]
        reproduction["coverage"][f"equilibrium_rate_{rate}_cell"]=(
            "complete_original_settings_10_endpoints" if len(rows)==1 and rows[0]["simulations"]==10
            else "local_evidence_missing_or_incomplete")
    reproduction["latest_equilibrium_process"]=optional(ROOT/"results/paper_reproduction/abm-full-equilibria/process.json")
    reproduction["latest_figures_5_7_process"]=optional(ROOT/"results/paper_reproduction/abm-full/process.json")
    figures_summary=optional(ROOT/"results/paper_reproduction/abm-full/endpoint_summary.json")
    reproduction["figures_5_7_completed_cell_summary"]=figures_summary
    figures_calls=(ROOT/"results/paper_reproduction/abm-full/calls.jsonl")
    import json
    completed=[json.loads(line) for line in figures_calls.read_text().splitlines()
               if line.strip() and json.loads(line).get("status")=="completed"] if figures_calls.exists() else []
    reproduction["figures_5_7_completed_native_calls"]=completed
    first_cell=[item for key,item in (figures_summary or {}).get("results",{}).items()
                if key.startswith("call-0001-")]
    reproduction["coverage"]["figure_5_first_cell"]=(
        "complete_original_settings_26_returned_endpoints_from_n3_25_two_workers"
        if len(first_cell)==1 and first_cell[0]["simulations"]==26
        else "local_evidence_missing_or_incomplete")
    reproduction["figures_5_7_completed_settings"]=(figures_summary or {}).get("checkpoints",0)
    reproduction["figures_5_7_full_settings"]=564
    reproduction["equilibrium_completed_settings"]=(summary or {}).get("checkpoints",0)
    reproduction["equilibrium_full_settings"]=101
    reproduction["partial_equilibrium_figure"]="results/paper_reproduction/abm-full-equilibria/partial_equilibrium.pdf"
    save_json(reproduction_path,reproduction)
    print("Updated results/reproduction_manifest.json and results/evolution_manifest.json from current artifacts.")


if __name__=="__main__":
    main()
