#!/usr/bin/env python3
"""Conventional specification search through the selected fixed evaluator.

Legacy PR uses its original finite enumeration; multiobjective-v1 uses a
deterministic local search over the same native grammar as Shinka.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
import tokenize

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


def multiobjective_native_budget(directory, decoder):
    """Freeze the observed distinct terminal attempts, including invalid ones."""
    directory = directory.resolve()
    resolved = read_json(directory / "resolved_config.json")
    protocol = resolved.get("protocol")
    if protocol != "multiobjective-v1" and not (isinstance(protocol, dict) and protocol.get("version") == "multiobjective-v1"):
        raise ValueError("The comparison must use an actual multiobjective-v1 native run.")
    records, seen, excluded = [], set(), []
    for path in sorted(directory.glob("*/results/correct.json")):
        metrics_path, program = path.parent / "metrics.json", path.parent.parent / "main.py"
        if not metrics_path.exists() or not program.exists():
            excluded.append({"path": str(path), "reason": "incomplete artifacts"})
            continue
        correct, metrics = read_json(path), read_json(metrics_path)
        public = metrics.get("public", {})
        if public.get("status") == "paused_execution_window":
            excluded.append({"path": str(path), "reason": "pending numerical work"})
            continue
        if public.get("protocol") != "multiobjective-v1" or type(correct.get("correct")) is not bool:
            excluded.append({"path": str(path), "reason": "not a terminal multiobjective evaluator record"})
            continue
        try:
            spec, _ = decoder.read_program(program)
            identity = "spec:" + decoder.spec_hash(spec)
        except decoder.InvalidSpecification:
            # Invalid declarations still consume attempted-comparison budget.
            # AST/token fingerprints discard comments and cosmetic whitespace;
            # they do not pretend an invalid program defines an estimable model.
            source = program.read_text()
            try:
                normalized = ast.dump(ast.parse(source), include_attributes=False)
            except SyntaxError:
                tokens = []
                try:
                    for token in tokenize.generate_tokens(io.StringIO(source).readline):
                        if token.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.ENCODING, tokenize.ENDMARKER):
                            tokens.append((token.type, "" if token.type in (tokenize.INDENT, tokenize.DEDENT) else token.string))
                except (tokenize.TokenError, IndentationError):
                    pass
                normalized = repr(tokens) if tokens else source.strip()
            identity = "invalid-source:" + hashlib.sha256(normalized.encode()).hexdigest()
        if identity in seen:
            excluded.append({"path": str(path), "reason": "canonical or cosmetic duplicate", "identity": identity})
            continue
        seen.add(identity)
        records.append({"identity": identity, "valid": correct["correct"] is True and public.get("valid") is True,
                        "correctness_file": str(path), "metrics_sha256": sha(metrics_path),
                        "program_sha256": sha(program), "error": correct.get("error", "")})
    return {"directory": str(directory), "observed_utc": now(), "attempt_limit_including_reference": len(records),
            "distinct_valid_attempts": sum(record["valid"] for record in records),
            "distinct_invalid_attempts": sum(not record["valid"] for record in records),
            "records": records, "excluded": excluded,
            "counting_rule": "One distinct completed specification or invalid-program fingerprint consumes one slot, whether scientifically valid or invalid. Pending work and cosmetic/canonical repeats consume no additional slots. The reference counts if actually observed."}


def multiobjective_neighbors(spec, catalog):
    """Deterministic local edits over the full grammar, not a finite model list.

    All declared atom families/covariates participate. Integer parameters have
    local +/-1 and geometric steps, so parameter values are not a tiny subcatalog.
    Higher-order terms arise by extending/replacing/deleting native factors.
    """
    effects = spec["network_effects"]
    atoms = []
    for effect, descriptor in catalog["effects"].items():
        rule = descriptor["parameter_rule"]
        values = rule.get("values", [69 if effect in ("gwesp", "Jout") else 1])
        if rule["kind"] == "degree_root_switch":
            values = [1, 2]
        if rule["kind"] == "ignored":
            values = [rule["canonical"]]
        covariates = catalog["covariates"][descriptor["covariate_kind"]] if descriptor.get("covariate_kind") else [None]
        for parameter, covariate in itertools.product(values, covariates):
            atoms.append({"effect": effect, "parameter": parameter,
                          **({"covariate": covariate} if covariate else {})})
    structural = [atom for atom in atoms if catalog["effects"][atom["effect"]]["role"] == "network"]
    modifiers = [atom for atom in atoms if catalog["effects"][atom["effect"]]["role"] == "modifier"]
    closure = {"transTriads", "transTies", "gwesp", "Jout", "cycle4ND"}

    def changed(index, term, label):
        return {"schema_version": 2, "network_effects": effects[:index] + ([term] if term is not None else []) + effects[index + 1:]}, label

    # Compare alternative closure responses first, then other operator changes.
    for index, term in enumerate(effects):
        if term.get("effect") in closure:
            for atom in structural:
                if atom["effect"] in closure and atom != term:
                    yield changed(index, atom, "replace closure operator")
    for index, term in enumerate(effects):
        factors = term.get("product", [term])
        for position, factor in enumerate(factors):
            k = factor["parameter"]
            rule = catalog["effects"][factor["effect"]]["parameter_rule"]
            parameters = rule.get("values", [])
            if rule["kind"] == "degree_root_switch":
                parameters = [1, 2]
            elif rule["kind"] in ("positive_integer", "truncation_knot", "gwesp_integer"):
                parameters = sorted({k - 1, k + 1, k // 2, max(1, k * 2)})
            for parameter in parameters:
                if parameter == k:
                    continue
                atom = {**factor, "parameter": parameter}
                replacement = {"product": factors[:position] + [atom] + factors[position + 1:]} if "product" in term else atom
                yield changed(index, replacement, "change native functional parameter")
        yield changed(index, None, "delete objective term")
        for atom in structural:
            if atom != term:
                yield changed(index, atom, "replace objective term with native atom")
        if "product" in term:
            for position in range(len(factors)):
                for atom in atoms:
                    yield changed(index, {"product": factors[:position] + [atom] + factors[position + 1:]}, "replace native product factor")
                reduced = factors[:position] + factors[position + 1:]
                yield changed(index, {"product": reduced} if len(reduced) > 1 else reduced[0], "remove native product factor")
        if len(factors) < 3:
            for atom in atoms:
                yield changed(index, {"product": factors + [atom]}, "extend native product")
    for atom in structural:
        yield {"schema_version": 2, "network_effects": effects + [atom]}, "add native structural atom"
    # Adding a product while preserving its main structural effect permits
    # conditional mechanisms; all original empirical controls remain included.
    for term in effects:
        factors = term.get("product", [term])
        if len(factors) < 3:
            for modifier in modifiers:
                yield {"schema_version": 2, "network_effects": effects + [{"product": factors + [modifier]}]}, "add covariate-modified mechanism"
    # This includes non-ego dyadic structural products such as GWESP x Jaccard,
    # not merely covariate modifiers. The common decoder admits only the actual
    # native-compatible pairs. Existing pairs can subsequently gain a third atom.
    for left, right in itertools.combinations_with_replacement(atoms, 2):
        yield {"schema_version": 2, "network_effects": effects + [{"product": [left, right]}]}, "add native two-factor product"


def multiobjective_work_snapshot(spec, helper, settings, protocol):
    """Read existing numerical event/fit records for actual cost attribution."""
    baseline, _ = helper.read_program(helper.REFERENCE)
    folders, fit_records, events = set(), {}, {}
    for model in (baseline, spec):
        for year in helper.YEARS:
            key, _ = helper.prediction_identity(model, year, settings, protocol)
            folders.add(ROOT / "results/cache" / key)
            old = helper.legacy_folder(model, year, settings)
            if old is not None:
                folders.add(old)
    for folder in sorted(folders):
        if (folder / "events.jsonl").exists():
            for line in (folder / "events.jsonl").read_text().splitlines():
                event = json.loads(line)
                if event.get("status") != "running" and "elapsed_seconds" in event:
                    events[str(event["invocation_id"])] = {"stage": event["stage"], "seconds": event["elapsed_seconds"],
                                                          "status": event["status"], "exit_code": event.get("exit_code"), "folder": str(folder)}
        if (folder / "fit_diagnostics.json").exists():
            # Copied checkpoints have identical estimates/diagnostics. Deduplicate
            # them without charging their historical fitting cost to this search.
            for row in read_json(folder / "fit_diagnostics.json"):
                if row.get("elapsed_seconds") is None:
                    continue
                identity = {key: row.get(key) for key in ("attempt", "elapsed_seconds", "estimates", "standard_errors")}
                key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
                fit_records[key] = {"seconds": row["elapsed_seconds"], "valid": row.get("valid"), "attempt": row.get("attempt")}
    return {"events": events, "fits": fit_records}


def multiobjective_front(rows):
    valid = [row for row in rows if row["valid"]]
    return [row["canonical_sha256"] for row in valid if not any(
        all(other[key] >= row[key] for key in ("J1", "J2", "J3"))
        and any(other[key] > row[key] for key in ("J1", "J2", "J3"))
        for other in valid)]


def run_multiobjective(args):
    """Conventional comparison through the same trusted scientific evaluator."""
    from scripts import multiobjective_evaluation as helper
    from scripts import network_specification_v2 as decoder

    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be positive and includes the reference.")
    if args.limit is None and args.native_results_dir is None:
        raise ValueError("Declare --limit or use --native-results-dir for an observed comparison budget.")
    output = args.results_dir.resolve()
    if output == ROOT / "results/conventional_search":
        output = output / "multiobjective-v1"
    output.relative_to(ROOT / "results")
    path = output / "results.json"
    state = read_json(path) if path.exists() else None
    protocol = read_json(helper.PROTOCOL)
    settings = read_json(ROOT / protocol["prediction_settings"])
    catalog = read_json(decoder.CATALOG)
    baseline, _ = decoder.read_program(helper.REFERENCE)
    if state is None:
        native = multiobjective_native_budget(args.native_results_dir, decoder) if args.native_results_dir else None
        caps = ([args.limit] if args.limit is not None else []) + ([native["attempt_limit_including_reference"]] if native else [])
        cap = min(caps)
        if cap < 1:
            raise ValueError("No completed distinct native attempts are available for a conventional comparison budget.")
        state = {"protocol": "multiobjective-v1", "scientific_protocol": protocol, "estimation_and_forecast_settings": settings,
                 "catalog_version": catalog["version"], "method": "deterministic first-improvement local specification search",
                 "requested_limit": args.limit, "attempt_limit_including_reference": cap, "native_comparison": native,
                 "ordering": "Closure replacements; native parameter +/-1, half/double or fixed alternative; deletions and atom replacements; factor replacements/removals/extensions; structural additions; covariate-modified mechanisms and all native-compatible two-factor products (including non-ego dyadic structural interactions). Catalog order and canonical incumbent order break move-order ties.",
                 "acceptance": "Move to the first strictly larger fixed auxiliary score 2+(J1+J2+J3/10)/3; retain every valid observed Pareto-nondominated vector separately. Exact ties retain the incumbent.",
                 "budget_rule": "One distinct terminal candidate attempt including the reference, valid or invalid. A paused candidate remains pending and resumes in the same slot. Canonical repeats and structurally inadmissible unevaluated edits do not enlarge the comparison budget.",
                 "limitations": "A deterministic local heuristic with fixed scalar preferences and order effects, not exhaustive grammar coverage or a proof of superiority. Disconnected Pareto trade-offs and improvements requiring several simultaneous edits may be missed. Shared caches can equalize attempted-specification counts without equalizing computation; report actual numerical effort separately.",
                 "evaluations": [], "incumbent": None, "pending": None, "status": "declared", "complete": False}
    else:
        expected_native = str(args.native_results_dir.resolve()) if args.native_results_dir else None
        frozen_native = state.get("native_comparison", {}).get("directory") if state.get("native_comparison") else None
        if (state.get("protocol") != "multiobjective-v1" or state.get("scientific_protocol") != protocol
            or state.get("estimation_and_forecast_settings") != settings or state.get("catalog_version") != catalog["version"]
            or state.get("requested_limit") != args.limit or frozen_native != expected_native):
            raise ValueError("Resume requires the same scientific protocol and frozen comparison budget; use a separate results directory for a different comparison.")
    if not args.execute:
        print(json.dumps({"method": state["method"], "attempt_limit_including_reference": state["attempt_limit_including_reference"],
                          "results_directory": str(output), "executed": False}, indent=2))
        return 0
    hours = args.window_hours
    if hours is None:
        hours = read_json(ROOT / "shinka/native_multiobjective_config.json")["resource_policy"]["default_session_hours"]
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("--window-hours must be finite and positive.")
    deadline = time.time() + hours * 3600
    if os.environ.get("SHINKA_EXECUTION_DEADLINE"):
        existing_deadline = float(os.environ["SHINKA_EXECUTION_DEADLINE"])
        if not math.isfinite(existing_deadline):
            raise ValueError("SHINKA_EXECUTION_DEADLINE must be finite Unix seconds.")
        deadline = min(deadline, existing_deadline)
    os.environ["SHINKA_EXECUTION_DEADLINE"] = str(deadline)
    with execution_lock():
        # The shared numerical lock may have been occupied by another session.
        # Its completed conventional checkpoint, if any, takes precedence over
        # the copy read before waiting; the declared comparison stays unchanged.
        if path.exists():
            latest = read_json(path)
            if any(latest.get(key) != state.get(key) for key in (
                "protocol", "scientific_protocol", "estimation_and_forecast_settings",
                "catalog_version", "requested_limit", "attempt_limit_including_reference", "native_comparison")):
                raise ValueError("The conventional comparison changed while waiting for the numerical lock.")
            state = latest
        while len(state["evaluations"]) < state["attempt_limit_including_reference"]:
            if helper.deadline_reached():
                state.update(status="paused_execution_window", updated_utc=now(), complete=False)
                save_json(path, state)
                return 75
            pending = state["pending"]
            if pending is None:
                seen = {row["canonical_sha256"] for row in state["evaluations"]}
                chosen = None
                if not state["evaluations"]:
                    chosen = baseline, "reference Model 3"
                elif state["incumbent"] is None:
                    state.update(status="invalid_reference", updated_utc=now(), complete=False)
                    save_json(path, state)
                    return 1
                else:
                    incumbent = next(row for row in state["evaluations"] if row["canonical_sha256"] == state["incumbent"])
                    for proposal, move in multiobjective_neighbors(incumbent["specification"], catalog):
                        try:
                            proposal = decoder.validate_spec(proposal, catalog)
                        except decoder.InvalidSpecification:
                            continue
                        if decoder.spec_hash(proposal) not in seen:
                            source = "def build_network_spec(allowed_schema):\n    return " + repr(proposal) + "\n"
                            if len(source.encode()) <= decoder.PROGRAM_BYTE_LIMIT:
                                chosen = proposal, move
                                break
                if chosen is None:
                    state.update(status="local_neighborhood_exhausted", updated_utc=now(), complete=True)
                    save_json(path, state)
                    return 0
                spec, move = chosen
                key = decoder.spec_hash(spec)
                folder = output / "specifications" / key
                folder.mkdir(parents=True, exist_ok=True)
                program = folder / "candidate.py"
                source = "def build_network_spec(allowed_schema):\n    return " + repr(spec) + "\n"
                if program.exists() and program.read_text() != source:
                    raise ValueError("A pending conventional candidate source changed.")
                program.write_text(source)
                pending = {"canonical_sha256": key, "specification": spec, "move": move,
                           "parent": state["incumbent"], "results_directory": str(folder),
                           "driver_seconds": 0.0, "work_before": multiobjective_work_snapshot(spec, helper, settings, protocol)}
                state["pending"] = pending
                state.update(status="evaluating", updated_utc=now(), complete=False)
                save_json(path, state)
            folder = Path(pending["results_directory"])
            program = folder / "candidate.py"
            spec, _ = decoder.read_program(program)
            if decoder.spec_hash(spec) != pending["canonical_sha256"]:
                raise ValueError("Pending candidate identity changed; refusing to advance or restart another model.")
            reused = False
            if (folder / "correct.json").exists() and (folder / "metrics.json").exists():
                saved = read_json(folder / "metrics.json")
                reused = saved.get("public", {}).get("status") in ("complete", "invalid_evaluation")
            if helper.deadline_reached():
                state.update(status="paused_execution_window", updated_utc=now(), complete=False)
                save_json(path, state)
                return 75
            started = time.monotonic()
            exit_code = 0 if reused else helper.evaluate(program, folder)
            pending["driver_seconds"] += time.monotonic() - started
            metrics, correct = read_json(folder / "metrics.json"), read_json(folder / "correct.json")
            public = metrics["public"]
            after = multiobjective_work_snapshot(spec, helper, settings, protocol)
            before = pending["work_before"]
            new_events = [value for key, value in after["events"].items() if key not in before["events"]]
            new_fits = [value for key, value in after["fits"].items() if key not in before["fits"]]
            effort = {"new_native_fit_attempts": len(new_fits), "new_native_fit_seconds": math.fsum(row["seconds"] for row in new_fits),
                      "new_r_process_seconds": math.fsum(row["seconds"] for row in new_events), "new_r_processes": new_events,
                      "shared_cache_only": not new_events and not new_fits,
                      "note": "Fitting seconds come from newly completed native diagnostics; R process time additionally includes forecasting/scoring and failed or interrupted processes. Interrupted fits without final diagnostics remain represented by process time."}
            pending["effort"] = effort
            if exit_code == 75 or public.get("status") == "paused_execution_window":
                state.update(status="paused_execution_window", updated_utc=now(), complete=False)
                save_json(path, state)
                return 75
            valid = correct.get("correct") is True and public.get("valid") is True
            if valid and (public.get("canonical_sha256") != pending["canonical_sha256"]
                          or set(public.get("years", {})) != {str(year) for year in helper.YEARS}
                          or not all(type(public.get(key)) in (int, float) and math.isfinite(public[key]) for key in ("J1", "J2", "J3"))
                          or type(metrics.get("combined_score")) not in (int, float) or not math.isfinite(metrics["combined_score"])):
                raise ValueError("Completed evaluator output must identify this specification, all four development years and three finite scientific objectives.")
            if valid and abs(metrics["combined_score"] - (2 + (public["J1"] + public["J2"] + public["J3"] / 10) / 3)) > 1e-12:
                raise ValueError("The conventional preference must equal the declared multiobjective auxiliary score.")
            row = {key: pending[key] for key in ("canonical_sha256", "specification", "move", "parent", "results_directory", "driver_seconds")}
            row.update(valid=valid, error=correct.get("error", ""), completed_utc=now(), effort=effort,
                       reused_terminal_evaluation=reused, evaluator_last_call_seconds=public.get("runtime_seconds"),
                       combined_score=metrics["combined_score"] if valid else None,
                       **{key: public[key] if valid else None for key in ("J1", "J2", "J3")})
            state["evaluations"].append(row)
            if valid:
                incumbent = next((old for old in state["evaluations"] if old["canonical_sha256"] == state["incumbent"]), None)
                if incumbent is None or row["combined_score"] > incumbent["combined_score"]:
                    state["incumbent"] = row["canonical_sha256"]
            state["pending"] = None
            state.update(pareto_front=multiobjective_front(state["evaluations"]), updated_utc=now(),
                         complete=len(state["evaluations"]) == state["attempt_limit_including_reference"],
                         status="comparison_budget_complete" if len(state["evaluations"]) == state["attempt_limit_including_reference"] else "running")
            save_json(path, state)
            print(json.dumps(row, allow_nan=False), flush=True)
            if len(state["evaluations"]) == 1 and not valid:
                state.update(status="invalid_reference", complete=False)
                save_json(path, state)
                return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", choices=("legacy-pr", "multiobjective-v1"), default="legacy-pr")
    parser.add_argument("--native-results-dir", type=Path, help="Derive the comparison cap from observed native completed attempts, using the selected protocol's counting rule")
    parser.add_argument("--limit", type=int, help="Fixed terminal-attempt cap including the reference; legacy default is 15; multiobjective requires this or observed native results")
    parser.add_argument("--window-hours", type=float, help="Multiobjective cooperative execution window; existing native default applies if omitted")
    parser.add_argument("--results-dir", type=Path, default=ROOT/"results/conventional_search")
    parser.add_argument("--execute", action="store_true", help="Execute comparisons; otherwise describe the multiobjective comparison or save the original legacy plan")
    args = parser.parse_args()
    if args.protocol == "multiobjective-v1":
        return run_multiobjective(args)
    args.limit = 15 if args.limit is None else args.limit
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
