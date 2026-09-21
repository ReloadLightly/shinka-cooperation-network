"""Explicit CLI routing only: no R, native scheduler, data, or model calls."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr
import io
import json
import re
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import evaluate as dispatcher
from scripts import multiobjective_evaluation


class ProtocolCliTests(unittest.TestCase):
    def invoke(self, script, *args):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            output = cwd / 'MUST_NOT_BE_CREATED'
            result = subprocess.run(
                [sys.executable, str(ROOT / script), '--results-dir' if script != 'evaluate.py'
                 else '--results_dir', str(output), *args],
                cwd=cwd, text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(list(cwd.iterdir()), [], result.stderr)
            return result

    def test_evaluator_requires_protocol_before_reading_candidate(self):
        result = self.invoke('evaluate.py', '--program_path', 'MISSING.py')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('--protocol', result.stderr)
        self.assertIn('required', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_native_launcher_requires_config_before_importing_shinka(self):
        result = self.invoke('scripts/run_shinka.py')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('--config', result.stderr)
        self.assertIn('required', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_conventional_launcher_requires_protocol_before_preflight(self):
        result = self.invoke('scripts/conventional_search.py', '--limit', '1')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('--protocol', result.stderr)
        self.assertIn('required', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_unknown_evaluator_protocol_rejected_without_work(self):
        result = self.invoke('evaluate.py', '--program_path', 'MISSING.py',
                             '--protocol', 'invented-protocol')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('invalid choice', result.stderr)

    def test_unknown_conventional_protocol_rejected_without_work(self):
        result = self.invoke('scripts/conventional_search.py', '--protocol', 'invented-protocol')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('invalid choice', result.stderr)

    def test_help_needs_no_selector_or_scientific_environment(self):
        for script in ('evaluate.py', 'scripts/run_shinka.py', 'scripts/conventional_search.py'):
            with self.subTest(script=script):
                result = self.invoke(script, '--help')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout)


class EvaluatorDispatchTests(unittest.TestCase):
    def test_explicit_protocol_routes_and_preserves_exit_code(self):
        for protocol in ('pr-only-v2', 'multiobjective-v1'):
            for code in (0, 1, 75):
                with self.subTest(protocol=protocol, exit_code=code):
                    with mock.patch.object(dispatcher, 'evaluate', return_value=code) as old, \
                         mock.patch.object(multiobjective_evaluation, 'evaluate', return_value=code) as current:
                        actual = dispatcher.main([
                            '--protocol', protocol, '--program_path', 'candidate.py',
                            '--results_dir', 'output',
                        ])
                    selected, other = (old, current) if protocol == 'pr-only-v2' else (current, old)
                    selected.assert_called_once_with(Path('candidate.py'), Path('output'))
                    other.assert_not_called()
                    self.assertEqual(actual, code)

    def test_omitted_protocol_never_dispatches(self):
        with mock.patch.object(dispatcher, 'evaluate') as old, \
             mock.patch.object(multiobjective_evaluation, 'evaluate') as current, \
             redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            dispatcher.main(['--program_path', 'candidate.py', '--results_dir', 'output'])
        self.assertEqual(raised.exception.code, 2)
        old.assert_not_called()
        current.assert_not_called()


class NativeCallSiteTests(unittest.TestCase):
    def literal_extra_arguments(self, filename):
        """Inspect actual constructor arguments without importing native Shinka."""
        tree = ast.parse((ROOT / filename).read_text())
        values = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'LocalJobConfig':
                for keyword in node.keywords:
                    if keyword.arg == 'extra_cmd_args':
                        values.append(ast.literal_eval(keyword.value))
        return values

    def test_multiobjective_launcher_keeps_explicit_current_protocol(self):
        self.assertIn({'protocol': 'multiobjective-v1'}, self.literal_extra_arguments('scripts/run_shinka.py'))

    def test_legacy_profile_explicitly_routes_legacy_evaluator(self):
        config = json.loads((ROOT / 'shinka/native_config.json').read_text())
        self.assertEqual(config['job']['extra_cmd_args']['protocol'], 'pr-only-v2')
        # The legacy launcher expands this actual job dictionary into LocalJobConfig.
        tree = ast.parse((ROOT / 'scripts/run_shinka.py').read_text())
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                            and node.func.id == 'LocalJobConfig'
                            and any(keyword.arg is None and isinstance(keyword.value, ast.Name)
                                    and keyword.value.id == 'job_values' for keyword in node.keywords)
                            for node in ast.walk(tree)))

    def test_legacy_native_invalid_fixture_still_selects_legacy_protocol(self):
        self.assertEqual(self.literal_extra_arguments('shinka/check_native_evaluator.py'),
                         [{'protocol': 'pr-only-v2'}])


class DocumentedCommandTests(unittest.TestCase):
    def test_maintained_shell_examples_select_protocol(self):
        selectors = {'evaluate.py': '--protocol', 'scripts/run_shinka.py': '--config',
                     'scripts/conventional_search.py': '--protocol'}
        checked = 0
        for name in ('README.md', 'docs/RUNBOOK.md', 'docs/SHINKA_CONTRACT.md', 'docs/SELECTION.md'):
            text = (ROOT / name).read_text()
            for block in re.findall(r'```bash\n(.*?)```', text, flags=re.DOTALL):
                block = block.replace('\\\n', ' ')
                for line in block.splitlines():
                    tokens = shlex.split(line, comments=True)
                    for script, selector in selectors.items():
                        if script in tokens:
                            with self.subTest(document=name, command=line):
                                self.assertIn(selector, tokens)
                            checked += 1
        self.assertGreater(checked, 10)


if __name__ == '__main__':
    unittest.main()
