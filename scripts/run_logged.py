#!/usr/bin/env python3
"""Execute a scientific command with durable logs, PID and practical memory use."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import shutil
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        parser.error("Provide a command after --")
    out = args.run_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    invocation = str(time.time_ns())
    resources = out / f"resources-{invocation}.txt"
    if (out / "resources.txt").exists():
        legacy = out / f"resources-preserved-{(out / 'resources.txt').stat().st_mtime_ns}.txt"
        if not legacy.exists():
            shutil.copy2(out / "resources.txt", legacy)
    record = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "command": cmd,
              "invocation_id": invocation, "resources_file": str(resources),
              "cwd": os.getcwd(), "status": "running", "orchestrator_pid": os.getpid()}
    try:
        record["revision"] = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except subprocess.CalledProcessError:
        record["revision"] = "uncommitted initial reconstruction"
    start = time.monotonic()
    with (out / "stdout.log").open("a") as stdout, (out / "stderr.log").open("a") as stderr:
        proc = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(resources), *cmd], stdout=stdout, stderr=stderr)
        record["pid"] = proc.pid
        (out / "process.json").write_text(json.dumps(record, indent=2) + "\n")
        with (out / "events.jsonl").open("a") as events:
            events.write(json.dumps(record) + "\n")
        status = proc.wait()
    if resources.exists():
        shutil.copy2(resources, out / "resources.txt")
    record.update(exit_code=status, status=("completed" if status == 0 else "resumable" if status == 75 else "failed"),
                  elapsed_seconds=time.monotonic()-start, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (out / "process.json").write_text(json.dumps(record, indent=2) + "\n")
    with (out / "events.jsonl").open("a") as events:
        events.write(json.dumps(record) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
