"""Public output-boundary regression; no task code or provider execution."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_feedback_integration_v18 import _completed_batch, _input, _outputs

from patchloop.dev.check_feedback import check_failure_diagnostics, output_tail
from patchloop.dev.contracts import (
    DEV_RUN_SCHEMA,
    DevLimits,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.runner import _build_context, _recent_checks, _RunCounters
from patchloop.dev.tools import DevToolGateway
from patchloop.sandbox.runner import SandboxResult, _bounded_text
from patchloop.util import canonical_json, sha256_json

# Abridged public B1 stdout from pl39-rollout-live-a, action
# call_utu0r6Cp3atCknHFZh265PNf; the source signature was cut to "turn:".
# Failure signature:
# sha256:772a5804333453461737ffbff5589954fd6edf70398709c11e46a01a59aa7d03
# Only public terminal lines are retained, not task/private source or reasoning.
PUBLIC_SUMMARY = (
    "=========================== short test summary info ============================\n"
    "FAILED pyfakefs/tests/fake_os_test.py::FakeOsModuleTest::"
    "test_makedirs_raises_if_parent_is_looping_link - AssertionError: 17 != 40\n"
    "FAILED pyfakefs/tests/fake_os_test.py::FakeOsModuleTest::"
    "test_mkdir_broken_link_with_trailing_sep_linux_windows - AssertionError: 17 != 2\n"
    "2 failed, 515 passed, 570 skipped in 6.44s\n"
)
CAPTURED_TAIL = "turn:\n        source excerpt\nE   AssertionError: 17 != 2\n" + PUBLIC_SUMMARY


class OutputSandbox:
    official = False

    def __init__(self, stdout: str, stderr: str = "", *, truncated: bool = False):
        self.calls = 0
        self.result = SandboxResult(
            command=["public-check"], exit_code=1, stdout=stdout, stderr=stderr,
            timed_out=False, truncated=truncated, duration_ms=1,
            original_output_bytes=len((stdout + stderr).encode("utf-8")),
        )

    def run_check(self, workspace, check):
        del workspace, check
        self.calls += 1
        return self.result


def test_captured_source_fragment_is_not_an_exception():
    assert DevToolGateway._exception_type(CAPTURED_TAIL, "") == "AssertionError"


def test_gateway_clipping_is_line_aligned_and_reported(gateway_factory):
    # The old 12k tail starts inside a source line, exactly at "turn:".
    suffix = CAPTURED_TAIL + "padding\n" * ((12_000 - len(CAPTURED_TAIL)) // 8)
    suffix += "\n" * (12_000 - len(suffix))
    stdout = "public prefix\n    def raise_os_error() -> NoRe" + suffix
    assert stdout[-12_000:].startswith("turn:")
    gateway, _, _ = gateway_factory(sandbox=OutputSandbox(stdout))
    result = gateway.execute(RequestedTool(
        name="run_check", action_id="clipped-check",
        arguments={"check_id": gateway.public_task.visible_checks[0].id},
    ))
    assert result.output["truncated"] is True
    assert not result.output["stdout"].startswith("turn:")
    assert len(result.output["stdout"]) <= 12_000
    assert result.output["public_check_failure"]["exception_type"] == "AssertionError"
    assert "AssertionError: 17 != 40" in result.output["stdout"]


def test_sandbox_byte_clip_does_not_publish_partial_line():
    stdout, stderr, clipped, original = _bounded_text(b"ok\r\npartial", b"", 7)
    assert (stdout, stderr, clipped, original) == ("ok\r\n", "", True, 11)


@pytest.mark.parametrize("text,limit,expected,clipped", [
    ("", 0, "", False),
    ("one", 0, "", True),
    ("one", 3, "one", False),
    ("one", 2, "", True),
    ("old\nnew", 3, "new", True),
    ("old\nnew", 4, "new", True),
    ("old\r\nnew\r\n", 6, "new\r\n", True),
    ("old\r\nnew\r\n", 7, "new\r\n", True),
    ("old\n새 줄\n", 4, "새 줄\n", True),
    ("old\n새 줄\n", 3, "", True),
    ("old\n" + "long" * 20, 12, "", True),
])
def test_character_tail_preserves_whole_observed_lines(text, limit, expected, clipped):
    assert output_tail(text, limit) == (expected, clipped)


@pytest.mark.parametrize("stdout,stderr,cap,expected_stdout,expected_stderr", [
    (b"", b"", 0, "", ""),
    (b"a", b"b", 2, "a", "b"),
    (b"ok\npartial", b"lost\n", 4, "ok\n", ""),
    (b"ok\n", b"err\r\ncut", 9, "ok\n", "err\r\n"),
    (b"ok\r\n", b"", 3, "", ""),
    ("한글\n끝".encode(), b"", 7, "한글\n", ""),
    ("한글\n끝".encode(), b"", 8, "한글\n", ""),
    ("한글\n끝".encode(), b"", 2, "", ""),
])
def test_byte_prefix_preserves_crlf_unicode_and_allocation(
    stdout, stderr, cap, expected_stdout, expected_stderr,
):
    actual = _bounded_text(stdout, stderr, cap)
    assert actual == (
        expected_stdout, expected_stderr, len(stdout) + len(stderr) > cap,
        len(stdout) + len(stderr),
    )
    assert len((actual[0] + actual[1]).encode()) <= cap


@pytest.mark.parametrize("stdout,stderr,expected", [
    ("turn:\nNoReturn:\nPASS\n", "", None),
    ("ValueError: ordinary unframed log\n", "", None),
    ("E   assert False\nE   None\n", "", None),
    ("FAILED public.py::case - turn\n", "", None),
    ("E   Broken.: message\n", "", None),
    ("FAILED public.py::case - package..BrokenError: message\n", "", None),
    ("", '  File "public.py", line 1\npackage..BrokenError: message\n', None),
    ("Traceback (most recent call last):\nValueError\n", "", None),
    ("", 'Traceback (most recent call last):\n  File "public.py", line 1\n'
     '    fail()\napp.CustomFault: message\nextra note\n', "app.CustomFault"),
    ("", '  File "public.py", line 2\n    bad(\n       ^\nSyntaxError: bad syntax\n',
     "SyntaxError"),
    ("", 'Traceback (most recent call last):\n  File "public.py", line 1\n'
     'ValueError: cause\n\nDuring handling of the above exception, another exception '
     'occurred:\n\nTraceback (most recent call last):\n  File "public.py", line 2\n'
     'TypeError: terminal\n', "TypeError"),
    ("E   AssertionError\n", "", "AssertionError"),
    ("E   AppFault: custom failure\n", "", "AppFault"),
    ("E   FileNotFoundError: intermediate\n" + PUBLIC_SUMMARY, "", "AssertionError"),
    ("FAILED public.py::one - ValueError: one\n"
     "FAILED public.py::two - TypeError: two\n", "", None),
    ("FAILED public.py::one - ValueError: one\nERROR public.py::two\n", "", None),
])
def test_only_recognized_terminal_formats_provide_exception_type(stdout, stderr, expected):
    assert DevToolGateway._exception_type(stdout, stderr) == expected


def test_literal_failure_summary_bounds_and_comparison_text():
    exception, summary = check_failure_diagnostics(CAPTURED_TAIL, "")
    assert exception == "AssertionError"
    assert summary == {
        "lines": [line for line in PUBLIC_SUMMARY.splitlines() if line.startswith("FAILED ")],
        "observed_count": 2, "truncated": False,
    }
    many = "\n".join(f"FAILED public.py::case{i} - ValueError: {i}" for i in range(12))
    many += "\nFAILED public.py::long - ValueError: " + "x" * 4_001
    exception, summary = check_failure_diagnostics(many, "")
    assert exception == "ValueError"
    assert len(summary["lines"]) == 8 and summary["observed_count"] == 13
    assert sum(map(len, summary["lines"])) <= 4_000 and summary["truncated"] is True


def test_diagnostics_precede_delivery_clipping_and_survive_native_restart(
    gateway_factory, monkeypatch,
):
    stdout = PUBLIC_SUMMARY + "public log line\n" * 1_000
    sandbox = OutputSandbox(stdout)
    gateway, journal, workspace = gateway_factory(sandbox=sandbox)
    call = RequestedTool(
        name="run_check", action_id="public-error",
        arguments={"check_id": gateway.public_task.visible_checks[0].id},
        turn_decision=PublicTurnDecision(mode="verify", basis="Observe the public check result."),
    )
    _, results = _completed_batch(gateway, [call], "check-turn")
    result = results[0]
    assert "FAILED" not in result.output["stdout"]
    focus = result.output["public_check_failure"]
    assert focus["exception_type"] == "AssertionError"
    assert focus["failure_summary"]["observed_count"] == 2
    assert result.output["failure_signature"] == sha256_json({
        "check_id": call.arguments["check_id"], "exit_code": 1, "timed_out": False,
        "stdout": stdout[-8_000:], "stderr": "",
    })
    items = _input(gateway, results, workspace.parent)
    assert _outputs(items)[call.action_id]["output"] == result.output
    projected = input_context(items)["current_public_failure"]
    assert projected["failure_summary"] == focus["failure_summary"]
    assert projected["evidence_currency"] == "current"

    def must_not_reparse(*args, **kwargs):
        raise AssertionError("durable feedback must not be regenerated on restart")

    monkeypatch.setattr(DevToolGateway, "_public_check_failure", must_not_reparse)
    restarted = DevToolGateway(
        workspace=workspace, public_task=gateway.public_task, sandbox=sandbox,
        journal=journal, limits=gateway.limits,
    )
    replay = restarted.execute(call)
    assert replay.replayed and replay.output == result.output and sandbox.calls == 1
    assert restarted.current_public_failure() == gateway.current_public_failure()
    assert _recent_checks(restarted) == _recent_checks(gateway)
    recent = _recent_checks(restarted)[0]
    assert recent["truncated"] and len(recent["stdout"]) <= 4_000
    assert recent["stdout"].startswith("public log line\n")


@pytest.mark.parametrize("change", ["passed", "timed_out", "deadline_exhausted", "cleanup_failed"])
def test_output_diagnostics_do_not_reclassify_execution_outcome(gateway_factory, change):
    sandbox = OutputSandbox(CAPTURED_TAIL, truncated=True)
    sandbox.result = replace(sandbox.result, **(
        {"exit_code": 0} if change == "passed" else {change: True}
    ))
    gateway, _, _ = gateway_factory(sandbox=sandbox)
    result = gateway._run_check(gateway.public_task.visible_checks[0].id)
    assert result["truncated"] is True
    assert result["passed"] is (change == "passed")
    assert ("public_check_failure" in result) is (change == "timed_out")


def test_public_feedback_does_not_read_other_task_fields(gateway_factory):
    gateway, journal, _ = gateway_factory(sandbox=OutputSandbox(CAPTURED_TAIL))
    result = gateway.execute(RequestedTool(
        name="run_check", action_id="public-only",
        arguments={"check_id": gateway.public_task.visible_checks[0].id},
    ))
    package = SimpleNamespace(
        public=gateway.public_task, private="PRIVATE_SPEC_SENTINEL",
        reference_patch="REFERENCE_PATCH_SENTINEL", hidden="HIDDEN_PATH_SENTINEL",
        reasoning="RAW_REASONING_SENTINEL",
    )
    context = _build_context(
        package=package, gateway=gateway, journal=journal, correction=None,
        latest_tool_results=[result], counters=_RunCounters(), elapsed_seconds=0,
        limits=gateway.limits,
    )
    for sentinel in (package.private, package.reference_patch, package.hidden, package.reasoning):
        assert sentinel not in context and sentinel not in canonical_json(journal.events())


def test_feedback_changes_surface_identity_not_global_limits_or_run_schema():
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    assert dev_tool_surface_hash() != (
        "sha256:43e2a53673700c48b46247df8b1d91e7ce2af52b88d042f00d843128e9e5f6de"
    )
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1_800)
