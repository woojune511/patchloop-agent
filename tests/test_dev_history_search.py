from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import request

from patchloop.artifacts import ArtifactStore
from patchloop.dev import history_search as search
from patchloop.dev import runner, segments
from patchloop.dev.contracts import (
    DevModelTurn,
    DevRunRequest,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.conversation import SEGMENT_RULES, history_metadata, segment_seed
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.errors import ActionConflict, ContractError, RecoveryError, ResumeContractMismatch
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("history search test attempted a provider request")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def call(action="history-1", query="original_dispatch"):
    return RequestedTool(name=search.TOOL, action_id=action, arguments={"query": query},
                         turn_decision={"mode": "inspect", "basis": "Recover exact inputs.",
                                        "evidence_goal": "Recover original_dispatch conditions."})


def exchange(action="probe-1", diff="old-diff", text="original_dispatch"):
    arguments = {"question": "Check original inputs", "python_source": f"print('{text}')"}
    result = {"action_id": action, "tool": "run_probe", "status": "succeeded",
              "workspace_diff_hash": diff, "output": {"stdout": text, "stderr": "",
              "environment": {"cwd": "isolated", "pythonpath": ["src"]}}}
    return [{"type": "function_call", "call_id": action, "name": "run_probe",
             "arguments": canonical_json(arguments)},
            {"type": "function_call_output", "call_id": action, "output": canonical_json(result)}]


def items(*, observation=None, exchanges=(), state=None):
    current = {"current_diff": {"patch_hash": "new-diff"}, **(state or {})}
    if observation is not None:
        current["operator_public_observation"] = observation
    return [*segment_seed("test", {"task_id": "fixture"}),
            SEGMENT_RULES.archive(exchanges=exchanges),
            {"role": "developer", "content": canonical_json({
                "kind": "harness_current_state", "state": current})}]


def deliver(journal, store, data, *, turn="t1", dispatched=True):
    artifact = store.put_text(canonical_json(data))
    journal.append("turn_started", {"turn_id": turn,
        "model_input_artifact": artifact.model_dump(mode="json"),
        "model_input_hash": artifact.content_hash,
        "native_history": history_metadata(data, context_policy="segmented-v1")})
    if dispatched:
        journal.append("model_call_finished", {"turn_id": turn})


def test_exact_program_setup_result_and_supplied_observation_survive_segment_loss():
    history = search.PublicHistory()
    observation = {"call": "original_dispatch(x=3)", "setup": {"missing": "child/init.py"},
                   "result": "original_dispatch failed"}
    initial = items(observation=observation, exchanges=exchange())
    history.ingest(initial, sequence=1, turn_id="old", input_hash="input")
    history.ingest(items(), sequence=8, turn_id="new", input_hash="next")
    result = history.search("original_dispatch", current_diff_hash="new-diff")
    assert len(result["records"]) == 2
    bodies = [r["body"] for r in result["records"]]
    assert {"field": "operator_public_observation", "value": observation} in bodies
    probe = next(r for r in result["records"] if r["kind"] == "public_tool_exchange")
    assert probe["body"]["result"] == json.loads(exchange()[1]["output"])
    assert probe["body"]["call"]["arguments"] == json.loads(exchange()[0]["arguments"])
    assert probe["diff_currency"] == "older_or_different_diff"
    assert all(r["origin"]["first_delivered_sequence"] == 1 for r in result["records"])


def test_only_dispatched_inputs_no_future_private_opaque_or_model_notes(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_history")
    store = ArtifactStore(tmp_path / "artifacts")
    data = items(exchanges=exchange(), state={
        "working_notes": {"findings": ["unverified_hypothesis"]},
        "working_plan": {"plan": "unverified_hypothesis"}})
    data.insert(3, {"type": "reasoning", "id": "r", "encrypted_content": "opaque_secret"})
    deliver(journal, store, data)
    journal.append("evaluator_finished", {"hidden": "private_secret"})
    cutoff = len(journal.events()) + 1
    deliver(journal, store, items(observation={"text": "future_secret"}), turn="t2")
    deliver(journal, store, items(observation={"text": "count_only_secret"}),
            turn="t3", dispatched=False)
    history = search.PublicHistory()
    history.sync(journal.events(), store, before_sequence=cutoff)
    assert len(history.records) == 1
    assert history.search("original_dispatch", current_diff_hash="old-diff")["records"]
    for query in ["future_secret", "private_secret", "opaque_secret", "unverified_hypothesis"]:
        assert not history.search(query, current_diff_hash="new")["records"]
    history.sync(journal.events(), store, before_sequence=len(journal.events()) + 1)
    assert "count_only_secret" not in canonical_json(history.records)
    assert {r["kind"] for r in history.records.values()} == {
        "public_tool_exchange", "supplied_public_observation"}
    assert len(history.records) == 2


def test_artifact_or_history_metadata_corruption_fails_closed(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_history")
    store = ArtifactStore(tmp_path / "artifacts")
    deliver(journal, store, items(exchanges=exchange()))
    events = journal.events()
    events[0]["payload"]["native_history"]["item_count"] += 1
    with pytest.raises(RecoveryError, match="history contract"):
        search.PublicHistory().sync(events, store, before_sequence=99)
    events[0]["payload"]["model_input_hash"] = "corrupt"
    with pytest.raises(RecoveryError, match="identity mismatch"):
        search.PublicHistory().sync(events, store, before_sequence=99)


def test_oversize_has_exact_labelled_excerpt_and_combined_budget_is_hard():
    history = search.PublicHistory()
    for n, size in enumerate([60_000, 23_000, 500]):
        history.ingest(items(observation={"text": "needle " * 100 + "x" * size}),
                       sequence=n + 1, turn_id=str(n), input_hash=str(n))
    result = history.search("needle", current_diff_hash="new")
    assert len(result["records"]) == 3
    assert len(canonical_json(result)) <= search.MAX_RESULT_CHARS
    missing = next(r for r in result["records"] if r["body"] is None)
    assert missing["delivery"] == "excerpt_only_result_bound"
    assert not missing["excerpt_is_complete_record"]
    excerpt = missing["excerpt"]
    assert excerpt["pointer"] == "/value/text"
    original = history.records[missing["record_id"]]["body"]["value"]["text"]
    assert original[excerpt["start"]:excerpt["end"]] == excerpt["text"]


def test_record_id_fetch_recovers_a_body_crowded_out_by_the_other_hit():
    history = search.PublicHistory()
    for n in range(2):
        history.ingest(items(observation={"name": n, "text": "needle " * 4000}),
                       sequence=n + 1, turn_id=str(n), input_hash=str(n))
    result = history.search("needle", current_diff_hash="new")
    missing = next(r for r in result["records"] if r["body"] is None)
    fetched = history.search(missing["record_id"], current_diff_hash="new")
    assert len(fetched["records"]) == 1
    assert fetched["records"][0]["delivery"] == "complete"
    assert sha256_json(fetched["records"][0]["body"]) == missing["record_id"]
    assert all(r["body"] is None or sha256_json(r["body"]) == r["record_id"]
               for r in result["records"])


def test_candidate_previews_cannot_evict_complete_higher_ranked_evidence(monkeypatch):
    history = search.PublicHistory()
    for n in range(8):
        history.ingest(items(observation={"text": "needle " * (2700 if n < 2 else 10000),
                                         "name": n}),
                       sequence=n, turn_id=str(n), input_hash=str(n))
    ordered = list(history.records.values())
    _, excerpts = history.rank("needle")
    monkeypatch.setattr(history, "rank", lambda query: (
        [(8 - i, record) for i, record in enumerate(ordered)], excerpts))
    result = history.search("needle", current_diff_hash="new")
    assert all(r["delivery"] == "complete" for r in result["records"][:2])
    assert all(r["body"] is None for r in result["records"][2:])
    assert len(canonical_json(result)) <= search.MAX_RESULT_CHARS


def test_large_record_pages_round_trip_without_silent_truncation():
    history = search.PublicHistory()
    history.ingest(items(observation={"source": 'needle "한글"\n' * 6000}),
                   sequence=1, turn_id="t", input_hash="input")
    key = next(iter(history.records))
    text, offset = "", None
    while True:
        result = history.search(key, current_diff_hash="new", offset=offset)
        assert len(canonical_json(result)) <= search.MAX_RESULT_CHARS
        row = result["records"][0]
        assert row["body"] is None and row["delivery"] == "partial_json_page"
        page = row["page"]
        assert page["start"] == len(text) and page["end"] > page["start"]
        text += page["text"]
        offset = page["next_offset"]
        if offset is None:
            break
    assert json.loads(text) == history.records[key]["body"]
    assert sha256_json(json.loads(text)) == key
    for offset, query in [(len(text), key), (-1, key), (True, key), (0, "needle")]:
        with pytest.raises(ContractError):
            history.search(query, current_diff_hash="new", offset=offset)


def test_eight_candidates_include_exact_excerpt_of_large_record_conditions():
    history = search.PublicHistory()
    history.ingest(items(observation={"call": "load_config source_path fallback_enabled",
                                     "unrelated": "background detail " * 6000}),
                   sequence=1, turn_id="first", input_hash="first")
    target = next(iter(history.records))
    for n in range(10):
        history.ingest(items(observation={"name": n, "call": "load_config retry mode"}),
                       sequence=n + 2, turn_id=str(n), input_hash=str(n))
    history.ingest(items(), sequence=20, turn_id="current", input_hash="current")
    result = history.search("load_config source_path fallback_enabled", current_diff_hash="new")
    assert len(result["records"]) == 8
    candidate = next(r for r in result["records"] if r["record_id"] == target)
    assert candidate["excerpt"]["text"] == "load_config source_path fallback_enabled"


def test_visible_duplicate_is_labelled_and_exact_id_lookup_remains_available():
    history = search.PublicHistory()
    a = items(observation={"text": "original_dispatch left"})
    b = items(observation={"text": "original_dispatch right"})
    history.ingest(a, sequence=1, turn_id="a", input_hash="a")
    old = next(iter(history.records))
    history.ingest(b, sequence=2, turn_id="b", input_hash="b")
    result = history.search("original_dispatch", current_diff_hash="new")
    assert result["records"][0]["record_id"] == old
    visible = next(r for r in result["records"] if r["already_visible"])
    assert history.search(visible["record_id"], current_diff_hash="new")["records"][0]["body"]


def test_reduced_handoff_view_does_not_mark_original_action_body_visible():
    history = search.PublicHistory()
    full = exchange(text="original_dispatch complete caller and environment")
    history.ingest(items(exchanges=full), sequence=1, turn_id="first", input_hash="first")
    shortened = json.loads(json.dumps(full))
    body = json.loads(shortened[1]["output"])
    body["output"]["stdout"] = "original_dispatch"
    shortened[1]["output"] = canonical_json(body)
    history.ingest(items(exchanges=shortened), sequence=2, turn_id="next", input_hash="next")
    assert len(history.records) == 1
    result = history.search("original_dispatch", current_diff_hash="new")
    assert not result["records"][0]["already_visible"]
    assert result["records"][0]["body"]["result"] == json.loads(full[1]["output"])


@pytest.mark.parametrize("query", ["", "  ", "x" * 801, 3])
def test_invalid_query(query):
    with pytest.raises(ContractError, match="1-800"):
        search.PublicHistory().search(query, current_diff_hash="d")


def test_registration_is_opt_in_singleton_and_does_not_change_baseline():
    assert search.TOOL not in {s["name"] for s in dev_tool_schemas(finish_enabled=True)}
    schemas = dev_tool_schemas(finish_enabled=True, history_search_policy=search.POLICY)
    assert next(s for s in schemas if s["name"] == search.TOOL)["parameters"]["properties"][
        "turn_decision"]["properties"]["mode"]["enum"] == ["inspect"]
    assert validate_tool_batch([call()]) == "single_action"
    with pytest.raises(ContractError):
        validate_tool_batch([call(), call("second")])
    with pytest.raises(ContractError):
        validate_tool_batch([call()], allowed_tools={"read_file"})
    assert dev_tool_surface_hash(history_search_policy=search.POLICY) != dev_tool_surface_hash()
    assert system_prompt(history_search_policy=search.POLICY).endswith(search.INSTRUCTIONS)
    assert "search_history" not in system_prompt()
    with pytest.raises(ValidationError, match="requires segmented"):
        DevRunRequest(task="public.yaml", provider="mock", model="mock",
                      history_search_policy=search.POLICY)


def test_search_spends_optional_headroom_not_required_anchor_or_repair_read(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.history_search_policy = search.POLICY
    counters = runner._RunCounters()
    policy = runner._tool_policy(gateway, counters, gateway.limits)
    assert search.TOOL in policy.allowed_tools
    counters.model_calls = gateway.limits.max_model_calls - policy.completion_budget_calls
    protected = runner._tool_policy(gateway, counters, gateway.limits)
    assert search.TOOL not in protected.allowed_tools
    assert "read_file" in protected.allowed_tools


def test_completion_cost_reserve_includes_the_anchor_read_after_history_search():
    from test_dev_budget_v16 import PolicyGateway
    from test_dev_completion_cost import funded_policy, ledger_for_slots

    gateway = PolicyGateway()
    gateway.current_diff.patch = ""
    gateway.anchor = False
    gateway.public_task.visible_checks = []
    gateway.statuses = {}
    gateway.probe_sandbox = None
    gateway.ready_to_submit = lambda: False
    gateway.history_search_policy = search.POLICY
    ledger = ledger_for_slots(8)
    policy = funded_policy(gateway, ledger)
    assert search.TOOL in policy.allowed_tools
    assert policy.completion_cost["future_calls_reserved"] == policy.completion_budget_calls == 5
    admission = ledger.admit(60_000, future_cost_reserve_nanos=(
        policy.completion_cost["future_cost_reserve_nanos"]))
    ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                  output_tokens=admission.output_ceiling)
    assert ledger.remaining_nanos >= 5 * ledger.future_call_reservation_nanos()
    assert funded_policy(gateway, ledger).protected_completion_possible


def test_gateway_replay_and_recovery_do_not_cache_stale_corpus_or_authorize_edits(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.history_search_policy = search.POLICY
    store = ArtifactStore(journal.root / "artifacts")
    deliver(journal, store, items(exchanges=exchange()))
    first = gateway.execute(call())
    assert first.status == "succeeded" and first.output["records"]
    assert not gateway.has_current_mutation_evidence()
    events = len(journal.events())
    assert gateway.execute(call()) == first.model_copy(update={"replayed": True})
    assert len(journal.events()) == events
    with pytest.raises(ActionConflict):
        gateway.execute(call(query="changed"))
    deliver(journal, store, items(observation={"result": "newly_seen"}), turn="t2")
    second = gateway.execute(call("history-2", "newly_seen"))
    assert second.output["records"] and not second.evidence_cache_hit
    counters = runner._RunCounters(failed_check_pending=True)
    runner._update_inspection_counters(counters, [second], gateway)
    assert counters.inspection_turns_at_diff == 1
    assert not counters.failed_check_repair_read_used and counters.current_anchor_diff_hash is None
    restored = DevToolGateway(workspace=workspace, public_task=gateway.public_task,
                              sandbox=gateway.sandbox, journal=journal, limits=gateway.limits,
                              history_search_policy=search.POLICY)
    assert restored.execute(call("history-2", "newly_seen")) == second.model_copy(
        update={"replayed": True})
    third = restored.execute(call("history-3", "newly_seen"))
    assert third.output == second.output


def test_mock_search_round_trip_reaches_isolated_evaluation_and_binds_resume(monkeypatch, tmp_path):
    original = MockDevAdapter._next_action
    searched = []

    def next_action(self, context, schemas):
        state = json.loads(context)
        if state.get("source_spans") and not searched:
            searched.append(True)
            assert search.TOOL in {s["name"] for s in schemas}
            return DevModelTurn(tool_calls=[call(query="parse_rows")])
        return original(self, context, schemas)

    monkeypatch.setattr(MockDevAdapter, "_next_action", next_action)
    req = request(tmp_path).model_copy(update={"context_policy": "segmented-v1",
                                             "history_search_policy": search.POLICY})
    result = runner.run_dev(req)
    assert result["runs"][0]["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(tmp_path, result["runs"][0]["run_id"])
    actions = [e["payload"]["result"] for e in journal.events()
               if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"]
               == search.TOOL]
    assert len(actions) == 1 and actions[0]["output"]["records"]
    assert actions[0]["output"]["presentation"] == "full-first-evidence-v2"
    assert all(r["delivery"] == "complete" for r in actions[0]["output"]["records"])
    assert all(r["body"]["result"]["output"]["spans"] for r in actions[0]["output"]["records"]
               if r["candidate"]["tool"] in {"read_file", "search_files"})
    envelope = journal.load_envelope()
    assert envelope.history_search_policy == search.POLICY
    assert envelope.segment_boundary_policy == segments.DEFAULT_BOUNDARY_POLICY
    changed = envelope.model_copy(update={"history_search_policy": "none"})
    with pytest.raises(ResumeContractMismatch):
        runner._validate_resume_envelope(envelope, changed)
    assert searched


def test_pending_search_rebuilds_the_original_dispatch_cutoff(monkeypatch, gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.history_search_policy = search.POLICY
    store = ArtifactStore(journal.root / "artifacts")
    deliver(journal, store, items(exchanges=exchange()))
    append = journal.append

    def crash(event_type, payload):
        if event_type == "action_finished":
            raise RuntimeError("interrupted before receipt")
        return append(event_type, payload)

    monkeypatch.setattr(journal, "append", crash)
    with pytest.raises(RuntimeError, match="interrupted before receipt"):
        gateway.execute(call())
    monkeypatch.setattr(journal, "append", append)
    # Even if later material exists, a pending action must not search beyond its
    # durable admission. Ordinary runtime recovery will not dispatch this input.
    deliver(journal, store, items(observation={"text": "original_dispatch later"}), turn="t2")
    restored = DevToolGateway(workspace=workspace, public_task=gateway.public_task,
                              sandbox=gateway.sandbox, journal=journal, limits=gateway.limits,
                              history_search_policy=search.POLICY)
    result = restored.execute(call())
    assert result.status == "succeeded" and len(result.output["records"]) == 1
    assert result.output["records"][0]["kind"] == "public_tool_exchange"
    assert sum(e["event_type"] == "action_started" for e in journal.events()) == 1


def test_fake_provider_counts_search_and_preserves_segment_rules(monkeypatch, tmp_path):
    from test_dev_segments import assert_submitted, configured, records

    class Script(MockDevAdapter):
        searched = False

        def _next_action(self, context, schemas):
            state = json.loads(context)
            if state.get("source_spans") and not self.searched:
                self.searched = True
                return DevModelTurn(tool_calls=[call(query="parse_rows")])
            return super()._next_action(context, schemas)

    req, inputs, counted, _ = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=Script("csv-quoted-newline"))
    req = req.model_copy(update={"history_search_policy": search.POLICY})
    result = runner.run_dev(req)
    # This fixture deliberately pairs synthetic Docker provenance with a local
    # smoke task. The existing isolated evaluator must still reject that mismatch.
    assert_submitted(result["runs"][0])
    assert len(inputs) == len(counted) == 5  # One extra ordinary model call.
    journal, _ = records(req)
    assert sum(e["event_type"] == "action_started" for e in journal.events()) == 6
    boundaries = [e["payload"] for e in journal.events() if e["event_type"] == segments.EVENT]
    assert len(boundaries) == 2  # Initial segment, normal mutation-result follow-up.
    search_result = next(e["payload"]["result"] for e in journal.events()
                         if e["event_type"] == "action_finished"
                         and e["payload"]["result"]["tool"] == search.TOOL)
    assert search_result["status"] == "succeeded" and search_result["output"]["records"]
