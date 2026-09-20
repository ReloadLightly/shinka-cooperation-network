#!/usr/bin/env python3
"""Inventory scientific publication artifacts without reading held-out outcomes.

Copies generated work-directory outputs to source_outputs, hashes scientific
artifacts, and reports credential-pattern matches by filename only. Does not
stage files, contact a remote, parse R objects, or change scientific settings.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/publication"
EPHEMERAL = {"evaluation.lock", "r-execution.lock", "campaign_supervisor.lock"}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def stable_read(path):
    """Reject actively changing files instead of claiming an atomic snapshot."""
    for _ in range(3):
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) == (
            after.st_size, after.st_mtime_ns, after.st_ino
        ) and len(content) == after.st_size:
            return content, after
    raise RuntimeError(f"File changed during publication snapshot: {path.relative_to(ROOT)}")


def snapshot(source, destination):
    if source.is_symlink():
        raise RuntimeError("Refusing to publish a symlink as a scientific artifact.")
    content, stat = stable_read(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.read_bytes() != content:
        temporary = destination.with_name(destination.name + ".pending")
        temporary.write_bytes(content)
        temporary.replace(destination)
    return {"source_path": str(source.relative_to(ROOT)),
            "published_path": str(destination.relative_to(ROOT)),
            "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "source_mtime_ns": stat.st_mtime_ns}


def preserve_source_outputs():
    copies = []
    for work in sorted((ROOT / "results/paper_reproduction").glob("*/work")):
        originals = []
        for name in ("output", "figures_tables_main", "figures_tables_appendix"):
            originals.extend(path for path in (work / name).rglob("*") if path.is_file())
        if (work / "cluster.out").is_file():
            originals.append(work / "cluster.out")
        records = [snapshot(path, work.parent / "source_outputs" / path.relative_to(work))
                   for path in sorted(originals)]
        if records:
            manifest_path = work.parent / "source_outputs/provenance.json"
            manifest = {"schema_version": 1, "purpose": "Publication copies of generated original-source outputs; raw inputs and copied source remain excluded.",
                        "source_run": str(work.parent.relative_to(ROOT)), "files": records}
            previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
            manifest["snapshot_utc"] = (previous.get("snapshot_utc")
                                         if previous.get("files") == records else utc())
            write_json(manifest_path, manifest)
            copies.extend(records)
    audit = ROOT / "data/preparation_audit.json"
    if audit.is_file():
        record = snapshot(audit, ROOT / "results/audits/data_preparation.json")
        provenance = {"schema_version": 1, "file": record,
                      "coverage": "R/audit_data.R emits training-only missingness/composition and annual coverage, with no target labels or tie counts."}
        write_json(ROOT / "results/audits/data_preparation_provenance.json", provenance)
        copies.append(record)
    return copies


def excluded_reason(path):
    relative = path.relative_to(ROOT)
    if path.is_symlink():
        return "symlink_not_followed"
    if "work" in relative.parts:
        return "workcopy_input_or_duplicate_output; generated outputs published via source_outputs"
    if set(relative.parts) & {"home", ".codex", ".claude"} or path.name == "auth.json":
        return "authentication_or_private_session_scope"
    if path.name in EPHEMERAL or path.name.endswith((".sqlite-wal", ".sqlite-shm", ".pending")):
        return "ephemeral_lock_or_incomplete_publication"
    if "__pycache__" in relative.parts or path.suffix == ".pyc":
        return "generated_python_cache"
    if relative.parts[:2] == ("results", "final_test"):
        comparison = ROOT / "results/final_test/comparison.json"
        try:
            completed = json.loads(comparison.read_text()).get("status") == "complete"
        except (FileNotFoundError, json.JSONDecodeError):
            completed = False
        if not completed:
            return "final_test_reserved_until_completed_comparison"
    return None


def candidate_paths():
    paths = set()
    for name in ("results", "runs", "logs", "environment/logs"):
        for directory, subdirectories, filenames in os.walk(ROOT / name, followlinks=False):
            subdirectories[:] = [part for part in subdirectories
                                 if part not in {"home", ".codex", ".claude", "__pycache__"}
                                 and Path(directory) / part != OUT]
            paths.update(Path(directory) / filename for filename in filenames
                         if (Path(directory) / filename).is_file())
    for name in ("sources/manifest.json", "sources/metadata/dataverse.json",
                 "sources/archive/IO_Final.zip", "environment/provenance.json",
                 "environment/versions.json", "environment/rsiena-source-integrity.json",
                 "environment/prroc-verification.json", "environment/session-info.txt",
                 "environment/r-packages.tsv", "environment/conda-linux-64.explicit.txt",
                 "shinka/provenance.json", "shinka/security_review.json"):
        if (ROOT / name).is_file():
            paths.add(ROOT / name)
    return sorted(paths)


def category(path):
    relative = path.relative_to(ROOT)
    if relative.parts[:2] == ("results", "cache"):
        return "empirical_fit_cache_and_diagnostics"
    if "checkpoints" in relative.parts:
        return "original_abm_checkpoint"
    if "source_outputs" in relative.parts:
        return "original_source_output_snapshot"
    if relative.parts[0] == "runs":
        return "native_engine_and_adapter_evidence"
    if relative.parts[0] in ("environment", "sources", "shinka"):
        return "environment_or_source_provenance"
    return "scientific_result_or_execution_log"


def credential_scan(paths):
    # Matching contents are never printed or persisted. This heuristic scan does
    # not replace contextual review and cannot decode opaque R serialization.
    patterns = {
        "api_token": rb"(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})",
        "jwt": rb"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}",
        "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "literal_bearer": rb"(?i)authorization[\s\"':=]+bearer[ \t]+[A-Za-z0-9_./+~-]{20,}",
        "credential_assignment": rb"(?i)[\"'](?:access_token|refresh_token|id_token|api_key|password)[\"']\s*:\s*[\"'][A-Za-z0-9_./+~=:-]{20,}[\"']",
        "credential_url": rb"https?://[^\s/:]{2,}:[^\s/@]{4,}@",
    }
    matches = collections.defaultdict(list)
    references = []
    opaque = []
    scanned = 0
    for path in sorted(set(paths)):
        if not path.is_file() or path.is_symlink() or excluded_reason(path):
            continue
        if path.suffix.lower() in (".rds", ".rdata", ".zip", ".gz", ".pdf", ".png"):
            opaque.append(str(path.relative_to(ROOT)))
            continue
        content, _ = stable_read(path)
        scanned += 1
        for label, pattern in patterns.items():
            if re.search(pattern, content):
                matches[label].append(str(path.relative_to(ROOT)))
        if re.search(rb"(?i)(\.codex/(?:auth|sessions)|\.claude/(?:credentials|projects)|auth\.json|access_token|refresh_token|id_token)", content):
            references.append(str(path.relative_to(ROOT)))
    return {"schema_version": 1, "scanned_utc": utc(), "files_scanned": scanned,
            "high_confidence_pattern_matches": dict(matches),
            "auth_or_session_reference_filenames": references,
            "opaque_files_not_credential_decoded": opaque,
            "limitations": "Filename-only heuristic report; opaque R/archive/image artifacts are hashed, not deserialized for credential inspection. Auth-reference matches may be sandbox code or ignore rules, not credentials. No user-home credential/session files were opened."}


def main():
    copied = preserve_source_outputs()
    paths = candidate_paths()
    names = b"\0".join(str(path.relative_to(ROOT)).encode() for path in paths) + b"\0"
    ignored_result = subprocess.run(["git", "check-ignore", "-z", "--stdin"], input=names,
                                    cwd=ROOT, stdout=subprocess.PIPE, check=False)
    if ignored_result.returncode not in (0, 1):
        raise RuntimeError("git check-ignore failed")
    ignored = {name.decode() for name in ignored_result.stdout.split(b"\0") if name}
    included, excluded = [], []
    for path in paths:
        relative = str(path.relative_to(ROOT))
        reason = excluded_reason(path)
        if reason:
            excluded.append({"path": relative, "size_bytes": path.lstat().st_size,
                             "sha256": None, "reason": reason})
            continue
        content, stat = stable_read(path)
        included.append({"path": relative, "size_bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest(),
                         "mtime_ns": stat.st_mtime_ns, "category": category(path),
                         "git_ignored_at_inventory": relative in ignored})
    groups = {}
    for item in included:
        group = groups.setdefault(item["category"], {"files": 0, "bytes": 0})
        group["files"] += 1
        group["bytes"] += item["size_bytes"]
    inventory = {"schema_version": 1, "snapshot_utc": utc(),
                 "scope": "Generated scientific results, fitted snapshots/checkpoints including failures, full logs, native integration evidence, source archive and environment provenance; not an inventory of source code/docs or installed dependencies.",
                 "reserved_outcomes": {"path": "data/targets/2010.rds", "opened_or_hashed_by_this_tool": False},
                 "file_count": len(included), "total_bytes": sum(item["size_bytes"] for item in included),
                 "category_totals": groups,
                 "largest_files": sorted(included, key=lambda item: item["size_bytes"], reverse=True)[:12],
                 "publication_files": included, "excluded_scoped_files": excluded,
                 "copied_generated_outputs": copied,
                 "excluded_dependencies": [".venv-shinka/", "vendor/", "environment/runtime/", "environment/R-library/", "environment/conda-pkgs/", "environment/cache/", "environment/uv-cache/", "shinka/headless/node_modules/", "shinka/models/", "shinka/tools/"],
                 "private_directories_not_traversed": ["home/", ".codex/", ".claude/"],
                 "regenerate_command": "python3 scripts/publication_inventory.py"}
    write_json(OUT / "inventory.json", inventory)
    git_names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    scan_paths = [ROOT / name.decode() for name in git_names.split(b"\0") if name]
    scan_paths = [path for path in scan_paths if OUT not in path.parents]
    scan_paths.extend(ROOT / item["path"] for item in included)
    scan = credential_scan(scan_paths)
    write_json(OUT / "credential_scan.json", scan)
    print(json.dumps({"inventory": str((OUT / "inventory.json").relative_to(ROOT)),
                      "file_count": len(included), "total_bytes": inventory["total_bytes"],
                      "still_ignored_scientific_files": sum(item["git_ignored_at_inventory"] for item in included),
                      "credential_pattern_match_filenames": scan["high_confidence_pattern_matches"],
                      "source_output_snapshots": len(copied)}, indent=2))


if __name__ == "__main__":
    main()
