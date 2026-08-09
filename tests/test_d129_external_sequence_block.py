from __future__ import annotations

import copy
import inspect
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import d129_external_sequence_block as d129
from patchloop.util import canonical_json, sha256_bytes

GATE_RECORDED_AT = "2026-08-09T00:00:00Z"
RECEIPT_RECORDED_AT = "2026-08-09T00:00:01Z"
TERMINAL_RECORDED_AT = "2026-08-09T00:00:02Z"
SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
RECEIPT_COMMIT = "c" * 40
RECEIPT_TREE = "d" * 40
TERMINAL_COMMIT = "e" * 40
TERMINAL_TREE = "f" * 40
SECRET = "d129-sequence-block-secret-must-never-be-rendered"


def _gate_binding() -> dict[str, Any]:
    return {
        "path": d129.D129_GATE_PATH.as_posix(),
        "gate_id": d129.D129_GATE_ID,
        "semantic_body_hash": d129.D129_GATE_BODY_SHA256,
        "file_sha256": d129.D129_GATE_FILE_SHA256,
        "file_bytes": d129.D129_GATE_FILE_BYTES,
        "status": d129.D129_GATE_STATUS,
        "recorded_at": GATE_RECORDED_AT,
        "evidence_commit": d129.D129_EVIDENCE_COMMIT,
        "evidence_tree": d129.D129_EVIDENCE_TREE,
        "evidence_parent": d129.D129_EVIDENCE_PARENT,
        "blob_oid": d129.D129_GATE_BLOB_OID,
        "artifact_mutated": False,
    }


def _source_identity() -> dict[str, Any]:
    return {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d129.D129_EVIDENCE_COMMIT],
        "source_paths_added": [path.as_posix() for path in d129.SOURCE_PATHS],
        "module_bindings": [],
        "loaded_module_bindings": [],
        "python_routing_env_presence": {"PYTHONHOME": False, "PYTHONPATH": False},
        "worktree_and_index_clean_before_receipt": True,
        "git_cli_observation": {},
        "git_identity_vendor_authenticated_or_signed": False,
    }


def _receipt_commit_binding(root: Path) -> dict[str, Any]:
    raw = (root / d129.RECEIPT_PATH).read_bytes()
    return {
        "commit": RECEIPT_COMMIT,
        "tree": RECEIPT_TREE,
        "parents": [SOURCE_COMMIT],
        "receipt_path": d129.RECEIPT_PATH.as_posix(),
        "receipt_blob_oid": "1" * 40,
        "receipt_file_sha256": sha256_bytes(raw),
        "receipt_file_bytes": len(raw),
        "receipt_only_add_commit": True,
    }


def _rewrite_envelope(
    path: Path,
    *,
    schema: str,
    prefix: str,
    mutate: Any,
) -> bytes:
    payload = json.loads(path.read_bytes())
    mutate(payload["semantic_body"])
    raw = d129._pretty_bytes(d129._envelope(schema, prefix, payload["semantic_body"]))
    path.write_bytes(raw)
    return raw


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "repository"
    (root / d129.RECEIPT_PATH.parent).mkdir(parents=True)
    source = _source_identity()
    state: dict[str, Any] = {
        "source": source,
        "gate": _gate_binding(),
        "times": iter((RECEIPT_RECORDED_AT, TERMINAL_RECORDED_AT)),
        "writes": [],
    }

    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setattr(d129, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d129, "_now", lambda: next(state["times"]))
    monkeypatch.setattr(d129, "_gate_binding", lambda _root: copy.deepcopy(state["gate"]))
    monkeypatch.setattr(
        d129,
        "_source_identity_for_receipt",
        lambda _root: copy.deepcopy(state["source"]),
    )

    def validate_source(_root: Path, value: Any) -> None:
        assert canonical_json(value) == canonical_json(state["source"])

    monkeypatch.setattr(d129, "_validate_source_identity", validate_source)

    real_write = d129._write_new

    def write_new(selected_root: Path, relative: Path, raw: bytes) -> None:
        state["writes"].append(relative)
        real_write(selected_root, relative, raw)

    monkeypatch.setattr(d129, "_write_new", write_new)
    monkeypatch.setattr(
        d129,
        "_receipt_commit_binding",
        lambda selected_root, _source, _raw: _receipt_commit_binding(selected_root),
    )

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        if commit == RECEIPT_COMMIT:
            return {"commit": commit, "tree": RECEIPT_TREE, "parents": [SOURCE_COMMIT]}
        if commit == TERMINAL_COMMIT:
            return {"commit": commit, "tree": TERMINAL_TREE, "parents": [RECEIPT_COMMIT]}
        raise AssertionError(f"unexpected commit identity: {commit}")

    monkeypatch.setattr(d129, "_commit_identity", commit_identity)
    monkeypatch.setattr(
        d129,
        "_diff_rows",
        lambda _root, commit: (
            [{"status": "A", "path": d129.RECEIPT_PATH.as_posix()}]
            if commit == RECEIPT_COMMIT
            else pytest.fail(f"unexpected diff commit: {commit}")
        ),
    )

    def commit_blob(_root: Path, commit: str, path: Path) -> tuple[str, bytes]:
        assert commit == RECEIPT_COMMIT and path == d129.RECEIPT_PATH
        return "1" * 40, (root / d129.RECEIPT_PATH).read_bytes()

    monkeypatch.setattr(d129, "_commit_blob", commit_blob)
    return root, state


def _create_and_record(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = d129.create_d129_approval_receipt(repository=root)
    terminal = d129.record_d129_sequence_block_terminal(repository=root)
    return receipt, terminal


def test_receipt_binds_exact_gate_scope_event_order_and_pre_receipt_activity(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository

    assert d129.D129_GATE_ID == (
        "d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
    )
    assert d129.D129_GATE_BODY_SHA256 == (
        "sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c"
    )
    assert d129.D129_GATE_FILE_SHA256 == (
        "sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512"
    )
    assert d129.D129_GATE_FILE_BYTES == 18_678
    assert d129.D129_EVIDENCE_COMMIT == "70f9955dca8d873f91d622505f7afe7f3cfec59e"
    assert d129.D129_EVIDENCE_TREE == "ad9e348284c1161f258ef7e20ea7cc63cd55399d"
    assert d129.D129_EVIDENCE_PARENT == "1fef6716cddca571777c8b7f9f1dc4501f988d1c"
    assert d129.D129_GATE_BLOB_OID == "5ccf4a0e4ddaf7b4096186bc960035fdb76f337e"

    first = d129.create_d129_approval_receipt(repository=root)
    raw = (root / d129.RECEIPT_PATH).read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]
    second = d129.create_d129_approval_receipt(repository=root)

    assert first == second
    assert state["writes"] == [d129.RECEIPT_PATH]
    assert raw == (root / d129.RECEIPT_PATH).read_bytes() == d129._pretty_bytes(payload)
    assert body["predecessor_binding"] == _gate_binding()
    assert body["source_identity"] == _source_identity()
    assert body["approval_binding"]["approved_scope"] == list(d129.APPROVED_SCOPE)
    assert body["approval_binding"]["not_authorized"] == list(d129.NOT_AUTHORIZED)
    assert body["event_order"] == [
        {"ordinal": 1, "event": "exact-user-approval-received"},
        {"ordinal": 2, "event": "official-docs-tool-open-observed"},
        {"ordinal": 3, "event": "corrective-source-committed"},
        {"ordinal": 4, "event": "approval-receipt-recorded"},
    ]
    assert body["pre_receipt_activity"] == {
        "activity_kind": "public-official-documentation-tool-open",
        "official_url": "https://developers.openai.com/api/docs/pricing",
        "agent_visible_web_tool_open_invocation_count": 1,
        "underlying_http_request_or_redirect_count": "unknown",
        "agent_supplied_openai_api_key_or_explicit_authentication": False,
        "agent_supplied_cookie": False,
        "underlying_tool_cookie_service_auth_or_header_state": "unknown",
        "provider_response_api_call_count": 0,
        "canonical_pricing_capture_get_count": 0,
        "canonical_pricing_evidence_artifact_created": False,
        "canonical_replayable_entity_retained": False,
        "canonical_retained_entity_bytes": 0,
        "canonical_retained_entity_sha256": None,
        "web_tool_returned_content_bytes": "unknown",
        "used_as_pricing_evidence": False,
        "exact_lookup_timestamp_retained": False,
    }
    assert first["pre_receipt_official_docs_web_tool_open_invocation_count"] == 1
    assert first["canonical_pricing_capture_get_count"] == 0
    assert first["external_phase_attempt_created"] is False
    assert SECRET.encode() not in raw


def test_terminal_consumes_receipt_and_is_canonical_idempotent_without_external_phase(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    receipt, first = _create_and_record(root)
    raw = (root / d129.TERMINAL_PATH).read_bytes()
    payload = json.loads(raw)
    body = payload["semantic_body"]
    second = d129.record_d129_sequence_block_terminal(repository=root)

    assert first == second
    assert state["writes"] == [d129.RECEIPT_PATH, d129.TERMINAL_PATH]
    assert raw == (root / d129.TERMINAL_PATH).read_bytes() == d129._pretty_bytes(payload)
    assert first["status"] == d129.TERMINAL_STATUS
    assert first["receipt_artifact_id"] == receipt["artifact_id"]
    assert first["receipt_consumed"] is True
    assert body["sequence_block"]["observed_blockers"] == [d129.TERMINAL_BLOCKER]
    assert body["sequence_block"]["passed"] is False
    assert body["sequence_block"]["all_external_activity_was_attempt_first"] is False
    assert body["sequence_block"]["attempt_artifact_created"] is False
    assert body["sequence_block"]["no_attempt_retroactively_created"] is True
    assert body["next_gate"] == {
        "action": "prepare-separate-d130-offline-successor-gate",
        "requires_new_exact_user_approval_after-d130": True,
        "this_d129_receipt_is_consumed": True,
        "does_not_authorize_external_retry_resume_repair_or_execution": True,
    }


def test_activity_accounting_separates_visible_lookup_from_unknown_http_and_canonical_capture(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    _create_and_record(root)
    body = json.loads((root / d129.TERMINAL_PATH).read_bytes())["semantic_body"]
    activity = body["activity_accounting"]
    pre = activity["pre_receipt_official_docs_activity"]

    assert pre["agent_visible_web_tool_open_invocation_count"] == 1
    assert pre["underlying_http_request_or_redirect_count"] == "unknown"
    assert pre["official_url"] == d129.OFFICIAL_DOCS_URL
    assert pre["agent_supplied_openai_api_key_or_explicit_authentication"] is False
    assert pre["agent_supplied_cookie"] is False
    assert pre["underlying_tool_cookie_service_auth_or_header_state"] == "unknown"
    assert pre["provider_response_api_call_count"] == 0
    assert pre["canonical_pricing_capture_get_count"] == 0
    assert pre["canonical_replayable_entity_retained"] is False
    assert pre["canonical_retained_entity_bytes"] == 0
    assert pre["canonical_retained_entity_sha256"] is None
    assert pre["web_tool_returned_content_bytes"] == "unknown"
    assert activity["post_receipt_canonical_pricing_capture_get_count"] == 0
    assert activity["canonical_pricing_capture_attempted"] is False
    assert activity["canonical_pricing_artifact_created"] is False


def test_all_docker_sdk_provider_memory_execution_and_cost_authority_remains_zero(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    _create_and_record(root)

    for relative in (d129.RECEIPT_PATH, d129.TERMINAL_PATH):
        body = json.loads((root / relative).read_bytes())["semantic_body"]
        authority = body["authority"]
        for key, value in authority.items():
            if key.endswith("_count"):
                assert value == 0, key
        assert authority["d129_external_phase_attempt_created"] is False
        assert authority["d129_execution_hash_created"] is False
        assert authority["d129_execution_candidate_created"] is False
        assert authority["d129_cost_reserved_or_spent_usd"] == "0"
        assert authority["d129_four_row_ac_execution_authorized"] is False

    terminal = json.loads((root / d129.TERMINAL_PATH).read_bytes())["semantic_body"]
    assert terminal["activity_accounting"]["post_receipt_docker_cli_or_daemon_call_count"] == 0
    assert terminal["activity_accounting"]["post_receipt_image_pull_or_load_count"] == 0
    assert terminal["activity_accounting"]["post_receipt_sdk_probe_count"] == 0
    assert (
        terminal["activity_accounting"]["post_receipt_provider_evaluator_or_agent_call_count"] == 0
    )
    assert terminal["authority"]["d129_receipt_consumed"] is True
    assert terminal["authority"]["d129_environment_ready"] is False


def test_receipt_collision_or_forbidden_descendant_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collision = tmp_path / "collision"
    (collision / d129.RECEIPT_PATH.parent).mkdir(parents=True)
    original = b"preexisting-noncanonical-receipt"
    (collision / d129.RECEIPT_PATH).write_bytes(original)
    monkeypatch.setattr(d129, "_gate_binding", lambda _root: _gate_binding())
    monkeypatch.setattr(d129, "_assert_runtime_import_boundary", lambda _root: None)

    with pytest.raises(d129.D129ExternalSequenceBlockError):
        d129.create_d129_approval_receipt(repository=collision)
    assert (collision / d129.RECEIPT_PATH).read_bytes() == original

    forbidden = tmp_path / "forbidden"
    (forbidden / d129.RECEIPT_PATH.parent).mkdir(parents=True)
    orphan_path = d129.FORBIDDEN_DESCENDANT_PATHS[0]
    orphan = b"forbidden-preexisting-attempt"
    (forbidden / orphan_path).write_bytes(orphan)
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="unexpected artifact"):
        d129.create_d129_approval_receipt(repository=forbidden)
    assert (forbidden / orphan_path).read_bytes() == orphan
    assert not (forbidden / d129.RECEIPT_PATH).exists()

    unsafe = tmp_path / "unsafe"
    (unsafe / d129.RECEIPT_PATH.parent).mkdir(parents=True)
    target = unsafe / d129.RECEIPT_PATH
    target.write_bytes(b"linklike-target-must-be-preserved")
    monkeypatch.setattr(d129.d129, "_is_linklike", lambda path: path == target)
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="linklike"):
        d129._write_new(unsafe, d129.RECEIPT_PATH, b"replacement")
    assert target.read_bytes() == b"linklike-target-must-be-preserved"

    parent_unsafe = tmp_path / "parent-unsafe"
    (parent_unsafe / d129.TERMINAL_PATH.parent).mkdir(parents=True)
    unsafe_parent = parent_unsafe / "reports" / "live-pilot"
    monkeypatch.setattr(d129.d129, "_is_linklike", lambda path: path == unsafe_parent)
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="parent is unsafe"):
        d129._write_new(parent_unsafe, d129.TERMINAL_PATH, b"new")
    assert not (parent_unsafe / d129.TERMINAL_PATH).exists()

    cleanup = tmp_path / "cleanup"
    (cleanup / d129.TERMINAL_PATH.parent).mkdir(parents=True)
    monkeypatch.setattr(d129.d129, "_is_linklike", lambda _path: False)
    monkeypatch.setattr(
        d129.os,
        "link",
        lambda *_args: (_ for _ in ()).throw(OSError("forced publication failure")),
    )
    with pytest.raises(OSError, match="forced publication failure"):
        d129._write_new(cleanup, d129.TERMINAL_PATH, b"never-published")
    assert not (cleanup / d129.TERMINAL_PATH).exists()
    assert not list((cleanup / d129.TERMINAL_PATH.parent).glob(".*.tmp"))


def test_terminal_requires_receipt_only_commit_and_preserves_orphaned_terminal(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _state = repository
    d129.create_d129_approval_receipt(repository=root)
    monkeypatch.setattr(
        d129,
        "_receipt_commit_binding",
        lambda *_args: (_ for _ in ()).throw(
            d129.D129ExternalSequenceBlockError("receipt commit is not receipt-only")
        ),
    )
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="not receipt-only"):
        d129.record_d129_sequence_block_terminal(repository=root)
    assert not (root / d129.TERMINAL_PATH).exists()

    orphan_root = root.parent / "orphan-terminal"
    (orphan_root / d129.TERMINAL_PATH.parent).mkdir(parents=True)
    orphan = b"orphaned-terminal"
    (orphan_root / d129.TERMINAL_PATH).write_bytes(orphan)
    with pytest.raises(d129.D129ExternalSequenceBlockError):
        d129.record_d129_sequence_block_terminal(repository=orphan_root)
    assert (orphan_root / d129.TERMINAL_PATH).read_bytes() == orphan


def test_source_commit_must_be_clean_exact_sole_child_of_d129_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    real_python_routing = d129._python_routing_env_presence
    real_loaded_modules = d129._loaded_module_bindings
    expected_diff = [{"status": "A", "path": path.as_posix()} for path in d129.SOURCE_PATHS]
    monkeypatch.setattr(d129, "_status_lines", lambda _root: [])
    monkeypatch.setattr(d129, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d129, "_head", lambda _root: SOURCE_COMMIT)
    monkeypatch.setattr(
        d129,
        "_commit_identity",
        lambda _root, _commit: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [d129.D129_EVIDENCE_COMMIT],
        },
    )
    monkeypatch.setattr(d129, "_diff_rows", lambda _root, _commit: expected_diff)
    monkeypatch.setattr(
        d129,
        "_binding_for_path",
        lambda _root, _commit, path: {"path": path.as_posix()},
    )
    monkeypatch.setattr(d129, "_python_routing_env_presence", lambda: {})
    monkeypatch.setattr(d129, "_loaded_module_bindings", lambda _root, _commit: [])
    monkeypatch.setattr(d129.d129, "_git_cli_observation", lambda _root: {})

    source = d129._source_identity_for_receipt(root)
    assert source["parents"] == [d129.D129_EVIDENCE_COMMIT]
    assert source["source_paths_added"] == [path.as_posix() for path in d129.SOURCE_PATHS]

    monkeypatch.setattr(
        d129,
        "_commit_identity",
        lambda _root, _commit: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": ["0" * 40],
        },
    )
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="source parent"):
        d129._source_identity_for_receipt(root)

    monkeypatch.setattr(
        d129,
        "_commit_identity",
        lambda _root, _commit: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [d129.D129_EVIDENCE_COMMIT],
        },
    )
    monkeypatch.setattr(
        d129,
        "_diff_rows",
        lambda _root, _commit: [*expected_diff, {"status": "M", "path": "unrelated.txt"}],
    )
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="source commit scope"):
        d129._source_identity_for_receipt(root)

    monkeypatch.setattr(d129, "_python_routing_env_presence", real_python_routing)
    for name in d129.PYTHON_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHONPATH", "hostile-import-routing")
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="import routing"):
        d129._python_routing_env_presence()

    monkeypatch.delenv("PYTHONPATH")
    monkeypatch.setattr(d129, "_loaded_module_bindings", real_loaded_modules)
    outside = tmp_path / "outside-loaded-module.py"
    outside.write_text("# outside repository\n", encoding="utf-8")
    _relative, module_name = d129.LOADED_MODULE_PATHS[0]
    module = sys.modules[module_name]
    monkeypatch.setattr(module, "__file__", str(outside))
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="outside repository"):
        d129._loaded_module_bindings(Path(__file__).resolve().parents[1], SOURCE_COMMIT)


def test_fully_rehashed_nested_receipt_tamper_is_rejected_without_repair(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    d129.create_d129_approval_receipt(repository=root)
    path = root / d129.RECEIPT_PATH
    original = path.read_bytes()
    mutations = (
        lambda body: body["event_order"][1].update({"ordinal": 3}),
        lambda body: body["pre_receipt_activity"].update(
            {"underlying_http_request_or_redirect_count": 1}
        ),
        lambda body: body["pre_receipt_activity"].update({"used_as_pricing_evidence": True}),
        lambda body: body["approval_binding"].update(
            {"receipt_preceded_official_docs_lookup": True}
        ),
        lambda body: body["authority"].update({"d129_sdk_probe_count": 1}),
    )

    for mutate in mutations:
        path.write_bytes(original)
        tampered = _rewrite_envelope(
            path,
            schema=d129.RECEIPT_SCHEMA,
            prefix="d129approval",
            mutate=mutate,
        )
        with pytest.raises(d129.D129ExternalSequenceBlockError, match="full rebuild"):
            d129.validate_d129_sequence_block(repository=root, mode="receipt")
        assert path.read_bytes() == tampered


def test_fully_rehashed_nested_terminal_tamper_is_rejected_without_repair(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    _create_and_record(root)
    path = root / d129.TERMINAL_PATH
    original = path.read_bytes()
    mutations = (
        (
            lambda body: body["sequence_block"].update(
                {"all_external_activity_was_attempt_first": True}
            ),
            "full rebuild",
        ),
        (
            lambda body: body["sequence_block"].update({"attempt_artifact_created": True}),
            "full rebuild",
        ),
        (
            lambda body: body["activity_accounting"].update(
                {"post_receipt_canonical_pricing_capture_get_count": 1}
            ),
            "full rebuild",
        ),
        (
            lambda body: body["evidence_boundary"].update(
                {"lookup_is_not_used_as_replayable_pricing_evidence": False}
            ),
            "full rebuild",
        ),
        (
            lambda body: body["next_gate"].update({"this_d129_receipt_is_consumed": False}),
            "full rebuild",
        ),
        (
            lambda body: body["receipt_commit_binding"].update({"unexpected": False}),
            "receipt commit binding fields",
        ),
        (
            lambda body: body["receipt_commit_binding"].update({"receipt_path": False}),
            "receipt commit binding differs",
        ),
    )

    for mutate, match in mutations:
        path.write_bytes(original)
        tampered = _rewrite_envelope(
            path,
            schema=d129.TERMINAL_SCHEMA,
            prefix="d129sequenceblock",
            mutate=mutate,
        )
        with pytest.raises(d129.D129ExternalSequenceBlockError, match=match):
            d129.validate_d129_sequence_block(repository=root, mode="terminal")
        assert path.read_bytes() == tampered


def test_chronology_inversion_is_rejected_without_inventing_lookup_timestamp(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    d129.create_d129_approval_receipt(repository=root)
    receipt_path = root / d129.RECEIPT_PATH
    _rewrite_envelope(
        receipt_path,
        schema=d129.RECEIPT_SCHEMA,
        prefix="d129approval",
        mutate=lambda body: body.update({"recorded_at": GATE_RECORDED_AT}),
    )
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="receipt chronology"):
        d129.validate_d129_sequence_block(repository=root, mode="receipt")

    assert d129._pre_receipt_activity()["exact_lookup_timestamp_retained"] is False
    assert [row["ordinal"] for row in d129._receipt_event_order()] == [1, 2, 3, 4]


def test_post_evidence_commit_is_terminal_plus_active_docs_only_and_clean(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _state = repository
    _create_and_record(root)
    terminal, raw = d129._read_json(root, d129.TERMINAL_PATH)
    expected = [
        {"status": "A", "path": d129.TERMINAL_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in d129.ACTIVE_DOC_PATHS),
    ]
    monkeypatch.setattr(d129, "_status_lines", lambda _root: [])
    monkeypatch.setattr(d129, "_head", lambda _root: TERMINAL_COMMIT)
    monkeypatch.setattr(
        d129,
        "_commit_identity",
        lambda _root, commit: {
            "commit": commit,
            "tree": TERMINAL_TREE,
            "parents": [RECEIPT_COMMIT],
        },
    )
    monkeypatch.setattr(d129, "_diff_rows", lambda _root, _commit: expected)
    monkeypatch.setattr(
        d129,
        "_commit_blob",
        lambda _root, _commit, path: (
            ("2" * 40, raw) if path == d129.TERMINAL_PATH else pytest.fail(path)
        ),
    )

    assert d129._validate_post_evidence_checkout(root, terminal, raw) == TERMINAL_COMMIT

    monkeypatch.setattr(
        d129,
        "_diff_rows",
        lambda _root, _commit: [*expected, {"status": "M", "path": "patchloop/agent/model.py"}],
    )
    with pytest.raises(d129.D129ExternalSequenceBlockError, match="evidence commit scope"):
        d129._validate_post_evidence_checkout(root, terminal, raw)


def test_validation_is_read_only_secret_safe_and_public_surface_has_no_external_runner(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, _state = repository
    _create_and_record(root)
    before = {path: (root / path).read_bytes() for path in (d129.RECEIPT_PATH, d129.TERMINAL_PATH)}

    receipt = d129.validate_d129_sequence_block(repository=root, mode="receipt")
    terminal = d129.validate_d129_sequence_block(repository=root, mode="terminal")

    assert receipt["status"] == d129.RECEIPT_STATUS
    assert terminal["status"] == d129.TERMINAL_STATUS
    assert before == {
        path: (root / path).read_bytes() for path in (d129.RECEIPT_PATH, d129.TERMINAL_PATH)
    }
    assert all(SECRET.encode() not in raw for raw in before.values())
    assert tuple(inspect.signature(d129.create_d129_approval_receipt).parameters) == ("repository",)
    assert tuple(inspect.signature(d129.record_d129_sequence_block_terminal).parameters) == (
        "repository",
    )
    assert set(d129.__all__) == {
        "D129ExternalSequenceBlockError",
        "RECEIPT_PATH",
        "RECEIPT_SCHEMA",
        "RECEIPT_STATUS",
        "TERMINAL_PATH",
        "TERMINAL_SCHEMA",
        "TERMINAL_STATUS",
        "create_d129_approval_receipt",
        "record_d129_sequence_block_terminal",
        "validate_d129_sequence_block",
    }
    source = inspect.getsource(d129)
    for forbidden in (
        "import httpx",
        "import openai",
        "import socket",
        "import subprocess",
        "load_dotenv",
        "dotenv_values",
        "OPENAI_API_KEY",
        "run_d129_external_no_call_preflight",
        "capture_official_pricing_evidence(",
        "remediate_already_running_docker_environment(",
    ):
        assert forbidden not in source
    script = (Path(__file__).resolve().parents[1] / d129.SOURCE_PATHS[1]).read_text(
        encoding="utf-8"
    )

    for required in (
        "--create-receipt",
        "--record-procedural-terminal",
        "--validate-receipt",
        "--validate-terminal",
        "--validate-post-commit",
    ):
        assert required in script
    for forbidden in (
        "--run-external",
        "--pull",
        "--capture-pricing",
        "--sdk-preflight",
        "--create-attempt",
    ):
        assert forbidden not in script
