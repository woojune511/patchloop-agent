from __future__ import annotations

import json

import pytest
from test_dev_conversation_v22 import _provider_smoke
from test_dev_conversation_v23 import _output, _span
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from typer.testing import CliRunner

import patchloop.cli as cli
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.conversation import (
    APPEND_POLICY,
    WINDOW_POLICY,
    WINDOW_RULES,
    assemble_model_input,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, reference_native_sources
from patchloop.dev.public_history import NATIVE, source_groups
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError, ResumeContractMismatch
from patchloop.util import canonical_json, sha256_json


def build(state=None, *, previous=None, history=(), policy=WINDOW_POLICY):
    return assemble_model_input(
        system_prompt="Fixed public instructions", state={
            "public_task": {"description": "PUBLIC_GOAL"}, **(state or {}),
        }, history=list(history), previous_input=previous, context_policy=policy,
    )


def group(content="one\ntwo", *, start=1, digest="raw-hash", path="src.py"):
    return source_groups({
        (path, digest, n): line for n, line in enumerate(content.split("\n"), start)
    })[0]


def read(action="read", *, content="one\ntwo", path="src.py"):
    return [
        {"type": "function_call", "call_id": action, "name": "read_file",
         "arguments": canonical_json({"path": path, "start_line": 1, "end_line": 2})},
        _output(action, [_span(content, path=path)]),
    ]


def native(items):
    return [item for item in items if item.get("type") in NATIVE]


def state(items):
    return reconstruct_state(items, context_policy=WINDOW_POLICY)


def test_default_input_and_metadata_remain_exact_append_wire():
    before = build(policy=APPEND_POLICY)
    changed = {"public_task": {"description": "PUBLIC_GOAL"}, "remaining_budget": {"model": 3}}
    expected = [*before, *read(), {"role": "developer", "content": json.dumps({
        "kind": "harness_current_state", "state": {"remaining_budget": {"model": 3}},
    }, separators=(",", ":"), ensure_ascii=False)}]
    actual = assemble_model_input(system_prompt="Fixed public instructions", state=changed,
                                  history=read(), previous_input=before)
    assert canonical_json(actual) == canonical_json(expected)
    metadata = history_metadata(actual)
    assert metadata["schema_version"] == "single-user-append-only-state-v3"
    assert "context_policy" not in metadata and "seed_hash" not in metadata
    assert validate_model_input(actual, metadata) == actual


@pytest.mark.parametrize("policy", [None, WINDOW_POLICY, "unknown"])
def test_cli_policy_is_explicit_and_validated_without_provider(monkeypatch, policy):
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captured.append(request) or {})
    args = ["dev", "--provider", "mock", "--task", "tasks/smoke/csv-quoted-newline/public.yaml",
            "--model", "mock-dev"]
    if policy is not None:
        args += ["--context-policy", policy]
    result = CliRunner().invoke(cli.app, args)
    if policy == "unknown":
        assert result.exit_code != 0 and not captured
    else:
        assert result.exit_code == 0
        assert captured[0].context_policy == (policy or APPEND_POLICY)


def test_window_expires_only_snapshots_preserving_seed_native_and_public_observations():
    seed = build({"working_notes": {"open_question": None}})
    cipher = {"type": "reasoning", "id": "r", "encrypted_content": "cipher-exact", "summary": []}
    old = build({
        "remaining_budget": {"model": 8}, "current_sources": [group()],
        "working_notes": {"open_question": "EXPIRED_NOTE"},
        "protocol_correction": {"message": "CONSUMED_CORRECTION"},
        "recent_checks": [{"action_id": "harness-check", "passed": True, "diff_hash": "old"}],
        "future_public_fact": {"value": "OBSERVED_FACT"},
    }, previous=seed, history=[cipher, *read()])
    old_bytes = canonical_json(old)
    current = {"remaining_budget": {"model": 7}, "current_sources": [],
               "visible_check_status": [{"check_id": "check", "status": "NOT_RUN",
                                         "diff_hash": "new"}]}
    result = build(current, previous=old, history=read("helper", path="helper.py"))
    assert canonical_json(old) == old_bytes and result[:3] == seed
    assert native(result) == native([*old, *read("helper", path="helper.py")])
    assert state(result) == {"public_task": {"description": "PUBLIC_GOAL"}, **current}
    wire = canonical_json(result)
    assert "EXPIRED_NOTE" not in wire and "CONSUMED_CORRECTION" not in wire
    assert "OBSERVED_FACT" in wire and "harness-check" in wire
    assert not [i for i in native(result) if i.get("call_id") == "harness-check"]
    assert WINDOW_RULES.inventory([*old, result[-1], *read("helper", path="helper.py")]) == (
        WINDOW_RULES.inventory(result)
    )
    metadata = history_metadata(result, context_policy=WINDOW_POLICY)
    assert metadata["state_update_count"] == metadata["historical_evidence_count"] == 1
    assert metadata["seed_hash"] == sha256_json(seed)
    assert wire.count("PUBLIC_GOAL") == 1 and metadata["user_message_count"] == 1


def test_inline_sources_are_rescued_exactly_without_reading_gaps_or_new_hashes():
    old = build({"current_sources": [group(), group("five", start=5),
                                      group("old", digest="old-hash")]}, previous=build())
    result = build({"current_sources": [group("one")]}, previous=old)
    facts = WINDOW_RULES.inventory(result)[0]
    assert facts == {("src.py", "raw-hash", 1): "one", ("src.py", "raw-hash", 2): "two",
                     ("src.py", "raw-hash", 5): "five", ("src.py", "old-hash", 1): "old"}
    next_input = build({"remaining_budget": {"model": 2}}, previous=result)
    assert WINDOW_RULES.inventory(next_input)[0] == facts
    assert native(next_input) == []  # Archives never impersonate function outputs.


def test_current_delivery_refs_stay_resolvable_after_helper_exploration_and_restart():
    first = build(previous=build(), history=read())
    raw = {"source_spans": [_span()], "working_notes": {"open_question": "current"}}
    current = compact_model_state(reference_native_sources(raw, first), first)
    second = build(current, previous=first, history=read("helper", path="helper.py"))
    third = build(current, previous=second)
    restored = build(current, previous=json.loads(canonical_json(second)))
    assert third == restored
    assert WINDOW_RULES.inventory(third)[0]["src.py", "raw-hash", 2] == "two"
    assert "inline_spans" not in state(third)["current_sources"][0]
    assert len([i for i in native(third) if i.get("call_id") == "read"]) == 2


def test_quoted_public_delivery_can_resolve_but_cannot_become_native_output():
    archive = WINDOW_RULES.archive(exchanges=read())
    history = [archive]
    raw = {"source_spans": [_span()]}
    assert reference_native_sources(raw, history) == raw  # Default remains native-only.
    projected = reference_native_sources(raw, history, archive_kind=PUBLIC_EVIDENCE_KIND)
    assert "content" not in projected["source_spans"][0]
    view = compact_model_state(projected, history, archive_kind=PUBLIC_EVIDENCE_KIND)
    items = build(view, previous=[*build(), archive])
    assert WINDOW_RULES.inventory(items)[0]["src.py", "raw-hash", 1] == "one"
    assert native(items) == []
    # Plain source archives have no action ID: keep the already observed inline fallback.
    inline = WINDOW_RULES.archive(facts={("src.py", "raw-hash", 1): "one"})
    assert reference_native_sources(raw, [inline], archive_kind=PUBLIC_EVIDENCE_KIND) == raw


def test_reasoning_only_correction_and_parallel_results_survive_exactly_once():
    initial = build()
    reasoning = {"type": "reasoning", "id": "incomplete", "encrypted_content": "opaque",
                 "summary": [], "status": "incomplete"}
    corrected = build({"protocol_correction": {"code": "incomplete", "issue": "token_limit"}},
                      previous=initial, history=[reasoning])
    restored = state(json.loads(canonical_json(corrected)))
    assert restored["protocol_correction"]["code"] == "incomplete"
    batch = [*read("a"), *read("b")]
    final = build({"protocol_correction": None}, previous=corrected, history=batch)
    assert native(final) == [reasoning, *batch]
    assert "token_limit" not in canonical_json(final)
    assert build({"protocol_correction": None}, previous=final) == final


@pytest.mark.parametrize("damage", ["gap", "forward", "truncated", "conflict", "task"])
def test_unobserved_or_conflicting_source_and_task_change_are_not_silently_repaired(damage):
    seed = build()
    target = group()
    history = read()
    if damage in {"gap", "forward"}:
        target.pop("inline_spans")
        target["content_delivery"] = {"read": {"output.spans[0]": [[1, 3]]}}
        if damage == "forward":
            target["content_delivery"]["read"]["output.spans[0]"] = [[1, 2]]
            history = []
    elif damage == "truncated":
        target["inline_spans"][0]["end_line"] = 9
    elif damage == "conflict":
        target["inline_spans"][0]["content"] = "wrong\ntwo"
    current = {"current_sources": [target]}
    if damage == "task":
        current["public_task"] = {"description": "changed"}
    with pytest.raises(RecoveryError):
        build(current, previous=seed, history=history)


def test_policy_metadata_and_archive_shape_are_strict():
    items = build(previous=build(), history=read())
    metadata = history_metadata(items, context_policy=WINDOW_POLICY)
    assert validate_model_input(items, metadata, context_policy=WINDOW_POLICY) == items
    with pytest.raises(RecoveryError):
        validate_model_input(items, metadata)
    for field in ("seed_hash", "history_hash", "current_state_hash", "evidence_inventory_hash"):
        with pytest.raises(RecoveryError):
            validate_model_input(items, {**metadata, field: "wrong"}, context_policy=WINDOW_POLICY)
    archive = WINDOW_RULES.archive(records=[{"field": "fact", "value": "public"}])
    view = json.loads(archive["content"])
    view["instructions"] = "changed authority"
    with pytest.raises(RecoveryError):
        history_metadata([*items, {**archive, "content": canonical_json(view)}],
                         context_policy=WINDOW_POLICY)


def payload(store, items, parent=None):
    artifact = store.put_json(items)
    seed = store.put_text(canonical_json(items[:3]), "application/json")
    return {
        "model_input_artifact": artifact.model_dump(mode="json"),
        "model_input_hash": artifact.content_hash,
        "native_history": history_metadata(items, context_policy=WINDOW_POLICY),
        "context_window": {
            "window_id": "window_" + seed.content_hash.removeprefix("sha256:"),
            "seed_artifact": seed.model_dump(mode="json"),
            "previous_input_artifact": store.put_json(parent).model_dump(mode="json") if parent
            else None, "last_exchange_turn_id": "turn_1" if parent else None,
        },
    }


@pytest.mark.parametrize("damage", ["seed", "native", "evidence", "policy"])
def test_resume_rejects_lost_history_even_with_recomputed_current_input_metadata(tmp_path, damage):
    store = ArtifactStore(tmp_path / "artifacts")
    parent = build({"unique_public_fact": "preserve"}, previous=build(), history=read())
    items = build({"remaining_budget": {"model": 2}}, previous=parent, history=read("b"))
    saved = payload(store, items, parent)
    assert runner._load_active_model_input(saved, store, context_policy=WINDOW_POLICY) == items
    if damage == "seed":
        saved["context_window"]["window_id"] = "wrong"
    elif damage == "policy":
        with pytest.raises(runner._ProviderContinuationError):
            runner._load_active_model_input(saved, store)
        return
    else:
        if damage == "native":
            items = [i for i in items if i.get("call_id") != "read"]
        else:
            items = [i for i in items if not WINDOW_RULES.payload(i)
                     or WINDOW_RULES.payload(i)["kind"] != PUBLIC_EVIDENCE_KIND]
        saved = payload(store, items, parent)
    with pytest.raises(runner._ProviderContinuationError):
        runner._load_active_model_input(saved, store, context_policy=WINDOW_POLICY)


@pytest.mark.parametrize("boundary", [
    "provider_call_finished", "turn_decision_recorded", "action_finished", "tool_batch_finished",
])
def test_runner_counts_exact_window_and_resume_never_repeats_exchange_or_mutation(
    tmp_path, monkeypatch, boundary,
):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(update={"context_policy": WINDOW_POLICY})
    _crash_journal_once(monkeypatch, event_type=boundary, when="after", predicate=lambda p: (
        p.get("action_id") == "edit" or p.get("action_ids") == ["edit"]
        or any(c["action_id"] == "edit" for c in p.get("tool_calls", []))
    ))
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    resumed = request.model_copy(update={"resume_run_id": run_id})
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 3 and inputs == counted
    assert [i["call_id"] for i in inputs[-1] if i.get("type") == "function_call"] == [
        "read", "edit",
    ]
    assert [i["encrypted_content"] for i in native(inputs[-1]) if i["type"] == "reasoning"] == [
        "cipher-0", "cipher-1",
    ]
    journal = DevJournal(request.state_root, run_id)
    store = ArtifactStore(request.state_root / "artifacts")
    started = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    assert len({p["context_window"]["window_id"] for p in started}) == 1
    for index, p in enumerate(started):
        saved = runner._load_active_model_input(p, store, context_policy=WINDOW_POLICY)
        assert saved == inputs[index]
        assert p["native_history"]["state_update_count"] <= 1
    assert len([e for e in journal.events() if e["event_type"] == "action_finished"
                and e["payload"]["action_id"] == "edit"]) == 1
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 3
    wire = canonical_json(inputs)
    for forbidden in ("hidden-multiline-csv", "reference.patch", "PLAINTEXT_REASONING_SENTINEL"):
        assert forbidden not in wire


def test_context_policy_is_exact_resume_contract_before_count_or_mutation(tmp_path, monkeypatch):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(update={"context_policy": WINDOW_POLICY})
    _crash_journal_once(monkeypatch, event_type="provider_call_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    before = journal.path.read_bytes()
    assert runner._model_hash(request, None) != runner._model_hash(
        request.model_copy(update={"context_policy": APPEND_POLICY}), None,
    )
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={
            "resume_run_id": run_id, "context_policy": APPEND_POLICY,
        }))
    assert journal.path.read_bytes() == before and len(inputs) == len(counted) == 1
