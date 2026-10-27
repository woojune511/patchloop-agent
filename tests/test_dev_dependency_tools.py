"""Opt-in caller source reads never become workspace mutation evidence."""

from __future__ import annotations

import json

import pytest
from test_dev_tools import mutation_call, read_calls

from diagnostics.repair_cycle_context import build_handoff
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.dependency_sources import DependencySources
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError, RecoveryError
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.probe_runtime import runtime
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def dependencies(tmp_path):
    contents = {
        "caller/__init__.py": "raise RuntimeError('source must never be imported')\n",
        "caller/lint/expand.py": "def expand(items):\n    return list(items)\n",
        "caller/large.py": "".join(f"# {i:04d} {'x' * 94}\n" for i in range(600)),
        "caller/matches.py": "".join(f"needle_{i} = {i}\n" for i in range(25)),
        "foreign/secret.py": "SECRET = 1\n",
    }
    directory = tmp_path / "site-packages"
    for relative, content in contents.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode())
    python, image = runtime("python312-v1")
    files = {path: sha256_bytes(text.encode()) for path, text in contents.items()}
    descriptor = {
        "schema_version": "prepared-probe-dependencies-v1",
        "repository_url": "https://example.invalid/project.git", "base_commit": "a" * 40,
        "python": python, "image": image, "platform": "linux/amd64", "source_roots": [],
        "files": files, "content_hash": sha256_json(files),
        "wheel_lock": {"operator_caller_requirements": ["caller==1.2"],
                       "source_metadata": {"project_name": "project"}},
    }
    path = tmp_path / "prepared-probe-dependencies.json"
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    prepared = PreparedDependencies(
        path, read_descriptor(path)[1], descriptor["repository_url"], descriptor["base_commit"],
        callers=("caller==1.2",),
    )
    return DependencySources(prepared, {"caller": "caller"}), directory


def rebuild(gateway, sources):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
        dependency_sources=sources,
    )


def source_call(action_id="dependency-read", *, tool="read_file", **overrides):
    arguments = ({"path": "caller/lint/expand.py", "start_line": None, "end_line": None}
                 if tool == "read_file" else {"query": "def expand", "path_glob": "caller/**"})
    arguments.update({"source_scope": "dependency:caller", **overrides})
    return RequestedTool(
        name=tool, action_id=action_id, arguments=arguments,
        turn_decision=PublicTurnDecision(mode="inspect", basis="Inspect registered caller source.",
                                         evidence_goal="Locate public caller behavior."),
    )


def test_schemas_are_opt_in_and_scoped_validation_preserves_repository_defaults(dependencies):
    sources, _ = dependencies
    legacy = dev_tool_schemas(finish_enabled=False)
    assert legacy == dev_tool_schemas(finish_enabled=False, dependency_sources=None)
    enabled = dev_tool_schemas(finish_enabled=False, dependency_sources=sources.catalog(),
                               read_paths=["only-repository.py"])
    for old in legacy:
        assert "source_scope" not in old["parameters"]["properties"]
    for schema in enabled:
        if schema["name"] in {"read_file", "search_files"}:
            params = schema["parameters"]
            assert params["properties"]["source_scope"]["enum"] == [
                "repository", "dependency:caller"]
            assert "source_scope" in params["required"]
            assert "pylint" not in schema["description"]
    assert validate_tool_batch([source_call()], allowed_read_paths=["only-repository.py"])
    repository = source_call(source_scope="repository")
    with pytest.raises(ContractError, match="targeted repair"):
        validate_tool_batch([repository], allowed_read_paths=["only-repository.py"])
    for scope in (None, 4, "other", "dependency:../caller"):
        with pytest.raises(ContractError, match="source_scope"):
            validate_tool_batch([source_call(source_scope=scope)])


def test_registered_read_search_are_bounded_and_do_not_grant_workspace_evidence(
    gateway_factory, dependencies,
):
    sources, _ = dependencies
    gateway = rebuild(gateway_factory()[0], sources)
    before = gateway.evidence_ledger()
    read = gateway.execute(source_call())
    assert read.status == "succeeded", read.message
    assert read.output["dependency_spans"][0]["content"] == (
        "def expand(items):\n    return list(items)")
    assert read.output["provenance"]["version"] == "1.2"
    assert "spans" not in read.output and gateway.spans == {}
    assert gateway.context_spans() == [] and gateway.evidence_ledger() == before
    search = gateway.execute(source_call("search", tool="search_files"))
    assert search.status == "succeeded", search.message
    assert search.output["searched_file_count"] == 4
    assert len(search.output["dependency_spans"]) == 1
    assert gateway.evidence_ledger() == before
    assert all(span["read_only"] for span in gateway.dependency_context_spans())
    assert not gateway._read_cache
    start = next(e for e in gateway.journal.events() if e["event_type"] == "action_started")
    assert start["payload"]["dependency_source_identity"] == sources.identity


def test_dependency_paging_search_limits_and_retained_context(gateway_factory, dependencies):
    gateway = rebuild(gateway_factory()[0], dependencies[0])
    page = gateway.execute(source_call(path="caller/large.py"))
    assert page.status == "succeeded", page.message
    output = page.output
    assert output["truncated"] and output["line_count"] == 600
    span = output["dependency_spans"][0]
    assert len(span["content"]) <= 24_000 and span["end_line"] < 600
    next_page = gateway.execute(source_call(
        "page-2", path="caller/large.py", start_line=output["next_start_line"], end_line=None))
    assert next_page.status == "succeeded"
    assert next_page.output["start_line"] == span["end_line"] + 1
    retained = gateway.dependency_context_spans()
    assert sum(len(item["content"]) for item in retained) <= 24_000
    assert retained[0]["start_line"] == next_page.output["start_line"]
    search = gateway.execute(source_call("many", tool="search_files", query="needle_"))
    assert search.status == "succeeded"
    assert len(search.output["dependency_spans"]) == 20 and search.output["truncated"]
    assert sum(len(item["content"]) for item in search.output["dependency_spans"]) <= 24_000
    rejected = gateway.execute(source_call("too-wide", start_line=1, end_line=401))
    assert rejected.status == "failed" and "400" in rejected.message


def test_repository_zero_file_search_hint_is_only_enabled_for_registered_sources(
    gateway_factory, dependencies,
):
    gateway = gateway_factory()[0]
    missing = source_call(tool="search_files", source_scope="repository", path_glob="caller/**")
    legacy = gateway.execute(missing)
    assert "available_sources" not in legacy.output and "source_scope" not in legacy.output
    enabled = rebuild(gateway, dependencies[0])
    missing = missing.model_copy(update={"action_id": "enabled-search"})
    result = enabled.execute(missing)
    assert result.status == "succeeded"
    assert result.output["searched_file_count"] == 0
    assert result.output["source_scope"] == "repository"
    assert result.output["available_sources"] == dependencies[0].catalog()


def test_dependency_access_is_read_only_and_requires_registered_scope(
    gateway_factory, dependencies,
):
    gateway = rebuild(gateway_factory()[0], dependencies[0])
    for index, arguments in enumerate((
        {"path": "../outside.py"}, {"path": "foreign/secret.py"},
        {"source_scope": "dependency:foreign"},
    )):
        result = gateway.execute(source_call(f"invalid-{index}", **arguments))
        assert result.status == "failed"
    mutation = mutation_call(gateway)
    mutation.arguments["source_scope"] = "dependency:caller"
    with pytest.raises(ContractError, match="only for read_file"):
        validate_tool_batch([mutation])
    with pytest.raises(ContractError, match="only for read_file"):
        gateway.execute(mutation)
    disabled = gateway_factory()[0].execute(source_call())
    assert disabled.status == "failed" and "not enabled" in disabled.message


def test_replay_hydration_and_handoff_retain_dependency_after_workspace_edit(
    gateway_factory, dependencies,
):
    sources, _ = dependencies
    gateway = rebuild(gateway_factory()[0], sources)
    call = source_call()
    first = gateway.execute(call)
    count = len(gateway.journal.events())
    replay = gateway.execute(call)
    assert replay.replayed and replay.output == first.output
    assert replay.input_hash == first.input_hash
    assert len(gateway.journal.events()) == count
    expected = gateway.dependency_context_spans()
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    assert gateway.dependency_context_spans() == expected
    resumed = rebuild(gateway, sources)
    assert resumed.dependency_context_spans() == expected
    assert all(not span["path"].startswith("caller/") for span in resumed.context_spans())
    result = build_handoff(
        resumed, history=[], latest_original={"candidate_diff_hash": resumed.current_diff_hash,
                                               "status": "test-fixture"},
        correction=None, parent_request={"input": []}, counters={"tool_actions": 4},
    )
    assert result["state"]["dependency_sources"] == expected
    assert result["state"]["current_sources"] == resumed.context_spans()
    assert result["state"]["counters"]["tool_actions"] == 4


def test_tampered_dependency_cannot_be_replayed_retained_or_hydrated(gateway_factory, dependencies):
    sources, directory = dependencies
    gateway = rebuild(gateway_factory()[0], sources)
    call = source_call()
    assert gateway.execute(call).status == "succeeded"
    (directory / "caller/lint/expand.py").write_text("# altered\n", encoding="utf-8")
    for operation in (lambda: gateway.execute(call), gateway.dependency_context_spans,
                      lambda: rebuild(gateway, sources)):
        with pytest.raises(RecoveryError):
            operation()
    # A new action must also perform the backend hash check; no source cache can hide it.
    assert gateway.execute(source_call("new-read")).status == "failed"


def test_missing_or_changed_registry_cannot_reuse_saved_dependency_evidence(
    gateway_factory, dependencies,
):
    sources, _ = dependencies
    gateway = rebuild(gateway_factory()[0], sources)
    assert gateway.execute(source_call()).status == "succeeded"
    with pytest.raises((ContractError, RecoveryError)):
        rebuild(gateway, None)
    sources.identity = "sha256:" + "0" * 64
    with pytest.raises(RecoveryError, match="identity changed"):
        gateway.execute(source_call())
    with pytest.raises(RecoveryError):
        rebuild(gateway, sources)
