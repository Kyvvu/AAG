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


def test_consistency_catches_undeclared_granularity_prefix() -> None:
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["plan.sketch"] = spec["action_types"].pop("task.idle")
    assert any("not a declared granularity" in e for e in generate.check_consistency(spec))


def test_consistency_catches_granularity_restated_on_action_type() -> None:
    # `granularity` is derived from the type prefix; carrying it on an action
    # type would let the two disagree, so the checker must reject it.
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["task.start"]["granularity"] = "step"
    assert any("derived from the type prefix" in e for e in generate.check_consistency(spec))


def test_consistency_rejects_legacy_scope_field() -> None:
    # AAG <=0.5.0 drafts carried `scope: task|step` per action type. It is gone;
    # a source still carrying it must fail loudly rather than be ignored.
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["task.start"]["scope"] = "task"
    assert any("derived from the type prefix" in e for e in generate.check_consistency(spec))


def test_consistency_catches_bad_verb() -> None:
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["step.resource"]["verbs"] = ["FETCH"]
    assert any("unknown verb" in e for e in generate.check_consistency(spec))


def test_consistency_catches_wrong_type_count() -> None:
    spec = copy.deepcopy(generate.load())
    del spec["action_types"]["task.idle"]
    assert any("12 action types" in e for e in generate.check_consistency(spec))


def test_consistency_catches_bare_leaf_without_scoped_to() -> None:
    spec = copy.deepcopy(generate.load())
    spec["properties"]["suggested_leaves"].append({"path": "orphan", "bare": True})
    assert any("scoped_to" in e for e in generate.check_consistency(spec))


def test_consistency_catches_leaf_with_undefined_group() -> None:
    spec = copy.deepcopy(generate.load())
    spec["properties"]["suggested_leaves"].append({"path": "nogroup.leaf"})
    assert any("undefined group" in e for e in generate.check_consistency(spec))
