"""Public task declarations survive preparation and ordinary-run admission."""

from __future__ import annotations

import json
import socket

import httpx
import pytest
from test_caller_source_registration import caller_bundle
from test_dev_segments import configured, records
from test_prepared_probe_dependencies import DependencyProbe
from test_probe_callers import caller_bundle as preparation_bundle  # noqa: F401

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_callers
from patchloop.contracts import PublicTask
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.errors import ContractError, ResumeContractMismatch
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("caller readiness validation must not make network requests")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def with_caller(public, *, requirement="caller-dist==1.2", root="caller"):
    return PublicTask.model_validate({
        **public.model_dump(),
        "caller_requirements": [{"requirement": requirement, "source_root": root}],
    })


def declare_run_task(monkeypatch, request):
    task_dir, package = runner._resolve_task_file(request.task)
    public = with_caller(package.public)
    replacement = package.model_copy(update={
        "public": public, "public_spec_hash": sha256_json(public.model_dump(mode="json")),
        "task_content_hash": sha256_json([package.task_content_hash, public.model_dump()]),
    })
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, replacement))
    return public


def test_undeclared_tasks_keep_original_serialized_identity(smoke_package):
    public = smoke_package.public
    explicit = PublicTask.model_validate({**public.model_dump(), "caller_requirements": []})
    assert public.model_dump_json() == explicit.model_dump_json()
    assert "caller_requirements" not in explicit.model_dump()
    assert probe_callers.task_requirements(public, None) is None
    assert probe_callers.task_source_roots(public, {}) == {}


@pytest.mark.parametrize("requirement,root", [
    ("caller>=1", "caller"), ("caller==1.*", "caller"),
    ("caller==1", "../caller"), ("caller==1", "caller/*"),
    ("caller==1", ".patchloop-hidden/caller"), ("caller==1", "C:/caller"),
])
def test_task_requires_exact_pin_and_literal_public_root(smoke_package, requirement, root):
    with pytest.raises(ValueError):
        with_caller(smoke_package.public, requirement=requirement, root=root)


def test_task_caller_duplicates_are_rejected(smoke_package):
    public = with_caller(smoke_package.public)
    record = {"requirement": "Caller_Dist==2", "source_root": "other"}
    with pytest.raises(ValueError, match="unique"):
        PublicTask.model_validate({**public.model_dump(), "caller_requirements": [
            *public.model_dump()["caller_requirements"], record,
        ]})


def test_current_task_declares_public_issue_version():
    public = load_public_task(
        runner.repository_root() / "tasks/dev-train/current-dev20/13/public.yaml",
    )
    assert "pylint 2.12.2" in public.issue.description
    assert [(c.requirement, c.source_root) for c in public.caller_requirements] == [
        ("pylint==2.12.2", "pylint"),
    ]


def test_preparation_includes_task_pin_without_operator_repeat(preparation_bundle):  # noqa: F811
    request, _, calls = preparation_bundle
    public = with_caller(
        request["public"], requirement="fixture-caller==1.0", root="fixture_caller",
    )
    path = prepared.prepare_dependencies(**{
        **request, "public": public, "caller_requirements": None,
    })
    descriptor = json.loads(path.read_bytes())
    assert probe_callers.from_descriptor(descriptor) == ("fixture-caller==1.0",)
    assert len(calls) == 2
    assert "fixture_caller/__init__.py" in descriptor["files"]


@pytest.mark.parametrize("fault", ["pin", "lock-mode", "source"])
def test_preparation_refuses_conflict_or_unusable_task_scope(preparation_bundle, fault):  # noqa: F811
    request, _, calls = preparation_bundle
    request["public"] = with_caller(
        request["public"], requirement="fixture-caller==1.0",
        root="absent" if fault == "source" else "fixture_caller",
    )
    if fault == "pin":
        request["caller_requirements"] = ["fixture-caller==2.0"]
    elif fault == "lock-mode":
        request.update(resolve=False, wheel_lock=request["output"] / "unused.json")
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**request)
    assert not (request["output"] / prepared.MANIFEST).exists()
    assert len(calls) == (2 if fault == "source" else 0)


@pytest.mark.parametrize("fault", [
    "disabled", "no-bundle", "missing-caller", "wrong-version", "missing-source", "changed-bytes",
    "conflicting-root",
])
def test_unready_task_fails_before_credentials_count_or_dispatch(monkeypatch, tmp_path, fault):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    public = declare_run_task(monkeypatch, request)
    path = caller_bundle(tmp_path, public)
    data = json.loads(path.read_bytes())
    if fault == "missing-caller":
        data["wheel_lock"]["operator_caller_requirements"] = []
    elif fault == "wrong-version":
        data["wheel_lock"]["operator_caller_requirements"] = ["caller-dist==1.3"]
    elif fault == "missing-source":
        data["files"] = {p: h for p, h in data["files"].items() if not p.startswith("caller/")}
        data["content_hash"] = sha256_json(data["files"])
    elif fault == "changed-bytes":
        source = path.parent / "site-packages/caller/lint/expand.py"
        source.write_text("changed", encoding="utf-8")
    path.write_text(canonical_json(data), encoding="utf-8")
    request = request.model_copy(update={
        "enable_probes": fault != "disabled",
        "prepared_probe_dependencies": None if fault in {"disabled", "no-bundle"} else path,
        "caller_source_roots": {"caller-dist": "elsewhere"} if fault == "conflicting-root" else {},
    })
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    credentials = []
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda *a: credentials.append(True))
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED", result
    assert inputs == counted == []
    # Full snapshot byte verification remains in the existing probe preflight.
    if fault != "changed-bytes":
        assert credentials == []


def test_task_scope_is_rendered_when_request_omits_roots_and_resume_is_exact(
    monkeypatch, tmp_path,
):
    class Stop:
        def next_turn(self, context, tools):
            for tool in tools:
                if tool["name"] in {"read_file", "search_files"}:
                    assert tool["parameters"]["properties"]["source_scope"]["enum"] == [
                        "repository", "dependency:caller-dist",
                    ]
            return DevModelTurn(tool_calls=[RequestedTool(
                name="stop_task", action_id="done", arguments={
                    "reason_code": "insufficient_public_evidence", "summary": "Scope validated.",
                }, turn_decision={"mode": "stop", "basis": "End readiness test."},
            )])

    request, inputs, counted, _ = configured(monkeypatch, tmp_path, script=Stop())
    public = declare_run_task(monkeypatch, request)
    path = caller_bundle(tmp_path, public)
    request = request.model_copy(update={
        "enable_probes": True, "prepared_probe_dependencies": path,
    })
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert len(inputs) == len(counted) == 1 and inputs == counted
    assert str(path) not in canonical_json(inputs)
    journal, _ = records(request)
    event = next(e for e in journal.events() if e["event_type"] == "execution_prepared")
    catalog = event["payload"]["registered_dependency_sources"]
    assert [(c["scope"], c["root"], c["version"]) for c in catalog] == [
        ("dependency:caller-dist", "caller", "1.2"),
    ]
    assert "caller_source_roots" not in json.loads(journal.envelope_path.read_bytes())
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"resume_run_id": result["run_id"]})
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 1
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={
            "caller_source_roots": {"caller-dist": "caller"},
        }))
    assert journal.path.read_bytes() == before and len(inputs) == 1
