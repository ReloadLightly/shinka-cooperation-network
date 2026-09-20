#!/usr/bin/env python3
"""Recreate the pinned native integration without any paid model/API calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "9912af12d423504b8d580f4179fd15f5f88b8c50"


def run(*args: str, cwd: Path = ROOT) -> None:
    print("RUN", *args, flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-python", action="store_true")
    args = parser.parse_args()
    source = ROOT / "vendor/ShinkaEvolve"
    if not source.exists():
        run("git", "clone", "https://github.com/SakanaAI/ShinkaEvolve.git", str(source))
        run("git", "checkout", COMMIT, cwd=source)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if actual != COMMIT:
        raise RuntimeError(f"Existing Shinka checkout has wrong revision: {actual}")
    node_root = ROOT / "shinka/headless"
    if not (node_root / "node_modules/@roberttlange/headless/package.json").exists():
        run("npm", "ci", "--ignore-scripts", cwd=node_root)
    patch_targets = [
        (source / "shinka/llm/providers/headless.py",
         '{"low", "medium", "high", "xhigh"}',
         '{"low", "medium", "high", "xhigh", "max", "ultra"}')]
    dist = node_root / "node_modules/@roberttlange/headless/dist"
    for name in ["cli.js", "config.js"]:
        patch_targets.append((dist / name, 'value === "high" || value === "xhigh"',
          'value === "high" || value === "xhigh" || value === "max" || value === "ultra"'))
    patch_targets.append((dist / "agents.js", '"--ask-for-approval", "never", "--search"',
      '"--ask-for-approval", "never", "-c", \'web_search="disabled"\', "-c", "features.shell_tool=false"'))
    patch_targets += [
        (source / "shinka/webui/visualization.py",
         'with ReusableTCPServer(("", port), handler_factory) as httpd:',
         'with ReusableTCPServer(("127.0.0.1", port), handler_factory) as httpd:'),
        (source / "shinka/webui/visualization.py", 'http://0.0.0.0:{port}',
         'http://127.0.0.1:{port}')]
    for path, before, after in patch_targets:
        text = path.read_text()
        if after in text:
            continue
        if before not in text:
            raise RuntimeError(f"Unexpected upstream source, refusing patch: {path}")
        path.write_text(text.replace(before, after))
    local_runtime = source / "shinka/launch/local.py"
    if "Project compatibility patch: native Popen.kill" not in local_runtime.read_text():
        run("git", "apply", str(ROOT / "shinka/patches/local-evaluation-process-tree.patch"), cwd=source)
    tools = ROOT / "shinka/tools"
    tools.mkdir(parents=True, exist_ok=True)
    deb = tools / "bubblewrap_0.6.1-1ubuntu0.3_amd64.deb"
    if not deb.exists():
        run("apt-get", "download", "bubblewrap=0.6.1-1ubuntu0.3", cwd=tools)
    run("dpkg-deb", "-x", str(deb), str(tools / "bubblewrap"))
    model = ROOT / "shinka/models/potion-base-8M"
    model.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((ROOT / "shinka/provenance.json").read_text())
    revision = provenance["embedding"]["revision"]
    for name in ["config.json", "tokenizer.json", "model.safetensors", "README.md"]:
        destination = model / name
        if not destination.exists():
            url = f"https://huggingface.co/minishlab/potion-base-8M/resolve/{revision}/{name}"
            urllib.request.urlretrieve(url, destination)
        expected = provenance["artifacts"][str(destination.relative_to(ROOT))]["sha256"]
        if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Embedding checksum mismatch: {destination}")
    if not args.skip_python:
        if not (ROOT / ".venv-shinka/bin/python").exists():
            run("uv", "venv", ".venv-shinka", "--python", "3.13.5")
        run("uv", "pip", "install", "--python", ".venv-shinka/bin/python",
            "-r", "shinka/requirements.lock")


if __name__ == "__main__":
    main()
