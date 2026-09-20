#!/usr/bin/env python3
"""Exercise native invalid-evaluator loading and SQLite ingestion; no R or LLM."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.environ["SHINKA_PRICING_MODE"] = "offline"
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    from shinka.launch import LocalJobConfig
    from shinka.launch.scheduler import JobScheduler
    from shinka.database import DatabaseConfig, Program, ProgramDatabase
    folder = ROOT / "runs/shinka_infrastructure/native_invalid_contract" / str(time.time_ns())
    folder.mkdir(parents=True)
    sentinel = folder / "MUST_NOT_EXECUTE"
    source = ("from pathlib import Path\n"
              f"Path({str(sentinel)!r}).write_text('UNSAFE EXECUTION')\n"
              "def build_network_spec(allowed_schema):\n"
              "    return {'schema_version': 1, 'network_effects': ['degPlus', 'transTriads']}\n")
    candidate = folder / "malicious.py"
    candidate.write_text(source)
    result_directory = folder / "evaluation"
    result_directory.mkdir()
    scheduler = JobScheduler("local", LocalJobConfig(eval_program_path=str(ROOT / "evaluate.py"),
                             python_executable=sys.executable, time="00:00:30"), max_workers=1)
    original_cwd = Path.cwd()
    try:
        # Deliberately run from the generation folder to check absolute evaluator paths.
        os.chdir(folder)
        result, elapsed = scheduler.run(str(candidate), str(result_directory))
    finally:
        os.chdir(original_cwd)
        scheduler.shutdown()
    metrics = result["metrics"]
    correct = result["correct"]
    assert correct["correct"] is False and correct["error"]
    assert metrics["combined_score"] is None and metrics["public"]["raw_F"] is None
    assert isinstance(metrics["text_feedback"], str)
    assert not sentinel.exists(), "candidate source was executed"
    database = ProgramDatabase(DatabaseConfig(db_path=str(folder / "invalid_fixture.sqlite"), num_islands=1))
    program = Program(id="invalid-contract-fixture", code=source, combined_score=metrics["combined_score"],
                      public_metrics=metrics["public"], private_metrics=metrics["private"],
                      text_feedback=metrics["text_feedback"], correct=correct["correct"])
    database.add(program)
    restored = database.get(program.id)
    assert restored is not None and restored.combined_score is None and not bool(restored.correct)
    assert database.get_top_programs(correct_only=True) == []
    assert database.get_best_program() is None
    assert database.conn.execute("SELECT COUNT(*) FROM archive").fetchone()[0] == 0
    database.close()
    evidence = {"native_local_scheduler_executed_actual_evaluate_py": True,
                "generation_directory_cwd": str(folder), "evaluator_path_absolute": True,
                "candidate_python_never_executed": True, "correct": False,
                "combined_score": None, "raw_F": None, "native_SQLite_null_preserved": True,
                "invalid_excluded_from_archive_and_best": True, "runtime_seconds": elapsed,
                "no_R_or_model_calls": True, "error": correct["error"]}
    (folder / "checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
