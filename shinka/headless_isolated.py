#!/usr/bin/env python3
"""OS-isolated launcher for the pinned native Headless subscription adapter.

The evaluator/data repository is absent from the mount namespace. This is a
launch boundary, not a replacement evolution loop. No API credentials pass in.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from network_proxy import subscription_proxy

ROOT = Path(__file__).resolve().parents[1]
BWRAP = ROOT / "shinka/tools/bubblewrap/usr/bin/bwrap"
HEADLESS = ROOT / "shinka/headless/node_modules"


def sandbox_command(workdir: Path, command: list[str], proxy_socket: Path) -> list[str]:
    account_home = Path.home()
    authentication = json.loads((account_home / ".codex/auth.json").read_text())
    if (authentication.get("auth_mode") != "chatgpt" or authentication.get("OPENAI_API_KEY")
            or not isinstance(authentication.get("tokens"), dict)):
        raise RuntimeError("Only cached ChatGPT subscription authentication is authorized")
    node = Path(shutil.which("node") or "").resolve().parent.parent
    if not (node / "bin/node").is_file():
        raise RuntimeError("Node installation not found")
    if not BWRAP.is_file():
        raise RuntimeError("Pinned bubblewrap is missing; run shinka/bootstrap.py")
    cmd = [str(BWRAP), "--die-with-parent", "--unshare-user", "--unshare-pid", "--unshare-net",
           "--unshare-ipc", "--unshare-uts", "--new-session", "--proc", "/proc",
           "--dev", "/dev", "--tmpfs", "/tmp"]
    for path in ["/usr", "/bin", "/lib", "/lib64"]:
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]
    for path in ["/etc/ssl", "/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf",
                 "/etc/passwd", "/etc/group", "/etc/localtime"]:
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]
    cmd += ["--ro-bind", str(node), "/opt/node", "--ro-bind", str(HEADLESS),
            "/opt/headless/node_modules", "--bind", str(workdir), "/work",
            "--ro-bind", str(proxy_socket), "/run/shinka-subscription.sock",
            "--ro-bind", str(ROOT / "shinka/network_bridge.py"), "/opt/shinka-network-bridge.py",
            "--dir", str(account_home / ".codex")]
    for name in ["auth.json", "models_cache.json"]:
        source = account_home / ".codex" / name
        if source.is_file():
            cmd += ["--ro-bind", str(source), str(source)]
    cmd += ["--chdir", "/work", "--setenv", "PATH", "/opt/node/bin:/usr/bin:/bin"]
    return cmd + ["/usr/bin/python3", "/opt/shinka-network-bridge.py", *command]


def main() -> int:
    argv = sys.argv[1:]
    root_public = ROOT / "runs/public_mutation"
    root_public.mkdir(parents=True, exist_ok=True)
    workdir = root_public.resolve()
    if "--work-dir" in argv:
        i = argv.index("--work-dir")
        workdir = Path(argv[i + 1]).resolve()
        if not workdir.is_relative_to(root_public.resolve()):
            raise RuntimeError("Headless workdir must be inside runs/public_mutation")
        argv[i + 1] = "/work"
    if "--prompt-file" in argv:
        i = argv.index("--prompt-file")
        source = Path(argv[i + 1]).resolve()
        if not source.is_relative_to(workdir):
            raise RuntimeError("Prompt must be inside the public mutation workspace")
        argv[i + 1] = "/work/" + str(source.relative_to(workdir))
    env = {key: value for key, value in os.environ.items() if key in {
        "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TZ", "PATH"}}
    if argv == ["--self-check"]:
        command = ["/bin/sh", "-c",
                   'test ! -e "$1/evaluate.py" && test ! -e "$1/data" && '
                   'test ! -e "$1/results" && test ! -e "$1/sources" && '
                   'test ! -e "$1/runs/evolution_native" && '
                   'test ! -e "$HOME/.codex/sessions" && '
                   '/opt/node/bin/codex login status', "isolation", str(ROOT)]
    else:
        command = ["/opt/node/bin/node",
                   "/opt/headless/node_modules/@roberttlange/headless/dist/cli.js", *argv]
    started = time.time()
    # Complete adapter output is kept outside mutation-visible workdir.
    logs = ROOT / "runs/shinka_adapter_logs"
    logs.mkdir(parents=True, exist_ok=True)
    call_id = f"{time.time_ns()}"
    record = {"call_id": call_id, "started_unix": started, "argv": argv,
              "host_workdir": str(workdir), "billing_route": "ChatGPT subscription; no API keys passed"}
    # Commit an attempt before launch and stream directly to durable files. An
    # external timeout can kill this process before a completion record exists.
    with (logs / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({**record, "event": "started"}) + "\n")
    stdout_path, stderr_path = logs / f"{call_id}.stdout", logs / f"{call_id}.stderr"
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        with subscription_proxy(logs / "network_connect.jsonl") as proxy_socket:
            result = subprocess.run(sandbox_command(workdir, command, proxy_socket), env=env,
                                    stdout=stdout, stderr=stderr)
    record.update(runtime_seconds=time.time() - started, returncode=result.returncode,
                  stdout_sha256=hashlib.sha256(stdout_path.read_bytes()).hexdigest())
    with (logs / "calls.jsonl").open("a") as stream:
        stream.write(json.dumps(record) + "\n")
    with (logs / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({**record, "event": "completed"}) + "\n")
    sys.stdout.write(stdout_path.read_text(errors="replace"))
    sys.stderr.write(stderr_path.read_text(errors="replace"))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
