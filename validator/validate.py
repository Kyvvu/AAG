#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate AAG actions and tasks against the action schema.

Usage:
    python validator/validate.py FILE [FILE ...]

Each FILE is one of:
  * a single action — a ``.json`` file holding one JSON object;
  * a task          — a ``.ndjson`` stream (one action per line), or a ``.json``
                      file holding a JSON array of actions.

Every action is checked against ``spec/action.schema.json``. A task additionally
checks a few structural invariants: one shared ``task_id`` (an error), and — as
warnings — that it begins with ``task.start``, that any ``task.end`` is last, and
that ``seq`` values are non-decreasing.

Exit code is non-zero if any file has errors. Depends on ``jsonschema`` and the
generated ``spec/action.schema.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "spec" / "action.schema.json"


def load_validator() -> Draft202012Validator:
    """Build a validator from the generated action schema.

    The ``date-time`` ``format`` on ``timestamp`` is *enforced*, not merely
    annotated — so a malformed timestamp is rejected. This requires the
    ``rfc3339-validator`` package (a dependency of this repo); without it,
    jsonschema silently skips the ``date-time`` check.

    Returns:
        A validator with format-checking enabled.
    """
    schema = json.loads(SCHEMA_PATH.read_text())
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def read_actions(path: Path) -> tuple[list[Any], bool]:
    """Read a file into a list of actions.

    Returns ``(actions, is_task)``. A single action becomes a one-element list
    with ``is_task=False``. A ``.ndjson`` stream or a ``.json`` array is a task.
    """
    if path.suffix == ".ndjson":
        actions = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return actions, True
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data, True
    return [data], False


def validate_action(action: Any, validator: Draft202012Validator, where: str) -> list[str]:
    """Return schema-validation error strings for one action (empty if valid)."""
    errors: list[str] = []
    for err in sorted(validator.iter_errors(action), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{where}: {loc}: {err.message}")
    return errors


def validate_task(actions: list[Any]) -> tuple[list[str], list[str]]:
    """Structural checks over a task's actions (schema checks happen separately).

    Returns ``(errors, warnings)``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    task_ids = {a["task_id"] for a in actions if isinstance(a, dict) and "task_id" in a}
    if len(task_ids) > 1:
        errors.append(f"a task must share one task_id; found {sorted(str(t) for t in task_ids)}")

    types = [a.get("type") for a in actions if isinstance(a, dict)]
    if types and types[0] != "task.start":
        warnings.append(f"task does not begin with task.start (first is {types[0]!r})")
    if "task.end" in types and types[-1] != "task.end":
        warnings.append("a task.end is present but is not the last action")

    seqs = [a["seq"] for a in actions if isinstance(a, dict) and "seq" in a]
    if seqs != sorted(seqs):
        warnings.append(f"seq values are not non-decreasing: {seqs}")

    return errors, warnings


def validate_file(path: Path, validator: Draft202012Validator) -> tuple[list[str], list[str], int]:
    """Validate one file. Returns ``(errors, warnings, action_count)``."""
    try:
        actions, is_task = read_actions(path)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"could not read: {exc}"], [], 0

    errors: list[str] = []
    warnings: list[str] = []
    if is_task:
        for i, action in enumerate(actions):
            errors += validate_action(action, validator, f"action {i}")
        task_errors, warnings = validate_task(actions)
        errors += task_errors
    else:
        errors += validate_action(actions[0], validator, "action")
    return errors, warnings, len(actions)


def main(argv: list[str]) -> int:
    """Validate the given files and report the result.

    Args:
        argv: Paths to validate. Each is a single action (``.json`` object) or a
            task (``.ndjson`` stream / ``.json`` array).

    Returns:
        Process exit code: ``0`` if every file is valid, ``1`` if any file has
        errors, ``2`` if no paths were given.
    """
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    validator = load_validator()
    failed = 0
    for arg in argv:
        path = Path(arg)
        errors, warnings, count = validate_file(path, validator)
        for warning in warnings:
            print(f"  warning: {warning}")
        if errors:
            failed += 1
            print(f"FAIL  {path}  ({count} action{'s' if count != 1 else ''})")
            for error in errors:
                print(f"  error: {error}")
        else:
            print(f"ok    {path}  ({count} action{'s' if count != 1 else ''})")

    print(f"\n{len(argv) - failed}/{len(argv)} file(s) valid.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
