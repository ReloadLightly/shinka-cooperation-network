#!/usr/bin/env python3
"""Retrieve and verify primary replication sources without editing originals."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
import stat
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE_SHA="2f4c2c02e3969437976c505098848e0ef7333466aeba3cccd807b3b44ba75308"


def fetch(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url,timeout=120) as response:
            data=response.read()
        temporary=path.with_suffix(path.suffix+".part")
        temporary.write_bytes(data)
        temporary.replace(path)


def main():
    sources=ROOT/"sources"
    archive=sources/"archive/IO_Final.zip"
    metadata=sources/"metadata/dataverse.json"
    fetch("https://dataverse.harvard.edu/api/access/datafile/6429192",archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=ARCHIVE_SHA:
        raise RuntimeError("Replication archive checksum mismatch; preserved file for inspection, not extracted.")
    fetch("https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/S0ILRB",metadata)
    version=json.loads(metadata.read_text())["data"]["latestVersion"]
    if (version["versionNumber"],version["versionMinorNumber"])!=(1,0):
        raise RuntimeError("Metadata version changed; review specific v1.0 metadata before proceeding.")
    file=next(x["dataFile"] for x in version["files"] if x["dataFile"]["id"]==6429192)
    if hashlib.md5(archive.read_bytes()).hexdigest()!=file["checksum"]["value"]:
        raise RuntimeError("Archive does not match Dataverse MD5 metadata.")
    original=sources/"original"
    original.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            target=(original/info.filename).resolve()
            if not target.is_relative_to(original.resolve()) or stat.S_ISLNK(info.external_attr>>16):
                raise RuntimeError("Unexpected unsafe archive member.")
            if info.is_dir():
                target.mkdir(parents=True,exist_ok=True)
            else:
                payload=bundle.read(info)
                if target.exists():
                    if target.read_bytes()!=payload:
                        raise RuntimeError(f"Untouched source has changed: {target}")
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(payload)
                    target.chmod(0o444)
    for directory in sorted((p for p in original.rglob("*") if p.is_dir()),reverse=True):
        directory.chmod(0o555)
    fetch("https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S0020818322000315/resource/name/S0020818322000315sup001.pdf",sources/"reference/appendix.pdf")
    manifest={"verified_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
              "dataset_doi":"10.7910/DVN/S0ILRB","dataset_version":"1.0","file_id":6429192,
              "sha256":ARCHIVE_SHA,"md5":file["checksum"]["value"],"license":version["license"],
              "source_files":{str(p.relative_to(original)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in original.rglob("*") if p.is_file()}}
    path=sources/"manifest.json"
    if not path.exists():
        path.write_text(json.dumps(manifest,indent=2)+"\n")
    else:
        previous=json.loads(path.read_text())
        if previous["source_files"]!=manifest["source_files"]:
            raise RuntimeError("Source manifest mismatch.")
    print("Verified archive SHA256, Dataverse MD5, version1.0, reuse metadata, and all original files.")


if __name__ == "__main__":
    main()
