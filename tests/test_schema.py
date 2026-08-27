# SPDX-License-Identifier: Apache-2.0
"""The action schema enforces the closed grammar.

These cases are written by hand — not derived from the generator — so they
independently pin the grammar: the type enum, per-type verb legality, required
fields, the task.start-only fields, and the closed top-level field set. Each
negative case asserts both that it fails *and* the reason it fails.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / "spec" / "action.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def act(**fields: Any) -> dict[str, Any]:
    """A minimally-populated action; add or override fields via kwargs."""
    base: dict[str, Any] = {
        "agent_id": "a",
        "task_id": "t",
        "timestamp": "2026-01-01T00:00:00Z",
        "step_name": "x",
    }
    base.update(fields)
    return base


def messages(action: dict[str, Any]) -> list[str]:
    """Return the schema-validation error messages for an action (empty if valid)."""
    return [e.message for e in VALIDATOR.iter_errors(action)]


def _drop(field: str) -> dict[str, Any]:
    """A valid verbless action with one required field removed."""
    action = act(type="step.exec")
    action.pop(field)
    return action


VALID: list[tuple[str, dict[str, Any]]] = [
    ("resource_get_intended", act(type="step.resource", verb="GET")),
    ("resource_get_completed", act(type="step.resource", verb="GET", output={"status": "ok"})),
    ("resource_post", act(type="step.resource", verb="POST")),
    ("resource_patch", act(type="step.resource", verb="PATCH")),
    ("resource_delete", act(type="step.resource", verb="DELETE")),
    ("with_seq_and_action_id", act(type="step.resource", verb="GET", seq=3, action_id="act-1")),
    ("with_properties", act(type="step.resource", verb="GET",
                            properties={"target": {"trust": "internal", "host": "h"},
                                        "data": {"classification": "pii"}})),
    ("message_get", act(type="step.message", verb="GET")),
    ("message_post", act(type="step.message", verb="POST")),
    ("self_get", act(type="step.self", verb="GET")),
    ("model_verbless", act(type="step.model")),
    ("credential_get", act(type="step.credential", verb="GET")),
    ("credential_delete", act(type="step.credential", verb="DELETE")),
    ("exec_verbless", act(type="step.exec", properties={"command": "ls"})),
    ("gate_verbless", act(type="step.gate", output={"decision": "pass"}, properties={"kind": "guardrail"})),
    ("unknown_verbless", act(type="step.unknown")),
    ("task_start", act(type="task.start", aag_version="0.5.0",
                       properties={"agent": {"risk_classification": "high"}})),
    ("task_start_with_parent", act(type="task.start", parent_task_id="run-parent")),
    ("task_end", act(type="task.end")),
    ("task_error", act(type="task.error")),
    ("task_idle", act(type="task.idle")),
]

INVALID: list[tuple[str, dict[str, Any], str]] = [
    ("missing_agent_id", _drop("agent_id"), "is a required property"),
    ("missing_task_id", _drop("task_id"), "is a required property"),
    ("missing_timestamp", _drop("timestamp"), "is a required property"),
    ("missing_step_name", _drop("step_name"), "is a required property"),
    ("missing_type", _drop("type"), "is a required property"),
    ("resource_missing_verb", act(type="step.resource"), "is a required property"),
    ("message_verb_patch", act(type="step.message", verb="PATCH"), "is not one of"),
    ("message_verb_delete", act(type="step.message", verb="DELETE"), "is not one of"),
    ("model_with_verb", act(type="step.model", verb="POST"), "False schema does not allow"),
    ("task_start_with_verb", act(type="task.start", verb="GET"), "False schema does not allow"),
    ("task_end_with_verb", act(type="task.end", verb="GET"), "False schema does not allow"),
    ("exec_with_verb", act(type="step.exec", verb="GET"), "False schema does not allow"),
    ("gate_with_verb", act(type="step.gate", verb="GET"), "False schema does not allow"),
    ("unknown_type", act(type="step.frobnicate"), "is not one of"),
    ("verb_lowercase", act(type="step.resource", verb="get"), "is not one of"),
    ("aag_version_on_non_start", act(type="step.exec", aag_version="0.5.0"), "False schema does not allow"),
    ("parent_task_id_on_non_start", act(type="step.exec", parent_task_id="p"), "False schema does not allow"),
    ("additional_top_level_field", act(type="step.exec", frobnicate=1), "Additional properties are not allowed"),
    ("negative_seq", act(type="step.exec", seq=-1), "less than the minimum"),
    ("seq_not_integer", act(type="step.exec", seq="3"), "is not of type 'integer'"),
]


@pytest.mark.parametrize("action", [a for _, a in VALID], ids=[i for i, _ in VALID])
def test_valid_actions_pass(action: dict[str, Any]) -> None:
    assert messages(action) == []


@pytest.mark.parametrize(
    "action,reason",
    [(a, r) for _, a, r in INVALID],
    ids=[i for i, _, _ in INVALID],
)
def test_invalid_actions_fail(action: dict[str, Any], reason: str) -> None:
    errs = messages(action)
    assert errs, "expected validation errors, got none"
    assert any(reason in m for m in errs), f"expected {reason!r} in {errs}"
