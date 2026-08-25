# SPDX-License-Identifier: Apache-2.0
"""Every shipped example behaves: valid actions pass, invalid_* fail, tasks are
well-formed streams."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "spec" / "action.schema.json").read_text())
# Format-checking enabled so examples are validated exactly as the shipped
# validator validates them (e.g. the timestamp date-time format is enforced).
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)

ACTION_FILES = sorted((ROOT / "examples" / "actions").glob("*.json"))
TASK_FILES = sorted((ROOT / "examples" / "tasks").glob("*.ndjson"))


@pytest.mark.parametrize("path", ACTION_FILES, ids=[p.name for p in ACTION_FILES])
def test_action_example(path: Path) -> None:
    action = json.loads(path.read_text())
    errs = [e.message for e in VALIDATOR.iter_errors(action)]
    if path.name.startswith("invalid_"):
        assert errs, f"{path.name} is named invalid_ but validates"
    else:
        assert not errs, f"{path.name} should be valid: {errs}"


@pytest.mark.parametrize("path", TASK_FILES, ids=[p.name for p in TASK_FILES])
def test_task_example(path: Path) -> None:
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    assert lines, f"{path.name} is empty"
    task_ids = set()
    types = []
    for i, line in enumerate(lines):
        action = json.loads(line)
        errs = [e.message for e in VALIDATOR.iter_errors(action)]
        assert not errs, f"{path.name} line {i} invalid: {errs}"
        task_ids.add(action["task_id"])
        types.append(action["type"])
    assert len(task_ids) == 1, f"{path.name} mixes task_ids: {task_ids}"
    assert types[0] == "step.task_start"
    assert types[-1] == "step.task_end"
