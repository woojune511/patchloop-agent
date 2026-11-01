from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import patchloop.dev.tools as tools
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.source_glob import matches_source_glob
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.git_execution import GitExecutionUncertain


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
            additive_test_roots=[],
            allowed_paths=["pkg/direct.py"], forbidden_paths=[],
            max_changed_files=1, max_diff_lines=50,
        ),
        visible_checks=[], test_suites=[],
        model_dump=lambda **kwargs: {"task_id": "public-search-test"},
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


def test_search_enumerates_tracking_once_for_many_files(search_gateway, monkeypatch):
    gateway = search_gateway
    for number in range(64):
        (gateway.workspace / f"extra{number:03}.py").write_text("ordinary source\n")
    subprocess.run(["git", "add", "--", "extra*.py"], cwd=gateway.workspace, check=True)
    calls = []
    original = tools.run_git

    def counted(workspace, *args, **kwargs):
        calls.append(args)
        return original(workspace, *args, **kwargs)

    monkeypatch.setattr(tools, "run_git", counted)
    result = gateway._search_files("not present")
    assert result["searched_file_count"] == 69
    assert result["spans"] == []
    assert calls == [("ls-files", "-z")]


def test_search_refreshes_index_and_current_content_with_unusual_names(search_gateway):
    gateway = search_gateway
    name = "space 한글[1].py"
    target = gateway.workspace / name
    target.write_text("fresh marker\n", encoding="utf-8")
    assert gateway._search_files("fresh marker")["spans"] == []
    subprocess.run(["git", "add", "--", name], cwd=gateway.workspace, check=True)
    first = gateway._search_files("fresh marker")["spans"]
    assert [s["path"] for s in first] == [name]
    target.write_text("changed marker\n", encoding="utf-8")
    assert gateway._search_files("fresh marker")["spans"] == []
    assert gateway._search_files("changed marker")["spans"][0]["file_hash"] != first[0]["file_hash"]
    subprocess.run(["git", "rm", "--cached", "--force", "--", name], cwd=gateway.workspace,
                   check=True, capture_output=True)
    assert gateway._search_files("changed marker")["spans"] == []


def test_search_keeps_size_and_symlink_boundaries(search_gateway):
    gateway = search_gateway
    (gateway.workspace / "huge.py").write_bytes(b"PUBLIC_SEARCH_MARKER" + b"x" * 1_000_001)
    subprocess.run(["git", "add", "--", "huge.py"], cwd=gateway.workspace, check=True)
    assert gateway._search_files("PUBLIC_SEARCH_MARKER")["searched_file_count"] == 5
    link = gateway.workspace / "link.py"
    try:
        link.symlink_to(gateway.workspace / "root.py")
    except OSError:
        pytest.skip("host does not permit symlink creation")
    subprocess.run(["git", "add", "--", "link.py"], cwd=gateway.workspace, check=True)
    result = gateway._search_files("PUBLIC_SEARCH_MARKER")
    assert result["searched_file_count"] == 5
    assert all(s["path"] != "link.py" for s in result["spans"])


def test_expired_search_launches_no_git(search_gateway, monkeypatch):
    gateway = search_gateway
    gateway.deadline = ExecutionDeadline.from_remaining(0)

    def forbidden(*args, **kwargs):
        raise AssertionError("expired search cannot launch Git")

    monkeypatch.setattr("patchloop.git_execution.subprocess.Popen", forbidden)
    with pytest.raises(ExecutionDeadlineExceeded):
        gateway._search_files("marker")


def test_search_scan_deadline_stops_without_another_git(search_gateway, monkeypatch):
    gateway = search_gateway
    now = [0.0]
    deadline = ExecutionDeadline.from_remaining(1, clock=lambda: now[0])
    gateway.deadline = deadline
    calls = []

    def enumerated(workspace, *args, **kwargs):
        assert kwargs["deadline"] is deadline
        calls.append(args)
        now[0] = 2.0
        return SimpleNamespace(stdout=b"root.py\0")

    monkeypatch.setattr(tools, "run_git", enumerated)
    with pytest.raises(ExecutionDeadlineExceeded):
        gateway._search_files("marker")
    assert calls == [("ls-files", "-z")]


def test_search_preserves_git_cleanup_uncertainty(search_gateway, monkeypatch):
    uncertain = GitExecutionUncertain(
        "unconfirmed cleanup", details={"descendant_cleanup": "unknown"},
    )

    def failed(*args, **kwargs):
        raise uncertain

    monkeypatch.setattr(tools, "run_git", failed)
    with pytest.raises(GitExecutionUncertain) as captured:
        search_gateway._search_files("marker")
    assert captured.value is uncertain


def test_source_validation_batches_tracking_but_refreshes_index_and_bytes(
    search_gateway, monkeypatch,
):
    gateway = search_gateway
    observed = gateway._search_files("PUBLIC_SEARCH_MARKER")["spans"]
    gateway.spans = {span["span_id"]: span for span in observed}
    calls = []
    original = tools.run_git

    def counted(workspace, *args, **kwargs):
        calls.append(args)
        return original(workspace, *args, **kwargs)

    monkeypatch.setattr(tools, "run_git", counted)
    assert gateway._validated_source_spans() == observed
    assert calls == [("ls-files", "-z")]

    (gateway.workspace / "root.py").write_text("changed source\n", encoding="utf-8")
    subprocess.run(["git", "rm", "--cached", "--", "notes.txt"], cwd=gateway.workspace,
                   check=True, capture_output=True)
    (gateway.workspace / "added.py").write_text("PUBLIC_SEARCH_MARKER\n", encoding="utf-8")
    subprocess.run(["git", "add", "-N", "--", "added.py"], cwd=gateway.workspace, check=True)
    new_span = gateway._read_file("added.py", 1, 1)["spans"][0]
    gateway.spans[new_span["span_id"]] = new_span
    calls.clear()
    assert {s["path"] for s in gateway._validated_source_spans()} == {
        "pkg/direct.py", "pkg/deep/nested.py", "pkg/deep/deeper/leaf.py", "added.py",
    }
    assert calls == [("ls-files", "-z")]


def test_source_validation_deadline_after_inventory_stops_before_read(search_gateway, monkeypatch):
    gateway = search_gateway
    observed = gateway._search_files("PUBLIC_SEARCH_MARKER")["spans"]
    gateway.spans = {span["span_id"]: span for span in observed}
    now = [0.0]
    gateway.deadline = ExecutionDeadline.from_remaining(1, clock=lambda: now[0])

    def enumerated():
        now[0] = 2.0
        return {span["path"] for span in observed}

    def unexpected_read(*args, **kwargs):
        raise AssertionError("expired source validation cannot read file bytes")

    monkeypatch.setattr(gateway, "_tracked_paths", enumerated)
    monkeypatch.setattr(Path, "read_bytes", unexpected_read)
    with pytest.raises(ExecutionDeadlineExceeded):
        gateway._validated_source_spans()


def test_inventory_tracking_honors_explicit_deadline_override(search_gateway):
    gateway = search_gateway
    gateway.deadline = ExecutionDeadline.from_remaining(0)
    valid = ExecutionDeadline.from_remaining(10)
    assert gateway._tracked_path(
        "root.py", tracked_paths={"root.py"}, deadline=valid,
    )[0] == "root.py"
    gateway.deadline = valid
    with pytest.raises(ExecutionDeadlineExceeded):
        gateway._tracked_path(
            "root.py", tracked_paths={"root.py"}, deadline=ExecutionDeadline.from_remaining(0),
        )


def test_search_uses_index_without_tree_walk_and_preserves_path_order(search_gateway, monkeypatch):
    gateway = search_gateway
    names = [f"case{letter}{number:02}.py" for letter in ("Z", "a") for number in range(13)]
    for name in names:
        (gateway.workspace / name).write_text("ORDER_MARKER\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", *names], cwd=gateway.workspace, check=True)

    def unexpected_walk(*args, **kwargs):
        raise AssertionError("search must not enumerate untracked/Git directories")

    monkeypatch.setattr(Path, "rglob", unexpected_walk)
    result = gateway._search_files("ORDER_MARKER", "case*.py")
    assert [s["path"] for s in result["spans"]] == sorted(names, key=Path)[:20]
    assert result["truncated"] is True


@pytest.mark.parametrize("link_kind", ["is_symlink", "is_junction"])
def test_index_search_does_not_follow_linked_directory(search_gateway, monkeypatch, link_kind):
    gateway = search_gateway
    linked = gateway.workspace / "pkg" / "deep"
    original = getattr(Path, link_kind)
    monkeypatch.setattr(Path, link_kind, lambda path: path == linked or original(path))
    result = gateway._search_files("PUBLIC_SEARCH_MARKER", "pkg/**/*.py")
    assert [s["path"] for s in result["spans"]] == ["pkg/direct.py"]
