"""Declarative native RSiena network specifications, with no candidate execution.

This module is separate from the active v1 evaluator.  A candidate constructs
statistics; the trusted estimator fits every coefficient and the evaluator owns
all outcomes, forecast rules, objective values and Pareto comparisons.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "configs/effect-catalog-v2.json"
PROGRAM_BYTE_LIMIT = 32768
NATIVE_INTEGER_MAX = 2147483647
LEGACY_PARAMETERS = {"degPlus": 1, "transTriads": 0, "inPop": 0, "gwesp": 69}


class InvalidSpecification(ValueError):
    """An unsupported or intrinsically redundant scientific specification."""


def _json_key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _atom(value, catalog):
    if not isinstance(value, dict) or not {"effect", "parameter"} <= set(value):
        raise InvalidSpecification("Every atom requires effect and integer parameter.")
    if set(value) - {"effect", "parameter", "covariate"}:
        raise InvalidSpecification("Atoms accept only effect, parameter and optional covariate; coefficients are estimated.")
    effect = value["effect"]
    if not isinstance(effect, str):
        raise InvalidSpecification("Effect names must be literal strings.")
    effect = catalog["effect_aliases"].get(effect, effect)
    if effect not in catalog["effects"]:
        raise InvalidSpecification(f"Unsupported native RSiena effect: {effect!r}.")
    descriptor = catalog["effects"][effect]
    parameter = value["parameter"]
    if type(parameter) is not int or not 0 <= parameter <= NATIVE_INTEGER_MAX:
        raise InvalidSpecification(f"{effect}: parameter must be an integer representable by native R/C++ (0..{NATIVE_INTEGER_MAX}).")
    rule = descriptor["parameter_rule"]
    kind = rule["kind"]
    if kind == "degree_root_switch":
        if parameter < 1:
            raise InvalidSpecification("degPlus uses parameter 1 for raw degree or >=2 for square roots.")
        parameter = 2 if parameter >= 2 else 1
    elif kind == "ignored":
        parameter = rule["canonical"]
    elif kind == "choices":
        if parameter not in rule["values"]:
            raise InvalidSpecification(f"{effect}: supported parameters are {rule['values']}.")
    elif kind == "positive_integer":
        if parameter < 1:
            raise InvalidSpecification(f"{effect}: native parameter must be at least 1.")
    elif kind == "truncation_knot":
        maximum_degree = catalog["network_node_count"] - 1
        if not 1 <= parameter < maximum_degree:
            raise InvalidSpecification(f"outTrunc requires a genuine knot 1..{maximum_degree - 1} for the declared {catalog['network_node_count']}-actor universe. At k>={maximum_degree} its native tie-change contribution is the protected density contribution, not a truncation mechanism.")
    elif kind == "gwesp_integer":
        # Mirror GwespFunction.cpp's actual double-precision calculation. Huge
        # k either overflows exp(k/100) or rounds its geometric factor to 1,
        # making all cumulative weights zero; neither is an estimable statistic.
        try:
            scale = math.exp(parameter / 100.0)
            factor = 1.0 - math.exp(-parameter / 100.0)
        except OverflowError as exc:
            raise InvalidSpecification("gwesp parameter overflows the native exponential.") from exc
        if not math.isfinite(scale) or factor == 1.0:
            raise InvalidSpecification("gwesp parameter makes native weights nonfinite or identically zero at double precision.")
    else:
        raise InvalidSpecification(f"Unknown trusted parameter rule: {kind}.")
    atom = {"effect": effect, "parameter": parameter}
    covariate_kind = descriptor.get("covariate_kind")
    if covariate_kind:
        covariate = value.get("covariate")
        if not isinstance(covariate, str) or covariate not in catalog["covariates"][covariate_kind]:
            raise InvalidSpecification(f"{effect}: covariate must be a declared {covariate_kind} origin-available variable.")
        atom["covariate"] = covariate
    elif "covariate" in value:
        raise InvalidSpecification(f"{effect} does not accept a covariate.")
    return atom


def _term(value, catalog):
    if isinstance(value, dict) and "product" in value:
        if set(value) != {"product"}:
            raise InvalidSpecification("An interaction contains exactly one product field.")
        factors = value["product"]
        if not isinstance(factors, list) or len(factors) not in (2, 3):
            raise InvalidSpecification("Native network products contain exactly two or three atoms; nested products are unsupported.")
        factors = sorted((_atom(atom, catalog) for atom in factors), key=_json_key)
        types = [catalog["effects"][atom["effect"]]["interaction_type"] for atom in factors]
        egos = types.count("ego")
        dyads = types.count("dyadic")
        compatible = (egos >= 1 or dyads == 2) if len(factors) == 2 else (egos >= 2 or egos + dyads == 3)
        if not compatible:
            raise InvalidSpecification("Unsupported native interaction: two factors require >=1 ego or both dyadic; three require >=2 ego or all ego/dyadic.")
        # Native GWESP(0) returns a binary closure indicator for BOTH the
        # tie-change contribution and tie statistic. Products of repeated
        # copies therefore have exactly the same native meaning as one copy.
        # This does not apply to transTies, whose contribution is not binary.
        folded = []
        seen_zero_gwesp = False
        for atom in factors:
            zero_gwesp = atom["effect"] == "gwesp" and atom["parameter"] == 0
            if zero_gwesp and seen_zero_gwesp:
                continue
            folded.append(atom)
            seen_zero_gwesp = seen_zero_gwesp or zero_gwesp
        if len(folded) == 1:
            if catalog["effects"][folded[0]["effect"]]["role"] == "modifier":
                raise InvalidSpecification("A reduced product cannot introduce a standalone covariate modifier; original main controls are protected.")
            return folded[0]
        if len(folded) != len(factors):
            types = [catalog["effects"][atom["effect"]]["interaction_type"] for atom in folded]
            if types.count("ego") < 1 and types.count("dyadic") != 2:
                raise InvalidSpecification("The reduced two-factor interaction must retain >=1 ego factor or two dyadic factors.")
            factors = folded
        return {"product": factors}
    atom = _atom(value, catalog)
    if catalog["effects"][atom["effect"]]["role"] == "modifier":
        raise InvalidSpecification("egoX, altX and X are interaction modifiers only; the original empirical main controls are protected.")
    return atom


def validate_spec(spec, catalog=None):
    """Return one canonical schema-v2 specification, accepting legacy v1 input.

    Factor order, term order and native aliases have no influence on identity.
    Proportional estimation moments are rejected, not merged into actor-choice
    mechanisms: degree popularity and degree activity remain distinct models.
    """
    catalog = catalog if catalog is not None else json.loads(CATALOG.read_text())
    if catalog.get("schema_version") != 2:
        raise InvalidSpecification("The trusted schema-v2 catalog is required.")
    if not isinstance(spec, dict) or set(spec) != {"schema_version", "network_effects"}:
        raise InvalidSpecification("Return exactly schema_version and network_effects; fitness and coefficient values are not candidate inputs.")
    version = spec["schema_version"]
    if type(version) is not int or version not in (1, 2):
        raise InvalidSpecification("Unsupported schema_version; use 2 (legacy literal schema 1 can be normalized).")
    effects = spec["network_effects"]
    if not isinstance(effects, list):
        raise InvalidSpecification("network_effects must be a literal list.")
    if version == 1:
        if not all(isinstance(effect, str) and effect in LEGACY_PARAMETERS for effect in effects):
            raise InvalidSpecification("Legacy schema 1 supports only degPlus, transTriads, inPop and gwesp.")
        effects = [{"effect": effect, "parameter": LEGACY_PARAMETERS[effect]} for effect in effects]
    terms = sorted((_term(term, catalog) for term in effects), key=_json_key)
    keys = [_json_key(term) for term in terms]
    if len(set(keys)) != len(keys):
        raise InvalidSpecification("Repeated canonical terms, including native aliases, cannot be separately estimated.")
    estimated_atoms = {(term["effect"], term["parameter"]) for term in terms if "effect" in term}
    for group in catalog["proportional_main_moment_groups"]:
        present = estimated_atoms.intersection((atom["effect"], atom["parameter"]) for atom in group["members"])
        if len(present) > 1:
            raise InvalidSpecification(f"Jointly estimated {group['name']} statistics are proportional on symmetric networks: {sorted(present)}. Choose one mechanism; do not interpret aliases as new evidence.")
    # GWESP(0) and transTies have the same per-ego closure-presence statistic,
    # including when multiplied by the same native ego covariate factor(s).
    # Their tie-change contributions differ, so this is an identification
    # exclusion, never an alias or a merger of their scientific identities.
    interaction_moments = set()
    for term in terms:
        if "product" not in term:
            continue
        factors = [{"effect": "transTies", "parameter": 0}
                   if atom["effect"] == "gwesp" and atom["parameter"] == 0
                   else atom for atom in term["product"]]
        moment_key = _json_key({"product": sorted(factors, key=_json_key)})
        if moment_key in interaction_moments:
            raise InvalidSpecification("gwesp(0) and transTies with the same compatible ego covariate factors have identical estimation moments but different actor-choice mechanisms; choose one interaction.")
        interaction_moments.add(moment_key)
    return {"schema_version": 2, "network_effects": terms}


def _docstring(node):
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def read_program(path):
    """Read only a single literal-return function; never execute candidate code."""
    path = Path(path)
    if path.stat().st_size > PROGRAM_BYTE_LIMIT:
        raise InvalidSpecification("Candidate exceeds the 32 KiB declarative-program limit.")
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, RecursionError, UnicodeError) as exc:
        raise InvalidSpecification(f"Malformed candidate: {exc}") from exc
    body = [node for node in tree.body if not _docstring(node)]
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise InvalidSpecification("Only build_network_spec(allowed_schema) is allowed; no imports or top-level executable statements.")
    function = body[0]
    args = function.args
    if (function.name != "build_network_spec" or function.decorator_list or function.returns
        or len(args.args) != 1 or args.args[0].arg != "allowed_schema"
        or args.args[0].annotation or args.defaults or args.kw_defaults or args.kwonlyargs
        or args.posonlyargs or args.vararg or args.kwarg or function.type_comment
        or getattr(function, "type_params", ())):
        raise InvalidSpecification("Required signature: build_network_spec(allowed_schema), without decorators or annotations.")
    statements = [node for node in function.body if not _docstring(node)]
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        raise InvalidSpecification("The function must return one literal specification; calls and statements are unsupported.")
    literal = statements[0].value
    if not isinstance(literal, ast.Dict) or len(literal.keys) != 2:
        raise InvalidSpecification("Return a dictionary with exactly two distinct literal keys.")
    try:
        for node in ast.walk(literal):
            if isinstance(node, ast.Dict):
                names = [ast.literal_eval(key) for key in node.keys]
                if len(names) != len(set(names)):
                    raise InvalidSpecification("Duplicate dictionary keys are unsupported.")
        spec = ast.literal_eval(literal)
    except (ValueError, TypeError, RecursionError, MemoryError) as exc:
        raise InvalidSpecification("Specification must be literal data with distinct keys; candidate code is never executed.") from exc
    return validate_spec(spec), source


def canonical_bytes(spec):
    return _json_key(validate_spec(spec)).encode("utf-8")


def spec_hash(spec):
    return hashlib.sha256(canonical_bytes(spec)).hexdigest()


def legacy_specification(spec):
    """Return the exact old-schema representation for an old-cache lookup.

    This helper supplies specification identity only. Training observations,
    estimator/forecast settings, software, seeds and acceptance still have to
    match before any saved result can be reused.
    """
    spec = validate_spec(spec)
    effects = spec["network_effects"]
    if len(effects) > 3 or any("product" in term or "covariate" in term
                             or LEGACY_PARAMETERS.get(term["effect"]) != term["parameter"]
                             for term in effects):
        return None
    return {"schema_version": 1, "network_effects": sorted(term["effect"] for term in effects)}


def complexity(spec):
    """Descriptive structural complexity, never an objective bonus/penalty."""
    terms = validate_spec(spec)["network_effects"]
    return {"estimated_network_terms": len(terms),
            "interaction_terms": sum("product" in term for term in terms),
            "factor_occurrences": sum(len(term["product"]) if "product" in term else 1 for term in terms)}
