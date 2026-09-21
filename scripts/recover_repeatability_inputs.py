#!/usr/bin/env python3
"""Recover only the eight development packets from the published source archive.

Trusted data preparation, NOT forecasting or scoring. The mixed-year RData is
necessarily deserialized by R, but rows after 2009 are discarded before packet
construction. Every produced packet must match its PRE-EXISTING published hash.
No primary evaluator, fit, metric, or reserved-year evaluation is changed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.forecast_repeatability import inspect_inputs, packet_paths, sha
from scripts.scientific_contract import immutable_json

RAW_MEMBER = "IO_Final/data/data_raw.RData"
PREPARATION_SHA256 = "efa5dd793fb65afa1af402b2452effba5f6c6d246b6edb509ea16e818ffd0357"


def restricted_preparation(original: str) -> str:
    """Restrict the frozen preparation source; refuse ambiguous source drift."""
    if hashlib.sha256(original.encode()).hexdigest() != PREPARATION_SHA256:
        raise ValueError("Original preparation source differs from the reviewed version")
    replacements = {
        'source("R/empirical.R")': 'source("R/empirical.R")\nstopifnot(getRversion() == "4.2.1", packageVersion("RSiena") == "1.3.10")',
        'load("sources/original/IO_Final/data/data_raw.RData",envir=env)': 'load(args[1],envir=env)',
        'dat <- as.data.frame(dat[required]); gc()': 'dat <- as.data.frame(dat[required]); gc()\ndat <- dat[dat$year <= 2009L, , drop=FALSE]; gc()',
        'if(!all(1990:2010 %in% unique(dat$year)))': 'if(!all(1990:2009 %in% unique(dat$year)))',
        'for(t in 2006:2010)': 'for(t in 2006:2009)',
    }
    for before, after in replacements.items():
        if original.count(before) != 1:
            raise ValueError("Ambiguous preparation source fragment: " + before)
        original = original.replace(before, after)
    return original


def recover() -> dict:
    plan = inspect_inputs(ROOT)
    expected = plan["packets"]
    if set(expected) != set(packet_paths()):
        raise ValueError("Recovery must contain exactly the eight development inputs")
    if not plan["missing_inputs"]:
        return {"status": "already_present_and_hash_verified", "packets": expected}
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    archive = ROOT / "sources/archive/IO_Final.zip"
    if sha(archive) != manifest["sha256"]:
        raise ValueError("Published raw archive checksum differs")
    code = restricted_preparation((ROOT / "R/audit_data.R").read_text())
    output = ROOT / "results/diagnostics/forecast-repeatability-v1"
    output.mkdir(parents=True, exist_ok=True)
    # Never extract arbitrary archive paths or execute the original paper scripts.
    with tempfile.TemporaryDirectory(prefix="step2-development-preparation-") as temp:
        temp = Path(temp)
        raw = temp / "data_raw.RData"
        with zipfile.ZipFile(archive) as source:
            raw.write_bytes(source.read(RAW_MEMBER))
        if sha(raw) != manifest["source_files"][RAW_MEMBER]:
            raise ValueError("Raw member checksum differs")
        script = temp / "prepare_development.R"
        script.write_text(code)
        packets = temp / "packets"
        # This log contains the existing preparation coverage, not raw rows.
        log = output / "input_recovery.log"
        with log.open("x") as stream:
            subprocess.run([str(ROOT / "environment/run-r"), str(script), str(raw),
                            "--output", str(packets)], cwd=ROOT, stdout=stream,
                           stderr=subprocess.STDOUT, check=True, timeout=300)
        produced = {"data/" + p.relative_to(packets).as_posix(): sha(p)
                    for kind in ("past", "targets")
                    for p in (packets / kind).glob("*.rds")}
        if produced != expected:
            differences = {name: {"expected": expected.get(name), "actual": produced.get(name)}
                           for name in set(expected) | set(produced)
                           if expected.get(name) != produced.get(name)}
            raise ValueError("Reconstructed packets are NOT identical: " + json.dumps(differences))
        # Only byte-identical packets may enter the diagnostic's data directory.
        for name in packet_paths():
            destination = ROOT / name
            content = (packets / name.removeprefix("data/")).read_bytes()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if sha(destination) != expected[name]:
                    raise ValueError("Existing packet changed during recovery: " + name)
            else:
                with destination.open("xb") as handle:
                    handle.write(content)
        verified = inspect_inputs(ROOT)
        if not verified["ready"] or verified["packets"] != expected:
            raise RuntimeError("Post-recovery input check failed")
        record = {
            "status": "recovered_and_byte_identical",
            "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "archive_sha256": sha(archive), "raw_member": RAW_MEMBER,
            "raw_member_sha256": sha(raw), "preparation_source_sha256": PREPARATION_SHA256,
            "restricted_preparation_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "packets_sha256": produced, "all_eight_match_published_hashes": True,
            "mixed_year_archive_deserialized_by_trusted_preparer": True,
            "rows_after_2009_removed_before_packet_construction": True,
            "reserved_year_packet_created": False, "forecast_calls": 0,
            "fit_calls": 0, "score_calls": 0,
            "scope": "Trusted input recovery only; never report zero raw-archive access. No 2010 forecast, score, analysis or model selection.",
        }
        immutable_json(output / "input_recovery.json", record)
        (output / "prepare_development.R").write_text(code)
        return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Allow trusted mixed-year archive loading to recover development packets")
    args = parser.parse_args()
    if not args.execute:
        print("Dry run. Add --execute to recover only hash-identical development inputs; no forecasts or refits.")
        return 0
    print(json.dumps(recover(), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
