#!/usr/bin/env python3
"""Development-only planning, fixed-set sensitivity, sealing, then reserved test.

Only the explicit `run --execute` stage may access 2010 outcomes. Every valid
final prediction is committed before first access; terminal fit failures remain
null, and paused work is resumable. This is not an evolutionary controller.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import multiobjective_evaluation as evaluator
from scripts.network_specification_v2 import read_program, validate_spec, spec_hash, complexity
from scripts.scientific_contract import digest, immutable_json, scientific_identity, prediction_layers, require_search_open
from scripts.resources import scientific_execution
from scripts.final_test import validate_prediction

read_json, save_json, sha = evaluator.read_json, evaluator.save_json, evaluator.sha
YEARS = (2006, 2007, 2008, 2009)
OBJECTIVES = ("J1", "J2", "J3")


class FinalForecastFailure(RuntimeError):
    """A completed native attempt failed; not a missing/tampered commitment."""


def selection_root():
    return ROOT / "results/selection/multiobjective-v1"


def final_root():
    return ROOT / "results/final_test/multiobjective-v1"


def reporting_policy():
    value = read_json(ROOT / "configs/finalist-reporting-v1.json")
    offsets = value["development_seed_offsets"]
    if (not isinstance(offsets, list) or not offsets or len(set(offsets)) != len(offsets)
        or any(type(x) is not int or x < 2 or x >= 1000 for x in offsets)
        or 2 not in offsets or value["simulations_per_forecast"] != 1000
        or value["sensitivity_changes_membership"] is not False
        or value["final_target"] != 2010 or value["final_seed_offset"] != 1):
        raise ValueError("Invalid prespecified finalist reporting policy")
    return value


def path_in_results(path):
    path = Path(path).resolve()
    path.relative_to((ROOT / "results").resolve())
    return path


def evidence(path):
    path = path_in_results(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def verify(item):
    path = path_in_results(ROOT / item["path"])
    if sha(path) != item["sha256"]:
        raise RuntimeError(f"Changed or missing sealed evidence: {item['path']}")
    return path


def settings_and_protocol():
    protocol = read_json(ROOT / "configs/multiobjective-v1.json")
    settings = read_json(ROOT / protocol["prediction_settings"])
    if settings["development_years"] != list(YEARS) or settings["final_test_year"] != 2010 or settings["forecast"]["simulations"] != 1000:
        raise RuntimeError("The original development years and endpoint budget are fixed")
    return settings, protocol


def require_development(spec, settings, protocol):
    """Read and verify saved evidence; no implicit estimation or scoring."""
    years = {}
    for year in YEARS:
        folder = evaluator.saved_forecast_folder(spec, year, settings, protocol)
        validate_prediction(folder, year, settings, year * 1000 + 1)
        expected = {"predictions": sha(folder / "predictions.rds"),
                    "target": sha(ROOT / f"data/targets/{year}.rds"),
                    "scorer": sha(ROOT / "R/score.R"), "PRROC": settings["software"]["PRROC"]}
        if read_json(folder / "score_provenance.json") != expected:
            raise RuntimeError("Development score provenance is stale; selection does not silently rescore")
        scores = read_json(folder / "scores.json")
        if scores.get("target") != year or scores.get("seed") != year * 1000 + 1 or scores.get("simulations") != 1000:
            raise RuntimeError("Development year, seed or budget differs")
        for value, upper in ((scores["primary"]["pr_auc"], 1), (scores["primary"]["brier"], 1), (scores["spending"]["rmse"], 10)):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= upper:
                raise RuntimeError("Nonfinite or out-of-range development metric")
        names = ("accepted_fit.rds", "fit_diagnostics.json", "predictions.rds", "forecast_audit.json",
                 "prediction_commit.json", "scores.json", "score_provenance.json", "eligibility_mask.rds", "provenance.json")
        years[str(year)] = {"folder": str(folder.relative_to(ROOT)), "scores": scores,
                            "evidence": [evidence(folder / name) for name in names]}
    return years


def differences(candidate, reference):
    annual = {}
    if set(candidate) != set(reference) or not candidate:
        raise RuntimeError("Comparison requires identical, nonempty year sets")
    for year in candidate:
        c, b = candidate[year], reference[year]
        if sha(ROOT / c["folder"] / "eligibility_mask.rds") != sha(ROOT / b["folder"] / "eligibility_mask.rds"):
            raise RuntimeError("Candidate/reference dyad masks differ")
        cs, bs = c["scores"], b["scores"]
        if cs["spending"]["n"] != bs["spending"]["n"]:
            raise RuntimeError("Candidate/reference spending masks differ")
        annual[year] = {"J1": cs["primary"]["pr_auc"] - bs["primary"]["pr_auc"],
                        "J2": bs["primary"]["brier"] - cs["primary"]["brier"],
                        "J3": bs["spending"]["rmse"] - cs["spending"]["rmse"]}
    values = {key: math.fsum(row[key] for row in annual.values()) / len(annual) for key in OBJECTIVES}
    return {**values, "combined_score": 2 + (values["J1"] + values["J2"] + values["J3"] / 10) / 3,
            "years": annual}


def choose_representatives(rows, reference_key):
    """Pure fixed selection rule; never consumes sensitivity/final scores."""
    if not rows or len({r["canonical_sha256"] for r in rows}) != len(rows):
        raise ValueError("Unique development rows are required")
    if reference_key not in {r["canonical_sha256"] for r in rows}:
        raise ValueError("Original reference must be included")
    for row in rows:
        if any(type(row.get(k)) not in (int, float) or not math.isfinite(row[k]) for k in (*OBJECTIVES, "combined_score")):
            raise ValueError("Nonfinite development objective")
    frontier = [r for r in rows if not any(
        all(other[k] >= r[k] for k in OBJECTIVES) and any(other[k] > r[k] for k in OBJECTIVES) for other in rows)]
    champions = {}
    for key in (*OBJECTIVES, "combined_score"):
        best = min(frontier, key=lambda r: (-r[key], r["complexity"], r["canonical_sha256"]))
        champions[key] = best["canonical_sha256"]
    selected = set(champions.values()) | {reference_key}
    return champions, [r for r in sorted(rows, key=lambda r: r["canonical_sha256"]) if r["canonical_sha256"] in selected]


def build_plan():
    require_search_open(ROOT)
    settings, protocol = settings_and_protocol()
    science = scientific_identity(ROOT)
    reference, _ = read_program(ROOT / "candidates/initial_multiobjective.py")
    baseline = require_development(reference, settings, protocol)
    reference_key = spec_hash(reference)
    rows = {reference_key: {"canonical_sha256": reference_key, "specification": reference,
             "complexity": complexity(reference)["estimated_network_terms"], "development": baseline,
             **differences(baseline, baseline)}}
    archive = ROOT / "results/evaluations/multiobjective-v1"
    for path in sorted(archive.glob("*/metrics.json")):
        metrics = read_json(path)
        public = metrics.get("public", {})
        if public.get("valid") is not True:
            continue
        spec, _ = read_program(path.parent / "candidate.py")
        key = spec_hash(spec)
        if (public.get("scientific_fingerprint") != science["sha256"]
            or public.get("canonical_sha256") != key or public.get("protocol") != "multiobjective-v1"
            or read_json(path.parent / "correct.json").get("correct") is not True):
            raise RuntimeError("An archived candidate is not bound to this evaluator; do not silently include/exclude it")
        development = require_development(spec, settings, protocol)
        comparison = differences(development, baseline)
        if any(abs(public[k] - comparison[k]) > 1e-12 for k in OBJECTIVES):
            raise RuntimeError("Archived objectives differ from the verified annual scores")
        rows[key] = {"canonical_sha256": key, "specification": spec,
                     "complexity": complexity(spec)["estimated_network_terms"], "development": development,
                     "source_evidence": [evidence(path), evidence(path.parent / "candidate.py"), evidence(path.parent / "correct.json")],
                     **comparison}
    champions, finalists = choose_representatives(list(rows.values()), reference_key)
    return {"version": "multiobjective-finalist-set-v1", "scientific": science,
            "settings": settings, "protocol": protocol, "reporting": reporting_policy(),
            "reference": reference_key, "champions": champions, "finalists": finalists,
            "population_size": len(rows), "population_evidence": [e for row in rows.values() for e in row.get("source_evidence", [])],
            "membership_frozen_before_sensitivity": True}


def validate_plan(plan):
    if plan["scientific"] != scientific_identity(ROOT) or plan["reporting"] != reporting_policy():
        raise RuntimeError("Scientific/reporting protocol changed after planning")
    for item in plan.get("population_evidence", []):
        verify(item)
    for row in plan["finalists"]:
        if set(row["development"]) != set(map(str, YEARS)):
            raise RuntimeError("Finalist lacks the four development years")
        if spec_hash(validate_spec(row["specification"])) != row["canonical_sha256"]:
            raise RuntimeError("Finalist specification identity changed")
        for item in row.get("source_evidence", []):
            verify(item)
        for year, record in row["development"].items():
            verify_score_record(record, int(year), int(year) * 1000 + 1, plan["settings"])


def verify_score_record(record, year, seed, settings):
    folder = path_in_results(ROOT / record["folder"])
    required = {"accepted_fit.rds", "predictions.rds", "forecast_audit.json", "prediction_commit.json",
                "scores.json", "score_provenance.json", "eligibility_mask.rds"}
    paths = [verify(item) for item in record["evidence"]]
    if any(path.parent != folder for path in paths) or not required <= {path.name for path in paths}:
        raise RuntimeError("Scored evidence is incomplete or refers to a different forecast")
    saved = read_json(folder / "scores.json")
    if any(record["scores"].get(key) != value for key, value in saved.items()):
        raise RuntimeError("Reported metrics differ from the committed score artifact")
    if saved.get("target") != year or saved.get("seed") != seed or saved.get("simulations") != 1000:
        raise RuntimeError("Scored year, seed or simulation count differs")
    validate_prediction(folder, year, settings, seed)
    # Only development callers invoke this preselection check. Final outcomes
    # are opened exclusively by run_final after the commitment barrier.
    if year not in YEARS:
        raise RuntimeError("Preselection score verification cannot access final outcomes")
    identity = {"predictions": sha(folder / "predictions.rds"), "target": sha(ROOT / f"data/targets/{year}.rds"),
                "scorer": sha(ROOT / "R/score.R"), "PRROC": settings["software"]["PRROC"]}
    if read_json(folder / "score_provenance.json") != identity:
        raise RuntimeError("Saved development scoring inputs changed")


def _copy_fit(source, destination):
    for name in ("accepted_fit.rds", "fit_diagnostics.json"):
        src, dst = source / name, destination / name
        if dst.exists():
            if sha(src) != sha(dst):
                raise RuntimeError("A reused training fit changed")
        else:
            temporary = destination / (name + ".pending")
            shutil.copy2(src, temporary)
            temporary.replace(dst)


def forecast(spec, year, settings, protocol, directory, *, fitted_source=None):
    """Use the structured R adapter; never access outcomes in this stage."""
    directory.mkdir(parents=True, exist_ok=True)
    layers = prediction_layers(ROOT, spec, year, settings, protocol)
    immutable_json(directory / "provenance.json", layers)
    immutable_json(directory / "specification.json", spec)
    immutable_json(directory / "settings.json", settings)
    if year in YEARS and fitted_source is None:
        raise RuntimeError("Development sensitivity must reuse an accepted fit; implicit refitting is prohibited")
    if fitted_source is not None:
        if year not in YEARS:
            raise RuntimeError("Accepted-fit reuse is restricted to development sensitivity")
        original_settings = copy.deepcopy(settings)
        original_settings["forecast"].pop("seed_override", None)
        expected_source = evaluator.saved_forecast_folder(spec, year, original_settings, protocol)
        if fitted_source.resolve() != expected_source.resolve():
            raise RuntimeError("Fit source does not match this specification's verified development cache")
        validate_prediction(fitted_source, year, original_settings, year * 1000 + 1)
        _copy_fit(fitted_source, directory)
        immutable_json(directory / "reused_training_fit.json", {"source": str(fitted_source.relative_to(ROOT)),
                       "sha256": sha(fitted_source / "accepted_fit.rds"), "fit_sha256": layers["fit_sha256"]})
    committed = directory / "prediction_commit.json"
    if committed.exists():
        if not (directory / "predictions.rds").exists() or sha(directory / "predictions.rds") != read_json(committed)["sha256"]:
            raise RuntimeError("A committed prediction is missing/changed; restore it, never regenerate after commitment")
    complete = all((directory / name).is_file() for name in ("predictions.rds", "forecast_audit.json", "simulations.rds"))
    if not complete:
        if committed.exists():
            raise RuntimeError("Committed forecast publication is incomplete; restore its artifacts")
        if evaluator.deadline_reached():
            raise evaluator.ExecutionWindowPaused("No new native operation admitted after the execution deadline")
        try:
            evaluator.legacy.run_r([ROOT / "R/forecast_multiobjective.R", "--spec", directory / "specification.json",
                "--target", year, "--output", directory, "--settings", directory / "settings.json"], directory,
                "fit_and_forecast", settings["estimation"]["timeout_seconds"] * settings["estimation"]["max_attempts"] + settings["forecast"]["timeout_seconds"])
        except RuntimeError as exc:
            marker = directory / "checkpoint.json"
            if marker.exists() and read_json(marker).get("status") == "paused_execution_window":
                raise evaluator.ExecutionWindowPaused("Resume saved native finalist work") from exc
            raise FinalForecastFailure(str(exc)) from exc
    seed = settings["forecast"].get("seed_override", year * 1000 + 1)
    validate_prediction(directory, year, settings, seed)
    immutable_json(committed, {"sha256": sha(directory / "predictions.rds"), "target": year})
    return directory


def scored_record(folder, year, settings, spec):
    scores = evaluator.score_saved(folder, year, settings, spec)
    return {"folder": str(folder.relative_to(ROOT)), "scores": scores,
            "evidence": [evidence(folder / name) for name in ("accepted_fit.rds", "prediction_commit.json", "predictions.rds",
                "forecast_audit.json", "scores.json", "score_provenance.json", "eligibility_mask.rds")]}


def sensitivity(plan):
    validate_plan(plan)
    results = []
    for offset in plan["reporting"]["development_seed_offsets"]:
        models = {}
        for row in plan["finalists"]:
            key, spec = row["canonical_sha256"], row["specification"]
            annual = {}
            for year in YEARS:
                settings = copy.deepcopy(plan["settings"])
                settings["forecast"]["seed_override"] = year * 1000 + offset
                source = ROOT / row["development"][str(year)]["folder"]
                folder = selection_root() / "sensitivity" / f"seed-{offset}" / key / str(year)
                forecast(spec, year, settings, plan["protocol"], folder, fitted_source=source)
                annual[str(year)] = scored_record(folder, year, settings, spec)
            models[key] = annual
        results.append({"seed_offset": offset, "models": models,
                        "comparisons": {key: differences(annual, models[plan["reference"]]) for key, annual in models.items()}})
    descriptive = {}
    for key in (row["canonical_sha256"] for row in plan["finalists"]):
        descriptive[key] = {}
        for objective in OBJECTIVES:
            values = [rep["comparisons"][key][objective] for rep in results]
            mean = math.fsum(values) / len(values)
            sd = math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)) if len(values) > 1 else None
            descriptive[key][objective] = {"n": len(values), "mean": mean, "sample_sd": sd,
                                           "minimum": min(values), "maximum": max(values)}
    result = {"plan_sha256": digest(plan), "repetitions": results, "descriptive": descriptive,
              "membership_changed": False, "interpretation": plan["reporting"]["interpretation"]}
    immutable_json(selection_root() / "sensitivity.json", result)
    return result


def check_sensitivity(plan, value):
    if value.get("plan_sha256") != digest(plan) or value.get("membership_changed") is not False:
        raise RuntimeError("Sensitivity belongs to a different finalist set")
    reps = value.get("repetitions", [])
    if [r.get("seed_offset") for r in reps] != plan["reporting"]["development_seed_offsets"]:
        raise RuntimeError("Incomplete or different prespecified simulation repetitions")
    expected = {row["canonical_sha256"] for row in plan["finalists"]}
    for rep in reps:
        if set(rep["models"]) != expected or set(rep["comparisons"]) != expected:
            raise RuntimeError("Missing or extra sensitivity finalist")
        for key, annual in rep["models"].items():
            if set(annual) != set(map(str, YEARS)):
                raise RuntimeError("Incomplete development sensitivity years")
            for year, row in annual.items():
                settings = copy.deepcopy(plan["settings"])
                settings["forecast"]["seed_override"] = int(year) * 1000 + rep["seed_offset"]
                verify_score_record(row, int(year), int(year) * 1000 + rep["seed_offset"], settings)
            if differences(annual, rep["models"][plan["reference"]]) != rep["comparisons"][key]:
                raise RuntimeError("Sensitivity objective vector differs from saved scores")


def lock(plan):
    validate_plan(plan)
    result = read_json(selection_root() / "sensitivity.json")
    check_sensitivity(plan, result)
    locked = {"version": "sealed-multiobjective-finalists-v1", "plan_sha256": digest(plan),
              "plan": evidence(selection_root() / "plan.json"),
              "sensitivity": evidence(selection_root() / "sensitivity.json"),
              "finalists": [row["canonical_sha256"] for row in plan["finalists"]],
              "past_2010_sha256": sha(ROOT / "data/past/2010.rds"),
              "reporter_sha256": sha(Path(__file__)), "final_outcomes_accessed": False}
    immutable_json(selection_root() / "selected.json", locked)
    return locked


def verify_commitments(plan, records):
    expected = {row["canonical_sha256"] for row in plan["finalists"]}
    if set(records) != expected or records[plan["reference"]].get("status") != "committed":
        raise RuntimeError("Every finalist needs a terminal forecast record and the reference must be committed before access")
    for record in records.values():
        if record.get("status") == "invalid_forecast":
            if record.get("scientific_fitness") is not None:
                raise RuntimeError("Invalid forecasts cannot have fitness")
            verify(record["failure"])
            continue
        if record.get("status") != "committed":
            raise RuntimeError("A finalist forecast is incomplete")
        path = verify(record["commitment"])
        commit = read_json(path)
        if commit.get("target") != 2010 or sha(path.parent / "predictions.rds") != commit["sha256"]:
            raise RuntimeError("Final commitment is missing or changed; do not refit or regenerate")


def run_final(plan):
    validate_plan(plan)
    selected = read_json(selection_root() / "selected.json")
    if (selected["plan_sha256"] != digest(plan) or selected["reporter_sha256"] != sha(Path(__file__))
        or selected["past_2010_sha256"] != sha(ROOT / "data/past/2010.rds")):
        raise RuntimeError("Sealed finalist protocol or training packet changed")
    verify(selected["plan"])
    check_sensitivity(plan, read_json(verify(selected["sensitivity"])))
    final = final_root()
    final.mkdir(parents=True, exist_ok=True)
    reservation = final / "reservation.json"
    access = final / "outcome_access.json"
    if reservation.exists():
        record = read_json(reservation)
        if record["selection_sha256"] != sha(selection_root() / "selected.json"):
            raise RuntimeError("Final reservation belongs to another selection")
        records = record["forecasts"]
    else:
        records = {}
    if not access.exists():
        for row in plan["finalists"]:
            key, spec = row["canonical_sha256"], row["specification"]
            if key in records:
                continue
            try:
                folder = forecast(spec, 2010, plan["settings"], plan["protocol"], final / "forecasts" / key)
                records[key] = {"status": "committed", "commitment": evidence(folder / "prediction_commit.json")}
            except evaluator.ExecutionWindowPaused:
                save_json(reservation, {"selection_sha256": sha(selection_root() / "selected.json"), "forecasts": records})
                raise
            except FinalForecastFailure as exc:
                save_json(final / f"failure-{key}.json", {"error": str(exc), "exception": type(exc).__name__, "scientific_fitness": None})
                records[key] = {"status": "invalid_forecast", "scientific_fitness": None,
                                "failure": evidence(final / f"failure-{key}.json")}
            save_json(reservation, {"selection_sha256": sha(selection_root() / "selected.json"), "forecasts": records})
        verify_commitments(plan, records)
        immutable_json(access, {"reservation_sha256": sha(reservation),
                       "access_started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "note": "Committed before first target-file hash/read; a crash may precede actual access."})
    if read_json(access)["reservation_sha256"] != sha(reservation):
        raise RuntimeError("Final forecast records changed after outcome access")
    verify_commitments(plan, records)
    # The ONLY opening of 2010 outcomes starts below, after complete commitments.
    target_hash = sha(ROOT / "data/targets/2010.rds")
    immutable_json(final / "outcome_identity.json", {"sha256": target_hash, "target": 2010})
    models = {}
    for row in plan["finalists"]:
        key = row["canonical_sha256"]
        if records[key]["status"] == "committed":
            folder = verify(records[key]["commitment"]).parent
            models[key] = {"2010": scored_record(folder, 2010, plan["settings"], row["specification"])}
        else:
            verify(records[key]["failure"])
    comparison = {"selection_sha256": sha(selection_root() / "selected.json"), "target": 2010,
                  "forecasts": records, "models": models,
                  "comparisons": {key: differences(values, models[plan["reference"]]) if key in models else None
                                  for key, values in ((row["canonical_sha256"], models.get(row["canonical_sha256"])) for row in plan["finalists"])},
                  "interpretation": "Every locked finalist is reported, including predictive losses and null failed forecasts. Final results must not return to evolutionary feedback."}
    immutable_json(final / "comparison.json", comparison)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("plan", "sensitivity", "lock", "run"))
    parser.add_argument("--execute", action="store_true", help="Required for forecasts or reserved outcome access")
    args = parser.parse_args()
    if args.stage in ("sensitivity", "run") and not args.execute:
        print(f"Dry run: {args.stage} requires --execute. No forecasts or outcomes accessed.")
        return 0
    try:
        with scientific_execution():
            plan_path = selection_root() / "plan.json"
            if args.stage == "plan":
                if plan_path.exists():
                    validate_plan(read_json(plan_path))
                else:
                    immutable_json(plan_path, build_plan())
                print(plan_path)
                return 0
            plan = read_json(plan_path)
            function = {"sensitivity": sensitivity, "lock": lock, "run": run_final}[args.stage]
            function(plan)
            print(f"Completed {args.stage}; artifacts under {selection_root() if args.stage != 'run' else final_root()}")
            return 0
    except evaluator.ExecutionWindowPaused as exc:
        print(f"PAUSED: {exc}", file=sys.stderr)
        return 75


if __name__ == "__main__":
    raise SystemExit(main())
