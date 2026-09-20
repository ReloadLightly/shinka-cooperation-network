#!/usr/bin/env python3
"""Runs only inside the isolated network namespace; forwards TCP to one Unix socket."""
from __future__ import annotations

import os
import select
import socket
import socketserver
import subprocess
import sys
import threading


class Bridge(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as upstream:
            upstream.connect("/run/shinka-subscription.sock")
            sockets = [self.request, upstream]
            for connection in sockets:
                connection.settimeout(600)
            try:
                while True:
                    readable, _, _ = select.select(sockets, [], [], 600)
                    if not readable:
                        return
                    for connection in readable:
                        chunk = connection.recv(65536)
                        if not chunk:
                            return
                        (upstream if connection is self.request else self.request).sendall(chunk)
            except OSError:
                return


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    block_on_close = False


def main():
    with Server(("127.0.0.1", 8768), Bridge) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        environment = os.environ.copy()
        for name in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
                     "WS_PROXY", "WSS_PROXY", "ws_proxy", "wss_proxy"]:
            environment[name] = "http://127.0.0.1:8768"
        environment["NO_PROXY"] = environment["no_proxy"] = ""
        try:
            return subprocess.run(sys.argv[1:], env=environment).returncode
        finally:
            server.shutdown()
            thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
