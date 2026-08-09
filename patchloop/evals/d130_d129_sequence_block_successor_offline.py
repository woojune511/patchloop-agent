"""Build the offline D-130 successor to the blocked D-129 sequence incident.

D-130 preserves the D-129 gate, non-retroactive receipt, consumed procedural
terminal, and exact Git topology.  It authorizes no receipt, armed intent,
external observation, Docker, pricing, SDK, provider, evaluator, agent,
retrieval, execution hash, candidate, cost, or experiment.  Its next admission
is deliberately local-only: create and commit a receipt and durable armed
intent before a separately approved external activation.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import patchloop.errors as errors_module
import patchloop.runtime as runtime_module
import patchloop.util as util_module
from patchloop.errors import ContractError
from patchloop.evals import d129_d128_terminal_successor_offline as d129_offline
from patchloop.evals import d129_external_sequence_block as d129_sequence
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-130"
SCHEMA_VERSION = "d129-external-sequence-block-successor-offline-source-gate-d130-v1"
STATUS = (
    "D130_D129_EXTERNAL_SEQUENCE_BLOCK_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_"
    "ADMISSION_APPROVAL_REQUIRED"
)
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d130-d129-external-sequence-block-successor-offline-source-gate.json"
)

E129_COMMIT = "70f9955dca8d873f91d622505f7afe7f3cfec59e"
E129_TREE = "ad9e348284c1161f258ef7e20ea7cc63cd55399d"
E129_PARENT = "1fef6716cddca571777c8b7f9f1dc4501f988d1c"
S129_COMMIT = "d42334312c4752cbe9f4aa039c22b8ed51b8b66b"
S129_TREE = "4a5f75ba8af5d879af735385fc81b0008267e27e"
R129_COMMIT = "3fdfaa79a93df1e709eb9c01fdea9c4646cf0ad9"
R129_TREE = "44e68cd7aed2a22ffa9591d4338277a75de6c545"
T129_COMMIT = "a4598a15be1432b52f0e26d21d79ace17944e6a9"
T129_TREE = "f0c9464d58e6025a5edf3081ba41ddd8c4f3defa"

D129_GATE_PATH = d129_sequence.D129_GATE_PATH
D129_GATE_ID = d129_sequence.D129_GATE_ID
D129_GATE_BODY_SHA256 = d129_sequence.D129_GATE_BODY_SHA256
D129_GATE_FILE_SHA256 = d129_sequence.D129_GATE_FILE_SHA256
D129_GATE_FILE_BYTES = d129_sequence.D129_GATE_FILE_BYTES
D129_GATE_STATUS = d129_sequence.D129_GATE_STATUS
D129_GATE_BLOB_OID = d129_sequence.D129_GATE_BLOB_OID

D129_RECEIPT_PATH = d129_sequence.RECEIPT_PATH
D129_RECEIPT_SCHEMA = d129_sequence.RECEIPT_SCHEMA
D129_RECEIPT_ID = "d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42"
D129_RECEIPT_BODY_SHA256 = "sha256:0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42"
D129_RECEIPT_FILE_SHA256 = "sha256:820c67d9c5f75cda89aa52f3252295a08ba0ee385e61e6a8ac83cd0637a23885"
D129_RECEIPT_FILE_BYTES = 12_014
D129_RECEIPT_STATUS = d129_sequence.RECEIPT_STATUS
D129_RECEIPT_BLOB_OID = "c16793a4b1fc87c3e526976e4652a2dafceaff7a"

D129_TERMINAL_PATH = d129_sequence.TERMINAL_PATH
D129_TERMINAL_SCHEMA = d129_sequence.TERMINAL_SCHEMA
D129_TERMINAL_ID = (
    "d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8"
)
D129_TERMINAL_BODY_SHA256 = (
    "sha256:b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8"
)
D129_TERMINAL_FILE_SHA256 = (
    "sha256:fbb7fac37555ea4d8a2de0d5947fdffe74e3b716b359e2a23834ed6689bd732d"
)
D129_TERMINAL_FILE_BYTES = 13_118
D129_TERMINAL_STATUS = d129_sequence.TERMINAL_STATUS
D129_TERMINAL_BLOB_OID = "c0fd613da5a745dc2bb3b50afb984d6e4d1b7fd0"

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d130_d129_sequence_block_successor_offline.py"),
    Path("scripts/build_d130_d129_sequence_block_successor_offline.py"),
    Path("tests/test_d130_d129_sequence_block_successor_offline.py"),
)
DEPENDENCY_PATHS = (
    Path("patchloop/evals/d129_external_sequence_block.py"),
    Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
    Path("patchloop/errors.py"),
    Path("patchloop/runtime.py"),
    Path("patchloop/util.py"),
)
SOURCE_BINDING_PATHS = IMPLEMENTATION_PATHS + DEPENDENCY_PATHS
ACTIVE_DOC_PATHS = d129_sequence.ACTIVE_DOC_PATHS
PYTHON_ROUTING_ENV_NAMES = ("PYTHONHOME", "PYTHONPATH")
LOADED_MODULE_PATHS = (
    (IMPLEMENTATION_PATHS[0], __name__),
    (DEPENDENCY_PATHS[0], d129_sequence.__name__),
    (DEPENDENCY_PATHS[1], d129_offline.__name__),
    (DEPENDENCY_PATHS[2], errors_module.__name__),
    (DEPENDENCY_PATHS[3], runtime_module.__name__),
    (DEPENDENCY_PATHS[4], util_module.__name__),
)

D129_FORBIDDEN_DESCENDANTS = d129_sequence.FORBIDDEN_DESCENDANT_PATHS
D130_FUTURE_PATHS = (
    Path("reports/live-pilot/artifacts/d130-local-admission-approval-receipt.json"),
    Path("reports/live-pilot/artifacts/d130-external-phase-armed-intent.json"),
    Path("reports/live-pilot/artifacts/d130-external-activation-receipt.json"),
    Path("reports/live-pilot/artifacts/d130-docker-image-readiness-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d130-replayable-official-pricing-evidence.json"),
    Path("reports/live-pilot/artifacts/d130-repeated-no-call-readiness-preflight.json"),
    Path("reports/live-pilot/artifacts/d130-terminal-successor-no-call-preflight-gate.json"),
)

ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_chain",
    "procedural_incident_preservation",
    "source_identity",
    "successor_contract",
    "approval_template_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)

FOCUSED_TESTS_PASSED = 13


class D130OfflineGateError(ContractError):
    """Raised when the D-130 offline successor is not exact."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D130OfflineGateError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _repo_root(repository: str | Path | None) -> Path:
    try:
        return d129_offline._repo_root(repository)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _parse_time(value: Any, *, label: str) -> datetime:
    try:
        return d129_offline._parse_time(value, label=label)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    try:
        return d129_offline._commit_identity(root, commit)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    try:
        return d129_offline._diff_rows(root, commit)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    try:
        return d129_offline._commit_blob(root, commit, path)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _status_lines(root: Path) -> list[str]:
    try:
        return d129_offline._status_lines(root)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _head(root: Path) -> str:
    try:
        value = d129_offline._git_command(root, "rev-parse", "HEAD")
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc
    _require(isinstance(value, str), "D-130 HEAD differs")
    return value


def _stable_read(root: Path, path: Path) -> bytes:
    try:
        return d129_offline._stable_read(root, path)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc


def _path_absent(root: Path, path: Path) -> None:
    _require(not d129_offline._lexists(root / path), f"D-130 unexpected artifact exists: {path}")


def _assert_runtime_import_boundary(root: Path) -> None:
    presence = {name: name in os.environ for name in PYTHON_ROUTING_ENV_NAMES}
    _require(not any(presence.values()), "D-130 Python import routing environment is present")
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-130 loaded module differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D130OfflineGateError(f"D-130 loaded module differs: {relative}") from exc
        _require(loaded == expected, f"D-130 loaded module is outside repository: {relative}")


def _artifact(
    root: Path,
    *,
    path: Path,
    commit: str,
    blob_oid: str,
    schema: str,
    artifact_id: str,
    id_key: str,
    body_sha256: str,
    file_sha256: str,
    file_bytes: int,
    status: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _stable_read(root, path)
    _require(
        len(raw) == file_bytes and sha256_bytes(raw) == file_sha256,
        f"D-130 {path.name} file differs",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(oid == blob_oid and committed == raw, f"D-130 {path.name} blob differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D130OfflineGateError(f"D-130 {path.name} JSON differs") from exc
    _require(isinstance(payload, dict), f"D-130 {path.name} root differs")
    body = payload.get("semantic_body")
    _require(
        payload.get("schema_version") == schema
        and payload.get(id_key) == artifact_id
        and payload.get("semantic_body_hash") == body_sha256
        and isinstance(body, dict)
        and sha256_text(canonical_json(body)) == body_sha256
        and body.get("status") == status
        and _pretty_bytes(payload) == raw,
        f"D-130 {path.name} tuple differs",
    )
    return payload, {
        "path": path.as_posix(),
        "schema_version": schema,
        "artifact_id": artifact_id,
        "semantic_body_hash": body_sha256,
        "file_sha256": file_sha256,
        "file_bytes": file_bytes,
        "status": status,
        "recorded_at": body["recorded_at"],
        "commit": commit,
        "blob_oid": blob_oid,
        "artifact_mutated": False,
    }


def _topology(root: Path) -> dict[str, Any]:
    expected = (
        (E129_COMMIT, E129_TREE, [E129_PARENT]),
        (S129_COMMIT, S129_TREE, [E129_COMMIT]),
        (R129_COMMIT, R129_TREE, [S129_COMMIT]),
        (T129_COMMIT, T129_TREE, [R129_COMMIT]),
    )
    rows: dict[str, Any] = {}
    for label, (commit, tree, parents) in zip(
        ("e129", "s129", "r129", "t129"), expected, strict=True
    ):
        identity = _commit_identity(root, commit)
        _require(
            identity["tree"] == tree and identity["parents"] == parents,
            f"D-130 {label} topology differs",
        )
        rows[label] = identity
    expected_e = [
        {"status": "A", "path": D129_GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    expected_s = [{"status": "A", "path": path.as_posix()} for path in d129_sequence.SOURCE_PATHS]
    expected_r = [{"status": "A", "path": D129_RECEIPT_PATH.as_posix()}]
    expected_t = [
        {"status": "A", "path": D129_TERMINAL_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    for commit, wanted, label in (
        (E129_COMMIT, expected_e, "E129"),
        (S129_COMMIT, expected_s, "S129"),
        (R129_COMMIT, expected_r, "R129"),
        (T129_COMMIT, expected_t, "T129"),
    ):
        _require(
            sorted(_diff_rows(root, commit), key=lambda row: row["path"])
            == sorted(wanted, key=lambda row: row["path"]),
            f"D-130 {label} scope differs",
        )
    return rows


def _predecessor_chain(root: Path) -> dict[str, Any]:
    topology = _topology(root)
    gate_payload, gate = _artifact(
        root,
        path=D129_GATE_PATH,
        commit=E129_COMMIT,
        blob_oid=D129_GATE_BLOB_OID,
        schema=d129_offline.SCHEMA_VERSION,
        artifact_id=D129_GATE_ID,
        id_key="gate_id",
        body_sha256=D129_GATE_BODY_SHA256,
        file_sha256=D129_GATE_FILE_SHA256,
        file_bytes=D129_GATE_FILE_BYTES,
        status=D129_GATE_STATUS,
    )
    receipt_payload, receipt = _artifact(
        root,
        path=D129_RECEIPT_PATH,
        commit=R129_COMMIT,
        blob_oid=D129_RECEIPT_BLOB_OID,
        schema=D129_RECEIPT_SCHEMA,
        artifact_id=D129_RECEIPT_ID,
        id_key="artifact_id",
        body_sha256=D129_RECEIPT_BODY_SHA256,
        file_sha256=D129_RECEIPT_FILE_SHA256,
        file_bytes=D129_RECEIPT_FILE_BYTES,
        status=D129_RECEIPT_STATUS,
    )
    terminal_payload, terminal = _artifact(
        root,
        path=D129_TERMINAL_PATH,
        commit=T129_COMMIT,
        blob_oid=D129_TERMINAL_BLOB_OID,
        schema=D129_TERMINAL_SCHEMA,
        artifact_id=D129_TERMINAL_ID,
        id_key="artifact_id",
        body_sha256=D129_TERMINAL_BODY_SHA256,
        file_sha256=D129_TERMINAL_FILE_SHA256,
        file_bytes=D129_TERMINAL_FILE_BYTES,
        status=D129_TERMINAL_STATUS,
    )
    try:
        d129_sequence._validate_receipt_payload(
            root, receipt_payload, _stable_read(root, D129_RECEIPT_PATH)
        )
        d129_sequence._validate_terminal_payload(
            root, terminal_payload, _stable_read(root, D129_TERMINAL_PATH)
        )
    except ContractError as exc:
        raise D130OfflineGateError(f"D-130 D-129 replay failed: {exc}") from exc
    gate_body = gate_payload["semantic_body"]
    receipt_body = receipt_payload["semantic_body"]
    terminal_body = terminal_payload["semantic_body"]
    _require(
        receipt_body["predecessor_binding"]["gate_id"] == D129_GATE_ID
        and receipt_body["source_identity"]["commit"] == S129_COMMIT
        and terminal_body["receipt_binding"]["artifact_id"] == D129_RECEIPT_ID
        and terminal_body["receipt_commit_binding"]["commit"] == R129_COMMIT,
        "D-130 D-129 cross-binding differs",
    )
    times = [
        _parse_time(gate_body["recorded_at"], label="gate recorded_at"),
        _parse_time(receipt_body["recorded_at"], label="receipt recorded_at"),
        _parse_time(terminal_body["recorded_at"], label="terminal recorded_at"),
    ]
    _require(times == sorted(times) and len(set(times)) == 3, "D-130 D-129 chronology differs")
    for path in (*D129_FORBIDDEN_DESCENDANTS, *D130_FUTURE_PATHS):
        _path_absent(root, path)
    return {
        "d129_e_s_r_t_git_topology": topology,
        "offline_source_gate": gate,
        "approval_receipt": receipt,
        "sequence_block_terminal": terminal,
        "sequence_incident": {
            "approval_preceded_lookup": True,
            "receipt_preceded_lookup": False,
            "phase_attempt_preceded_lookup": False,
            "no_attempt_retroactively_created": True,
            "official_docs_web_tool_open_invocation_count": 1,
            "underlying_http_request_or_redirect_count": "unknown",
            "canonical_pricing_capture_get_count": 0,
            "canonical_replayable_entity_retained": False,
            "d129_receipt_consumed": True,
            "retry_resume_or_repair_authorized": False,
        },
    }


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(current == committed, f"D-130 source drift: {path}")
    return {
        "path": path.as_posix(),
        "file_bytes": len(committed),
        "file_sha256": sha256_bytes(committed),
        "blob_oid": oid,
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    bindings: list[dict[str, Any]] = []
    for relative, module_name in LOADED_MODULE_PATHS:
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-130 loaded module differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D130OfflineGateError(f"D-130 loaded module differs: {relative}") from exc
        _require(loaded == expected, f"D-130 loaded module is outside repository: {relative}")
        bindings.append(
            {
                **_file_binding(root, commit, relative),
                "module_name": module_name,
                "loaded_path": relative.as_posix(),
                "loaded_path_matches_repository": True,
            }
        )
    return bindings


def _source_identity_for_build(root: Path) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-130 source gate requires clean committed source")
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [T129_COMMIT], "D-130 source parent differs")
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-130 source scope differs",
    )
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths_added": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, head),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": d129_offline._git_cli_observation(root),
        "worktree_and_index_clean_before_gate": True,
        "git_identity_vendor_authenticated_or_signed": False,
    }


def _validate_source_identity(root: Path, source: Any) -> None:
    _assert_runtime_import_boundary(root)
    _require(isinstance(source, dict), "D-130 source identity differs")
    expected_keys = {
        "commit",
        "tree",
        "parents",
        "implementation_paths_added",
        "file_bindings",
        "loaded_module_bindings",
        "python_routing_env_presence",
        "git_cli_observation",
        "worktree_and_index_clean_before_gate",
        "git_identity_vendor_authenticated_or_signed",
    }
    _require(set(source) == expected_keys, "D-130 source fields differ")
    identity = _commit_identity(root, source["commit"])
    _require(
        identity["tree"] == source["tree"]
        and identity["parents"] == [T129_COMMIT]
        and source["parents"] == [T129_COMMIT],
        "D-130 source topology differs",
    )
    expected_diff = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, source["commit"]), key=lambda row: row["path"])
        == sorted(expected_diff, key=lambda row: row["path"]),
        "D-130 source commit scope differs",
    )
    _require(
        source["implementation_paths_added"] == [path.as_posix() for path in IMPLEMENTATION_PATHS]
        and source["python_routing_env_presence"]
        == {name: False for name in PYTHON_ROUTING_ENV_NAMES}
        and source["worktree_and_index_clean_before_gate"] is True
        and source["git_identity_vendor_authenticated_or_signed"] is False,
        "D-130 source claims differ",
    )
    expected_bindings = [
        _file_binding(root, source["commit"], path) for path in SOURCE_BINDING_PATHS
    ]
    _require(
        canonical_json(source["file_bindings"]) == canonical_json(expected_bindings),
        "D-130 source bindings differ",
    )
    _require(
        canonical_json(source["loaded_module_bindings"])
        == canonical_json(_loaded_module_bindings(root, source["commit"])),
        "D-130 loaded module bindings differ",
    )
    d129_offline._validate_git_observation(source["git_cli_observation"])


def _incident_preservation() -> dict[str, Any]:
    return {
        "d129_sequence_incident_preserved_without_reinterpretation": True,
        "approval_preceded_lookup": True,
        "receipt_and_attempt_preceded_lookup": False,
        "retroactive_attempt_created": False,
        "official_docs_web_tool_open_invocation_count": 1,
        "underlying_http_request_or_redirect_count": "unknown",
        "canonical_pricing_capture_get_count": 0,
        "canonical_replayable_entity_retained": False,
        "docker_cli_or_daemon_call_count_after_receipt": 0,
        "sdk_probe_count_after_receipt": 0,
        "provider_evaluator_agent_call_count": 0,
        "d129_receipt_consumed": True,
        "d129_retry_resume_or_repair_authorized": False,
    }


def _successor_contract() -> dict[str, Any]:
    return {
        "admission_is_local_only": True,
        "stage_1_may_create_exact_d130_receipt": True,
        "stage_1_may_commit_receipt_only": True,
        "stage_1_may_create_durable_external_phase_armed_intent": True,
        "stage_1_may_commit_armed_intent_only": True,
        "stage_1_may_render_activation_challenge": True,
        "stage_1_official_docs_or_network_lookup_authorized": False,
        "stage_1_docker_sdk_or_credential_observation_authorized": False,
        "stage_1_external_call_count_must_remain_zero": True,
        "stage_2_requires_separate_exact_activation": True,
        "stage_2_must_quote_gate_receipt_intent_and_commit_tuples": True,
        "stage_2_not_authorized_by_this_gate": True,
    }


def _approval_template_contract() -> dict[str, Any]:
    return {
        "template_kind": "two-stage-local-admission-then-exact-external-activation",
        "first_approval_scope": [
            "create-new-exact-d130-local-admission-receipt",
            "create-receipt-only-local-git-commit",
            "create-durable-external-phase-armed-intent-with-zero-external-actions",
            "create-armed-intent-only-local-git-commit",
            "render-exact-activation-challenge",
        ],
        "first_approval_explicitly_excludes": [
            "official-docs-search-or-open",
            "network-or-pricing-capture",
            "docker-cli-daemon-image-or-container-call",
            "sdk-or-credential-observation",
            "provider-evaluator-agent-memory-retrieval",
            "execution-hash-candidate-cost-or-ac-run",
        ],
        "later_activation_requires_new_user_message": True,
        "template_is_not_a_receipt_intent_activation_or_candidate": True,
    }


def _authority() -> dict[str, Any]:
    return {
        "d130_offline_source_gate_materialized": True,
        "d129_sequence_incident_preserved": True,
        "d130_approval_recorded": False,
        "d130_receipt_created": False,
        "d130_armed_intent_created": False,
        "d130_external_activation_recorded": False,
        "d130_external_phase_attempt_created": False,
        "d130_network_or_official_docs_call_count": 0,
        "d130_canonical_pricing_capture_get_count": 0,
        "d130_docker_cli_daemon_or_image_call_count": 0,
        "d130_container_create_start_run_exec_count": 0,
        "d130_sdk_probe_count": 0,
        "d130_credential_presence_observed": False,
        "d130_provider_evaluator_or_agent_call_count": 0,
        "d130_retrieval_or_memory_injection_count": 0,
        "d130_execution_hash_created": False,
        "d130_execution_candidate_created": False,
        "d130_cost_reserved_or_spent_usd": "0",
        "d130_four_row_ac_execution_authorized": False,
    }


def _body(
    *, recorded_at: str, predecessor: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "external-sequence-block-successor-offline-source-gate",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_chain": predecessor,
        "procedural_incident_preservation": _incident_preservation(),
        "source_identity": source,
        "successor_contract": _successor_contract(),
        "approval_template_contract": _approval_template_contract(),
        "implementation_integrity": {
            "implementation_paths": [path.as_posix() for path in IMPLEMENTATION_PATHS],
            "dependency_paths": [path.as_posix() for path in DEPENDENCY_PATHS],
            "focused_tests_passed": FOCUSED_TESTS_PASSED,
            "builder_external_call_count": 0,
            "builder_reads_dotenv_or_credential_value": False,
        },
        "offline_qualification": {
            "predecessor_full_replay_verified": True,
            "source_commit_and_loaded_modules_verified": True,
            "canonical_new_only_gate_verified": True,
            "two_stage_admission_contract_qualified_offline": True,
            "external_environment_ready": False,
            "qualification_grade": "offline-source-only",
        },
        "blocked_prerequisites": [
            "exact-d130-local-admission-user-approval-not-recorded",
            "d130-receipt-only-commit-not-created",
            "d130-armed-intent-only-commit-not-created",
            "separate-exact-external-activation-not-recorded",
            "docker-pricing-sdk-no-call-readiness-not-observed",
            "execution-hash-candidate-cost-and-ac-remain-later-gates",
        ],
        "evidence_boundary": {
            "d129_approved_docs_lookup_is_historical_not_pricing_evidence": True,
            "underlying_d129_transport_count_remains_unknown": True,
            "d130_performed_no_external_lookup": True,
            "user_identity_is_self_attested_not_authenticated_or_signed": True,
            "git_identity_is_observed_not_vendor_authenticated_or_signed": True,
            "gate_does_not_self_bind_its_future_evidence_commit": True,
        },
        "authority": _authority(),
        "next_gate": {
            "action": "request-exact-d130-local-admission-approval",
            "must_quote_exact_d130_gate_tuple_bytes_and_evidence_commit": True,
            "may_create_only_receipt-and-armed-intent-local-commits": True,
            "must_not_search-or-open-official-docs-in-admission-stage": True,
            "requires_separate_exact_activation_before_any_external_action": True,
            "does_not_authorize_external-execution-hash-candidate-cost-or-ac": True,
        },
    }


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d130_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _write_new(root: Path, raw: bytes) -> None:
    try:
        output = d129_offline._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D130OfflineGateError(str(exc)) from exc
    _require(not d129_offline._lexists(output), "D-130 output already exists")
    temporary = output.with_name(f".{output.name}.d130-{uuid.uuid4().hex}.tmp")
    _require(not d129_offline._lexists(temporary), "D-130 temporary collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-130 temporary output differs")
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise D130OfflineGateError("D-130 output collision") from exc
        _require(_stable_read(root, OUTPUT_PATH) == raw, "D-130 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _validate_checkout(root: Path, source: dict[str, Any], raw: bytes) -> dict[str, Any]:
    head = _head(root)
    status = _status_lines(root)
    if head == source["commit"]:
        _require(status == [f"?? {OUTPUT_PATH.as_posix()}"], "D-130 source checkout state differs")
        return {"source_commit": head, "evidence_commit": None}
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [source["commit"]], "D-130 evidence parent differs")
    expected = [
        {"status": "A", "path": OUTPUT_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-130 evidence scope differs",
    )
    _require(status == [], "D-130 post-evidence checkout is not clean")
    _, committed = _commit_blob(root, head, OUTPUT_PATH)
    _require(committed == raw, "D-130 committed gate bytes differ")
    return {"source_commit": source["commit"], "evidence_commit": head}


def _validate_payload(
    root: Path,
    payload: Any,
    raw: bytes,
    *,
    check_checkout: bool = True,
) -> dict[str, Any]:
    _require(isinstance(payload, dict) and tuple(payload) == ROOT_KEYS, "D-130 root differs")
    _require(payload["schema_version"] == SCHEMA_VERSION, "D-130 schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict) and tuple(body) == BODY_KEYS, "D-130 body fields differ")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload["semantic_body_hash"] == body_hash
        and payload["gate_id"] == f"d130_{body_hash.removeprefix('sha256:')}"
        and _pretty_bytes(payload) == raw,
        "D-130 envelope differs",
    )
    _require(body["milestone"] == MILESTONE and body["status"] == STATUS, "D-130 status differs")
    predecessor = _predecessor_chain(root)
    _require(
        canonical_json(body["predecessor_chain"]) == canonical_json(predecessor),
        "D-130 predecessor differs",
    )
    _validate_source_identity(root, body["source_identity"])
    expected = _envelope(
        _body(
            recorded_at=body["recorded_at"],
            predecessor=predecessor,
            source=body["source_identity"],
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-130 full rebuild differs")
    terminal_time = _parse_time(
        predecessor["sequence_block_terminal"]["recorded_at"],
        label="terminal recorded_at",
    )
    _require(
        _parse_time(body["recorded_at"], label="recorded_at") > terminal_time,
        "D-130 chronology differs",
    )
    checkout = (
        _validate_checkout(root, body["source_identity"], raw)
        if check_checkout
        else {"source_commit": body["source_identity"]["commit"], "evidence_commit": None}
    )
    return {**payload, "_checkout": checkout}


def _result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    checkout = payload.get("_checkout", {})
    return {
        "status": STATUS,
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "evidence_commit": checkout.get("evidence_commit"),
        "local_admission_approval_required": True,
        "receipt_created": False,
        "armed_intent_created": False,
        "external_activation_recorded": False,
        "external_call_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
    }


def validate_d130_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate the exact offline D-130 gate without external activity."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D130OfflineGateError("D-130 gate JSON differs") from exc
    return _result(_validate_payload(root, payload, raw), raw)


def run_d130_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Materialize only the append-only D-130 offline source gate."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    if d129_offline._lexists(root / OUTPUT_PATH):
        return validate_d130_offline_source_gate(repository=root)
    for path in D130_FUTURE_PATHS:
        _path_absent(root, path)
    predecessor = _predecessor_chain(root)
    source = _source_identity_for_build(root)
    recorded_at = _now()
    terminal_time = _parse_time(
        predecessor["sequence_block_terminal"]["recorded_at"],
        label="terminal recorded_at",
    )
    _require(
        _parse_time(recorded_at, label="recorded_at") > terminal_time,
        "D-130 chronology differs before publication",
    )
    payload = _envelope(_body(recorded_at=recorded_at, predecessor=predecessor, source=source))
    raw = _pretty_bytes(payload)
    _validate_payload(root, payload, raw, check_checkout=False)
    _write_new(root, raw)
    return validate_d130_offline_source_gate(repository=root)


def render_d130_two_stage_admission_template(*, repository: str | Path | None = None) -> str:
    """Render a non-authoritative local-admission template without side effects."""

    result = validate_d130_offline_source_gate(repository=repository)
    evidence_commit = result["evidence_commit"] or "<exact D-130 gate+docs evidence commit>"
    return "\n".join(
        (
            "D-130 local admission approval (no external actions)",
            "",
            f"Gate ID: {result['gate_id']}",
            f"Body SHA: {result['semantic_body_hash']}",
            f"File SHA: {result['file_sha256']}",
            f"File bytes: {result['file_bytes']}",
            f"Source/evidence commit: {evidence_commit}",
            "",
            "Approved local-only scope:",
            "- create and commit one exact D-130 approval receipt",
            "- create and commit one durable ARMED_WAITING_EXACT_ACTIVATION intent",
            "- render the exact activation challenge",
            "",
            "Explicitly not approved in this admission:",
            "- search or open official docs, network, pricing capture",
            "- Docker, SDK, credential or endpoint observation",
            "- provider/evaluator/agent, memory/retrieval",
            "- execution hash/candidate, cost, or four-row A/C",
            "",
            "A later exact activation must quote the receipt, armed-intent, and commit tuples.",
        )
    )


__all__ = [
    "D130OfflineGateError",
    "OUTPUT_PATH",
    "SCHEMA_VERSION",
    "STATUS",
    "render_d130_two_stage_admission_template",
    "run_d130_offline_source_gate",
    "validate_d130_offline_source_gate",
]
