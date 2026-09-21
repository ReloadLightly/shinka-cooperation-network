#!/usr/bin/env python3
"""Local execution checks and owned-service lifecycle; never model inference.

No downloads, authentication changes, data regeneration or scientific evaluation.
The CLI replays hash-bound saved evidence only. A successful local check does not
establish that any configured model route will answer a live inference request.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
UPSTREAM = '9912af12d423504b8d580f4179fd15f5f88b8c50'
EMBEDDING_REVISION = 'bf8b056651a2c21b8d2565580b8569da283cab23'


class HostUnavailable(RuntimeError):
    """A host prerequisite failed; never evidence against a candidate model."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HostUnavailable('Local service attempted an HTTP redirect')


def service_ports(config, webui_port):
    name = config['evolution']['embedding_model']
    prefix = 'local/potion-base-8M@'
    if not isinstance(name, str) or not name.startswith(prefix):
        raise HostUnavailable('Expected the pinned local embedding model')
    url = urlsplit(name[len(prefix):])
    try:
        port = url.port
    except ValueError as exc:
        raise HostUnavailable('Invalid local embedding port') from exc
    if (url.scheme != 'http' or url.hostname != '127.0.0.1'
            or url.username or url.password or url.query or url.fragment
            or url.path.rstrip('/') != '/v1' or type(port) is not int):
        raise HostUnavailable('Embedding endpoint must be loopback HTTP /v1')
    ports = {'embedding': port, 'webui': webui_port}
    if any(type(p) is not int or not 1 <= p <= 65535 for p in ports.values()):
        raise HostUnavailable('Service ports must be integers from 1 through 65535')
    if len(set(ports.values())) != len(ports):
        raise HostUnavailable('Embedding and WebUI require different ports')
    return ports


def require_free_ports(ports):
    """Fail on conflicts; never kill or borrow another process's service."""
    for name, port in ports.items():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise HostUnavailable(f'{name} port {port} is unavailable; existing processes are untouched') from exc


def probe_service(name, port):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    path = '/v1/models' if name == 'embedding' else '/'
    with opener.open(f'http://127.0.0.1:{port}{path}', timeout=1.0) as response:
        if response.status != 200:
            return False
        body = response.read(131072)
    if name == 'embedding':
        item = json.loads(body)
        return (item.get('model') == 'minishlab/potion-base-8M'
                and item.get('revision') == EMBEDDING_REVISION
                and item.get('local_only') is True)
    return b'<html' in body.lower() or b'<!doctype html' in body.lower()


def wait_services(processes, ports, timeout=60.0):
    if set(processes) != set(ports):
        raise HostUnavailable('Owned services do not match declared endpoints')
    deadline = time.monotonic() + timeout
    pending = set(ports)
    while True:
        for name, process in processes.items():
            if process.poll() is not None:
                raise HostUnavailable(f'{name} exited during startup; inspect its local log')
        for name in tuple(pending):
            try:
                if probe_service(name, ports[name]):
                    pending.remove(name)
            except (OSError, URLError, HTTPError, ValueError):
                pass
        if not pending:
            # A healthy unrelated listener must not conceal an exited child.
            if any(p.poll() is not None for p in processes.values()):
                raise HostUnavailable('Owned service exited after the HTTP check')
            return
        if time.monotonic() >= deadline:
            raise HostUnavailable('Service startup timed out: ' + ', '.join(sorted(pending)))
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))


def stop_services(processes):
    """Terminate only child process groups created with start_new_session=True."""
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        # Descendants can survive their group leader. Clean the owned group too.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def _command_ok(command, root, timeout=30):
    try:
        env = dict(os.environ, SHINKA_PRICING_MODE='offline', PYTHON_DOTENV_DISABLED='1')
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=timeout)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def inspect_runtime(root=ROOT, *, check_runtime=False, check_isolation=False):
    root = Path(root)
    required = {
        'r_wrapper': root/'environment/run-r',
        'r_runtime': root/'environment/runtime/bin/Rscript',
        'headless_cli': root/'shinka/headless/node_modules/@roberttlange/headless/dist/cli.js',
        'bubblewrap': root/'shinka/tools/bubblewrap/usr/bin/bwrap',
        'embedding_model': root/'shinka/models/potion-base-8M',
        'visualizer': Path(sys.executable).parent/'shinka_visualize',
        'subscription_auth_file': Path.home()/'.codex/auth.json',
    }
    checks = {name: path.exists() for name, path in required.items()}
    for name in ('r_wrapper', 'r_runtime', 'bubblewrap', 'visualizer'):
        checks[name] = checks[name] and os.access(required[name], os.X_OK)
    import shutil
    checks['node'] = shutil.which('node') is not None
    checks['codex_cli'] = shutil.which('codex') is not None
    try:
        checks['model2vec_importable'] = importlib.util.find_spec('model2vec') is not None
    except (ImportError, ValueError):
        checks['model2vec_importable'] = False
    source = root/'vendor/ShinkaEvolve'
    try:
        version = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source,
                                          text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
        checks['pinned_shinka_checkout'] = version == UPSTREAM
        from scripts.check_native_patch import verify_patch
        checks['native_patch'] = verify_patch(source, root/'shinka/multiobjective_native.patch')
    except (OSError, RuntimeError, subprocess.SubprocessError):
        checks['pinned_shinka_checkout'] = False
        checks['native_patch'] = False
    # Import the API without constructing a runner or model client.
    checks['native_api_imports'] = _command_ok([sys.executable, '-c',
        'from shinka.core import EvolutionConfig, ShinkaEvolveRunner; '
        'from shinka.database import DatabaseConfig; from shinka.launch import LocalJobConfig'], root)
    r_ok = None
    if check_runtime:
        expression = ('stopifnot(as.character(getRversion())=="4.2.1",'
                      'as.character(packageVersion("RSiena"))=="1.3.10",'
                      'as.character(packageVersion("PRROC"))=="1.3.1")')
        r_ok = checks['r_runtime'] and _command_ok([str(required['r_wrapper']), '-e', expression], root)
    isolation_ok = None
    if check_isolation:
        needed = ('node', 'codex_cli', 'bubblewrap', 'headless_cli', 'subscription_auth_file')
        isolation_ok = all(checks[k] for k in needed) and _command_ok(
            [sys.executable, str(root/'shinka/headless_isolated.py'), '--self-check'], root, timeout=45)
    passed = all(checks.values()) and r_ok is True and isolation_ok is True
    return {'checks': checks, 'r_versions_checked': r_ok, 'isolation_checked': isolation_ok,
            'local_runtime_passed': passed, 'model_inference_verified': False,
            'model_route_note': 'No inference request made; configured aliases and allowance remain unverified.'}


def require_runtime(root=ROOT):
    report = inspect_runtime(root, check_runtime=True, check_isolation=True)
    if not report['local_runtime_passed']:
        missing = [key for key, ok in report['checks'].items() if not ok]
        if report['r_versions_checked'] is not True:
            missing.append('pinned R package versions')
        if report['isolation_checked'] is not True:
            missing.append('subscription isolation self-check')
        raise HostUnavailable('Execution prerequisites failed: ' + ', '.join(missing))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-runtime', action='store_true')
    parser.add_argument('--check-isolation', action='store_true')
    parser.add_argument('--webui-port', type=int, default=8765)
    args = parser.parse_args()
    from scripts import replicated_evaluation as ev
    report = inspect_runtime(check_runtime=args.check_runtime, check_isolation=args.check_isolation)
    config = json.loads((ROOT/'shinka/native_replicated_config.json').read_text())
    report['configured_model_routes'] = config['evolution']['llm_models']
    try:
        ports = service_ports(config, args.webui_port)
        require_free_ports(ports)
        report['ports_available'] = True
    except HostUnavailable as exc:
        report['ports_available'] = False
        report['ports_error'] = str(exc)
    try:
        reference = ev.result_for(ev.policy()['reference'], ev.evidence_root(), allow_new=False)
        registry = ev.read(ROOT/ev.REGISTRY)['specifications']
        other = next(x['specification'] for x in registry.values() if x['label'] == 'gwesp69')
        candidate = ev.result_for(other, ev.evidence_root(), allow_new=False)
        value = ev.build_metrics(other, candidate, reference, ev.identity(ROOT))
        report['saved_evidence'] = {'verified': True, 'cells': len(reference)+len(candidate),
                                   'objectives': {key: value['public'][key] for key in ev.KEYS}}
    except Exception as exc:
        report['saved_evidence'] = {'verified': False, 'error_type': type(exc).__name__,
                                   'action': 'Hydrate/verify the pinned evidence; never regenerate it for preflight.'}
    report['local_prerequisites_passed'] = (report['local_runtime_passed'] and report['ports_available']
                                          and report['saved_evidence']['verified'])
    report.update(version='step5c-host-v1', new_fits=0, new_forecasts=0, new_simulations=0,
                  llm_calls=0, reserved_year_access=False, campaign_started=False)
    print(json.dumps(report, indent=2))
    return 0 if report['local_prerequisites_passed'] else 75


if __name__ == '__main__':
    raise SystemExit(main())
