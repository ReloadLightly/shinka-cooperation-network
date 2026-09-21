"""Trusted multiobjective-v1 evaluation; activated separately from legacy work.

The same native forecasts supply all three objectives. Candidate source is read
as literal data only. Neither candidate code nor the evolutionary sampler owns
the objective definitions, observations, estimator or forward-simulation rule.
"""
from __future__ import annotations

import csv
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

# The root evaluate.py CLI dispatches here for multiobjective-v1; a direct entry
# remains available for the same fixed evaluator and historical invocations.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate as legacy
from scripts.network_specification_v2 import (
    read_program, validate_spec, spec_hash, legacy_specification, complexity,
)
from scripts.resources import scientific_execution
from scripts.scientific_contract import (
    prediction_layers, scientific_identity, require_expected_fingerprint, require_search_open,
    immutable_json,
)
from scripts.evaluation_feedback import failure_summary, failure_text, hypothesis_record

ROOT = legacy.ROOT
PROTOCOL = ROOT / "configs/multiobjective-v1.json"
REFERENCE = ROOT / "candidates/initial_multiobjective.py"
YEARS = (2006, 2007, 2008, 2009)
read_json, save_json, sha = legacy.read_json, legacy.save_json, legacy.sha


class ExecutionWindowPaused(RuntimeError):
    """Recoverable incomplete work, never a scientific loss or bandit reward."""


def deadline_reached():
    value = os.environ.get("SHINKA_EXECUTION_DEADLINE")
    return bool(value and time.time() >= float(value))


def prediction_identity(spec, year, settings, protocol):
    if year not in YEARS:
        raise ValueError("Evolution can evaluate only development targets 2006–2009.")
    versions = read_json(ROOT / "environment/versions.json")
    # Catalog descriptions, unrelated entries and publication timestamps are
    # provenance, not scientific reasons to refit an unchanged specification.
    relevant_packages = {p["package"]: p["version"] for p in versions["packages"]
                         if p["package"] in ("RSiena", "jsonlite", "data.table")}
    value = {
        "specification": validate_spec(spec), "target": year,
        "training": [1990, year - 1], "past_sha256": sha(ROOT / f"data/past/{year}.rds"),
        "source_archive_sha256": settings["archive_sha256"],
        "data_preprocessing": "authors-sample-annual-past-packets-v1",
        "forward_data_semantics": "training-only-v2-fixed-origin-membership",
        "adapter_semantics": protocol["adapter_semantics"],
        "software": {"R": versions["R"], "platform": versions["platform"],
                     "packages": relevant_packages},
        "estimation": {key: val for key, val in settings["estimation"].items()
                       if key not in ("policy_revision", "covariance_eigenvalues")},
        "forecast": settings["forecast"],
    }
    layers = prediction_layers(ROOT, validate_spec(spec), year, settings, protocol)
    value["implementation_binding"] = {"fit_sha256": layers["fit_sha256"],
                                       "forecast_sha256": layers["forecast_sha256"]}
    key = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return key, value


def legacy_folder(spec, year, settings):
    old_spec = legacy_specification(spec)
    if old_spec is None:
        return None
    key, expected = legacy.identity(old_spec, year, settings)
    folder = legacy.CACHE / key
    path = folder / "provenance.json"
    return folder if path.exists() and read_json(path) == expected else None


def previous_structured_folder(spec, year, settings, protocol):
    """Explicit compatibility import of the pre-contract structured cache.

    Both scientific provenance and all recorded native implementation hashes
    must match. A version-string claim alone never permits reuse.
    """
    _, current = prediction_identity(spec, year, settings, protocol)
    previous = {key: value for key, value in current.items() if key != "implementation_binding"}
    key = hashlib.sha256(json.dumps(previous, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    folder = ROOT / "results/cache" / key
    provenance = folder / "provenance.json"
    implementation = folder / "implementation_provenance.json"
    if not provenance.exists() or not implementation.exists() or read_json(provenance) != previous:
        return None
    hashes = read_json(implementation).get("files", {})
    required = ("R/empirical.R", "R/forecast.R", "R/network_specification_v2.R",
                "R/forecast_multiobjective.R", "configs/effect-catalog-v2.json")
    if set(hashes) != set(required) or any(sha(ROOT / name) != hashes[name] for name in required):
        return None
    return folder


def saved_forecast_folder(spec, year, settings, protocol):
    """Locate compatible complete saved predictions without running R."""
    old = legacy_folder(spec, year, settings)
    key, expected = prediction_identity(spec, year, settings, protocol)
    current = ROOT / "results/cache" / key
    candidates = [old, current, previous_structured_folder(spec, year, settings, protocol)]
    for folder in candidates:
        if folder is None or not all((folder / name).is_file() for name in ("predictions.rds", "forecast_audit.json", "accepted_fit.rds", "prediction_commit.json")):
            continue
        if folder == current and read_json(folder / "provenance.json") != expected:
            raise RuntimeError("Saved structured prediction identity differs from current inputs")
        return folder
    raise RuntimeError(f"Complete compatible saved development forecast is required for {year}; no implicit fitting in selection")


def fit_summary(diagnostics):
    keys = ("attempt", "nsub", "n3", "seed", "elapsed_seconds", "valid",
            "maximum_absolute_t_ratio", "overall_maximum_convergence", "native_ok",
            "termination", "phase3_complete", "finite_identified",
            "covariance_minimum_eigenvalue", "covariance_condition_number")
    return [{key: row.get(key) for key in keys} for row in diagnostics]


def fitted_structural_summary(folder, diagnostics, spec):
    """Read fitted training coefficients, never transformed forecast initials.

    New exports bind estimates directly to requestedEffects. Legacy exports
    retain the included training-effect order used by fit$theta/covtheta; that
    fallback is restricted to the unchanged legacy grammar and matching vector
    lengths. Missing feedback metadata does not change predictive fitness.
    """
    def term_key(term):
        def atom_key(atom):
            return f"{atom['effect']}|{atom['parameter']}|{atom.get('covariate', '')}"
        value = ("product(" + ";".join(map(atom_key, term["product"])) + ")"
                 if "product" in term else "atom(" + atom_key(term) + ")")
        return "network|" + value

    source = folder / "fitted_coefficients.csv"
    direct = source.exists()
    if not direct:
        source = folder / "training_effects.csv"
    try:
        accepted = diagnostics[-1]
        if accepted.get("valid") is not True:
            raise ValueError("No accepted training fit supplies coefficient feedback.")
        with source.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not direct:
            estimates, errors = accepted.get("estimates", []), accepted.get("standard_errors", [])
            if legacy_specification(spec) is None or not rows or not len(rows) == len(estimates) == len(errors):
                raise ValueError("Legacy effect order cannot be bound to accepted coefficient/SE vectors.")
            if any(row.get("include") != "TRUE" or row.get("fix") != "FALSE" for row in rows):
                raise ValueError("Legacy coefficient rows are not the included, estimated training effects.")
            for row, estimate, error in zip(rows, estimates, errors):
                row["estimate"], row["standard_error"] = estimate, error
        requested = {term_key(term): term for term in spec["network_effects"]}
        seen, coefficients = set(), []
        for row in rows:
            if row["type"] != "eval":
                continue
            process, effect = row["name"], row["shortName"]
            parameter = int(row["parm"])
            first, second = row["interaction1"], row["interaction2"]
            term, role = None, None
            if process == "dv.net":
                key = row.get(".spec_key")
                if not key and legacy_specification(spec) is not None and not first and not second:
                    key = term_key({"effect": effect, "parameter": parameter})
                if key in requested:
                    if key in seen:
                        raise ValueError("Repeated fitted native structural identity.")
                    seen.add(key)
                    term, role = requested[key], "evolved_network_term"
                elif effect == "density" and not first and not second:
                    role = "retained_network_density"
            elif process == "milex.beh":
                if effect in ("outdeg", "behDenseTriads") and first == "dv.net" and not second:
                    role = "retained_spending_network_mechanism"
                elif effect in ("linear", "quad") and not first and not second:
                    role = "retained_spending_shape"
            if role is None:
                continue
            estimate, error = float(row["estimate"]), float(row["standard_error"])
            if not math.isfinite(estimate) or not math.isfinite(error) or error <= 0:
                raise ValueError("A structural fitted coefficient or standard error is unavailable/nonfinite.")
            coefficients.append({
                "process": process, "role": role, "native_effect": effect,
                "native_label": row["effectName"],
                "native_parameter": parameter, "interaction1": first, "interaction2": second,
                "native_effect_number": int(row["effectNumber"]),
                "native_specification_key": row.get(".spec_key"),
                "specification_term": term, "estimate": estimate, "standard_error": error,
            })
        if seen != set(requested):
            raise ValueError("Some declared network terms lack an unambiguous fitted native identity.")
        return {
            "available": True, "accepted_attempt": accepted.get("attempt"),
            "source": str(source),
            "mapping": ("requestedEffects with fitted theta and sqrt(diag(covtheta))"
                        if direct else "included training-effect order and accepted diagnostic coefficient/SE vectors"),
            "coefficients": coefficients,
            "interpretation": "Training-objective coefficients with native RSiena estimation SEs. Positive coefficients favor increases in the corresponding native objective statistic, conditional on other terms; interaction signs depend on operand values. Controls and spending structure are retained; their coefficients are jointly re-estimated. These SEs do not quantify forecast Monte Carlo uncertainty or establish efficiency/security effects.",
        }
    except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
        return {"available": False, "source": str(source), "coefficients": [],
                "limitation": str(exc)}


def fitted_coefficient_feedback(annual):
    """Keep text economical; public metrics retain every structural coefficient."""
    def label(row):
        def atom_label(atom):
            covariate = "," + atom["covariate"] if "covariate" in atom else ""
            return f"{atom['effect']}({atom['parameter']}{covariate})"
        term = row["specification_term"]
        if term is not None:
            return "*".join(map(atom_label, term["product"])) if "product" in term else atom_label(term)
        return f"{row['process']}:{row['native_effect']}({row['native_parameter']},{row['interaction1']})"

    summaries = []
    for year, values in annual.items():
        fitted = values["candidate_structural_coefficients"]
        if not fitted["available"]:
            summaries.append(f"{year} fitted coefficient feedback unavailable: {fitted['limitation']}.")
            continue
        network = [row for row in fitted["coefficients"] if row["role"] == "evolved_network_term"]
        spending = [row for row in fitted["coefficients"] if row["role"] == "retained_spending_network_mechanism"]
        shown = network[:8] + spending
        text = "; ".join(f"{label(row)} beta={row['estimate']:+.6g}, SE={row['standard_error']:.6g}"
                         for row in shown)
        omitted = f"; {len(network) - 8} further network terms in public metrics" if len(network) > 8 else ""
        summaries.append(f"{year} fitted candidate: {text}{omitted}.")
    return (" ".join(summaries)
            + " Native estimation SEs describe training coefficients, not forecast Monte Carlo uncertainty. "
            "Product signs depend on operand values; coefficient magnitudes across different statistics are not directly comparable. "
            "Annual public metrics record candidate/reference structural coefficients, density, spending shapes and availability limitations.")


def calibration_summary(folder):
    """Descriptive reliability bins from already committed/scored predictions.

    Brier is overall probability MSE; these bins provide a separate calibration
    description. No independent-dyad confidence intervals are constructed.
    """
    bins = [[] for _ in range(10)]
    with (folder / "eligibility_and_scores.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["eligible"] != "TRUE":
                continue
            p, y = float(row["probability"]), int(row["label"])
            bins[min(9, int(p * 10))].append((p, y))
    n = sum(map(len, bins))
    rows = [{"lower": i / 10, "upper": (i + 1) / 10, "n": len(values),
             "mean_probability": math.fsum(p for p, _ in values) / len(values),
             "observed_frequency": math.fsum(y for _, y in values) / len(values)}
            for i, values in enumerate(bins) if values]
    return {"bins": rows, "n": n,
            "bin_weighted_absolute_gap": math.fsum(
                row["n"] * abs(row["mean_probability"] - row["observed_frequency"])
                for row in rows) / n if n else None,
            "interpretation": "Descriptive ten-bin reliability; no independent-dyad uncertainty claim."}


def score_saved(folder, year, settings, spec):
    audit = read_json(folder / "forecast_audit.json")
    if audit.get("returned_simulations") != 1000 or audit.get("target_outcomes_accessed") is not False:
        raise RuntimeError("Invalid native endpoint count or target-access record.")
    diagnostics = read_json(folder / "fit_diagnostics.json")
    if not diagnostics or diagnostics[-1].get("valid") is not True or not (folder / "accepted_fit.rds").exists():
        raise RuntimeError(f"No scientifically accepted fit at {folder}.")
    commitment = {"sha256": sha(folder / "predictions.rds"), "target": year}
    path = folder / "prediction_commit.json"
    if path.exists():
        old = read_json(path)
        if any(old.get(key) != value for key, value in commitment.items()):
            raise RuntimeError("Saved predictions changed after publication.")
    else:
        save_json(path, {**commitment, "committed_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    # Only after predictions are committed may scoring access target outcomes.
    target = ROOT / f"data/targets/{year}.rds"
    score_identity = {"predictions": commitment["sha256"], "target": sha(target),
                      "scorer": sha(ROOT / "R/score.R"), "PRROC": settings["software"]["PRROC"]}
    if not (folder / "scores.json").exists() or not (folder / "score_provenance.json").exists() or read_json(folder / "score_provenance.json") != score_identity:
        legacy.run_r([ROOT / "R/score.R", folder / "predictions.rds", target, folder], folder, "score", 300)
        save_json(folder / "score_provenance.json", score_identity)
    result = read_json(folder / "scores.json")
    for label, value, upper in (("PR-AUC", result["primary"]["pr_auc"], 1),
                               ("Brier", result["primary"]["brier"], 1),
                               ("spending RMSE", result["spending"]["rmse"], 10)):
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= upper:
            raise ValueError(f"Invalid {label}; all three annual objectives must be available.")
    if result.get("target") != year or result.get("simulations") != 1000:
        raise RuntimeError("Scored target or simulation budget differs from the fixed protocol.")
    result["calibration"] = calibration_summary(folder)
    result["fit_diagnostics"] = diagnostics
    result["structural_coefficients"] = fitted_structural_summary(folder, diagnostics, spec)
    result["cache_directory"] = str(folder)
    return result


def forecast_year(spec, year, settings, protocol):
    try:
        return _forecast_year_bound(spec, year, settings, protocol)
    except ExecutionWindowPaused:
        raise
    except Exception as exc:
        # The mutation process cannot read private caches. Export allowlisted
        # diagnostics rather than sending it an inaccessible filesystem path.
        try:
            key, _ = prediction_identity(spec, year, settings, protocol)
            folder = ROOT / "results/cache" / key
            old = legacy_folder(spec, year, settings)
            if not folder.exists() and old is not None:
                folder = old
            exc.development_failure = failure_summary(folder, year, exc)
        except Exception:
            pass  # Preserve the original error if even provenance is unavailable.
        raise


def _forecast_year_bound(spec, year, settings, protocol):
    if year not in YEARS or settings["development_years"] != list(YEARS):
        raise ValueError("The four development years are fixed; final outcomes remain reserved.")
    with scientific_execution():
        old = legacy_folder(spec, year, settings)
        if old and (old / "predictions.rds").exists() and (old / "forecast_audit.json").exists():
            with (old / "evaluation.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return score_saved(old, year, settings, spec)
        previous = previous_structured_folder(spec, year, settings, protocol)
        if previous is not None and (previous / "predictions.rds").exists() and (previous / "forecast_audit.json").exists():
            with (previous / "evaluation.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return score_saved(previous, year, settings, spec)
        if old is None:
            old = previous
        key, provenance = prediction_identity(spec, year, settings, protocol)
        folder = ROOT / "results/cache" / key
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "evaluation.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            immutable_json(folder / "provenance.json", provenance)
            save_json(folder / "specification.json", spec)
            save_json(folder / "settings.json", settings)
            implementation = {
                "protocol": "multiobjective-v1", "prediction_identity": key,
                "files": {name: sha(ROOT / name) for name in (
                    "R/empirical.R", "R/forecast.R", "R/network_specification_v2.R",
                    "R/forecast_multiobjective.R", "configs/effect-catalog-v2.json")},
                "note": "Implementation/catalog hashes document execution; scientific semantic versions and actual inputs determine reuse."}
            if not (folder / "implementation_provenance.json").exists():
                save_json(folder / "implementation_provenance.json", implementation)
            if old and not (folder / "training_checkpoint_reuse.json").exists():
                copied = []
                for source in [*old.glob("fit-attempt-*.rds"), old / "accepted_fit.rds", old / "fit_diagnostics.json"]:
                    destination = folder / source.name
                    if source.exists() and not destination.exists():
                        shutil.copy2(source, destination)
                        copied.append({"file": source.name, "sha256": sha(source)})
                save_json(folder / "training_checkpoint_reuse.json", {
                    "source": str(old), "files": copied,
                    "reason": "Same canonical native specification, past observations, software, estimation settings and seeds; parameter-aware native continuation preserves original derivative order."})
            if not ((folder / "predictions.rds").exists() and (folder / "forecast_audit.json").exists()):
                if deadline_reached():
                    raise ExecutionWindowPaused(f"Execution window ended before the next fit/forecast for {year}; resume {folder}.")
                marker = folder / "checkpoint.json"
                if marker.exists():
                    marker.unlink()
                with (folder / "implementation_invocations.jsonl").open("a") as stream:
                    stream.write(json.dumps({"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                              **implementation}, allow_nan=False) + "\n")
                try:
                    legacy.run_r([ROOT / "R/forecast_multiobjective.R", "--spec", folder / "specification.json",
                                  "--target", year, "--output", folder, "--settings", folder / "settings.json"],
                                 folder, "fit_and_forecast",
                                 settings["estimation"]["timeout_seconds"] * settings["estimation"]["max_attempts"]
                                 + settings["forecast"]["timeout_seconds"])
                except RuntimeError as exc:
                    if marker.exists() and read_json(marker).get("status") == "paused_execution_window":
                        raise ExecutionWindowPaused(f"Saved native checkpoint at {folder}; {read_json(marker)}") from exc
                    raise
            return score_saved(folder, year, settings, spec)


def evaluate(program_path, results_dir):
    out = Path(results_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    start, annual, private, spec, source, science = time.monotonic(), {}, {}, None, None, None
    try:
        require_search_open(ROOT)
        science = scientific_identity(ROOT)
        require_expected_fingerprint(science)
        protocol = read_json(PROTOCOL)
        settings = read_json(ROOT / protocol["prediction_settings"])
        spec, source = read_program(program_path)
        baseline_spec, _ = read_program(REFERENCE)
        hypothesis = hypothesis_record(source, spec, baseline_spec, spec_hash(spec), science["sha256"])
        immutable_json(out / "hypothesis.json", hypothesis)
        for year in YEARS:
            baseline = forecast_year(baseline_spec, year, settings, protocol)
            candidate = baseline if spec == baseline_spec else forecast_year(spec, year, settings, protocol)
            bdir, cdir = Path(baseline["cache_directory"]), Path(candidate["cache_directory"])
            if sha(bdir / "eligibility_mask.rds") != sha(cdir / "eligibility_mask.rds"):
                raise RuntimeError(f"Common undirected eligibility mask differs for {year}.")
            if candidate["spending"]["n"] != baseline["spending"]["n"]:
                raise RuntimeError(f"Spending comparison mask differs for {year}.")
            annual[str(year)] = {
                "valid": True,
                "J1": candidate["primary"]["pr_auc"] - baseline["primary"]["pr_auc"],
                "J2": baseline["primary"]["brier"] - candidate["primary"]["brier"],
                "J3": baseline["spending"]["rmse"] - candidate["spending"]["rmse"],
                "candidate_pr_auc": candidate["primary"]["pr_auc"], "reference_pr_auc": baseline["primary"]["pr_auc"],
                "candidate_brier": candidate["primary"]["brier"], "reference_brier": baseline["primary"]["brier"],
                "candidate_spending_rmse": candidate["spending"]["rmse"], "reference_spending_rmse": baseline["spending"]["rmse"],
                "candidate_roc_auc": candidate["primary"]["roc_auc"], "eligible_pairs": candidate["primary"]["n"],
                "spending_countries": candidate["spending"]["n"],
                "formation": candidate["formation"], "dissolution": candidate["dissolution"],
                "persistence": candidate["persistence"],
                "network_diagnostics": candidate["network_diagnostics"],
                "structural_predictive_checks": candidate["structural_predictive_checks"],
                "calibration": candidate["calibration"],
                "fit_diagnostics": fit_summary(candidate["fit_diagnostics"]),
                "reference_fit_diagnostics": fit_summary(baseline["fit_diagnostics"]),
                "candidate_structural_coefficients": candidate["structural_coefficients"],
                "reference_structural_coefficients": baseline["structural_coefficients"],
            }
            private[str(year)] = {"candidate": candidate, "reference": baseline}
            # Useful on a later pause/failure; this is not partial candidate fitness.
            save_json(out / "annual_progress.json", {"protocol": "multiobjective-v1", "valid": False,
                      "canonical_sha256": spec_hash(spec), "completed_years": annual,
                      "note": "No candidate objectives until all four required annual comparisons are valid."})
        if set(annual) != {str(year) for year in YEARS}:
            raise RuntimeError("A complete fitness requires every development target.")
        objectives = {key: math.fsum(row[key] for row in annual.values()) / 4 for key in ("J1", "J2", "J3")}
        score = 2 + (objectives["J1"] + objectives["J2"] + objectives["J3"] / 10) / 3
        if not all(math.isfinite(value) for value in [score, *objectives.values()]):
            raise RuntimeError("Nonfinite multiobjective fitness.")
        old_terms = {json.dumps(t, sort_keys=True) for t in baseline_spec["network_effects"]}
        new_terms = {json.dumps(t, sort_keys=True) for t in spec["network_effects"]}
        feedback = (f"Network-objective change: added {sorted(new_terms-old_terms)}; removed {sorted(old_terms-new_terms)}. "
                    + "; ".join(f"{key}={value:+.12f}" for key, value in objectives.items())
                    + f". Stable auxiliary score={score:.12f}; Pareto selection uses all three objectives. "
                    + " ".join(f"{year}: PR={r['candidate_pr_auc']:.12f} (delta {r['J1']:+.12f}), "
                                f"Brier={r['candidate_brier']:.12f} (improvement {r['J2']:+.12f}), "
                                f"spending RMSE={r['candidate_spending_rmse']:.12f} (improvement {r['J3']:+.12f})."
                                for year, r in annual.items())
                    + " " + fitted_coefficient_feedback(annual)
                    + " All coefficients were jointly estimated with Model 3 controls and spending structure retained. "
                    "Formation/dissolution diagnostics distinguish new agreements from persistence. "
                    "Brier measures probability MSE; spending RMSE is in ordinal categories. "
                    "Fresh-randomness sensitivity remains pending; adjacent years and dependent dyads limit evidence. "
                    "No final-year outcomes were used; predictive gains do not establish efficiency or security.")
        public = {"protocol": "multiobjective-v1", "status": "complete", "valid": True,
                  **objectives, "raw_F": objectives["J1"], "years": annual,
                  "canonical_sha256": spec_hash(spec), "canonical_specification": spec,
                  "complexity": complexity(spec)["estimated_network_terms"], "structural_complexity": complexity(spec),
                  "runtime_seconds": time.monotonic() - start, "scientific_fingerprint": science["sha256"]}
        save_json(out / "metrics.json", {"combined_score": score, "public": public,
                  "private": {"annual_artifacts": {year: {role: data["cache_directory"] for role, data in values.items()}
                                                     for year, values in private.items()}}, "text_feedback": feedback})
        save_json(out / "correct.json", {"correct": True, "error": ""})
        save_json(out / "canonical_specification.json", spec)
        archive = ROOT / "results/evaluations/multiobjective-v1" / spec_hash(spec)
        archive.mkdir(parents=True, exist_ok=True)
        (archive / "candidate.py").write_text(source)
        save_json(archive / "annual_results.json", private)
        save_json(archive / "protocol.json", protocol)
        for name in ("metrics.json", "correct.json", "canonical_specification.json", "hypothesis.json"):
            shutil.copy2(out / name, archive / name)
        return 0
    except Exception as exc:
        paused = isinstance(exc, ExecutionWindowPaused)
        status = "paused_execution_window" if paused else "invalid_evaluation"
        error = f"{type(exc).__name__}: {exc}"
        diagnosis = getattr(exc, "development_failure", None)
        public = {"protocol": "multiobjective-v1", "status": status, "valid": False,
                  "J1": None, "J2": None, "J3": None, "raw_F": None,
                  "years": annual, "runtime_seconds": time.monotonic() - start}
        if science is not None:
            public["scientific_fingerprint"] = science["sha256"]
        if diagnosis is not None:
            public["failure_diagnostics"] = diagnosis
        if spec is not None:
            public.update(canonical_sha256=spec_hash(spec), canonical_specification=spec,
                          complexity=complexity(spec)["estimated_network_terms"])
        save_json(out / "metrics.json", {"combined_score": None, "public": public, "private": {},
                  "text_feedback": ("PAUSED; resume the same candidate from saved numerical checkpoints. " if paused else
                                    "INVALID evaluation; no scientific objective vector or loss. ") + (failure_text(diagnosis) if diagnosis else error)})
        save_json(out / "correct.json", {"correct": False, "error": error})
        (out / "error.log").write_text(traceback.format_exc())
        return 75 if paused else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fixed multiobjective-v1 scientific evaluator")
    parser.add_argument("--program_path", type=Path, required=True)
    parser.add_argument("--results_dir", type=Path, required=True)
    parser.add_argument("--protocol", choices=("multiobjective-v1",), default="multiobjective-v1")
    arguments = parser.parse_args()
    raise SystemExit(evaluate(arguments.program_path, arguments.results_dir))
