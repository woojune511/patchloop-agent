from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
import test_dev_context_v12 as source_tests
from pydantic import ValidationError
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import configured, records
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevRunEnvelope, DevRunRequest
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ResumeContractMismatch

source_gateway = source_tests.source_gateway
observe = source_tests.observe


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("source retention tests must not call a real provider")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.mark.parametrize("option", [None, 24_000, 48_000])
def test_cli_and_request_bind_only_nondefault_retention(tmp_path, monkeypatch, option):
    base = mock_request(tmp_path)
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captured.append(request) or {})
    args = ["dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
            "--planning-policy", "brief-v1"]
    if option is not None:
        args += ["--retained-source-chars", str(option)]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    request = captured[0]
    assert request.retained_source_chars == (option or 24_000)
    assert ("retained_source_chars" in request.model_dump()) == (option == 48_000)
    assert (runner._model_hash(request, None) == runner._model_hash(base, None)) == (
        option != 48_000
    )


@pytest.mark.parametrize("value", [0, 32_000, 48_001, "48000", 48_000.5, True])
def test_invalid_retention_is_rejected_before_execution(tmp_path, monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid configuration reached run_dev")
    monkeypatch.setattr(runner, "run_dev", forbidden)
    base = mock_request(tmp_path)
    with pytest.raises(ValidationError, match="retained_source_chars"):
        DevRunRequest.model_validate({**base.model_dump(), "retained_source_chars": value})
    # CLI converts integer text before the request validates the two supported choices.
    if not isinstance(value, str):
        result = CliRunner().invoke(app, [
            "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
            "--retained-source-chars", str(value),
        ])
        assert result.exit_code != 0


@pytest.mark.parametrize("cap", [24_000, 48_000])
def test_retention_survives_fresh_segment_without_unread_or_stale_source(
    source_gateway, cap,
):
    gateway, sources, tracked = source_gateway
    # Each observed range fits the unchanged 24k per-read limit. The combined old
    # source exceeds it; the unobserved gap must not be filled by a larger pool.
    lines = [f"line{number:04d} " + "가" * 90 for number in range(1, 601)]
    sources["src.py"] = ("\n".join(lines) + "\n").encode()
    first = observe(gateway, "src.py", 1, 200, action_id="older")
    second = observe(gateway, "src.py", 202, 401, action_id="newer")
    latest = observe(gateway, "src.py", 501, 510, action_id="latest")
    for result in (first, second, latest):
        assert len(result.output["spans"][0]["content"]) < 24_000
    # Recover observations from the durable journal with the selected run setting.
    recovered = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits, retained_source_chars=cap,
    )
    recovered._tracked_path = tracked
    projection = recovered.prepare_context_projection(latest_results=[latest])
    selected = {n for s in projection.source_spans
                for n in range(s["start_line"], s["end_line"] + 1)}
    observed = set(range(1, 201)) | set(range(202, 402))
    assert selected <= observed
    assert (selected == observed) == (cap == 48_000)
    assert 201 not in selected and not selected & set(range(501, 511))
    assert projection.retained_content_chars <= cap
    assert sum(len(s["content"].encode()) for s in projection.source_spans) > cap
    assert recovered.context_spans(exclude={latest.output["spans"][0]["span_id"]}) == list(
        projection.source_spans
    )
    state = json.loads(runner._build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=recovered,
        journal=gateway.journal, correction=None, latest_tool_results=[latest],
        counters=runner._RunCounters(), elapsed_seconds=0, limits=gateway.limits,
    ))
    # A new segment receives the projected source even without prior native history.
    wire = assemble_model_input(
        system_prompt="Fixed", state=state, history=[], context_policy=segments.POLICY,
    )
    delivered = reconstruct_state(wire, context_policy=segments.POLICY)
    assert delivered["context_projection"]["retained_content_limit"] == cap
    assert delivered["source_spans"] == list(projection.source_spans)
    assert delivered["latest_tool_results"][0]["output"] == latest.output
    sources["src.py"] = b"changed source\n"
    assert recovered.prepare_context_projection(latest_results=[latest]).delivered_spans == ()


def test_48k_does_not_expand_individual_read_output(source_gateway):
    gateway, sources, _ = source_gateway
    gateway.retained_source_chars = 48_000
    sources["src.py"] = ("\n".join("x" * 100 for _ in range(400)) + "\n").encode()
    result = observe(gateway, "src.py", 1, 400)
    span = result.output["spans"][0]
    assert len(span["content"]) <= 24_000
    assert span["end_line"] < 400


@pytest.mark.parametrize("cap", [24_000, 48_000])
def test_mock_handoff_resume_binds_cap_and_reaches_isolated_evaluation(
    tmp_path, monkeypatch, cap,
):
    request = mock_request(tmp_path).model_copy(update={
        "context_policy": segments.POLICY, "retained_source_chars": cap,
        "repair_recheck": True,
    })
    contexts = []
    original = runner._build_context

    def capture(**kwargs):
        context = original(**kwargs)
        contexts.append(json.loads(context))
        return context

    monkeypatch.setattr(runner, "_build_context", capture)
    _crash_journal_once(
        monkeypatch, event_type=segments.EVENT, when="after",
        predicate=lambda payload: payload["reason"] != "initial",
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    before = journal.path.read_bytes()
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"retained_source_chars": 72_000 - cap}))
    assert journal.path.read_bytes() == before
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["accepted_mutations"] == 1
    assert result["cost_nanos"] == result["call_counts"]["input_count"] == 0
    assert {c["context_projection"]["retained_content_limit"] for c in contexts} == {cap}
    envelope = json.loads(journal.envelope_path.read_text(encoding="utf-8"))
    assert ("retained_source_chars" in envelope) == (cap == 48_000)
    assert DevRunEnvelope.model_validate(envelope).model_dump(mode="json") == envelope
    started = next(e["payload"] for e in journal.events() if e["event_type"] == "run_started")
    assert started.get("retained_source_chars", 24_000) == cap
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("resource", ["tokens", "bytes"])
def test_48k_fresh_state_still_stops_at_segment_limits(tmp_path, monkeypatch, resource):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"retained_source_chars": 48_000})
    if resource == "tokens":
        def count(self, payload, **kwargs):
            counted.append(payload["input"])
            return 60_001
        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", count)
    else:
        monkeypatch.setattr(segments, "MAX_REQUEST_BYTES", 1)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    assert not inputs and len(counted) == (resource == "tokens")
