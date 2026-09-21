#!/usr/bin/env python3
"""One explicitly authorized 3000-draw phase-3 diagnostic; no refits or scores."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import convergence_preflight as pre

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "results/diagnostics/convergence-pilot-v1"
POLICY = "configs/convergence-pilot-v1.json"
IMPLEMENTATION = ("R/convergence_pilot.R", "scripts/convergence_pilot.py")
REQUIRED = {"inputs.json", "result.json", "native.log", "native-state.json",
            "diagnostic-fit.rds", "moment-deviations.rds", "moment-covariance.csv",
            "parameter-diagnostics.csv", "session-info.txt", "resources.txt"}


def validate_policy(policy: dict) -> None:
    expected = {"version":"convergence-pilot-v1", "stage":"3B", "fit_path":pre.FIT,
        "fit_sha256":pre.FIT_SHA, "packet_member":pre.PACKET, "packet_sha256":pre.PACKET_SHA,
        "nsub":0, "n3":3000, "simOnly":False, "seed":2009301,
        "maximum_native_calls":1, "timeout_seconds":3600, "serial":True,
        "allow_refit":False, "allow_outcomes":False, "automatic_retries":0,
        "thresholds":{"individual_strictly_below":0.1,"overall_strictly_below":0.25}}
    for key,value in expected.items():
        if type(policy.get(key)) is not type(value) or policy.get(key)!=value:
            raise ValueError(f"Undeclared pilot setting: {key}")


def inspect(root: Path=ROOT, require_native: bool=False) -> dict:
    policy=pre.read(root/POLICY); validate_policy(policy)
    for name,value in policy["helper_sha256"].items():
        if pre.sha(root/name)!=value:
            raise ValueError(f"Step 3A helper changed: {name}")
    old=pre.inspect(root,require_native=require_native)
    pre.verify_artifacts(root/pre.DEFAULT_OUTPUT)
    return {"policy":policy,"policy_sha256":pre.sha(root/POLICY),"preflight_inputs":old,
            "implementation":{n:pre.sha(root/n) for n in IMPLEMENTATION}}


def validate_result(r: dict) -> None:
    expected={"status":"completed","stage":"3B","draws":3000,"parameters":58,
      "actors":161,"seed":2009301,"nsub":0,"simOnly":False,"simulator_calls":3000,
      "phase3_entries":1,"optimization_entries":0,"newton_checks":1,
      "coefficients_identical_at_every_simulator_call":True,"coefficients_identical_after":True,
      "fixed_flags_identical":True,"observed_targets_identical":True,
      "historical_fit_accepted":False,"new_refits":0,"new_forecasts":0,
      "target_packets_read":0,"raw_archives_read":0,"training_years":list(range(1990,2009))}
    for key,value in expected.items():
        if type(r.get(key)) is not type(value) or r.get(key)!=value:
            raise ValueError(f"Pilot contract violated: {key}")
    for label,n in (("original",1000),("fresh_prefix",1000),("fresh_full",3000)):
        d=r[label]
        if d["draws"]!=n:
            raise ValueError("Diagnostic draw count differs")
        for key in ("maximum_absolute_t","overall"):
            if not isinstance(d[key],(int,float)) or not math.isfinite(d[key]) or d[key]<0:
                raise ValueError("Nonfinite diagnostic")
        if d["individual_pass"] is not (d["maximum_absolute_t"]<0.1) or d["overall_pass"] is not (d["overall"]<0.25):
            raise ValueError("Diagnostic pass label differs from fixed thresholds")
    if abs(r["original"]["overall"]-0.26134400479858994)>1e-12:
        raise ValueError("Original diagnostic changed")
    if any(not math.isfinite(v) or v>1e-12 or v<0 for v in r["reconstruction"].values()):
        raise ValueError("Native reconstruction failed")
    # A failed fresh convergence assessment is still a valid completed measurement.
    d=r["fresh_native_diagnostics"]
    if not d["native_ok"] or not d["phase3_complete"]:
        raise ValueError("Native execution incomplete")


def verify_artifacts(output: Path) -> dict:
    c=pre.read(output/"commitment.json")
    if c.get("stage")!="3B" or c.get("status")!="completed" or not REQUIRED.issubset(c["artifacts"]):
        raise ValueError("Incomplete pilot commitment")
    for name,value in c["artifacts"].items():
        if Path(name).name!=name or pre.sha(output/name)!=value:
            raise ValueError(f"Committed pilot artifact changed: {name}")
    result=pre.read(output/"result.json");validate_result(result)
    return result


def native_once(argv: list[str], root: Path, log, timeout: int) -> int:
    """Terminate the complete process group on an operational timeout; never retry."""
    p=subprocess.Popen(argv,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        return p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait()
        raise


def run(output: Path, root: Path=ROOT, *, worker=native_once) -> dict:
    output=output.resolve(); output.relative_to((root/"results/diagnostics").resolve())
    if output.exists():
        # Complete evidence is read, never regenerated. Partial/failed evidence stops.
        return verify_artifacts(output)
    inputs=inspect(root,require_native=True)
    output.mkdir(parents=True)
    pre.write_new(output/"inputs.json",inputs)
    pre.write_new(output/"started.json",{"stage":"3B","started_utc":datetime.now(timezone.utc).isoformat(),
        "seed":2009301,"n3":3000,"maximum_native_calls":1})
    packet=output/"training-packet.rds";packet.write_bytes(pre.training_bytes(root/pre.BUNDLE))
    try:
        with (output/"native.log").open("x") as log:
            rc=worker(["/usr/bin/time","-v","-o",str(output/"resources.txt"),
               str(root/"environment/run-r"),str(root/"R/convergence_pilot.R"),
               "--execute-one-pilot",str(root),str(output)],root,log,3600)
        if rc!=0:
            raise RuntimeError(f"Native pilot stopped with exit code {rc}; no retry")
        if pre.sha(packet)!=pre.PACKET_SHA or inspect(root,require_native=True)!=inputs:
            raise ValueError("Inputs or source changed during pilot")
        result=pre.read(output/"result.json");validate_result(result)
    except Exception as exc:
        pre.write_new(output/"failure.json",{"stage":"3B","status":"failed_or_incomplete",
            "error_type":type(exc).__name__,"error":str(exc),"automatic_retries":0})
        raise
    finally:
        packet.unlink(missing_ok=True)
    artifacts={p.name:pre.sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    pre.write_new(output/"commitment.json",{"stage":"3B","status":"completed","artifacts":artifacts})
    verify_artifacts(output)
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("check","self-test","run","verify-artifacts"))
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",type=Path,default=ROOT/OUTPUT)
    args=p.parse_args()
    if args.action=="run" and not args.execute:
        print("Dry request: one pilot requires --execute. No input read or native call.");return 0
    try:
        if args.action=="check":result=inspect()
        elif args.action=="self-test":
            return subprocess.call([str(ROOT/"environment/run-r"),str(ROOT/"R/convergence_pilot.R"),"--self-test"],cwd=ROOT)
        elif args.action=="run":result=run(args.output)
        else:result=verify_artifacts(args.output)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError) as e:
        print(f"Step 3B stopped: {e}",file=sys.stderr);return 1
    print(json.dumps(result,indent=2,allow_nan=False));return 0


if __name__=="__main__":raise SystemExit(main())
