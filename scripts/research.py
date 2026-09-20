#!/usr/bin/env python3
"""Small execution entry point for serial, resumable scientific work.

This schedules scientific stages only. Evolution is exclusively the native
Shinka runner in scripts/run_shinka.py.
"""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluate import CACHE, SETTINGS, BASELINE, forecast_year, identity, preflight, read_json, save_json
from scripts.specification import read_program
from scripts.resources import scientific_execution


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage", choices=["audits","baselines","status"])
    parser.add_argument("--target", type=int, choices=[2006,2007,2008,2009])
    args=parser.parse_args()
    if args.stage == "status":
        records=[]
        for path in sorted((ROOT/"results").rglob("process.json")):
            if "/work/" not in str(path):
                records.append({"file":str(path.relative_to(ROOT)), **read_json(path)})
        for path in sorted(CACHE.glob("*/fit_diagnostics.json")):
            records.append({"file":str(path.relative_to(ROOT)),"fit_diagnostics":read_json(path)})
        print(json.dumps(records,indent=2))
        return 0
    (ROOT/"results").mkdir(exist_ok=True)
    with scientific_execution():
        if args.stage == "audits":
            for script in ["R/source_parity.R","R/audit_forward.R","scripts/check_metrics.R"]:
                tag=Path(script).stem
                cmd=[sys.executable,str(ROOT/"scripts/run_logged.py"),"--run-dir",str(ROOT/"results/audit_runs"/tag),"--",
                     str(ROOT/"environment/run-r"),script]
                subprocess.run(cmd,cwd=ROOT,check=True)
            subprocess.run([sys.executable,str(ROOT/"scripts/check_contract.py")],cwd=ROOT,check=True)
            preflight()
            return 0
        settings=read_json(SETTINGS)
        spec,_=read_program(BASELINE)
        years=[args.target] if args.target else settings["development_years"]
        summary={}
        for target in years:
            print(f"Running training-only baseline for {target}",flush=True)
            summary[str(target)]=forecast_year(spec,target,settings)
            save_json(ROOT/"results/evolution_forecast/baseline-progress.json",summary)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
