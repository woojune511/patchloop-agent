import copy

import pytest

from diagnostics.swebench_lite_prepare import PUBLIC_FIELDS, partition, select_rows


def row(instance="org__repo-1", repo="org/repo"):
    return dict(
        instance_id=instance,
        repo=repo,
        base_commit="a" * 40,
        problem_statement="public issue",
        patch="secret answer",
        test_patch="secret tests",
        FAIL_TO_PASS=["new"],
        PASS_TO_PASS=["old"],
        eval_script="secret evaluator",
        log_parser="parse_log_pytest",
        eval_type="pass_and_fail",
        image="image:latest",
        version="1",
        environment_setup_commit="b" * 40,
        hints_text="secret hint",
        future_private_field="secret future field",
    )


def test_projection_never_exposes_answers_hints_or_evaluation_fields():
    data = row()
    before = copy.deepcopy(data)
    public, private = partition(data)
    assert set(public) == set(PUBLIC_FIELDS)
    assert "secret" not in str(public)
    assert "hints_text" not in private and "future_private_field" not in private
    assert private["patch"] == "secret answer"
    assert data == before


def test_selection_is_order_independent_diverse_and_answer_independent():
    rows = [row(f"o__r{i}-{j}", f"o/r{i}") for i in range(4) for j in range(3)]
    expected = [r["instance_id"] for r in select_rows(rows)]
    changed = copy.deepcopy(rows[::-1])
    for value in changed:
        value.update(patch="different answer", FAIL_TO_PASS=[], image="missing")
    assert [r["instance_id"] for r in select_rows(changed)] == expected
    assert len({r["repo"] for r in select_rows(rows)}) == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("FAIL_TO_PASS", []),
        ("PASS_TO_PASS", ["new"]),
        ("FAIL_TO_PASS", ["new", "new"]),
        ("PASS_TO_PASS", [123]),
        ("test_patch", ""),
        ("eval_script", ""),
    ],
)
def test_missing_or_ambiguous_oracle_is_rejected(field, value):
    data = row()
    data[field] = value
    with pytest.raises(ValueError):
        partition(data)


def test_string_membership_is_normalized_only_in_private_projection():
    data = row()
    data["FAIL_TO_PASS"] = '["new"]'
    assert partition(data)[1]["FAIL_TO_PASS"] == ["new"]
    assert data["FAIL_TO_PASS"] == '["new"]'


def test_selection_rejects_duplicate_ids_or_insufficient_repositories():
    with pytest.raises(ValueError, match="duplicate"):
        select_rows([row(), row()])
    with pytest.raises(ValueError, match="insufficient"):
        select_rows([row()])
