"""Interpret a bounded declarative Python program without executing its code.

The accepted language deliberately consists of one function returning a literal
specification. This prevents candidate access to files, imports, evaluator state,
outcomes, clocks, network and process APIs without relying on a Python sandbox.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "configs/effect-catalog-v1.json"


class InvalidSpecification(ValueError):
    pass


def _docstring(node):
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def validate_spec(spec, catalog=None):
    catalog = catalog or json.loads(CATALOG.read_text())
    if not isinstance(spec, dict) or set(spec) != {"schema_version", "network_effects"}:
        raise InvalidSpecification("Return exactly schema_version and network_effects; coefficients and fitness are not candidate inputs.")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != catalog["schema_version"]:
        raise InvalidSpecification("Unsupported schema_version.")
    effects = spec["network_effects"]
    if not isinstance(effects, list) or not all(isinstance(x, str) for x in effects):
        raise InvalidSpecification("network_effects must be a literal list of catalog effect names.")
    if len(effects) != len(set(effects)):
        raise InvalidSpecification("Repeated effects are not a distinct mathematical specification.")
    if len(effects) > catalog["max_network_effects"]:
        raise InvalidSpecification(f"At most {catalog['max_network_effects']} mutable network effects are permitted.")
    unknown = sorted(set(effects) - set(catalog["effects"]))
    if unknown:
        raise InvalidSpecification(f"Unsupported RSiena effects: {unknown}")
    return {"schema_version": spec["schema_version"], "network_effects": sorted(effects)}


def read_program(path):
    path = Path(path)
    if path.stat().st_size > 32768:
        raise InvalidSpecification("Candidate exceeds the 32 KiB declarative-program limit.")
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise InvalidSpecification(f"Malformed candidate: {exc}") from exc
    body = [node for node in tree.body if not _docstring(node)]
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise InvalidSpecification("Only build_network_spec(allowed_schema) is allowed; no imports or top-level executable statements.")
    function = body[0]
    args = function.args
    if (function.name != "build_network_spec" or function.decorator_list or function.returns
        or len(args.args) != 1 or args.args[0].arg != "allowed_schema"
        or args.args[0].annotation or args.defaults or args.kw_defaults or args.kwonlyargs
        or args.posonlyargs or args.vararg or args.kwarg or function.type_comment):
        raise InvalidSpecification("Required signature: build_network_spec(allowed_schema), with no decorators or evaluated annotations.")
    statements = [node for node in function.body if not _docstring(node)]
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        raise InvalidSpecification("Function must return one literal specification; loops, calls and filesystem access are prohibited.")
    literal = statements[0].value
    if not isinstance(literal, ast.Dict) or len(literal.keys) != 2:
        raise InvalidSpecification("Return a dictionary with exactly two distinct literal keys.")
    try:
        spec = ast.literal_eval(literal)
    except (ValueError, TypeError, RecursionError, MemoryError) as exc:
        raise InvalidSpecification("Specification must be literal data; candidate code is never executed.") from exc
    spec = validate_spec(spec)
    return spec, source


def canonical_bytes(spec):
    return json.dumps(validate_spec(spec), sort_keys=True, separators=(",", ":")).encode()


def spec_hash(spec):
    return hashlib.sha256(canonical_bytes(spec)).hexdigest()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("program_path", type=Path)
    options = parser.parse_args()
    spec, _ = read_program(options.program_path)
    print(json.dumps({"canonical_specification": spec, "sha256": spec_hash(spec)}, indent=2))
