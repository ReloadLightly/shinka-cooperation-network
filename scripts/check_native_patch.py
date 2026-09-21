#!/usr/bin/env python3
"""Check the installed native patch contents, not just a marker comment."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify_patch(source=None, patch=None):
    source = Path(source) if source is not None else ROOT / 'vendor/ShinkaEvolve'
    patch = Path(patch) if patch is not None else ROOT / 'shinka/multiobjective_native.patch'
    result = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch.resolve())],
                            cwd=source, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Installed Shinka patch does not match the versioned patch. Preserve the checkout and run bootstrap/reconcile; no automatic reset or scientific rerun.\n' + result.stderr[-2000:])
    return True


if __name__ == '__main__':
    verify_patch()
    print('Installed native patch matches the versioned patch.')
