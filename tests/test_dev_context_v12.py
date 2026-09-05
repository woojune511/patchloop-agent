from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import PropertyMock

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.dev.context import project_observed_sources, source_lines, valid_observed_span
from patchloop.dev.contracts import DevLimits, DevToolResult, PublicTurnDecision, RequestedTool
from patchloop.dev.runner import _build_context, _RunCounters
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.repository import DiffSummary
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def source_gateway(tmp_path, monkeypatch):
    raw_sources = {"src.py": b"first\nsecond\nthird\nfourth\n"}
    public = SimpleNamespace(
        constraints=SimpleNamespace(
            allowed_paths=["src.py"], forbidden_paths=[], max_diff_lines=50, max_changed_files=1,
        ),
        visible_checks=[],
        model_dump=lambda **kwargs: {"task_id": "public-source-test"},
    )
    journal = DevJournal(tmp_path / "state", "run_dev_source")
    gateway = DevToolGateway(
        workspace=tmp_path / "workspace", public_task=public,
        sandbox=None, journal=journal, limits=DevLimits(),
    )

    def tracked(path):
        if path not in raw_sources:
            raise ContractError("not a tracked public path")
        return path, SimpleNamespace(read_bytes=lambda: raw_sources[path])

    monkeypatch.setattr(gateway, "_tracked_path", tracked)
    monkeypatch.setattr(
        DevToolGateway, "current_diff",
        PropertyMock(return_value=DiffSummary([], 0, 0, "", [])),
    )
    return gateway, raw_sources, tracked


def observe(gateway, path, start, end, *, action_id="read"):
    output = gateway._read_file(path, start, end)
    result = DevToolResult(
        action_id=action_id, input_hash=sha256_json([path, start, end]),
        tool="read_file", status="succeeded", output=output,
        workspace_diff_hash=gateway.current_diff_hash,
    )
    gateway._restore_read_result(result)
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    return result


def replacement(old_text, new_text="replacement"):
    return {
        "path": "src.py", "old_text": old_text, "new_text": new_text, "occurrence": 1,
        "hypothesis": "A bounded public replacement addresses the observed behavior.",
        "expected_behavior": "The observed source changes as requested.",
        "causal_revision": None,
    }


def test_clipped_read_never_counts_or_authorizes_unseen_lines(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = ("\n".join(
        "UNSEEN_ANCHOR" if number == 350 else f"line {number:03} " + "x" * 92
        for number in range(1, 401)
    ) + "\n").encode()
    result = observe(gateway, "src.py", 1, 400)
    span = result.output["spans"][0]
    assert result.output["truncated"] is True
    assert span["end_line"] == span["content"].count("\n") + 1 < 350
    assert len(span["content"]) <= 24_000
    assert "UNSEEN_ANCHOR" not in span["content"]
    ledger = gateway.evidence_ledger()
    assert ledger["covered_files"][0]["covered_line_count"] == span["end_line"]
    with pytest.raises(ContractError, match="evidence spans"):
        gateway._validate_replacement_intent(replacement("UNSEEN_ANCHOR"))


def test_eof_oversized_line_and_malformed_span_cannot_create_readiness(source_gateway):
    gateway, sources, _ = source_gateway
    eof = observe(gateway, "src.py", 5, 20)
    assert eof.output["spans"] == []
    assert eof.output["eof"] is True
    assert gateway.has_current_mutation_evidence() is False
    sources["src.py"] = b"x" * 24_001 + b"\n"
    oversized = observe(gateway, "src.py", 1, 1, action_id="oversized")
    assert oversized.output["spans"] == []
    assert oversized.output["diagnostic"]
    assert gateway.has_current_mutation_evidence() is False
    forged = gateway._span("src.py", 1, 10, "x", sha256_bytes(sources["src.py"]))
    gateway.spans[forged["span_id"]] = forged
    assert gateway.prepare_context_projection().editable_paths == ()
    sources["src.py"] = b"\n"
    observe(gateway, "src.py", 1, 1, action_id="blank")
    assert gateway.has_current_mutation_evidence() is False


def test_replacement_accepts_observed_union_but_not_missing_gap(source_gateway):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 2)
    observe(gateway, "src.py", 3, 4, action_id="next")
    validated = gateway._validate_replacement_intent(replacement("second\nthird"))
    assert (validated.anchor_start_line, validated.anchor_end_line) == (2, 3)
    assert len(validated.anchor_evidence_span_ids) == 2
    gateway.spans.clear()
    observe(gateway, "src.py", 1, 1, action_id="before-gap")
    observe(gateway, "src.py", 3, 4, action_id="after-gap")
    with pytest.raises(ContractError, match="contiguously"):
        gateway._validate_replacement_intent(replacement("first\nsecond\nthird"))


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_unchanged_observed_text_survives_mutation_with_either_newline(
    source_gateway, newline
):
    gateway, sources, _ = source_gateway
    sources["src.py"] = newline.join(["old", "stable one", "stable two", "end"]).encode()
    observe(gateway, "src.py", 2, 3)
    sources["src.py"] = newline.join(["new", "stable one", "stable two", "end"]).encode()
    rebound = gateway._revalidated_spans(paths=["src.py"], diff_hash="changed")
    assert len(rebound) == 1
    assert rebound[0]["content"] == "stable one\nstable two"
    assert valid_observed_span(
        rebound[0], source_lines(sources["src.py"].decode()), sha256_bytes(sources["src.py"])
    )


def test_postimage_reports_only_returned_complete_lines(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = ("\n".join("x" * 100 for _ in range(400)) + "\n").encode()
    span = gateway._mutation_postimage_evidence(
        path="src.py", focus_start_line=1, focus_line_count=400, diff_hash="changed"
    )
    assert span is not None
    assert span["end_line"] == span["content"].count("\n") + 1 < 400
    assert span["truncated"] is True
    sources["src.py"] = b""
    assert gateway._mutation_postimage_evidence(
        path="src.py", focus_start_line=1, focus_line_count=1, diff_hash="empty"
    ) is None


def test_revalidated_observation_cannot_rebind_to_a_substring_of_a_changed_line(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = b"abc\nunchanged\n"
    observe(gateway, "src.py", 1, 1)
    sources["src.py"] = b"xabc\nunchanged\n"
    assert gateway._revalidated_spans(paths=["src.py"], diff_hash="changed") == []
    sources["src.py"] = b"moved\nabc\nunchanged\n"
    rebound = gateway._revalidated_spans(paths=["src.py"], diff_hash="changed")
    assert [(span["start_line"], span["end_line"]) for span in rebound] == [(2, 2)]


def test_search_bounds_total_complete_source_and_keeps_matches_visible(
    source_gateway, monkeypatch
):
    gateway, _, _ = source_gateway
    gateway.workspace.mkdir()
    source = gateway.workspace / "src.py"
    source.write_text("\n".join(f"MATCH {number} " + "x" * 2_000 for number in range(40)))
    monkeypatch.setattr(
        "patchloop.dev.tools.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    result = gateway._search_files("MATCH", "*.py")
    assert result["truncated"] is True
    assert sum(len(span["content"]) for span in result["spans"]) <= 24_000
    lines = source_lines(source.read_text())
    file_hash = sha256_bytes(source.read_bytes())
    assert result["spans"]
    assert all(valid_observed_span(span, lines, file_hash) for span in result["spans"])
    assert all("MATCH" in span["content"] for span in result["spans"])


def test_projection_pins_failed_anchor_and_subtracts_native_overlap(source_gateway):
    gateway, sources, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.last_failed_mutation = {"replacement": replacement("second\nthird")}
    for number in range(12):
        path = f"helper_{number}.py"
        sources[path] = ("\n".join("x" * 99 for _ in range(50)) + "\n").encode()
        observe(gateway, path, 1, 50, action_id=path)
    projection = gateway.prepare_context_projection()
    assert projection.retained_content_chars <= 24_000
    assert projection.omitted_observed_line_count > 0
    assert any("second\nthird" in span["content"] for span in projection.source_spans)
    assert projection.editable_paths == ("src.py",)
    snapshot = gateway.state_snapshot(projection=projection)
    assert snapshot.mutation_evidence_paths == projection.editable_paths
    latest = observe(gateway, "src.py", 2, 4, action_id="latest")
    projection = gateway.prepare_context_projection([latest])
    retained_src = [span for span in projection.source_spans if span["path"] == "src.py"]
    assert all(span["end_line"] < 2 for span in retained_src)
    assert any(span["content"] == "second\nthird\nfourth" for span in projection.delivered_spans)


def test_projection_merges_overlap_never_fills_gaps_and_is_order_independent():
    make = DevToolGateway._span
    spans = [make("src.py", 1, 2, "one\ntwo", "hash"),
             make("src.py", 2, 3, "two\nthree", "hash"),
             make("src.py", 5, 5, "five", "hash")]
    left = project_observed_sources(
        spans, native_spans=[], priorities=[], editable_paths={"src.py"}
    )
    right = project_observed_sources(
        list(reversed(spans)), native_spans=[], priorities=[], editable_paths={"src.py"}
    )
    assert left == right
    assert [(span["start_line"], span["end_line"]) for span in left.source_spans] == [
        (1, 3), (5, 5),
    ]
    assert left.source_spans[0]["content"] == "one\ntwo\nthree"


def test_projection_pinned_anchor_is_atomic_at_the_exact_character_budget():
    make = DevToolGateway._span
    first = {**make("src.py", 1, 1, "one", "hash"), "last_observed_seq": 1}
    second = {**make("src.py", 2, 2, "two", "hash"), "last_observed_seq": 2}
    kwargs = {"native_spans": [], "priorities": [("src.py", 1, 2, 0)],
              "editable_paths": {"src.py"}}
    fits = project_observed_sources([first, second], max_chars=7, **kwargs)
    missing = project_observed_sources([first, second], max_chars=6, **kwargs)
    assert fits.source_spans[0]["content"] == "one\ntwo"
    assert fits.retained_content_chars == 7
    assert missing.source_spans == ()
    assert missing.editable_paths == ()
    assert missing.omitted_pinned_ranges == ({"path": "src.py", "start_line": 1, "end_line": 2},)


def test_omitted_source_metadata_is_bounded_body_free_and_preserves_gaps():
    spans = [
        DevToolGateway._span(f"helper_{number:02}.py", line, line, "body", "hash")
        for number in range(16) for line in (1, 3)
    ]
    projection = project_observed_sources(
        spans, native_spans=[], priorities=[], editable_paths=set(), max_chars=0
    )
    assert projection.omitted_observed_line_count == 32
    assert projection.omitted_observed_range_count == 32
    assert len(projection.omitted_observed_ranges) == 12
    assert all(
        set(row) == {"path", "file_hash", "start_line", "end_line"}
        and row["start_line"] == row["end_line"] in {1, 3}
        for row in projection.omitted_observed_ranges
    )


def test_omitted_range_metadata_excludes_both_native_and_retained_evidence():
    make = DevToolGateway._span
    projection = project_observed_sources(
        [make("src.py", 1, 5, "one\ntwo\nthree\nfour\nfive", "hash")],
        native_spans=[make("src.py", 2, 3, "two\nthree", "hash")],
        priorities=[], editable_paths={"src.py"}, max_chars=3,
    )
    assert projection.source_spans[0]["content"] == "one"
    assert projection.omitted_observed_ranges == ({
        "path": "src.py", "file_hash": "hash", "start_line": 4, "end_line": 5,
    },)
    assert projection.omitted_observed_range_count == 1


def test_public_context_projects_both_read_and_search_outcomes_without_fingerprints(
    source_gateway, monkeypatch
):
    gateway, _, _ = source_gateway
    read = observe(gateway, "src.py", 1, 4)
    monkeypatch.setattr(gateway, "evidence_ledger", lambda **kwargs: {
        "canonical_searches": [{"query": "outdated-search-only"}],
        "recent_inspections": [
            {"tool": "read_file", "path": "src.py", "start_line": 2, "end_line": 3,
             "outcome": "covered_only", "new_covered_line_count": 0,
             "evidence_goal": "Resolve the exact branch.", "result_fingerprint": "OMIT"},
            {"tool": "search_files", "query": "absent", "path_glob": "*.py",
             "outcome": "zero_match", "new_covered_line_count": 0},
        ],
    })
    context = json.loads(_build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=gateway,
        journal=gateway.journal, correction=None, latest_tool_results=[read],
        counters=_RunCounters(), elapsed_seconds=0, limits=gateway.limits,
    ))
    outcomes = context["evidence_ledger"]["recent_inspection_outcomes"]
    assert [row["tool"] for row in outcomes] == ["read_file", "search_files"]
    assert outcomes[0]["start_line"] == 2
    assert outcomes[1]["query"] == "absent"
    assert "canonical_searches" not in context["evidence_ledger"]
    assert "OMIT" not in str(context["evidence_ledger"])
    assert "omitted_observed_ranges" in context["context_projection"]
    assert "omitted_observed_range_count" in context["context_projection"]


def note_call(action_id, update):
    return RequestedTool(
        name="read_file", action_id=action_id,
        arguments={"path": "src.py", "start_line": 1, "end_line": 4},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Continue the public inspection.",
            evidence_goal="Observe a missing source range.", memory_update=update,
        ),
    )


def source_note(statement="The file begins with first.", start=1, end=1):
    return {
        "findings": [{"note_id": None, "statement": statement, "evidence": [{
            "kind": "source", "path": "src.py", "start_line": start, "end_line": end,
        }]}],
        "remove_note_ids": [],
        "open_question": "Which observed branch should change?",
    }


def test_notes_first_nonnull_is_durable_bounded_and_expires_after_source_change(source_gateway):
    gateway, sources, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    first = note_call("a", source_note())
    ignored = note_call("b", source_note("ignored second parallel update"))
    payload = gateway.record_working_notes_update(
        [note_call("null", None), first, ignored], turn_id="turn1"
    )
    assert payload["diagnostics"] == ["ignored_additional_memory_updates"]
    assert len(gateway.working_notes()["findings"]) == 1
    assert gateway.working_notes()["findings"][0]["status"] == "current"
    assert gateway.record_working_notes_update([ignored], turn_id="turn1") == payload
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits,
    )
    restored._tracked_path = tracked
    assert restored.working_notes() == gateway.working_notes()
    assert len([event for event in gateway.journal.events()
                if event["event_type"] == "working_notes_updated"]) == 1
    sources["src.py"] = ("\n".join(f"source line {number}" for number in range(12)) + "\n").encode()
    observe(gateway, "src.py", 1, 12, action_id="expanded-source")
    for number in range(2, 10):
        gateway.record_working_notes_update(
            [note_call(str(number), source_note(f"Public observation {number}", number, number))],
            turn_id=f"turn{number}",
        )
    assert len(gateway.working_notes()["findings"]) == 6
    sources["src.py"] = b"changed\n"
    assert gateway.working_notes()["findings"] == []


def test_source_note_rebinds_unique_unchanged_text_but_expires_ambiguous_text(source_gateway):
    gateway, sources, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update(
        [note_call("a", source_note("The observed branch contains second.", 2, 2))],
        turn_id="turn1",
    )
    sources["src.py"] = b"inserted\nfirst\nsecond\nthird\nfourth\n"
    finding = gateway.working_notes()["findings"][0]
    assert finding["evidence"][0]["start_line"] == 3
    assert finding["evidence"][0]["file_hash"] == sha256_bytes(sources["src.py"])
    observe(gateway, "src.py", 3, 3, action_id="current")
    sources["src.py"] += b"second\n"
    assert gateway.working_notes()["findings"] == []


def test_explicit_note_update_preserves_identity_independent_of_reference_order(source_gateway):
    gateway, _, tracked = source_gateway
    result = observe(gateway, "src.py", 1, 4)
    first = source_note("Initial observation.")
    first["findings"][0]["evidence"].append({"kind": "tool_result", "action_id": result.action_id})
    gateway.record_working_notes_update([note_call("a", first)], turn_id="first")
    original_id = gateway.working_notes()["findings"][0]["note_id"]
    revised = copy.deepcopy(first)
    revised["findings"][0]["statement"] = "More precise public observation."
    revised["findings"][0]["note_id"] = original_id
    revised["findings"][0]["evidence"].reverse()
    gateway.record_working_notes_update([note_call("b", revised)], turn_id="revised")
    notes = gateway.working_notes()
    assert len(notes["findings"]) == 1
    assert notes["findings"][0]["note_id"] == original_id
    assert notes["findings"][0]["statement"] == "More precise public observation."
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits,
    )
    restored._tracked_path = tracked
    assert restored.working_notes() == notes


def test_accepted_mutation_note_binds_current_output_diff_not_preimage_baseline(source_gateway):
    gateway, _, _ = source_gateway
    result = DevToolResult(
        action_id="accepted", input_hash="input", tool="replace_text", status="succeeded",
        output={"worktree_diff_hash": gateway.current_diff_hash},
        workspace_diff_hash="historical-baseline",
    )
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    update = source_note("The preceding exact replacement was accepted.")
    update["findings"][0]["evidence"] = [{"kind": "tool_result", "action_id": "accepted"}]
    gateway.record_working_notes_update([note_call("next", update)], turn_id="next")
    finding = gateway.working_notes()["findings"][0]
    assert finding["evidence"][0]["diff_hash"] == gateway.current_diff_hash
    assert finding["status"] == "current"


def test_bad_notes_are_nonblocking_and_cannot_cite_this_batch_or_hidden_paths(source_gateway):
    gateway, _, _ = source_gateway
    update = source_note()
    invalid = gateway.record_working_notes_update(
        [note_call("not-executed", update)], turn_id="unobserved"
    )
    assert invalid["diagnostics"] == ["unobserved_public_evidence"]
    invalid_shape = gateway.record_working_notes_update(
        [note_call("next", {"raw_reasoning": "PRIVATE_SENTINEL"})], turn_id="badshape"
    )
    assert invalid_shape["diagnostics"] == ["invalid_memory_update_shape"]
    hidden = copy.deepcopy(update)
    hidden["findings"][0]["evidence"][0]["path"] = ".patchloop-hidden/private.py"
    gateway.record_working_notes_update([note_call("hidden", hidden)], turn_id="hidden")
    tool_update = copy.deepcopy(update)
    tool_update["findings"][0]["evidence"] = [{"kind": "tool_result", "action_id": "future"}]
    gateway.record_working_notes_update([note_call("future", tool_update)], turn_id="future")
    assert gateway.working_notes()["findings"] == []
    assert "PRIVATE_SENTINEL" not in gateway.journal.path.read_text()
    assert ".patchloop-hidden/private.py" not in gateway.journal.path.read_text()


def test_note_can_reference_prior_public_failure_without_copying_output(source_gateway):
    gateway, _, _ = source_gateway
    result = DevToolResult(
        action_id="check-before", input_hash="input", tool="run_check", status="succeeded",
        output={"check_id": "visible", "passed": False, "stderr": "PUBLIC_ERROR"},
        workspace_diff_hash=gateway.current_diff_hash,
    )
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    update = source_note("The preceding visible check failed.")
    update["findings"][0]["evidence"] = [{"kind": "tool_result", "action_id": "check-before"}]
    payload = gateway.record_working_notes_update([note_call("next", update)], turn_id="next")
    assert payload["diagnostics"] == []
    assert payload["findings"][0]["evidence"][0]["input_hash"] == "input"
    assert "PUBLIC_ERROR" not in str(gateway.working_notes())


def test_module_traceback_does_not_claim_later_lines_never_ran(source_gateway):
    gateway, _, _ = source_gateway
    source = 'for i in (0, 1):\n    assert i == 0\n    print("later observed")\n'
    check = RegisteredCheck(id="loop", command=["python", "-c", source], timeout_seconds=10)
    failure = gateway._public_check_failure(
        check=check, diff_hash="diff", failure_signature="failure",
        stdout="later observed\n",
        stderr=(
            'Traceback (most recent call last):\n'
            '  File "<string>", line 2, in <module>\nAssertionError\n'
        ),
    )
    assert failure["public_location"]["line"] == 2
    assert failure["execution_boundary"]["later_source_lines_observed"] is None


def test_same_failure_does_not_require_a_new_causal_revision(source_gateway):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    for diff_hash in ("first", "second"):
        gateway._remember_check({
            "check_id": "public", "diff_hash": diff_hash,
            "passed": False, "failure_signature": "same",
        })
    assert gateway.requires_alternative is True
    validated = gateway._validate_replacement_intent(replacement("second"))
    assert validated.intent.causal_revision is None
