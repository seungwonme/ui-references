"""Pinned, offline DTCG schema checks and the supported reference semantics."""
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = Path(__file__).resolve().parents[1] / "assets/dtcg-format.schema.json"
SCHEMA_SHA256 = "32e93b780e4e4bca778d0780cb797a560deedc470c608af16576223f7e42915f"
SCHEMA_ID = "https://www.designtokens.org/schemas/2025.10/format.json"
PROFILE = "dtcg-2025.10-curly-aliases-v1"
ALIAS = re.compile(r"\{([^{}]+)\}\Z")


class TokenError(ValueError):
    """A contract failure safe to surface without dumping input values."""


def contract_info():
    return {"format": "DTCG 2025.10", "profile": PROFILE, "schema_sha256": SCHEMA_SHA256,
            "structure_and_values": "pass", "alias_semantics": "pass",
            "full_dtcg_conformance": False,
            "unsupported": ["$root", "$extends", "$ref", "array-alias-flattening"],
            "design_document": "project-prose-v1"}


@lru_cache(maxsize=1)
def schema_validator():
    try:
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
    except ImportError:
        raise TokenError("Token validation needs jsonschema; run this entry point with uv --no-config run --locked --script.") from None
    try:
        raw = SCHEMA.read_bytes()
    except OSError:
        raise TokenError("Pinned token schema is missing; restore the complete skill/runtime bundle.") from None
    if hashlib.sha256(raw).hexdigest() != SCHEMA_SHA256:
        raise TokenError("Pinned token schema hash differs; restore the reviewed schema before validation.")
    schema = json.loads(raw)
    # Register the bundled resource and its nested $id resources. No network retriever is installed.
    registry = Registry().with_resource(SCHEMA_ID, Resource.from_contents(schema))
    return Draft7Validator(schema, registry=registry)


def check_schema(validator, value, label):
    from jsonschema.exceptions import best_match
    error = best_match(validator.iter_errors(value))
    if error is not None:
        path = "/".join(str(part) for part in error.absolute_path) or "(root)"
        raise TokenError(f"DTCG 2025.10 schema check failed at {label}/{path} (rule: {error.validator}).")


def checked_tokens(document):
    try:
        json.dumps(document, allow_nan=False)
    except (ValueError, TypeError):
        raise TokenError("Token input must contain finite JSON values.") from None
    validator = schema_validator()
    check_schema(validator, document, "tokens")
    nodes = {}

    def collect(group, prefix="", inherited=None):
        for feature in ("$root", "$extends", "$ref"):
            if feature in group:
                raise TokenError(f"{PROFILE} does not support {feature} at {prefix or '(root)'}; select a compatible adapter.")
        if "$value" in group:
            if not prefix:
                raise TokenError("A token must have a name.")
            nodes[prefix] = (group, inherited)
        else:
            for key, value in group.items():
                if not key.startswith("$"):
                    collect(value, f"{prefix}.{key}" if prefix else key, group.get("$type", inherited))

    collect(document)
    resolved = {}

    def materialize(value, trail):
        if isinstance(value, str):
            match = ALIAS.fullmatch(value)
            return visit(match[1], trail)[2] if match else value
        if isinstance(value, dict):
            if "$ref" in value:
                raise TokenError(f"{PROFILE} does not support property-level $ref; select a compatible adapter.")
            return {key: materialize(item, trail) for key, item in value.items()}
        if isinstance(value, list):
            output = []
            for item in value:
                converted = materialize(item, trail)
                if isinstance(item, str) and ALIAS.fullmatch(item) and isinstance(converted, list):
                    raise TokenError(f"{PROFILE} does not support array-alias-flattening; select a compatible adapter.")
                output.append(converted)
            return output
        if isinstance(value, float) and not math.isfinite(value):
            raise TokenError("Token values must be finite JSON numbers.")
        return value

    token_schema = validator.schema["definitions"][SCHEMA_ID.removesuffix(".json") + "/token.json"]
    value_validator = validator.evolve(schema=token_schema)

    def visit(name, trail):
        if name not in nodes:
            raise TokenError(f"Missing token alias target: {name}")
        if name in trail:
            raise TokenError(f"Circular token alias involving: {name}")
        if name in resolved:
            return resolved[name]
        node, inherited = nodes[name]
        value = node["$value"]
        alias = ALIAS.fullmatch(value) if isinstance(value, str) else None
        if alias:
            target = visit(alias[1], trail | {name})
            kind = node.get("$type", target[1])
            if kind != target[1]:
                raise TokenError(f"Token alias type mismatch: {name}")
            actual = target[2]
        else:
            kind = node.get("$type", inherited)
            actual = materialize(value, trail | {name})
        if not kind:
            raise TokenError(f"Token {name} needs a $type (direct, inherited, or aliased).")
        # Inheritance and aliases can bypass static type branches. Check the resolved value with its effective type.
        check_schema(value_validator, {"$type": kind, "$value": actual}, name)
        resolved[name] = (node, kind, actual)
        return resolved[name]

    for name in nodes:
        visit(name, set())
    return resolved
