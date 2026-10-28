"""Registered caller evidence survives compact stages without acquiring edit authority."""

import copy
import json
from types import SimpleNamespace

import pytest
from test_dev_dependency_tools import dependencies as dependencies
from test_dev_dependency_tools import rebuild, source_call
from test_dev_tools import read_calls

from patchloop.dev import diagnosis_context, repair_context, runner
from patchloop.dev.model_state import compact_model_state
from patchloop.util import sha256_bytes


def source(path, content):
    return {"path": path, "file_hash": sha256_bytes(content.encode()),
            "start_line": 1, "end_line": 1, "content": content}


@pytest.mark.parametrize("project", [diagnosis_context.project, repair_context.project])
def test_compact_stage_keeps_caller_and_test_bodies_with_scope_separation(project):
    # The same path and bytes in two scopes must not merge their permissions.
    repository = source("caller/shared.py", "def choose(items): return items")
    dependency = {**repository, "source_scope": "dependency:caller", "read_only": True,
                  "provenance": {"scope": "dependency:caller", "origin": "prepared_dependency",
                                 "manifest_hash": "registered-manifest"}}
    public_test = source("tests/test_behavior.py", "def test_selected(): assert True")
    state = {
        "public_task": {"constraints": {"allowed_paths": ["caller/**", "tests/**"],
                                         "forbidden_paths": []}},
        "workflow_gate": "needs_path_diagnosis",
        "diagnosis_stage": {"path": {"unobserved_changes": [{"path": "implementation.py"}]}},
        "source_spans": [repository, public_test], "dependency_sources": [dependency],
        "observed_source_index": {"entries": [], "omitted_count": 0},
        "latest_tool_results": [],
    }
    original = copy.deepcopy(state)
    # Empty history represents a fresh segment: bodies cannot be replaced by old refs.
    view = compact_model_state(project(state), history=[])
    assert state == original
    assert view["dependency_sources"] == [dependency]
    assert {row["path"] for row in view["current_sources"]} == {
        repository["path"], public_test["path"]}
    for row in view["current_sources"]:
        assert row["edit_permission"] == "allowed"
        assert row["inline_spans"][0]["content"] in {
            repository["content"], public_test["content"]}
    assert "edit_permission" not in view["dependency_sources"][0]
    assert view["dependency_sources"][0]["read_only"] is True


def test_compaction_does_not_create_a_dependency_scope_or_source_body():
    view = compact_model_state({"source_spans": [], "latest_tool_results": []}, history=[])
    assert "dependency_sources" not in view
    assert view["current_sources"] == []


@pytest.mark.parametrize("registered", [False, True])
def test_normal_context_retains_only_already_registered_caller_evidence(
    gateway_factory, dependencies, registered,
):
    gateway = gateway_factory()[0]
    if registered:
        gateway = rebuild(gateway, dependencies[0])
        assert gateway.execute(source_call()).status == "succeeded"
        assert gateway.execute(source_call("large-caller", path="caller/large.py")).status == (
            "succeeded")
    # The caller read is no longer the latest tool result. Retention must survive
    # a fresh segment rather than referring to a discarded native exchange.
    latest = gateway.execute(read_calls()[1])
    assert latest.status == "succeeded"
    context = json.loads(runner._build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=gateway,
        journal=gateway.journal, correction=None, latest_tool_results=[latest],
        counters=runner._RunCounters(), elapsed_seconds=0, limits=gateway.limits,
    ))
    if not registered:
        assert "dependency_sources" not in context
        return
    expected = gateway.dependency_context_spans()
    assert expected and context["dependency_sources"] == expected
    assert sum(len(span["content"]) for span in expected) <= gateway.retained_source_chars
    assert all(span["read_only"] and span["source_scope"] == "dependency:caller"
               for span in expected)
    context.update(workflow_gate="needs_path_diagnosis", diagnosis_stage={
        "path": {"unobserved_changes": [{"path": "parser.py"}]}})
    fresh = compact_model_state(diagnosis_context.project(context), history=[])
    returned = compact_model_state(repair_context.project(context), history=[])
    assert fresh["dependency_sources"] == returned["dependency_sources"] == expected
