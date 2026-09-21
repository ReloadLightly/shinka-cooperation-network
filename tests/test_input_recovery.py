import subprocess
import sys
import unittest
import tempfile
import zipfile
import hashlib
from pathlib import Path
from unittest import mock
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

class DevelopmentBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / 'inputs.zip'
        self.values = {n: n.encode() for n in recovery.packet_paths()}
        self.expected = {n: hashlib.sha256(b).hexdigest() for n,b in self.values.items()}

    def write_bundle(self, values):
        with zipfile.ZipFile(self.bundle,'w') as z:
            for n,b in values.items(): z.writestr(n,b)

    def test_exact_bundle_is_validated(self):
        self.write_bundle(self.values)
        self.assertEqual(recovery.validated_bundle(self.bundle,self.expected),self.values)

    def test_changed_bytes_are_rejected(self):
        values=dict(self.values);values['data/past/2006.rds']=b'changed'
        self.write_bundle(values)
        with self.assertRaises(ValueError): recovery.validated_bundle(self.bundle,self.expected)

    def test_reserved_or_traversal_or_missing_entries_are_rejected(self):
        for name in ('data/targets/2010.rds','../escape.rds'):
            values=dict(self.values); values[name]=b'forbidden'
            self.write_bundle(values)
            with self.assertRaises(ValueError): recovery.validated_bundle(self.bundle,self.expected)
        self.write_bundle({n:b for n,b in self.values.items() if n!='data/past/2006.rds'})
        with self.assertRaises(ValueError): recovery.validated_bundle(self.bundle,self.expected)

    def test_expected_manifest_cannot_expand_the_scope(self):
        self.write_bundle(self.values)
        with self.assertRaises(ValueError):
            recovery.validated_bundle(self.bundle,{**self.expected,'data/targets/2010.rds':'x'})

    def test_restore_is_exact_and_repeatable_without_raw_data_or_r(self):
        self.write_bundle(self.values)
        root=Path(self.temp.name)/'repo'
        plan={'ready':True,'packets':self.expected}
        with mock.patch.object(recovery,'inspect_inputs',return_value=plan):
            record=recovery.restore_bundle(self.bundle,root)
            second=recovery.restore_bundle(self.bundle,root)
        self.assertEqual(record,second)
        self.assertFalse(record['raw_archive_loaded'])
        self.assertEqual({n:(root/n).read_bytes() for n in self.values},self.values)
        self.assertFalse((root/'data/targets/2010.rds').exists())

    def test_restore_never_overwrites_changed_existing_packet(self):
        self.write_bundle(self.values)
        root=Path(self.temp.name)/'repo'
        p=root/'data/past/2006.rds';p.parent.mkdir(parents=True);p.write_bytes(b'local-change')
        with mock.patch.object(recovery,'inspect_inputs',return_value={'ready':True,'packets':self.expected}):
            with self.assertRaises(ValueError): recovery.restore_bundle(self.bundle,root)
        self.assertEqual(p.read_bytes(),b'local-change')

if __name__ == '__main__':
    unittest.main()
