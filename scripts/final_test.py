#!/usr/bin/env python3
"""Trusted, sealed selection and held-out scoring; never imported by candidates."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate import BASELINE, CACHE, SETTINGS, identity, preflight, read_json, run_r, save_json, sha
from scripts.specification import CATALOG, read_program, spec_hash, validate_spec
from scripts.resources import scientific_execution

YEARS = [2006, 2007, 2008, 2009]
FINAL = ROOT / "results/final_test"
SELECTION = ROOT / "results/selection/selected.json"
RESERVATION = FINAL / "reservation.json"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def checked_settings():
    settings = read_json(SETTINGS)
    if (settings["development_years"] != YEARS or settings["final_test_year"] != 2010
            or settings["forecast"]["simulations"] != 1000
            or settings["forecast"]["seed_rule"] != "target_year * 1000 + 1"
            or settings["forecast"]["fresh_finalist_seed_rule"] != "target_year * 1000 + 2"
            or "seed_override" in settings["forecast"]):
        raise RuntimeError("Selection tooling requires the fixed v1 years, 1,000 endpoints and declared +1/+2 seed schedule.")
    return settings


def protocol_identity():
    # This never hashes or opens 2010 outcomes. The 2010 past packet ends in 2009.
    files = [SETTINGS, CATALOG, ROOT/"evaluate.py", ROOT/"scripts/specification.py",
             ROOT/"scripts/final_test.py", ROOT/"scripts/conventional_search.py", ROOT/"scripts/resources.py", ROOT/"R/forecast.R", ROOT/"R/empirical.R",
             ROOT/"R/score.R", ROOT/"R/audit_data.R", ROOT/"environment/versions.json",
             ROOT/"environment/conda-linux-64.explicit.txt", ROOT/"sources/manifest.json"]
    files += [ROOT/f"data/past/{year}.rds" for year in YEARS+[2010]]
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in files}
    return {"files": hashes, "sha256": digest(hashes)}


def finite_auc(value):
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("PR-AUC must be a finite number in [0,1].")
    return value


def evidence(path):
    path = Path(path).resolve()
    path.relative_to(ROOT/"results")
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def verify_evidence(item):
    path = (ROOT/item["path"]).resolve()
    path.relative_to(ROOT/"results")
    if sha(path) != item["sha256"]:
        raise RuntimeError(f"Selection evidence changed: {path}")
    return path


def require_development(spec, settings):
    """Read complete, accepted existing evidence. Never launches a missing fit."""
    with execution_lock():
        return _require_development_locked(spec, settings)


def _require_development_locked(spec, settings):
    annual = {}
    for year in YEARS:
        key, expected = identity(spec, year, settings)
        folder = CACHE/key
        needed = ["provenance.json", "specification.json", "settings.json", "accepted_fit.rds", "fit_diagnostics.json", "predictions.rds",
                  "forecast_audit.json", "prediction_commit.json", "scores.json",
                  "score_provenance.json", "eligibility_mask.rds"]
        missing = [name for name in needed if not (folder/name).is_file()]
        if missing:
            raise RuntimeError(f"Complete development evidence required for {spec_hash(spec)} / {year}: missing {missing}")
        if read_json(folder/"provenance.json") != expected:
            raise RuntimeError("Development cache provenance does not match current protocol.")
        if read_json(folder/"specification.json") != spec or read_json(folder/"settings.json") != settings:
            raise RuntimeError("Development cache specification/settings differ from declared provenance.")
        validate_prediction(folder, year, settings, year*1000+1)
        diagnostics = read_json(folder/"fit_diagnostics.json")
        if not isinstance(diagnostics, list) or not diagnostics or diagnostics[-1].get("valid") is not True:
            raise RuntimeError(f"No accepted convergence diagnostics: {folder}")
        score_identity = {"predictions": sha(folder/"predictions.rds"),
                          "target": sha(ROOT/f"data/targets/{year}.rds"),
                          "scorer": sha(ROOT/"R/score.R"), "PRROC": settings["software"]["PRROC"]}
        if read_json(folder/"score_provenance.json") != score_identity:
            raise RuntimeError("Development score provenance is stale.")
        score = read_json(folder/"scores.json")
        if score["target"] != year or score["seed"] != year*1000+1 or score["simulations"] != 1000:
            raise RuntimeError("Development score uses a different year, seed or budget.")
        finite_auc(score["primary"]["pr_auc"])
        annual[str(year)] = {"pr_auc": score["primary"]["pr_auc"], "cache_directory": str(folder),
                             "evidence": [evidence(folder/name) for name in needed]}
    return annual


def comparison(candidate, baseline):
    annual = {}
    for year in map(str, YEARS):
        if sha(Path(candidate[year]["cache_directory"])/"eligibility_mask.rds") != sha(Path(baseline[year]["cache_directory"])/"eligibility_mask.rds"):
            raise RuntimeError(f"Candidate and baseline eligibility differ in {year}.")
        annual[year] = {"candidate_pr_auc": candidate[year]["pr_auc"],
                        "baseline_pr_auc": baseline[year]["pr_auc"],
                        "delta": candidate[year]["pr_auc"]-baseline[year]["pr_auc"]}
    return {"years": annual, "raw_F": math.fsum(row["delta"] for row in annual.values())/4}


def validate_prediction(folder, year, settings, seed):
    if not (folder/"accepted_fit.rds").is_file() or not (folder/"accepted_fit.rds").stat().st_size:
        raise RuntimeError(f"Prediction is missing its accepted training fit: {folder}")
    audit = read_json(folder/"forecast_audit.json")
    if (audit.get("target_outcomes_accessed") is not False
            or audit.get("returned_simulations") != settings["forecast"]["simulations"]
            or audit.get("requested_simulations") != settings["forecast"]["simulations"]
            or audit.get("seed") != seed or audit.get("conditional") is not False
            or audit.get("simOnly") is not True or audit.get("allowOnly") is not False):
        raise RuntimeError(f"Invalid native forecast audit for {year}: {folder}")
    diagnostics = read_json(folder/"fit_diagnostics.json")
    if not isinstance(diagnostics, list) or not diagnostics or diagnostics[-1].get("valid") is not True:
        raise RuntimeError(f"Prediction has no accepted fit diagnostics: {folder}")
    if (folder/"prediction_commit.json").exists():
        commitment = read_json(folder/"prediction_commit.json")
        if commitment["target"] != year or commitment["sha256"] != sha(folder/"predictions.rds"):
            raise RuntimeError("Published prediction changed after commitment.")


@contextmanager
def execution_lock():
    with scientific_execution():
        yield


@contextmanager
def cache_lock(folder):
    # Keep this order even when called directly; scientific_execution is reentrant.
    with execution_lock():
        folder.mkdir(parents=True, exist_ok=True)
        with (folder/"evaluation.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


def forecast_only(spec, year, settings, root, fitted_source=None):
    with execution_lock():
        key, _ = identity(spec, year, settings)
        with cache_lock(root/key):
            return _forecast_only_locked(spec, year, settings, root, fitted_source)


def _forecast_only_locked(spec, year, settings, root, fitted_source=None):
    key, provenance = identity(spec, year, settings)
    folder = root/key
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/"provenance.json").exists() and read_json(folder/"provenance.json") != provenance:
        raise RuntimeError("Existing forecast directory has different provenance.")
    save_json(folder/"provenance.json", provenance)
    save_json(folder/"specification.json", spec)
    save_json(folder/"settings.json", settings)
    if fitted_source is not None:
        source_settings = json.loads(json.dumps(settings))
        source_settings["forecast"].pop("seed_override", None)
        source_key, source_provenance = identity(spec, year, source_settings)
        if (year not in YEARS or Path(fitted_source).resolve() != (CACHE/source_key).resolve()
                or read_json(Path(fitted_source)/"provenance.json") != source_provenance):
            raise RuntimeError("Fit reuse is restricted to this specification's validated training-only development cache.")
        validate_prediction(Path(fitted_source), year, source_settings, year*1000+1)
        for name in ("accepted_fit.rds", "fit_diagnostics.json"):
            source = Path(fitted_source)/name
            destination = folder/name
            if destination.exists() and sha(source) != sha(destination):
                raise RuntimeError("Fresh-randomness run has a different fitted model.")
            if not destination.exists():
                temporary = destination.with_suffix(destination.suffix+".pending")
                shutil.copy2(source, temporary)
                temporary.replace(destination)
        save_json(folder/"reused_training_fit.json", {"source": str(fitted_source),
                  "sha256": sha(folder/"accepted_fit.rds"), "purpose": "Fresh simulation randomness only; coefficients unchanged"})
    complete = all((folder/name).is_file() for name in ("predictions.rds", "forecast_audit.json"))
    if complete:
        try:
            read_json(folder/"forecast_audit.json")
        except (json.JSONDecodeError, UnicodeError):
            complete = False
    if not complete:
        if (folder/"prediction_commit.json").exists():
            raise RuntimeError("Committed forecast publication is incomplete; restore its original artifacts rather than regenerating committed predictions.")
        # An interruption can leave a prediction without its closing native audit.
        # Preserve that unpublished material, retain the fit, and repeat the same
        # fixed-seed forecast. Never restart a committed final-year prediction.
        partial = [folder/name for name in ("predictions.rds", "predictions.pending.rds", "forecast_audit.json",
                   "predictions.csv", "behavior_predictions.csv", "simulations.rds", "forecast_effects.csv")
                   if (folder/name).exists()]
        if partial:
            recovery = folder/"incomplete_publications"/dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            recovery.mkdir(parents=True, exist_ok=False)
            for path in partial:
                path.replace(recovery/path.name)
            save_json(recovery/"recovery.json", {"recovered_utc": now(), "reason": "Prediction/audit pair incomplete before commitment; repeat same forecast seed using retained fit"})
        run_r([ROOT/"R/forecast.R", "--spec", folder/"specification.json", "--target", year,
               "--output", folder, "--settings", folder/"settings.json"], folder, "fit_and_forecast",
              settings["estimation"]["timeout_seconds"]*settings["estimation"]["max_attempts"]
              + settings["forecast"]["timeout_seconds"])
    seed = settings["forecast"].get("seed_override", year*1000+1)
    validate_prediction(folder, year, settings, seed)
    if not (folder/"prediction_commit.json").exists():
        with (folder/"predictions.rds").open("rb") as stream:
            os.fsync(stream.fileno())
        save_json(folder/"prediction_commit.json", {"sha256": sha(folder/"predictions.rds"),
                  "committed_utc": now(), "target": year})
    return folder


def score(folder, year, settings):
    with cache_lock(folder):
        return _score_locked(folder, year, settings)


def verify_reserved_predictions(reservation):
    commits = reservation.get("prediction_commits", {})
    if set(commits) != {"baseline", "candidate"}:
        raise RuntimeError("Final access requires both committed prediction sets.")
    folders = {}
    for role, item in commits.items():
        commit_path = verify_evidence(item)
        commitment = read_json(commit_path)
        if commitment.get("target") != 2010 or sha(commit_path.parent/"predictions.rds") != commitment.get("sha256"):
            raise RuntimeError("Reserved final predictions changed or are missing; regeneration after outcome access is prohibited.")
        folders[role] = commit_path.parent
    return folders


def _score_locked(folder, year, settings):
    validate_prediction(folder, year, settings, settings["forecast"].get("seed_override", year*1000+1))
    if not (folder/"prediction_commit.json").is_file():
        raise RuntimeError("Scoring requires a published prediction commitment.")
    if year == 2010:
        reservation = read_json(RESERVATION)
        if (reservation.get("outcomes_accessed") is not True
                or sha(SELECTION) != reservation.get("selection_sha256")
                or read_json(SELECTION).get("protocol") != protocol_identity()):
            raise RuntimeError("Final scoring requires the matching sealed selection and prior access reservation.")
        allowed = verify_reserved_predictions(reservation)
        if folder.resolve() not in {p.resolve() for p in allowed.values()}:
            raise RuntimeError("Forecast is not one of the two reserved final predictions.")
    elif year not in YEARS:
        raise RuntimeError("Unsupported target year.")
    target = ROOT/f"data/targets/{year}.rds"
    expected = {"predictions": sha(folder/"predictions.rds"), "target": sha(target),
                "scorer": sha(ROOT/"R/score.R"), "PRROC": settings["software"]["PRROC"]}
    if year == 2010 and reservation.get("target_sha256") != expected["target"]:
        raise RuntimeError("Final target hash is missing from or differs from its first-access reservation.")
    outputs = ("scores.json", "eligibility_mask.rds", "eligibility_and_scores.csv", "score_provenance.json")
    complete = all((folder/name).is_file() for name in outputs)
    if complete:
        try:
            complete = read_json(folder/"score_provenance.json") == expected
            read_json(folder/"scores.json")
        except (json.JSONDecodeError, UnicodeError):
            complete = False
    if not complete:
        run_r([ROOT/"R/score.R", folder/"predictions.rds", target, folder], folder, "score", 300)
        save_json(folder/"score_provenance.json", expected)
    result = read_json(folder/"scores.json")
    finite_auc(result["primary"]["pr_auc"])
    if (result["target"] != year or result["simulations"] != 1000
            or result["seed"] != settings["forecast"].get("seed_override", year*1000+1)):
        raise RuntimeError("Scorer returned a different target, seed or budget.")
    return {"pr_auc": result["primary"]["pr_auc"], "cache_directory": str(folder), "scores": result}


def sensitivity_root(spec, protocol):
    return ROOT/"results/selection/sensitivity"/digest({"spec": spec, "protocol": protocol["sha256"]})


def require_fresh_development(spec, baseline_spec, settings, protocol, original):
    """Reconstruct every expected fresh cache; a supplied evidence list is not sufficient."""
    annual = {"baseline": {}, "candidate": {}}
    artifacts = {}
    required = ("provenance.json", "specification.json", "settings.json", "predictions.rds",
                "prediction_commit.json", "scores.json", "score_provenance.json", "forecast_audit.json",
                "accepted_fit.rds", "fit_diagnostics.json", "eligibility_mask.rds", "reused_training_fit.json")
    for year in YEARS:
        fresh_settings = json.loads(json.dumps(settings))
        fresh_settings["forecast"]["seed_override"] = year*1000+2
        for role, structure in (("baseline", baseline_spec), ("candidate", spec)):
            key, expected = identity(structure, year, fresh_settings)
            folder = sensitivity_root(spec, protocol)/"private"/key
            if not all((folder/name).is_file() for name in required):
                raise RuntimeError(f"Incomplete fresh development evidence for {role}/{year}: {folder}")
            if (read_json(folder/"provenance.json") != expected
                    or read_json(folder/"specification.json") != structure
                    or read_json(folder/"settings.json") != fresh_settings):
                raise RuntimeError("Fresh development provenance, specification or seed settings mismatch.")
            validate_prediction(folder, year, fresh_settings, year*1000+2)
            source = Path(original[role][str(year)]["cache_directory"])
            reused = read_json(folder/"reused_training_fit.json")
            if (sha(source/"accepted_fit.rds") != sha(folder/"accepted_fit.rds")
                    or sha(source/"fit_diagnostics.json") != sha(folder/"fit_diagnostics.json")
                    or reused.get("sha256") != sha(source/"accepted_fit.rds")
                    or Path(reused["source"]).resolve() != source.resolve()):
                raise RuntimeError("Fresh forecasts did not reuse the validated training-only fit.")
            expected_score = {"predictions": sha(folder/"predictions.rds"),
                              "target": sha(ROOT/f"data/targets/{year}.rds"),
                              "scorer": sha(ROOT/"R/score.R"), "PRROC": settings["software"]["PRROC"]}
            result = read_json(folder/"scores.json")
            if (read_json(folder/"score_provenance.json") != expected_score
                    or result.get("target") != year or result.get("seed") != year*1000+2
                    or result.get("simulations") != 1000):
                raise RuntimeError("Fresh score has wrong provenance, target, seed or simulation count.")
            annual[role][str(year)] = {"pr_auc": finite_auc(result["primary"]["pr_auc"]), "cache_directory": str(folder)}
            for name in required:
                item = evidence(folder/name)
                artifacts[item["path"]] = item
    return comparison(annual["candidate"], annual["baseline"]), list(artifacts.values())


def validate_sensitivity(spec, baseline_spec, settings, protocol, original, path):
    path = path.resolve()
    if path != (sensitivity_root(spec, protocol)/"sensitivity.json").resolve():
        raise RuntimeError("Sensitivity artifact is outside its expected protocol/specification directory.")
    fresh = read_json(path)
    expected_fresh, expected_evidence = require_fresh_development(spec, baseline_spec, settings, protocol, original)
    primary = comparison(original["candidate"], original["baseline"])
    if (fresh.get("status") != "complete" or fresh.get("canonical_sha256") != spec_hash(spec)
            or fresh.get("canonical_specification") != spec or fresh.get("protocol") != protocol
            or fresh.get("simulations_per_target") != 1000 or fresh.get("final_outcomes_accessed") is not False
            or fresh.get("seed_schedule") != {str(y): y*1000+2 for y in YEARS}
            or fresh.get("original") != primary or fresh.get("fresh") != expected_fresh
            or fresh.get("evidence") != expected_evidence):
        raise RuntimeError("Fresh-randomness artifact does not match complete, independently verified four-year evidence.")
    if dt.datetime.fromisoformat(fresh["completed_utc"]) > dt.datetime.now(dt.timezone.utc):
        raise RuntimeError("Fresh-randomness evidence timestamp is in the future.")
    return fresh


def sensitivity(spec, settings):
    if SELECTION.exists() or RESERVATION.exists():
        raise RuntimeError("Selection has been sealed; preselection sensitivity cannot change its evidence.")
    baseline_spec, _ = read_program(BASELINE)
    original = {"baseline": require_development(baseline_spec, settings), "candidate": require_development(spec, settings)}
    protocol = protocol_identity()
    root = sensitivity_root(spec, protocol)
    if (root/"sensitivity.json").exists():
        result = validate_sensitivity(spec, baseline_spec, settings, protocol, original, root/"sensitivity.json")
        print(root/"sensitivity.json")
        return result
    annual = {"baseline": {}, "candidate": {}}
    for year in YEARS:
        fresh = json.loads(json.dumps(settings))
        fresh["forecast"]["seed_override"] = year*1000+2
        folders = {}
        for role, candidate_spec in (("baseline", baseline_spec), ("candidate", spec)):
            candidate_hash = spec_hash(candidate_spec)
            if candidate_hash not in folders:
                folders[candidate_hash] = forecast_only(candidate_spec, year, fresh, root/"private",
                                                        original[role][str(year)]["cache_directory"])
            annual[role][str(year)] = score(folders[candidate_hash], year, fresh)
    primary = comparison(original["candidate"], original["baseline"])
    fresh_result, evidence_files = require_fresh_development(spec, baseline_spec, settings, protocol, original)
    result = {"schema_version": 1, "status": "complete", "completed_utc": now(),
              "canonical_specification": spec, "canonical_sha256": spec_hash(spec), "protocol": protocol,
              "simulations_per_target": 1000, "seed_schedule": {str(y): y*1000+2 for y in YEARS},
              "original": primary, "fresh": fresh_result,
              "fresh_minus_original_F": fresh_result["raw_F"]-primary["raw_F"],
              "evidence": evidence_files,
              "final_outcomes_accessed": False,
              "interpretation": "One paired fresh Monte Carlo replicate; no independent-dyad significance test and no changed primary fitness."}
    save_json(root/"sensitivity.json", result)
    print(root/"sensitivity.json")
    return result


def lock_selection(spec, settings, sensitivity_path, reason):
    if not reason.strip():
        raise RuntimeError("Record a nonempty development-based selection reason.")
    if RESERVATION.exists() and not SELECTION.exists():
        raise RuntimeError("Final reservation exists without its selected manifest; restore the original selection.")
    baseline_spec, _ = read_program(BASELINE)
    candidate = require_development(spec, settings)
    baseline = require_development(baseline_spec, settings)
    primary = comparison(candidate, baseline)
    protocol = protocol_identity()
    validate_sensitivity(spec, baseline_spec, settings, protocol, {"candidate": candidate, "baseline": baseline}, sensitivity_path)
    items = [item for data in (candidate, baseline) for row in data.values() for item in row["evidence"]]
    manifest = {"schema_version": 1, "status": "locked_before_final_access", "selected_utc": now(),
                "canonical_specification": spec, "canonical_sha256": spec_hash(spec),
                "baseline_specification": baseline_spec, "protocol": protocol,
                "development": primary, "development_evidence": list({x["path"]: x for x in items}.values()),
                "fresh_randomness": evidence(sensitivity_path), "selection_reason": reason,
                "final_test_year": 2010, "final_outcomes_accessed_at_selection": False}
    if SELECTION.exists():
        existing = read_json(SELECTION)
        manifest["selected_utc"] = existing["selected_utc"]
        if existing != manifest:
            raise RuntimeError("Selection already exists and differs; reselection or changed evidence is prohibited.")
        if RESERVATION.exists():
            if sha(SELECTION) != read_json(RESERVATION).get("selection_sha256") or SELECTION.stat().st_mode & 0o222:
                raise RuntimeError("Existing sealed selection changed; restore its original artifacts.")
            print(SELECTION)
            return
        # Recover only the interruption between publishing the same manifest and
        # its reservation; no final scorer can run without that reservation.
        if dt.datetime.fromisoformat(existing["selected_utc"]) > dt.datetime.now(dt.timezone.utc):
            raise RuntimeError("Interrupted selection timestamp is in the future.")
    else:
        save_json(SELECTION, manifest)
    SELECTION.chmod(0o444)
    save_json(RESERVATION, {"selection_sha256": sha(SELECTION), "selected_utc": manifest["selected_utc"],
                           "outcomes_accessed": False})
    print(SELECTION)


def run_final(settings):
    manifest = read_json(SELECTION)
    reservation = read_json(RESERVATION)
    if (SELECTION.stat().st_mode & 0o222 or sha(SELECTION) != reservation["selection_sha256"]
            or manifest.get("status") != "locked_before_final_access"
            or manifest.get("final_outcomes_accessed_at_selection") is not False
            or manifest.get("final_test_year") != 2010 or manifest.get("protocol") != protocol_identity()):
        raise RuntimeError("Missing, writable, altered or stale selection lock; final outcomes remain inaccessible.")
    spec = validate_spec(manifest["canonical_specification"])
    baseline_spec, _ = read_program(BASELINE)
    if manifest["canonical_sha256"] != spec_hash(spec) or manifest["baseline_specification"] != baseline_spec:
        raise RuntimeError("Selected or baseline structure differs from its locked identity.")
    original = {"candidate": require_development(spec, settings), "baseline": require_development(baseline_spec, settings)}
    expected_items = [item for data in original.values() for row in data.values() for item in row["evidence"]]
    expected_items = list({item["path"]: item for item in expected_items}.values())
    if (manifest.get("development") != comparison(original["candidate"], original["baseline"])
            or manifest.get("development_evidence") != expected_items):
        raise RuntimeError("Selection does not contain the complete current four-year candidate/baseline evidence.")
    fresh_path = verify_evidence(manifest["fresh_randomness"])
    fresh = validate_sensitivity(spec, baseline_spec, settings, manifest["protocol"], original, fresh_path)
    selection_time = dt.datetime.fromisoformat(manifest["selected_utc"])
    if selection_time > dt.datetime.now(dt.timezone.utc):
        raise RuntimeError("Selection timestamp is in the future.")
    if dt.datetime.fromisoformat(fresh["completed_utc"]) > selection_time:
        raise RuntimeError("Fresh development evidence was completed after the selected structure was sealed.")
    if reservation.get("outcomes_accessed") and selection_time >= dt.datetime.fromisoformat(reservation["first_outcome_access_utc"]):
        raise RuntimeError("Selection was not committed before final access.")
    reserved = verify_reserved_predictions(reservation) if reservation.get("outcomes_accessed") else None
    folders = {}
    roles = {}
    # BOTH prediction sets are committed before even hashing target outcomes.
    for role, candidate_spec in (("baseline", baseline_spec), ("candidate", spec)):
        key = spec_hash(candidate_spec)
        if key not in folders:
            folders[key] = forecast_only(candidate_spec, 2010, settings, FINAL/"private")
        roles[role] = folders[key]
    if reserved is not None and roles != reserved:
        raise RuntimeError("Resumption refers to different final forecast directories.")
    if not reservation.get("outcomes_accessed"):
        reservation.update(outcomes_accessed=True, first_outcome_access_utc=now(),
                           prediction_commits={role: evidence(folder/"prediction_commit.json") for role, folder in roles.items()})
        save_json(RESERVATION, reservation)
    target_hash = sha(ROOT/"data/targets/2010.rds")
    if reservation.get("target_sha256", target_hash) != target_hash:
        raise RuntimeError("Reserved target outcomes changed after first access; refusing a new final comparison.")
    reservation["target_sha256"] = target_hash
    save_json(RESERVATION, reservation)
    scored = {role: score(folder, 2010, settings) for role, folder in roles.items()}
    if sha(roles["candidate"]/"eligibility_mask.rds") != sha(roles["baseline"]/"eligibility_mask.rds"):
        raise RuntimeError("Final-test candidate and baseline eligibility differ.")
    delta = scored["candidate"]["pr_auc"]-scored["baseline"]["pr_auc"]
    result = {"status": "complete", "completed_utc": now(), "selection": evidence(SELECTION),
              "target": 2010, "training_years": [1990, 2009], "canonical_specification": spec,
              "baseline_pr_auc": scored["baseline"]["pr_auc"], "candidate_pr_auc": scored["candidate"]["pr_auc"],
              "delta_pr_auc": delta, "results": scored,
              "interpretation": "2010 held out from this evolutionary search, not historically untouched. Subsequent model changes are exploratory."}
    if (FINAL/"comparison.json").exists():
        existing = read_json(FINAL/"comparison.json")
        result["completed_utc"] = existing["completed_utc"]
        if existing != result:
            raise RuntimeError("Completed final comparison differs on resumption; refusing to overwrite it.")
    else:
        save_json(FINAL/"comparison.json", result)
    print(json.dumps({k: result[k] for k in ("status", "baseline_pr_auc", "candidate_pr_auc", "delta_pr_auc")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fresh = commands.add_parser("sensitivity", help="Re-simulate all development years with the fixed fresh seed schedule")
    fresh.add_argument("--program-path", required=True, type=Path)
    lock = commands.add_parser("lock", help="Seal one selected structure before any final-year outcome access")
    lock.add_argument("--program-path", required=True, type=Path)
    lock.add_argument("--sensitivity", required=True, type=Path)
    lock.add_argument("--selection-reason", required=True)
    commands.add_parser("run", help="Refit through 2009, predict both models, then score reserved 2010 once")
    args = parser.parse_args()
    with execution_lock():
        preflight()
        settings = checked_settings()
        if args.command == "run":
            run_final(settings)
        else:
            spec, _ = read_program(args.program_path)
            if args.command == "sensitivity":
                sensitivity(spec, settings)
            else:
                lock_selection(spec, settings, args.sensitivity.resolve(), args.selection_reason)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        folder = ROOT/"results/selection/errors"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")+".log")
        path.write_text(traceback.format_exc())
        print(f"Selection/final-test stage failed; no scientific loss assigned. Diagnostics: {path}", file=sys.stderr)
        raise
