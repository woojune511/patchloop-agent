from __future__ import annotations

import copy
import inspect
import json
from contextlib import nullcontext
from pathlib import Path

import pytest

from patchloop.evals import d132_d130_external_activation_offline as d132
from patchloop.util import canonical_json, sha256_bytes

TIMESTAMP = "2026-08-09T12:00:00Z"
SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
EVIDENCE_COMMIT = "c" * 40
EVIDENCE_TREE = "d" * 40


def _fake_predecessor() -> dict[str, object]:
    return {
        "d131_gate": {
            "gate_id": d132.D131_GATE_ID,
            "semantic_body_hash": d132.D131_BODY_SHA256,
            "file_sha256": d132.D131_FILE_SHA256,
            "file_bytes": d132.D131_FILE_BYTES,
            "recorded_at": "2026-08-09T10:37:33Z",
            "evidence_commit_binding": {"commit": d132.D131_EVIDENCE_COMMIT},
        },
        "d130_local_admission_receipt": {
            "artifact_id": d132.D130_RECEIPT_ID,
            "semantic_body_hash": d132.D130_RECEIPT_BODY_SHA256,
            "file_sha256": d132.D130_RECEIPT_FILE_SHA256,
            "file_bytes": d132.D130_RECEIPT_FILE_BYTES,
            "recorded_at": "2026-08-09T11:16:27Z",
            "commit_binding": {"commit": d132.D130_RECEIPT_COMMIT},
        },
        "d130_armed_intent": {
            "artifact_id": d132.D130_INTENT_ID,
            "semantic_body_hash": d132.D130_INTENT_BODY_SHA256,
            "file_sha256": d132.D130_INTENT_FILE_SHA256,
            "file_bytes": d132.D130_INTENT_FILE_BYTES,
            "recorded_at": "2026-08-09T11:17:25Z",
            "commit_binding": {"commit": d132.D130_INTENT_COMMIT},
            "state": "ARMED_WAITING_EXACT_ACTIVATION",
        },
    }


def _configure_offline_repository(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, object]]:
    (root / d132.OUTPUT_PATH.parent).mkdir(parents=True)
    predecessor = _fake_predecessor()
    source = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d132.D130_INTENT_COMMIT],
        "branch": "codex/d132-test",
        "direct_predecessor_intent_commit": d132.D130_INTENT_COMMIT,
        "implementation_paths_added": [path.as_posix() for path in d132.IMPLEMENTATION_PATHS],
        "file_bindings": [],
        "loaded_module_bindings": [],
        "git_cli_observation": {},
        "clean_committed_source": True,
    }
    state: dict[str, object] = {
        "head": SOURCE_COMMIT,
        "predecessor": predecessor,
        "source": source,
        "post_commit": False,
        "status_override": None,
        "time_index": 0,
    }

    monkeypatch.setattr(d132, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d132, "_d130_predecessor_binding", lambda _root: copy.deepcopy(predecessor))
    monkeypatch.setattr(d132, "_source_identity_for_gate", lambda _root: copy.deepcopy(source))

    def validate_source(_root: Path, value: object) -> None:
        assert canonical_json(value) == canonical_json(source)

    monkeypatch.setattr(d132, "_validate_source_identity", validate_source)
    monkeypatch.setattr(d132, "_head", lambda _root: state["head"])

    def now() -> str:
        index = int(state["time_index"])
        state["time_index"] = index + 1
        return f"2026-08-09T12:{index:02d}:00Z"

    monkeypatch.setattr(d132, "_now", now)

    def status_lines(_root: Path) -> list[str]:
        if state["status_override"] is not None:
            return list(state["status_override"])
        if state["post_commit"]:
            return []
        return [f"?? {d132.OUTPUT_PATH.as_posix()}"] if (root / d132.OUTPUT_PATH).exists() else []

    monkeypatch.setattr(d132, "_status_lines", status_lines)

    def write_new(_root: Path, relative: Path, raw: bytes) -> None:
        selected = root / relative
        selected.parent.mkdir(parents=True, exist_ok=True)
        with selected.open("xb") as handle:
            handle.write(raw)
        if relative != d132.OUTPUT_PATH:
            line = f"?? {relative.as_posix()}"
            pending = list(state["status_override"] or [])
            if line not in pending:
                pending.append(line)
            state["status_override"] = pending

    monkeypatch.setattr(d132, "_write_new", write_new)
    return root, state


@pytest.fixture
def offline_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict[str, object]]:
    return _configure_offline_repository(tmp_path, monkeypatch)


def _seal_offline_gate(
    root: Path,
    state: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    gate = d132.run_d132_offline_source_gate(repository=root)
    state["head"] = EVIDENCE_COMMIT
    state["post_commit"] = True
    state["status_override"] = []
    monkeypatch.setattr(
        d132,
        "_rebuild_gate_evidence_commit",
        lambda _root, *, commit, source, gate_raw: {
            "commit": commit,
            "tree": EVIDENCE_TREE,
            "parents": [source["commit"]],
            "artifact_path": d132.OUTPUT_PATH.as_posix(),
            "artifact_blob_oid": "e" * 40,
            "artifact_file_sha256": sha256_bytes(gate_raw),
            "artifact_file_bytes": len(gate_raw),
            "exact_gate_add_and_active_docs_modify_commit": True,
        },
    )
    return gate


def _install_fake_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, dict[str, object]]:
    commits: dict[str, dict[str, object]] = {}

    def commit_identity(_root: Path, commit: str) -> dict[str, object]:
        record = commits[commit]
        return {
            "commit": commit,
            "tree": record["tree"],
            "parents": record["parents"],
            "branch": "codex/d132-test",
        }

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        return copy.deepcopy(commits[commit]["rows"])

    def commit_blob(_root: Path, commit: str, path: Path) -> tuple[str, bytes]:
        oid, raw = commits[commit]["blobs"][path.as_posix()]
        return str(oid), bytes(raw)

    monkeypatch.setattr(d132, "_commit_identity", commit_identity)
    monkeypatch.setattr(d132, "_diff_rows", diff_rows)
    monkeypatch.setattr(d132, "_commit_blob", commit_blob)
    return commits


def _record_commit(
    commits: dict[str, dict[str, object]],
    *,
    commit: str,
    parent: str,
    rows: list[dict[str, str]],
    blobs: dict[Path, bytes],
) -> None:
    commits[commit] = {
        "tree": sha256_bytes(commit.encode()).removeprefix("sha256:")[:40],
        "parents": [parent],
        "rows": copy.deepcopy(rows),
        "blobs": {
            path.as_posix(): (
                sha256_bytes(raw).removeprefix("sha256:")[:40],
                raw,
            )
            for path, raw in blobs.items()
        },
    }


def _seal_activation_receipt(
    root: Path,
    state: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    _seal_offline_gate(root, state, monkeypatch)
    d132.create_d130_external_activation_receipt(repository=root)
    raw = (root / d132.ACTIVATION_RECEIPT_PATH).read_bytes()
    commits = _install_fake_commits(monkeypatch)
    commit = "f" * 40
    _record_commit(
        commits,
        commit=commit,
        parent=EVIDENCE_COMMIT,
        rows=[{"status": "A", "path": d132.ACTIVATION_RECEIPT_PATH.as_posix()}],
        blobs={d132.ACTIVATION_RECEIPT_PATH: raw},
    )
    state["head"] = commit
    state["status_override"] = []
    return commits, d132._current_receipt_commit_identity(root)


def _install_external_mocks(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    docker_ready: bool = True,
    raise_phase: str | None = None,
) -> dict[str, object]:
    calls: dict[str, int] = {
        "docker": 0,
        "pricing": 0,
        "docker_snapshot": 0,
        "sdk": 0,
    }
    observations: dict[str, dict[str, object]] = {}
    original_boundary = d132._terminal_status_and_boundary
    original_pricing_capture = d132.pricing_capture.capture_official_pricing_evidence
    original_sdk_observation = d132._sdk_observation
    original_validate_sdk = d132._validate_sdk_observation
    original_validate_terminal = d132._validate_terminal_artifact
    terminal_cache: dict[tuple[str, str, str], tuple[dict[str, object], bytes]] = {}

    def validate_terminal_cached(
        selected_root: Path, phase: str
    ) -> tuple[dict[str, object], bytes]:
        raw = (selected_root / d132.PHASE_PATHS[phase][2]).read_bytes()
        key = (str(selected_root), phase, sha256_bytes(raw))
        if key not in terminal_cache:
            terminal_cache[key] = original_validate_terminal(selected_root, phase)
        return copy.deepcopy(terminal_cache[key])

    monkeypatch.setattr(d132, "_validate_terminal_artifact", validate_terminal_cached)
    monkeypatch.setattr(d132, "_require_external_helper_contracts", lambda: None)
    monkeypatch.setattr(
        d132.docker_remediation,
        "validate_docker_no_start_remediation_observation",
        lambda value: value,
    )
    monkeypatch.setattr(
        d132.docker_remediation,
        "validate_docker_readiness_snapshot",
        lambda value: value,
    )

    def check_marker(phase: str) -> None:
        _attempt, started, terminal = d132.PHASE_PATHS[phase]
        assert (root / started).is_file()
        assert not (root / terminal).exists()
        if raise_phase == phase:
            raise RuntimeError(f"simulated {phase} helper crash")

    def remediate() -> dict[str, object]:
        phase = "docker-image-readiness-remediation"
        calls["docker"] += 1
        check_marker(phase)
        value = {
            "passed": docker_ready,
            "observed_blockers": [] if docker_ready else ["daemon-unavailable"],
            "docker_cli_command_count": 6 if docker_ready else 3,
            "image_store_mutation_count": 0,
        }
        observations[phase] = value
        return copy.deepcopy(value)

    model_page = (
        b"# GPT-5.4 mini\n"
        b"Default snapshot: `gpt-5.4-mini-2026-03-17`\n"
        b"| Input | $0.75 | 1M tokens |\n"
        b"| Cached input | $0.075 | 1M tokens |\n"
        b"| Output | $4.5 | 1M tokens |\n"
        b"| Responses | `v1/responses` | Supported |\n"
        b"| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |\n"
    )
    monkeypatch.setattr(
        d132.pricing_capture,
        "_capture_response",
        lambda: (
            {
                "final_url": d132.pricing_capture.OFFICIAL_MODEL_PAGE_URL,
                "http_status": 200,
                "content_type": "text/markdown; charset=utf-8",
                "content_encoding": None,
                "etag": '"d132-test"',
                "redirect_count": 0,
                "public_get_request_count": 1,
            },
            model_page,
        ),
    )
    monkeypatch.setattr(
        d132.pricing_capture,
        "_utc_now_text",
        lambda: "2026-08-09T12:05:30Z",
    )

    def capture() -> dict[str, object]:
        phase = "official-pricing-capture"
        calls["pricing"] += 1
        check_marker(phase)
        value = original_pricing_capture()
        observations[phase] = value
        return copy.deepcopy(value)

    cli = {
        "file_name": "docker.exe",
        "file_bytes": d132.docker_remediation.APPROVED_CLI_BYTES,
        "file_sha256": d132.docker_remediation.APPROVED_CLI_SHA256,
        "linklike": False,
    }

    def observe() -> dict[str, object]:
        phase = "read-only-no-call-preflight"
        calls["docker_snapshot"] += 1
        check_marker(phase)
        return {
            "observation": {"passed": True},
            "docker_cli_command_count": 3,
            "read_only_daemon_or_image_call_count": 3,
        }

    d127_sdk = {
        "checks": {"all_mocked_contracts_passed": True},
        "network_call_count": 0,
        "synthetic_endpoint_probe": {
            "passed": True,
            "transport_attempt_count": 0,
        },
    }
    sdk_bindings: list[dict[str, object]] = []
    for module_name in d132.SDK_MODULE_NAMES:
        module_path = root / ".venv" / "Lib" / "site-packages" / module_name / "__init__.py"
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_bytes(f"# mocked {module_name} module\n".encode())
        sdk_bindings.append(
            {
                "module_name": module_name,
                "resolved_path": str(module_path.resolve(strict=True)),
                **d132.d127._bounded_external_file_binding(
                    module_path.resolve(strict=True), maximum_bytes=4 * 1024 * 1024
                ),
                "under_repository_venv": True,
            }
        )
    sdk = {
        "python_routing_environment_presence": {
            name: False for name in d132.d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES
        },
        "python_routing_environment_values_persisted": False,
        "d127_sdk_probe_skipped_due_to_python_routing": False,
        "loaded_sdk_module_bindings": sdk_bindings,
        "d127_sdk_observation": d127_sdk,
    }

    def sdk_observation(*_args: object, **_kwargs: object) -> dict[str, object]:
        calls["sdk"] += 1
        check_marker("read-only-no-call-preflight")
        observations["read-only-no-call-preflight"] = sdk
        return copy.deepcopy(sdk)

    def terminal_boundary(
        selected_root: Path,
        phase: str,
        recorded_at: str,
        observation: dict[str, object],
    ) -> tuple[str, bool, list[str], dict[str, int]]:
        if phase == "official-pricing-capture":
            return original_boundary(selected_root, phase, recorded_at, observation)
        if phase == "docker-image-readiness-remediation":
            return (
                d132.DOCKER_READY_STATUS if docker_ready else d132.DOCKER_BLOCKED_STATUS,
                docker_ready,
                [] if docker_ready else ["daemon-unavailable"],
                {
                    "docker_cli_command_count": 6 if docker_ready else 3,
                    "read_only_daemon_or_image_call_count": 6 if docker_ready else 3,
                    "image_pull_call_count": 0,
                    "docker_image_store_mutation_count": 0,
                    "official_public_get_request_count": 0,
                    "sdk_credential_or_endpoint_observation_count": 0,
                    "sdk_transport_attempt_count": 0,
                    "sdk_network_call_count": 0,
                },
            )
        return (
            d132.PREFLIGHT_READY_STATUS,
            True,
            [],
            {
                "docker_cli_command_count": 6,
                "read_only_daemon_or_image_call_count": 6,
                "image_pull_call_count": 0,
                "docker_image_store_mutation_count": 0,
                "official_public_get_request_count": 0,
                "sdk_credential_or_endpoint_observation_count": 1,
                "sdk_transport_attempt_count": 0,
                "sdk_network_call_count": 0,
            },
        )

    monkeypatch.setattr(
        d132.docker_remediation,
        "remediate_already_running_docker_environment",
        remediate,
    )
    monkeypatch.setattr(d132.pricing_capture, "capture_official_pricing_evidence", capture)
    monkeypatch.setattr(d132.docker_remediation, "approved_cli_binding", lambda: dict(cli))
    monkeypatch.setattr(d132.docker_remediation, "observe_docker_readiness", observe)
    monkeypatch.setattr(d132.d127, "_model_factory_contract", lambda _root: {"passed": True})
    monkeypatch.setattr(d132, "_sdk_observation", sdk_observation)
    monkeypatch.setattr(d132, "_validate_sdk_observation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(d132, "_terminal_status_and_boundary", terminal_boundary)
    return {
        "calls": calls,
        "observations": observations,
        "model_page": model_page,
        "original_terminal_boundary": original_boundary,
        "original_sdk_observation": original_sdk_observation,
        "original_validate_sdk_observation": original_validate_sdk,
        "clear_terminal_cache": terminal_cache.clear,
    }


def _commit_attempt(
    root: Path,
    state: dict[str, object],
    commits: dict[str, dict[str, object]],
    *,
    phase: str,
    commit: str,
) -> dict[str, object]:
    attempt_path = d132.PHASE_PATHS[phase][0]
    raw = (root / attempt_path).read_bytes()
    attempt = json.loads(raw)
    parent = attempt["semantic_body"]["parent_commit_binding"]["commit"]
    _record_commit(
        commits,
        commit=commit,
        parent=parent,
        rows=[{"status": "A", "path": attempt_path.as_posix()}],
        blobs={attempt_path: raw},
    )
    state["head"] = commit
    state["status_override"] = []
    return d132._current_attempt_commit_identity(root, phase=phase)


def _commit_transition(
    root: Path,
    state: dict[str, object],
    commits: dict[str, dict[str, object]],
    *,
    phase: str,
    commit: str,
) -> dict[str, object]:
    _attempt, started_path, terminal_path = d132.PHASE_PATHS[phase]
    started_raw = (root / started_path).read_bytes()
    terminal_raw = (root / terminal_path).read_bytes()
    started = json.loads(started_raw)
    parent = started["semantic_body"]["attempt_commit_binding"]["commit"]
    _record_commit(
        commits,
        commit=commit,
        parent=parent,
        rows=[
            {"status": "A", "path": started_path.as_posix()},
            {"status": "A", "path": terminal_path.as_posix()},
        ],
        blobs={started_path: started_raw, terminal_path: terminal_raw},
    )
    state["head"] = commit
    state["status_override"] = []
    return d132._current_phase_transition_commit_identity(root, phase=phase)


def _docker_result(
    tail: tuple[str, ...],
    *,
    stdout: bytes = b"",
    stderr: bytes = b"",
    return_code: int = 0,
) -> d132.d127_docker.BoundedCommandResult:
    return d132.d127_docker.BoundedCommandResult(
        argv=("docker.exe", *tail),
        return_code=return_code,
        timed_out=False,
        stdout_prefix=stdout,
        stderr_prefix=stderr,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
    )


def _docker_snapshot(
    states: tuple[str, str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    daemon = {
        "ClientVersion": d132.docker_remediation.APPROVED_CLI_VERSION,
        "ServerVersion": "29.6.2",
        "ServerOs": "linux",
        "ServerArch": "amd64",
    }
    version_stdout = (json.dumps(daemon, separators=(",", ":")) + "\n").encode()
    rows: list[dict[str, object]] = [
        _docker_result(
            ("version", "--format", d132.d127_docker.d126.DOCKER_VERSION_FORMAT),
            stdout=version_stdout,
        ).summary("daemon-version")
    ]
    images: dict[str, object] = {}
    for index, (key, state) in enumerate(zip(("moto", "babel"), states, strict=True)):
        image = d132.docker_remediation.EXACT_DOCKER_IMAGES[index]
        tail = (
            "image",
            "inspect",
            "--format",
            d132.d127_docker.IMAGE_PROJECTION_FORMAT,
            image,
        )
        if state == "present":
            projection = {
                "requested_repo_digest": image,
                "requested_digest": image.rsplit("@", 1)[1],
                "config_id": "sha256:" + str(index + 1) * 64,
                "repo_digests": [image],
                "matched_repo_digest": image,
            }
            stdout = (
                json.dumps(
                    {"Id": projection["config_id"], "RepoDigests": [image]},
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
            result = _docker_result(tail, stdout=stdout)
        else:
            stderr = f"Error response from daemon: No such image: {image}\n".encode()
            result = _docker_result(tail, stderr=stderr, return_code=1)
            projection = d132.d127_docker._confirmed_missing_projection(result, image)
            assert projection is not None
        rows.append(result.summary(f"image-{key}"))
        images[key] = projection
    return {
        "daemon": daemon,
        "images": images,
        "passed": states == ("present", "present"),
    }, rows


def _source(function: object) -> str:
    return inspect.getsource(function)


def _module_source() -> str:
    return Path(d132.__file__).read_text(encoding="utf-8")


def test_exact_d132_and_future_artifact_paths_are_disjoint() -> None:
    assert (
        Path(
            "reports/live-pilot/artifacts/"
            "d132-d130-external-activation-successor-offline-source-gate.json"
        )
        == d132.OUTPUT_PATH
    )
    assert (
        Path("reports/live-pilot/artifacts/d130-external-activation-receipt.json")
        == d132.ACTIVATION_RECEIPT_PATH
    )
    assert d132.DOCKER_ATTEMPT_PATH != d132.DOCKER_TERMINAL_PATH
    assert d132.PRICING_ATTEMPT_PATH != d132.PRICING_PATH
    assert d132.PREFLIGHT_ATTEMPT_PATH != d132.PREFLIGHT_PATH
    assert d132.GATE_PATH not in {
        d132.OUTPUT_PATH,
        d132.ACTIVATION_RECEIPT_PATH,
        d132.DOCKER_ATTEMPT_PATH,
        d132.DOCKER_TERMINAL_PATH,
        d132.PRICING_ATTEMPT_PATH,
        d132.PRICING_PATH,
        d132.PREFLIGHT_ATTEMPT_PATH,
        d132.PREFLIGHT_PATH,
    }


def test_exact_d131_gate_tuple_and_commit_are_bound() -> None:
    assert d132.D131_GATE_ID == (
        "d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057"
    )
    assert d132.D131_BODY_SHA256 == (
        "sha256:849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057"
    )
    assert d132.D131_FILE_SHA256 == (
        "sha256:8dfcd275b3e66113bc92df64e33bcf14f80c101cba2e40246d42b61f22dac048"
    )
    assert d132.D131_FILE_BYTES == 14_516
    assert d132.D131_EVIDENCE_COMMIT == "283b9124af38252f47a06cbb1a484807b5030be2"
    assert d132.D131_EVIDENCE_TREE == "78b62219f438b695ca3bf26d5de77a5ccf175e21"
    assert d132.D131_EVIDENCE_PARENT == "9cd736c0221bba17375c3b7ddce02e5214fc21fe"
    assert d132.D131_GATE_BLOB_OID == "c4e7135a66a2d1d7ca85dd60685f9cb8a8c01cfd"


def test_exact_d130_local_receipt_tuple_and_commit_are_bound() -> None:
    assert d132.D130_RECEIPT_ID == (
        "d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010"
    )
    assert d132.D130_RECEIPT_BODY_SHA256 == (
        "sha256:03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010"
    )
    assert d132.D130_RECEIPT_FILE_SHA256 == (
        "sha256:01901a4f20a0231856e0326d2bc37283794b9cff998463707bc19b15d22731ba"
    )
    assert d132.D130_RECEIPT_FILE_BYTES == 11_514
    assert d132.D130_RECEIPT_COMMIT == "6987246b438fa6e6e711fa3b254aaf75ac4c2a66"
    assert d132.D130_RECEIPT_TREE == "13c52c79d3f58cc8fcfd584eb7d6df7536e76b9d"
    assert d132.D130_RECEIPT_PARENT == d132.D131_EVIDENCE_COMMIT
    assert d132.D130_RECEIPT_BLOB_OID == "879ac90cc3a4e61cc97fadf930426d6ba74e4422"


def test_exact_d130_armed_intent_tuple_and_commit_are_bound() -> None:
    assert d132.D130_INTENT_ID == (
        "d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153"
    )
    assert d132.D130_INTENT_BODY_SHA256 == (
        "sha256:4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153"
    )
    assert d132.D130_INTENT_FILE_SHA256 == (
        "sha256:349d6680850374c1cee10e49f3319ef18bdd3640c48d075e999cbefac72c460c"
    )
    assert d132.D130_INTENT_FILE_BYTES == 13_175
    assert d132.D130_INTENT_COMMIT == "4a40971b4e155683c49bbd6bcadc7468514ef84c"
    assert d132.D130_INTENT_TREE == "40dc0b5193dde2a58b176f791e807b798540888c"
    assert d132.D130_INTENT_PARENT == d132.D130_RECEIPT_COMMIT
    assert d132.D130_INTENT_BLOB_OID == "2ac0ef87a4783db396aefa2abe1e777dc2c640bb"


def test_predecessor_commit_chain_is_linear_and_activation_is_not_reused() -> None:
    assert d132.D130_RECEIPT_PARENT == d132.D131_EVIDENCE_COMMIT
    assert d132.D130_INTENT_PARENT == d132.D130_RECEIPT_COMMIT
    source = _module_source()
    assert "request" in source.casefold() or "challenge" in source.casefold()
    assert "unexercised" in source.casefold()
    assert "fresh" in d132.STATUS.casefold()
    assert "reus" in source.casefold()
    assert "effective_activation_approval" in source


def test_source_bindings_exclude_historical_d128_top_level_runner() -> None:
    assert (
        Path("patchloop/evals/d132_d130_external_activation_offline.py"),
        Path("scripts/build_d132_d130_external_activation_offline.py"),
        Path("tests/test_d132_d130_external_activation_offline.py"),
    ) == d132.IMPLEMENTATION_PATHS
    bound = {path.as_posix() for path in d132.SOURCE_BINDING_PATHS}
    assert "patchloop/evals/d128_terminal_successor_no_call_preflight.py" not in bound
    source = _module_source()
    assert "import d128_terminal_successor_no_call_preflight" not in source
    assert "d128.run_d128_external_no_call_preflight" not in source


def test_public_api_names_signatures_and_schemas_are_exact() -> None:
    functions = (
        d132.run_d132_offline_source_gate,
        d132.validate_d132_offline_source_gate,
        d132.render_d132_external_activation_template,
        d132.create_d130_external_activation_receipt,
        d132.validate_d130_external_activation_receipt,
        d132.run_d130_external_no_call_preflight,
        d132.validate_d130_external_no_call_gate,
    )
    for function in functions:
        assert "repository" in inspect.signature(function).parameters
    assert "mode" in inspect.signature(d132.validate_d132_offline_source_gate).parameters
    assert "mode" in inspect.signature(d132.validate_d130_external_activation_receipt).parameters
    assert "mode" in inspect.signature(d132.validate_d130_external_no_call_gate).parameters
    assert d132.ACTIVATION_RECEIPT_SCHEMA.endswith("-d132-v1")
    assert d132.ATTEMPT_SCHEMA.endswith("-d132-v1")
    assert d132.ACTION_STARTED_SCHEMA.endswith("-d132-v1")
    assert d132.DOCKER_SCHEMA.endswith("-d132-v1")
    assert d132.PRICING_SCHEMA.endswith("-d132-v1")
    assert d132.PREFLIGHT_SCHEMA.endswith("-d132-v1")
    assert d132.FINAL_GATE_SCHEMA.endswith("-d132-v1")


def test_offline_gate_builder_has_no_future_writer_or_external_helper_call(
    offline_repository: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _state = offline_repository

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("future or external path invoked by offline builder")

    for name in (
        "create_d130_external_activation_receipt",
        "run_d130_external_no_call_preflight",
    ):
        monkeypatch.setattr(d132, name, forbidden)
    monkeypatch.setattr(
        d132.docker_remediation, "remediate_already_running_docker_environment", forbidden
    )
    monkeypatch.setattr(d132.pricing_capture, "capture_official_pricing_evidence", forbidden)

    first = d132.run_d132_offline_source_gate(repository=root)
    raw = (root / d132.OUTPUT_PATH).read_bytes()
    payload = json.loads(raw)
    second = d132.run_d132_offline_source_gate(repository=root)

    assert first == second
    assert raw == (root / d132.OUTPUT_PATH).read_bytes() == d132._pretty_bytes(payload)
    assert payload["gate_id"] == first["gate_id"]
    assert payload["semantic_body_hash"] == first["semantic_body_hash"]
    assert sha256_bytes(raw) == first["file_sha256"]
    assert all(not (root / path).exists() for path in d132.FUTURE_PATHS)


def test_offline_gate_contract_keeps_future_paths_absent_and_authority_zero(
    offline_repository: tuple[Path, dict[str, object]],
) -> None:
    root, _state = offline_repository
    d132.run_d132_offline_source_gate(repository=root)
    payload = json.loads((root / d132.OUTPUT_PATH).read_bytes())
    body = payload["semantic_body"]

    incident = body["pre_source_activation_incident"]
    assert incident["exact_activation_request_or_challenge_received"] is True
    assert incident["message_explicitly_said_challenge_is_not_activation"] is True
    assert incident["effective_activation_approval_recorded"] is False
    assert (
        incident[
            "activation_message_was_received_before_committed_activation_receipt_writer_existed"
        ]
        is True
    )
    assert incident["received_activation_binding"] == {
        "request_title": "D-130 external no-call preflight exact activation request",
        "quoted_d131_gate_receipt_intent_and_both_commit_tuples": True,
        "approved_scope": list(d132.d131.ACTIVATION_SCOPE),
        "explicitly_not_authorized": list(d132.d131.ACTIVATION_EXCLUSIONS),
    }
    assert incident["activation_receipt_created"] is False
    assert incident["external_phase_attempt_created"] is False
    assert incident["external_action_count"] == 0
    assert incident["activation_exercised"] is False
    assert incident["activation_is_nonretroactive"] is True
    assert incident["activation_is_nonreusable_after_d132_topology_change"] is True
    source_approval = body["d132_source_preparation_approval"]
    assert source_approval["approval_received"] is True
    assert source_approval["approved_scope"] == list(d132.D132_SOURCE_PREPARATION_SCOPE)
    assert source_approval["explicitly_not_authorized"] == list(
        d132.D132_SOURCE_PREPARATION_EXCLUSIONS
    )
    assert source_approval["offline_source_only"] is True
    assert source_approval["future_writer_or_external_helper_invocation_authorized"] is False
    authority = body["authority"]
    assert authority["official_docs_or_network_call_count"] == 0
    assert authority["canonical_pricing_capture_get_count"] == 0
    assert authority["docker_cli_daemon_image_or_container_call_count"] == 0
    assert authority["sdk_credential_or_endpoint_observation_count"] == 0
    assert authority["provider_evaluator_agent_call_count"] == 0
    assert authority["execution_hash_created"] is False
    assert authority["execution_candidate_created"] is False
    assert authority["cost_reserved_or_spent_usd"] == "0"
    assert (
        body["implementation_integrity"]["gate_builder_activation_receipt_writer_invocation_count"]
        == 0
    )
    assert body["implementation_integrity"]["gate_builder_external_runner_invocation_count"] == 0

    tampered = copy.deepcopy(payload)
    tampered["semantic_body"]["authority"]["external_phase_authorized"] = True
    tampered = d132._gate_envelope(tampered["semantic_body"])
    collision = d132._pretty_bytes(tampered)
    (root / d132.OUTPUT_PATH).write_bytes(collision)
    with pytest.raises(d132.D132ActivationOfflineError, match="full rebuild"):
        d132.validate_d132_offline_source_gate(repository=root)
    assert (root / d132.OUTPUT_PATH).read_bytes() == collision


def test_fresh_activation_template_quotes_gate_receipt_intent_and_commits(
    offline_repository: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = offline_repository
    gate = _seal_offline_gate(root, state, monkeypatch)
    template = d132.render_d132_external_activation_template(repository=root)

    for value in (
        gate["gate_id"],
        d132.D131_GATE_ID,
        d132.D130_RECEIPT_ID,
        d132.D130_INTENT_ID,
        d132.D130_RECEIPT_COMMIT,
        d132.D130_INTENT_COMMIT,
        EVIDENCE_COMMIT,
    ):
        assert value in template
    assert "request/challenge was not effective activation and is non-reusable" in template
    assert "I approve the exact ordered scope above" in template
    assert "승인" in template or "approval" in template.casefold()
    assert "This template is not activation" not in template
    assert "This challenge is not activation" not in template


def test_activation_receipt_is_new_only_canonical_and_requires_receipt_only_commit(
    offline_repository: tuple[Path, dict[str, object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = offline_repository
    _seal_offline_gate(root, state, monkeypatch)

    first = d132.create_d130_external_activation_receipt(repository=root)
    receipt_path = root / d132.ACTIVATION_RECEIPT_PATH
    raw = receipt_path.read_bytes()
    payload = json.loads(raw)
    second = d132.create_d130_external_activation_receipt(repository=root)

    assert first == second
    assert raw == receipt_path.read_bytes() == d132._pretty_bytes(payload)
    assert payload["schema_version"] == d132.ACTIVATION_RECEIPT_SCHEMA
    assert payload["semantic_body"]["activation_approval"]["fresh_post_d132_activation"] is True
    assert payload["semantic_body"]["activation_approval"]["pre_source_activation_reused"] is False
    assert payload["semantic_body"]["activity_accounting"] == {
        "official_docs_or_network_call_count": 0,
        "canonical_pricing_capture_get_count": 0,
        "docker_cli_daemon_image_or_container_call_count": 0,
        "sdk_credential_or_endpoint_observation_count": 0,
        "provider_evaluator_agent_call_count": 0,
        "retrieval_or_memory_injection_count": 0,
        "cost_reserved_or_spent_usd": "0",
    }

    collision = b"existing-noncanonical-activation-receipt"
    receipt_path.write_bytes(collision)
    with pytest.raises(d132.D132ActivationOfflineError):
        d132.create_d130_external_activation_receipt(repository=root)
    assert receipt_path.read_bytes() == collision
    receipt_path.write_bytes(raw)

    orphan = root / d132.DOCKER_ATTEMPT_PATH
    orphan.write_bytes(b"orphaned-downstream-attempt")
    with pytest.raises(d132.D132ActivationOfflineError):
        d132.create_d130_external_activation_receipt(repository=root)
    assert orphan.read_bytes() == b"orphaned-downstream-attempt"
    orphan.unlink()

    receipt_commit = "f" * 40
    state["head"] = receipt_commit
    state["status_override"] = []
    monkeypatch.setattr(
        d132,
        "_commit_identity",
        lambda _root, commit: {
            "commit": commit,
            "tree": "1" * 40,
            "parents": [EVIDENCE_COMMIT],
            "branch": "codex/d132-test",
        },
    )
    monkeypatch.setattr(
        d132,
        "_diff_rows",
        lambda _root, _commit: [{"status": "A", "path": d132.ACTIVATION_RECEIPT_PATH.as_posix()}],
    )
    monkeypatch.setattr(
        d132,
        "_commit_blob",
        lambda _root, _commit, _path: ("2" * 40, raw),
    )
    committed = d132.validate_d130_external_activation_receipt(
        repository=root, mode="post-receipt-commit"
    )
    assert committed["receipt_commit"] == receipt_commit

    monkeypatch.setattr(
        d132,
        "_diff_rows",
        lambda _root, _commit: [
            {"status": "A", "path": d132.ACTIVATION_RECEIPT_PATH.as_posix()},
            {"status": "A", "path": "unexpected.txt"},
        ],
    )
    with pytest.raises(d132.D132ActivationOfflineError, match="artifact-only"):
        d132.validate_d130_external_activation_receipt(repository=root, mode="post-receipt-commit")


def test_each_external_phase_persists_attempt_before_action(
    offline_repository: tuple[Path, dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = offline_repository
    commits, receipt_commit = _seal_activation_receipt(root, state, monkeypatch)
    phase = "docker-image-readiness-remediation"
    attempt_path, started_path, terminal_path = d132.PHASE_PATHS[phase]
    receipt = json.loads((root / d132.ACTIVATION_RECEIPT_PATH).read_bytes())
    receipt_time = receipt["semantic_body"]["recorded_at"]

    monkeypatch.setattr(d132, "_now", lambda: receipt_time)
    with pytest.raises(d132.D132ActivationOfflineError, match="clock|chronology"):
        d132._create_attempt_artifact(
            root,
            phase=phase,
            parent_commit=receipt_commit,
            predecessor_terminal=None,
        )
    assert not (root / attempt_path).exists()

    monkeypatch.setattr(d132, "_now", lambda: "2026-08-09T12:10:00Z")
    attempt, attempt_raw = d132._create_attempt_artifact(
        root,
        phase=phase,
        parent_commit=receipt_commit,
        predecessor_terminal=None,
    )
    assert (root / attempt_path).exists()
    assert not (root / started_path).exists()
    assert not (root / terminal_path).exists()

    fake_attempt_commit = {
        "commit": "1" * 40,
        "tree": "2" * 40,
        "parents": [receipt_commit["commit"]],
    }
    with pytest.raises(d132.D132ActivationOfflineError, match="not clean"):
        d132._write_action_started(
            root,
            phase=phase,
            attempt_commit=fake_attempt_commit,
        )
    assert not (root / started_path).exists()

    attempt_commit = "1" * 40
    _record_commit(
        commits,
        commit=attempt_commit,
        parent=str(receipt_commit["commit"]),
        rows=[
            {"status": "A", "path": attempt_path.as_posix()},
            {"status": "A", "path": "unexpected.txt"},
        ],
        blobs={attempt_path: attempt_raw},
    )
    state["head"] = attempt_commit
    state["status_override"] = []
    with pytest.raises(d132.D132ActivationOfflineError, match="artifact-only"):
        d132._write_action_started(
            root,
            phase=phase,
            attempt_commit=fake_attempt_commit,
        )
    assert not (root / started_path).exists()

    _record_commit(
        commits,
        commit=attempt_commit,
        parent=str(receipt_commit["commit"]),
        rows=[{"status": "A", "path": attempt_path.as_posix()}],
        blobs={attempt_path: attempt_raw},
    )
    exact_attempt_commit = d132._current_attempt_commit_identity(root, phase=phase)
    attempt_time = attempt["semantic_body"]["recorded_at"]
    monkeypatch.setattr(d132, "_now", lambda: attempt_time)
    with pytest.raises(d132.D132ActivationOfflineError, match="clock"):
        d132._write_action_started(
            root,
            phase=phase,
            attempt_commit=exact_attempt_commit,
        )
    assert not (root / started_path).exists()

    monkeypatch.setattr(d132, "_now", lambda: "2026-08-09T12:11:00Z")
    started, _started_raw = d132._write_action_started(
        root,
        phase=phase,
        attempt_commit=exact_attempt_commit,
    )
    assert (root / started_path).exists()
    assert not (root / terminal_path).exists()

    monkeypatch.setattr(
        d132.docker_remediation,
        "validate_docker_no_start_remediation_observation",
        lambda value: value,
    )
    observation = {
        "passed": True,
        "observed_blockers": [],
        "docker_cli_command_count": 6,
        "image_store_mutation_count": 0,
    }
    monkeypatch.setattr(d132, "_now", lambda: started["semantic_body"]["recorded_at"])
    with pytest.raises(d132.D132ActivationOfflineError, match="clock"):
        d132._write_terminal(
            root,
            phase=phase,
            observation=observation,
            attempt_commit=exact_attempt_commit,
        )
    assert not (root / terminal_path).exists()


def test_docker_helper_is_exact_no_start_and_pull_scope_is_two_digest_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert d132.docker_remediation.APPROVED_CLI_VERSION == "29.6.2"
    assert d132.docker_remediation.LOCAL_DOCKER_ENDPOINT == (
        "npipe:////./pipe/dockerDesktopLinuxEngine"
    )
    images = tuple(d132.docker_remediation.EXACT_DOCKER_IMAGES)
    assert len(images) == 2
    assert all("@sha256:" in image for image in images)
    binding = {
        "file_name": "docker.exe",
        "file_bytes": d132.docker_remediation.APPROVED_CLI_BYTES,
        "file_sha256": d132.docker_remediation.APPROVED_CLI_SHA256,
        "linklike": False,
    }
    monkeypatch.setattr(
        d132.docker_remediation.d127,
        "_isolated_docker_config",
        lambda: nullcontext(),
    )
    monkeypatch.setattr(
        d132.docker_remediation.d127,
        "approved_cli_binding",
        lambda: dict(binding),
    )
    monkeypatch.setattr(
        d132.docker_remediation.d127,
        "_launch_desktop",
        lambda: pytest.fail("no-start helper must never launch Docker Desktop"),
    )

    cases = (
        (("present", "present"), ()),
        (("absent", "present"), (images[0],)),
        (("present", "absent"), (images[1],)),
        (("absent", "absent"), images),
    )
    for states, expected_pulls in cases:
        snapshots = iter((_docker_snapshot(states), _docker_snapshot(("present", "present"))))
        pulls: list[str] = []
        monkeypatch.setattr(
            d132.docker_remediation.d127,
            "_observe_readiness",
            lambda selected=snapshots: next(selected),
        )

        def pull(
            *tail: str,
            timeout_seconds: int,
            selected=pulls,
        ) -> d132.d127_docker.BoundedCommandResult:
            assert tail[:5] == (
                "image",
                "pull",
                "--quiet",
                "--platform",
                "linux/amd64",
            )
            assert timeout_seconds == 1_200
            selected.append(tail[-1])
            return _docker_result(tuple(tail), stdout=(tail[-1] + "\n").encode())

        monkeypatch.setattr(d132.docker_remediation.d127, "_docker_command", pull)
        result = d132.docker_remediation.remediate_already_running_docker_environment()

        assert tuple(pulls) == expected_pulls
        assert tuple(result["pulled_images"]) == expected_pulls
        assert result["image_pull_call_count"] == len(expected_pulls)
        assert result["daemon_start_attempted"] is False
        assert result["daemon_start_count"] == 0
        assert result["container_create_start_run_exec_count"] == 0
        assert result["docker_workload_call_count"] == 0


def test_pricing_capture_is_bounded_replayable_and_sdk_transport_is_zero(
    offline_repository: tuple[Path, dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = offline_repository
    commits, _receipt_commit = _seal_activation_receipt(root, state, monkeypatch)
    external = _install_external_mocks(root, monkeypatch)
    calls = external["calls"]
    phase_commits = (
        ("docker-image-readiness-remediation", "1" * 40, "2" * 40),
        ("official-pricing-capture", "3" * 40, "4" * 40),
        ("read-only-no-call-preflight", "5" * 40, "6" * 40),
    )

    for phase, attempt_commit, transition_commit in phase_commits:
        before = copy.deepcopy(calls)
        attempt_wait = d132.run_d130_external_no_call_preflight(repository=root)
        assert attempt_wait["status"] == (
            f"WAITING_{phase.replace('-', '_').upper()}_ATTEMPT_COMMIT"
        )
        assert attempt_wait["external_activity"] == {
            "docker_cli_command_count": 0,
            "official_public_get_request_count": 0,
            "sdk_credential_or_endpoint_observation_count": 0,
        }
        assert calls == before
        assert d132.run_d130_external_no_call_preflight(repository=root) == attempt_wait
        assert calls == before

        _commit_attempt(
            root,
            state,
            commits,
            phase=phase,
            commit=attempt_commit,
        )
        terminal_wait = d132.run_d130_external_no_call_preflight(repository=root)
        assert terminal_wait["status"] == (
            f"WAITING_{phase.replace('-', '_').upper()}_TERMINAL_TRANSITION_COMMIT"
        )
        after_action = copy.deepcopy(calls)
        assert d132.run_d130_external_no_call_preflight(repository=root) == terminal_wait
        assert calls == after_action
        _commit_transition(
            root,
            state,
            commits,
            phase=phase,
            commit=transition_commit,
        )

    assert calls == {"docker": 1, "pricing": 1, "docker_snapshot": 2, "sdk": 1}
    pricing = json.loads((root / d132.PRICING_PATH).read_bytes())["semantic_body"]["observation"]
    assert d132.pricing_capture.MAX_DECODED_ENTITY_BYTES == 128_000
    assert d132.pricing_capture.OFFICIAL_HOST == "developers.openai.com"
    assert pricing["public_get_request_count"] == 1
    assert pricing["decoded_entity_bytes"] == len(external["model_page"])
    assert pricing["decoded_entity_bytes"] <= d132.pricing_capture.MAX_DECODED_ENTITY_BYTES
    assert d132.pricing_capture.validate_official_pricing_evidence(pricing) == pricing
    sdk = json.loads((root / d132.PREFLIGHT_PATH).read_bytes())["semantic_body"]["observation"][
        "sdk_credential_factory_observation"
    ]
    assert sdk["d127_sdk_probe_skipped_due_to_python_routing"] is False
    assert [binding["module_name"] for binding in sdk["loaded_sdk_module_bindings"]] == [
        "openai",
        "httpx",
    ]
    assert all(
        binding["under_repository_venv"] is True
        and Path(binding["resolved_path"]).is_relative_to(root / ".venv")
        for binding in sdk["loaded_sdk_module_bindings"]
    )
    d127_sdk = sdk["d127_sdk_observation"]
    assert d127_sdk["network_call_count"] == 0
    assert d127_sdk["synthetic_endpoint_probe"]["transport_attempt_count"] == 0

    def require_zero_sdk(
        _root: Path,
        value: dict[str, object],
        *,
        source: dict[str, object],
    ) -> None:
        del source
        d132._validate_sdk_module_bindings(_root, value["loaded_sdk_module_bindings"])
        observation = value["d127_sdk_observation"]
        assert isinstance(observation, dict)
        d132._require(observation["network_call_count"] == 0, "SDK network count differs")
        probe = observation["synthetic_endpoint_probe"]
        assert isinstance(probe, dict)
        d132._require(probe["transport_attempt_count"] == 0, "SDK transport count differs")

    monkeypatch.setattr(d132, "_validate_sdk_observation", require_zero_sdk)
    preflight = json.loads((root / d132.PREFLIGHT_PATH).read_bytes())["semantic_body"]
    boundary = external["original_terminal_boundary"]
    status, ready, blockers, counts = boundary(
        root,
        "read-only-no-call-preflight",
        preflight["recorded_at"],
        preflight["observation"],
    )
    assert (status, ready, blockers) == (d132.PREFLIGHT_READY_STATUS, True, [])
    assert counts["sdk_transport_attempt_count"] == 0
    assert counts["sdk_network_call_count"] == 0

    unstable = copy.deepcopy(preflight["observation"])
    unstable["docker_readiness_snapshots"][1]["observation"]["passed"] = False
    unstable_status, unstable_ready, unstable_blockers, _counts = boundary(
        root,
        "read-only-no-call-preflight",
        preflight["recorded_at"],
        unstable,
    )
    assert unstable_status == d132.PREFLIGHT_BLOCKED_STATUS
    assert unstable_ready is False
    assert "read-only-docker-readiness-snapshots-are-not-stable" in unstable_blockers

    stale_status, stale_ready, stale_blockers, _counts = boundary(
        root,
        "read-only-no-call-preflight",
        "2026-08-13T12:05:31Z",
        preflight["observation"],
    )
    assert stale_status == d132.PREFLIGHT_BLOCKED_STATUS
    assert stale_ready is False
    assert "official-pricing-evidence-older-than-72-hours" in stale_blockers

    bad_cli = copy.deepcopy(preflight["observation"])
    bad_cli["approved_docker_cli_bindings"]["before"]["file_bytes"] += 1
    with pytest.raises(d132.D132ActivationOfflineError, match="CLI binding"):
        boundary(
            root,
            "read-only-no-call-preflight",
            preflight["recorded_at"],
            bad_cli,
        )

    transport_attempt = copy.deepcopy(preflight["observation"])
    transport_attempt["sdk_credential_factory_observation"]["d127_sdk_observation"][
        "synthetic_endpoint_probe"
    ]["transport_attempt_count"] = 1
    with pytest.raises(d132.D132ActivationOfflineError, match="transport"):
        boundary(
            root,
            "read-only-no-call-preflight",
            preflight["recorded_at"],
            transport_attempt,
        )

    sdk_delegate_calls: list[str] = []

    def forbidden_sdk_delegate(*_args: object, **_kwargs: object) -> object:
        sdk_delegate_calls.append("called")
        raise AssertionError("routed Python must skip the D-127 SDK probe")

    monkeypatch.setattr(d132.d127, "_sdk_observation", forbidden_sdk_delegate)
    expected_loaded_bindings = copy.deepcopy(sdk["loaded_sdk_module_bindings"])
    monkeypatch.setattr(
        d132,
        "_loaded_sdk_module_bindings",
        lambda _root: copy.deepcopy(expected_loaded_bindings),
    )
    monkeypatch.setattr(
        d132,
        "_validate_sdk_observation",
        external["original_validate_sdk_observation"],
    )
    receipt = json.loads((root / d132.ACTIVATION_RECEIPT_PATH).read_bytes())
    source = receipt["semantic_body"]["source_identity"]
    for routed_name in d132.d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES:
        with monkeypatch.context() as routing_environment:
            for name in d132.d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES:
                routing_environment.delenv(name, raising=False)
            routing_environment.setenv(routed_name, "mocked-routing-value")
            routed_sdk = external["original_sdk_observation"](
                root, source, {"mocked_factory_check": True}
            )
        assert routed_sdk["d127_sdk_probe_skipped_due_to_python_routing"] is True
        assert routed_sdk["loaded_sdk_module_bindings"] == expected_loaded_bindings
        assert routed_sdk["d127_sdk_observation"] is None
        routed_preflight = copy.deepcopy(preflight["observation"])
        routed_preflight["sdk_credential_factory_observation"] = routed_sdk
        routed_status, routed_ready, routed_blockers, routed_counts = boundary(
            root,
            "read-only-no-call-preflight",
            preflight["recorded_at"],
            routed_preflight,
        )
        assert routed_status == d132.PREFLIGHT_BLOCKED_STATUS
        assert routed_ready is False
        assert "python-module-routing-environment-present" in routed_blockers
        assert routed_counts["sdk_transport_attempt_count"] == 0
        assert routed_counts["sdk_network_call_count"] == 0
    assert sdk_delegate_calls == []

    receipt_payload, receipt_raw = d132._load_activation_receipt(root)
    phase_records = []
    for phase, _attempt_commit, transition_commit in phase_commits:
        transition = d132._rebuild_phase_transition_commit(
            root, phase=phase, commit=transition_commit
        )
        phase_records.append(d132._phase_record(root, phase=phase, transition=transition))
    fresh_gate_body = d132._build_final_gate_body(
        root,
        recorded_at="2026-08-09T12:11:00Z",
        receipt=d132._activation_receipt_binding(receipt_payload, receipt_raw),
        source=receipt_payload["semantic_body"]["source_identity"],
        phase_records=phase_records,
    )
    assert fresh_gate_body["status"] == d132.FINAL_GATE_READY_STATUS
    assert (
        fresh_gate_body["qualification"]["official_pricing_fresh_within_72_hours_at_final_gate"]
        is True
    )

    calls_before_stale_gate = copy.deepcopy(calls)
    monkeypatch.setattr(d132, "_now", lambda: "2026-08-13T12:05:31Z")
    gate_wait = d132.run_d130_external_no_call_preflight(repository=root)
    assert gate_wait["status"] == "WAITING_FINAL_GATE_EVIDENCE_COMMIT"
    assert calls == calls_before_stale_gate
    current = d132.validate_d130_external_no_call_gate(repository=root)
    assert current == d132.validate_d130_external_no_call_gate(repository=root)
    assert current["status"] == d132.FINAL_GATE_BLOCKED_STATUS
    assert current["environment_ready_for_execution_hash"] is False
    assert (
        "replayable-official-pricing-is-not-fresh-at-final-gate-creation"
        in current["observed_blockers"]
    )
    assert current["completed_phases"] == list(d132.PHASE_PATHS)
    assert current["execution_hash_created"] is False
    assert current["execution_candidate_created"] is False
    assert current["cost_reserved_or_spent_usd"] == "0"

    gate_raw = (root / d132.FINAL_GATE_PATH).read_bytes()
    evidence_commit = "7" * 40
    _record_commit(
        commits,
        commit=evidence_commit,
        parent="6" * 40,
        rows=[
            {"status": "A", "path": d132.FINAL_GATE_PATH.as_posix()},
            *({"status": "M", "path": path.as_posix()} for path in d132.ACTIVE_DOC_PATHS),
        ],
        blobs={d132.FINAL_GATE_PATH: gate_raw},
    )
    state["head"] = evidence_commit
    state["status_override"] = []
    post = d132.validate_d130_external_no_call_gate(repository=root, mode="post-evidence-commit")
    assert post == d132.validate_d130_external_no_call_gate(
        repository=root, mode="post-evidence-commit"
    )
    assert post["evidence_commit"] == evidence_commit


def test_blocked_or_orphaned_phase_is_terminal_idempotent_and_final_gate_is_non_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_of_order_root, out_of_order_state = _configure_offline_repository(
        tmp_path / "out-of-order", monkeypatch
    )
    _seal_activation_receipt(out_of_order_root, out_of_order_state, monkeypatch)
    out_of_order_external = _install_external_mocks(out_of_order_root, monkeypatch)
    pricing_orphan = out_of_order_root / d132.PRICING_ATTEMPT_PATH
    pricing_orphan.write_bytes(b"out-of-order-later-phase-artifact")
    with pytest.raises(d132.D132ActivationOfflineError, match="order|orphan|later"):
        d132.run_d130_external_no_call_preflight(repository=out_of_order_root)
    assert not (out_of_order_root / d132.DOCKER_ATTEMPT_PATH).exists()
    assert out_of_order_external["calls"] == {
        "docker": 0,
        "pricing": 0,
        "docker_snapshot": 0,
        "sdk": 0,
    }

    tamper_root, tamper_state = _configure_offline_repository(
        tmp_path / "post-inventory-tamper", monkeypatch
    )
    tamper_commits, _receipt = _seal_activation_receipt(tamper_root, tamper_state, monkeypatch)
    tamper_external = _install_external_mocks(tamper_root, monkeypatch)
    d132.run_d130_external_no_call_preflight(repository=tamper_root)
    _commit_attempt(
        tamper_root,
        tamper_state,
        tamper_commits,
        phase="docker-image-readiness-remediation",
        commit="1" * 40,
    )
    original_inventory = d132._validate_future_inventory
    mutated = False

    def inventory_then_tamper(selected_root: Path) -> None:
        nonlocal mutated
        original_inventory(selected_root)
        if selected_root == tamper_root and not mutated:
            (selected_root / d132.DOCKER_ATTEMPT_PATH).write_bytes(
                b"tampered-after-inventory-validation"
            )
            tamper_external["clear_terminal_cache"]()
            mutated = True

    monkeypatch.setattr(d132, "_validate_future_inventory", inventory_then_tamper)
    with pytest.raises(d132.D132ActivationOfflineError):
        d132.run_d130_external_no_call_preflight(repository=tamper_root)
    assert mutated is True
    assert not (tamper_root / d132.DOCKER_STARTED_PATH).exists()
    assert tamper_external["calls"] == {
        "docker": 0,
        "pricing": 0,
        "docker_snapshot": 0,
        "sdk": 0,
    }

    orphan_root, orphan_state = _configure_offline_repository(
        tmp_path / "started-orphan", monkeypatch
    )
    orphan_commits, _receipt = _seal_activation_receipt(orphan_root, orphan_state, monkeypatch)
    orphan_external = _install_external_mocks(
        orphan_root,
        monkeypatch,
        raise_phase="docker-image-readiness-remediation",
    )
    d132.run_d130_external_no_call_preflight(repository=orphan_root)
    _commit_attempt(
        orphan_root,
        orphan_state,
        orphan_commits,
        phase="docker-image-readiness-remediation",
        commit="1" * 40,
    )
    with pytest.raises(RuntimeError, match="simulated"):
        d132.run_d130_external_no_call_preflight(repository=orphan_root)
    assert (orphan_root / d132.DOCKER_STARTED_PATH).is_file()
    assert not (orphan_root / d132.DOCKER_TERMINAL_PATH).exists()
    assert not (orphan_root / d132.FINAL_GATE_PATH).exists()
    calls_after_crash = copy.deepcopy(orphan_external["calls"])
    with pytest.raises(d132.D132ActivationOfflineError, match="consumed|retry"):
        d132.run_d130_external_no_call_preflight(repository=orphan_root)
    assert orphan_external["calls"] == calls_after_crash
    assert not (orphan_root / d132.DOCKER_TERMINAL_PATH).exists()
    assert not (orphan_root / d132.FINAL_GATE_PATH).exists()

    blocked_root, blocked_state = _configure_offline_repository(tmp_path / "blocked", monkeypatch)
    blocked_commits, _receipt = _seal_activation_receipt(blocked_root, blocked_state, monkeypatch)
    blocked_external = _install_external_mocks(blocked_root, monkeypatch, docker_ready=False)
    d132.run_d130_external_no_call_preflight(repository=blocked_root)
    _commit_attempt(
        blocked_root,
        blocked_state,
        blocked_commits,
        phase="docker-image-readiness-remediation",
        commit="1" * 40,
    )
    terminal_wait = d132.run_d130_external_no_call_preflight(repository=blocked_root)
    assert terminal_wait["status"].endswith("TERMINAL_TRANSITION_COMMIT")
    _commit_transition(
        blocked_root,
        blocked_state,
        blocked_commits,
        phase="docker-image-readiness-remediation",
        commit="2" * 40,
    )
    gate_wait = d132.run_d130_external_no_call_preflight(repository=blocked_root)
    assert gate_wait["status"] == "WAITING_FINAL_GATE_EVIDENCE_COMMIT"
    assert all(
        not (blocked_root / path).exists()
        for phase in list(d132.PHASE_PATHS)[1:]
        for path in d132.PHASE_PATHS[phase]
    )
    calls_before_replay = copy.deepcopy(blocked_external["calls"])
    blocked = d132.run_d130_external_no_call_preflight(repository=blocked_root)
    assert blocked["status"] == d132.FINAL_GATE_BLOCKED_STATUS
    assert blocked["environment_ready_for_execution_hash"] is False
    assert blocked["execution_hash_created"] is False
    assert blocked["execution_candidate_created"] is False
    assert blocked["cost_reserved_or_spent_usd"] == "0"
    assert (
        blocked_external["calls"]
        == calls_before_replay
        == {
            "docker": 1,
            "pricing": 0,
            "docker_snapshot": 0,
            "sdk": 0,
        }
    )

    gate_path = blocked_root / d132.FINAL_GATE_PATH
    untampered = gate_path.read_bytes()
    tampered = json.loads(untampered)
    tampered["semantic_body"]["authority"]["execution_hash_or_candidate_authorized"] = True
    gate_path.write_bytes(d132._pretty_bytes(tampered))
    with pytest.raises(d132.D132ActivationOfflineError):
        d132.validate_d130_external_no_call_gate(repository=blocked_root)
    assert gate_path.read_bytes() != untampered
