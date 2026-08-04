# SPDX-License-Identifier: Apache-2.0
"""The validator: single actions, task streams/arrays, and task-level checks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import validate

ROOT = Path(__file__).resolve().parent.parent
ACTIONS = ROOT / "examples" / "actions"
TASKS = ROOT / "examples" / "tasks"

VALIDATOR = validate.load_validator()


def _act(**fields: Any) -> dict[str, Any]:
    """A minimal valid ``step.exec`` action; add or override fields via kwargs."""
    base: dict[str, Any] = {
        "agent_id": "a",
        "task_id": "t",
        "timestamp": "2026-01-01T00:00:00Z",
        "step_name": "x",
        "type": "step.exec",
    }
    base.update(fields)
    return base


def test_read_single_object(tmp_path: Path) -> None:
    f = tmp_path / "a.json"
    f.write_text(json.dumps(_act()))
    actions, is_task = validate.read_actions(f)
    assert not is_task
    assert len(actions) == 1


def test_read_json_array_is_task(tmp_path: Path) -> None:
    f = tmp_path / "t.json"
    f.write_text(json.dumps([_act(), _act()]))
    actions, is_task = validate.read_actions(f)
    assert is_task
    assert len(actions) == 2


def test_read_ndjson_is_task(tmp_path: Path) -> None:
    f = tmp_path / "t.ndjson"
    f.write_text(json.dumps(_act()) + "\n" + json.dumps(_act()) + "\n")
    actions, is_task = validate.read_actions(f)
    assert is_task
    assert len(actions) == 2


def test_valid_action_no_errors() -> None:
    assert validate.validate_action(_act(), VALIDATOR, "a") == []


def test_invalid_action_has_errors() -> None:
    assert validate.validate_action(_act(verb="GET"), VALIDATOR, "a")  # verb on a verbless type


def test_malformed_timestamp_is_rejected() -> None:
    # The date-time format is enforced (not just annotated) via the validator's
    # format checker — a syntactically-wrong timestamp must fail.
    errors = validate.validate_action(_act(timestamp="not-a-real-timestamp"), VALIDATOR, "a")
    assert any("date-time" in e for e in errors)


def test_well_formed_timestamp_is_accepted() -> None:
    assert validate.validate_action(_act(timestamp="2026-07-30T09:14:23Z"), VALIDATOR, "a") == []


def test_task_mixed_task_id_is_error() -> None:
    errors, _ = validate.validate_task([_act(task_id="T1"), _act(task_id="T2")])
    assert any("share one task_id" in e for e in errors)


def test_task_out_of_order_seq_warns() -> None:
    _, warnings = validate.validate_task([_act(type="task.start", seq=1), _act(seq=0)])
    assert any("non-decreasing" in w for w in warnings)


def test_task_missing_start_warns() -> None:
    _, warnings = validate.validate_task([_act(type="step.exec")])
    assert any("does not begin with task.start" in w for w in warnings)


def test_task_end_not_last_warns() -> None:
    _, warnings = validate.validate_task([_act(type="task.start"), _act(type="task.end"), _act()])
    assert any("not the last action" in w for w in warnings)


def test_clean_task_has_no_issues() -> None:
    actions = [_act(type="task.start", seq=0), _act(seq=1), _act(type="task.end", seq=2)]
    errors, warnings = validate.validate_task(actions)
    assert errors == []
    assert warnings == []


def test_example_valid_action() -> None:
    errors, _, count = validate.validate_file(ACTIONS / "step_resource_post.json", VALIDATOR)
    assert errors == []
    assert count == 1


def test_example_invalid_action() -> None:
    errors, _, _ = validate.validate_file(ACTIONS / "invalid_step_model_with_verb.json", VALIDATOR)
    assert errors


def test_example_task() -> None:
    errors, _, count = validate.validate_file(TASKS / "support_ticket.ndjson", VALIDATOR)
    assert errors == []
    assert count == 8


def test_main_exit_codes() -> None:
    assert validate.main([str(ACTIONS / "step_resource_post.json")]) == 0
    assert validate.main([str(ACTIONS / "invalid_step_model_with_verb.json")]) == 1
    assert validate.main([]) == 2
