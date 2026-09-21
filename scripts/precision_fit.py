#!/usr/bin/env python3
"""Explicit development-only opt-in to precision-before-continuation-v1.

This entry point estimates a model but never forecasts, scores outcomes, selects
finalists or launches Shinka. Without --execute it performs no scientific reads.
The historical evaluator and its cache are not silently migrated.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.network_specification_v2 import read_program
from scripts.scientific_contract import immutable_json, require_search_open
from scripts.convergence_pilot import native_process

VERSION = "precision-before-continuation-v1"
SETTINGS = "configs/precision-fit-v1.json"
POLICY = "configs/convergence-assessment-v1.json"
BUNDLE = "sources/archive/step2-development-inputs.zip"
SOURCE_FILES = (
    "R/empirical.R", "R/forecast.R", "R/network_specification_v2.R",
    "R/forecast_multiobjective.R", "R/convergence_preflight.R", "R/precision_convergence.R",
    "scripts/precision_fit.py", "scripts/convergence_pilot.py",
    "scripts/network_specification_v2.py", "configs/effect-catalog-v2.json",
    "configs/convergence-preflight-v1.json", "configs/evaluator-v2.json",
    SETTINGS, POLICY, "environment/versions.json", "environment/conda-linux-64.explicit.txt",
)
PACKET_HASHES = {
    2006: "7e00ccdf14204ac676cd141533e2612bc8bd810dbd371992d24670b47ad69ac5",
    2007: "7b772635ff780df37102249f103c96b6f0c79efda3fb9a1c55349ba110872435",
    2008: "332836625db9ff13b86e0dbf7a34386e8abcfc155df4b196cfacddf3aa1a496f",
    2009: "f8aea6ff84f4a82c43cce7cd6bc12fcd0a4fc36e0db0f6aeb4618381fc1771e4",
}


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_profile(settings: dict, original: dict, policy: dict) -> None:
    wanted = json.loads(json.dumps(original))
    wanted["version"] = "precision-fit-v1"
    wanted["estimation"]["convergence_assessment"] = VERSION
    if settings != wanted:
        raise ValueError("The new profile may change only its version and precision-policy selector")
    fixed = {"version": VERSION, "diagnostic_draws": 3000, "nsub": 0, "simOnly": False,
             "serial": True, "individual_strictly_below": 0.1, "overall_strictly_below": 0.25,
             "seed_base": 52000000, "maximum_assessments_per_unchanged_vector": 1,
             "maximum_extra_assessments_per_fit": 3, "role_specific_rules": False,
             "reserved_outcome_access": False}
    for name, value in fixed.items():
        if policy.get(name) != value or type(policy.get(name)) is not type(value):
            raise ValueError(f"Altered policy: {name}")


def packet_bytes(root: Path, target: int) -> bytes:
    if target not in PACKET_HASHES:
        raise ValueError("This entry point permits development years 2006-2009 only")
    member = f"data/past/{target}.rds"
    expected = {f"data/{kind}/{year}.rds" for kind in ("past", "targets") for year in PACKET_HASHES}
    with zipfile.ZipFile(root/BUNDLE) as z:
        if len(z.namelist()) != 8 or set(z.namelist()) != expected:
            raise ValueError("Unsafe, duplicated or changed development bundle directory")
        if z.getinfo(member).file_size > 100_000_000:
            raise ValueError("Unexpected packet size")
        data = z.read(member)
    if hashlib.sha256(data).hexdigest() != PACKET_HASHES[target]:
        raise ValueError("Training packet hash mismatch")
    return data


def request(root: Path, spec: dict, target: int) -> dict:
    if target not in PACKET_HASHES:
        raise ValueError("Reserved or invalid target")
    settings, original, policy = (read(root/n) for n in (SETTINGS, "configs/evaluator-v2.json", POLICY))
    validate_profile(settings, original, policy)
    native_hashes = read(root/"configs/convergence-preflight-v1.json")["native_source_sha256"]
    for name, expected in native_hashes.items():
        if sha(root/"vendor/RSiena"/name) != expected:
            raise ValueError(f"Native source differs: {name}")
    return {"version": VERSION, "target": target, "training": [1990, target-1],
            "specification": spec, "past_sha256": PACKET_HASHES[target],
            "settings": settings, "policy": policy,
            "source_sha256": {name: sha(root/name) for name in SOURCE_FILES},
            "native_source_sha256": native_hashes,
            "historical_imports": False, "forecasts": 0, "outcome_access": False}


def validate_acceptance(s: dict, req: dict) -> None:
    d = s["diagnostics"]
    if (s.get("version") != VERSION or req.get("version") != VERSION
        or s.get("status") != "accepted" or type(s.get("target")) is not int
        or s["target"] not in PACKET_HASHES or s["target"] != req.get("target")
        or type(s.get("authoritative_n3")) is not int or s["authoritative_n3"] not in (1000, 3000)
        or type(s.get("accepted_attempt")) is not int or s["accepted_attempt"] not in range(1, 5)
        or s.get("new_forecasts") != 0 or s.get("targets_read") != 0):
        raise ValueError("Malformed precision acceptance record")
    for k in ("valid", "native_ok", "phase3_complete", "covariance_all_finite", "finite_identified"):
        if d.get(k) is not True:
            raise ValueError(f"Missing native acceptance requirement: {k}")
    if (d.get("termination") != "OK" or d.get("covariance_message") != ""
        or d.get("phase3_iterations") != s["authoritative_n3"]):
        raise ValueError("Native termination, covariance or draw count differs")
    for k, cutoff in (("maximum_absolute_t_ratio", .1), ("overall_maximum_convergence", .25)):
        value = d.get(k)
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value < cutoff:
            raise ValueError(f"Invalid convergence ratio: {k}")
    for k in ("divergence", "fixed_parameters", "newly_fixed_parameters"):
        if d[k].get("shape_valid") is not True or d[k].get("any") is not False:
            raise ValueError(f"Invalid native parameter flags: {k}")


def verify(output: Path, root: Path = ROOT) -> dict:
    c = read(output/"precision-fit-commitment.json")
    if c.get("version") != VERSION or not {"accepted_fit.rds", "accepted.json", "request.json", "specification.json"}.issubset(c["files"]):
        raise ValueError("Missing policy acceptance evidence")
    for name, expected in c["files"].items():
        path = (output/name).resolve()
        path.relative_to(output.resolve())
        if sha(path) != expected:
            raise ValueError(f"Changed committed evidence: {name}")
    s = read(output/"accepted.json")
    validate_acceptance(s, read(output/"request.json"))
    return {"status": "accepted_fit_verified", "version": VERSION,
            "target": s["target"], "authoritative_n3": s["authoritative_n3"], "new_native_calls": 0}


def run(spec_path: Path, target: int, output: Path, root: Path = ROOT,
        *, runner=native_process) -> dict:
    output = output.resolve()
    output.relative_to((root/"results/precision-fits-v1").resolve())
    require_search_open(root)
    spec, _ = read_program(spec_path)
    req = request(root, spec, target)
    data = packet_bytes(root, target)
    output.mkdir(parents=True, exist_ok=True)
    with (output/"run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = set(p.name for p in output.iterdir()) - {"run.lock"}
        if existing and not (output/"request.json").is_file():
            raise ValueError("Unbound or historical files cannot enter a precision-policy fit directory")
        immutable_json(output/"request.json", req)
        immutable_json(output/"specification.json", spec)
        if (output/"precision-fit-commitment.json").exists():
            return verify(output, root)
        invocations = output/"invocations"; invocations.mkdir(exist_ok=True)
        call = invocations/f"{len(list(invocations.iterdir()))+1:06d}"; call.mkdir()
        packet = call/"training-packet.rds"; packet.write_bytes(data)
        command = ["/usr/bin/time", "-v", "-o", str(call/"resources.txt"),
                   str(root/"environment/run-r"), str(root/"R/precision_convergence.R"),
                   "--execute-fit-only", str(root), str(output), str(output/"specification.json"),
                   str(packet), str(target), str(root/SETTINGS)]
        try:
            with (call/"native.log").open("x") as log:
                runner(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True,
                       timeout=req["settings"]["estimation"]["timeout_seconds"]*7)
            if request(root, spec, target) != req or sha(packet) != PACKET_HASHES[target]:
                raise ValueError("Inputs changed during estimator execution")
        except Exception as exc:
            immutable_json(call/"failure.json", {"error": type(exc).__name__, "message": str(exc),
                           "automatic_retry": False, "fitness": None})
            raise
        finally:
            packet.unlink(missing_ok=True)
        files = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*"))
                 if p.is_file() and p.name != "run.lock"}
        immutable_json(output/"precision-fit-commitment.json", {"version": VERSION, "files": files})
        return verify(output, root)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--target", type=int, choices=tuple(PACKET_HASHES), required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--verify-only", action="store_true")
    a = p.parse_args(argv)
    if a.execute and a.verify_only:
        p.error("--execute and --verify-only are mutually exclusive")
    if not a.execute and not a.verify_only:
        print("Dry request: opt-in precision fit requires --execute. No training data or outcomes read.")
        return 0
    try:
        result = verify(a.output) if a.verify_only else run(a.spec, a.target, a.output)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Precision fit stopped: {exc}", file=sys.stderr)
        return 75 if isinstance(exc, subprocess.CalledProcessError) and exc.returncode == 75 else 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
