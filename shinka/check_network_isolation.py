#!/usr/bin/env python3
"""Verify subscription sandbox boundaries with sockets/HTTPS; no model requests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch

from headless_isolated import ROOT, sandbox_command
from network_proxy import public_addresses, subscription_proxy, validate_authority


def main():
    folder = ROOT / "runs/shinka_network_checks" / str(time.time_ns())
    folder.mkdir(parents=True)
    public = ROOT / "runs/public_mutation/network_check"
    public.mkdir(parents=True, exist_ok=True)
    # Test that an exact allowed DNS name cannot rebind to a private IP.
    with patch("network_proxy.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))]):
        try:
            public_addresses("chatgpt.com")
        except ValueError:
            dns_guard = True
        else:
            raise AssertionError("Private DNS resolution was accepted")
    for invalid in ["localhost:443", "127.0.0.1:443", "10.0.0.1:443", "[::1]:443",
                    "api.openai.com:443", "chatgpt.com.evil.example:443", "chatgpt.com:80",
                    "https://chatgpt.com:443", "chatgpt.com:443/path", "user@chatgpt.com:443"]:
        try:
            validate_authority(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid destination accepted: {invalid}")
    namespace = os.readlink("/proc/self/ns/net")
    with socket.socket() as host_listener:
        host_listener.bind(("127.0.0.1", 0))
        host_listener.listen()
        port = host_listener.getsockname()[1]
        code = r'''
import http.client,json,os,pathlib,socket,ssl,subprocess,sys
root=pathlib.Path(sys.argv[1]);port=int(sys.argv[2]);host_namespace=sys.argv[3]
checks={"different_network_namespace":os.readlink("/proc/self/ns/net")!=host_namespace}
checks["protected_paths_absent"]=all(not (root/p).exists() for p in ["evaluate.py","data","results","sources","runs/evolution_native"])
checks["prior_sessions_absent"]=not (pathlib.Path.home()/".codex/sessions").exists()
for key,target in [("host_loopback_blocked",("127.0.0.1",port)),("direct_public_network_blocked",("1.1.1.1",443))]:
 try:
  with socket.create_connection(target,timeout=2):pass
 except OSError:checks[key]=True
 else:checks[key]=False
for name,authority in [("proxy_loopback_blocked",f"127.0.0.1:{port}"),("proxy_private_ip_blocked","10.0.0.1:443"),("proxy_paid_api_host_blocked","api.openai.com:443"),("proxy_other_domain_blocked","example.com:443"),("proxy_url_blocked","https://chatgpt.com:443")]:
 with socket.create_connection(("127.0.0.1",8768),timeout=5) as connection:
  connection.sendall(f"CONNECT {authority} HTTP/1.1\r\n\r\n".encode())
  checks[name]=connection.recv(1024).startswith(b"HTTP/1.1 403")
statuses={}
for host in ["chatgpt.com","auth.openai.com"]:
 connection=http.client.HTTPSConnection("127.0.0.1",8768,timeout=30,context=ssl.create_default_context())
 connection.set_tunnel(host,443)
 connection.request("HEAD","/",headers={"Host":host,"User-Agent":"research-infrastructure-read-only-check"})
 response=connection.getresponse();statuses[host]=response.status;response.read();connection.close()
checks["allowed_public_https_reachable"]=all(100<=v<=599 for v in statuses.values())
login=subprocess.run(["/opt/node/bin/codex","login","status"],capture_output=True,text=True,timeout=15)
checks["subscription_login_available"]=login.returncode==0 and "Logged in using ChatGPT" in login.stdout+login.stderr
print(json.dumps({"checks":checks,"public_https_statuses":statuses,"login_status":(login.stdout+login.stderr).strip(),"no_model_calls":True}))
assert all(checks.values()),checks
'''
        command = ["/usr/bin/python3", "-c", code, str(ROOT), str(port), namespace]
        env = {k: v for k, v in os.environ.items() if k in {"HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TZ"}}
        with subscription_proxy(folder / "connect.jsonl") as proxy:
            result = subprocess.run(sandbox_command(public, command, proxy), env=env,
                                    capture_output=True, text=True, timeout=100)
    (folder / "stdout.log").write_text(result.stdout)
    (folder / "stderr.log").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"Network isolation check failed; inspect {folder}: {result.stderr[-1000:]}")
    evidence = json.loads(result.stdout)
    evidence["checks"]["private_dns_rebinding_blocked"] = dns_guard
    evidence["checks"]["malformed_authorities_blocked"] = True
    evidence["recorded_unix"] = time.time()
    evidence["output_directory"] = str(folder.relative_to(ROOT))
    (folder / "checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    bindings = ["shinka/headless_isolated.py", "shinka/network_proxy.py", "shinka/network_bridge.py",
                "shinka/check_network_isolation.py", "shinka/headless/node_modules/@roberttlange/headless/dist/agents.js"]
    review = {"mutation_network_isolation_verified": True,
              "review": "Executed socket, DNS guard, public HTTPS, protected-path and subscription-login checks; no model call",
              "evidence": str((folder / "checks.json").relative_to(ROOT)),
              "bound_files_sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in bindings},
              "limitations": ["This socket check makes no model call; actual route-smoke evidence is recorded separately in runs/shinka_infrastructure/adapter_smoke.json.",
                              "Subscription hosts are permitted for TLS CONNECT; application paths and encrypted content are not inspected."]}
    (ROOT / "shinka/security_review.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
