import pytest

from diagnostics.anyio_benchmark_prepare import BASE, INSTANCE, partition


def row():
    return dict(
        instance_id=INSTANCE,
        base_commit=BASE,
        repo="agronholm/anyio",
        problem_statement="public issue",
        patch="secret reference",
        test_patch="secret tests",
        hints_text="excluded hint",
        FAIL_TO_PASS=["new"],
        PASS_TO_PASS=[str(i) for i in range(32)],
        install_config={},
        environment_setup_commit=BASE,
        docker_image="image",
    )


def test_public_projection_excludes_answers_and_grading():
    public, private = partition(row())
    assert set(public) == {"instance_id", "base_commit", "repo", "problem_statement"}
    assert "secret" not in str(public)
    assert private["patch"] == "secret reference"
    assert "hints_text" not in private


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_commit", "wrong"),
        ("instance_id", "wrong"),
        ("PASS_TO_PASS", ["new"] * 32),
        ("FAIL_TO_PASS", []),
    ],
)
def test_rejects_wrong_identity_or_membership(field, value):
    data = row()
    data[field] = value
    with pytest.raises(ValueError):
        partition(data)
