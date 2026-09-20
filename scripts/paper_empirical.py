#!/usr/bin/env python3
"""Materialize and optionally execute original empirical R callers after final testing.

No model settings, rate handling, data preparation, or scoring are rewritten.
The default action prepares an inspectable work copy and launches no R process.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluate import read_json, run_r, save_json, sha
from scripts.resources import scientific_execution

SOURCE = ROOT/"sources/original/IO_Final"
RUNS = ROOT/"results/paper_reproduction"
SELECTION = ROOT/"results/selection/selected.json"
RESERVATION = ROOT/"results/final_test/reservation.json"
FINAL_COMPARISON = ROOT/"results/final_test/comparison.json"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def build_caller(analysis, work):
    source_name = "01.mainPaper.R" if analysis == "main_paper" else "02.appendix.R"
    lines = (SOURCE/source_name).read_text().splitlines(keepends=True)
    if analysis == "main_paper":
        code = "".join(lines)
        ranges = [[1, len(lines)]]
        scope = "Complete original 01.mainPaper.R caller, including descriptive figures, four main SAOM fits and original post-estimation."
    else:
        # These boundaries delimit original top-level statements, not rewritten
        # algorithm calls. The first block supplies the authors' full settings/kp;
        # the second performs their 1990-2008 fit and 2009-2010 validation.
        setup_end = lines.index("## Do some descriptive figures of DV distribution\n")
        prediction_start = lines.index("## Asess GOF with out-of-sample predictions. Set new parameters.\n")
        if setup_end >= prediction_start:
            raise RuntimeError("Original appendix caller boundaries are inconsistent.")
        code = "".join(lines[:setup_end]+lines[prediction_start:])
        ranges = [[1, setup_end], [prediction_start+1, len(lines)]]
        scope = "Original appendix setup plus prediction section; preceding distribution plots, robustness fits and structural-zero GOF are not executed. The complete untouched 00.gof.predict script, including its regression comparisons/importance outputs, is executed."
    placeholder = 'wd <- c("YourDirectoryHere")'
    if code.count(placeholder) != 1:
        raise RuntimeError("Expected exactly one original working-directory placeholder.")
    code = code.replace(placeholder, "wd <- c("+json.dumps(str(work))+")")
    return code, {"original_caller": source_name, "copied_line_ranges_inclusive": ranges,
                  "scope": scope, "text_substitution": "Only the original YourDirectoryHere path is replaced in copied statements."}


def materialize(analysis, output):
    output.relative_to(RUNS)
    work = output/"work"
    work.mkdir(parents=True, exist_ok=True)
    source_manifest = read_json(ROOT/"sources/manifest.json")
    if sha(ROOT/"sources/archive/IO_Final.zip") != source_manifest["sha256"]:
        raise RuntimeError("Replication archive checksum differs from its recorded provenance.")
    source_hashes = {}
    for relative, expected in source_manifest["source_files"].items():
        relative_path = Path(relative)
        if relative_path.parts[0] != "IO_Final":
            raise RuntimeError("Unexpected archive source root.")
        relative_path = Path(*relative_path.parts[1:])
        source = SOURCE/relative_path
        if sha(source) != expected:
            raise RuntimeError(f"Untouched replication source changed: {source}")
        destination = work/relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if sha(destination) != expected:
                raise RuntimeError(f"Existing work-copy source differs; use a new run directory: {destination}")
        else:
            temporary = destination.with_name(destination.name+".copying")
            shutil.copy2(source, temporary)
            temporary.replace(destination)
        source_hashes[str(relative_path)] = expected
    for directory in ("output/main", "output/appendix", "output/abm", "figures_tables_main", "figures_tables_appendix"):
        (work/directory).mkdir(parents=True, exist_ok=True)
    code, extraction = build_caller(analysis, work)
    caller = work/("run_original_"+analysis+".R")
    if caller.exists() and caller.read_text() != code:
        raise RuntimeError("Generated caller changed; use a new run directory instead of overwriting it.")
    if not caller.exists():
        caller.write_text(code)
    plan = {"schema_version": 1, "mode": "paper_reproduction", "analysis": analysis,
            "profile": "original_source_settings", "source_archive_sha256": source_manifest["sha256"],
            "untouched_workcopy_files": source_hashes, "generated_caller": str(caller),
            "generated_caller_sha256": sha(caller), "caller_extraction": extraction,
            "country_sample_reduced": False, "source_settings_changed": False,
            "original_validation_rate_handling_preserved": True if analysis == "appendix_prediction" else None,
            "original_symmetric_scoring_preserved": True if analysis == "appendix_prediction" else None,
            "execution_gate": "Completed final-test comparison with matching locked selection is required before any original empirical R execution.",
            "checkpoint_support": "No per-call or within-fit resumption. Original save() outputs are preserved but the shipped caller re-estimates on restart. Retry only in a new run directory.",
            "r_command_after_gate": [str(ROOT/"environment/run-r"), str(caller)],
            "working_directory": str(ROOT),
            "environment_versions_sha256": sha(ROOT/"environment/versions.json"),
            "environment_lock_sha256": sha(ROOT/"environment/conda-linux-64.explicit.txt")}
    plan_path = output/"prepared.json"
    if plan_path.exists() and read_json(plan_path) != plan:
        raise RuntimeError("Existing preparation uses a different source/environment; select a new run directory.")
    if not plan_path.exists():
        save_json(plan_path, plan)
    return caller, plan


def completed_final_gate():
    """Checks saved evidence only; does not open or hash the 2010 target packet."""
    if not all(path.is_file() for path in (SELECTION, RESERVATION, FINAL_COMPARISON)):
        raise RuntimeError("Original empirical scripts use 2010 data. Execution is reserved until scripts/final_test.py run has completed for a sealed selection.")
    selected = read_json(SELECTION)
    reservation = read_json(RESERVATION)
    final = read_json(FINAL_COMPARISON)
    if (SELECTION.stat().st_mode & 0o222
            or reservation.get("selection_sha256") != sha(SELECTION)
            or reservation.get("outcomes_accessed") is not True
            or not reservation.get("target_sha256")
            or selected.get("status") != "locked_before_final_access"
            or selected.get("final_outcomes_accessed_at_selection") is not False
            or final.get("status") != "complete" or final.get("target") != 2010
            or final.get("selection", {}).get("sha256") != sha(SELECTION)
            or final.get("canonical_specification") != selected.get("canonical_specification")):
        raise RuntimeError("Final-test completion/selection evidence is incomplete or inconsistent.")
    for field in ("baseline_pr_auc", "candidate_pr_auc"):
        value = final.get(field)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise RuntimeError("Final comparison lacks valid measured PR-AUC values.")
    if (dt.datetime.fromisoformat(selected["selected_utc"])
            >= dt.datetime.fromisoformat(reservation["first_outcome_access_utc"])
            or dt.datetime.fromisoformat(final["completed_utc"])
            < dt.datetime.fromisoformat(reservation["first_outcome_access_utc"])):
        raise RuntimeError("Final comparison chronology does not establish selection before target access.")
    return {"selection_sha256": sha(SELECTION), "final_comparison_sha256": sha(FINAL_COMPARISON),
            "final_completed_utc": final["completed_utc"]}


def run_original(analysis, output, caller, plan, timeout):
    gate = completed_final_gate()
    result_path = output/"execution.json"
    if result_path.exists():
        previous = read_json(result_path)
        if previous.get("status") == "completed" and previous.get("prepared_sha256") == sha(output/"prepared.json"):
            for name, expected in previous["outputs"].items():
                if sha(output/"work"/name) != expected:
                    raise RuntimeError("Completed original-source output changed; restore it instead of relaunching.")
            print(json.dumps({"status": "already_completed", "manifest": str(result_path)}, indent=2))
            return 0
        raise RuntimeError("This original-source attempt already started and is not checkpoint-resumable. Preserve its outputs/logs and retry with a new --run-dir.")
    record = {"status": "running", "started_utc": now(), "analysis": analysis,
              "prepared_sha256": sha(output/"prepared.json"), "final_test_gate": gate,
              "timeout_seconds": timeout, "scientific_reproduction_verified": False}
    save_json(result_path, record)
    try:
        run_r([caller], output, "original_"+analysis, timeout)
        outputs = {str(path.relative_to(output/"work")): sha(path)
                   for directory in ("output", "figures_tables_main", "figures_tables_appendix")
                   for path in (output/"work"/directory).rglob("*") if path.is_file()}
        record.update(status="completed", completed_utc=now(), outputs=outputs,
                      interpretation="Original source exited successfully. Published figures/statistics and convergence still require independent scientific comparison; this is not automatically a successful reproduction.")
        save_json(result_path, record)
        print(json.dumps({"status": "completed", "manifest": str(result_path), "scientific_reproduction_verified": False}, indent=2))
        return 0
    except BaseException as exc:
        record.update(status="interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
                      finished_utc=now(), error=f"{type(exc).__name__}: {exc}")
        save_json(result_path, record)
        (output/"execution_error.log").write_text(traceback.format_exc())
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", choices=["main_paper", "appendix_prediction"], required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--execute", action="store_true", help="Execute only after the reserved final comparison is complete")
    parser.add_argument("--timeout-seconds", type=int, default=604800, help="Outer command timeout; original R algorithm settings are unchanged (default seven days)")
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    output = (args.run_dir or RUNS/("original-"+args.analysis)).resolve()
    caller, plan = materialize(args.analysis, output)
    if not args.execute:
        print(json.dumps({"status": "materialized_only", "plan": str(output/"prepared.json"),
                          "caller": str(caller), "r_launched": False,
                          "execution_gate": plan["execution_gate"], "source_scope": plan["caller_extraction"]["scope"]}, indent=2))
        return 0
    completed_final_gate()
    print("Waiting for the serial scientific-work lock; final-test completion will be checked again before R starts.", flush=True)
    with scientific_execution():
        return run_original(args.analysis, output, caller, plan, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
