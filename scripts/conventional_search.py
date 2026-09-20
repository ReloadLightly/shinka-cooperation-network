#!/usr/bin/env python3
"""Deterministic conventional specification enumeration using the fixed evaluator."""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate import BASELINE, evaluate, preflight, read_json, save_json, sha
from scripts.specification import CATALOG, read_program, spec_hash, validate_spec
from scripts.final_test import RESERVATION, checked_settings, comparison, execution_lock, now, protocol_identity, require_development


def ordered_space(catalog, baseline):
    names = sorted(catalog["effects"])
    base = set(baseline["network_effects"])
    rest = set(names)-base
    proposed = [base]
    proposed += [base-{term} for term in sorted(base)]
    proposed += [(base-{old}) | {new} for old in sorted(base) for new in sorted(rest)]
    proposed += [base | {new} for new in sorted(rest)]
    proposed += [set(terms) for size in range(catalog["max_network_effects"]+1)
                 for terms in itertools.combinations(names, size)]
    unique = {}
    for terms in proposed:
        if len(terms) <= catalog["max_network_effects"]:
            spec = validate_spec({"schema_version": catalog["schema_version"], "network_effects": sorted(terms)}, catalog)
            unique.setdefault(spec_hash(spec), spec)
    if len(names) != 4 or catalog["max_network_effects"] != 3 or len(unique) != 15:
        raise RuntimeError("This prespecified search expects exactly four catalog effects and all 15 subsets of size at most three.")
    return list(unique.values())


def observed_native_budget(path):
    """Count actual native evaluator outputs, not configured generations."""
    path = path.resolve()
    if not (path/"resolved_config.json").is_file():
        raise RuntimeError("Native comparison requires its resolved configuration.")
    valid = set()
    failures = 0
    records = []
    for correctness in sorted(path.glob("*/results/correct.json")):
        record = read_json(correctness)
        program = correctness.parent.parent/"main.py"
        item = {"correctness_file": str(correctness), "sha256": sha(correctness)}
        if record.get("correct") is True:
            spec, _ = read_program(program)
            metrics = read_json(correctness.parent/"metrics.json")
            if metrics.get("public", {}).get("canonical_sha256") != spec_hash(spec):
                raise RuntimeError(f"Native program/metrics identity mismatch: {program}")
            valid.add(spec_hash(spec))
            item.update(status="valid", canonical_sha256=spec_hash(spec),
                        program_sha256=sha(program), metrics_sha256=sha(correctness.parent/"metrics.json"))
        elif record.get("correct") is False:
            failures += 1
            item.update(status="failed", error=record.get("error"))
        else:
            raise RuntimeError(f"Malformed native correctness record: {correctness}")
        records.append(item)
    limit = len(valid)+failures
    if not records or limit < 1:
        raise RuntimeError("No actual native evaluation attempts found; configured generations are not evidence.")
    return {"directory": str(path), "resolved_config_sha256": sha(path/"resolved_config.json"),
            "unique_valid_specifications": len(valid), "failed_evaluation_attempts": failures,
            "budget_including_seed": limit, "records": records,
            "counting_rule": "Unique successful mathematical specifications plus every failed evaluator attempt; includes the baseline seed if observed. Repeated successes do not enlarge the budget."}


def verify_frozen_native_budget(value, supplied_path):
    if (value is None) != (supplied_path is None):
        raise RuntimeError("Resume must use the same native comparison option as the frozen plan.")
    if value is None:
        return None
    if supplied_path.resolve() != Path(value["directory"]).resolve():
        raise RuntimeError("Native results directory differs from the frozen comparison.")
    if sha(supplied_path/"resolved_config.json") != value["resolved_config_sha256"]:
        raise RuntimeError("Native resolved configuration changed after the comparison budget was frozen.")
    for item in value["records"]:
        correct = Path(item["correctness_file"])
        if sha(correct) != item["sha256"]:
            raise RuntimeError("A native evaluation used to set the budget changed.")
        if item["status"] == "valid":
            if (sha(correct.parent.parent/"main.py") != item["program_sha256"]
                    or sha(correct.parent/"metrics.json") != item["metrics_sha256"]):
                raise RuntimeError("A native program or its metrics changed after budget freezing.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-results-dir", type=Path, help="Cap by observed native unique-valid specifications plus failed evaluations")
    parser.add_argument("--limit", type=int, default=15, help="Additional fixed cap including the baseline; default exhausts all 15 models")
    parser.add_argument("--results-dir", type=Path, default=ROOT/"results/conventional_search")
    parser.add_argument("--execute", action="store_true", help="Without this flag save only the prespecified plan, after baseline evidence checks")
    args = parser.parse_args()
    if not 1 <= args.limit <= 15:
        raise ValueError("limit must be between 1 and 15 inclusive.")
    output = args.results_dir.resolve()
    output.relative_to(ROOT/"results")
    with execution_lock():
        preflight()
        if RESERVATION.exists() and read_json(RESERVATION).get("outcomes_accessed"):
            raise RuntimeError("Final outcomes were accessed; subsequent specification searches require an explicitly exploratory protocol.")
        settings = checked_settings()
        baseline, _ = read_program(BASELINE)
        baseline_evidence = require_development(baseline, settings)
        catalog = read_json(CATALOG)
        models = ordered_space(catalog, baseline)
        plan_path = output/"plan.json"
        previous_plan = read_json(plan_path) if plan_path.exists() else None
        if previous_plan is None:
            native = observed_native_budget(args.native_results_dir) if args.native_results_dir else None
        else:
            # New native generations do not change an already frozen comparison.
            native = verify_frozen_native_budget(previous_plan["native_comparison"], args.native_results_dir)
        cap = min(args.limit, native["budget_including_seed"] if native else 15)
        plan = {"schema_version": 1, "method": "deterministic exhaustive conventional specification search",
                "protocol": protocol_identity(), "catalog_sha256": sha(CATALOG), "model_count": 15,
                "budget_including_baseline": cap, "requested_limit": args.limit, "native_comparison": native,
                "ordering": "Baseline; each deletion; each replacement; each addition; remaining subsets by size then catalog name. Fixed before scores; no adaptive reordering.",
                "failure_policy": "One attempted specification consumes one budget slot; preserve invalid results without numeric fitness. Native fixed within-fit retries remain unchanged.",
                "models": [{"index": index, "canonical_sha256": spec_hash(spec), "specification": spec}
                           for index, spec in enumerate(models)]}
        if previous_plan is not None and previous_plan != plan:
            raise RuntimeError("Existing conventional plan differs. Use a new results directory for a distinct fixed budget/protocol.")
        if previous_plan is None:
            save_json(plan_path, plan)
        if not args.execute:
            print(json.dumps({"plan": str(plan_path), "budget_including_baseline": cap, "executed": False}, indent=2))
            return 0
        prior_rows = {}
        if (output/"results.json").exists():
            prior = read_json(output/"results.json")
            if prior.get("plan_sha256") != sha(plan_path):
                raise RuntimeError("Previous conventional results refer to a different frozen plan.")
            prior_rows = {row["canonical_sha256"]: row for row in prior["evaluations"]}
        rows = []
        for index, spec in enumerate(models[:cap]):
            folder = output/"specifications"/spec_hash(spec)
            folder.mkdir(parents=True, exist_ok=True)
            program = folder/"candidate.py"
            text = "def build_network_spec(allowed_schema):\n    return " + repr(spec) + "\n"
            if program.exists() and program.read_text() != text:
                raise RuntimeError("Conventional candidate source changed after enumeration.")
            if not program.exists():
                program.write_text(text)
            started = time.monotonic()
            reused_evaluation = (folder/"correct.json").exists()
            if reused_evaluation and not (folder/"metrics.json").exists():
                raise RuntimeError("Completed correctness record has missing metrics; restore original metrics instead of repeating a completed evaluation.")
            if not reused_evaluation:
                evaluate(program, folder)
            correct = read_json(folder/"correct.json")
            metrics = read_json(folder/"metrics.json")
            if type(correct.get("correct")) is not bool:
                raise RuntimeError("Malformed conventional correctness output.")
            previous_row = prior_rows.get(spec_hash(spec), {})
            row = {"index": index, "canonical_sha256": spec_hash(spec), "specification": spec,
                   "valid": correct.get("correct") is True, "error": correct.get("error", ""),
                   "results_directory": str(folder), "reused_evaluation": reused_evaluation,
                   "driver_elapsed_seconds": previous_row.get("driver_elapsed_seconds") if reused_evaluation else time.monotonic()-started,
                   "evaluator_runtime_seconds": metrics["public"].get("runtime_seconds"),
                   "metrics_sha256": sha(folder/"metrics.json"), "correct_sha256": sha(folder/"correct.json"),
                   "raw_F": metrics["public"].get("raw_F") if correct.get("correct") is True else None}
            if previous_row and any(previous_row.get(field) != row[field] for field in ("metrics_sha256", "correct_sha256")):
                raise RuntimeError("A previously completed conventional evaluation changed; refusing to replace its evidence.")
            if row["valid"]:
                if metrics["public"].get("canonical_sha256") != spec_hash(spec):
                    raise RuntimeError("Conventional metrics refer to a different specification.")
                candidate_evidence = require_development(spec, settings)
                expected = comparison(candidate_evidence, baseline_evidence)["raw_F"]
                if (type(row["raw_F"]) not in (int, float) or not math.isfinite(row["raw_F"])
                        or abs(row["raw_F"]-expected) > settings["fitness"]["numerical_tolerance"]):
                    raise RuntimeError("Conventional metrics do not equal the verified four-year mean delta.")
            rows.append(row)
            valid = [r for r in rows if r["valid"]]
            best = sorted(valid, key=lambda r: (-r["raw_F"], len(r["specification"]["network_effects"]), r["canonical_sha256"]))
            save_json(output/"results.json", {"updated_utc": now(), "complete": len(rows)==cap,
                      "plan_sha256": sha(plan_path), "evaluations": rows,
                      "best": best[0] if best else None,
                      "tie_break": "Exact equal raw_F: fewer mutable effects, then canonical hash; no complexity term in fitness.",
                      "comparison_scope": "Same catalog, full four-year estimator/forecast fidelity and attempt-count cap. Shared caches may reduce actual compute; report native and conventional runtime separately."})
            print(json.dumps(row, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
