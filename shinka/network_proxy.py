"""Invocation-local CONNECT egress for the subscription adapter's net namespace.

Only exact subscription hosts on TLS port 443 are reachable. DNS addresses are
checked and then used directly, preventing a second resolution after validation.
No request bodies, TLS plaintext, credentials, or prompt contents are logged.
"""
from __future__ import annotations

import contextlib
import ipaddress
import json
from pathlib import Path
import re
import select
import socket
import socketserver
import tempfile
import threading
import time

ALLOWED_HOSTS = frozenset({"chatgpt.com", "auth.openai.com"})


def validate_authority(authority: str) -> str:
    if not re.fullmatch(r"(?:chatgpt\.com|auth\.openai\.com):443", authority):
        raise ValueError("CONNECT destination is not an exact allowed subscription host:443")
    return authority[:-4]


def public_addresses(host: str):
    if host not in ALLOWED_HOSTS:
        raise ValueError("Host is outside the subscription allowlist")
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("Subscription DNS resolved to a non-public address")
    return addresses


def connect_public(host: str) -> socket.socket:
    last_error = None
    for family, kind, protocol, _, address in public_addresses(host):
        remote = socket.socket(family, kind, protocol)
        remote.settimeout(20)
        try:
            remote.connect(address)
            return remote
        except OSError as exc:
            last_error = exc
            remote.close()
    raise OSError("No allowed subscription endpoint was reachable") from last_error


def relay(left: socket.socket, right: socket.socket) -> None:
    for connection in (left, right):
        connection.settimeout(600)
    while True:
        readable, _, _ = select.select([left, right], [], [], 600)
        if not readable:
            return
        for connection in readable:
            chunk = connection.recv(65536)
            if not chunk:
                return
            (right if connection is left else left).sendall(chunk)


class ConnectHandler(socketserver.BaseRequestHandler):
    def handle(self):
        event = {"started_unix": time.time(), "host": None, "status": "rejected"}
        sent_tunnel = False
        try:
            self.request.settimeout(10)
            header = bytearray()
            while not header.endswith(b"\r\n\r\n"):
                chunk = self.request.recv(1)
                if not chunk or len(header) >= 8192:
                    raise ValueError("Missing or oversized CONNECT header")
                header.extend(chunk)
            first = header.decode("ascii").split("\r\n", 1)[0].split(" ")
            if len(first) != 3 or first[0] != "CONNECT" or first[2] not in {"HTTP/1.0", "HTTP/1.1"}:
                raise ValueError("Only HTTP CONNECT is supported")
            host = validate_authority(first[1])
            event["host"] = host
            with connect_public(host) as remote:
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                sent_tunnel = True
                event["status"] = "connected"
                relay(self.request, remote)
        except (ValueError, OSError, UnicodeError) as exc:
            event["error_type"] = type(exc).__name__
            if not sent_tunnel:
                with contextlib.suppress(OSError):
                    self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        finally:
            event["elapsed_seconds"] = time.time() - event["started_unix"]
            self.server.record(event)


class ConnectServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    block_on_close = False

    def record(self, event):
        with self.log_lock:
            with self.log_path.open("a") as stream:
                stream.write(json.dumps(event) + "\n")


@contextlib.contextmanager
def subscription_proxy(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shinka-egress-") as temporary:
        endpoint = Path(temporary) / "connect.sock"
        with ConnectServer(str(endpoint), ConnectHandler) as server:
            endpoint.chmod(0o600)
            server.log_path = log_path
            server.log_lock = threading.Lock()
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield endpoint
            finally:
                server.shutdown()
                thread.join(timeout=2)
