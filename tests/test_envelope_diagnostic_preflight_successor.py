from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import envelope_diagnostic_preflight_successor as successor

REPOSITORY = Path(__file__).resolve().parents[1]
SENTINEL_A = "sk-v21-sentinel-short"
SENTINEL_B = "sk-v21-sentinel-with-a-different-length-must-not-affect-fixture"


@pytest.fixture(scope="module")
def contract() -> successor.EnvelopeDiagnosticContract:
    return successor._build_contract(REPOSITORY)


def _channel() -> Any:
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as channel

    return channel


def test_contract_binds_consumed_v20_without_inventing_cause(
    contract: successor.EnvelopeDiagnosticContract,
) -> None:
    predecessor = contract.predecessor
    assert predecessor.source_commit == successor.V20_SOURCE_COMMIT
    assert predecessor.source_tree == successor.V20_SOURCE_TREE
    assert predecessor.evidence_commit == successor.V20_EVIDENCE_COMMIT
    assert predecessor.base_child_code == "child_output_invalid"
    assert predecessor.supervisor_code == "supervised_output_invalid"
    assert predecessor.envelope_received is False
    assert predecessor.outer_launch_attempt_count == 1
    assert predecessor.outer_process_return_count == 1
    assert predecessor.outer_result_message_nonempty_count == 1
    assert predecessor.outer_returncode == 0
    assert predecessor.worker_launch_attempt_count is None
    assert predecessor.activity_accounting_complete is False
    assert predecessor.unknown_post_marker_activity_possible is True
    assert predecessor.partial_write_proven_as_cause is False
    assert predecessor.retry_or_resume_allowed is False


def test_contract_is_source_only_and_fixture_only(
    contract: successor.EnvelopeDiagnosticContract,
) -> None:
    assert contract.correction_scope == "two-hop-complete-write-and-typed-decode-stage-only"
    assert contract.predecessor_retry_or_repair is False
    assert contract.predecessor_root_cause_established is False
    assert contract.readiness_or_sdk_result_created is False
    assert contract.execution_currently_authorized is False
    assert contract.runtime.offline_fixed_public_fixture_only is True
    assert contract.runtime.live_diagnostic_default_exposed is False
    assert contract.runtime.activation_runtime_exposed is False
    assert contract.authority.offline_fixed_fixture_process_launch_limit == 2
    assert contract.authority.state_approval_attempt_or_terminal_creation_authorized is False
    assert contract.authority.docker_dotenv_sdk_network_or_provider_observation_authorized is False


def test_channel_top_level_imports_are_stdlib_only() -> None:
    tree = ast.parse((REPOSITORY / successor.SUPERVISOR_PATH).read_text(encoding="utf-8"))
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {alias.name.split(".", 1)[0] for node in imports for alias in node.names}
    assert "patchloop" not in imported
    assert "openai" not in imported
    assert "httpx" not in imported
    assert "dotenv" not in imported


def test_write_all_retries_short_writes() -> None:
    channel = _channel()
    expected = b"complete-write-must-survive-short-writes"
    written = bytearray()

    def short_writer(_descriptor: int, value: bytes | memoryview) -> int:
        chunk = bytes(value)[:3]
        written.extend(chunk)
        return len(chunk)

    assert channel._write_all(7, expected, write=short_writer) is None
    assert bytes(written) == expected


@pytest.mark.parametrize("mode", ["zero", "oversize"])
def test_write_all_nonprogress_or_impossible_progress_fails(mode: str) -> None:
    channel = _channel()

    def invalid_writer(_descriptor: int, value: bytes | memoryview) -> int:
        return 0 if mode == "zero" else len(value) + 1

    with pytest.raises(Exception) as caught:
        channel._write_all(7, b"abc", write=invalid_writer)
    message = str(caught.value).lower()
    assert SENTINEL_A not in message
    assert "abc" not in message


def test_write_all_retries_interrupted_error() -> None:
    channel = _channel()
    calls = 0
    written = bytearray()

    def writer(_descriptor: int, value: bytes | memoryview) -> int:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise InterruptedError
        chunk = bytes(value)
        written.extend(chunk)
        return len(chunk)

    channel._write_all(7, b"safe", write=writer)
    assert bytes(written) == b"safe"


def test_frame_decode_stage_matrix_has_no_invalid_raw_metadata() -> None:
    channel = _channel()
    valid = channel.encode_frame(channel.fixed_worker_fixture())
    header_length = channel.FRAME_HEADER_BYTES

    def framed(body: bytes) -> bytes:
        return len(body).to_bytes(4, "big") + hashlib.sha256(body).digest() + body

    cases = {
        "no_message": b"",
        "header_invalid": b"x",
        "frame_length_invalid": valid[:-1],
        "digest_invalid": valid[:header_length]
        + bytes([valid[header_length] ^ 1])
        + valid[header_length + 1 :],
        "utf8_invalid": framed(b"\xff"),
        "json_invalid": framed(b"{"),
        "object_invalid": framed(b"[]"),
    }
    for expected, raw in cases.items():
        result = channel.decode_worker_frame(raw)
        assert result.stage == expected
        assert result.value is None
        dumped = repr(result)
        assert "sha256:" not in dumped
        assert SENTINEL_A not in dumped
    decoded = channel.decode_worker_frame(valid)
    assert decoded.stage == "valid"
    assert decoded.value == channel.fixed_worker_fixture()


def test_frame_semantic_stage_is_separate_from_wire_schema() -> None:
    channel = _channel()
    value = channel.fixed_worker_fixture()
    contradictory = {**value, "raw_output_returned": True}
    decoded = channel.decode_worker_frame(channel.encode_frame(contradictory))
    assert decoded.stage == "semantic_invalid"
    assert decoded.value is None


def test_fixed_fixture_has_zero_external_activity_and_no_secret_fields() -> None:
    channel = _channel()
    fixture = channel.fixed_worker_fixture()
    serialized = json.dumps(fixture, sort_keys=True)
    assert fixture["fixture_id"] == "v21-public-fixed-placeholder-no-dispatch"
    activity = fixture["activity"]
    assert activity["dotenv_read_count"] == 0
    assert activity["sdk_import_count"] == 0
    assert activity["transport_dispatch_count"] == 0
    assert activity["network_call_count"] == 0
    assert activity["provider_evaluator_agent_call_count"] == 0
    assert activity["credential_value_read_count"] == 0
    assert SENTINEL_A not in serialized
    assert SENTINEL_B not in serialized


def test_real_nested_fixed_fixture_chain_uses_two_process_hops() -> None:
    evidence = successor.run_offline_fixed_fixture_chain(repository=REPOSITORY)
    assert evidence.parent_supervisor_launch_attempt_count == 1
    assert evidence.parent_supervisor_process_return_count == 1
    assert evidence.parent_supervisor_frame_stage == "valid"
    assert evidence.supervisor_worker_launch_attempt_count == 1
    assert evidence.supervisor_worker_process_return_count == 1
    assert evidence.supervisor_worker_frame_stage == "valid"
    assert evidence.complete_framed_message_received_on_both_hops is True
    assert evidence.fixture_protocol_accounting_complete is True
    assert evidence.process_external_activity_absence_proven is False
    assert evidence.passed is True


def test_real_chain_is_ambient_secret_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL_A)
    first = successor.run_offline_fixed_fixture_chain(repository=REPOSITORY)
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL_B)
    second = successor.run_offline_fixed_fixture_chain(repository=REPOSITORY)
    assert first == second
    raw = first.model_dump_json()
    assert SENTINEL_A not in raw and SENTINEL_B not in raw


def test_source_additions_do_not_include_dirty_index() -> None:
    assert "docs/00-index.md" not in successor.SOURCE_ADDED_PATHS
    assert tuple(sorted(successor.SOURCE_ADDED_PATHS)) == successor.SOURCE_ADDED_PATHS


def test_noncanonical_duplicate_and_bool_counter_frames_are_rejected() -> None:
    channel = _channel()
    fixture = channel.fixed_worker_fixture()
    noncanonical = json.dumps(fixture, indent=2).encode("utf-8")
    frame = (
        len(noncanonical).to_bytes(4, "big") + hashlib.sha256(noncanonical).digest() + noncanonical
    )
    assert channel.decode_worker_frame(frame).stage == "schema_invalid"

    canonical = json.dumps(fixture, sort_keys=True, separators=(",", ":"))
    duplicate = (
        canonical.replace(
            '"fixture_id":"v21-public-fixed-placeholder-no-dispatch"',
            '"fixture_id":"v21-public-fixed-placeholder-no-dispatch",'
            '"fixture_id":"v21-public-fixed-placeholder-no-dispatch"',
            1,
        ).encode("utf-8")
        + b"\n"
    )
    frame = len(duplicate).to_bytes(4, "big") + hashlib.sha256(duplicate).digest() + duplicate
    assert channel.decode_worker_frame(frame).stage == "json_invalid"

    fixture["activity"]["network_call_count"] = False
    assert channel.decode_worker_frame(channel.encode_frame(fixture)).stage == "semantic_invalid"

    supervisor = channel.build_supervisor_envelope(
        worker_runner=lambda: channel.WorkerProcessOutcome(
            launch_attempt_count=1,
            process_return_count=1,
            returncode=0,
            frame=channel.FrameDecodeResult(
                channel.FrameStage.VALID, channel.fixed_worker_fixture()
            ),
            activity_accounting_complete=True,
            unknown_process_activity_possible=False,
        )
    )
    supervisor["activity"]["worker_launch_attempt_count"] = True
    assert channel.decode_supervisor_frame(channel.encode_frame(supervisor)).stage == (
        "semantic_invalid"
    )

    supervisor = channel.build_supervisor_envelope(
        worker_runner=lambda: channel.WorkerProcessOutcome(
            launch_attempt_count=1,
            process_return_count=1,
            returncode=0,
            frame=channel.FrameDecodeResult(channel.FrameStage.HEADER_INVALID),
            activity_accounting_complete=False,
            unknown_process_activity_possible=True,
        )
    )
    assert supervisor["code"] == "worker_frame_invalid"
    supervisor["code"] = "worker_nonzero_exit"
    assert channel.decode_supervisor_frame(channel.encode_frame(supervisor)).stage == (
        "semantic_invalid"
    )


def test_public_fixture_runner_rejects_dirty_supervisor_binding(
    contract: successor.EnvelopeDiagnosticContract, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(successor, "load_contract", lambda **_kwargs: contract)
    monkeypatch.setattr(successor, "sha256_bytes", lambda _value: "sha256:" + "0" * 64)
    monkeypatch.setattr(
        successor,
        "_run_fixture_supervisor_process",
        lambda _root: pytest.fail("unbound fixture process must not launch"),
    )
    with pytest.raises(successor.EnvelopeDiagnosticError):
        successor.run_offline_fixed_fixture_chain(repository=REPOSITORY)


def test_checked_in_source_qualification_when_present() -> None:
    if not (REPOSITORY / successor.QUALIFICATION_PATH).exists():
        pytest.skip("qualification is created only after the exact source commit")
    summary = successor.validate_source_qualification(repository=REPOSITORY)
    assert summary["offline_fixed_fixture_process_launch_count"] == 2
    assert summary["external_observations_made"] == 0
    assert summary["external_mutations_made"] == 0
    assert summary["execution_authorized"] is False
