#!/usr/bin/env python3
"""Step 3A: verify one saved training fit without any new simulation or fitting.

Only the declared 1990-2008 packet is decompressed. No evaluator, forecast,
scorer, raw-data preparation or evolutionary controller is imported or called.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = "configs/convergence-preflight-v1.json"
FIT = "results/cache/ed64802bacb0fbdd1ae1bc45746e29795f85bc0f92ceedf427660ea0c40efc99/fit-attempt-3.rds"
FIT_SHA = "5c122ed7a1e061d8d23f50c73a22baa4b80884ad74be49ab7a56bdb80dfe0e5c"
PACKET = "data/past/2009.rds"
PACKET_SHA = "f8aea6ff84f4a82c43cce7cd6bc12fcd0a4fc36e0db0f6aeb4618381fc1771e4"
BUNDLE = "sources/archive/step2-development-inputs.zip"
DEFAULT_OUTPUT = "results/diagnostics/convergence-preflight-v1"
EXPECTED_MEMBERS = {f"data/{kind}/{year}.rds" for kind in ("past", "targets") for year in range(2006, 2010)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def write_new(path: Path, value: dict) -> None:
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate_policy(p: dict) -> None:
    fixed = {"version":"convergence-preflight-v1", "stage":"3A", "fit_path":FIT,
             "fit_sha256":FIT_SHA, "packet_member":PACKET,"packet_sha256":PACKET_SHA,
             "bundle_path":BUNDLE,"training_years":list(range(1990,2009)),
             "actor_count":161,"parameter_count":58,"verification_timeout_seconds":300,
             "new_simulations_allowed":False,"new_fits_allowed":False,"outcome_access_allowed":False,
             "thresholds":{"individual_strictly_below":0.1,"overall_strictly_below":0.25}}
    for key, value in fixed.items():
        if p.get(key) != value or type(p.get(key)) is not type(value):
            raise ValueError(f"Step 3A scope changed: {key}")
    pilot = {"status":"prepared_not_executed","nsub":0,"n3":3000,"simOnly":False,
             "seed":2009301,"preserve_original_fixed_flags":True,"useStdInits":False,
             "prevAns":None,"serial":True,"pilot_is_separately_authorized":True}
    if p.get("next_pilot") != pilot:
        raise ValueError("Undeclared next-pilot settings")
    if p["runtime"]["R"] != "4.2.1" or p["runtime"]["RSiena"] != "1.3.10":
        raise ValueError("Pinned native version differs")
    if not p.get("native_source_sha256") or not p.get("preserved_source_sha256"):
        raise ValueError("Missing source fingerprints")


def training_bytes(bundle: Path) -> bytes:
    """Validate archive structure, then read ONLY the one training member."""
    with zipfile.ZipFile(bundle) as z:
        if len(z.namelist()) != 8 or set(z.namelist()) != EXPECTED_MEMBERS:
            raise ValueError("Unexpected, duplicate or unsafe bundle entries")
        if z.getinfo(PACKET).file_size > 100_000_000:
            raise ValueError("Unexpected training packet size")
        content = z.read(PACKET)
    if hashlib.sha256(content).hexdigest() != PACKET_SHA:
        raise ValueError("Training packet differs from the original fit provenance")
    return content


def inspect(root: Path = ROOT, *, require_native: bool = False) -> dict:
    p = read(root / POLICY); validate_policy(p)
    original = read((root / FIT).parent / "provenance.json")
    if (original["training"] != [1990,2008] or original["target"] != 2009
        or original["files"][PACKET] != PACKET_SHA
        or original["specification"] != {"schema_version":1,"network_effects":["degPlus","transTriads"]}):
        raise ValueError("Original training provenance differs")
    provenance = read(root / "results/evolution_forecast/diagnosis-2009/matrix_input_provenance.json")
    if not any(x["path"] == FIT and x["sha256"] == FIT_SHA for x in provenance["inputs"]):
        raise ValueError("Original saved-fit identity differs")
    expected = {FIT:FIT_SHA, **p["preserved_source_sha256"]}
    if require_native:
        expected.update({"vendor/RSiena/"+k:v for k,v in p["native_source_sha256"].items()})
    for name, value in expected.items():
        if sha(root / name) != value:
            raise ValueError(f"Input/source hash mismatch: {name}")
    training_bytes(root / BUNDLE)
    if require_native and not (root / "environment/run-r").is_file():
        raise FileNotFoundError("Pinned R launcher missing")
    return {"status":"inputs_verified", "policy_sha256":sha(root/POLICY),
            "files":{name:sha(root/name) for name in expected},
            "implementation":{n:sha(root/n) for n in ("scripts/convergence_preflight.py","R/convergence_preflight.R")},
            "packet_member":PACKET,"packet_sha256":PACKET_SHA,
            "native_source_bytes_checked":require_native,"target_packets_decompressed":0,
            "raw_archives_opened":0,"simulations":0,"fits":0}


def validate_report(report: dict) -> None:
    if report.get("status") != "verified_no_simulation" or report.get("stage") != "3A":
        raise ValueError("Native preflight did not complete")
    for key in ("new_simulations","new_fits","new_forecasts","target_packets_read","raw_archives_read"):
        if type(report.get(key)) is not int or report[key] != 0:
            raise ValueError(f"Scope violation: {key}")
    dry = report["dry_initialization"]
    for key in ("coefficients_identical","parameter_order_identical","fixed_flags_identical",
                "observed_targets_equal","period_targets_equal"):
        if dry.get(key) is not True:
            raise ValueError(f"Native initialization mismatch: {key}")
    if (dry.get("optimization_iterations") != 0 or dry.get("phase3_body_entered") is not False
        or dry.get("simulator_entered") is not False or dry.get("free_coordinates") != 58
        or dry.get("nsub") != 0 or dry.get("n3") != 3000 or dry.get("simOnly") is not False
        or dry.get("seed") != 2009301):
        raise ValueError("Native route was not a stopped, unchanged diagnostic initialization")
    if report["pilot"]["status"] != "prepared_not_executed":
        raise ValueError("Step 3B was not authorized")
    if report["original_diagnostics"]["full_original_acceptance"] is not False:
        raise ValueError("Historical failed fit must not be relabelled")


def verify(output: Path, root: Path = ROOT, *, runner=subprocess.run) -> dict:
    output = output.resolve()
    output.relative_to((root / "results/diagnostics").resolve())
    inputs = inspect(root,require_native=True)  # Before output or native execution.
    if output.exists():
        raise FileExistsError("Preflight output exists; use verify-artifacts or a new output name")
    output.mkdir(parents=True)
    write_new(output / "inputs.json",inputs)
    packet = output / "training-packet.rds"
    packet.write_bytes(training_bytes(root/BUNDLE))
    try:
        with (output / "native.log").open("x") as log:
            runner([str(root/"environment/run-r"),str(root/"R/convergence_preflight.R"),
                    "--verify-only",str(root),str(output)],cwd=root,stdout=log,
                   stderr=subprocess.STDOUT,check=True,timeout=300)
        if sha(packet) != PACKET_SHA or inspect(root,require_native=True) != inputs:
            raise ValueError("Scientific inputs changed during verification")
        report = read(output / "verification.json"); validate_report(report)
    finally:
        # Remove only this invocation's temporary copy, never the published input.
        packet.unlink(missing_ok=True)
    evidence = {p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    write_new(output / "commitment.json",{"stage":"3A","artifacts":evidence,
               "simulations":0,"refits":0,"pilot_executed":False})
    return report


def verify_artifacts(output: Path) -> dict:
    c = read(output/"commitment.json")
    required = {"inputs.json","verification.json","parameter-map.csv",
                "saved-moment-covariance.csv","saved-moment-means.csv","native.log","session-info.txt"}
    if not required.issubset(c["artifacts"]) or c.get("pilot_executed") is not False:
        raise ValueError("Incomplete or wrong-stage commitment")
    for name,value in c["artifacts"].items():
        if Path(name).name != name or sha(output/name) != value:
            raise ValueError(f"Committed evidence changed: {name}")
    report = read(output/"verification.json"); validate_report(report)
    return {"status":"committed_preflight_verified","new_simulations":0,"new_fits":0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("check","verify","verify-artifacts"))
    parser.add_argument("--execute",action="store_true",help="Permit read-only native preflight, never simulation")
    parser.add_argument("--output",type=Path,default=ROOT/DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.action == "verify" and not args.execute:
        print("Dry request: add --execute for Step 3A only. No files read or native calls made.")
        return 0
    try:
        result = (inspect() if args.action=="check" else
                  verify(args.output) if args.action=="verify" else verify_artifacts(args.output))
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,subprocess.SubprocessError) as exc:
        print(f"Step 3A stopped: {exc}",file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
