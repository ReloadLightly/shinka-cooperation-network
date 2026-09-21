#!/usr/bin/env python3
"""Fetch and materialize only pinned Step 4 evidence; never numerical execution."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.replicated_evaluation import RESULT_COMMIT, RESULT_SUBDIR


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--fetch',action='store_true');a=p.parse_args()
    dest=a.destination.resolve()
    if dest.exists() and any(dest.iterdir()):raise ValueError('Destination must be empty; preserve existing evidence')
    if a.fetch:
        remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()
        if remote.rstrip('/').removesuffix('.git') not in ('https://github.com/ReloadLightly/shinka-cooperation-network','git@github.com:ReloadLightly/shinka-cooperation-network'):
            raise ValueError('Wrong repository origin')
        subprocess.run(['git','fetch','--no-tags','--depth=1','origin',RESULT_COMMIT],cwd=ROOT,check=True)
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['git','archive',RESULT_COMMIT,RESULT_SUBDIR],cwd=ROOT,stdout=stream,check=True)
        stream.seek(0)
        with tarfile.open(fileobj=stream) as archive:
            members=archive.getmembers()
            for member in members:
                path=(dest/member.name).resolve();path.relative_to(dest)
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):raise ValueError('Unsafe archive member')
            dest.mkdir(parents=True,exist_ok=True)
            archive.extractall(dest,members=members,filter='data')
    print(f'Pinned saved evidence materialized at {dest}; no simulations or outcome-packet reads.')

if __name__=='__main__':main()
