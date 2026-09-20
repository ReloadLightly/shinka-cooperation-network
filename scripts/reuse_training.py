#!/usr/bin/env python3
"""Reuse completed training checkpoints after a forecast-only code correction.

Prediction caches retain their full identity. This explicit operation copies no
prediction or score and refuses changes to any training input or setting.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate import CACHE, SETTINGS, identity, preflight, read_json, save_json, sha
from scripts.resources import scientific_execution


def training_identity(provenance):
    # Explicit allowlist of forecast-only differences. Unknown new settings or
    # source files remain part of training identity and fail closed on changes.
    value = json.loads(json.dumps(provenance))
    value["files"].pop("R/forecast.R")
    value["settings"].pop("forecast")
    return value


def reuse(source):
    source = source.resolve()
    if source.parent != CACHE.resolve():
        raise ValueError("Source must be one recorded content-addressed cache directory.")
    preflight()
    old = read_json(source / "provenance.json")
    process = read_json(source / "process.json")
    if process.get("status") in (None, "running"):
        raise ValueError("Source process must have a recorded terminal state.")
    key, current = identity(old["specification"], old["target"], read_json(SETTINGS))
    if training_identity(old) != training_identity(current):
        raise ValueError("Training provenance differs; a new fit is required.")
    destination = CACHE / key
    if source == destination:
        raise ValueError("Same prediction cache: resume it directly without copying.")
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "process.json").exists():
        raise ValueError("Destination has already run; do not replace its artifacts.")
    diagnostics = read_json(source / "fit_diagnostics.json")
    paths = [source / "fit_diagnostics.json"]
    for row in diagnostics:
        attempt = row["attempt"]
        paths += [source / f"fit-attempt-{attempt}.rds", source / f"fit-{attempt}.txt"]
    if (source / "accepted_fit.rds").exists():
        paths.append(source / "accepted_fit.rds")
    if not diagnostics or any(not path.is_file() for path in paths):
        raise ValueError("No complete auditable training checkpoint set to reuse.")
    for path in paths:
        target = destination / path.name
        if target.exists() and sha(target) != sha(path):
            raise ValueError(f"Destination artifact differs: {target}")
    record = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_cache": str(source), "destination_cache": str(destination),
        "purpose": "Training-only checkpoint reuse across forecast-only differences",
        "training_identity_sha256": hashlib.sha256(json.dumps(training_identity(old), sort_keys=True).encode()).hexdigest(),
        "copied_artifact_sha256": {p.name: sha(p) for p in paths},
        "predictions_or_scores_copied": False,
        "completed_attempts": len(diagnostics),
    }
    for path in paths:
        if not (destination / path.name).exists():
            shutil.copy2(path, destination / path.name)
    save_json(destination / "provenance.json", current)
    save_json(destination / "training_checkpoint_reuse.json", record)
    print(json.dumps(record, indent=2))
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_cache", type=Path)
    args = parser.parse_args()
    with scientific_execution():
        reuse(args.source_cache)
