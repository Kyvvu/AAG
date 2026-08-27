#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate spec/vocabulary.json from spec/vocabulary.yaml.

``vocabulary.yaml`` is the canonical, human-authored source of truth.
``vocabulary.json`` is a machine-readable mirror produced by this script — do
not edit it by hand.

Before emitting, the script checks the YAML for internal consistency (so a
broken source can't silently produce a broken mirror).

Usage:
    python spec/generate.py            # (re)write vocabulary.json
    python spec/generate.py --check    # verify vocabulary.json is up to date (CI)

Depends only on PyYAML.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
YAML_PATH = HERE / "vocabulary.yaml"
JSON_PATH = HERE / "vocabulary.json"
SCHEMA_PATH = HERE / "action.schema.json"

VALID_VERBS = {"GET", "POST", "PATCH", "DELETE"}


def load() -> dict[str, Any]:
    """Parse ``vocabulary.yaml``.

    Returns:
        The vocabulary as a nested dict (the canonical source of truth).
    """
    with YAML_PATH.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{YAML_PATH.name} must contain a mapping, got {type(data).__name__}")
    return data


def check_consistency(spec: dict[str, Any]) -> list[str]:
    """Check the loaded vocabulary for internal contradictions.

    Args:
        spec: The parsed vocabulary (see :func:`load`).

    Returns:
        A list of human-readable problems. An empty list means the vocabulary is
        sound and safe to project.
    """
    errors: list[str] = []

    verbs = set(spec.get("verbs", {}))
    if verbs != VALID_VERBS:
        errors.append(f"`verbs` must be exactly {sorted(VALID_VERBS)}, got {sorted(verbs)}")

    # `granularity` is a derived projection of the type namespace, not a field on
    # an action: the declared values must be exactly the set of type prefixes.
    granularities = set(spec.get("granularity", {}).get("values", []))

    action_types = spec.get("action_types", {})
    # Tripwire: the count is deliberately hard-coded — adding or removing a type
    # is a conscious, versioned change, so it should force an edit here too.
    if len(action_types) != 12:
        errors.append(f"expected 12 action types, found {len(action_types)}")
    for t, d in action_types.items():
        if "." not in t:
            errors.append(f"{t}: type must contain a '.' granularity prefix")
            continue
        prefix = t.split(".", 1)[0]
        if prefix not in granularities:
            errors.append(
                f"{t}: prefix '{prefix}' is not a declared granularity "
                f"{sorted(granularities)}"
            )
        if "scope" in d or "granularity" in d:
            errors.append(
                f"{t}: granularity is derived from the type prefix and must not "
                f"be restated on the action type"
            )
        for v in d.get("verbs", []):
            if v not in VALID_VERBS:
                errors.append(f"{t}: unknown verb '{v}'")
        if not d.get("meaning"):
            errors.append(f"{t}: missing `meaning`")

    props = spec.get("properties", {})
    groups = set(props.get("groups", {}))
    for leaf in props.get("suggested_leaves", []):
        path = leaf.get("path", "")
        if leaf.get("bare"):
            if "." in path:
                errors.append(f"bare leaf '{path}' must not contain a '.'")
            if not leaf.get("scoped_to"):
                errors.append(f"bare leaf '{path}' is missing `scoped_to`")
        elif "." not in path:
            errors.append(f"leaf '{path}' must be dotted (group.leaf) or marked `bare`")
        else:
            group = path.split(".", 1)[0]
            if group not in groups:
                errors.append(f"leaf '{path}' references undefined group '{group}'")

    return errors


# Emitted into both generated files. These are spec/schema artifacts, so they
# carry the specification's license (CC-BY-4.0), not the generator's (Apache-2.0).
_GENERATED = (
    "GENERATED from vocabulary.yaml — do not edit by hand (run: python spec/generate.py). "
    "SPDX-License-Identifier: CC-BY-4.0"
)


def _dumps(doc: dict[str, Any]) -> str:
    """Serialize a dict to canonical, newline-terminated JSON.

    Args:
        doc: The object to serialize.

    Returns:
        Pretty-printed JSON (2-space indent, non-ASCII preserved) ending in a
        newline, so the generated files are diff-friendly.
    """
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def render_vocabulary(spec: dict[str, Any]) -> str:
    """Render the JSON mirror of the vocabulary, do-not-edit marker first.

    Args:
        spec: The parsed vocabulary (see :func:`load`).

    Returns:
        The serialized ``vocabulary.json`` content.
    """
    doc: dict[str, Any] = {"_comment": _GENERATED}
    doc.update(spec)
    return _dumps(doc)


def build_action_schema(spec: dict[str, Any]) -> dict[str, Any]:
    """Derive a JSON Schema for a single action from the vocabulary.

    Encodes the closed grammar: the type enum, the per-type verb legality
    (verb required and constrained where a type declares verbs; forbidden
    otherwise), the always-required fields, the task.start-only fields, a
    closed top-level field set, and an open `properties` object.
    """
    types = list(spec["action_types"])
    verbs = list(spec["verbs"])
    fields = spec["fields"]

    # Field -> JSON Schema fragment. `properties` is the open extension point;
    # `input`/`output` are intentionally untyped (any JSON value — granularity
    # is open, see model.md §2.5 and the RFC).
    field_schema: dict[str, dict[str, Any]] = {
        "agent_id": {"type": "string"},
        "task_id": {"type": "string"},
        "parent_task_id": {"type": "string"},
        "action_id": {"type": "string"},
        "seq": {"type": "integer", "minimum": 0},
        "timestamp": {"type": "string", "format": "date-time"},
        "step_name": {"type": "string"},
        "type": {"type": "string", "enum": types},
        "verb": {"type": "string", "enum": verbs},
        "aag_version": {"type": "string"},
        "properties": {"type": "object"},
        "input": {},
        "output": {},
    }
    # Attach each field's meaning from the yaml as its description.
    properties: dict[str, Any] = {}
    for name, frag in field_schema.items():
        frag = dict(frag)
        meaning = fields.get(name, {}).get("meaning")
        if meaning:
            frag["description"] = meaning
        properties[name] = frag

    required = [f for f, d in fields.items() if d.get("required") is True]

    all_of: list[dict[str, Any]] = []
    # Per-type verb legality.
    for t, d in spec["action_types"].items():
        # `required: [type]` so the conditional only fires when `type` is present;
        # an action missing `type` then fails once (on `type`) without noise.
        cond: dict[str, Any] = {"if": {"properties": {"type": {"const": t}}, "required": ["type"]}}
        if d.get("verbs"):
            cond["then"] = {"required": ["verb"], "properties": {"verb": {"enum": d["verbs"]}}}
        else:
            cond["then"] = {"properties": {"verb": False}}  # verb not allowed
        all_of.append(cond)

    # Fields restricted to task.start.
    task_only = [f for f, d in fields.items() if d.get("only_on") == ["task.start"]]
    if task_only:
        all_of.append({
            "if": {"not": {"properties": {"type": {"const": "task.start"}}}},
            "then": {"properties": {f: False for f in task_only}},
        })

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$comment": _GENERATED,
        "title": "AAG Action",
        "description": f"A single Agent Action Grammar action (AAG {spec['version']}).",
        "type": "object",
        "required": required,
        "additionalProperties": False,
        "properties": properties,
        "allOf": all_of,
    }


def main(argv: list[str]) -> int:
    """Run the generator.

    Loads and consistency-checks the vocabulary, then either writes
    ``vocabulary.json`` and ``action.schema.json`` or, with ``--check``, verifies
    they are up to date without writing.

    Args:
        argv: Command-line arguments; ``--check`` selects verify-only mode.

    Returns:
        Process exit code: ``0`` on success, ``1`` if ``--check`` finds a stale
        file, ``2`` if the vocabulary is inconsistent.
    """
    spec = load()

    errors = check_consistency(spec)
    if errors:
        print("vocabulary.yaml is inconsistent:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    outputs = {
        JSON_PATH: render_vocabulary(spec),
        SCHEMA_PATH: _dumps(build_action_schema(spec)),
    }

    if "--check" in argv:
        stale = [p.name for p, out in outputs.items()
                 if (p.read_text() if p.exists() else "") != out]
        if stale:
            print(f"out of date: {', '.join(stale)} — run: python spec/generate.py",
                  file=sys.stderr)
            return 1
        print("vocabulary.json and action.schema.json are up to date.")
        return 0

    for path, out in outputs.items():
        path.write_text(out)
    print(f"Wrote {JSON_PATH.name} and {SCHEMA_PATH.name} — "
          f"{len(spec['action_types'])} action types, "
          f"{len(spec['properties']['suggested_leaves'])} suggested leaves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
