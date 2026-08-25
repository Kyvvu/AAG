# SPDX-License-Identifier: Apache-2.0
"""Meta-tests over the generator.

Guards against three failure modes: the committed vocabulary.json /
action.schema.json drifting from vocabulary.yaml; the consistency checker
silently accepting a broken source; and the emitted schema not being a valid
JSON Schema.
"""
from __future__ import annotations

import copy
import json

import generate
from jsonschema import Draft202012Validator


def test_shipped_yaml_is_consistent() -> None:
    assert generate.check_consistency(generate.load()) == []


def test_generated_files_up_to_date() -> None:
    spec = generate.load()
    assert generate.render_vocabulary(spec) == generate.JSON_PATH.read_text(), \
        "vocabulary.json is stale — run: python spec/generate.py"
    assert generate._dumps(generate.build_action_schema(spec)) == generate.SCHEMA_PATH.read_text(), \
        "action.schema.json is stale — run: python spec/generate.py"


def test_emitted_schema_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(json.loads(generate.SCHEMA_PATH.read_text()))


def test_consistency_catches_type_outside_the_step_namespace() -> None:
    """Every action type name must use the ``step.`` prefix."""
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["plan.sketch"] = spec["action_types"].pop("step.task_idle")
    assert any("'step.' namespace" in e for e in generate.check_consistency(spec))


def test_consistency_rejects_retired_granularity_on_action_type() -> None:
    """Unsupported action-type metadata fails the consistency check."""
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["step.task_start"]["granularity"] = "step"
    assert any("not valid action-type keys" in e for e in generate.check_consistency(spec))


def test_consistency_rejects_legacy_scope_field() -> None:
    # Unsupported action-type metadata must fail loudly rather than be ignored.
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["step.task_start"]["scope"] = "task"
    assert any("not valid action-type keys" in e for e in generate.check_consistency(spec))


def test_consistency_catches_bad_verb() -> None:
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["step.resource"]["verbs"] = ["FETCH"]
    assert any("unknown verb" in e for e in generate.check_consistency(spec))


def test_consistency_catches_wrong_type_count() -> None:
    spec = copy.deepcopy(generate.load())
    del spec["action_types"]["step.task_idle"]
    assert any("12 action types" in e for e in generate.check_consistency(spec))


def test_consistency_catches_bare_leaf_without_scoped_to() -> None:
    spec = copy.deepcopy(generate.load())
    spec["properties"]["suggested_leaves"].append({"path": "orphan", "bare": True})
    assert any("scoped_to" in e for e in generate.check_consistency(spec))


def test_consistency_catches_leaf_with_undefined_group() -> None:
    spec = copy.deepcopy(generate.load())
    spec["properties"]["suggested_leaves"].append({"path": "nogroup.leaf"})
    assert any("undefined group" in e for e in generate.check_consistency(spec))
