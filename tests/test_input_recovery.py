import subprocess
import sys
import unittest
from scripts import recover_repeatability_inputs as recovery

class InputRecoveryTests(unittest.TestCase):
    def test_restricts_original_preparation_without_altering_the_builder(self):
        original = (recovery.ROOT / 'R/audit_data.R').read_text()
        code = recovery.restricted_preparation(original)
        self.assertIn('dat <- dat[dat$year <= 2009L, , drop=FALSE]', code)
        self.assertIn('for(t in 2006:2009)', code)
        self.assertNotIn('for(t in 2006:2010)', code)
        self.assertIn('load(args[1],envir=env)', code)
        self.assertIn('build_past_data(dat,1990:(t-1L))', code)
        self.assertNotIn('siena07(', code)
        self.assertNotIn('score.R', code)

    def test_source_drift_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            recovery.restricted_preparation((recovery.ROOT / 'R/audit_data.R').read_text() + '\n')

    def test_default_dry_run_does_not_need_archive_or_runtime(self):
        result = subprocess.run([sys.executable, str(recovery.ROOT / 'scripts/recover_repeatability_inputs.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Dry run', result.stdout)

if __name__ == '__main__':
    unittest.main()
