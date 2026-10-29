"""Public mutation constraints and deliberate legacy-recovery wire differences."""

import pytest
from pydantic import ValidationError

from patchloop.dev.contracts import CausalRevision, TextReplacementIntent
from patchloop.dev.tools import dev_tool_schemas


@pytest.fixture
def intent():
    return {
        "path": "src/a.py", "old_text": "old", "new_text": "new", "occurrence": 1,
        "hypothesis": "cause", "expected_behavior": "effect",
    }


def parameters():
    return next(
        tool["parameters"] for tool in dev_tool_schemas(finish_enabled=False)
        if tool["name"] == "replace_text"
    )


@pytest.mark.parametrize("field,minimum,maximum", [
    ("path", 1, 1_000),
    ("old_text", 1, 20_000),
    ("new_text", 0, 20_000),
    ("hypothesis", 1, 1_500),
    ("expected_behavior", 1, 1_500),
])
def test_fresh_mutation_strings_advertise_their_actual_boundaries(intent, field, minimum, maximum):
    public = parameters()["properties"][field]
    assert public["type"] == "string"
    assert public.get("minLength", 0) == minimum
    assert public["maxLength"] == maximum
    for length in sorted({0, minimum, maximum, maximum + 1}):
        value = "가" * length
        intent[field] = value
        if minimum <= length <= maximum:
            parsed = TextReplacementIntent.model_validate(intent)
            assert getattr(parsed, field) == value
        else:
            with pytest.raises(ValidationError):
                TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("occurrence,valid", [
    (0, False), (1, True), (100, True), (101, False),
    ("all", True), ("ALL", False), ("first", False), ("", False),
])
def test_occurrence_selection_boundaries(intent, occurrence, valid):
    assert parameters()["properties"]["occurrence"]["anyOf"] == [
        {"type": "integer", "minimum": 1, "maximum": 100},
        {"const": "all", "type": "string"},
    ]
    intent["occurrence"] = occurrence
    if valid:
        assert TextReplacementIntent.model_validate(intent).occurrence == occurrence
    else:
        with pytest.raises(ValidationError):
            TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("field", [
    "path", "old_text", "new_text", "occurrence", "hypothesis", "expected_behavior",
])
def test_required_public_fields_keep_internal_recovery_defaults_and_null_rules(intent, field):
    public = parameters()
    assert field in public["required"]
    assert "default" not in public["properties"][field]
    intent.pop(field)
    if field == "occurrence":
        parsed = TextReplacementIntent.model_validate(intent)
        assert parsed.occurrence == 1
    else:
        with pytest.raises(ValidationError):
            TextReplacementIntent.model_validate(intent)
    intent[field] = None
    if field != "occurrence":
        assert public["properties"][field]["type"] == "string"
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("invalid", [
    {},
    {"falsified_prior_hypothesis": "cause"},
    {"alternative_mechanism": "cause"},
    {"falsified_prior_hypothesis": None, "alternative_mechanism": "cause"},
    {"falsified_prior_hypothesis": "cause", "alternative_mechanism": "cause", "extra": 1},
])
def test_legacy_revision_keeps_required_children_and_rejects_extra_fields(intent, invalid):
    internal = CausalRevision.model_json_schema()
    assert internal["required"] == ["falsified_prior_hypothesis", "alternative_mechanism"]
    assert internal["additionalProperties"] is False
    assert "causal_revision" not in parameters()["properties"]
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**intent, "causal_revision": invalid})


@pytest.mark.parametrize("field", ["falsified_prior_hypothesis", "alternative_mechanism"])
def test_legacy_revision_preserves_string_boundaries(intent, field):
    revision = {"falsified_prior_hypothesis": "cause", "alternative_mechanism": "new cause"}
    for length in (0, 1, 1_500, 1_501):
        revision[field] = "가" * length
        wire = {**intent, "causal_revision": revision}
        if 1 <= length <= 1_500:
            assert TextReplacementIntent.model_validate(wire).model_dump() == wire
        else:
            with pytest.raises(ValidationError):
                TextReplacementIntent.model_validate(wire)


def test_recovery_only_fields_stay_private_and_preserve_absent_versus_explicit_values(intent):
    public = parameters()
    assert set(public["properties"]) == set(intent)
    assert set(public["required"]) == set(intent)
    assert public["additionalProperties"] is False
    assert TextReplacementIntent.model_validate(intent).model_dump() == intent
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**intent, "unknown": "value"})
    recovery_values = {
        "causal_revision": [None, {
            "falsified_prior_hypothesis": "prior cause", "alternative_mechanism": "new cause",
        }],
        "repair_prediction": [None, {"legacy": "data"}],
        "requirement_ref": [None, {"legacy": "data"}, ["old", "annotations"]],
        "behavior_cases": [None, {"legacy": "data"}, ["old", "annotations"]],
    }
    for field, values in recovery_values.items():
        assert field not in public["properties"] and field not in public["required"]
        assert field not in TextReplacementIntent.model_validate(intent).model_dump()
        for value in values:
            assert TextReplacementIntent.model_validate({**intent, field: value}).model_dump() == {
                **intent, field: value,
            }


def test_schema_results_do_not_share_mutable_fields_or_change_model_constraints():
    first = parameters()
    first["properties"]["hypothesis"]["maxLength"] = 7
    first["required"].clear()
    second = parameters()
    assert second["properties"]["hypothesis"]["maxLength"] == 1_500
    assert set(second["required"]) == {
        "path", "old_text", "new_text", "occurrence", "hypothesis", "expected_behavior",
    }
    internal = TextReplacementIntent.model_json_schema()["properties"]["hypothesis"]
    assert internal["maxLength"] == 1_500
