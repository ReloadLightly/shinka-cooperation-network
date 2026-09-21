#!/usr/bin/env python3
"""One authorized Step 3B diagnostic; no refits, forecasts or automatic retries."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import signal
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import convergence_preflight as pre

OUTPUT = "results/diagnostics/convergence-pilot-v1"
PLAN = {"stage": "3B", "version": "convergence-pilot-v1", "seed": 2009301,
        "n3": 3000, "nsub": 0, "simOnly": False, "replications": 1,
        "serial": True, "timeout_seconds": 3600, "training_years": list(range(1990, 2009)),
        "fit_path": pre.FIT, "fit_sha256": pre.FIT_SHA,
        "packet_member": pre.PACKET, "packet_sha256": pre.PACKET_SHA,
        "individual_threshold": 0.1, "overall_threshold": 0.25,
        "refits": 0, "forecasts": 0, "step3c": False}
PREFLIGHT_HASHES = {
    "R/convergence_preflight.R": "b9deaf332852e108eaafe2123271303faf70f1638ea2198e6063929825a550e8",
    "scripts/convergence_preflight.py": "20da8e65111828766792024d4f82a21372e0ff58a2aea6ef8d379f7fc425cace",
    "configs/convergence-preflight-v1.json": "b84a567d4b2235af2ca180d49c1de7c7136f8b71b3238b81e0cbd56463a99483",
}
REQUIRED = {"request.json", "summary.json", "guard-audit.json", "raw-phase3.rds",
            "diagnostic.rds", "moment-deviations.csv", "moment-covariance.csv",
            "parameter-diagnostics.csv", "native.log", "resources.txt", "session-info.txt"}


def inspect(root: Path = ROOT, native: bool = False) -> dict:
    for name, expected in PREFLIGHT_HASHES.items():
        if pre.sha(root / name) != expected:
            raise ValueError(f"Step 3A source drift: {name}")
    pre.verify_artifacts(root / pre.DEFAULT_OUTPUT)
    return {"plan": PLAN, "preflight": pre.inspect(root, require_native=native),
            "implementation": {p: pre.sha(root/p) for p in
                ("R/convergence_pilot.R", "scripts/convergence_pilot.py")}}


def validate_summary(s: dict) -> None:
    required = {"status":"completed", "stage":"3B", "seed":2009301,"draws":3000,
                "replications":1,"nsub":0,"simOnly":False,"parameters":58,"actors":161,
                "coefficients_identical":True,"original_fixed_flags_preserved":True,
                "historical_attempt_accepted":False,"new_refits":0,"new_forecasts":0,
                "target_packets_read":0,"raw_archives_read":0,"step3c_started":False,
                "training_years":list(range(1990,2009))}
    for k,v in required.items():
        if s.get(k) != v or type(s.get(k)) is not type(v):
            raise ValueError(f"Pilot scope or completion mismatch: {k}")
    guard = s["guard"]
    for k,v in {"status":"completed","phase3_entries":1,"simulator_entries":3000,
                "simulator_exits":3000,"forbidden_entries":0,"potential_nr_calls":1,
                "postprocessing_entries":1,"checked_every_simulator_call":True}.items():
        if guard.get(k) != v or type(guard.get(k)) is not type(v):
            raise ValueError(f"Pilot guard mismatch: {k}")
    for k,n in (("fresh_first_1000",1000),("fresh_full_3000",3000)):
        d=s[k]
        if d.get("draws") != n:
            raise ValueError("Wrong diagnostic sample size")
        for metric, threshold, flag in (("maximum_absolute_t",0.1,"individual_pass"),("overall",0.25,"overall_pass")):
            x=d.get(metric)
            if type(x) not in (int,float) or not math.isfinite(x) or x < 0 or d.get(flag) is not (x < threshold):
                raise ValueError(f"Malformed diagnostic: {k}/{metric}")
    # A failed convergence criterion is a scientific result, NOT an execution error.
    d=s["native_diagnostics"]
    if type(d.get("valid")) is not bool:
        raise ValueError("Native diagnostic validity must be explicit")
    if d.get("phase3_iterations") != 3000 or d.get("phase3_complete") is not True:
        raise ValueError("Native phase 3 incomplete")
    for new,old in (("maximum_absolute_t_ratio","maximum_absolute_t"),("overall_maximum_convergence","overall")):
        if not math.isclose(d[new],s["fresh_full_3000"][old],rel_tol=0,abs_tol=1e-12):
            raise ValueError("Saved native and reconstructed diagnostics differ")


def verify_artifacts(output: Path) -> dict:
    commitment=pre.read(output/"commitment.json")
    if commitment.get("stage") != "3B" or not REQUIRED.issubset(commitment["artifacts"]):
        raise ValueError("Missing or wrong-stage evidence")
    for name,value in commitment["artifacts"].items():
        if Path(name).name != name or pre.sha(output/name) != value:
            raise ValueError(f"Changed committed artifact: {name}")
    if pre.read(output/"request.json")["plan"] != PLAN:
        raise ValueError("Changed pilot plan")
    summary=pre.read(output/"summary.json");validate_summary(summary)
    return {"status":"verified", "draws":3000, "refits":0,
            "diagnostic_pass":summary["native_diagnostics"]["valid"]}


def native_process(command: list[str], *, cwd: Path, stdout, stderr, check: bool, timeout: int):
    """Terminate the whole process group on timeout, including R under /usr/bin/time."""
    proc = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr, start_new_session=True)
    try:
        code = proc.wait(timeout=timeout)
    except BaseException:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
        raise
    if check and code:
        raise subprocess.CalledProcessError(code, command)
    return subprocess.CompletedProcess(command, code)


def run(output: Path, root: Path = ROOT, *, runner=native_process) -> dict:
    output=output.resolve()
    output.relative_to((root/"results/diagnostics").resolve())
    if output.exists():
        raise FileExistsError("Pilot directory exists. Inspect evidence; no automatic overwrite or retry.")
    inputs=inspect(root,native=True)
    output.mkdir(parents=True)
    request={**inputs,"created_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    pre.write_new(output/"request.json",request)
    packet=output/"training-packet.rds"
    packet.write_bytes(pre.training_bytes(root/pre.BUNDLE))
    try:
        with (output/"native.log").open("x") as log:
            runner(["/usr/bin/time","-v","-o",str(output/"resources.txt"),
                    str(root/"environment/run-r"),str(root/"R/convergence_pilot.R"),
                    "--execute-one-pilot",str(root),str(output)],cwd=root,
                   stdout=log,stderr=subprocess.STDOUT,check=True,timeout=PLAN["timeout_seconds"])
        if pre.sha(packet) != pre.PACKET_SHA or inspect(root,native=True) != inputs:
            raise ValueError("Original scientific inputs changed during pilot")
        summary=pre.read(output/"summary.json");validate_summary(summary)
    except Exception as exc:
        pre.write_new(output/"failure.json",{"stage":"3B","status":"stopped",
            "exception":type(exc).__name__,"message":str(exc),"automatically_retried":False,
            "interpretation":"Not a fabricated convergence result. Inspect native log and partial evidence."})
        raise
    finally:
        packet.unlink(missing_ok=True)
    names={p.name:pre.sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    if not REQUIRED.issubset(names):
        raise ValueError("Native evidence incomplete")
    pre.write_new(output/"commitment.json",{"stage":"3B","artifacts":names})
    verify_artifacts(output)
    return summary


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("check","run","verify-artifacts"))
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",type=Path,default=ROOT/OUTPUT)
    args=p.parse_args()
    if args.action=="run" and not args.execute:
        print("Dry request: one pilot requires --execute. No inputs read or simulations launched.")
        return 0
    try:
        result=(inspect() if args.action=="check" else run(args.output) if args.action=="run" else verify_artifacts(args.output))
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print(f"Step 3B stopped: {exc}",file=sys.stderr);return 1
    print(json.dumps(result,indent=2,allow_nan=False));return 0


if __name__=="__main__":
    raise SystemExit(main())
