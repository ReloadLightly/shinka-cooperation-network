#!/usr/bin/env python3
"""Resumable original-source ABM execution; never an evolutionary evaluator."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.resources import scientific_execution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["paper_reproduction"], default="paper_reproduction")
    parser.add_argument("--profile", choices=["full", "reduced"], default="full")
    parser.add_argument("--max-new-calls", type=int, default=1)
    parser.add_argument("--stage", choices=["all","equilibria"], default="all")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    out = (args.run_dir or ROOT / "results/paper_reproduction" / ("abm-"+args.profile+("-equilibria" if args.stage=="equilibria" else ""))).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "requested_run.json").write_text(json.dumps({
        "mode": "paper_reproduction", "profile": args.profile, "stage": args.stage,
        "max_new_calls": args.max_new_calls, "source": "sources/original/IO_Final",
        "country_sample_reduced": False,
        "notes": "Full retains original grid and settings; bounded calls pause with exit75. Reduced grids and S=4 are diagnostic only."
    }, indent=2)+"\n")
    cmd = [sys.executable, str(ROOT/"scripts/run_logged.py"), "--run-dir", str(out), "--",
           str(ROOT/"environment/run-r"), str(ROOT/"R/paper_abm.R"), str(ROOT), str(out),
           args.profile, str(args.max_new_calls), args.stage]
    print("Waiting for the serial scientific-work lock, then executing original source.",flush=True)
    with scientific_execution():
        return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
