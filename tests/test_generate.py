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


def test_consistency_catches_bad_scope() -> None:
    spec = copy.deepcopy(generate.load())
    spec["action_types"]["task.start"]["scope"] = "step"
    assert any("scope" in e for e in generate.check_consistency(spec))


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
