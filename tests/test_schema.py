# SPDX-License-Identifier: Apache-2.0
"""The action schema enforces the closed grammar.

These cases are written by hand — not derived from the generator — so they
independently pin the grammar: the kind enum, per-kind verb legality, required
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
    action = act(kind="step.exec")
    action.pop(field)
    return action


VALID: list[tuple[str, dict[str, Any]]] = [
    ("resource_get_intended", act(kind="step.resource", verb="GET")),
    ("resource_get_completed", act(kind="step.resource", verb="GET", output={"status": "ok"})),
    ("resource_post", act(kind="step.resource", verb="POST")),
    ("resource_patch", act(kind="step.resource", verb="PATCH")),
    ("resource_delete", act(kind="step.resource", verb="DELETE")),
    ("with_seq_and_action_id", act(kind="step.resource", verb="GET", seq=3, action_id="act-1")),
    ("with_properties", act(kind="step.resource", verb="GET",
                            properties={"target": {"trust": "internal", "host": "h"},
                                        "data": {"classification": "pii"}})),
    ("message_get", act(kind="step.message", verb="GET")),
    ("message_post", act(kind="step.message", verb="POST")),
    ("self_get", act(kind="step.self", verb="GET")),
    ("model_verbless", act(kind="step.model")),
    ("credential_get", act(kind="step.credential", verb="GET")),
    ("credential_delete", act(kind="step.credential", verb="DELETE")),
    ("exec_verbless", act(kind="step.exec", properties={"command": "ls"})),
    ("gate_verbless", act(kind="step.gate", output={"decision": "pass"}, properties={"kind": "guardrail"})),
    ("unknown_verbless", act(kind="step.unknown")),
    ("task_start", act(kind="task.start", aag_version="0.6.0",
                       properties={"agent": {"risk_classification": "high"}})),
    ("task_start_with_parent", act(kind="task.start", parent_task_id="run-parent")),
    ("task_end", act(kind="task.end")),
    ("task_error", act(kind="task.error")),
    ("task_idle", act(kind="task.idle")),
]

INVALID: list[tuple[str, dict[str, Any], str]] = [
    ("missing_agent_id", _drop("agent_id"), "is a required property"),
    ("missing_task_id", _drop("task_id"), "is a required property"),
    ("missing_timestamp", _drop("timestamp"), "is a required property"),
    ("missing_step_name", _drop("step_name"), "is a required property"),
    ("missing_kind", _drop("kind"), "is a required property"),
    ("resource_missing_verb", act(kind="step.resource"), "is a required property"),
    ("message_verb_patch", act(kind="step.message", verb="PATCH"), "is not one of"),
    ("message_verb_delete", act(kind="step.message", verb="DELETE"), "is not one of"),
    ("model_with_verb", act(kind="step.model", verb="POST"), "False schema does not allow"),
    ("task_start_with_verb", act(kind="task.start", verb="GET"), "False schema does not allow"),
    ("task_end_with_verb", act(kind="task.end", verb="GET"), "False schema does not allow"),
    ("exec_with_verb", act(kind="step.exec", verb="GET"), "False schema does not allow"),
    ("gate_with_verb", act(kind="step.gate", verb="GET"), "False schema does not allow"),
    # AAG <=0.5.0 called the classification field `type`. 0.6.0 renamed it to
    # `kind` with no alias, so the old field is rejected whether or not `kind`
    # is also present.
    ("legacy_type_field_without_kind", act(type="step.exec"), "'kind' is a required property"),
    ("legacy_type_field_beside_kind", act(kind="step.exec", type="step.exec"),
     "Additional properties are not allowed"),
    ("unknown_kind",act(kind="step.frobnicate"), "is not one of"),
    ("verb_lowercase", act(kind="step.resource", verb="get"), "is not one of"),
    ("aag_version_on_non_start", act(kind="step.exec", aag_version="0.6.0"), "False schema does not allow"),
    ("parent_task_id_on_non_start", act(kind="step.exec", parent_task_id="p"), "False schema does not allow"),
    ("additional_top_level_field", act(kind="step.exec", frobnicate=1), "Additional properties are not allowed"),
    ("negative_seq", act(kind="step.exec", seq=-1), "less than the minimum"),
    ("seq_not_integer", act(kind="step.exec", seq="3"), "is not of type 'integer'"),
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
