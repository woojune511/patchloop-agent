"""Public mutation constraints and deliberate legacy-recovery wire differences."""

import pytest
from pydantic import ValidationError

from patchloop.dev.contracts import TextReplacementIntent
from patchloop.dev.tools import dev_tool_schemas


@pytest.fixture
def intent():
    return {
        "path": "src/a.py", "old_text": "old", "new_text": "new", "occurrence": 1,
        "hypothesis": "cause", "expected_behavior": "effect", "causal_revision": None,
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
    ("falsified_prior_hypothesis", 1, 1_500),
    ("alternative_mechanism", 1, 1_500),
])
def test_other_mutation_strings_advertise_their_actual_boundaries(intent, field, minimum, maximum):
    properties = parameters()["properties"]
    nested = field not in properties
    if nested:
        properties = properties["causal_revision"]["properties"]
        intent["causal_revision"] = {
            "falsified_prior_hypothesis": "prior cause", "alternative_mechanism": "new cause",
        }
    public = properties[field]
    assert public["type"] == "string"
    assert public.get("minLength", 0) == minimum
    assert public["maxLength"] == maximum
    for length in sorted({0, minimum, maximum, maximum + 1}):
        value = "가" * length
        target = intent["causal_revision"] if nested else intent
        target[field] = value
        if minimum <= length <= maximum:
            parsed = TextReplacementIntent.model_validate(intent)
            assert getattr(parsed.causal_revision if nested else parsed, field) == value
        else:
            with pytest.raises(ValidationError):
                TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("occurrence,valid", [(0, False), (1, True), (100, True), (101, False)])
def test_occurrence_numeric_boundaries(intent, occurrence, valid):
    assert parameters()["properties"]["occurrence"] == {
        "type": "integer", "minimum": 1, "maximum": 100,
    }
    intent["occurrence"] = occurrence
    if valid:
        assert TextReplacementIntent.model_validate(intent).occurrence == occurrence
    else:
        with pytest.raises(ValidationError):
            TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("field", [
    "path", "old_text", "new_text", "occurrence", "hypothesis", "expected_behavior",
    "causal_revision",
])
def test_required_public_fields_keep_internal_recovery_defaults_and_null_rules(intent, field):
    public = parameters()
    assert field in public["required"]
    assert "default" not in public["properties"][field]
    intent.pop(field)
    if field in {"occurrence", "causal_revision"}:
        parsed = TextReplacementIntent.model_validate(intent)
        assert getattr(parsed, field) == (1 if field == "occurrence" else None)
    else:
        with pytest.raises(ValidationError):
            TextReplacementIntent.model_validate(intent)
    intent[field] = None
    if field == "causal_revision":
        assert public["properties"][field]["type"] == ["object", "null"]
        assert TextReplacementIntent.model_validate(intent).causal_revision is None
    else:
        assert public["properties"][field]["type"] in {"string", "integer"}
        with pytest.raises(ValidationError):
            TextReplacementIntent.model_validate(intent)


@pytest.mark.parametrize("invalid", [
    {},
    {"falsified_prior_hypothesis": "cause"},
    {"alternative_mechanism": "cause"},
    {"falsified_prior_hypothesis": None, "alternative_mechanism": "cause"},
    {"falsified_prior_hypothesis": "cause", "alternative_mechanism": "cause", "extra": 1},
])
def test_revision_object_keeps_required_children_and_rejects_extra_fields(intent, invalid):
    public = parameters()["properties"]["causal_revision"]
    assert public["required"] == ["falsified_prior_hypothesis", "alternative_mechanism"]
    assert public["additionalProperties"] is False
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**intent, "causal_revision": invalid})


def test_recovery_only_fields_stay_private_and_preserve_absent_versus_explicit_values(intent):
    public = parameters()
    assert set(public["properties"]) == set(intent) | {"turn_decision"}
    assert public["additionalProperties"] is False
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**intent, "unknown": "value"})
    for field in ("requirement_ref", "behavior_cases"):
        assert field not in public["properties"] and field not in public["required"]
        assert field not in TextReplacementIntent.model_validate(intent).model_dump()
        for value in (None, {"legacy": "data"}, ["old", "annotations"]):
            assert TextReplacementIntent.model_validate({**intent, field: value}).model_dump() == {
                **intent, field: value,
            }


def test_schema_results_do_not_share_mutable_fields_or_change_model_constraints():
    first = parameters()
    first["properties"]["hypothesis"]["maxLength"] = 7
    first["properties"]["causal_revision"]["required"].clear()
    second = parameters()
    assert second["properties"]["hypothesis"]["maxLength"] == 1_500
    assert len(second["properties"]["causal_revision"]["required"]) == 2
    internal = TextReplacementIntent.model_json_schema()["properties"]["hypothesis"]
    assert internal["maxLength"] == 1_500
