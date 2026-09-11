from __future__ import annotations

import copy
import json
import socket

import pytest
from test_fresh_state_design import call, output, span
from test_fresh_state_design import control as control

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_design as fresh
from diagnostics import model_state_episode as episode
from diagnostics import model_state_sampler as design
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner as loop
from patchloop.dev.conversation import (
    CONVERSATION_INSTRUCTIONS,
    assemble_model_input,
    history_metadata,
    reconstruct_state,
)
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_text


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("instruction tests cannot use credentials or network")

    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)


def test_all_four_arms_change_only_unsent_format_instructions(control):
    snapshots, _ = design.factorial_requests(control)
    originals = copy.deepcopy(snapshots)
    requests = {arm: episode.episode_request(request) for arm, request in snapshots.items()}
    assert snapshots == originals
    assert design.factorial_requests(control)[0] == originals  # Standalone sampler unchanged.
    for arm, request in requests.items():
        original = originals[arm]
        assert request["input"][1:] == original["input"][1:]
        restored = copy.deepcopy(request)
        restored["input"][0] = original["input"][0]
        assert design.wire(restored) == design.wire(original)  # Includes tool/property order.
        instructions = request["input"][0]["content"]
        assert CONVERSATION_INSTRUCTIONS in instructions
        assert "Read these top-level fields directly;" not in instructions
        assert "this archive and parse its output field" not in instructions
        assert "source_bodies view already resolves current lines" not in instructions
        assert "initial checkpoint only" in instructions
        assert instructions.count(episode.EPISODE_CONTEXT_INSTRUCTIONS) == 1
    for left, right in (("A", "C"), ("B", "D")):
        assert design.wire({k: v for k, v in requests[left].items() if k != "model"}) == (
            design.wire({k: v for k, v in requests[right].items() if k != "model"}))
    for left, right in (("A", "B"), ("C", "D")):
        pair = [copy.deepcopy(requests[arm]) for arm in (left, right)]
        for request in pair:
            state = json.loads(request["input"][1]["content"])
            state.pop(design.FIELD)
            request["input"][1]["content"] = design.wire(state).decode()
        assert design.wire(pair[0]) == design.wire(pair[1])


def test_unexpected_snapshot_contract_is_not_silently_rewritten(control):
    snapshot = design.factorial_requests(control)[0]["A"]
    snapshot["input"][0]["content"] += "UNRECOGNIZED_FORMAT"
    before = copy.deepcopy(snapshot)
    with pytest.raises(ContractError, match="snapshot instruction contract"):
        episode.episode_request(snapshot)
    assert snapshot == before


def resolve_current(items):
    initial = json.loads(items[1]["content"])
    observations = [*initial["public_evidence_archive"], *items[3:]]
    return fresh.materialize_sources(reconstruct_state(items), observations)


@pytest.mark.parametrize("arm", list("ABCD"))
def test_archive_native_mutation_and_saved_input_recovery_have_one_authority(
    control, arm, tmp_path,
):
    seed = episode.episode_request(design.factorial_requests(control)[0][arm])
    initial = copy.deepcopy(seed["input"])
    state = reconstruct_state(initial)
    assert resolve_current(initial) == state["source_bodies"]
    # New observation is native, not backfilled into the immutable initial archive.
    helper = {**span("NEW_PUBLIC_HELPER", 1, file_hash="helper"), "path": "helper.py"}
    read_exchange = [
        {"type": "reasoning", "id": "new-r1", "encrypted_content": "new-opaque-1",
         "summary": []},
        call("new-read", "read_file", {"path": "helper.py", "start_line": 1, "end_line": 1}),
        output("new-read", "read_file", {"spans": [helper]}),
    ]
    current = {k: copy.deepcopy(v) for k, v in state.items()
               if k not in {*fresh.EXTRA_FIELDS, design.FIELD}}
    current["remaining_budget"]["model_calls"] -= 1
    current["current_sources"].append({
        "path": "helper.py", "file_hash": "helper", "edit_permission": "supporting_only",
        "content_delivery": {"new-read": {"output.spans[0]": [[1, 1]]}},
    })
    after_read = assemble_model_input(
        system_prompt=loop.DEV_SYSTEM_PROMPT, state=current, history=read_exchange,
        previous_input=initial,
    )
    assert after_read[:len(initial)] == initial
    assert after_read[len(initial):-1] == read_exchange
    assert json.loads(after_read[-1]["content"])["state"]["current_sources"] == (
        current["current_sources"])
    assert "NEW_PUBLIC_HELPER" in canonical_json(resolve_current(after_read))

    # The post-image has a new raw hash. Unchanged text can point back across the
    # native/archive boundary without promoting the old source_bodies identity.
    alias = {**span("alpha", 10, file_hash="after"), "origin": "revalidated_after_mutation",
             "content_hash": sha256_text("alpha"), "content_delivery": [{
                 "action_id": "read1", "field": "output.spans[0]", "file_hash": "before",
                 "start_line": 10, "end_line": 10, "target_start_line": 10,
             }]}
    del alias["content"]
    mutation_exchange = [
        {"type": "reasoning", "id": "new-r2", "encrypted_content": "new-opaque-2",
         "summary": []},
        call("new-edit", "replace_text", {"path": "a.py", "old_text": "BETA",
                                            "new_text": "CURRENT_POST_IMAGE"}),
        output("new-edit", "replace_text", {
            "mutation_evidence": span("CURRENT_POST_IMAGE", 11, file_hash="after"),
            "revalidated_spans": [alias],
        }),
    ]
    current["current_diff"] = {"patch_hash": "after-diff", "patch": "AFTER_PUBLIC_PATCH"}
    current["current_public_failure"] = None
    current["remaining_budget"]["model_calls"] -= 1
    current["current_sources"][0] = {
        "path": "a.py", "file_hash": "after", "edit_permission": "allowed",
        "content_delivery": {"new-edit": {"output.mutation_evidence": [[11, 11]],
                                           "output.revalidated_spans[0]": [[10, 10]]}},
    }
    after_edit = assemble_model_input(
        system_prompt=loop.DEV_SYSTEM_PROMPT, state=current, history=mutation_exchange,
        previous_input=after_read,
    )
    assert after_edit[:len(after_read)] == after_read
    assert after_edit[len(after_read):-1] == mutation_exchange
    assert reconstruct_state(after_edit) == current
    assert json.loads(after_edit[-1]["content"])["state"].get("public_task") is None
    actual = resolve_current(after_edit)
    assert actual[0]["file_hash"] == "after"
    assert actual[0]["spans"][0]["content"] == "alpha\nCURRENT_POST_IMAGE"
    assert actual[0]["spans"][0]["start_line"] == 10
    assert actual[0]["spans"][0]["end_line"] == 11  # No unobserved gap filled.
    assert json.loads(initial[1]["content"])["source_bodies"][0]["file_hash"] == "current"
    assert "source_bodies" not in reconstruct_state(after_edit)

    # Read-only hydration uses the same saved-input loader as runtime recovery.
    # This does not add an episode resume/retry entrypoint or dispatch any model.
    store = ArtifactStore(tmp_path / "artifacts")
    journal = DevJournal(tmp_path, "run_dev_instruction_recovery")
    ref = store.put_json(after_edit)
    journal.append("turn_started", {"turn_id": "saved", "model_input_artifact": ref.model_dump(
        mode="json"), "model_input_hash": ref.content_hash,
        "native_history": history_metadata(after_edit)})
    restored = loop._load_active_model_input(journal.events()[-1]["payload"], store)
    assert restored == after_edit and resolve_current(restored) == actual
    assert restored[0] == initial[0]
    assert [i["call_id"] for i in restored if i.get("type") == "function_call_output"] == (
        ["new-read", "new-edit"])
    assert sum(i.get("type") == "reasoning" for i in restored) == 2
    assert all(i.get("summary", []) == [] for i in restored)
    assert "OPAQUE_CIPHER_SENTINEL" not in canonical_json(restored)
