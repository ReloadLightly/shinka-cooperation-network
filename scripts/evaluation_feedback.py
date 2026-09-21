"""Safe development diagnostics for proposers; never a substitute fitness."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re


def _read(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def failure_summary(folder, year, error):
    """Read only declared fit diagnostics and effect labels, never observations.

    Do not infer OOM from a generic nonzero exit. Signal 9 is an interruption;
    identifying host memory exhaustion needs separate host evidence.
    """
    folder = Path(folder)
    raw = _read(folder / "fit_diagnostics.json", [])
    diagnostics = raw if isinstance(raw, list) else []
    process = _read(folder / "process.json", {})
    checkpoint = _read(folder / "checkpoint.json", {})
    kind = "adapter_or_execution_failure"
    if checkpoint.get("status") == "paused_execution_window":
        kind = "paused_execution_window"
    elif process.get("status") == "timeout":
        kind = "timeout"
    elif process.get("status") == "interrupted" or process.get("exit_code") in (-9, 137):
        kind = "execution_interruption"
    elif diagnostics and diagnostics[-1].get("valid") is False:
        kind = "estimation_not_accepted"
    rows = []
    try:
        with (folder / "training_effects.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
    except OSError:
        pass
    # Native requestedEffects are grouped by dependent variable. The builder's
    # CSV preserves native within-variable order. Missing/ambiguous lengths are
    # explicitly unavailable, never attached to a guessed effect identity.
    names = list(dict.fromkeys(row.get("name") for row in rows))
    ordered = [row for name in names for row in rows if row.get("name") == name]
    attempts = []
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            continue
        record = {key: diagnostic.get(key) for key in (
            "attempt", "nsub", "n3", "seed", "valid", "maximum_absolute_t_ratio",
            "overall_maximum_convergence", "native_ok", "termination", "phase3_complete",
            "finite_identified", "covariance_minimum_eigenvalue", "covariance_condition_number",
            "divergence", "fixed_parameters", "newly_fixed_parameters", "covariance_message")}
        ratios = diagnostic.get("t_ratios", [])
        worst = []
        if isinstance(ratios, list):
            mapping = len(ordered) == len(ratios) and bool(ordered)
            for i in sorted((i for i, value in enumerate(ratios) if finite(value)), key=lambda i: -abs(ratios[i]))[:5]:
                effect = ordered[i] if mapping else {}
                worst.append({"parameter_index_1based": i + 1, "t_ratio": ratios[i],
                              "process": effect.get("name"), "effect": effect.get("shortName"),
                              "parameter": effect.get("parm"), "specification_key": effect.get(".spec_key"),
                              "interaction1": effect.get("interaction1"), "interaction2": effect.get("interaction2"),
                              "mapping": "native dependent-variable grouping of training effects" if mapping else "unavailable"})
        record["worst_t_ratios"] = worst
        attempts.append(record)
    # Error text may contain absolute cache paths. Keep it private in error.log;
    # public feedback uses the exception type plus allowlisted scientific fields.
    return {"target": year, "classification": kind, "exception_type": type(error).__name__,
            "stage": process.get("stage"), "exit_code": process.get("exit_code"),
            "attempts": attempts, "completed_attempts": len(attempts),
            "scientific_fitness": None,
            "limitation": "Convergence failure is not a predictive loss. Host OOM is not inferred from a kill signal. Effect labels are unavailable when native ordering cannot be bound."}


def failure_text(summary):
    text = f"Target {summary['target']}: {summary['classification']}; {summary['completed_attempts']} saved fitting attempts."
    for row in summary["attempts"]:
        text += (f" Attempt {row.get('attempt')}: max|t|={row.get('maximum_absolute_t_ratio')}, "
                 f"overall={row.get('overall_maximum_convergence')}, native_ok={row.get('native_ok')}.")
        for effect in row["worst_t_ratios"][:3]:
            label = effect.get("specification_key") or effect.get("effect") or f"parameter {effect['parameter_index_1based']} (identity unavailable)"
            text += f" {label}: t={effect['t_ratio']}."
    return text + " All scientific objectives remain null; diagnostics may inform another proposal."


def hypothesis_record(source, spec, reference, canonical, fingerprint):
    """Preserve proposer comments verbatim as a hypothesis, not as findings."""
    from scripts.scientific_contract import digest
    # Comments are untrusted scientific assertions, not commands to the evaluator.
    comments = [line.lstrip()[1:].strip() for line in source.splitlines() if line.lstrip().startswith("#")]
    comments = [line for line in comments if not re.fullmatch(r"EVOLVE-BLOCK-(START|END)", line)]
    old = {json.dumps(term, sort_keys=True): term for term in reference["network_effects"]}
    new = {json.dumps(term, sort_keys=True): term for term in spec["network_effects"]}
    return {"version": "development-hypothesis-v1", "canonical_sha256": canonical,
            "scientific_fingerprint": fingerprint, "source_digest": digest(source),
            "added_terms": [new[key] for key in sorted(new.keys() - old.keys())],
            "removed_terms": [old[key] for key in sorted(old.keys() - new.keys())],
            "proposer_comments": comments, "rationale_available": bool(comments),
            "interpretation": "Recorded before this evaluation. Comments are the proposer's hypothesis, not a measured result or causal/policy conclusion. No missing rationale is invented."}
