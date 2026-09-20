#!/usr/bin/env python3
"""Small scientific/security contract checks; no expensive estimation."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.specification import read_program, spec_hash, InvalidSpecification
from evaluate import save_json

initial, _ = read_program(ROOT/"candidates/initial.py")
alternate, _ = read_program(ROOT/"candidates/replace_degree.py")
assert spec_hash(initial) != spec_hash(alternate)
fixtures = {
    "imports": "import os\ndef build_network_spec(allowed_schema):\n return {}\n",
    "file_access": "def build_network_spec(allowed_schema):\n return open('/etc/passwd').read()\n",
    "decorator": "@open('/etc/passwd')\ndef build_network_spec(allowed_schema):\n return {}\n",
    "default_evaluation": "def build_network_spec(allowed_schema=open('/etc/passwd')):\n return {}\n",
    "fitness_redefinition": "def build_network_spec(allowed_schema):\n return {'schema_version':1,'combined_score':1,'network_effects':[]}\n",
    "unsupported_effect": "def build_network_spec(allowed_schema):\n return {'schema_version':1,'network_effects':['arbitraryUtility']}\n",
    "complexity_limit": "def build_network_spec(allowed_schema):\n return {'schema_version':1,'network_effects':['degPlus','transTriads','inPop','gwesp']}\n",
    "duplicate_terms": "def build_network_spec(allowed_schema):\n return {'schema_version':1,'network_effects':['degPlus','degPlus']}\n",
}
results = {}
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)/"candidate.py"
    for name, source in fixtures.items():
        path.write_text(source)
        try:
            read_program(path)
        except InvalidSpecification:
            results[name] = "rejected"
        else:
            raise AssertionError(f"Untrusted candidate accepted: {name}")
    path.write_text('"""Cosmetic rewrite"""\ndef build_network_spec(allowed_schema):\n return {"network_effects":["transTriads","degPlus"],"schema_version":1}\n')
    reordered, _ = read_program(path)
    assert spec_hash(reordered) == spec_hash(initial)
save_json(ROOT/"results/verification/contract_checks.json",{
    "status":"passed", "malicious_or_invalid_cases":results,
    "canonical_cosmetic_identity":True, "structural_candidate_distinct":True,
    "candidate_code_execution":"none; restricted literal AST interpretation"})
print("Candidate restriction and canonicalization checks passed.")
