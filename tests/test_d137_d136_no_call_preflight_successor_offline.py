from __future__ import annotations

import ast
import copy
import importlib
import json
import shutil
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from patchloop.evals import d137_d136_no_call_preflight_successor_offline as d137
from patchloop.evals import d137_no_call_preflight as no_call
from patchloop.util import canonical_json, sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d137_d136_no_call_preflight_successor_offline.py")
HELPER_PATH = Path("patchloop/evals/d137_no_call_preflight.py")
SCRIPT_PATH = Path("scripts/build_d137_d136_no_call_preflight_successor_offline.py")
TEST_PATH = Path("tests/test_d137_d136_no_call_preflight_successor_offline.py")

SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
GATE_COMMIT = "c" * 40
GATE_TREE = "d" * 40
RECEIPT_COMMIT = "e" * 40
RECEIPT_TREE = "f" * 40
DOCKER_ATTEMPT_COMMIT = "1" * 40
DOCKER_ATTEMPT_TREE = "2" * 40
DOCKER_TRANSITION_COMMIT = "3" * 40
DOCKER_TRANSITION_TREE = "4" * 40
DOCKER_MARKER_COMMIT = "5" * 40
DOCKER_MARKER_TREE = "6" * 40
SDK_ATTEMPT_COMMIT = "7" * 40
SDK_ATTEMPT_TREE = "8" * 40
SDK_TRANSITION_COMMIT = "9" * 40
SDK_TRANSITION_TREE = "0" * 40
SDK_MARKER_COMMIT = "a1" * 20
SDK_MARKER_TREE = "b2" * 20
SECRET = "d137-secret-value-must-never-be-persisted"


def _forbidden(label: str):
    def fail(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError(f"D-137 crossed forbidden {label} boundary")

    return fail


def _artifact_id(payload: dict[str, Any]) -> str:
    return str(payload.get("gate_id", payload.get("artifact_id")))


@pytest.fixture(autouse=True)
def forbid_unmocked_external_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        no_call,
        "_default_docker_dependencies",
        _forbidden("default Docker dependencies"),
    )
    monkeypatch.setattr(
        no_call,
        "_default_sdk_dependencies",
        _forbidden("default SDK dependencies"),
    )
    monkeypatch.setattr(
        no_call,
        "_run_bounded_command",
        _forbidden("Docker subprocess"),
    )
    monkeypatch.setattr(
        no_call.tempfile,
        "TemporaryDirectory",
        _forbidden("Docker temporary configuration"),
    )
    monkeypatch.setattr(
        no_call.importlib,
        "import_module",
        _forbidden("ambient SDK import"),
    )
    monkeypatch.setattr(
        no_call.importlib.metadata,
        "version",
        _forbidden("ambient SDK distribution inspection"),
    )
    monkeypatch.setattr(
        no_call.importlib.util,
        "find_spec",
        _forbidden("ambient SDK module-origin discovery"),
    )


@pytest.fixture
def sdk_repository() -> Iterator[Path]:
    fixed_temp_root = no_call.D137_FIXED_TEMP_ROOT.resolve(strict=True)
    root = Path(
        tempfile.mkdtemp(
            prefix="patchloop-d137-sdk-test-",
            dir=fixed_temp_root,
        )
    )
    (root / "patchloop/agent").mkdir(parents=True)
    shutil.copyfile(REPOSITORY / "uv.lock", root / "uv.lock")
    shutil.copyfile(REPOSITORY / "patchloop/agent/model.py", root / "patchloop/agent/model.py")
    for relative in (
        Path(".venv/d137-synthetic/python.exe"),
        Path(".venv/d137-synthetic/httpx/__init__.py"),
        Path(".venv/d137-synthetic/openai/__init__.py"),
        Path(".venv/d137-synthetic/httpx/loaded-elsewhere.py"),
        Path(".venv/d137-synthetic/openai/loaded-elsewhere.py"),
        Path("ignored-shadow/httpx/__init__.py"),
        Path("ignored-shadow/openai/__init__.py"),
        Path("outside-venv/python.exe"),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"d137-synthetic-non-sdk-placeholder\n")
    try:
        yield root
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == fixed_temp_root
            assert root.name.startswith("patchloop-d137-sdk-test-")
            shutil.rmtree(root)


def _docker_cli_binding(_path: Path) -> dict[str, Any]:
    return {
        "file_name": "docker.exe",
        "file_bytes": no_call.APPROVED_DOCKER_CLI_FILE_BYTES,
        "file_sha256": no_call.APPROVED_DOCKER_CLI_FILE_SHA256,
        "linklike": False,
    }


def _docker_dependencies(
    *,
    daemon_ready: bool = True,
    existing_container: bool = False,
    drift_second_snapshot: bool = False,
    secret_in_stderr: bool = False,
) -> tuple[no_call.DockerObservationDependencies, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    def runner(
        argv: Sequence[str],
        *,
        environment: Mapping[str, str],
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> no_call.BoundedCommandResult:
        call = {
            "argv": list(argv),
            "environment": dict(environment),
            "timeout_seconds": timeout_seconds,
            "max_output_bytes": max_output_bytes,
        }
        calls.append(call)
        role_index = (len(calls) - 1) % 4
        snapshot_index = (len(calls) - 1) // 4
        stderr = SECRET.encode() if secret_in_stderr else b""
        if role_index == 0:
            if daemon_ready:
                stdout = (
                    json.dumps(
                        {
                            "ClientVersion": no_call.APPROVED_DOCKER_CLI_VERSION,
                            "ServerVersion": "29.6.2",
                            "ServerOs": "linux",
                            "ServerArch": "amd64",
                        },
                        separators=(",", ":"),
                    ).encode()
                    + b"\n"
                )
                rc = 0
            else:
                stdout = b""
                rc = 1
        elif role_index in (1, 2):
            requested = str(argv[-1])
            config_digit = "9" if drift_second_snapshot and snapshot_index == 1 else str(role_index)
            stdout = (
                json.dumps(
                    {
                        "Id": "sha256:" + config_digit * 64,
                        "RepoDigests": [requested],
                    },
                    separators=(",", ":"),
                ).encode()
                + b"\n"
            )
            rc = 0
        else:
            stdout = ("a" * 64 + "\n").encode() if existing_container else b""
            rc = 0
        return no_call.BoundedCommandResult(
            return_code=rc,
            timed_out=False,
            stdout=stdout,
            stderr=stderr,
        )

    dependencies = no_call.DockerObservationDependencies(
        cli_path=no_call.APPROVED_DOCKER_CLI_PATH,
        cli_binding=_docker_cli_binding,
        command_runner=runner,
        child_environment={
            "DOCKER_CONFIG": r"C:\synthetic-d137-docker-config",
            "DOCKER_HOST": no_call.LOCAL_DOCKER_ENDPOINT,
        },
    )
    return dependencies, calls


def _sdk_dependencies(
    root: Path,
    *,
    credential_present: bool = True,
    pythonhome_present: bool = False,
    pythonpath_present: bool = False,
    version_drift: bool = False,
    base_url_drift: bool = False,
    max_retries_drift: bool = False,
    openai_owns_http: bool = False,
    interpreter_outside_venv: bool = False,
    module_spec_case: str | None = None,
    module_spec_case_name: str = "openai",
    loaded_module_origin_mismatch: str | None = None,
    binding_drift: str | None = None,
    venv_drift_during_httpx_spec: bool = False,
) -> tuple[no_call.SDKObservationDependencies, dict[str, Any]]:
    imports: list[str] = []
    presence_queries: list[str] = []
    state: dict[str, Any] = {
        "transport_handlers": [],
        "http_clients": [],
        "openai_clients": [],
        "imports": imports,
        "presence_queries": presence_queries,
        "file_bindings": [],
        "distribution_queries": [],
        "module_spec_queries": [],
        "binding_counts": {},
    }

    class FakeTransport:
        def __init__(self, handler: Any) -> None:
            state["transport_handlers"].append(handler)

    class FakeHTTPClient:
        def __init__(self, *, transport: Any, trust_env: bool) -> None:
            self.transport = transport
            self.trust_env = trust_env
            self.close_count = 0
            self.is_closed = False
            state["http_clients"].append(self)

        def close(self) -> None:
            self.close_count += 1
            self.is_closed = True

    class FakeOpenAIClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.base_url = (
                "https://invalid.example/v1/" if base_url_drift else kwargs["base_url"] + "/"
            )
            self.max_retries = 1 if max_retries_drift else kwargs["max_retries"]
            self.close_count = 0
            state["openai_clients"].append(self)

        def close(self) -> None:
            self.close_count += 1
            if openai_owns_http:
                self.kwargs["http_client"].close()

    httpx_module = ModuleType("httpx")
    httpx_module.__file__ = str(
        root
        / (
            ".venv/d137-synthetic/httpx/loaded-elsewhere.py"
            if loaded_module_origin_mismatch == "httpx"
            else ".venv/d137-synthetic/httpx/__init__.py"
        )
    )
    httpx_module.__version__ = "0.28.1"
    httpx_module.MockTransport = FakeTransport
    httpx_module.Client = FakeHTTPClient

    openai_module = ModuleType("openai")
    openai_module.__file__ = str(
        root
        / (
            ".venv/d137-synthetic/openai/loaded-elsewhere.py"
            if loaded_module_origin_mismatch == "openai"
            else ".venv/d137-synthetic/openai/__init__.py"
        )
    )
    openai_module.__version__ = "2.47.0"
    if version_drift:
        openai_module.__version__ = "0.0.0-drift"
    openai_module.OpenAI = FakeOpenAIClient

    def file_binding(path: Path) -> dict[str, Any]:
        state["file_bindings"].append(path)
        resolved = path.resolve(strict=True)
        if resolved == (root / ".venv/d137-synthetic/python.exe").resolve(strict=True):
            binding_role = "python"
        elif "openai" in resolved.parts:
            binding_role = "openai"
        elif "httpx" in resolved.parts:
            binding_role = "httpx"
        else:
            binding_role = "other"
        state["binding_counts"][binding_role] = state["binding_counts"].get(binding_role, 0) + 1
        digest_character = (
            "4"
            if binding_drift == binding_role and state["binding_counts"][binding_role] > 1
            else "3"
        )
        return {
            "file_name": path.name,
            "file_bytes": 1,
            "file_sha256": "sha256:" + digest_character * 64,
            "linklike": False,
        }

    def distribution_version(name: str) -> str | None:
        state["distribution_queries"].append(name)
        return {"httpx": "0.28.1", "openai": "2.47.0"}[name]

    def find_module_spec(name: str) -> Any:
        state["module_spec_queries"].append(name)
        assert name in {"httpx", "openai"}
        if venv_drift_during_httpx_spec and name == "httpx":
            (root / ".venv").rename(root / ".venv-drifted")
            state["venv_drifted"] = True
        if name == module_spec_case_name:
            if module_spec_case == "none":
                return None
            if module_spec_case == "built-in":
                return SimpleNamespace(origin="built-in")
            if module_spec_case == "missing":
                return SimpleNamespace()
            if module_spec_case == "unresolvable":
                return SimpleNamespace(origin=str(root / "does-not-exist" / name / "__init__.py"))
            if module_spec_case == "outside":
                return SimpleNamespace(origin=str(root / "ignored-shadow" / name / "__init__.py"))
            assert module_spec_case is None
        return SimpleNamespace(origin=str(root / ".venv/d137-synthetic" / name / "__init__.py"))

    def import_module(name: str) -> ModuleType:
        imports.append(name)
        assert name in {"httpx", "openai"}
        return {"httpx": httpx_module, "openai": openai_module}[name]

    def environment_present(name: str) -> bool:
        presence_queries.append(name)
        assert name in no_call.SDK_ENVIRONMENT_NAMES
        return {
            "OPENAI_API_KEY": credential_present,
            "PYTHONHOME": pythonhome_present,
            "PYTHONPATH": pythonpath_present,
        }[name]

    dependencies = no_call.SDKObservationDependencies(
        python_executable=(
            root / "outside-venv/python.exe"
            if interpreter_outside_venv
            else root / ".venv/d137-synthetic/python.exe"
        ),
        python_version="3.13.synthetic",
        file_binding=file_binding,
        distribution_version=distribution_version,
        find_module_spec=find_module_spec,
        import_module=import_module,
        environment_present=environment_present,
    )
    return dependencies, state


@pytest.fixture
def repository(
    monkeypatch: pytest.MonkeyPatch,
    sdk_repository: Path,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    fixed_temp_root = no_call.D137_FIXED_TEMP_ROOT.resolve(strict=True)
    root = Path(
        tempfile.mkdtemp(
            prefix="patchloop-d137-orchestrator-test-",
            dir=fixed_temp_root,
        )
    )
    (root / ".git").mkdir()
    (root / d137.GATE_PATH.parent).mkdir(parents=True)

    docker_dependencies, _docker_calls = _docker_dependencies()
    docker_ready = no_call.run_d137_docker_no_call_preflight_observation(
        repository=REPOSITORY,
        dependencies=docker_dependencies,
    )
    blocked_dependencies, _blocked_calls = _docker_dependencies(existing_container=True)
    docker_blocked = no_call.run_d137_docker_no_call_preflight_observation(
        repository=REPOSITORY,
        dependencies=blocked_dependencies,
    )
    sdk_dependencies, _sdk_state = _sdk_dependencies(sdk_repository)
    sdk_ready = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=sdk_dependencies,
    )
    blocked_sdk_dependencies, _blocked_sdk_state = _sdk_dependencies(
        sdk_repository,
        credential_present=False,
    )
    sdk_blocked = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=blocked_sdk_dependencies,
    )

    terminal_body = json.loads((REPOSITORY / d137.D136_TERMINAL_PATH).read_bytes())["semantic_body"]
    predecessor = {
        "pricing_terminal": {"recorded_at": terminal_body["recorded_at"]},
        "success_commit_binding": {
            "commit": d137.D136_SUCCESS_COMMIT,
            "tree": d137.D136_SUCCESS_TREE,
            "parents": [d137.D136_ATTEMPT_COMMIT],
            "artifact_paths": [
                d137.D136_STARTED_PATH.as_posix(),
                d137.D136_TERMINAL_PATH.as_posix(),
            ],
            "artifact_blob_oids": {
                d137.D136_STARTED_PATH.as_posix(): "b6090028bb40a6dce721bb1a2c6126cb094537f4",
                d137.D136_TERMINAL_PATH.as_posix(): "ee61520b3325e7a4e2ab891aeccff1a92862a543",
            },
            "exact_action_started_and_terminal_add_commit": True,
        },
    }
    source = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d137.D136_SUCCESS_COMMIT],
        "implementation_paths": [path.as_posix() for path in d137.IMPLEMENTATION_PATHS],
        "source_file_bindings": [],
        "loaded_module_bindings": [],
        "python_routing_environment_observation_performed": False,
        "python_routing_environment_observation_count": 0,
        "git_cli_observation": {"synthetic_test_observation": True},
        "exact_source_only_commit": True,
    }
    identities: dict[str, dict[str, Any]] = {
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [d137.D136_SUCCESS_COMMIT],
        },
        GATE_COMMIT: {
            "commit": GATE_COMMIT,
            "tree": GATE_TREE,
            "parents": [SOURCE_COMMIT],
        },
        RECEIPT_COMMIT: {
            "commit": RECEIPT_COMMIT,
            "tree": RECEIPT_TREE,
            "parents": [GATE_COMMIT],
        },
        DOCKER_ATTEMPT_COMMIT: {
            "commit": DOCKER_ATTEMPT_COMMIT,
            "tree": DOCKER_ATTEMPT_TREE,
            "parents": [RECEIPT_COMMIT],
        },
        DOCKER_TRANSITION_COMMIT: {
            "commit": DOCKER_TRANSITION_COMMIT,
            "tree": DOCKER_TRANSITION_TREE,
            "parents": [DOCKER_ATTEMPT_COMMIT],
        },
        DOCKER_MARKER_COMMIT: {
            "commit": DOCKER_MARKER_COMMIT,
            "tree": DOCKER_MARKER_TREE,
            "parents": [DOCKER_ATTEMPT_COMMIT],
        },
        SDK_ATTEMPT_COMMIT: {
            "commit": SDK_ATTEMPT_COMMIT,
            "tree": SDK_ATTEMPT_TREE,
            "parents": [DOCKER_TRANSITION_COMMIT],
        },
        SDK_TRANSITION_COMMIT: {
            "commit": SDK_TRANSITION_COMMIT,
            "tree": SDK_TRANSITION_TREE,
            "parents": [SDK_ATTEMPT_COMMIT],
        },
        SDK_MARKER_COMMIT: {
            "commit": SDK_MARKER_COMMIT,
            "tree": SDK_MARKER_TREE,
            "parents": [SDK_ATTEMPT_COMMIT],
        },
    }
    state: dict[str, Any] = {
        "head": SOURCE_COMMIT,
        "time_index": 0,
        "writes": [],
        "extra_diff": {},
        "identity_overrides": {},
        "status_override": None,
        "events": [],
        "docker_calls": 0,
        "sdk_calls": 0,
        "docker_observation": docker_ready,
        "docker_blocked": docker_blocked,
        "sdk_observation": sdk_ready,
        "sdk_blocked": sdk_blocked,
        "docker_error": None,
        "sdk_error": None,
        "docker_mutation": None,
        "sdk_mutation": None,
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        return copy.deepcopy(state["identity_overrides"].get(commit, identities[commit]))

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == SOURCE_COMMIT:
            rows = [
                {"status": "A", "path": path.as_posix()}
                for path in sorted(d137.IMPLEMENTATION_PATHS, key=lambda value: value.as_posix())
            ]
        elif commit == GATE_COMMIT:
            rows = [
                {"status": "A", "path": d137.GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d137.ACTIVE_DOC_PATHS),
            ]
        elif commit == RECEIPT_COMMIT:
            rows = [{"status": "A", "path": d137.RECEIPT_PATH.as_posix()}]
        elif commit == DOCKER_ATTEMPT_COMMIT:
            rows = [{"status": "A", "path": d137.DOCKER_ATTEMPT_PATH.as_posix()}]
        elif commit in (DOCKER_TRANSITION_COMMIT,):
            rows = [
                {"status": "A", "path": d137.DOCKER_STARTED_PATH.as_posix()},
                {"status": "A", "path": d137.DOCKER_TERMINAL_PATH.as_posix()},
            ]
        elif commit == DOCKER_MARKER_COMMIT:
            rows = [{"status": "A", "path": d137.DOCKER_STARTED_PATH.as_posix()}]
        elif commit == SDK_ATTEMPT_COMMIT:
            rows = [{"status": "A", "path": d137.SDK_ATTEMPT_PATH.as_posix()}]
        elif commit == SDK_TRANSITION_COMMIT:
            rows = [
                {"status": "A", "path": d137.SDK_STARTED_PATH.as_posix()},
                {"status": "A", "path": d137.SDK_TERMINAL_PATH.as_posix()},
            ]
        elif commit == SDK_MARKER_COMMIT:
            rows = [{"status": "A", "path": d137.SDK_STARTED_PATH.as_posix()}]
        else:
            raise AssertionError(f"unexpected synthetic commit: {commit}")
        return [*rows, *copy.deepcopy(state["extra_diff"].get(commit, []))]

    def commit_blob(_root: Path, commit: str, path: Path) -> tuple[str, bytes]:
        allowed = {
            GATE_COMMIT: {d137.GATE_PATH},
            RECEIPT_COMMIT: {d137.RECEIPT_PATH},
            DOCKER_ATTEMPT_COMMIT: {d137.DOCKER_ATTEMPT_PATH},
            DOCKER_TRANSITION_COMMIT: {
                d137.DOCKER_STARTED_PATH,
                d137.DOCKER_TERMINAL_PATH,
            },
            DOCKER_MARKER_COMMIT: {d137.DOCKER_STARTED_PATH},
            SDK_ATTEMPT_COMMIT: {d137.SDK_ATTEMPT_PATH},
            SDK_TRANSITION_COMMIT: {d137.SDK_STARTED_PATH, d137.SDK_TERMINAL_PATH},
            SDK_MARKER_COMMIT: {d137.SDK_STARTED_PATH},
        }
        assert path in allowed[commit]
        oid_seed = f"{commit}:{path.as_posix()}".encode()
        return sha256_bytes(oid_seed).removeprefix("sha256:")[:40], (root / path).read_bytes()

    def status_lines(_root: Path) -> list[str]:
        if state["status_override"] is not None:
            return list(state["status_override"])
        head = state["head"]
        if head == SOURCE_COMMIT and (root / d137.GATE_PATH).exists():
            paths = [d137.GATE_PATH]
        elif head == GATE_COMMIT and (root / d137.RECEIPT_PATH).exists():
            paths = [d137.RECEIPT_PATH]
        elif head == RECEIPT_COMMIT and (root / d137.DOCKER_ATTEMPT_PATH).exists():
            paths = [d137.DOCKER_ATTEMPT_PATH]
        elif head == DOCKER_ATTEMPT_COMMIT:
            paths = [
                path
                for path in (d137.DOCKER_STARTED_PATH, d137.DOCKER_TERMINAL_PATH)
                if (root / path).exists()
            ]
        elif head == DOCKER_TRANSITION_COMMIT and (root / d137.SDK_ATTEMPT_PATH).exists():
            paths = [d137.SDK_ATTEMPT_PATH]
        elif head == SDK_ATTEMPT_COMMIT:
            paths = [
                path
                for path in (d137.SDK_STARTED_PATH, d137.SDK_TERMINAL_PATH)
                if (root / path).exists()
            ]
        else:
            paths = []
        return [f"?? {path.as_posix()}" for path in paths]

    def validate_source(_root: Path, value: Any) -> dict[str, Any]:
        if canonical_json(value) != canonical_json(source):
            raise d137.D137NoCallPreflightSuccessorError("D-137 synthetic source differs")
        return copy.deepcopy(source)

    real_write_new = d137._write_new

    def write_new(selected_root: Path, path: Path, raw: bytes) -> None:
        state["writes"].append(path)
        real_write_new(selected_root, path, raw)

    def now() -> str:
        index = state["time_index"]
        state["time_index"] += 1
        return f"2026-08-10T01:{index:02d}:00Z"

    def docker_observation(*, repository: str | Path | None = None) -> dict[str, Any]:
        del repository
        state["docker_calls"] += 1
        state["events"].append("docker")
        assert (root / d137.DOCKER_STARTED_PATH).is_file()
        assert not (root / d137.DOCKER_TERMINAL_PATH).exists()
        error = state["docker_error"]
        if error is not None:
            raise error
        mutation = state["docker_mutation"]
        if mutation == "attempt":
            (root / d137.DOCKER_ATTEMPT_PATH).write_bytes(b"docker-attempt-toctou")
        elif mutation == "started":
            (root / d137.DOCKER_STARTED_PATH).write_bytes(b"docker-started-toctou")
        elif mutation == "checkout":
            state["status_override"] = [
                f"?? {d137.DOCKER_STARTED_PATH.as_posix()}",
                "?? unrelated-checkout-drift",
            ]
        return copy.deepcopy(state["docker_observation"])

    def sdk_observation(*, repository: str | Path | None = None) -> dict[str, Any]:
        del repository
        state["sdk_calls"] += 1
        state["events"].append("sdk")
        assert (root / d137.SDK_STARTED_PATH).is_file()
        assert not (root / d137.SDK_TERMINAL_PATH).exists()
        error = state["sdk_error"]
        if error is not None:
            raise error
        mutation = state["sdk_mutation"]
        if mutation == "attempt":
            (root / d137.SDK_ATTEMPT_PATH).write_bytes(b"sdk-attempt-toctou")
        elif mutation == "started":
            (root / d137.SDK_STARTED_PATH).write_bytes(b"sdk-started-toctou")
        elif mutation == "checkout":
            state["status_override"] = [
                f"?? {d137.SDK_STARTED_PATH.as_posix()}",
                "?? unrelated-checkout-drift",
            ]
        return copy.deepcopy(state["sdk_observation"])

    monkeypatch.setattr(d137, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(
        d137,
        "_exact_d136_success_topology",
        lambda _root: copy.deepcopy(predecessor),
    )
    monkeypatch.setattr(d137, "_source_identity_for_gate", lambda _root: copy.deepcopy(source))
    monkeypatch.setattr(d137, "_validate_source_identity", validate_source)
    monkeypatch.setattr(d137, "_commit_identity", commit_identity)
    monkeypatch.setattr(d137, "_diff_rows", diff_rows)
    monkeypatch.setattr(d137, "_commit_blob", commit_blob)
    monkeypatch.setattr(d137, "_head", lambda _root: state["head"])
    monkeypatch.setattr(d137, "_status_lines", status_lines)
    monkeypatch.setattr(d137, "_write_new", write_new)
    monkeypatch.setattr(d137, "_now", now)
    monkeypatch.setattr(
        no_call,
        "run_d137_docker_no_call_preflight_observation",
        docker_observation,
    )
    monkeypatch.setattr(
        no_call,
        "run_d137_sdk_no_call_preflight_observation",
        sdk_observation,
    )
    try:
        yield root, state
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == fixed_temp_root
            assert root.name.startswith("patchloop-d137-orchestrator-test-")
            shutil.rmtree(root)


def _seal_gate(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    result = d137.run_d137_offline_source_gate(repository=root)
    state["head"] = GATE_COMMIT
    post = d137.validate_d137_offline_source_gate(
        repository=root,
        mode="post-evidence-commit",
    )
    assert post["evidence_commit"] is not None
    return result


def _seal_receipt(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_gate(root, state)
    result = d137.create_d137_activation_receipt(repository=root)
    state["head"] = RECEIPT_COMMIT
    post = d137.validate_d137_activation_receipt(repository=root, mode="post-commit")
    assert post["receipt_commit"] is not None
    return result


def _seal_docker_attempt(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_receipt(root, state)
    result = d137.create_d137_docker_attempt(repository=root)
    state["head"] = DOCKER_ATTEMPT_COMMIT
    post = d137.validate_d137_docker_attempt(repository=root, mode="post-commit")
    assert post["attempt_commit"] is not None
    return result


def _seal_docker_transition(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_docker_attempt(root, state)
    result = d137.run_d137_docker_no_call_preflight(repository=root)
    state["head"] = DOCKER_TRANSITION_COMMIT
    post = d137.validate_d137_docker_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert post["transition_commit"] is not None
    return result


def _seal_sdk_attempt(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_docker_transition(root, state)
    result = d137.create_d137_sdk_attempt(repository=root)
    state["head"] = SDK_ATTEMPT_COMMIT
    post = d137.validate_d137_sdk_attempt(repository=root, mode="post-commit")
    assert post["attempt_commit"] is not None
    return result


def test_exact_d136_chain_bytes_and_git_topology_are_bound() -> None:
    rebuilt = d137._exact_d136_success_topology(REPOSITORY)
    assert rebuilt["success_commit_binding"] == {
        "commit": d137.D136_SUCCESS_COMMIT,
        "tree": d137.D136_SUCCESS_TREE,
        "parents": [d137.D136_ATTEMPT_COMMIT],
        "artifact_paths": [
            d137.D136_STARTED_PATH.as_posix(),
            d137.D136_TERMINAL_PATH.as_posix(),
        ],
        "artifact_blob_oids": {
            d137.D136_STARTED_PATH.as_posix(): "b6090028bb40a6dce721bb1a2c6126cb094537f4",
            d137.D136_TERMINAL_PATH.as_posix(): "ee61520b3325e7a4e2ab891aeccff1a92862a543",
        },
        "exact_action_started_and_terminal_add_commit": True,
    }
    assert rebuilt["pricing_replay_validation"]["public_get_request_count"] == 1

    expected_commits = {
        d137.D136_GATE_COMMIT: {
            "tree": d137.D136_GATE_TREE,
            "parents": [d137.D136_SOURCE_COMMIT],
            "paths": [("A", d137.D136_GATE_PATH.as_posix())],
        },
        d137.D136_RECEIPT_COMMIT: {
            "tree": d137.D136_RECEIPT_TREE,
            "parents": [d137.D136_GATE_COMMIT],
            "paths": [("A", d137.D136_RECEIPT_PATH.as_posix())],
        },
        d137.D136_ATTEMPT_COMMIT: {
            "tree": d137.D136_ATTEMPT_TREE,
            "parents": [d137.D136_RECEIPT_COMMIT],
            "paths": [("A", d137.D136_ATTEMPT_PATH.as_posix())],
        },
        d137.D136_SUCCESS_COMMIT: {
            "tree": d137.D136_SUCCESS_TREE,
            "parents": [d137.D136_ATTEMPT_COMMIT],
            "paths": sorted(
                [
                    ("A", d137.D136_STARTED_PATH.as_posix()),
                    ("A", d137.D136_TERMINAL_PATH.as_posix()),
                ]
            ),
        },
    }

    source = d137._commit_identity(REPOSITORY, d137.D136_SOURCE_COMMIT)
    assert source == {
        "commit": d137.D136_SOURCE_COMMIT,
        "tree": d137.D136_SOURCE_TREE,
        "parents": [d137.D136_SOURCE_PARENT],
    }
    source_rows = d137._diff_rows(REPOSITORY, d137.D136_SOURCE_COMMIT)
    assert sorted((row["status"], row["path"]) for row in source_rows) == sorted(
        ("A", path.as_posix()) for path in d137.D136_IMPLEMENTATION_PATHS
    )

    for commit, expected in expected_commits.items():
        identity = d137._commit_identity(REPOSITORY, commit)
        assert identity["tree"] == expected["tree"]
        assert identity["parents"] == expected["parents"]
        rows = sorted((row["status"], row["path"]) for row in d137._diff_rows(REPOSITORY, commit))
        if commit == d137.D136_GATE_COMMIT:
            assert rows == sorted(
                [
                    ("A", d137.D136_GATE_PATH.as_posix()),
                    *(("M", path.as_posix()) for path in d137.ACTIVE_DOC_PATHS),
                ]
            )
        else:
            assert rows == expected["paths"]

    for path, identifier, body_sha, file_sha, size, blob, commit in d137._D136_ARTIFACTS:
        raw = (REPOSITORY / path).read_bytes()
        payload = json.loads(raw)
        oid, committed = d137._commit_blob(REPOSITORY, commit, path)
        assert (_artifact_id(payload), payload["semantic_body_hash"]) == (identifier, body_sha)
        assert (sha256_bytes(raw), len(raw)) == (file_sha, size)
        assert (oid, committed) == (blob, raw)


def test_source_topology_accepts_git_lexical_diff_order_but_serializes_approved_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved = [path.as_posix() for path in d137.IMPLEMENTATION_PATHS]
    lexical_rows = [{"status": "A", "path": path} for path in sorted(approved)]
    identity = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d137.D136_SUCCESS_COMMIT],
    }
    bindings = [
        {
            "path": path.as_posix(),
            "blob_oid": "1" * 40,
            "file_sha256": "sha256:" + "2" * 64,
            "file_bytes": 1,
            "current_bytes_match_commit": True,
        }
        for path in d137.SOURCE_BINDING_PATHS
    ]
    modules = [{"module_name": "synthetic", "loaded_path_matches_repository": True}]
    git = {"git_engine": "synthetic", "stable": True}
    monkeypatch.setattr(d137, "_head", lambda _root: SOURCE_COMMIT)
    monkeypatch.setattr(d137, "_commit_identity", lambda _root, _commit: copy.deepcopy(identity))
    monkeypatch.setattr(d137, "_diff_rows", lambda _root, _commit: copy.deepcopy(lexical_rows))
    monkeypatch.setattr(d137, "_status_lines", lambda _root: [])
    monkeypatch.setattr(
        d137,
        "_file_binding",
        lambda _root, _commit, path: copy.deepcopy(bindings[d137.SOURCE_BINDING_PATHS.index(path)]),
    )
    monkeypatch.setattr(
        d137,
        "_loaded_module_bindings",
        lambda _root, _commit: copy.deepcopy(modules),
    )
    monkeypatch.setattr(d137, "_git_cli_observation", lambda _root: copy.deepcopy(git))
    monkeypatch.setenv("PYTHONHOME", "synthetic-present-but-unobserved")
    monkeypatch.setenv("PYTHONPATH", "synthetic-present-but-unobserved")

    value = d137._source_identity_for_gate(REPOSITORY)

    assert value["implementation_paths"] == approved
    assert value["implementation_paths"] != sorted(approved)
    assert value["python_routing_environment_observation_performed"] is False
    assert value["python_routing_environment_observation_count"] == 0
    assert d137._validate_source_identity(REPOSITORY, value) == value

    module_tamper = copy.deepcopy(value)
    module_tamper["loaded_module_bindings"].append({"module_name": "outside"})
    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="loaded module"):
        d137._validate_source_identity(REPOSITORY, module_tamper)

    git_tamper = copy.deepcopy(value)
    git_tamper["git_cli_observation"]["stable"] = False
    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="Git differs"):
        d137._validate_source_identity(REPOSITORY, git_tamper)


def test_public_paths_source_scope_and_no_historical_runner_import_are_exact() -> None:
    assert d137.IMPLEMENTATION_PATHS == (HELPER_PATH, MODULE_PATH, SCRIPT_PATH, TEST_PATH)
    assert len(d137.ACTIVE_DOC_PATHS) == 10
    assert d137.FUTURE_PATHS == (
        d137.RECEIPT_PATH,
        d137.DOCKER_ATTEMPT_PATH,
        d137.DOCKER_STARTED_PATH,
        d137.DOCKER_TERMINAL_PATH,
        d137.SDK_ATTEMPT_PATH,
        d137.SDK_STARTED_PATH,
        d137.SDK_TERMINAL_PATH,
    )
    assert set(d137.PHASE_PATHS) == {d137.PHASE_DOCKER, d137.PHASE_SDK}
    assert d137.PHASE_PATHS[d137.PHASE_DOCKER] == (
        d137.DOCKER_ATTEMPT_PATH,
        d137.DOCKER_STARTED_PATH,
        d137.DOCKER_TERMINAL_PATH,
    )
    assert d137.PHASE_PATHS[d137.PHASE_SDK] == (
        d137.SDK_ATTEMPT_PATH,
        d137.SDK_STARTED_PATH,
        d137.SDK_TERMINAL_PATH,
    )

    source = (REPOSITORY / MODULE_PATH).read_text(encoding="utf-8")
    helper = (REPOSITORY / HELPER_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert all(
        "d127" not in name and "d128" not in name and "d132" not in name for name in imported
    )
    assert "run_d128_external_no_call_preflight" not in source
    assert "run_d130_external_no_call_preflight" not in source
    assert "remediate_" not in source
    assert "run_d128_external_no_call_preflight" not in helper
    assert "run_d130_external_no_call_preflight" not in helper
    assert "remediate_docker" not in helper


def test_d136_success_is_replayable_pricing_only_and_grants_no_preflight_authority() -> None:
    terminal = json.loads((REPOSITORY / d137.D136_TERMINAL_PATH).read_bytes())["semantic_body"]
    observation = terminal["observation"]
    accounting = terminal["activity_accounting"]

    assert observation["public_get_request_count"] == 1
    assert observation["decoded_entity_bytes"] == 3_735
    assert observation["decoded_entity_sha256"] == sha256_bytes(
        __import__("base64").b64decode(observation["decoded_entity_base64"], validate=True)
    )
    assert accounting["pricing_helper_invocation_count"] == 1
    assert accounting["official_public_get_send_count"] == 1
    assert accounting["docker_cli_call_count"] == 0
    assert accounting["sdk_credential_dotenv_environment_value_or_endpoint_observation_count"] == 0
    assert accounting["provider_evaluator_agent_call_count"] == 0
    assert terminal["authority"] == {
        "docker_or_sdk_no_call_preflight_authorized": False,
        "execution_hash_or_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
        "four_row_ac_executed": False,
    }
    assert terminal["next_gate"] == {
        "status": "D137_NO_CALL_PREFLIGHT_SUCCESSOR_OFFLINE_SOURCE_APPROVAL_REQUIRED",
        "fresh_separate_approval_required": True,
        "current_activation_authorizes_next_gate": False,
    }


def test_helper_import_is_observation_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(no_call.subprocess, "run", _forbidden("Docker CLI on helper import"))

    reloaded = importlib.reload(no_call)

    assert reloaded.DOCKER_PHASE == "docker"
    assert reloaded.SDK_PHASE == "sdk"


def test_docker_helper_ready_uses_exact_bounded_read_only_commands_and_stable_snapshots() -> None:
    dependencies, calls = _docker_dependencies()

    result = no_call.run_d137_docker_no_call_preflight_observation(
        repository=REPOSITORY,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.DOCKER_READY_STATUS
    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["observation"]["normalized_snapshots_stable"] is True
    assert len(result["observation"]["snapshots"]) == 2
    assert len(calls) == 8
    assert all(call["timeout_seconds"] == no_call.DOCKER_COMMAND_TIMEOUT_SECONDS for call in calls)
    assert all(call["max_output_bytes"] == no_call.MAX_DOCKER_OUTPUT_BYTES for call in calls)
    assert all(
        call["environment"]
        == {
            "DOCKER_CONFIG": r"C:\synthetic-d137-docker-config",
            "DOCKER_HOST": no_call.LOCAL_DOCKER_ENDPOINT,
        }
        for call in calls
    )
    assert [call["argv"][1:] for call in calls[:4]] == [
        list(tail) for _role, tail in no_call._DOCKER_COMMANDS
    ]
    assert [call["argv"][1:] for call in calls[4:]] == [
        list(tail) for _role, tail in no_call._DOCKER_COMMANDS
    ]
    flattened = " ".join(part for call in calls for part in call["argv"])
    assert all(image in flattened for image in no_call.EXACT_DOCKER_IMAGES)
    argv_tokens = {part.casefold() for call in calls for part in call["argv"][1:]}
    assert argv_tokens.isdisjoint({"start", "run", "exec", "pull", "load", "create"})
    assert result["activity"] == {
        "docker_cli_file_binding_count": 4,
        "docker_cli_command_count": 8,
        "read_only_daemon_version_call_count": 2,
        "read_only_exact_image_inspect_call_count": 4,
        "read_only_container_inventory_call_count": 2,
        "docker_desktop_or_daemon_start_count": 0,
        "docker_image_pull_or_load_count": 0,
        "docker_image_store_mutation_count": 0,
        "container_create_start_run_exec_count": 0,
        "docker_workload_or_mutating_call_count": 0,
        "container_ids_raw_or_hashed_persisted": False,
        "raw_stdout_or_stderr_persisted": False,
    }
    assert no_call.validate_d137_docker_no_call_preflight_observation(result) == result


@pytest.mark.parametrize(
    ("kwargs", "blocker"),
    [
        ({"daemon_ready": False}, "already-running-linux-amd64-docker-daemon-not-ready"),
        ({"existing_container": True}, "existing-container-inventory-is-not-zero"),
        ({"drift_second_snapshot": True}, "docker-readiness-snapshots-not-stable"),
    ],
)
def test_docker_helper_blocked_paths_are_terminal_observations_without_mutation(
    kwargs: dict[str, bool],
    blocker: str,
) -> None:
    dependencies, calls = _docker_dependencies(**kwargs)

    result = no_call.run_d137_docker_no_call_preflight_observation(
        repository=REPOSITORY,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.DOCKER_BLOCKED_STATUS
    assert result["passed"] is False
    assert blocker in result["blockers"]
    assert len(calls) == 8
    assert result["activity"]["docker_workload_or_mutating_call_count"] == 0
    assert result["activity"]["container_create_start_run_exec_count"] == 0


def test_docker_helper_never_persists_raw_output_or_secret_and_validator_rejects_tamper() -> None:
    dependencies, _calls = _docker_dependencies(daemon_ready=False, secret_in_stderr=True)
    result = no_call.run_d137_docker_no_call_preflight_observation(
        repository=REPOSITORY,
        dependencies=dependencies,
    )

    assert SECRET not in canonical_json(result)
    for snapshot in result["observation"]["snapshots"]:
        for command in snapshot["commands"]:
            assert "stdout" not in command
            assert "stderr" not in command
            assert command["raw_stdout_or_stderr_persisted"] is False

    tampered = copy.deepcopy(result)
    tampered["activity"]["docker_image_pull_or_load_count"] = 1
    with pytest.raises(no_call.D137NoCallPreflightError):
        no_call.validate_d137_docker_no_call_preflight_observation(tampered)


def test_sdk_helper_ready_observes_only_provenance_routing_and_presence_bits(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository)

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_READY_STATUS
    assert result["passed"] is True
    assert result["blockers"] == []
    assert state["imports"] == ["httpx", "openai"]
    assert state["module_spec_queries"] == ["httpx", "openai"]
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
    assert result["observation"]["environment_presence_bits"] == {
        "OPENAI_API_KEY": True,
        "PYTHONHOME": False,
        "PYTHONPATH": False,
    }
    assert result["observer_contract"]["environment_values_available_to_observer"] is False
    assert result["observer_contract"]["dotenv_read_authorized"] is False
    assert result["observation"]["synthetic_probe"]["transport_dispatch_count"] == 0
    assert len(state["transport_handlers"]) == 1
    assert all(client.close_count == 1 for client in state["http_clients"])
    assert all(client.close_count == 1 for client in state["openai_clients"])
    assert result["activity"] == {
        "dynamic_module_import_count": 2,
        "find_module_spec_count": 2,
        "python_executable_file_binding_count": 2,
        "sdk_module_file_binding_count": 4,
        "distribution_version_observation_count": 2,
        "locked_version_source_read_count": 2,
        "checked_in_factory_source_read_count": 1,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 1,
        "http_client_fallback_close_call_count": 1,
        "http_client_closed": True,
    }
    assert no_call.validate_d137_sdk_no_call_preflight_observation(result) == result


@pytest.mark.parametrize(
    ("kwargs", "blocker"),
    [
        ({"credential_present": False}, "openai-api-key-presence-bit-is-false"),
        ({"pythonpath_present": True}, "pythonpath-presence-bit-is-true"),
        ({"version_drift": True}, "openai-module-version-does-not-match-lock"),
        ({"base_url_drift": True}, "synthetic-no-call-probe-did-not-pass"),
        ({"max_retries_drift": True}, "synthetic-client-max-retries-was-not-zero"),
    ],
)
def test_sdk_helper_blocked_paths_still_dispatch_zero_and_never_read_values(
    sdk_repository: Path,
    kwargs: dict[str, bool],
    blocker: str,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository, **kwargs)

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert blocker in result["blockers"]
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0
    assert result["activity"]["environment_value_read_count"] == 0
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)


@pytest.mark.parametrize(
    "routing_kwargs",
    [{"pythonhome_present": True}, {"pythonpath_present": True}],
)
def test_sdk_routing_presence_blocks_before_any_import_binding_or_probe_delegate(
    sdk_repository: Path,
    routing_kwargs: dict[str, bool],
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository, **routing_kwargs)

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert "sdk-import-and-probe-suppressed-by-preliminary-presence-checks" in result["blockers"]
    assert state["imports"] == []
    assert state["module_spec_queries"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []
    assert result["observation"]["python"] is None
    assert result["observation"]["modules"] is None
    assert result["observation"]["production_client_factory"] is None
    assert result["observation"]["synthetic_probe"] is None
    assert result["activity"] == {
        "dynamic_module_import_count": 0,
        "find_module_spec_count": 0,
        "python_executable_file_binding_count": 0,
        "sdk_module_file_binding_count": 0,
        "distribution_version_observation_count": 0,
        "locked_version_source_read_count": 0,
        "checked_in_factory_source_read_count": 0,
        "environment_presence_check_count": 3,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }


def test_sdk_wrong_interpreter_blocks_before_module_distribution_or_probe_delegates(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        interpreter_outside_venv=True,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert "python-interpreter-is-not-repository-venv" in result["blockers"]
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
    assert state["file_bindings"] == []
    assert state["distribution_queries"] == []
    assert state["module_spec_queries"] == []
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []
    assert "outside-venv" not in canonical_json(result)
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert result["activity"]["find_module_spec_count"] == 0
    assert result["activity"]["python_executable_file_binding_count"] == 0
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert result["activity"]["distribution_version_observation_count"] == 0
    assert result["activity"]["locked_version_source_read_count"] == 0
    assert result["activity"]["checked_in_factory_source_read_count"] == 0
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


def test_sdk_missing_credential_bit_blocks_before_import_distribution_or_probe(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        credential_present=False,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert "openai-api-key-presence-bit-is-false" in result["blockers"]
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
    assert state["file_bindings"] == []
    assert state["distribution_queries"] == []
    assert state["module_spec_queries"] == []
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert result["activity"]["find_module_spec_count"] == 0
    assert result["activity"]["python_executable_file_binding_count"] == 0
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert result["activity"]["distribution_version_observation_count"] == 0
    assert result["activity"]["locked_version_source_read_count"] == 0
    assert result["activity"]["checked_in_factory_source_read_count"] == 0
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


@pytest.mark.parametrize(
    "spec_case",
    ["none", "built-in", "missing", "unresolvable", "outside"],
)
def test_sdk_unsafe_or_unresolvable_spec_origin_is_sanitized_and_blocks_before_binding(
    sdk_repository: Path,
    spec_case: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        module_spec_case=spec_case,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert "openai-module-origin-is-not-repository-venv" in result["blockers"]
    assert "sdk-import-and-probe-suppressed-by-module-origin-provenance" in result["blockers"]
    assert state["module_spec_queries"] == ["httpx", "openai"]
    assert state["imports"] == []
    assert state["distribution_queries"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []
    serialized = canonical_json(result)
    assert "ignored-shadow" not in serialized
    assert "does-not-exist" not in serialized
    assert result["activity"]["find_module_spec_count"] == 2
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert result["activity"]["distribution_version_observation_count"] == 0
    assert result["activity"]["locked_version_source_read_count"] == 0
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


def test_sdk_venv_drift_between_origin_resolvers_records_exact_find_spec_count(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        venv_drift_during_httpx_spec=True,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert state["venv_drifted"] is True
    assert state["module_spec_queries"] == ["httpx"]
    assert state["imports"] == []
    assert state["distribution_queries"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []
    assert result["observation"]["modules"] == {
        "openai_origin_is_repository_venv": False,
        "httpx_origin_is_repository_venv": False,
        "openai_find_module_spec_performed": False,
        "httpx_find_module_spec_performed": True,
    }
    assert result["activity"]["find_module_spec_count"] == len(state["module_spec_queries"]) == 1
    assert result["activity"]["python_executable_file_binding_count"] == 1
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert result["activity"]["distribution_version_observation_count"] == 0
    assert result["activity"]["locked_version_source_read_count"] == 0
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0
    assert "venv-drifted" not in canonical_json(result)


@pytest.mark.parametrize("module_name", ["openai", "httpx"])
def test_sdk_loaded_module_origin_mismatch_is_rejected_before_probe(
    sdk_repository: Path,
    module_name: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        loaded_module_origin_mismatch=module_name,
    )

    with pytest.raises(no_call.D137NoCallPreflightError, match="loaded module origin differs"):
        no_call.run_d137_sdk_no_call_preflight_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["module_spec_queries"] == ["httpx", "openai"]
    assert state["imports"] == ["httpx", "openai"]
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []


@pytest.mark.parametrize(
    ("binding_role", "blocker"),
    [
        ("python", "python-executable-binding-changed-during-sdk-probe"),
        ("openai", "openai-module-binding-changed-during-sdk-probe"),
        ("httpx", "httpx-module-binding-changed-during-sdk-probe"),
    ],
)
def test_sdk_post_probe_file_binding_drift_is_terminally_blocked(
    sdk_repository: Path,
    binding_role: str,
    blocker: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        binding_drift=binding_role,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert blocker in result["blockers"]
    assert state["binding_counts"][binding_role] == 2
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


def test_sdk_helper_does_not_persist_credential_value_and_validator_rejects_dispatch_tamper(
    sdk_repository: Path,
) -> None:
    dependencies, _state = _sdk_dependencies(sdk_repository)
    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert SECRET not in canonical_json(result)
    assert set(result["observation"]["environment_presence_bits"].values()) <= {True, False}
    tampered = copy.deepcopy(result)
    tampered["observation"]["synthetic_probe"]["transport_dispatch_count"] = 1
    tampered["activity"]["synthetic_transport_dispatch_count"] = 1
    with pytest.raises(no_call.D137NoCallPreflightError):
        no_call.validate_d137_sdk_no_call_preflight_observation(tampered)


@pytest.mark.parametrize("openai_owns_http", [False, True])
def test_sdk_helper_cleanup_accepts_both_http_client_ownership_paths(
    sdk_repository: Path,
    openai_owns_http: bool,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        openai_owns_http=openai_owns_http,
    )

    result = no_call.run_d137_sdk_no_call_preflight_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    probe = result["observation"]["synthetic_probe"]
    assert probe["openai_client_close_call_count"] == 1
    assert probe["http_client_fallback_close_call_count"] == (0 if openai_owns_http else 1)
    assert probe["http_client_closed"] is True
    assert state["openai_clients"][0].close_count == 1
    assert state["http_clients"][0].close_count == 1
    assert result["passed"] is True


def test_offline_gate_is_idempotent_and_invokes_no_future_writer_or_observer(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository

    first = d137.run_d137_offline_source_gate(repository=root)
    raw = (root / d137.GATE_PATH).read_bytes()
    second = d137.run_d137_offline_source_gate(repository=root)
    pending = d137.validate_d137_offline_source_gate(repository=root)

    assert first == second == pending
    assert first["status"] == d137.GATE_STATUS
    assert first["external_action_count"] == 0
    assert first["future_artifacts_created"] is False
    assert first["fresh_exact_activation_required"] is True
    assert state["writes"] == [d137.GATE_PATH]
    assert state["docker_calls"] == state["sdk_calls"] == 0
    assert raw == (root / d137.GATE_PATH).read_bytes()
    assert all(not (root / path).exists() for path in d137.FUTURE_PATHS)

    body = json.loads(raw)["semantic_body"]
    assert body["offline_qualification"] == {
        "gate_builder_invoked_future_writer": False,
        "gate_builder_invoked_docker_or_sdk_helper": False,
        "external_action_count": 0,
        "future_artifacts_created": False,
        "focused_tests_are_mocked_only": True,
    }
    assert set(body["authority"].values()) <= {False, "0"}
    future = body["future_activation_contract"]
    assert future["docker_attempt_only_commit_required"] is True
    assert future["sdk_attempt_only_commit_required"] is True
    assert future["sdk_requires_committed_docker_ready_terminal"] is True
    assert future["post_marker_failure_consumes_phase_and_forbids_retry"] is True


def test_gate_prepublication_predecessor_drift_fails_without_publication(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    original = d137._exact_d136_success_topology
    calls = 0

    def drifting_predecessor(selected_root: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        value = original(selected_root)
        if calls == 2:
            value["success_commit_binding"]["tree"] = "f" * 40
        return value

    monkeypatch.setattr(d137, "_exact_d136_success_topology", drifting_predecessor)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="drifted before gate"):
        d137.run_d137_offline_source_gate(repository=root)
    assert calls == 2
    assert not (root / d137.GATE_PATH).exists()
    assert state["writes"] == []
    assert state["docker_calls"] == state["sdk_calls"] == 0


def test_gate_postcommit_scope_and_activation_template_are_exact_and_read_only(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)
    gate_raw = (root / d137.GATE_PATH).read_bytes()
    gate = json.loads(gate_raw)
    before_writes = list(state["writes"])

    post = d137.validate_d137_offline_source_gate(
        repository=root,
        mode="post-evidence-commit",
    )
    template = d137.render_d137_external_activation_template(repository=root)

    assert post["evidence_commit"] == {
        "commit": GATE_COMMIT,
        "tree": GATE_TREE,
        "parents": [SOURCE_COMMIT],
        "artifact_path": d137.GATE_PATH.as_posix(),
        "artifact_blob_oid": post["evidence_commit"]["artifact_blob_oid"],
        "artifact_file_sha256": sha256_bytes(gate_raw),
        "artifact_file_bytes": len(gate_raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }
    assert f"Gate ID: {gate['gate_id']}" in template
    assert f"Gate body SHA: {gate['semantic_body_hash']}" in template
    assert f"Gate file SHA: {sha256_bytes(gate_raw)}" in template
    assert f"Gate file bytes: {len(gate_raw)}" in template
    assert f"Source commit: {SOURCE_COMMIT}" in template
    assert f"Source tree: {SOURCE_TREE}" in template
    assert all(f"- {item}" in template for item in d137.ACTIVATION_SCOPE)
    assert len(d137.ACTIVATION_EXCLUSIONS) == 5
    assert all(f"- {item}" in template for item in d137.ACTIVATION_EXCLUSIONS)
    assert all(template.count(f"- {item}") == 1 for item in d137.ACTIVATION_EXCLUSIONS)
    assert "must not be retried" in template
    assert "not approval" in template.lower()
    assert state["writes"] == before_writes
    assert (root / d137.GATE_PATH).read_bytes() == gate_raw
    assert all(not (root / path).exists() for path in d137.FUTURE_PATHS)

    state["extra_diff"][GATE_COMMIT] = [{"status": "M", "path": "unrelated.txt"}]
    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="evidence commit scope"):
        d137.validate_d137_offline_source_gate(
            repository=root,
            mode="post-evidence-commit",
        )


def test_receipt_and_docker_attempt_are_idempotent_sole_artifact_boundaries(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)

    receipt_first = d137.create_d137_activation_receipt(repository=root)
    receipt_second = d137.create_d137_activation_receipt(repository=root)
    receipt_raw = (root / d137.RECEIPT_PATH).read_bytes()
    assert receipt_first == receipt_second
    assert receipt_first["receipt_commit"] is None
    assert receipt_first["commit_required_before_docker_attempt"] is True
    assert receipt_first["external_action_count"] == 0

    state["head"] = RECEIPT_COMMIT
    receipt_post = d137.validate_d137_activation_receipt(repository=root, mode="post-commit")
    assert receipt_post["receipt_commit"]["parents"] == [GATE_COMMIT]
    assert receipt_post["receipt_commit"]["artifact_file_sha256"] == sha256_bytes(receipt_raw)
    assert receipt_post["receipt_commit"]["single_artifact_add_commit"] is True

    attempt_first = d137.create_d137_docker_attempt(repository=root)
    attempt_second = d137.create_d137_docker_attempt(repository=root)
    attempt_raw = (root / d137.DOCKER_ATTEMPT_PATH).read_bytes()
    assert attempt_first == attempt_second
    assert attempt_first["phase"] == d137.PHASE_DOCKER
    assert attempt_first["attempt_commit"] is None
    assert attempt_first["commit_required_before_phase_observation"] is True
    assert attempt_first["external_action_count"] == 0

    state["head"] = DOCKER_ATTEMPT_COMMIT
    attempt_post = d137.validate_d137_docker_attempt(repository=root, mode="post-commit")
    assert attempt_post["attempt_commit"]["parents"] == [RECEIPT_COMMIT]
    assert attempt_post["attempt_commit"]["artifact_file_sha256"] == sha256_bytes(attempt_raw)
    assert attempt_post["attempt_commit"]["single_artifact_add_commit"] is True
    assert state["writes"] == [
        d137.GATE_PATH,
        d137.RECEIPT_PATH,
        d137.DOCKER_ATTEMPT_PATH,
    ]


def test_receipt_prepublication_gate_drift_fails_without_receipt(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_gate(root, state)
    original = d137._gate_binding_for_activation
    calls = 0

    def drifting_gate(
        selected_root: Path,
        *,
        evidence_commit: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], bytes]:
        nonlocal calls
        calls += 1
        gate, body, raw = original(selected_root, evidence_commit=evidence_commit)
        if calls == 2:
            gate = copy.deepcopy(gate)
            gate["file_bytes"] += 1
        return gate, body, raw

    monkeypatch.setattr(d137, "_gate_binding_for_activation", drifting_gate)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="drifted before receipt"):
        d137.create_d137_activation_receipt(repository=root)
    assert calls == 2
    assert not (root / d137.RECEIPT_PATH).exists()
    assert state["writes"] == [d137.GATE_PATH]
    assert state["docker_calls"] == state["sdk_calls"] == 0


def test_receipt_prepublication_status_drift_fails_without_receipt(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_gate(root, state)
    original = d137._gate_binding_for_activation
    calls = 0

    def drift_status(
        selected_root: Path,
        *,
        evidence_commit: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], bytes]:
        nonlocal calls
        calls += 1
        value = original(selected_root, evidence_commit=evidence_commit)
        if calls == 2:
            state["status_override"] = ["?? unrelated-receipt-prepublication-drift"]
        return value

    monkeypatch.setattr(d137, "_gate_binding_for_activation", drift_status)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="before receipt"):
        d137.create_d137_activation_receipt(repository=root)
    assert calls == 2
    assert not (root / d137.RECEIPT_PATH).exists()
    assert state["writes"] == [d137.GATE_PATH]


@pytest.mark.parametrize("phase", [d137.PHASE_DOCKER, d137.PHASE_SDK])
def test_phase_attempt_prepublication_predecessor_drift_fails_without_attempt(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    root, state = repository
    if phase == d137.PHASE_DOCKER:
        _seal_receipt(root, state)
        create = d137.create_d137_docker_attempt
        attempt_path = d137.DOCKER_ATTEMPT_PATH
    else:
        _seal_docker_transition(root, state)
        create = d137.create_d137_sdk_attempt
        attempt_path = d137.SDK_ATTEMPT_PATH
    original = d137._attempt_parent
    calls = 0

    def drifting_parent(
        selected_root: Path,
        selected_phase: str,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        nonlocal calls
        calls += 1
        predecessor, parent, recorded_at = original(selected_root, selected_phase)
        if calls == 2:
            predecessor = copy.deepcopy(predecessor)
            predecessor["file_bytes"] += 1
        return predecessor, parent, recorded_at

    monkeypatch.setattr(d137, "_attempt_parent", drifting_parent)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="drifted before attempt"):
        create(repository=root)
    assert calls == 2
    assert not (root / attempt_path).exists()
    assert state["docker_calls"] == (1 if phase == d137.PHASE_SDK else 0)
    assert state["sdk_calls"] == 0


@pytest.mark.parametrize("phase", [d137.PHASE_DOCKER, d137.PHASE_SDK])
def test_phase_attempt_prepublication_status_drift_fails_without_attempt(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    root, state = repository
    if phase == d137.PHASE_DOCKER:
        _seal_receipt(root, state)
        create = d137.create_d137_docker_attempt
        attempt_path = d137.DOCKER_ATTEMPT_PATH
    else:
        _seal_docker_transition(root, state)
        create = d137.create_d137_sdk_attempt
        attempt_path = d137.SDK_ATTEMPT_PATH
    original = d137._attempt_parent
    calls = 0

    def drift_status(
        selected_root: Path,
        selected_phase: str,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        nonlocal calls
        calls += 1
        value = original(selected_root, selected_phase)
        if calls == 2:
            state["status_override"] = ["?? unrelated-attempt-prepublication-drift"]
        return value

    monkeypatch.setattr(d137, "_attempt_parent", drift_status)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="before attempt"):
        create(repository=root)
    assert calls == 2
    assert not (root / attempt_path).exists()


@pytest.mark.parametrize("phase", [d137.PHASE_DOCKER, d137.PHASE_SDK])
@pytest.mark.parametrize("mutation", ["head", "status"])
def test_phase_started_prepublication_head_or_status_drift_writes_no_marker(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    mutation: str,
) -> None:
    root, state = repository
    if phase == d137.PHASE_DOCKER:
        _seal_docker_attempt(root, state)
        runner = d137.run_d137_docker_no_call_preflight
        attempt_path = d137.DOCKER_ATTEMPT_PATH
        attempt_commit = DOCKER_ATTEMPT_COMMIT
        started_path = d137.DOCKER_STARTED_PATH
    else:
        _seal_sdk_attempt(root, state)
        runner = d137.run_d137_sdk_no_call_preflight
        attempt_path = d137.SDK_ATTEMPT_PATH
        attempt_commit = SDK_ATTEMPT_COMMIT
        started_path = d137.SDK_STARTED_PATH
    original = d137._single_artifact_commit_binding
    mutated = False

    def drift_after_attempt_binding(
        selected_root: Path,
        *,
        commit: str,
        parent: str,
        path: Path,
        raw: bytes,
    ) -> dict[str, Any]:
        nonlocal mutated
        value = original(
            selected_root,
            commit=commit,
            parent=parent,
            path=path,
            raw=raw,
        )
        if not mutated and commit == attempt_commit and path == attempt_path:
            mutated = True
            if mutation == "head":
                state["head"] = "f0" * 20
            else:
                state["status_override"] = ["?? unrelated-pre-marker-drift"]
        return value

    monkeypatch.setattr(d137, "_single_artifact_commit_binding", drift_after_attempt_binding)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="before ACTION_STARTED"):
        runner(repository=root)
    assert mutated is True
    assert not (root / started_path).exists()
    assert state["docker_calls"] == (1 if phase == d137.PHASE_SDK else 0)
    assert state["sdk_calls"] == 0


def test_two_phase_ready_path_is_marker_first_idempotent_and_exactly_committed(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_docker_attempt(root, state)

    docker_first = d137.run_d137_docker_no_call_preflight(repository=root)
    docker_second = d137.run_d137_docker_no_call_preflight(repository=root)
    assert docker_first == docker_second
    assert docker_first["observation_status"] == no_call.DOCKER_READY_STATUS
    assert docker_first["passed"] is True
    assert docker_first["transition_commit"] is None
    assert state["docker_calls"] == 1
    assert state["events"] == ["docker"]
    assert state["writes"][-2:] == [d137.DOCKER_STARTED_PATH, d137.DOCKER_TERMINAL_PATH]

    state["head"] = DOCKER_TRANSITION_COMMIT
    docker_post = d137.validate_d137_docker_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert docker_post["transition_commit"]["parents"] == [DOCKER_ATTEMPT_COMMIT]
    assert docker_post["transition_commit"]["exact_action_started_and_terminal_add_commit"]

    sdk_attempt_first = d137.create_d137_sdk_attempt(repository=root)
    sdk_attempt_second = d137.create_d137_sdk_attempt(repository=root)
    assert sdk_attempt_first == sdk_attempt_second
    assert sdk_attempt_first["phase"] == d137.PHASE_SDK
    assert sdk_attempt_first["attempt_commit"] is None
    assert state["sdk_calls"] == 0

    state["head"] = SDK_ATTEMPT_COMMIT
    sdk_attempt_post = d137.validate_d137_sdk_attempt(repository=root, mode="post-commit")
    assert sdk_attempt_post["attempt_commit"]["parents"] == [DOCKER_TRANSITION_COMMIT]
    sdk_first = d137.run_d137_sdk_no_call_preflight(repository=root)
    sdk_second = d137.run_d137_sdk_no_call_preflight(repository=root)

    assert sdk_first == sdk_second
    assert sdk_first["observation_status"] == no_call.SDK_READY_STATUS
    assert sdk_first["passed"] is True
    assert sdk_first["transition_commit"] is None
    assert sdk_first["phase_consumed"] is True
    assert sdk_first["retry_allowed"] is False
    assert state["docker_calls"] == state["sdk_calls"] == 1
    assert state["events"] == ["docker", "sdk"]

    state["head"] = SDK_TRANSITION_COMMIT
    sdk_post = d137.validate_d137_sdk_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert sdk_post["transition_commit"]["parents"] == [SDK_ATTEMPT_COMMIT]
    assert sdk_post["transition_commit"]["exact_action_started_and_terminal_add_commit"]
    assert sdk_post["provider_evaluator_agent_call_count"] == 0
    assert sdk_post["cost_reserved_or_spent_usd"] == "0"


def test_blocked_docker_terminal_is_committable_and_forbids_sdk_phase(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    state["docker_observation"] = state["docker_blocked"]
    _seal_docker_attempt(root, state)

    result = d137.run_d137_docker_no_call_preflight(repository=root)

    assert result["status"] == d137.DOCKER_TERMINAL_BLOCKED_STATUS
    assert result["observation_status"] == no_call.DOCKER_BLOCKED_STATUS
    assert result["passed"] is False
    assert state["docker_calls"] == 1
    state["head"] = DOCKER_TRANSITION_COMMIT
    committed = d137.validate_d137_docker_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert committed["transition_commit"] is not None
    with pytest.raises(
        d137.D137NoCallPreflightSuccessorError,
        match="requires committed Docker READY",
    ):
        d137.create_d137_sdk_attempt(repository=root)
    assert state["sdk_calls"] == 0


def test_blocked_sdk_terminal_is_committable_consumed_and_never_retryable(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    state["sdk_observation"] = state["sdk_blocked"]
    _seal_sdk_attempt(root, state)

    result = d137.run_d137_sdk_no_call_preflight(repository=root)

    assert result["status"] == d137.SDK_TERMINAL_BLOCKED_STATUS
    assert result["observation_status"] == no_call.SDK_BLOCKED_STATUS
    assert result["passed"] is False
    assert result["phase_consumed"] is True
    assert result["retry_allowed"] is False
    assert state["docker_calls"] == state["sdk_calls"] == 1
    state["head"] = SDK_TRANSITION_COMMIT
    committed = d137.validate_d137_sdk_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert committed["transition_commit"]["parents"] == [SDK_ATTEMPT_COMMIT]
    assert committed["transition_commit"]["exact_action_started_and_terminal_add_commit"]
    assert committed["phase_consumed"] is True
    assert committed["retry_allowed"] is False


@pytest.mark.parametrize("phase", [d137.PHASE_DOCKER, d137.PHASE_SDK])
def test_post_marker_failure_is_consumed_preservable_and_never_retried(
    repository: tuple[Path, dict[str, Any]],
    phase: str,
) -> None:
    root, state = repository
    if phase == d137.PHASE_DOCKER:
        _seal_docker_attempt(root, state)
        state["docker_error"] = RuntimeError("synthetic Docker failure")
        runner = d137.run_d137_docker_no_call_preflight
        validator = d137.validate_d137_docker_action_started
        started_path = d137.DOCKER_STARTED_PATH
        marker_commit = DOCKER_MARKER_COMMIT
        call_key = "docker_calls"
    else:
        _seal_sdk_attempt(root, state)
        state["sdk_error"] = RuntimeError("synthetic SDK failure")
        runner = d137.run_d137_sdk_no_call_preflight
        validator = d137.validate_d137_sdk_action_started
        started_path = d137.SDK_STARTED_PATH
        marker_commit = SDK_MARKER_COMMIT
        call_key = "sdk_calls"

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="consumed"):
        runner(repository=root)
    marker_raw = (root / started_path).read_bytes()
    assert state[call_key] == 1
    pending = validator(repository=root, mode="pending-marker")
    assert pending["phase_consumed"] is True
    assert pending["retry_allowed"] is False
    assert pending["marker_preservation_commit"] is None

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="retry is forbidden"):
        runner(repository=root)
    assert state[call_key] == 1
    assert (root / started_path).read_bytes() == marker_raw

    state["head"] = marker_commit
    preserved = validator(repository=root, mode="post-preservation-commit")
    assert preserved["marker_preservation_commit"]["parents"] == [
        DOCKER_ATTEMPT_COMMIT if phase == d137.PHASE_DOCKER else SDK_ATTEMPT_COMMIT
    ]
    assert preserved["marker_preservation_commit"]["single_artifact_add_commit"] is True


@pytest.mark.parametrize("phase", [d137.PHASE_DOCKER, d137.PHASE_SDK])
@pytest.mark.parametrize("mutation", ["attempt", "started", "checkout"])
def test_post_helper_toctou_never_publishes_terminal_or_allows_second_helper_call(
    repository: tuple[Path, dict[str, Any]],
    phase: str,
    mutation: str,
) -> None:
    root, state = repository
    if phase == d137.PHASE_DOCKER:
        _seal_docker_attempt(root, state)
        state["docker_mutation"] = mutation
        runner = d137.run_d137_docker_no_call_preflight
        started_path = d137.DOCKER_STARTED_PATH
        terminal_path = d137.DOCKER_TERMINAL_PATH
        call_key = "docker_calls"
    else:
        _seal_sdk_attempt(root, state)
        state["sdk_mutation"] = mutation
        runner = d137.run_d137_sdk_no_call_preflight
        started_path = d137.SDK_STARTED_PATH
        terminal_path = d137.SDK_TERMINAL_PATH
        call_key = "sdk_calls"

    with pytest.raises(d137.D137NoCallPreflightSuccessorError):
        runner(repository=root)
    assert (root / started_path).exists()
    assert not (root / terminal_path).exists()
    assert state[call_key] == 1

    with pytest.raises(d137.D137NoCallPreflightSuccessorError):
        runner(repository=root)
    assert state[call_key] == 1
    assert not (root / terminal_path).exists()


def test_publication_collision_is_never_overwritten_or_observed_externally(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    original = d137._write_new
    collision = b"synthetic-racing-gate-collision"

    def race_publication(selected_root: Path, path: Path, raw: bytes) -> None:
        assert path == d137.GATE_PATH
        (selected_root / path).write_bytes(collision)
        original(selected_root, path, raw)

    monkeypatch.setattr(d137, "_write_new", race_publication)

    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="publication collision"):
        d137.run_d137_offline_source_gate(repository=root)
    assert (root / d137.GATE_PATH).read_bytes() == collision
    assert state["docker_calls"] == state["sdk_calls"] == 0


def test_sdk_attempt_before_committed_docker_ready_is_rejected_without_publication(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_receipt(root, state)

    with pytest.raises(
        d137.D137NoCallPreflightSuccessorError,
        match="path is absent|requires committed Docker READY",
    ):
        d137.create_d137_sdk_attempt(repository=root)
    assert not (root / d137.SDK_ATTEMPT_PATH).exists()
    assert state["docker_calls"] == state["sdk_calls"] == 0


def test_orphan_artifacts_fail_closed_without_helpers(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    orphan = root / d137.RECEIPT_PATH
    orphan.write_bytes(b"orphan-receipt")
    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="unexpected path"):
        d137.run_d137_offline_source_gate(repository=root)
    assert orphan.read_bytes() == b"orphan-receipt"
    orphan.unlink()

    _seal_docker_attempt(root, state)
    terminal = root / d137.DOCKER_TERMINAL_PATH
    terminal.write_bytes(b"orphan-terminal")
    with pytest.raises(d137.D137NoCallPreflightSuccessorError, match="terminal is orphaned"):
        d137.run_d137_docker_no_call_preflight(repository=root)
    assert terminal.read_bytes() == b"orphan-terminal"
    assert state["docker_calls"] == state["sdk_calls"] == 0
