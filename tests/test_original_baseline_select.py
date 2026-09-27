import pytest

from diagnostics.original_baseline_select import select


def row(i, repo):
    return {
        "instance_id": i,
        "repo": repo,
        "install_config": {"log_parser": "parse_log_pytest"},
        "problem_statement": "issue",
        "docker_image": "image",
    }


def test_selection_order_independent_excludes_known_repos_and_deduplicates():
    rows = [row(str(i), repo) for i, repo in enumerate(["a", "a", "b", "c", "known"])]
    selected, count = select(rows, {"known"})
    assert selected == select(list(reversed(rows)), {"known"})[0]
    assert count == 4
    assert {r["repo"] for r in selected} == {"a", "b", "c"}


def test_insufficient_pool_is_not_silently_filled_from_excluded_tasks():
    with pytest.raises(ValueError):
        select([row("a", "a"), row("b", "b"), row("c", "known")], {"known"})
