from __future__ import annotations

import ast
import copy
import inspect
import json
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals import d134_d132_pricing_consumed_incident_offline as d134
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d134_d132_pricing_consumed_incident_offline.py")
SCRIPT_PATH = Path("scripts/build_d134_d132_pricing_consumed_incident_offline.py")
TEST_PATH = Path("tests/test_d134_d132_pricing_consumed_incident_offline.py")

ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-official-pricing-capture-attempt-intent.json"
)
ATTEMPT_ID = (
    "d132d130officialpricingcaptureattempt_"
    "c518711e0a12b75a3ab81bbfd3e53eb3e13059d0f6fe4b3c4c1309e25924245f"
)
ATTEMPT_BODY_SHA = "sha256:c518711e0a12b75a3ab81bbfd3e53eb3e13059d0f6fe4b3c4c1309e25924245f"
ATTEMPT_FILE_SHA = "sha256:ba79ad9362bf14f0cdf8952d9297bea8fcd77fe36ab0eeff44e47e9047ec3f55"
ATTEMPT_FILE_BYTES = 18_137
ATTEMPT_BLOB = "530ad365efe8a79eaa6f131db1a4541a4f94c20c"
ATTEMPT_COMMIT = "30412b769b340f98000674f40de9102d1210507a"
ATTEMPT_TREE = "2a865bf4245936ccb2d4366153038875444a536b"
ATTEMPT_PARENT = "72f1aef7ab93b9d1167ef5d3b11947a9d1f32cf0"

MARKER_PATH = Path("reports/live-pilot/artifacts/d130-official-pricing-capture-action-started.json")
MARKER_ID = (
    "d132d130officialpricingcapturestarted_"
    "50876b05d4daa48d5f80bce7793f28ffb4f7909350661803dfa96f9a2e6dced7"
)
MARKER_BODY_SHA = "sha256:50876b05d4daa48d5f80bce7793f28ffb4f7909350661803dfa96f9a2e6dced7"
MARKER_FILE_SHA = "sha256:328c4fb5ae4d6e50308333e360f25fb88bc856bace7ba483f2eb7e2adde13328"
MARKER_FILE_BYTES = 12_815
MARKER_BLOB = "4e1af70ae48884a5c3ec492a9afc83313829ee75"
MARKER_COMMIT = "a10033b6abd7155ebaa5c66c13627ad3ea738566"
MARKER_TREE = "33d7aa66d2e7aa23e0b73ca851a02db20ec295e8"

CANONICAL_PRICING_PATH = Path(
    "reports/live-pilot/artifacts/d130-replayable-official-pricing-evidence.json"
)
CANONICAL_PREFLIGHT_PATH = Path(
    "reports/live-pilot/artifacts/d130-repeated-no-call-readiness-preflight.json"
)
CANONICAL_PREFLIGHT_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-read-only-preflight-attempt-intent.json"
)
CANONICAL_PREFLIGHT_STARTED_PATH = Path(
    "reports/live-pilot/artifacts/d130-read-only-preflight-action-started.json"
)
CANONICAL_FINAL_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d130-terminal-successor-no-call-preflight-gate.json"
)

SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
GATE_COMMIT = "c" * 40
GATE_TREE = "d" * 40
TERMINAL_COMMIT = "e" * 40
TERMINAL_TREE = "f" * 40
GATE_RECORDED_AT = "2026-08-09T14:30:00Z"
TERMINAL_RECORDED_AT = "2026-08-09T14:31:00Z"


def _fake_git_observation() -> dict[str, object]:
    return {
        "resolved_path": r"C:\Program Files\Git\mingw64\bin\git.exe",
        "file_name": "git.exe",
        "file_bytes": 4_422_544,
        "file_sha256": "sha256:" + "1" * 64,
        "linklike": False,
        "version": "git version 2.54.0.windows.1",
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "fsmonitor_disabled": True,
        "shell_used": False,
    }


def _forbidden(label: str):
    def fail(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError(f"D-134 crossed forbidden {label} boundary")

    return fail


@pytest.fixture
def repository(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    root = REPOSITORY / f"tmp-d134-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    required = {ATTEMPT_PATH, MARKER_PATH, *d134.SOURCE_BINDING_PATHS}
    committed_source_blobs: dict[str, bytes] = {}
    committed_predecessor_blobs: dict[str, bytes] = {}
    for relative in required:
        source = REPOSITORY / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        target.write_bytes(raw)
        if relative in d134.SOURCE_BINDING_PATHS:
            committed_source_blobs[relative.as_posix()] = raw
        if relative in {ATTEMPT_PATH, MARKER_PATH}:
            committed_predecessor_blobs[relative.as_posix()] = raw

    state: dict[str, Any] = {
        "head": SOURCE_COMMIT,
        "times": iter((GATE_RECORDED_AT, TERMINAL_RECORDED_AT)),
        "writes": [],
        "extra_diff": {},
        "identity_overrides": {},
    }
    identities: dict[str, dict[str, object]] = {
        ATTEMPT_COMMIT: {
            "commit": ATTEMPT_COMMIT,
            "tree": ATTEMPT_TREE,
            "parents": [ATTEMPT_PARENT],
        },
        MARKER_COMMIT: {
            "commit": MARKER_COMMIT,
            "tree": MARKER_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [MARKER_COMMIT],
        },
        GATE_COMMIT: {
            "commit": GATE_COMMIT,
            "tree": GATE_TREE,
            "parents": [SOURCE_COMMIT],
        },
        TERMINAL_COMMIT: {
            "commit": TERMINAL_COMMIT,
            "tree": TERMINAL_TREE,
            "parents": [GATE_COMMIT],
        },
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, object]:
        return copy.deepcopy(state["identity_overrides"].get(commit, identities[commit]))

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == ATTEMPT_COMMIT:
            rows = [{"status": "A", "path": ATTEMPT_PATH.as_posix()}]
        elif commit == MARKER_COMMIT:
            rows = [{"status": "A", "path": MARKER_PATH.as_posix()}]
        elif commit == SOURCE_COMMIT:
            rows = [{"status": "A", "path": path.as_posix()} for path in d134.IMPLEMENTATION_PATHS]
        elif commit == GATE_COMMIT:
            rows = [
                {"status": "A", "path": d134.GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d134.ACTIVE_DOC_PATHS),
            ]
        elif commit == TERMINAL_COMMIT:
            rows = [{"status": "A", "path": d134.TERMINAL_PATH.as_posix()}]
        else:
            raise AssertionError(f"unexpected commit diff: {commit}")
        return [*rows, *copy.deepcopy(state["extra_diff"].get(commit, []))]

    def commit_blob(_root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
        if commit == ATTEMPT_COMMIT and relative == ATTEMPT_PATH:
            return ATTEMPT_BLOB, committed_predecessor_blobs[relative.as_posix()]
        if commit == MARKER_COMMIT and relative == MARKER_PATH:
            return MARKER_BLOB, committed_predecessor_blobs[relative.as_posix()]
        if commit == SOURCE_COMMIT and relative.as_posix() in committed_source_blobs:
            index = d134.SOURCE_BINDING_PATHS.index(relative) + 1
            return f"{index:x}"[-1] * 40, committed_source_blobs[relative.as_posix()]
        if commit == GATE_COMMIT and relative == d134.GATE_PATH:
            return "8" * 40, (root / relative).read_bytes()
        if commit == TERMINAL_COMMIT and relative == d134.TERMINAL_PATH:
            return "9" * 40, (root / relative).read_bytes()
        raise AssertionError(f"unexpected committed blob: {commit}:{relative}")

    def status_lines(_root: Path) -> list[str]:
        if state["head"] == SOURCE_COMMIT and (root / d134.GATE_PATH).exists():
            return [f"?? {d134.GATE_PATH.as_posix()}"]
        if state["head"] == GATE_COMMIT and (root / d134.TERMINAL_PATH).exists():
            return [f"?? {d134.TERMINAL_PATH.as_posix()}"]
        return []

    real_write_new = d134._write_new

    def write_new(selected_root: Path, relative: Path, raw: bytes) -> None:
        state["writes"].append(relative)
        real_write_new(selected_root, relative, raw)

    def loaded_module_bindings(selected_root: Path, commit: str) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for relative, module_name in d134.LOADED_MODULE_PATHS:
            key = (relative.as_posix(), module_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    **d134._file_binding(selected_root, commit, relative),
                    "module_name": module_name,
                    "loaded_path": relative.as_posix(),
                    "loaded_path_matches_repository": True,
                }
            )
        return result

    monkeypatch.setattr(d134, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d134, "_now", lambda: next(state["times"]))
    monkeypatch.setattr(d134, "_commit_identity", commit_identity)
    monkeypatch.setattr(d134, "_diff_rows", diff_rows)
    monkeypatch.setattr(d134, "_commit_blob", commit_blob)
    monkeypatch.setattr(d134, "_status_lines", status_lines)
    monkeypatch.setattr(d134, "_head", lambda _root: state["head"])
    monkeypatch.setattr(d134, "_write_new", write_new)
    monkeypatch.setattr(d134, "_loaded_module_bindings", loaded_module_bindings)
    monkeypatch.setattr(d134.d131, "_git_cli_observation", lambda _root: _fake_git_observation())
    try:
        yield root, state
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == REPOSITORY.resolve(strict=True)
            shutil.rmtree(root)


def _payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_bytes())


def _rewrite_envelope(path: Path, payload: dict[str, object], *, prefix: str) -> bytes:
    body = payload["semantic_body"]
    assert isinstance(body, dict)
    body_hash = sha256_text(canonical_json(body))
    payload["semantic_body_hash"] = body_hash
    identity_key = "gate_id" if "gate_id" in payload else "artifact_id"
    payload[identity_key] = f"{prefix}_{body_hash.removeprefix('sha256:')}"
    raw = d134._pretty_bytes(payload)
    path.write_bytes(raw)
    return raw


def _build_gate(
    root: Path,
) -> tuple[dict[str, object], dict[str, object], bytes]:
    result = d134.run_d134_offline_source_gate(repository=root)
    raw = (root / d134.GATE_PATH).read_bytes()
    return result, json.loads(raw), raw


def _seal_gate(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, object], dict[str, object], bytes]:
    result, payload, raw = _build_gate(root)
    state["head"] = GATE_COMMIT
    return result, payload, raw


def _create_terminal(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, object], dict[str, object], bytes]:
    _seal_gate(root, state)
    result = d134.create_d134_procedural_terminal(repository=root)
    raw = (root / d134.TERMINAL_PATH).read_bytes()
    return result, json.loads(raw), raw


def test_exact_attempt_and_marker_bytes_and_linear_commit_tuples_are_bound() -> None:
    attempt_raw = (REPOSITORY / ATTEMPT_PATH).read_bytes()
    marker_raw = (REPOSITORY / MARKER_PATH).read_bytes()
    attempt = json.loads(attempt_raw)
    marker = json.loads(marker_raw)

    assert (attempt["artifact_id"], attempt["semantic_body_hash"]) == (
        ATTEMPT_ID,
        ATTEMPT_BODY_SHA,
    )
    assert (sha256_bytes(attempt_raw), len(attempt_raw)) == (
        ATTEMPT_FILE_SHA,
        ATTEMPT_FILE_BYTES,
    )
    assert (marker["artifact_id"], marker["semantic_body_hash"]) == (
        MARKER_ID,
        MARKER_BODY_SHA,
    )
    assert (sha256_bytes(marker_raw), len(marker_raw)) == (
        MARKER_FILE_SHA,
        MARKER_FILE_BYTES,
    )
    assert attempt["semantic_body"]["phase"] == "official-pricing-capture"
    assert marker["semantic_body"]["phase"] == "official-pricing-capture"
    assert marker["semantic_body"]["attempt_binding"] == {
        "path": ATTEMPT_PATH.as_posix(),
        "artifact_id": ATTEMPT_ID,
        "semantic_body_hash": ATTEMPT_BODY_SHA,
        "file_sha256": ATTEMPT_FILE_SHA,
        "file_bytes": ATTEMPT_FILE_BYTES,
        "status": "D132_D130_OFFICIAL_PRICING_CAPTURE_ATTEMPT_RECORDED_COMMIT_REQUIRED",
        "recorded_at": "2026-08-09T13:43:26.208409Z",
        "artifact_mutated": False,
    }
    assert marker["semantic_body"]["attempt_commit_binding"] == {
        "commit": ATTEMPT_COMMIT,
        "tree": ATTEMPT_TREE,
        "parents": [ATTEMPT_PARENT],
        "artifact_path": ATTEMPT_PATH.as_posix(),
        "artifact_blob_oid": ATTEMPT_BLOB,
        "artifact_file_sha256": ATTEMPT_FILE_SHA,
        "artifact_file_bytes": ATTEMPT_FILE_BYTES,
        "single_artifact_add_commit": True,
    }
    assert d134.ATTEMPT_COMMIT == ATTEMPT_COMMIT
    assert d134.MARKER_COMMIT == MARKER_COMMIT
    assert d134.ATTEMPT_BLOB_OID == ATTEMPT_BLOB
    assert d134.MARKER_BLOB_OID == MARKER_BLOB
    assert d134.ATTEMPT_PARENT == ATTEMPT_PARENT
    assert d134.MARKER_PARENT == ATTEMPT_COMMIT

    assert d134._commit_identity(REPOSITORY, ATTEMPT_COMMIT) == {
        "commit": ATTEMPT_COMMIT,
        "tree": ATTEMPT_TREE,
        "parents": [ATTEMPT_PARENT],
    }
    assert d134._diff_rows(REPOSITORY, ATTEMPT_COMMIT) == [
        {"status": "A", "path": ATTEMPT_PATH.as_posix()}
    ]
    attempt_oid, committed_attempt = d134._commit_blob(REPOSITORY, ATTEMPT_COMMIT, ATTEMPT_PATH)
    assert (attempt_oid, committed_attempt) == (ATTEMPT_BLOB, attempt_raw)
    assert d134._commit_identity(REPOSITORY, MARKER_COMMIT) == {
        "commit": MARKER_COMMIT,
        "tree": MARKER_TREE,
        "parents": [ATTEMPT_COMMIT],
    }
    assert d134._diff_rows(REPOSITORY, MARKER_COMMIT) == [
        {"status": "A", "path": MARKER_PATH.as_posix()}
    ]
    marker_oid, committed_marker = d134._commit_blob(REPOSITORY, MARKER_COMMIT, MARKER_PATH)
    assert (marker_oid, committed_marker) == (MARKER_BLOB, marker_raw)


def test_procedural_terminal_path_is_distinct_and_canonical_descendants_are_absent() -> None:
    assert d134.CANONICAL_D132_DESCENDANT_PATHS == (
        CANONICAL_PRICING_PATH,
        CANONICAL_PREFLIGHT_ATTEMPT_PATH,
        CANONICAL_PREFLIGHT_STARTED_PATH,
        CANONICAL_PREFLIGHT_PATH,
        CANONICAL_FINAL_GATE_PATH,
    )
    assert d134.TERMINAL_PATH != CANONICAL_PRICING_PATH
    assert d134.TERMINAL_PATH not in {
        CANONICAL_PREFLIGHT_PATH,
        CANONICAL_FINAL_GATE_PATH,
        ATTEMPT_PATH,
        MARKER_PATH,
    }
    assert not (REPOSITORY / CANONICAL_PRICING_PATH).exists()
    assert not (REPOSITORY / CANONICAL_PREFLIGHT_PATH).exists()
    assert not (REPOSITORY / CANONICAL_FINAL_GATE_PATH).exists()


def test_public_paths_schemas_statuses_and_signatures_are_exact() -> None:
    assert (
        Path(
            "reports/live-pilot/artifacts/"
            "d134-d132-pricing-consumed-incident-procedural-terminal-offline-source-gate.json"
        )
        == d134.GATE_PATH
    )
    assert (
        Path(
            "reports/live-pilot/artifacts/"
            "d134-d132-pricing-consumed-incident-procedural-terminal.json"
        )
        == d134.TERMINAL_PATH
    )
    assert d134.GATE_STATUS == (
        "D134_D132_PRICING_CONSUMED_INCIDENT_PROCEDURAL_TERMINAL_"
        "OFFLINE_SOURCE_QUALIFIED_TERMINALIZATION_APPROVAL_REQUIRED"
    )
    assert d134.TERMINAL_STATUS == ("D134_D132_PRICING_CONSUMED_INCIDENT_PROCEDURALLY_TERMINAL")
    assert tuple(inspect.signature(d134.run_d134_offline_source_gate).parameters) == ("repository",)
    assert tuple(
        inspect.signature(d134.render_d134_terminalization_approval_template).parameters
    ) == ("repository",)
    assert tuple(inspect.signature(d134.create_d134_procedural_terminal).parameters) == (
        "repository",
    )
    assert tuple(inspect.signature(d134.validate_d134_offline_source_gate).parameters) == (
        "repository",
        "mode",
    )
    assert tuple(inspect.signature(d134.validate_d134_procedural_terminal).parameters) == (
        "repository",
        "mode",
    )
    assert tuple(d134.IMPLEMENTATION_PATHS) == (MODULE_PATH, SCRIPT_PATH, TEST_PATH)


def test_source_and_cli_expose_no_retry_repair_or_external_helper_surface() -> None:
    source = (REPOSITORY / MODULE_PATH).read_text(encoding="utf-8")
    script = (REPOSITORY / SCRIPT_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
            imported_names.update(f"{node.module}.{alias.name}" for alias in node.names)

    forbidden_imports = {
        "docker",
        "httpx",
        "openai",
        "requests",
        "socket",
        "urllib",
        "patchloop.evals.d132_d130_external_activation_offline",
        "patchloop.evals.d127_d126_successor_no_call_preflight",
        "patchloop.evals.d127_docker_remediation",
        "patchloop.evals.d127_pricing_capture",
        "patchloop.evals.d128_docker_no_start_remediation",
    }
    assert not any(
        imported == forbidden or imported.startswith(f"{forbidden}.")
        for imported in imported_names
        for forbidden in forbidden_imports
    )
    for forbidden in (
        "OPENAI_API_KEY",
        "load_dotenv",
        "dotenv_values",
        "os.environ.get",
        "os.environ.items",
        "capture_official_pricing_evidence(",
        "run_d130_external_no_call_preflight(",
        "remediate_already_running_docker_environment(",
        "observe_docker_readiness(",
        "create_d130_external_activation_receipt(",
    ):
        assert forbidden not in source
    for forbidden_flag in (
        "--retry",
        "--resume",
        "--repair",
        "--run-external",
        "--capture-pricing",
        "--docker",
        "--sdk",
    ):
        assert forbidden_flag not in script
    for required_flag in (
        "--build-offline-gate",
        "--validate-offline-gate",
        "--validate-offline-gate-post-commit",
        "--print-terminalization-template",
        "--create-procedural-terminal",
        "--validate-procedural-terminal",
        "--validate-procedural-terminal-post-commit",
    ):
        assert required_flag in script
    assert source.count("d131._git_command(") == 1
    assert d134.d131.D131_GIT_ENGINE_PATH.is_absolute()
    assert set(d134.d131.D131_FIXED_GIT_ENVIRONMENT) == {
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_OPTIONAL_LOCKS",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_NO_LAZY_FETCH",
        "GIT_TERMINAL_PROMPT",
        "LC_ALL",
    }
    assert "PATH" not in d134.d131.D131_FIXED_GIT_ENVIRONMENT
    assert all(
        "OPENAI" not in key and "CREDENTIAL" not in key and "TOKEN" not in key
        for key in d134.d131.D131_FIXED_GIT_ENVIRONMENT
    )


def test_public_module_surface_is_narrow_and_offline_only() -> None:
    assert set(d134.__all__) == {
        "D134PricingConsumedIncidentError",
        "GATE_PATH",
        "GATE_SCHEMA",
        "GATE_STATUS",
        "TERMINAL_PATH",
        "TERMINAL_SCHEMA",
        "TERMINAL_STATUS",
        "create_d134_procedural_terminal",
        "render_d134_terminalization_approval_template",
        "run_d134_offline_source_gate",
        "validate_d134_offline_source_gate",
        "validate_d134_procedural_terminal",
    }


def test_source_commit_is_exact_marker_child_a_only_with_loaded_module_bindings(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    source = d134._source_identity_for_gate(root)

    assert source["commit"] == SOURCE_COMMIT
    assert source["tree"] == SOURCE_TREE
    assert source["parents"] == [MARKER_COMMIT]
    assert source["implementation_paths_added"] == [
        path.as_posix() for path in d134.IMPLEMENTATION_PATHS
    ]
    assert [row["path"] for row in source["file_bindings"]] == [
        path.as_posix() for path in d134.SOURCE_BINDING_PATHS
    ]
    assert [row["loaded_path"] for row in source["loaded_module_bindings"]] == list(
        dict.fromkeys(path.as_posix() for path, _module_name in d134.LOADED_MODULE_PATHS)
    )
    assert all(
        row["loaded_path_matches_repository"] is True and row["current_bytes_match_commit"] is True
        for row in source["loaded_module_bindings"]
    )
    assert source["python_routing_env_presence"] == {"PYTHONHOME": False, "PYTHONPATH": False}
    assert source["worktree_and_index_clean_before_gate"] is True
    assert source["git_identity_vendor_authenticated_or_signed"] is False

    state["identity_overrides"][SOURCE_COMMIT] = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": ["0" * 40],
    }
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="source parent"):
        d134._source_identity_for_gate(root)
    state["identity_overrides"].clear()

    state["extra_diff"][SOURCE_COMMIT] = [{"status": "M", "path": "README.md"}]
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="source scope"):
        d134._source_identity_for_gate(root)


def test_runtime_loaded_module_provenance_rejects_outside_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in d134.PYTHON_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    d134._assert_runtime_import_boundary(REPOSITORY)

    relative, module_name = d134.LOADED_MODULE_PATHS[0]
    outside = REPOSITORY.parent / f"outside-d134-{uuid.uuid4().hex}.py"
    assert not outside.exists()
    outside.write_text("# outside repository\n", encoding="utf-8")
    try:
        module = sys.modules[module_name]
        monkeypatch.setattr(module, "__file__", str(outside))
        with pytest.raises(d134.D134PricingConsumedIncidentError, match="outside repository"):
            d134._assert_runtime_import_boundary(REPOSITORY)
        assert relative == MODULE_PATH
    finally:
        outside.unlink(missing_ok=True)


def test_gate_builder_never_invokes_terminal_writer_and_is_canonical_idempotent(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = repository
    monkeypatch.setattr(
        d134,
        "create_d134_procedural_terminal",
        _forbidden("procedural terminal writer"),
    )
    first, payload, raw = _build_gate(root)
    second = d134.run_d134_offline_source_gate(repository=root)
    third = d134.validate_d134_offline_source_gate(repository=root)

    assert first == second == third
    assert state["writes"] == [d134.GATE_PATH]
    assert tuple(payload) == d134.GATE_ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d134.GATE_BODY_KEYS
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == (f"d134_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert first["file_sha256"] == sha256_bytes(raw)
    assert first["file_bytes"] == len(raw)
    assert first["procedural_terminal_created"] is False
    assert first["external_call_count"] == 0
    assert not (root / d134.TERMINAL_PATH).exists()

    body = payload["semantic_body"]
    assert body["offline_qualification"]["builder_invoked_terminal_writer"] is False
    assert body["offline_qualification"]["builder_invoked_network_or_external_helper"] is False
    assert body["qualified_procedural_terminal_contract"] == {
        "writer_is_future_only": True,
        "future_exact_approval_required": True,
        "future_terminal_is_append_only_new_only": True,
        "future_terminal_only_commit_required": True,
        "future_terminal_commit_parent_is_gate_evidence_commit": True,
        "retry_resume_repair_or_backfill_forbidden": True,
        "fixed_successor_requires_later_offline_gate": True,
    }
    incident = body["incident_contract"]
    assert incident["application_level_client_send_returned_response_count"] == 1
    assert incident["observation_provenance"] == (
        "user-approved-current-session-control-flow-observation-not-reconstructed-machine-telemetry"
    )
    assert incident["canonical_pricing_capture_count"] == 0
    assert incident["canonical_pricing_capture_get_count"] == 0
    assert incident["canonical_pricing_evidence_artifact_created"] is False
    assert incident["canonical_response_status_retention_state"] == "not-retained"
    assert incident["canonical_response_headers_retention_state"] == "not-retained"
    assert incident["canonical_response_body_retention_state"] == "not-retained"
    assert incident["canonical_redirect_accounting_state"] == "not-retained"
    assert incident["canonical_replay_bytes_retained"] == 0
    assert incident["canonical_http_exchange_completed"] == "unknown"
    assert incident["exact_failure_timestamp_retained"] is False
    assert body["predecessor_chain"]["activation_and_attempt_consumed"] is True
    assert body["predecessor_chain"]["retry_resume_repair_or_terminal_backfill_allowed"] is False
    authority = body["authority"]
    assert all(value == 0 for key, value in authority.items() if key.endswith("_count"))
    assert authority["canonical_pricing_terminal_created"] is False
    assert authority["execution_hash_or_candidate_created"] is False
    assert authority["cost_reserved_or_spent_usd"] == "0"
    assert authority["four_row_ac_executed"] is False


def test_gate_collision_orphan_and_linklike_paths_are_preserved(
    repository: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _state = repository
    gate = root / d134.GATE_PATH
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_bytes(b"foreign-d134-gate")
    with pytest.raises(d134.D134PricingConsumedIncidentError):
        d134.run_d134_offline_source_gate(repository=root)
    assert gate.read_bytes() == b"foreign-d134-gate"
    gate.unlink()

    terminal = root / d134.TERMINAL_PATH
    terminal.write_bytes(b"orphan-procedural-terminal")
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="unexpected path"):
        d134.run_d134_offline_source_gate(repository=root)
    assert terminal.read_bytes() == b"orphan-procedural-terminal"
    assert not gate.exists()
    terminal.unlink()

    gate.write_bytes(b"linklike-gate")
    real_linklike = d134.d131.d129_offline._is_linklike
    monkeypatch.setattr(
        d134.d131.d129_offline,
        "_is_linklike",
        lambda path: path == gate or real_linklike(path),
    )
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="linklike"):
        d134._write_new(root, d134.GATE_PATH, b"replacement")
    assert gate.read_bytes() == b"linklike-gate"

    gate.unlink()
    unsafe_parent = root / "reports" / "live-pilot"
    monkeypatch.setattr(
        d134.d131.d129_offline,
        "_is_linklike",
        lambda path: path == unsafe_parent or real_linklike(path),
    )
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="parent is unsafe"):
        d134._write_new(root, d134.GATE_PATH, b"never-written")
    assert not gate.exists()


def test_rehashed_gate_tamper_and_wrong_post_evidence_scope_are_rejected(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, payload, raw = _build_gate(root)
    gate = root / d134.GATE_PATH
    tampered = copy.deepcopy(payload)
    tampered["semantic_body"]["authority"]["d134_source_builder_network_call_count"] = 1
    tampered_raw = _rewrite_envelope(gate, tampered, prefix="d134")
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="full rebuild"):
        d134.validate_d134_offline_source_gate(repository=root)
    assert gate.read_bytes() == tampered_raw

    gate.write_bytes(raw)
    marker = root / MARKER_PATH
    marker_raw = marker.read_bytes()
    marker.write_bytes(b"tampered-marker-must-not-be-repaired")
    with pytest.raises(d134.D134PricingConsumedIncidentError):
        d134.validate_d134_offline_source_gate(repository=root)
    assert marker.read_bytes() == b"tampered-marker-must-not-be-repaired"
    marker.write_bytes(marker_raw)

    state["head"] = GATE_COMMIT
    post = d134.validate_d134_offline_source_gate(repository=root, mode="post-evidence-commit")
    binding = post["evidence_commit"]
    assert binding == {
        "commit": GATE_COMMIT,
        "tree": GATE_TREE,
        "parents": [SOURCE_COMMIT],
        "artifact_path": d134.GATE_PATH.as_posix(),
        "artifact_blob_oid": "8" * 40,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }
    assert len(d134.ACTIVE_DOC_PATHS) == 10

    state["extra_diff"][GATE_COMMIT] = [{"status": "M", "path": "patchloop/agent/model.py"}]
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="evidence scope"):
        d134.validate_d134_offline_source_gate(repository=root, mode="post-evidence-commit")
    assert gate.read_bytes() == raw


def test_terminalization_template_is_exact_read_only_and_requires_gate_commit(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, payload, raw = _build_gate(root)
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="not clean"):
        d134.render_d134_terminalization_approval_template(repository=root)

    state["head"] = GATE_COMMIT
    before = (root / d134.GATE_PATH).read_bytes()
    template = d134.render_d134_terminalization_approval_template(repository=root)
    post = d134.validate_d134_offline_source_gate(repository=root, mode="post-evidence-commit")
    assert f"Gate ID: {payload['gate_id']}" in template
    assert f"Gate body SHA: {payload['semantic_body_hash']}" in template
    assert f"Gate file SHA: {sha256_bytes(raw)}" in template
    assert f"Gate file bytes: {len(raw)}" in template
    assert f"Gate evidence commit tuple: {canonical_json(post['evidence_commit'])}" in template
    assert all(f"- {value}" in template for value in d134.TERMINALIZATION_SCOPE)
    assert all(f"- {value}" in template for value in d134.TERMINALIZATION_EXCLUSIONS)
    assert "not canonical pricing evidence" in template
    assert "not approval" in template.lower()
    assert "new exact user message" in template.lower()
    assert (root / d134.GATE_PATH).read_bytes() == before
    assert not (root / d134.TERMINAL_PATH).exists()


def test_procedural_terminal_is_canonical_idempotent_and_preserves_unknowns(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    first, payload, raw = _create_terminal(root, state)
    second = d134.create_d134_procedural_terminal(repository=root)
    third = d134.validate_d134_procedural_terminal(repository=root)

    assert first == second == third
    assert state["writes"] == [d134.GATE_PATH, d134.TERMINAL_PATH]
    assert tuple(payload) == d134.ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d134.TERMINAL_BODY_KEYS
    assert payload["schema_version"] == d134.TERMINAL_SCHEMA
    assert payload["artifact_id"] == (
        f"d134pricingincident_{payload['semantic_body_hash'].removeprefix('sha256:')}"
    )
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert first["file_sha256"] == sha256_bytes(raw)
    assert first["file_bytes"] == len(raw)
    assert first["external_call_count"] == 0

    body = payload["semantic_body"]
    incident = body["incident_observation"]
    assert incident["activation_and_pricing_attempt_consumed"] is True
    assert incident["application_level_client_send_returned_response_count"] == 1
    assert incident["application_level_request_was_unauthenticated"] is True
    assert incident["observation_provenance"] == (
        "user-approved-current-session-control-flow-observation-not-reconstructed-machine-telemetry"
    )
    assert incident["underlying_http_request_count"] == "unknown"
    assert incident["canonical_pricing_capture_count"] == 0
    assert incident["canonical_pricing_capture_get_count"] == 0
    assert incident["canonical_pricing_evidence_artifact_created"] is False
    assert incident["canonical_response_status_retention_state"] == "not-retained"
    assert incident["canonical_response_headers_retention_state"] == "not-retained"
    assert incident["canonical_response_body_retention_state"] == "not-retained"
    assert incident["canonical_redirect_accounting_state"] == "not-retained"
    assert incident["canonical_replay_bytes_retained"] == 0
    assert incident["canonical_http_exchange_completed"] == "unknown"
    assert incident["exact_failure_timestamp_retained"] is False
    assert incident["retry_resume_repair_or_backfill_allowed"] is False
    assert body["evidence_boundary"]["procedural_terminal_is_not_canonical_pricing_evidence"]
    authority = body["authority"]
    assert all(value == 0 for key, value in authority.items() if key.endswith("_count"))
    assert authority["canonical_pricing_terminal_created"] is False
    assert authority["execution_hash_or_candidate_created"] is False
    assert authority["cost_reserved_or_spent_usd"] == "0"
    assert authority["four_row_ac_executed"] is False
    assert all(not (root / path).exists() for path in d134.CANONICAL_D132_DESCENDANT_PATHS)


def test_terminal_collision_and_canonical_descendant_orphan_are_preserved(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)
    terminal = root / d134.TERMINAL_PATH
    terminal.write_bytes(b"foreign-procedural-terminal")
    with pytest.raises(d134.D134PricingConsumedIncidentError):
        d134.create_d134_procedural_terminal(repository=root)
    assert terminal.read_bytes() == b"foreign-procedural-terminal"
    terminal.unlink()

    canonical = root / CANONICAL_PRICING_PATH
    canonical.write_bytes(b"forbidden-canonical-terminal")
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="unexpected path"):
        d134.create_d134_procedural_terminal(repository=root)
    assert canonical.read_bytes() == b"forbidden-canonical-terminal"
    assert not terminal.exists()


def test_rehashed_terminal_tamper_and_chronology_inversion_are_rejected(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, payload, raw = _create_terminal(root, state)
    terminal = root / d134.TERMINAL_PATH

    tampered = copy.deepcopy(payload)
    tampered["semantic_body"]["incident_observation"][
        "canonical_response_status_retention_state"
    ] = "retained"
    tampered_raw = _rewrite_envelope(terminal, tampered, prefix="d134pricingincident")
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="full rebuild"):
        d134.validate_d134_procedural_terminal(repository=root)
    assert terminal.read_bytes() == tampered_raw

    terminal.write_bytes(raw)
    inverted = copy.deepcopy(payload)
    inverted["semantic_body"]["recorded_at"] = GATE_RECORDED_AT
    inverted_raw = _rewrite_envelope(terminal, inverted, prefix="d134pricingincident")
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="chronology"):
        d134.validate_d134_procedural_terminal(repository=root)
    assert terminal.read_bytes() == inverted_raw


def test_terminal_only_commit_is_exact_gate_child_and_rejects_extra_scope(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, _payload, raw = _create_terminal(root, state)
    state["head"] = TERMINAL_COMMIT
    post = d134.validate_d134_procedural_terminal(repository=root, mode="post-terminal-commit")
    assert post["terminal_commit"] == {
        "commit": TERMINAL_COMMIT,
        "tree": TERMINAL_TREE,
        "parents": [GATE_COMMIT],
        "artifact_path": d134.TERMINAL_PATH.as_posix(),
        "artifact_blob_oid": "9" * 40,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "single_artifact_add_commit": True,
    }
    assert post["external_call_count"] == 0

    state["extra_diff"][TERMINAL_COMMIT] = [{"status": "M", "path": "docs/current-status.md"}]
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="terminal commit scope"):
        d134.validate_d134_procedural_terminal(repository=root, mode="post-terminal-commit")

    state["extra_diff"].clear()
    state["identity_overrides"][TERMINAL_COMMIT] = {
        "commit": TERMINAL_COMMIT,
        "tree": TERMINAL_TREE,
        "parents": ["0" * 40],
    }
    with pytest.raises(d134.D134PricingConsumedIncidentError, match="terminal commit parent"):
        d134.validate_d134_procedural_terminal(repository=root, mode="post-terminal-commit")
