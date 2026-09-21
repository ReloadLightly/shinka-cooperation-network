"""Immutable scientific identities, separate from runtime/session bookkeeping.

No function here opens target outcomes. Existing legacy forecasts remain reusable
through their original, stricter provenance check. Native R source is unchanged.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

FINGERPRINT_ENV = "SHINKA_SCIENTIFIC_FINGERPRINT"
NATIVE_FIT_FILES = ("R/empirical.R", "R/network_specification_v2.R")
NATIVE_FORWARD_FILES = ("R/forecast.R", "R/forecast_multiobjective.R")
SCIENTIFIC_FILES = NATIVE_FIT_FILES + NATIVE_FORWARD_FILES + (
    "R/score.R", "evaluate.py", "scripts/network_specification_v2.py",
    "scripts/multiobjective_evaluation.py", "scripts/scientific_contract.py",
)


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_hashes(root, names):
    return {name: file_sha(Path(root) / name) for name in names}


def immutable_json(path, value):
    """Atomically publish once; identical retries are idempotent, changes fail.

    Atomic hard-link publication prevents a half-written lock surviving a crash.
    The surrounding campaign/cache lock coordinates operations across processes.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read_json(path) != value:
            raise RuntimeError(f"Immutable scientific record differs: {path}. Use a new campaign; do not overwrite evidence.")
        return
    fd, temporary = tempfile.mkstemp(prefix=".scientific-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if read_json(path) != value:
                raise RuntimeError(f"Concurrent scientific record differs: {path}")
    finally:
        Path(temporary).unlink(missing_ok=True)


def catalog_semantics(catalog):
    """Exclude prose while binding every field consulted by the decoder."""
    keys = ("schema_version", "network_node_count", "effect_aliases", "covariates")
    result = {key: catalog[key] for key in keys}
    result["effects"] = {
        name: {key: row[key] for key in ("role", "parameter_rule", "interaction_type", "covariate_kind") if key in row}
        for name, row in catalog["effects"].items()
    }
    result["proportional_main_moment_groups"] = [group["members"] for group in catalog["proportional_main_moment_groups"]]
    return result


def prediction_layers(root, spec, year, settings, protocol):
    """Bind fit and forecast inputs independently; neither includes outcomes.

    The R structured module contains both fit and transformation helpers, so its
    whole-file hash conservatively invalidates both layers when it changes.
    """
    root = Path(root)
    if year not in (*settings["development_years"], settings["final_test_year"]):
        raise ValueError("Target outside the declared temporal design")
    fit = {
        "specification": spec, "target": year, "training": [1990, year - 1],
        "past_sha256": file_sha(root / f"data/past/{year}.rds"),
        "archive_sha256": settings["archive_sha256"],
        "software": read_json(root / "environment/versions.json"),
        "estimation": {k: v for k, v in settings["estimation"].items() if k not in ("policy_revision", "covariance_eigenvalues")},
        "implementation": source_hashes(root, NATIVE_FIT_FILES),
        "adapter_semantics": protocol["adapter_semantics"],
    }
    forecast = {
        "fit_sha256": digest(fit), "forecast": settings["forecast"],
        "implementation": source_hashes(root, NATIVE_FORWARD_FILES),
        "forward_data_semantics": "training-only-v2-fixed-origin-membership",
    }
    return {"version": "layered-prediction-identity-v1", "fit": fit, "fit_sha256": digest(fit),
            "forecast": forecast, "forecast_sha256": digest(forecast)}


def scientific_identity(root):
    """Current evaluator fingerprint; binds development packets, never 2010."""
    root = Path(root)
    protocol = read_json(root / "configs/multiobjective-v1.json")
    settings = read_json(root / protocol["prediction_settings"])
    if settings["development_years"] != [2006, 2007, 2008, 2009]:
        raise RuntimeError("Scientific contract requires exactly the four declared development years")
    payload = {
        "version": "scientific-contract-v1", "protocol": protocol,
        "prediction_settings": settings,
        "catalog": catalog_semantics(read_json(root / protocol["effect_catalog"])),
        "files": source_hashes(root, SCIENTIFIC_FILES + ("environment/versions.json",)),
        "past": {str(year): file_sha(root / f"data/past/{year}.rds") for year in settings["development_years"]},
    }
    return {"sha256": digest(payload), "inputs": payload}


def require_expected_fingerprint(identity):
    expected = os.environ.get(FINGERPRINT_ENV)
    if expected and identity["sha256"] != expected:
        raise RuntimeError("Evaluator implementation or scientific inputs changed during this campaign; restore the bound revision or start a separately named campaign.")


def bind_campaign(directory, scientific, search):
    """Freeze science/search once without overwriting old population semantics."""
    directory = Path(directory)
    path = directory / "scientific_contract.json"
    value = {"version": "campaign-contract-v1", "scientific": scientific, "search": search}
    if not path.exists():
        database = directory / "programs.sqlite"
        if database.exists():
            with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in ("programs", "project_pending_evaluations"):
                    if table in tables and connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                        raise RuntimeError("An existing unbound population/pending evaluation is preserved, not silently relabeled. Finish it on its original revision or use a new results directory; compatible numerical caches remain reusable.")
    immutable_json(path, value)
    os.environ[FINGERPRINT_ENV] = scientific["sha256"]
    return value


def require_search_open(root):
    """Do not resume confirmatory search after a finalist set has been frozen."""
    root = Path(root)
    if any((root / "results/selection/multiobjective-v1" / name).exists() for name in ("plan.json", "selected.json")):
        raise RuntimeError("The multiobjective finalist set is frozen; further search belongs to a separately declared exploratory experiment.")
    legacy = root / "results/final_test/reservation.json"
    if legacy.exists() and read_json(legacy).get("outcomes_accessed"):
        raise RuntimeError("Reserved outcomes were already accessed by the legacy workflow; do not resume confirmatory search.")
