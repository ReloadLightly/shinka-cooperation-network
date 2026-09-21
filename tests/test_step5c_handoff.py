"""Step 5C regression and host-boundary tests; zero real R or model calls."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import replicated_evaluation as e
from scripts import replicated_host as h

SPEC = {'schema_version': 2, 'network_effects': [{'effect': 'gwesp', 'parameter': 40}]}


class FailureReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root/'cache'
        self.cell = self.cache/e.identity()['sha256']/e.spec_hash(SPEC)/'2006'
        self.program = self.root/'candidate.py'
        self.program.write_text('def build_network_spec(allowed_schema):\n    return '+repr(SPEC)+'\n')
        self.calls = 0
        for target, value in ((e, 'cache_root'),):
            item = patch.object(target, value, return_value=self.cache)
            item.start(); self.addCleanup(item.stop)
        item = patch.object(e, 'load_imported', side_effect=lambda spec, year, *a, **kw:
                            {'year': year, 'fixture': 'reference'} if spec == e.policy()['reference'] else None)
        item.start(); self.addCleanup(item.stop)
        item = patch.object(e.pf, 'request', return_value={})
        self.native_request = item.start(); self.addCleanup(item.stop)
        item = patch.object(e.pf, 'packet_bytes', return_value=b'test-fixture-not-RDS')
        item.start(); self.addCleanup(item.stop)

    def policy_failure(self, *args, **kwargs):
        self.calls += 1
        (self.cell/'last-native-error.json').write_text(json.dumps({
            'kind': 'numerical_policy_exhausted', 'message': 'Precision policy exhausted',
            'completed_fit_diagnostics': []}))
        raise subprocess.CalledProcessError(1, 'fixture-native-operation')

    def evaluate(self, name, *, allow_new=True):
        with patch.object(e.old, 'native_process', side_effect=self.policy_failure):
            code = e.evaluate(self.program, self.root/name, allow_new=allow_new,
                              campaign=self.root/'campaign', admission_limit=1)
        return code, e.read(self.root/name/'metrics.json')

    def test_terminal_policy_failure_replays_as_invalid_without_native_call(self):
        code, first = self.evaluate('first')
        self.assertEqual(code, 1)
        self.assertEqual(first['public']['status'], 'invalid_evaluation')
        evidence = {str(p.relative_to(self.cell)): p.read_bytes() for p in self.cell.rglob('*') if p.is_file()}
        budget = (self.root/'campaign/numerical-admissions.json').read_bytes()
        requests = self.native_request.call_count
        code, second = self.evaluate('second', allow_new=False)
        self.assertEqual(code, 1)
        self.assertEqual(first, second)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.native_request.call_count, requests)
        self.assertEqual(budget, (self.root/'campaign/numerical-admissions.json').read_bytes())
        self.assertEqual(evidence, {str(p.relative_to(self.cell)): p.read_bytes() for p in self.cell.rglob('*') if p.is_file()})

    def test_terminal_replay_does_not_consume_second_admission(self):
        self.evaluate('first')
        self.assertEqual(self.evaluate('second')[0], 1)
        self.assertEqual(len(e.read(self.root/'campaign/numerical-admissions.json')), 1)
        self.assertEqual(self.calls, 1)

    def test_corrupt_terminal_evidence_is_paused(self):
        self.evaluate('first')
        (self.cell/'fit-invocation/native.log').write_text('modified')
        code, result = self.evaluate('second')
        self.assertEqual(code, 75)
        self.assertEqual(result['public']['status'], 'paused_execution_window')
        self.assertIsNone(result['combined_score'])
        self.assertEqual(self.calls, 1)

    def test_changed_failure_record_is_paused(self):
        self.evaluate('first')
        path = self.cell/'failure.json'; value = e.read(path); value['message'] = 'modified'
        path.write_text(json.dumps(value))
        self.assertEqual(self.evaluate('second')[0], 75)
        self.assertEqual(self.calls, 1)

    def test_uncommitted_legacy_failure_stays_paused(self):
        self.cell.mkdir(parents=True)
        (self.cell/'failure.json').write_text(json.dumps({'error': 'ValueError', 'message': 'old untyped failure'}))
        self.assertEqual(self.evaluate('legacy', allow_new=False)[0], 75)
        self.assertEqual(self.calls, 0)

    def test_interrupted_operation_is_not_retried_or_scored(self):
        with patch.object(e.old, 'native_process', side_effect=subprocess.TimeoutExpired('fixture', 1)) as native:
            code = e.evaluate(self.program, self.root/'first', allow_new=True,
                              campaign=self.root/'campaign', admission_limit=1)
            self.assertEqual(code, 75)
            code = e.evaluate(self.program, self.root/'second', allow_new=False)
            self.assertEqual(code, 75)
            self.assertEqual(native.call_count, 1)
        self.assertIsNone(e.read(self.root/'second/metrics.json')['combined_score'])


class HostBoundaries(unittest.TestCase):
    def config(self, port=8766):
        return {'evolution': {'embedding_model': f'local/potion-base-8M@http://127.0.0.1:{port}/v1'}}

    def test_embedding_port_is_derived_from_config(self):
        self.assertEqual(h.service_ports(self.config(18766), 18765), {'embedding': 18766, 'webui': 18765})

    def test_collision_fails_without_stopping_existing_listener(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen()
            port = server.getsockname()[1]
            with self.assertRaises(h.HostUnavailable): h.require_free_ports({'fixture': port})
            self.assertEqual(server.getsockname()[1], port)

    def test_same_ports_refused(self):
        with self.assertRaises(h.HostUnavailable): h.service_ports(self.config(), 8766)

    def test_nonloopback_refused(self):
        value = self.config(); value['evolution']['embedding_model'] = 'local/potion-base-8M@http://example.com:8766/v1'
        with self.assertRaises(h.HostUnavailable): h.service_ports(value, 8765)

    def test_invalid_web_port_refused(self):
        for value in (0, 65536, True, '8765'):
            with self.assertRaises(h.HostUnavailable): h.service_ports(self.config(), value)

    def test_dead_service_refused_before_probe(self):
        process = Mock(); process.poll.return_value = 1
        with patch.object(h, 'probe_service') as probe:
            with self.assertRaises(h.HostUnavailable): h.wait_services({'embedding': process}, {'embedding': 8766})
        probe.assert_not_called()

    def test_wrong_health_response_times_out(self):
        process = Mock(); process.poll.return_value = None
        with patch.object(h, 'probe_service', return_value=False):
            with self.assertRaises(h.HostUnavailable): h.wait_services({'embedding': process}, {'embedding': 8766}, timeout=0)

    def test_healthy_owned_services_pass(self):
        process = Mock(); process.poll.return_value = None
        with patch.object(h, 'probe_service', return_value=True):
            h.wait_services({'embedding': process, 'webui': process}, {'embedding': 8766, 'webui': 8765})

    def test_cleanup_escalates_only_owned_groups(self):
        process = Mock(pid=123456)
        process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 5), 0]
        with patch.object(h.os, 'killpg') as kill:
            h.stop_services([process])
        self.assertEqual([call.args[0] for call in kill.call_args_list], [123456, 123456])

    def test_unavailable_runtime_cannot_pass(self):
        with patch.object(h, 'inspect_runtime', return_value={'checks': {'missing': False},
                'r_versions_checked': False, 'isolation_checked': False, 'local_runtime_passed': False}):
            with self.assertRaises(h.HostUnavailable): h.require_runtime()

    def test_runtime_failure_precedes_campaign_and_runner(self):
        from scripts import run_shinka_replicated as launcher
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'campaign'
            args = SimpleNamespace(results_dir=folder, window_hours=1, max_new_specs=1,
                                   execute=True, webui_port=8765)
            with patch.object(launcher, 'require_runtime', side_effect=h.HostUnavailable('fixture unavailable')):
                with self.assertRaises(h.HostUnavailable): launcher.launch(args)
            self.assertFalse(folder.exists())


if __name__ == '__main__':
    unittest.main()
