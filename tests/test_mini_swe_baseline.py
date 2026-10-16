"""Public-only input, pre-dispatch accounting and isolated action boundaries."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from diagnostics import mini_swe_dev20 as panel
from diagnostics import mini_swe_runtime as runtime
from patchloop.deadline import ExecutionDeadline
from patchloop.runtime import repository_root
from patchloop.task_loader import load_public_task


class Flow(Exception):
    def __init__(self, message):
        self.messages = [message]


class FormatFailure(Flow):
    pass


@pytest.fixture
def mini_protocol(monkeypatch):
    """Protocol stand-ins: core safety tests require neither network nor upstream install."""

    def parse(items, **kwargs):
        if not items:
            raise FormatFailure({"extra": {}})
        return [{"command": "true", "tool_call_id": "call_1"}]

    modules = {
        "minisweagent.exceptions": SimpleNamespace(
            LimitsExceeded=Flow, Submitted=Flow, FormatError=FormatFailure
        ),
        "minisweagent.models.utils.actions_toolcall_response": SimpleNamespace(
            BASH_TOOL_RESPONSE_API={"type": "function", "name": "bash"},
            finish_reason_from_responses_api=lambda r: r.status,
            parse_toolcall_actions_response=parse,
        ),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


def response(*, count=100, usage=True, output=True):
    fields = {
        "model": runtime.MODEL,
        "service_tier": "default",
        "object": "response",
        "status": "completed",
        "output": [{"type": "function_call"}] if output else [],
        "usage": {
            "input_tokens": count,
            "output_tokens": 200,
            "input_tokens_details": {"cached_tokens": 20},
        }
        if usage
        else None,
    }
    return SimpleNamespace(**fields, model_dump=lambda **kw: copy.deepcopy(fields))


def model(tmp_path, reply=None):
    client = SimpleNamespace(
        max_retries=0,
        responses=SimpleNamespace(
            input_tokens=SimpleNamespace(
                count=Mock(return_value=SimpleNamespace(input_tokens=100))
            ),
            create=Mock(return_value=reply or response()),
        ),
    )
    return runtime.CountedModel(
        client,
        {"format_error_template": "{{ error }}"},
        tmp_path,
        ExecutionDeadline.from_remaining(60),
    )


def test_count_exact_input_before_dispatch_and_settle(mini_protocol, tmp_path):
    adapter = model(tmp_path)
    events = []
    adapter.client.responses.input_tokens.count.side_effect = lambda **kw: (
        events.append(("count", kw)) or SimpleNamespace(input_tokens=100)
    )
    adapter.client.responses.create.side_effect = lambda **kw: (
        events.append(("create", kw)) or response()
    )
    output = adapter.query([{"role": "user", "content": "public task", "extra": {"local": 1}}])
    assert [x[0] for x in events] == ["count", "create"]
    assert events[0][1]["input"] == events[1][1]["input"]
    assert "extra" not in events[0][1]["input"][0]
    assert events[1][1]["max_output_tokens"] == 25000
    assert events[1][1]["store"] is False
    assert events[1][1]["include"] == ["reasoning.encrypted_content"]
    assert adapter.ledger.spent_nanos == 961500
    assert output["extra"]["cost"] == 0.0009615
    assert adapter.calls == 1


def test_insufficient_budget_never_dispatches(mini_protocol, tmp_path):
    adapter = model(tmp_path)
    adapter.ledger.spent_nanos = adapter.ledger.cap_nanos - 10
    with pytest.raises(Flow):
        adapter.query([])
    adapter.client.responses.create.assert_not_called()
    assert adapter.calls == 0


@pytest.mark.parametrize("where", ["count", "transport", "missing_usage", "mismatch"])
def test_uncertainty_prevents_any_further_provider_work(mini_protocol, tmp_path, where):
    adapter = model(tmp_path)
    if where == "count":
        adapter.client.responses.input_tokens.count.side_effect = TimeoutError()
    elif where == "transport":
        adapter.client.responses.create.side_effect = TimeoutError()
    else:
        adapter.client.responses.create.return_value = response(
            usage=where != "missing_usage", count=101 if where == "mismatch" else 100
        )
    with pytest.raises(runtime.OperationalStop):
        adapter.query([])
    with pytest.raises(runtime.OperationalStop):
        adapter.query([])
    assert adapter.uncertain
    assert adapter.client.responses.input_tokens.count.call_count == 1
    assert adapter.client.responses.create.call_count == (0 if where == "count" else 1)


def test_format_error_keeps_billed_usage(mini_protocol, tmp_path):
    adapter = model(tmp_path, response(output=False))
    with pytest.raises(FormatFailure) as caught:
        adapter.query([])
    assert adapter.calls == 1 and adapter.ledger.spent_nanos == 961500
    assert caught.value.messages[0]["extra"]["cost"] > 0
    assert not adapter.uncertain


def test_failure_to_persist_response_is_uncertain(mini_protocol, tmp_path):
    adapter = model(tmp_path)
    adapter.client.responses.create.return_value.model_dump = Mock(side_effect=OSError())
    with pytest.raises(OSError):
        adapter.query([])
    assert adapter.uncertain and adapter.calls == 1
    with pytest.raises(runtime.OperationalStop):
        adapter.query([])
    assert adapter.client.responses.create.call_count == 1


def test_call_limit_stops_before_counting(mini_protocol, tmp_path):
    adapter = model(tmp_path)
    adapter.calls = 40
    with pytest.raises(Flow):
        adapter.query([])
    adapter.client.responses.input_tokens.count.assert_not_called()


def test_replay_keeps_reasoning_and_tool_outputs():
    encrypted = {"type": "reasoning", "encrypted_content": "opaque"}
    tool = {"type": "function_call", "call_id": "one", "extra": "local"}
    observation = {"type": "function_call_output", "call_id": "one", "output": "result"}
    assert runtime.flatten_messages(
        [
            {"object": "response", "output": [encrypted, tool]},
            observation,
        ]
    ) == [encrypted, {"type": "function_call", "call_id": "one"}, observation]


def test_public_projection_contains_issue_and_scope_only():
    public = load_public_task(repository_root() / "tasks/dev-train/current-dev20/1/public.yaml")
    text = panel.task_text(public)
    assert public.issue.description in text
    assert "allowed_paths" in text and "visible_checks" in text
    for forbidden in ("native_row", "test_patch", "reference.patch", "private.yaml", "oracle.json"):
        assert forbidden not in text


@pytest.mark.parametrize("missing", [False, True])
def test_metadata_setup_supports_older_image_python(monkeypatch, missing):
    class DistributionNotFound(Exception):
        pass

    def distribution(name):
        assert name == "pydicom"
        if missing:
            raise DistributionNotFound()

    monkeypatch.setitem(sys.modules, "importlib.metadata", None)
    monkeypatch.setitem(
        sys.modules,
        "pkg_resources",
        SimpleNamespace(get_distribution=distribution, DistributionNotFound=DistributionNotFound),
    )
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    exec(runtime.metadata_setup("pydicom"), {})
    if missing:
        run.assert_called_once_with([sys.executable, "setup.py", "egg_info"], check=True)
    else:
        run.assert_not_called()


def test_container_has_no_host_mount_and_cleans_exact_identity(monkeypatch, tmp_path):
    calls = []
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"public archive")

    def fake(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout=b"", stderr=b"", returncode=0)

    monkeypatch.setattr(runtime, "command", fake)
    env = runtime.PublicContainer(
        {
            "image": "image@sha256:" + "a" * 64,
            "source_archive": str(archive),
            "public_module": "example",
        },
        tmp_path,
        ExecutionDeadline.from_remaining(60),
    )
    launch = calls[0]
    assert "--pull=never" in launch and "--network=none" in launch
    assert "--read-only" in launch and "--cap-drop=ALL" in launch
    assert "--volume" not in launch and "--mount" not in launch
    assert any(str(x).startswith("/testbed:rw,") for x in launch)
    assert "git init" in calls[2][-1] and "git commit" in calls[2][-1]
    env.cleanup()
    env.cleanup()
    assert [c for c in calls if c[:3] == ["docker", "rm", "-f"]] == [
        ["docker", "rm", "-f", env.name]
    ]


def test_commands_do_not_inherit_provider_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET_SENTINEL")
    run = Mock(return_value=SimpleNamespace(stdout=b""))
    monkeypatch.setattr(subprocess, "run", run)
    runtime.command(["docker", "version"])
    assert "OPENAI_API_KEY" not in run.call_args.kwargs["env"]
    assert "SECRET_SENTINEL" not in json.dumps(run.call_args.kwargs["env"])


def test_cleanup_uncertainty_is_not_success(monkeypatch, tmp_path):
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"public archive")
    monkeypatch.setattr(runtime, "command", Mock(return_value=SimpleNamespace(stdout=b"")))
    env = runtime.PublicContainer(
        {"image": "image", "source_archive": str(archive), "public_module": "example"},
        tmp_path,
        ExecutionDeadline.from_remaining(60),
    )
    monkeypatch.setattr(runtime, "command", Mock(return_value=SimpleNamespace(stdout=b"exists")))
    with pytest.raises(runtime.OperationalStop):
        env.cleanup()
    assert not env.closed


def test_shell_timeout_cannot_continue(mini_protocol, monkeypatch, tmp_path):
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"public archive")
    monkeypatch.setattr(runtime, "command", Mock(return_value=SimpleNamespace(stdout=b"")))
    env = runtime.PublicContainer(
        {"image": "image", "source_archive": str(archive), "public_module": "example"},
        tmp_path,
        ExecutionDeadline.from_remaining(60),
    )
    monkeypatch.setattr(
        env,
        "operator_command",
        Mock(side_effect=subprocess.CalledProcessError(124, ["timeout"], output=b"partial")),
    )
    with pytest.raises(runtime.OperationalStop):
        env.execute({"command": "sleep 1000"})
    assert env.actions == 1
    env.cleanup()
