from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.source_glob import matches_source_glob
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("root.py", "**/*", True),
        ("root.py", "**/*.py", True),
        ("pkg/direct.py", "pkg/**/*.py", True),
        ("pkg/deep/nested.py", "pkg/**/*.py", True),
        ("pkg/deep/deeper/leaf.py", "pkg/**/*.py", True),
        ("pkg/direct.py", "pkg/*.py", True),
        ("pkg/deep/nested.py", "pkg/*.py", False),
        ("pkg/direct.py", "*.py", False),
        ("pkg/direct.py", "pkg/direct.py", True),
        ("other/pkg/direct.py", "pkg/**/*.py", False),
        ("pkg/a.py", "pkg/?.py", True),
        ("pkg/ab.py", "pkg/?.py", False),
        ("pkg/a.py", "pkg/[ab].py", True),
        ("pkg/c.py", "pkg/[!ab].py", True),
        ("pkg/a.py", "pkg/[!ab].py", False),
        ("pkg/Direct.py", "pkg/direct.py", False),
        ("pkg/direct.py", "**/**/direct.py", True),
        ("direct.py", "**/**/direct.py", True),
        ("pkg/deep/end/file.py", "pkg/**/end/*.py", True),
        ("pkg/end/file.py", "pkg/**/end/*.py", True),
        ("pkg/end/deep/file.py", "pkg/**/end/*.py", False),
        ("pkg/deep/file.py", "pkg/**", True),
        ("pkg/deep/file.py", "pkg/**file.py", False),
    ],
)
def test_source_glob_matches_path_components(path, pattern, expected):
    assert matches_source_glob(path, pattern) is expected


@pytest.fixture
def search_gateway(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    tracked = [
        "root.py", "pkg/direct.py", "pkg/deep/nested.py", "pkg/deep/deeper/leaf.py",
        "notes.txt", ".patchloop-hidden/private.py", "broken.py",
    ]
    for relative in tracked:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# PUBLIC_SEARCH_MARKER\nvalue = 1\n")
    (workspace / "broken.py").write_bytes(b"\xff\xfePUBLIC_SEARCH_MARKER")
    for args in [
        ["init", "--quiet"], ["config", "core.autocrlf", "false"], ["add", "--", *tracked],
        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
    ]:
        subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True)
    (workspace / "untracked.py").write_text("PUBLIC_SEARCH_MARKER\n", encoding="utf-8")
    public = SimpleNamespace(
        constraints=SimpleNamespace(
            allowed_paths=["pkg/direct.py"], forbidden_paths=[],
            max_changed_files=1, max_diff_lines=50,
        ),
        visible_checks=[],
    )
    return DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None,
        journal=DevJournal(tmp_path / "state", "run_dev_search_v16"), limits=DevLimits(),
    )


def _search(action_id, *, pattern="**/*", query="PUBLIC_SEARCH_MARKER"):
    return RequestedTool(
        name="search_files", action_id=action_id,
        arguments={"query": query, "path_glob": pattern},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Locate the public behavior owner.",
            evidence_goal="Identify current source matching the literal observation.",
        ),
    )


def test_recursive_search_includes_zero_depth_and_preserves_public_admission(search_gateway):
    gateway = search_gateway
    recursive = gateway.execute(_search("recursive", pattern="pkg/**/*.py"))
    assert recursive.status == "succeeded"
    assert {span["path"] for span in recursive.output["spans"]} == {
        "pkg/direct.py", "pkg/deep/nested.py", "pkg/deep/deeper/leaf.py",
    }
    assert recursive.output["searched_file_count"] == 3
    all_files = gateway.execute(_search("all"))
    assert all_files.output["searched_file_count"] == 5
    assert {span["path"] for span in all_files.output["spans"]} == {
        "root.py", "pkg/direct.py", "pkg/deep/nested.py", "pkg/deep/deeper/leaf.py", "notes.txt",
    }
    exact = gateway.execute(_search("exact", pattern="root.py"))
    assert exact.output["searched_file_count"] == 1
    assert exact.output["spans"][0]["path"] == "root.py"
    direct = gateway.execute(_search("direct", pattern="pkg/*.py"))
    assert [span["path"] for span in direct.output["spans"]] == ["pkg/direct.py"]
    schema = next(s for s in dev_tool_schemas(finish_enabled=False) if s["name"] == "search_files")
    description = schema["parameters"]["properties"]["path_glob"]["description"]
    assert "zero or more directories" in description
    assert "literal text" in description


def test_empty_search_distinguishes_no_eligible_files_from_no_literal_match(search_gateway):
    no_files = search_gateway.execute(_search("no-files", pattern="absent/**/*.py"))
    no_text = search_gateway.execute(_search("no-text", query="NOT_PRESENT", pattern="**/*.py"))
    for result in (no_files, no_text):
        assert result.status == "succeeded"
        assert result.output["spans"] == []
        assert result.output["evidence_gain"]["marginal_evidence_gain"] is False
    assert no_files.output["searched_file_count"] == 0
    assert no_text.output["searched_file_count"] == 4
    # Regex metacharacters remain literal; path glob semantics do not change queries.
    literal = search_gateway.execute(_search("literal", query="PUBLIC_SEARCH_.*"))
    assert literal.output["spans"] == []
    assert literal.output["searched_file_count"] == 5


def test_search_metadata_and_results_survive_cache_and_gateway_restart(search_gateway, monkeypatch):
    gateway = search_gateway
    first = gateway.execute(_search("first", pattern="pkg/**/*.py"))
    restarted = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits,
    )

    def unexpected_search(*args, **kwargs):
        raise AssertionError("same-diff cached search must not scan again")

    monkeypatch.setattr(restarted, "_search_files", unexpected_search)
    replay = restarted.execute(_search("cached", pattern="pkg/**/*.py"))
    assert replay.evidence_cache_hit is True
    assert replay.output["searched_file_count"] == first.output["searched_file_count"] == 3
    fields = ("path", "start_line", "end_line", "content", "file_hash")
    assert [tuple(s[key] for key in fields) for s in replay.output["spans"]] == [
        tuple(s[key] for key in fields) for s in first.output["spans"]
    ]
    assert replay.output["evidence_gain"]["new_covered_line_count"] == 0
