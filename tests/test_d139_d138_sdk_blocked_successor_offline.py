from __future__ import annotations

import ast
import copy
import json
import shutil
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from patchloop.evals import d139_d138_sdk_blocked_successor_offline as d139
from patchloop.evals import d139_sdk_no_call_successor as no_call
from patchloop.util import canonical_json, sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]
HELPER_PATH = Path("patchloop/evals/d139_sdk_no_call_successor.py")
MODULE_PATH = Path("patchloop/evals/d139_d138_sdk_blocked_successor_offline.py")
SCRIPT_PATH = Path("scripts/build_d139_d138_sdk_blocked_successor_offline.py")
TEST_PATH = Path("tests/test_d139_d138_sdk_blocked_successor_offline.py")
FIXED_TEST_TEMP_ROOT = no_call.D139_FIXED_TEMP_ROOT
SECRET = "d139-ambient-secret-value-must-never-be-read-or-persisted"
_REAL_PUBLIC_RUNNER = no_call.run_d139_sdk_no_call_successor_observation
_REAL_ISOLATED_CHILD_PROCESS = no_call._run_isolated_child_process

SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
GATE_COMMIT = "c" * 40
GATE_TREE = "d" * 40
RECEIPT_COMMIT = "e" * 40
RECEIPT_TREE = "f" * 40
ATTEMPT_COMMIT = "1" * 40
ATTEMPT_TREE = "2" * 40
TRANSITION_COMMIT = "3" * 40
TRANSITION_TREE = "4" * 40
MARKER_COMMIT = "5" * 40
MARKER_TREE = "6" * 40

SOURCE_PREPARATION_FORBIDDEN_CALLS = {
    "_default_isolated_dependencies",
    "environment_present",
    "find_spec",
    "getenv",
    "getenvb",
    "import_module",
    "Popen",
    "run_d139_sdk_no_call_successor",
    "run_d139_sdk_no_call_successor_observation",
    "version",
}


def _dotted_call_name(value: ast.expr) -> str | None:
    parts: list[str] = []
    current: ast.expr = value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _module_level_call_names(source: str) -> set[str]:
    calls: set[str] = set()
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if (
            isinstance(statement, ast.If)
            and isinstance(statement.test, ast.Compare)
            and isinstance(statement.test.left, ast.Name)
            and statement.test.left.id == "__name__"
        ):
            continue
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            name = _dotted_call_name(node.func)
            if name is not None:
                calls.add(name)
    return calls


def _forbidden(label: str):
    def fail(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError(f"D-139 crossed forbidden {label} boundary")

    return fail


@pytest.fixture(autouse=True)
def forbid_unmocked_external_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    public_runner = no_call.run_d139_sdk_no_call_successor_observation

    def routed_runner(
        *,
        repository: str | Path | None = None,
        dependencies: (
            no_call.SDKWorkerDependencies | no_call.SDKIsolatedSuccessorDependencies | None
        ) = None,
        expected_committed_source_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if isinstance(dependencies, no_call.SDKWorkerDependencies):
            return no_call._run_worker_observation(
                repository=repository,
                dependencies=dependencies,
            )
        return public_runner(
            repository=repository,
            dependencies=dependencies,
            expected_committed_source_bindings=expected_committed_source_bindings,
        )

    monkeypatch.setattr(no_call, "run_d139_sdk_no_call_successor_observation", routed_runner)
    monkeypatch.setattr(
        no_call,
        "_default_isolated_dependencies",
        _forbidden("default isolated SDK or environment observation"),
    )
    monkeypatch.setattr(
        no_call,
        "_run_isolated_child_process",
        _forbidden("real isolated child process"),
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
    fixed_root = FIXED_TEST_TEMP_ROOT.resolve(strict=True)
    root = Path(
        tempfile.mkdtemp(
            prefix="patchloop-d139-sdk-test-",
            dir=fixed_root,
        )
    )
    model_source = """\
import httpx
from openai import OpenAI

OFFICIAL_API_BASE_URL = \"https://api.openai.com/v1\"

def create_openai_client(*, api_key: str):
    http_client = httpx.Client(trust_env=False)
    constructor_kwargs: dict[str, object] = {
        \"api_key\": api_key,
        \"base_url\": OFFICIAL_API_BASE_URL,
        \"http_client\": http_client,
    }
    return OpenAI(**constructor_kwargs)
"""
    lock_source = """\
[[package]]
name = \"httpx\"
version = \"0.28.1\"

[[package]]
name = \"openai\"
version = \"2.47.0\"
"""
    (root / "patchloop/agent").mkdir(parents=True)
    (root / "patchloop/evals").mkdir(parents=True)
    (root / "patchloop/agent/model.py").write_text(model_source, encoding="utf-8")
    (root / "patchloop/evals/d139_sdk_no_call_successor.py").write_text(
        "# d139 synthetic helper source\n",
        encoding="utf-8",
    )
    (root / "uv.lock").write_text(lock_source, encoding="utf-8")
    for relative in (
        Path(".venv/d139-synthetic/python.exe"),
        Path(".venv/d139-synthetic/httpx/__init__.py"),
        Path(".venv/d139-synthetic/openai/__init__.py"),
        Path(".venv/d139-synthetic/httpx/loaded-elsewhere.py"),
        Path(".venv/d139-synthetic/openai/loaded-elsewhere.py"),
        Path("ignored-shadow/httpx/__init__.py"),
        Path("ignored-shadow/openai/__init__.py"),
        Path("outside-venv/python.exe"),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"d139-synthetic-non-sdk-placeholder\n")
    try:
        yield root
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == fixed_root
            assert root.name.startswith("patchloop-d139-sdk-test-")
            shutil.rmtree(root)


def _sdk_dependencies(
    root: Path,
    *,
    launch_drift: str | None = None,
    interpreter_outside_venv: bool = False,
    interpreter_lexical_alias: bool = False,
    module_spec_case: str | None = None,
    module_spec_case_name: str = "openai",
    version_drift: str | None = None,
    loaded_module_origin_mismatch: str | None = None,
    binding_drift: str | None = None,
    preimport_binding_drift: str | None = None,
    origin_drift_before_import: str | None = None,
    base_url_drift: bool = False,
    max_retries_drift: bool = False,
    dispatch_during_constructor: bool = False,
    openai_owns_http: bool = False,
    venv_drift_during_httpx_spec: bool = False,
    venv_drift_during_probe: bool = False,
    preloaded_module: str | None = None,
    sequential_openai_drift: str | None = None,
    aba_committed_source: str | None = None,
    bootstrap_attempt: str | None = None,
) -> tuple[no_call.SDKWorkerDependencies, dict[str, Any]]:
    state: dict[str, Any] = {
        "launch_calls": 0,
        "presence_queries": [],
        "file_bindings": [],
        "distribution_queries": [],
        "module_spec_queries": [],
        "preloaded_queries": [],
        "imports": [],
        "transport_handlers": [],
        "http_clients": [],
        "openai_clients": [],
        "binding_counts": {},
        "sequential_drift_active": False,
    }

    class FakeTransport:
        def __init__(self, handler: Any) -> None:
            self.handler = handler
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
            if dispatch_during_constructor:
                kwargs["http_client"].transport.handler(SimpleNamespace())
            if venv_drift_during_probe:
                (root / ".venv").rename(root / ".venv-drifted-after-import")
                state["venv_drifted_after_import"] = True

        def close(self) -> None:
            self.close_count += 1
            if openai_owns_http:
                self.kwargs["http_client"].close()

    httpx_module = ModuleType("httpx")
    httpx_relative = (
        ".venv/d139-synthetic/httpx/loaded-elsewhere.py"
        if loaded_module_origin_mismatch == "httpx"
        else ".venv/d139-synthetic/httpx/../httpx/__init__.py"
        if loaded_module_origin_mismatch == "httpx-lexical"
        else ".venv/d139-synthetic/httpx/__init__.py"
    )
    httpx_module.__file__ = str(root / httpx_relative)
    httpx_module.__version__ = "0.28.1"
    httpx_module.MockTransport = FakeTransport
    httpx_module.Client = FakeHTTPClient

    openai_module = ModuleType("openai")
    openai_relative = (
        ".venv/d139-synthetic/openai/loaded-elsewhere.py"
        if loaded_module_origin_mismatch == "openai"
        else ".venv/d139-synthetic/openai/../openai/__init__.py"
        if loaded_module_origin_mismatch == "openai-lexical"
        else ".venv/d139-synthetic/openai/__init__.py"
    )
    openai_module.__file__ = str(root / openai_relative)
    openai_module.__version__ = "2.47.0"
    openai_module.OpenAI = FakeOpenAIClient

    def launch_contract() -> Mapping[str, Any]:
        state["launch_calls"] += 1
        value = copy.deepcopy(no_call.EXACT_LAUNCH_CONTRACT)
        if launch_drift is not None:
            value[launch_drift] = not value[launch_drift]
        return value

    def file_binding(path: Path) -> dict[str, Any]:
        state["file_bindings"].append(path)
        resolved = path.resolve(strict=True)
        if resolved == (root / ".venv/d139-synthetic/python.exe").resolve(strict=True):
            role = "python"
        elif "openai" in resolved.parts:
            role = "openai"
        elif "httpx" in resolved.parts:
            role = "httpx"
        else:
            role = "other"
        state["binding_counts"][role] = state["binding_counts"].get(role, 0) + 1
        post_probe_threshold = 2 if role == "python" else 3
        drifted = (
            (binding_drift == role and state["binding_counts"][role] > post_probe_threshold)
            or (preimport_binding_drift == role and state["binding_counts"][role] > 1)
            or (
                sequential_openai_drift == "binding"
                and state["sequential_drift_active"]
                and role == "openai"
            )
        )
        digest = "4" if drifted else "3"
        return {
            "file_name": resolved.name,
            "file_bytes": 1,
            "file_sha256": "sha256:" + digest * 64,
            "linklike": False,
        }

    def distribution_version(name: str) -> str | None:
        state["distribution_queries"].append(name)
        versions = {"httpx": "0.28.1", "openai": "2.47.0"}
        drifted = name == version_drift or (
            sequential_openai_drift == "version"
            and state["sequential_drift_active"]
            and name == "openai"
        )
        return "0.0.0-drift" if drifted else versions[name]

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
                return SimpleNamespace(origin=str(root / "missing" / name / "__init__.py"))
            if module_spec_case == "outside":
                return SimpleNamespace(origin=str(root / "ignored-shadow" / name / "__init__.py"))
            if module_spec_case == "lexical-alias":
                return SimpleNamespace(
                    origin=str(root / ".venv/d139-synthetic" / name / ".." / name / "__init__.py")
                )
            assert module_spec_case is None
        if name == origin_drift_before_import and state["module_spec_queries"].count(name) > 1:
            return SimpleNamespace(
                origin=str(root / ".venv/d139-synthetic" / name / "loaded-elsewhere.py")
            )
        if (
            sequential_openai_drift == "origin"
            and state["sequential_drift_active"]
            and name == "openai"
        ):
            return SimpleNamespace(
                origin=str(root / ".venv/d139-synthetic/openai/loaded-elsewhere.py")
            )
        return SimpleNamespace(origin=str(root / ".venv/d139-synthetic" / name / "__init__.py"))

    def import_module(name: str) -> ModuleType:
        state["imports"].append(name)
        if name == "httpx":
            state["sequential_drift_active"] = True
            if aba_committed_source == "lock":
                (root / "uv.lock").write_bytes(b"d139-swapped-lock\n")
        elif name == "openai" and aba_committed_source == "model":
            (root / "patchloop/agent/model.py").write_bytes(b"d139-swapped-model\n")
        return {"httpx": httpx_module, "openai": openai_module}[name]

    def module_is_preloaded(name: str) -> bool:
        state["preloaded_queries"].append(name)
        assert name in {"httpx", "openai"}
        return name == preloaded_module or (
            sequential_openai_drift == "preloaded"
            and state["sequential_drift_active"]
            and name == "openai"
        )

    bootstrap_counters = {key: 0 for key in no_call._GUARD_COUNTER_KEYS}
    if bootstrap_attempt is not None:
        bootstrap_counters[bootstrap_attempt] = 1
    dependencies = no_call.SDKWorkerDependencies(
        python_executable=(
            root / "outside-venv/python.exe"
            if interpreter_outside_venv
            else root / ".venv/d139-synthetic/../d139-synthetic/python.exe"
            if interpreter_lexical_alias
            else root / ".venv/d139-synthetic/python.exe"
        ),
        python_version="3.13.synthetic",
        launch_contract=launch_contract,
        file_binding=file_binding,
        distribution_version=distribution_version,
        find_module_spec=find_module_spec,
        module_is_preloaded=module_is_preloaded,
        import_module=import_module,
        expected_committed_source_bindings=_expected_committed_source_bindings(root),
        bootstrap_helper_binding_verified=True,
        bootstrap_audit_hook_installed=True,
        bootstrap_guard_counters=bootstrap_counters,
    )
    return dependencies, state


def _isolated_dependencies(
    root: Path,
    *,
    worker: dict[str, Any],
    credential_present: bool = True,
    pythonhome_present: bool = False,
    pythonpath_present: bool = False,
    launch_drift: str | None = None,
    interpreter_outside_venv: bool = False,
    interpreter_lexical_alias: bool = False,
    committed_binding_mismatch: str | None = None,
    binding_drift: str | None = None,
    remove_child_cwd: bool = False,
    execution_overrides: Mapping[str, Any] | None = None,
) -> tuple[no_call.SDKIsolatedSuccessorDependencies, dict[str, Any]]:
    state: dict[str, Any] = {
        "launch_calls": 0,
        "presence_queries": [],
        "file_bindings": [],
        "binding_counts": {},
        "child_requests": [],
        "parent_imports": [],
    }

    def launch_contract() -> Mapping[str, Any]:
        state["launch_calls"] += 1
        value = copy.deepcopy(no_call.EXACT_LAUNCH_CONTRACT)
        if launch_drift is not None:
            value[launch_drift] = not value[launch_drift]
        return value

    def environment_present(name: str) -> bool:
        state["presence_queries"].append(name)
        assert name in no_call.SDK_ENVIRONMENT_NAMES
        return {
            "OPENAI_API_KEY": credential_present,
            "PYTHONHOME": pythonhome_present,
            "PYTHONPATH": pythonpath_present,
        }[name]

    def file_binding(path: Path) -> dict[str, Any]:
        resolved = path.resolve(strict=True)
        state["file_bindings"].append(resolved)
        relative = resolved.relative_to(root.resolve(strict=True)).as_posix()
        roles = {
            ".venv/d139-synthetic/python.exe": "python",
            "patchloop/evals/d139_sdk_no_call_successor.py": "helper",
            "patchloop/agent/model.py": "model",
            "uv.lock": "lock",
        }
        role = roles[relative]
        state["binding_counts"][role] = state["binding_counts"].get(role, 0) + 1
        drifted = committed_binding_mismatch == role or (
            binding_drift == role and state["binding_counts"][role] > 1
        )
        expected = _expected_committed_source_bindings(root)
        if role in expected:
            file_bytes = expected[role]["file_bytes"]
            digest = expected[role]["file_sha256"]
        else:
            file_bytes = 31
            digest = "sha256:" + "3" * 64
        if drifted:
            digest = "sha256:" + "4" * 64
        return {
            "file_name": resolved.name,
            "file_bytes": file_bytes,
            "file_sha256": digest,
            "linklike": False,
        }

    def run_child(request: no_call.IsolatedChildRequest) -> no_call.IsolatedChildExecution:
        state["child_requests"].append(request)
        assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
        assert state["parent_imports"] == []
        assert request.cwd.is_dir()
        assert request.cwd.resolve(strict=True).parent == FIXED_TEST_TEMP_ROOT.resolve(strict=True)
        assert not request.cwd.resolve(strict=True).is_relative_to(root.resolve(strict=True))
        assert len(request.command) == 16
        assert request.command[0] == str(
            (root / ".venv/d139-synthetic/python.exe").resolve(strict=True)
        )
        assert request.command[1:6] == (
            "-E",
            "-s",
            "-B",
            "-c",
            no_call.ISOLATED_CHILD_BOOTSTRAP,
        )
        assert request.command[6] == str(root.resolve(strict=True))
        assert request.command[7] == str(
            (root / "patchloop/evals/d139_sdk_no_call_successor.py").resolve(strict=True)
        )
        assert request.command[8] == str(FIXED_TEST_TEMP_ROOT.resolve(strict=True))
        assert request.command[9] == no_call.ISOLATED_CHILD_ELIGIBILITY_TOKEN
        expected = _expected_committed_source_bindings(root)
        assert request.command[10] == expected["helper"]["file_sha256"]
        assert request.command[11] == str(expected["helper"]["file_bytes"])
        assert request.command[12] == expected["model"]["file_sha256"]
        assert request.command[13] == str(expected["model"]["file_bytes"])
        assert request.command[14] == expected["lock"]["file_sha256"]
        assert request.command[15] == str(expected["lock"]["file_bytes"])
        assert request.environment_entries == ()
        assert request.timeout_seconds == no_call.ISOLATED_CHILD_TIMEOUT_SECONDS
        assert request.stdout_limit_bytes == no_call.ISOLATED_CHILD_STDOUT_LIMIT_BYTES
        assert request.stderr_limit_bytes == no_call.ISOLATED_CHILD_STDERR_LIMIT_BYTES
        if remove_child_cwd:
            request.cwd.rmdir()
        canonical = no_call._compact_json_bytes(worker) + b"\n"
        values: dict[str, Any] = {
            "returncode": 0,
            "stdout": canonical,
            "stderr": b"",
            "timed_out": False,
            "stdout_overflow": False,
            "stderr_overflow": False,
            "process_start_count": 1,
            "process_kill_count": 0,
        }
        values.update(dict(execution_overrides or {}))
        return no_call.IsolatedChildExecution(**values)

    dependencies = no_call.SDKIsolatedSuccessorDependencies(
        python_executable=(
            root / "outside-venv/python.exe"
            if interpreter_outside_venv
            else root / ".venv/d139-synthetic/../d139-synthetic/python.exe"
            if interpreter_lexical_alias
            else root / ".venv/d139-synthetic/python.exe"
        ),
        python_version="3.13.synthetic",
        launch_contract=launch_contract,
        file_binding=file_binding,
        environment_present=environment_present,
        child_temp_root=FIXED_TEST_TEMP_ROOT,
        run_isolated_child=run_child,
    )
    return dependencies, state


def _expected_committed_source_bindings(root: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "helper": "patchloop/evals/d139_sdk_no_call_successor.py",
        "model": "patchloop/agent/model.py",
        "lock": "uv.lock",
    }
    result: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        raw = (root / path).read_bytes()
        result[name] = {
            "repository_relative_path": path,
            "file_bytes": len(raw),
            "file_sha256": sha256_bytes(raw),
            "linklike": False,
        }
    return result


def _substitute_helper_committed_sha(value: dict[str, Any], digest: str) -> None:
    parent = value["observation"]["source_bindings"]["helper"]
    parent["expected_committed_file_sha256"] = digest
    parent["file_binding_before"]["file_sha256"] = digest
    parent["file_binding_after"]["file_sha256"] = digest
    parent["committed_binding_match_before"] = True
    parent["binding_stable"] = True
    worker = value["observation"]["isolated_child"]["worker_observation"]
    worker["observation"]["committed_source_bindings"]["helper"][
        "expected_committed_file_sha256"
    ] = digest


def _assert_zero_sensitive_delegates(state: dict[str, Any]) -> None:
    assert state["file_bindings"] == []
    assert state["distribution_queries"] == []
    assert state["module_spec_queries"] == []
    assert state["preloaded_queries"] == []
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert state["http_clients"] == []
    assert state["openai_clients"] == []


@pytest.fixture
def repository(
    monkeypatch: pytest.MonkeyPatch,
    sdk_repository: Path,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    fixed_root = FIXED_TEST_TEMP_ROOT.resolve(strict=True)
    root = Path(
        tempfile.mkdtemp(
            prefix="patchloop-d139-orchestrator-test-",
            dir=fixed_root,
        )
    )
    (root / ".git").mkdir()
    (root / d139.GATE_PATH.parent).mkdir(parents=True)

    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker_ready = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    expected_source_bindings = _expected_committed_source_bindings(sdk_repository)
    ready_dependencies, ready_parent_state = _isolated_dependencies(
        sdk_repository,
        worker=worker_ready,
    )
    ready = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=ready_dependencies,
        expected_committed_source_bindings=expected_source_bindings,
    )
    blocked_dependencies, blocked_parent_state = _isolated_dependencies(
        sdk_repository,
        worker=worker_ready,
        credential_present=False,
    )
    blocked = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=blocked_dependencies,
        expected_committed_source_bindings=expected_source_bindings,
    )
    predecessor = {
        "source_commit": {
            "commit": d139.D138_SOURCE_COMMIT,
            "tree": d139.D138_SOURCE_TREE,
            "parents": [d139.D138_SOURCE_PARENT],
        },
        "artifacts": {
            d139.D138_SDK_TERMINAL_PATH.as_posix(): {
                "recorded_at": "2026-08-10T01:59:00Z",
            }
        },
        "final_transition_commit": {
            "commit": d139.D138_SDK_TRANSITION_COMMIT,
            "tree": d139.D138_SDK_TRANSITION_TREE,
            "parents": [d139.D138_SDK_ATTEMPT_COMMIT],
        },
        "consumed": True,
        "retry_allowed": False,
        "credential_value_observation_count": 0,
        "environment_presence_check_count": 3,
        "dotenv_read_count": 0,
        "child_process_start_count": 0,
        "sdk_import_count": 0,
        "sdk_probe_count": 0,
        "transport_dispatch_count": 0,
        "network_call_count": 0,
    }
    runtime_rows = {
        row["repository_relative_path"]: row for row in expected_source_bindings.values()
    }
    source = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d139.D138_SDK_TRANSITION_COMMIT],
        "exact_four_path_add_commit": True,
        "source_bindings": [
            {
                "path": path.as_posix(),
                "file_bytes": runtime_rows.get(path.as_posix(), {}).get("file_bytes", 31),
                "file_sha256": runtime_rows.get(path.as_posix(), {}).get(
                    "file_sha256", "sha256:" + "3" * 64
                ),
                "linklike": False,
            }
            for path in d139.SOURCE_BINDING_PATHS
        ],
        "loaded_module_provenance_validated": True,
    }
    git_cli = {
        "path": str(d139.GIT_ENGINE_PATH),
        "file_bytes": d139.GIT_ENGINE_FILE_BYTES,
        "file_sha256": d139.GIT_ENGINE_FILE_SHA256,
        "linklike": False,
        "version": d139.GIT_VERSION,
        "repository_local_core_autocrlf": "false",
        "minimal_secret_free_environment": True,
        "environment_value_observation_count": 0,
        "shell_used": False,
    }
    identities = {
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [d139.D138_SDK_TRANSITION_COMMIT],
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
        ATTEMPT_COMMIT: {
            "commit": ATTEMPT_COMMIT,
            "tree": ATTEMPT_TREE,
            "parents": [RECEIPT_COMMIT],
        },
        TRANSITION_COMMIT: {
            "commit": TRANSITION_COMMIT,
            "tree": TRANSITION_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
        MARKER_COMMIT: {
            "commit": MARKER_COMMIT,
            "tree": MARKER_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
    }
    state: dict[str, Any] = {
        "head": SOURCE_COMMIT,
        "time_index": 0,
        "writes": [],
        "events": [],
        "observer_calls": 0,
        "observation": ready,
        "ready": ready,
        "blocked": blocked,
        "worker_ready": worker_ready,
        "ready_parent_state": ready_parent_state,
        "blocked_parent_state": blocked_parent_state,
        "expected_source_bindings": expected_source_bindings,
        "observer_error": None,
        "observer_mutation": None,
        "status_override": None,
        "extra_diff": {},
        "identity_overrides": {},
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, Any]:
        return copy.deepcopy(state["identity_overrides"].get(commit, identities[commit]))

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == SOURCE_COMMIT:
            rows = [
                {"status": "A", "path": path.as_posix()}
                for path in sorted(d139.IMPLEMENTATION_PATHS, key=lambda path: path.as_posix())
            ]
        elif commit == GATE_COMMIT:
            rows = [
                {"status": "A", "path": d139.GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d139.ACTIVE_DOC_PATHS),
            ]
        elif commit == RECEIPT_COMMIT:
            rows = [{"status": "A", "path": d139.RECEIPT_PATH.as_posix()}]
        elif commit == ATTEMPT_COMMIT:
            rows = [{"status": "A", "path": d139.ATTEMPT_PATH.as_posix()}]
        elif commit == TRANSITION_COMMIT:
            rows = [
                {"status": "A", "path": d139.STARTED_PATH.as_posix()},
                {"status": "A", "path": d139.TERMINAL_PATH.as_posix()},
            ]
        elif commit == MARKER_COMMIT:
            rows = [{"status": "A", "path": d139.STARTED_PATH.as_posix()}]
        else:
            raise AssertionError(f"unexpected synthetic commit: {commit}")
        return [*rows, *copy.deepcopy(state["extra_diff"].get(commit, []))]

    def commit_blob(_root: Path, commit: str, path: Path) -> tuple[str, bytes]:
        allowed = {
            GATE_COMMIT: {d139.GATE_PATH},
            RECEIPT_COMMIT: {d139.RECEIPT_PATH},
            ATTEMPT_COMMIT: {d139.ATTEMPT_PATH},
            TRANSITION_COMMIT: {d139.STARTED_PATH, d139.TERMINAL_PATH},
            MARKER_COMMIT: {d139.STARTED_PATH},
        }
        assert path in allowed[commit]
        raw = (root / path).read_bytes()
        oid = sha256_bytes(f"{commit}:{path.as_posix()}".encode())[7:47]
        return oid, raw

    def status_lines(_root: Path) -> list[str]:
        if state["status_override"] is not None:
            return list(state["status_override"])
        head = state["head"]
        if head == SOURCE_COMMIT and (root / d139.GATE_PATH).exists():
            paths = [d139.GATE_PATH]
        elif head == GATE_COMMIT and (root / d139.RECEIPT_PATH).exists():
            paths = [d139.RECEIPT_PATH]
        elif head == RECEIPT_COMMIT and (root / d139.ATTEMPT_PATH).exists():
            paths = [d139.ATTEMPT_PATH]
        elif head == ATTEMPT_COMMIT:
            paths = [
                path for path in (d139.STARTED_PATH, d139.TERMINAL_PATH) if (root / path).exists()
            ]
        else:
            paths = []
        temporary_paths = [
            path.relative_to(root) for path in (root / d139.GATE_PATH.parent).glob(".*.d139-*.tmp")
        ]
        paths.extend(temporary_paths)
        return [f"?? {path.as_posix()}" for path in paths]

    real_write_new = d139._write_new

    def write_new(
        selected_root: Path,
        path: Path,
        raw: bytes,
        *,
        prepublish: d139.PrepublishCheck | None = None,
    ) -> None:
        real_write_new(selected_root, path, raw, prepublish=prepublish)
        state["writes"].append(path)
        state["events"].append(f"write:{path.name}")

    def now() -> str:
        index = state["time_index"]
        state["time_index"] += 1
        return f"2026-08-10T02:{index:02d}:00Z"

    def observe(
        *,
        repository: str | Path | None = None,
        expected_committed_source_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        del repository
        assert expected_committed_source_bindings == state["expected_source_bindings"]
        state["observer_calls"] += 1
        state["events"].append("observe-membership")
        assert (root / d139.STARTED_PATH).is_file()
        assert not (root / d139.TERMINAL_PATH).exists()
        error = state["observer_error"]
        if error is not None:
            raise error
        mutation = state["observer_mutation"]
        if mutation == "attempt":
            (root / d139.ATTEMPT_PATH).write_bytes(b"d139-attempt-toctou")
        elif mutation == "started":
            (root / d139.STARTED_PATH).write_bytes(b"d139-started-toctou")
        elif mutation == "checkout":
            state["status_override"] = [
                f"?? {d139.STARTED_PATH.as_posix()}",
                "?? unrelated-post-helper-drift",
            ]
        return copy.deepcopy(state["observation"])

    monkeypatch.setattr(d139, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d139, "_validate_d138_chain", lambda _root: copy.deepcopy(predecessor))
    monkeypatch.setattr(
        d139,
        "_source_identity",
        lambda _root, commit: (
            copy.deepcopy(source)
            if commit == SOURCE_COMMIT
            else (_ for _ in ()).throw(AssertionError(f"unexpected source commit: {commit}"))
        ),
    )
    monkeypatch.setattr(d139, "_git_cli_observation", lambda _root: copy.deepcopy(git_cli))
    monkeypatch.setattr(d139, "_commit_identity", commit_identity)
    monkeypatch.setattr(d139, "_diff_rows", diff_rows)
    monkeypatch.setattr(d139, "_commit_blob", commit_blob)
    monkeypatch.setattr(d139, "_head", lambda _root: state["head"])
    monkeypatch.setattr(d139, "_status_lines", status_lines)
    monkeypatch.setattr(d139, "_write_new", write_new)
    monkeypatch.setattr(d139, "_now", now)
    monkeypatch.setattr(
        no_call,
        "current_d139_sdk_launch_contract",
        lambda: copy.deepcopy(no_call.EXACT_LAUNCH_CONTRACT),
    )
    monkeypatch.setattr(no_call, "run_d139_sdk_no_call_successor_observation", observe)
    try:
        yield root, state
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == fixed_root
            assert root.name.startswith("patchloop-d139-orchestrator-test-")
            shutil.rmtree(root)


def _seal_gate(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    result = d139.run_d139_offline_source_gate(repository=root)
    state["head"] = GATE_COMMIT
    post = d139.validate_d139_offline_source_gate(
        repository=root,
        mode="post-evidence-commit",
    )
    assert post["evidence_commit"] is not None
    return result


def _seal_receipt(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_gate(root, state)
    result = d139.create_d139_activation_receipt(repository=root)
    state["head"] = RECEIPT_COMMIT
    post = d139.validate_d139_activation_receipt(repository=root, mode="post-commit")
    assert post["receipt_commit"] is not None
    return result


def _seal_attempt(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _seal_receipt(root, state)
    result = d139.create_d139_sdk_attempt(repository=root)
    state["head"] = ATTEMPT_COMMIT
    post = d139.validate_d139_sdk_attempt(repository=root, mode="post-commit")
    assert post["attempt_commit"] is not None
    return result


def test_launch_contract_is_exact_and_requires_dash_e_dash_s_dash_b() -> None:
    assert no_call.EXACT_LAUNCH_CONTRACT == {
        "ignore_python_environment": True,
        "user_site_disabled": True,
        "bytecode_writes_disabled": True,
        "isolated_mode": False,
        "safe_path_mode": False,
    }
    assert no_call.LAUNCHER_SOURCE_CONTRACT == {
        "required_python_flags": ["-E", "-s", "-B"],
        "ambient_environment_policy": "inherit-unchanged-required-not-runtime-observed",
        "environment_override_count": 0,
        "exact_cli_action": "--run-sdk-preflight",
    }
    assert (
        no_call.validate_d139_sdk_launch_contract(copy.deepcopy(no_call.EXACT_LAUNCH_CONTRACT))
        == no_call.EXACT_LAUNCH_CONTRACT
    )
    child = no_call.ISOLATED_CHILD_CONTRACT
    assert child["required_python_flags"] == ["-E", "-s", "-B"]
    assert child["child_environment_entries"] == []
    assert child["ambient_environment_entry_forward_count"] == 0
    assert child["credential_value_forward_count"] == 0
    assert child["fixed_temp_root"] == str(FIXED_TEST_TEMP_ROOT)
    assert child["timeout_seconds"] == 20
    assert child["stdout_contract"] == "one-canonical-json-line"
    assert child["stderr_contract"] == "empty"
    assert child["raw_captured_output_persistence_authorized"] is False
    assert child["validated_parsed_worker_observation_persistence_authorized"] is True
    assert child["audit_hook_coverage_boundary"] == "bootstrap-after-cpython-and-site-startup"
    assert child["pre_bootstrap_startup_network_coverage"] == "not-observed-not-claimed"
    assert (
        child["bootstrap_sys_path_policy"]
        == "exact-nonlink-base-prefix-before-repository-venv-only"
    )
    assert child["worker_sys_path_policy"] == child["bootstrap_sys_path_policy"]
    assert child["repository_source_sys_path_entry_forward_count"] == 0
    assert len(child["argv_layout"]) == 16
    assert child["argv_layout"][-6:] == [
        "expected-helper-sha256",
        "expected-helper-file-bytes",
        "expected-model-sha256",
        "expected-model-file-bytes",
        "expected-lock-sha256",
        "expected-lock-file-bytes",
    ]
    bootstrap = no_call.ISOLATED_CHILD_BOOTSTRAP
    assert "class _D139BootstrapEnvironment:" in bootstrap
    assert "class _D139BootstrapEnvironment(dict):" not in bootstrap
    for operation in (
        "keys = _deny_read",
        "items = _deny_read",
        "values = _deny_read",
        "copy = _deny_read",
        "update = _deny_mutation",
        "clear = _deny_mutation",
        "__ior__ = _deny_mutation",
        "def __iter__(",
    ):
        assert operation in bootstrap
    assert bootstrap.index("sys.addaudithook") < bootstrap.index("exec(compile")


@pytest.mark.parametrize(
    "field",
    [
        "ignore_python_environment",
        "user_site_disabled",
        "bytecode_writes_disabled",
        "isolated_mode",
        "safe_path_mode",
    ],
)
def test_launch_mismatch_blocks_before_any_environment_or_sdk_delegate(
    sdk_repository: Path,
    field: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        launch_drift=field,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "launch"
    assert result["observation"]["environment_presence_bits"] is None
    assert result["blockers"] == ["exact-python-launch-flags-differ"]
    assert state["launch_calls"] == 1
    assert state["presence_queries"] == []
    assert state["file_bindings"] == []
    assert state["child_requests"] == []
    assert state["parent_imports"] == []
    assert result["activity"]["environment_value_read_count"] == 0
    assert result["activity"]["parent_network_call_count"] == 0


def test_worker_ready_observation_is_provenance_bound_and_dispatch_zero(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository)

    result = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_READY_STATUS
    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["observation"]["stage"] == "complete"
    assert result["observation"]["parent_eligibility_bits"] == {
        "OPENAI_API_KEY": True,
        "PYTHONHOME": False,
        "PYTHONPATH": False,
    }
    assert state["presence_queries"] == []
    assert state["preloaded_queries"] == ["httpx", "openai", "httpx", "openai"]
    assert state["module_spec_queries"] == [
        "httpx",
        "openai",
        "httpx",
        "openai",
        "httpx",
        "openai",
        "openai",
        "httpx",
    ]
    assert state["distribution_queries"] == [
        "httpx",
        "openai",
        "httpx",
        "openai",
        "httpx",
        "openai",
        "openai",
        "httpx",
    ]
    assert state["imports"] == ["httpx", "openai"]
    assert len(state["transport_handlers"]) == 1
    assert all(client.close_count == 1 for client in state["http_clients"])
    assert all(client.close_count == 1 for client in state["openai_clients"])
    assert result["observation"]["synthetic_probe"]["transport_dispatch_count"] == 0
    assert result["activity"]["environment_value_read_count"] == 0
    assert result["activity"]["dotenv_read_count"] == 0
    assert result["activity"]["network_call_count"] == 0
    assert result["activity"]["bootstrap_audit_hook_installed_count"] == 1
    assert result["activity"]["bootstrap_environment_value_read_attempt_count"] == 0
    assert result["activity"]["bootstrap_environment_mutation_attempt_count"] == 0
    assert result["activity"]["bootstrap_dotenv_open_attempt_count"] == 0
    assert result["activity"]["bootstrap_network_denied_attempt_count"] == 0
    assert result["activity"]["bootstrap_subprocess_denied_attempt_count"] == 0
    assert result["activity"]["worker_audit_hook_installed_count"] == 1
    assert result["activity"]["environment_value_read_attempt_count"] == 0
    assert result["activity"]["environment_mutation_attempt_count"] == 0
    assert result["activity"]["dotenv_open_attempt_count"] == 0
    assert result["activity"]["network_denied_attempt_count"] == 0
    assert result["activity"]["subprocess_denied_attempt_count"] == 0
    assert result["activity"]["startup_environment_entry_count"] == 0
    assert result["activity"]["committed_helper_bootstrap_verification_count"] == 1
    assert result["activity"]["committed_model_binding_verification_count"] == 2
    assert result["activity"]["committed_lock_binding_verification_count"] == 8
    assert result["activity"]["provider_evaluator_or_agent_call_count"] == 0
    assert SECRET not in canonical_json(result)
    assert no_call._validate_worker_observation(result) == result


@pytest.mark.parametrize(
    ("kwargs", "blocker"),
    [
        ({"credential_present": False}, "openai-api-key-presence-bit-is-false"),
        ({"pythonhome_present": True}, "pythonhome-presence-bit-is-true"),
        ({"pythonpath_present": True}, "pythonpath-presence-bit-is-true"),
    ],
)
def test_presence_blocks_before_python_import_or_probe_and_reads_no_values(
    sdk_repository: Path,
    kwargs: dict[str, bool],
    blocker: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        **kwargs,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "presence"
    assert blocker in result["blockers"]
    assert "isolated-sdk-worker-suppressed-by-presence-checks" in result["blockers"]
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
    assert state["file_bindings"] == []
    assert state["child_requests"] == []
    assert state["parent_imports"] == []
    assert result["activity"]["environment_presence_check_count"] == 3
    assert result["activity"]["environment_value_read_count"] == 0
    assert result["activity"]["parent_sdk_dynamic_import_count"] == 0
    assert SECRET not in canonical_json(result)


def test_wrong_interpreter_blocks_before_binding_spec_distribution_or_import(
    sdk_repository: Path,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        interpreter_outside_venv=True,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "python"
    assert "python-interpreter-is-not-repository-venv" in result["blockers"]
    assert state["file_bindings"] == []
    assert state["child_requests"] == []
    assert state["parent_imports"] == []
    assert "outside-venv" not in canonical_json(result)


@pytest.mark.parametrize("layer", ["parent", "worker"])
def test_linklike_python_or_venv_ancestor_is_rejected_before_binding_or_child(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    layer: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    original = no_call._is_linklike
    target = (
        sdk_repository / ".venv"
        if layer == "parent"
        else sdk_repository / ".venv/d139-synthetic/python.exe"
    ).absolute()

    def linklike(path: Path) -> bool:
        return path.absolute() == target or original(path)

    monkeypatch.setattr(no_call, "_is_linklike", linklike)
    if layer == "parent":
        dependencies, state = _isolated_dependencies(sdk_repository, worker=worker)
        result = no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )
        assert result["observation"]["stage"] == "python"
        assert state["file_bindings"] == []
        assert state["child_requests"] == []
    else:
        dependencies, state = _sdk_dependencies(sdk_repository)
        result = no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )
        assert result["observation"]["stage"] == "python"
        assert state["file_bindings"] == []
        assert state["imports"] == []
    assert result["status"] == no_call.SDK_BLOCKED_STATUS


@pytest.mark.parametrize("layer", ["parent", "worker"])
def test_python_lexical_dotdot_alias_is_rejected_before_binding_or_child(
    sdk_repository: Path,
    layer: str,
) -> None:
    if layer == "worker":
        dependencies, state = _sdk_dependencies(
            sdk_repository,
            interpreter_lexical_alias=True,
        )
        result = no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )
        assert state["file_bindings"] == []
        assert state["imports"] == []
    else:
        worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
        worker = no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=worker_dependencies,
        )
        dependencies, state = _isolated_dependencies(
            sdk_repository,
            worker=worker,
            interpreter_lexical_alias=True,
        )
        result = no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )
        assert state["file_bindings"] == []
        assert state["child_requests"] == []
    assert result["observation"]["stage"] == "python"
    assert result["status"] == no_call.SDK_BLOCKED_STATUS


@pytest.mark.parametrize("role", ["helper", "model", "lock"])
def test_linklike_parent_source_is_rejected_before_isolated_child(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(sdk_repository, worker=worker)
    relative = _expected_committed_source_bindings(sdk_repository)[role]["repository_relative_path"]
    target = (sdk_repository / relative).absolute()
    original = no_call._is_linklike
    monkeypatch.setattr(
        no_call,
        "_is_linklike",
        lambda path: path.absolute() == target or original(path),
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="ancestor is link-like"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )

    assert state["child_requests"] == []


def test_public_ready_parent_uses_exact_empty_environment_child_and_persists_no_raw_output(
    sdk_repository: Path,
) -> None:
    worker_dependencies, worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(sdk_repository, worker=worker)

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_READY_STATUS
    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["observation"]["stage"] == "complete"
    assert result["observation"]["environment_presence_bits"] == {
        "OPENAI_API_KEY": True,
        "PYTHONHOME": False,
        "PYTHONPATH": False,
    }
    assert state["presence_queries"] == list(no_call.SDK_ENVIRONMENT_NAMES)
    assert len(state["child_requests"]) == 1
    assert state["parent_imports"] == []
    assert state["binding_counts"] == {
        "python": 2,
        "helper": 2,
        "model": 2,
        "lock": 2,
    }
    assert worker_state["imports"] == ["httpx", "openai"]
    child = result["observation"]["isolated_child"]
    assert child["contract"] == no_call.ISOLATED_CHILD_CONTRACT
    assert child["worker_observation"] == worker
    assert child["environment_entry_forward_count"] == 0
    assert child["credential_value_forward_count"] == 0
    assert child["canonical_stdout_replay"] is True
    assert result["activity"]["environment_presence_check_count"] == 3
    assert result["activity"]["environment_value_read_count"] == 0
    assert result["activity"]["parent_sdk_dynamic_import_count"] == 0
    assert result["activity"]["parent_file_binding_count"] == 8
    assert result["activity"]["child_process_start_count"] == 1
    assert result["activity"]["child_environment_entry_forward_count"] == 0
    serialized = canonical_json(result)
    assert '"stdout":' not in serialized
    assert '"stderr":' not in serialized
    assert SECRET not in serialized
    assert no_call.validate_d139_sdk_no_call_successor_observation(result) == result


@pytest.mark.parametrize("role", ["helper", "model", "lock"])
def test_committed_source_mismatch_blocks_before_child_process(
    sdk_repository: Path,
    role: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        committed_binding_mismatch=role,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "source"
    facts = result["observation"]["source_bindings"]
    assert facts[role]["committed_binding_match_before"] is False
    assert facts[role]["file_binding_after"] is None
    assert facts[role]["binding_stable"] is None
    assert f"{role}-source-does-not-match-committed-binding" in result["blockers"]
    assert "isolated-sdk-worker-suppressed-by-committed-source-binding" in result["blockers"]
    assert state["child_requests"] == []
    assert state["binding_counts"] == {
        "python": 1,
        "helper": 1,
        "model": 1,
        "lock": 1,
    }
    assert result["activity"]["parent_file_binding_count"] == 4
    assert result["activity"]["child_process_start_count"] == 0
    assert no_call.validate_d139_sdk_no_call_successor_observation(result) == result


@pytest.mark.parametrize(
    ("role", "blocker"),
    [
        ("python", "python-executable-binding-changed-during-isolated-child"),
        ("helper", "helper-source-binding-changed-during-isolated-child"),
        ("model", "model-source-binding-changed-during-isolated-child"),
        ("lock", "lock-source-binding-changed-during-isolated-child"),
    ],
)
def test_parent_binding_drift_after_child_is_terminally_blocked(
    sdk_repository: Path,
    role: str,
    blocker: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        binding_drift=role,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "complete"
    assert blocker in result["blockers"]
    assert len(state["child_requests"]) == 1
    assert state["binding_counts"][role] == 2
    assert result["activity"]["child_process_start_count"] == 1
    assert result["activity"]["parent_network_call_count"] == 0
    assert no_call.validate_d139_sdk_no_call_successor_observation(result) == result


@pytest.mark.parametrize(
    "case",
    [
        "missing-final-lf",
        "double-final-lf",
        "noncanonical-json",
        "invalid-utf8",
        "nonempty-stderr",
        "nonzero-returncode",
        "timeout",
        "stdout-overflow",
        "stderr-overflow",
        "wrong-process-start-count",
        "unexpected-kill",
    ],
)
def test_isolated_child_execution_or_output_drift_fails_without_raw_persistence(
    sdk_repository: Path,
    case: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    canonical = no_call._compact_json_bytes(worker) + b"\n"
    overrides: dict[str, Any] = {}
    if case == "missing-final-lf":
        overrides["stdout"] = canonical[:-1]
    elif case == "double-final-lf":
        overrides["stdout"] = canonical + b"\n"
    elif case == "noncanonical-json":
        overrides["stdout"] = json.dumps(worker, indent=2).encode("utf-8") + b"\n"
    elif case == "invalid-utf8":
        overrides["stdout"] = b"\xff\n"
    elif case == "nonempty-stderr":
        overrides["stderr"] = SECRET.encode("utf-8")
    elif case == "nonzero-returncode":
        overrides["returncode"] = 1
    elif case == "timeout":
        overrides.update(timed_out=True, process_kill_count=1)
    elif case == "stdout-overflow":
        overrides.update(stdout_overflow=True, process_kill_count=1)
    elif case == "stderr-overflow":
        overrides.update(stderr_overflow=True, process_kill_count=1)
    elif case == "wrong-process-start-count":
        overrides["process_start_count"] = 0
    else:
        overrides["process_kill_count"] = 1
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        execution_overrides=overrides,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="isolated child"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )

    assert len(state["child_requests"]) == 1
    assert state["parent_imports"] == []


def test_isolated_child_cwd_removal_and_fixed_root_ancestor_drift_fail_closed(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        remove_child_cwd=True,
    )
    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="cwd drifted"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )
    assert len(state["child_requests"]) == 1

    original_linklike = no_call._is_linklike
    drift = False

    def linklike(path: Path) -> bool:
        if drift and path.resolve(strict=True) == FIXED_TEST_TEMP_ROOT.resolve(strict=True):
            return True
        return original_linklike(path)

    monkeypatch.setattr(no_call, "_is_linklike", linklike)
    with (
        pytest.raises(no_call.D139SDKNoCallSuccessorError, match="ancestor is link-like"),
        no_call._isolated_child_cwd(FIXED_TEST_TEMP_ROOT, sdk_repository),
    ):
        drift = True


@pytest.mark.parametrize("mode", ["normal", "timeout", "stdout-overflow", "drain-error", "stuck"])
def test_low_level_child_runner_uses_exact_empty_environment_and_bounded_failure_paths(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeStream:
        def __init__(self, raw: bytes, *, fail: bool = False) -> None:
            self.raw = raw
            self.fail = fail
            self.closed = False

        def read(self, _size: int) -> bytes:
            if self.fail:
                self.fail = False
                raise OSError("synthetic drain failure")
            raw, self.raw = self.raw, b""
            return raw

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            stdout = (
                b"x" * (no_call.ISOLATED_CHILD_STDOUT_LIMIT_BYTES + 1)
                if mode == "stdout-overflow"
                else b"{}\n"
            )
            self.stdout = FakeStream(stdout, fail=mode == "drain-error")
            self.stderr = FakeStream(b"")
            self.returncode: int | None = None
            self.wait_count = 0

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            if mode != "stuck":
                self.returncode = -9

        def wait(self, *, timeout: int) -> int:
            self.wait_count += 1
            if mode == "stuck" or (mode == "timeout" and self.wait_count == 1):
                raise no_call.subprocess.TimeoutExpired("synthetic", timeout)
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    process = FakeProcess()

    def popen(command: list[str], **kwargs: Any) -> FakeProcess:
        calls.append({"command": command, **kwargs})
        return process

    monkeypatch.setattr(no_call.subprocess, "Popen", popen)
    expected = _expected_committed_source_bindings(sdk_repository)
    helper = (sdk_repository / "patchloop/evals/d139_sdk_no_call_successor.py").resolve(strict=True)
    python = (sdk_repository / ".venv/d139-synthetic/python.exe").resolve(strict=True)
    with no_call._isolated_child_cwd(FIXED_TEST_TEMP_ROOT, sdk_repository) as cwd:
        request = no_call._child_request(
            root=sdk_repository.resolve(strict=True),
            helper=helper,
            python_path=python,
            temp_root=FIXED_TEST_TEMP_ROOT.resolve(strict=True),
            cwd=cwd,
            expected_committed_source_bindings=expected,
        )
        if mode in {"drain-error", "stuck"}:
            match = "pipe drain failed" if mode == "drain-error" else "bounded kill"
            with pytest.raises(no_call.D139SDKNoCallSuccessorError, match=match):
                _REAL_ISOLATED_CHILD_PROCESS(request)
        else:
            execution = _REAL_ISOLATED_CHILD_PROCESS(request)
            assert execution.process_start_count == 1
            assert execution.timed_out is (mode == "timeout")
            assert execution.stdout_overflow is (mode == "stdout-overflow")
            assert execution.stderr_overflow is False
            assert execution.process_kill_count == (0 if mode == "normal" else 1)

    assert len(calls) == 1
    call = calls[0]
    assert tuple(call["command"]) == request.command
    assert call["cwd"] == str(request.cwd)
    assert call["env"] == {}
    assert call["stdin"] is no_call.subprocess.DEVNULL
    assert call["stdout"] is no_call.subprocess.PIPE
    assert call["stderr"] is no_call.subprocess.PIPE
    assert call["shell"] is False


@pytest.mark.parametrize("role", ["interpreter", "helper"])
def test_child_argv_rejects_linklike_interpreter_or_helper_before_process_start(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    helper = (sdk_repository / "patchloop/evals/d139_sdk_no_call_successor.py").absolute()
    python = (sdk_repository / ".venv/d139-synthetic/python.exe").absolute()
    target = python if role == "interpreter" else helper
    original = no_call._is_linklike
    monkeypatch.setattr(
        no_call,
        "_is_linklike",
        lambda path: path.absolute() == target or original(path),
    )
    monkeypatch.setattr(no_call.subprocess, "Popen", _forbidden("child process start"))
    with no_call._isolated_child_cwd(FIXED_TEST_TEMP_ROOT, sdk_repository) as cwd:
        request = no_call._child_request(
            root=sdk_repository.resolve(strict=True),
            helper=helper,
            python_path=python,
            temp_root=FIXED_TEST_TEMP_ROOT.resolve(strict=True),
            cwd=cwd,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )
        with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="ancestor is link-like"):
            _REAL_ISOLATED_CHILD_PROCESS(request)


@pytest.mark.parametrize("role", ["interpreter", "helper"])
def test_child_argv_rejects_absolute_dotdot_alias_before_process_start(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    helper = (sdk_repository / "patchloop/evals/d139_sdk_no_call_successor.py").absolute()
    python = (sdk_repository / ".venv/d139-synthetic/python.exe").absolute()
    monkeypatch.setattr(no_call.subprocess, "Popen", _forbidden("child process start"))
    with no_call._isolated_child_cwd(FIXED_TEST_TEMP_ROOT, sdk_repository) as cwd:
        request = no_call._child_request(
            root=sdk_repository.resolve(strict=True),
            helper=helper,
            python_path=python,
            temp_root=FIXED_TEST_TEMP_ROOT.resolve(strict=True),
            cwd=cwd,
            expected_committed_source_bindings=_expected_committed_source_bindings(sdk_repository),
        )
        command = list(request.command)
        command[0 if role == "interpreter" else 7] = str(
            sdk_repository
            / (
                ".venv/d139-synthetic/../d139-synthetic/python.exe"
                if role == "interpreter"
                else "patchloop/evals/../evals/d139_sdk_no_call_successor.py"
            )
        )
        aliased = no_call.IsolatedChildRequest(
            command=tuple(command),
            cwd=request.cwd,
            environment_entries=request.environment_entries,
            timeout_seconds=request.timeout_seconds,
            stdout_limit_bytes=request.stdout_limit_bytes,
            stderr_limit_bytes=request.stderr_limit_bytes,
        )
        with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="lexical spelling differs"):
            _REAL_ISOLATED_CHILD_PROCESS(aliased)


def test_worker_guard_denies_values_mutations_dotenv_network_and_subprocess_with_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_os = no_call.os
    captured: dict[str, Any] = {}
    fake_os = SimpleNamespace(
        environ={},
        environb={},
        getenvb=lambda *_args: None,
        putenv=lambda *_args: None,
        unsetenv=lambda *_args: None,
        PathLike=real_os.PathLike,
        fsdecode=real_os.fsdecode,
    )
    fake_sys = SimpleNamespace(addaudithook=lambda callback: captured.setdefault("audit", callback))
    monkeypatch.setattr(no_call, "os", fake_os)
    monkeypatch.setattr(no_call, "sys", fake_sys)

    counters = no_call._install_worker_guards()
    denied = fake_os.environ
    assert len(denied) == 0
    assert not isinstance(denied, dict)
    for action in (
        lambda: denied["OPENAI_API_KEY"],
        lambda: denied.get("OPENAI_API_KEY"),
        lambda: fake_os.getenvb(b"OPENAI_API_KEY"),
        lambda: iter(denied),
        lambda: denied.__contains__("OPENAI_API_KEY"),
        denied.keys,
        denied.items,
        denied.values,
        denied.copy,
        lambda: denied | {},
        lambda: {} | denied,
    ):
        with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="value access"):
            action()
    for action in (
        lambda: denied.__setitem__("OPENAI_API_KEY", SECRET),
        lambda: denied.__delitem__("OPENAI_API_KEY"),
        lambda: denied.setdefault("OPENAI_API_KEY", SECRET),
        lambda: denied.pop("OPENAI_API_KEY"),
        denied.popitem,
        lambda: fake_os.putenv("OPENAI_API_KEY", SECRET),
        lambda: fake_os.unsetenv("OPENAI_API_KEY"),
        lambda: denied.update({"OPENAI_API_KEY": SECRET}),
        denied.clear,
        lambda: denied.__ior__({"OPENAI_API_KEY": SECRET}),
    ):
        with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="mutation"):
            action()

    audit = captured["audit"]
    for event, args, message in (
        ("open", ("C:/synthetic/.env",), "dotenv"),
        ("socket.connect", (), "network"),
        ("subprocess.Popen", (), "subprocess"),
        ("os.putenv", (), "mutation"),
    ):
        try:
            audit(event, args)
        except no_call.D139SDKNoCallSuccessorError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("D-139 guard event was not denied")
    assert counters == {
        "environment_value_read_attempt_count": 11,
        "environment_mutation_attempt_count": 11,
        "dotenv_open_attempt_count": 1,
        "network_denied_attempt_count": 1,
        "subprocess_denied_attempt_count": 1,
    }


def test_worker_sys_path_keeps_only_repository_venv_and_non_package_runtime_paths(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_root = FIXED_TEST_TEMP_ROOT.resolve(strict=True)
    outside = Path(tempfile.mkdtemp(prefix="patchloop-d139-sys-path-test-", dir=fixed_root))
    try:
        base_prefix = outside / "base"
        standard = base_prefix / "Lib"
        other_site = standard / "site-packages"
        linklike = sdk_repository / ".venv/d139-synthetic/linklike"
        other_site.mkdir(parents=True)
        linklike.mkdir()
        venv_entry = sdk_repository / ".venv/d139-synthetic"
        venv_alias = sdk_repository / ".venv/d139-synthetic/../d139-synthetic"
        fake_sys = SimpleNamespace(
            base_prefix=str(base_prefix),
            path=[
                str(sdk_repository),
                str(sdk_repository / "patchloop"),
                str(venv_entry),
                str(venv_alias),
                str(linklike),
                str(other_site),
                str(standard),
            ],
        )
        original_linklike = no_call._is_linklike
        monkeypatch.setattr(
            no_call,
            "_is_linklike",
            lambda path: path.absolute() == linklike.absolute() or original_linklike(path),
        )
        monkeypatch.setattr(no_call, "sys", fake_sys)

        no_call._remove_repository_from_sys_path(sdk_repository)

        assert fake_sys.path == [
            str(standard.resolve(strict=True)),
            str(venv_entry.resolve(strict=True)),
        ]
    finally:
        assert outside.resolve(strict=True).parent == fixed_root
        shutil.rmtree(outside)


@pytest.mark.parametrize("module_name", ["httpx", "openai"])
def test_preloaded_module_is_blocked_before_spec_distribution_import_or_probe(
    sdk_repository: Path,
    module_name: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        preloaded_module=module_name,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "module-preloaded"
    assert f"{module_name}-module-was-preloaded-before-marked-import" in result["blockers"]
    assert state["preloaded_queries"] == ["httpx", "openai"]
    assert state["module_spec_queries"] == []
    assert state["distribution_queries"] == []
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert result["activity"]["preloaded_module_membership_check_count"] == 2
    assert result["activity"]["dynamic_module_import_count"] == 0


@pytest.mark.parametrize(
    "case", ["none", "built-in", "missing", "unresolvable", "outside", "lexical-alias"]
)
def test_unsafe_module_origin_is_sanitized_and_suppresses_bind_import_and_probe(
    sdk_repository: Path,
    case: str,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository, module_spec_case=case)

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "module-origin"
    assert "openai-module-origin-is-not-repository-venv" in result["blockers"]
    assert state["module_spec_queries"] == ["httpx", "openai"]
    assert state["distribution_queries"] == []
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert result["activity"]["find_module_spec_count"] == 2
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert "ignored-shadow" not in canonical_json(result)
    assert "missing" not in canonical_json(result)


def test_linklike_module_origin_is_canonical_blocked_before_binding_version_or_import(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository)
    target = (sdk_repository / ".venv/d139-synthetic/openai/__init__.py").absolute()
    original_linklike = no_call._is_linklike
    stable_reads: list[str] = []
    original_read = no_call._stable_committed_read

    def stable_read(*args: Any, **kwargs: Any) -> bytes:
        stable_reads.append(str(kwargs.get("label")))
        return original_read(*args, **kwargs)

    monkeypatch.setattr(
        no_call,
        "_is_linklike",
        lambda path: path.absolute() == target or original_linklike(path),
    )
    monkeypatch.setattr(no_call, "_stable_committed_read", stable_read)

    result = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["observation"]["stage"] == "module-origin"
    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert state["binding_counts"] == {"python": 1}
    assert state["distribution_queries"] == []
    assert state["imports"] == []
    assert stable_reads == []


@pytest.mark.parametrize("package", ["httpx", "openai"])
def test_lock_or_distribution_version_mismatch_blocks_before_import_and_probe(
    sdk_repository: Path,
    package: str,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository, version_drift=package)

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert result["observation"]["stage"] == "module-version"
    assert f"{package}-module-version-does-not-match-lock" in result["blockers"]
    assert state["imports"] == []
    assert state["transport_handlers"] == []
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0


@pytest.mark.parametrize("module_name", ["httpx", "openai"])
def test_loaded_module_origin_mismatch_is_rejected_before_probe(
    sdk_repository: Path,
    module_name: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        loaded_module_origin_mismatch=module_name,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="loaded origin differs"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == ["httpx", "openai"]
    assert state["transport_handlers"] == []


def test_linklike_loaded_module_file_is_rejected_after_import_before_probe(
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository)
    target = (sdk_repository / ".venv/d139-synthetic/openai/__init__.py").absolute()
    original = no_call._is_linklike

    def linklike(path: Path) -> bool:
        return (state["imports"] == ["httpx", "openai"] and path.absolute() == target) or original(
            path
        )

    monkeypatch.setattr(no_call, "_is_linklike", linklike)

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="ancestor is link-like"):
        no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == ["httpx", "openai"]
    assert state["transport_handlers"] == []


@pytest.mark.parametrize("module_name", ["httpx", "openai"])
def test_loaded_module_lexical_dotdot_alias_is_rejected_before_probe(
    sdk_repository: Path,
    module_name: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        loaded_module_origin_mismatch=f"{module_name}-lexical",
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="lexical spelling differs"):
        no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == ["httpx", "openai"]
    assert state["transport_handlers"] == []


@pytest.mark.parametrize("role", ["python", "httpx", "openai"])
def test_preimport_binding_drift_is_rejected_before_first_import(
    sdk_repository: Path,
    role: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        preimport_binding_drift=role,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="drifted|drift"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == []
    assert state["transport_handlers"] == []


@pytest.mark.parametrize("module_name", ["httpx", "openai"])
def test_spec_origin_drift_after_prebind_is_rejected_before_first_import(
    sdk_repository: Path,
    module_name: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        origin_drift_before_import=module_name,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="origin drifted"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == []
    assert state["transport_handlers"] == []


@pytest.mark.parametrize("drift", ["preloaded", "origin", "binding", "version"])
def test_httpx_import_cannot_hide_openai_preimport_toctou(
    sdk_repository: Path,
    drift: str,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        sequential_openai_drift=drift,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="openai"):
        no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["imports"] == ["httpx"]
    assert state["transport_handlers"] == []
    assert state["openai_clients"] == []


@pytest.mark.parametrize(
    ("source_name", "relative", "expected_imports"),
    [
        ("lock", Path("uv.lock"), ["httpx"]),
        ("model", Path("patchloop/agent/model.py"), ["httpx", "openai"]),
    ],
)
def test_committed_lock_or_model_swap_use_restore_is_detected_on_each_read(
    sdk_repository: Path,
    source_name: str,
    relative: Path,
    expected_imports: list[str],
) -> None:
    selected = sdk_repository / relative
    original = selected.read_bytes()
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        aba_committed_source=source_name,
    )

    try:
        with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="committed.*binding"):
            no_call._run_worker_observation(
                repository=sdk_repository,
                dependencies=dependencies,
            )
    finally:
        selected.write_bytes(original)

    assert selected.read_bytes() == original
    assert state["imports"] == expected_imports
    assert state["transport_handlers"] == []


def test_caught_bootstrap_guard_attempt_is_not_representable_as_worker_evidence(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        bootstrap_attempt="network_denied_attempt_count",
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="bootstrap guard recorded"):
        no_call._run_worker_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["launch_calls"] == 0
    _assert_zero_sensitive_delegates(state)


def test_post_import_venv_containment_is_re_resolved_even_with_stable_bindings(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        venv_drift_during_probe=True,
    )

    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="provenance drifted"):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert state["venv_drifted_after_import"] is True
    assert state["imports"] == ["httpx", "openai"]
    assert len(state["transport_handlers"]) == 1
    assert state["binding_counts"] == {"python": 2, "httpx": 3, "openai": 3}


@pytest.mark.parametrize(
    ("binding_role", "blocker"),
    [
        ("python", "python-executable-binding-changed-during-probe"),
        ("openai", "openai-module-binding-changed-during-probe"),
        ("httpx", "httpx-module-binding-changed-during-probe"),
    ],
)
def test_post_probe_binding_drift_is_terminally_blocked(
    sdk_repository: Path,
    binding_role: str,
    blocker: str,
) -> None:
    dependencies, state = _sdk_dependencies(sdk_repository, binding_drift=binding_role)

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert blocker in result["blockers"]
    assert state["binding_counts"][binding_role] == (3 if binding_role == "python" else 4)
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


@pytest.mark.parametrize("openai_owns_http", [False, True])
def test_cleanup_accepts_both_http_client_ownership_paths(
    sdk_repository: Path,
    openai_owns_http: bool,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        openai_owns_http=openai_owns_http,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
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


@pytest.mark.parametrize(
    ("kwargs", "blocker"),
    [
        ({"base_url_drift": True}, "synthetic-no-call-probe-did-not-pass"),
        ({"max_retries_drift": True}, "synthetic-no-call-probe-did-not-pass"),
    ],
)
def test_probe_contract_drift_is_blocked_without_dispatch(
    sdk_repository: Path,
    kwargs: dict[str, bool],
    blocker: str,
) -> None:
    dependencies, _state = _sdk_dependencies(sdk_repository, **kwargs)

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert blocker in result["blockers"]
    assert result["activity"]["synthetic_transport_dispatch_count"] == 0
    assert result["activity"]["network_call_count"] == 0


def test_synthetic_dispatch_is_rejected_and_clients_are_still_closed(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        dispatch_during_constructor=True,
    )

    with pytest.raises(
        no_call.D139SDKNoCallSuccessorError,
        match="synthetic transport dispatch is forbidden",
    ):
        no_call.run_d139_sdk_no_call_successor_observation(
            repository=sdk_repository,
            dependencies=dependencies,
        )

    assert len(state["http_clients"]) == 1
    assert state["http_clients"][0].close_count == 1
    assert state["http_clients"][0].is_closed is True


def test_observation_validator_rejects_dispatch_and_value_read_tamper(
    sdk_repository: Path,
) -> None:
    dependencies, _state = _sdk_dependencies(sdk_repository)
    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    dispatch = copy.deepcopy(result)
    dispatch["observation"]["synthetic_probe"]["transport_dispatch_count"] = 1
    dispatch["activity"]["synthetic_transport_dispatch_count"] = 1
    with pytest.raises(no_call.D139SDKNoCallSuccessorError):
        no_call._validate_worker_observation(dispatch)

    value_read = copy.deepcopy(result)
    value_read["activity"]["environment_value_read_count"] = 1
    with pytest.raises(no_call.D139SDKNoCallSuccessorError):
        no_call._validate_worker_observation(value_read)


@pytest.mark.parametrize(
    "tamper",
    [
        "schema",
        "status",
        "stage",
        "eligibility",
        "source-count",
        "module-path",
        "check",
        "blocker",
        "activity",
        "bootstrap-activity",
        "factory-extra",
        "factory-false",
        "probe-transport",
        "probe-placeholder",
        "probe-ambient",
        "probe-base-url",
        "probe-trust-env",
        "probe-max-retries",
        "probe-dispatch",
        "probe-openai-close",
        "probe-fallback-close",
        "probe-http-closed",
        "probe-passed",
        "passed",
    ],
)
def test_worker_canonical_replay_rejects_stage_check_activity_factory_and_probe_tamper(
    sdk_repository: Path,
    tamper: str,
) -> None:
    dependencies, _state = _sdk_dependencies(sdk_repository)
    value = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )
    changed = copy.deepcopy(value)
    observation = changed["observation"]
    if tamper == "schema":
        changed["schema_version"] = "d139-tampered"
    elif tamper == "status":
        changed["status"] = no_call.SDK_BLOCKED_STATUS
    elif tamper == "stage":
        observation["stage"] = "unknown"
    elif tamper == "eligibility":
        observation["parent_eligibility_bits"]["OPENAI_API_KEY"] = False
    elif tamper == "source-count":
        observation["committed_source_bindings"]["model"]["verification_count"] += 1
    elif tamper == "module-path":
        observation["modules"]["openai"]["repository_relative_path"] = "../outside.py"
    elif tamper == "check":
        observation["checks"]["exact_launch_contract"] = False
    elif tamper == "blocker":
        changed["blockers"].append("synthetic-blocker")
    elif tamper == "activity":
        changed["activity"]["environment_value_read_count"] = 1
    elif tamper == "bootstrap-activity":
        changed["activity"]["bootstrap_network_denied_attempt_count"] = 1
    elif tamper == "factory-extra":
        observation["production_client_factory"]["arbitrary"] = True
    elif tamper == "factory-false":
        observation["production_client_factory"]["httpx_trust_env_false"] = False
    elif tamper == "probe-transport":
        observation["synthetic_probe"]["transport_kind"] = "ambient"
    elif tamper == "probe-placeholder":
        observation["synthetic_probe"]["fixed_nonsecret_placeholder_used"] = False
    elif tamper == "probe-ambient":
        observation["synthetic_probe"]["ambient_credential_value_used"] = True
    elif tamper == "probe-base-url":
        observation["synthetic_probe"]["official_base_url"] = "https://invalid.example/v1"
    elif tamper == "probe-trust-env":
        observation["synthetic_probe"]["trust_env"] = True
    elif tamper == "probe-max-retries":
        observation["synthetic_probe"]["max_retries"] = 1
    elif tamper == "probe-dispatch":
        observation["synthetic_probe"]["transport_dispatch_count"] = 1
    elif tamper == "probe-openai-close":
        observation["synthetic_probe"]["openai_client_close_call_count"] = 0
    elif tamper == "probe-fallback-close":
        observation["synthetic_probe"]["http_client_fallback_close_call_count"] = 2
    elif tamper == "probe-http-closed":
        observation["synthetic_probe"]["http_client_closed"] = False
    elif tamper == "probe-passed":
        observation["synthetic_probe"]["passed"] = False
    else:
        changed["passed"] = False

    with pytest.raises(no_call.D139SDKNoCallSuccessorError):
        no_call._validate_worker_observation(changed)


@pytest.mark.parametrize(
    "tamper",
    [
        "stage",
        "check",
        "blocker",
        "activity",
        "source-expected-sha",
        "child-contract",
        "child-process-count",
        "child-stdout-bytes",
        "child-environment-forward",
        "child-worker",
        "status",
        "passed",
    ],
)
def test_public_parent_replay_and_committed_source_cross_binding_reject_tamper(
    sdk_repository: Path,
    tamper: str,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, _state = _isolated_dependencies(sdk_repository, worker=worker)
    expected = _expected_committed_source_bindings(sdk_repository)
    value = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=expected,
    )
    changed = copy.deepcopy(value)
    observation = changed["observation"]
    if tamper == "stage":
        observation["stage"] = "presence"
    elif tamper == "check":
        observation["checks"]["exact_launch_contract"] = False
    elif tamper == "blocker":
        changed["blockers"].append("synthetic-blocker")
    elif tamper == "activity":
        changed["activity"]["environment_value_read_count"] = 1
    elif tamper == "source-expected-sha":
        fact = observation["source_bindings"]["helper"]
        fact["expected_committed_file_sha256"] = "sha256:" + "9" * 64
    elif tamper == "child-contract":
        observation["isolated_child"]["contract"]["shell"] = True
    elif tamper == "child-process-count":
        observation["isolated_child"]["process_start_count"] = 2
    elif tamper == "child-stdout-bytes":
        observation["isolated_child"]["stdout_bytes"] += 1
    elif tamper == "child-environment-forward":
        observation["isolated_child"]["environment_entry_forward_count"] = 1
    elif tamper == "child-worker":
        observation["isolated_child"]["worker_observation"]["passed"] = False
    elif tamper == "status":
        changed["status"] = no_call.SDK_BLOCKED_STATUS
    else:
        changed["passed"] = False

    with pytest.raises(no_call.D139SDKNoCallSuccessorError):
        validated = no_call.validate_d139_sdk_no_call_successor_observation(changed)
        no_call.validate_d139_sdk_no_call_successor_committed_source_bindings(
            validated,
            expected,
        )


def test_self_consistent_committed_sha_substitution_requires_external_gate_cross_binding(
    sdk_repository: Path,
) -> None:
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, _state = _isolated_dependencies(sdk_repository, worker=worker)
    expected = _expected_committed_source_bindings(sdk_repository)
    value = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
        expected_committed_source_bindings=expected,
    )
    substituted = copy.deepcopy(value)
    _substitute_helper_committed_sha(substituted, "sha256:" + "9" * 64)

    assert no_call.validate_d139_sdk_no_call_successor_observation(substituted) == substituted
    with pytest.raises(no_call.D139SDKNoCallSuccessorError, match="committed source"):
        no_call.validate_d139_sdk_no_call_successor_committed_source_bindings(
            substituted,
            expected,
        )


def test_venv_drift_between_origin_resolvers_records_exact_delegate_count(
    sdk_repository: Path,
) -> None:
    dependencies, state = _sdk_dependencies(
        sdk_repository,
        venv_drift_during_httpx_spec=True,
    )

    result = no_call.run_d139_sdk_no_call_successor_observation(
        repository=sdk_repository,
        dependencies=dependencies,
    )

    assert result["status"] == no_call.SDK_BLOCKED_STATUS
    assert state["venv_drifted"] is True
    assert state["module_spec_queries"] == ["httpx"]
    assert result["activity"]["find_module_spec_count"] == 1
    assert result["activity"]["sdk_module_file_binding_count"] == 0
    assert result["activity"]["distribution_version_observation_count"] == 0
    assert result["activity"]["dynamic_module_import_count"] == 0
    assert "venv-drifted" not in canonical_json(result)


def test_helper_import_is_side_effect_free_and_default_dependencies_stay_unused() -> None:
    source = (REPOSITORY / HELPER_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "run_d138_" not in source
    assert "d138_no_call_preflight" not in source
    assert "docker" not in source.lower()
    assert not any(
        name == blocked or name.startswith(blocked + ".")
        for name in imported
        for blocked in ("httpx", "openai", "requests", "urllib")
    )
    assert {name.rsplit(".", 1)[-1] for name in _module_level_call_names(source)}.isdisjoint(
        SOURCE_PREPARATION_FORBIDDEN_CALLS
    )
    assert 'if __name__ == "__main__"' in source


def test_exact_d138_sdk_blocked_chain_bytes_and_git_topology_are_bound() -> None:
    rebuilt = d139._validate_d138_chain(REPOSITORY)

    assert rebuilt["source_commit"] == {
        "commit": d139.D138_SOURCE_COMMIT,
        "tree": d139.D138_SOURCE_TREE,
        "parents": [d139.D138_SOURCE_PARENT],
    }
    assert rebuilt["final_transition_commit"] == {
        "commit": d139.D138_SDK_TRANSITION_COMMIT,
        "tree": d139.D138_SDK_TRANSITION_TREE,
        "parents": [d139.D138_SDK_ATTEMPT_COMMIT],
    }
    assert rebuilt["consumed"] is True
    assert rebuilt["retry_allowed"] is False
    assert rebuilt["environment_presence_check_count"] == 3
    assert rebuilt["credential_value_observation_count"] == 0
    assert rebuilt["dotenv_read_count"] == 0
    assert rebuilt["child_process_start_count"] == 0
    assert rebuilt["sdk_import_count"] == 0
    assert rebuilt["sdk_probe_count"] == 0
    assert rebuilt["transport_dispatch_count"] == 0
    assert rebuilt["network_call_count"] == 0
    assert len(d139._D138_ARTIFACTS) == 5
    assert set(rebuilt["artifacts"]) == {path.as_posix() for path, *_rest in d139._D138_ARTIFACTS}
    for path, artifact_id, body_sha, file_sha, size, blob, commit in d139._D138_ARTIFACTS:
        raw = (REPOSITORY / path).read_bytes()
        payload = json.loads(raw)
        oid, committed = d139._commit_blob(REPOSITORY, commit, path)
        assert payload.get("gate_id", payload.get("artifact_id")) == artifact_id
        assert payload["semantic_body_hash"] == body_sha
        assert sha256_bytes(raw) == file_sha
        assert len(raw) == size
        assert (oid, committed) == (blob, raw)


def test_public_paths_source_scope_cli_and_no_d138_runner_import_are_exact() -> None:
    assert d139.IMPLEMENTATION_PATHS == (HELPER_PATH, MODULE_PATH, SCRIPT_PATH, TEST_PATH)
    assert len(d139.ACTIVE_DOC_PATHS) == 10
    assert d139.FUTURE_PATHS == (
        d139.RECEIPT_PATH,
        d139.ATTEMPT_PATH,
        d139.STARTED_PATH,
        d139.TERMINAL_PATH,
    )
    source = (REPOSITORY / MODULE_PATH).read_text(encoding="utf-8")
    helper = (REPOSITORY / HELPER_PATH).read_text(encoding="utf-8")
    script = (REPOSITORY / SCRIPT_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(".d138_" in name for name in imported_modules)
    assert {name for name in imported_modules if name.startswith("patchloop")} == {
        "patchloop",
        "patchloop.errors",
        "patchloop.evals",
        "patchloop.util",
    }
    declared_loaded_names = {name for _path, name in d139.LOADED_MODULE_PATHS}
    assert declared_loaded_names == {
        "patchloop",
        "patchloop.errors",
        "patchloop.evals",
        "patchloop.evals.d139_d138_sdk_blocked_successor_offline",
        "patchloop.evals.d139_sdk_no_call_successor",
        "patchloop.util",
    }
    assert "run_d138_" not in source
    assert "run_d138_" not in helper
    for preparation_surface in (source, helper, script):
        assert {
            name.rsplit(".", 1)[-1] for name in _module_level_call_names(preparation_surface)
        }.isdisjoint(SOURCE_PREPARATION_FORBIDDEN_CALLS)
    assert "--run-sdk-preflight" in script
    assert "--create-activation-receipt" in script
    assert "--create-sdk-attempt" in script
    assert "--validate-sdk-action-started-preservation-postcommit" in script
    assert "--validate-sdk-terminal-postcommit" in script


def test_source_topology_accepts_git_lexical_order_and_binds_loaded_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved = [path.as_posix() for path in d139.IMPLEMENTATION_PATHS]
    identity = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": [d139.D138_SDK_TRANSITION_COMMIT],
    }
    monkeypatch.setattr(d139, "_commit_identity", lambda _root, _commit: identity)
    monkeypatch.setattr(
        d139,
        "_diff_rows",
        lambda _root, _commit: [{"status": "A", "path": path} for path in sorted(approved)],
    )
    monkeypatch.setattr(
        d139,
        "_commit_blob",
        lambda root, _commit, path: ("1" * 40, (root / path).read_bytes()),
    )
    monkeypatch.setattr(d139, "_assert_runtime_import_boundary", lambda _root: None)

    value = d139._source_identity(REPOSITORY, SOURCE_COMMIT)

    assert value["parents"] == [d139.D138_SDK_TRANSITION_COMMIT]
    assert value["exact_four_path_add_commit"] is True
    assert [path.as_posix() for path in d139.IMPLEMENTATION_PATHS] == approved
    assert approved != sorted(approved)
    assert {binding["path"] for binding in value["source_bindings"]} == {
        path.as_posix() for path in d139.SOURCE_BINDING_PATHS
    }

    monkeypatch.setattr(
        d139,
        "_diff_rows",
        lambda _root, _commit: [
            *({"status": "A", "path": path} for path in sorted(approved)),
            {"status": "M", "path": "unapproved.py"},
        ],
    )
    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="source commit scope"):
        d139._source_identity(REPOSITORY, SOURCE_COMMIT)


def test_loaded_module_provenance_and_fixed_git_are_currently_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d139._assert_runtime_import_boundary(REPOSITORY)
    git = d139._git_cli_observation(REPOSITORY)
    assert git["path"] == str(d139.GIT_ENGINE_PATH)
    assert git["file_sha256"] == d139.GIT_ENGINE_FILE_SHA256
    assert git["version"] == d139.GIT_VERSION
    assert git["minimal_secret_free_environment"] is True
    assert git["environment_value_observation_count"] == 0
    assert git["shell_used"] is False

    monkeypatch.setattr(d139.no_call, "__file__", str(REPOSITORY / "README.md"))
    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="loaded module provenance"):
        d139._assert_runtime_import_boundary(REPOSITORY)


@pytest.mark.parametrize("operation", ["stable-read", "loaded-module"])
def test_source_or_loaded_module_linklike_ancestor_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    target = (REPOSITORY / "patchloop").absolute()
    original = d139._is_linklike
    monkeypatch.setattr(
        d139,
        "_is_linklike",
        lambda path: path.absolute() == target or original(path),
    )

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="ancestor is link-like"):
        if operation == "stable-read":
            d139._stable_read(REPOSITORY, HELPER_PATH)
        else:
            d139._assert_runtime_import_boundary(REPOSITORY)


def test_gate_artifact_parent_linklike_reparse_fails_before_temp_or_target_publication(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    target = (root / d139.GATE_PATH.parent).absolute()
    original = d139._is_linklike
    monkeypatch.setattr(
        d139,
        "_is_linklike",
        lambda path: path.absolute() == target or original(path),
    )

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="ancestor is link-like"):
        d139.run_d139_offline_source_gate(repository=root)

    assert not (root / d139.GATE_PATH).exists()
    assert list((root / d139.GATE_PATH.parent).glob(".*.d139-*.tmp")) == []
    assert state["writes"] == []
    assert state["observer_calls"] == 0


def test_orchestrator_repository_absolute_dotdot_alias_is_rejected_before_read_or_write(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    aliased = root / "reports" / ".."

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="lexical spelling differs"):
        d139.run_d139_offline_source_gate(repository=aliased)

    assert not (root / d139.GATE_PATH).exists()
    assert state["writes"] == []
    assert state["observer_calls"] == 0


def test_offline_gate_is_idempotent_and_performs_zero_future_observation(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository

    assert not (root / d139.GATE_PATH).exists()
    assert all(not (root / path).exists() for path in d139.FUTURE_PATHS)

    first = d139.run_d139_offline_source_gate(repository=root)
    raw = (root / d139.GATE_PATH).read_bytes()
    second = d139.run_d139_offline_source_gate(repository=root)
    pending = d139.validate_d139_offline_source_gate(repository=root)

    assert first == second == pending
    assert (root / d139.GATE_PATH).read_bytes() == raw
    assert state["observer_calls"] == 0
    assert state["writes"] == [d139.GATE_PATH]
    assert all(not (root / path).exists() for path in d139.FUTURE_PATHS)
    payload = json.loads(raw)
    body = payload["semantic_body"]
    predecessor = body["d138_sdk_blocked_predecessor"]
    assert predecessor["environment_presence_check_count"] == 3
    for zero_key in (
        "credential_value_observation_count",
        "dotenv_read_count",
        "child_process_start_count",
        "sdk_import_count",
        "sdk_probe_count",
        "transport_dispatch_count",
        "network_call_count",
    ):
        assert predecessor[zero_key] == 0
    authority = body["authority"]
    assert authority["external_action_count"] == 0
    assert authority["environment_or_credential_presence_observation_count"] == 0
    assert authority["environment_or_credential_value_observation_count"] == 0
    assert authority["environment_or_credential_mutation_count"] == 0
    assert authority["dotenv_read_count"] == 0
    assert authority["sdk_import_or_transport_dispatch_count"] == 0
    assert authority["isolated_child_launch_count"] == 0
    assert authority["network_or_docker_call_count"] == 0
    assert authority["future_artifacts_created"] is False


@pytest.mark.parametrize("tamper", ["git-shell", "git-environment-count", "chronology"])
def test_rehashed_gate_rejects_git_provenance_or_predecessor_chronology_tamper(
    repository: tuple[Path, dict[str, Any]],
    tamper: str,
) -> None:
    root, _state = repository
    d139.run_d139_offline_source_gate(repository=root)
    payload = json.loads((root / d139.GATE_PATH).read_bytes())
    body = payload["semantic_body"]
    if tamper == "git-shell":
        body["git_cli_observation"]["shell_used"] = True
    elif tamper == "git-environment-count":
        body["git_cli_observation"]["environment_value_observation_count"] = 1
    else:
        body["recorded_at"] = "2026-08-10T01:58:00Z"
    rebuilt = d139._envelope(d139.GATE_SCHEMA, "d139", body, gate=True)
    (root / d139.GATE_PATH).write_bytes(d139._pretty_bytes(rebuilt))

    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        d139.validate_d139_offline_source_gate(repository=root)


def test_gate_evidence_commit_scope_and_activation_template_are_exact_and_read_only(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)
    before = {path: (root / path).read_bytes() for path in (d139.GATE_PATH,)}
    write_count = len(state["writes"])

    template = d139.render_d139_external_activation_template(repository=root)

    assert "Gate evidence commit tuple: " in template
    assert f"Source commit: {SOURCE_COMMIT}" in template
    assert d139.D138_SDK_TRANSITION_COMMIT in template
    assert "python.exe' -E -s -B" in template
    assert "--run-sdk-preflight" in template
    assert (
        f"Parent launcher source contract: {canonical_json(no_call.LAUNCHER_SOURCE_CONTRACT)}"
        in template
    )
    assert f"Isolated child contract: {canonical_json(no_call.ISOLATED_CHILD_CONTRACT)}" in template
    assert "bounded empty-environment child" in template
    assert "This rendered template is not approval" in template
    assert len(state["writes"]) == write_count
    assert (root / d139.GATE_PATH).read_bytes() == before[d139.GATE_PATH]
    assert all(not (root / path).exists() for path in d139.FUTURE_PATHS)

    post = d139.validate_d139_offline_source_gate(
        repository=root,
        mode="post-evidence-commit",
    )
    commit = post["evidence_commit"]
    assert commit["parents"] == [SOURCE_COMMIT]
    assert commit["exact_gate_add_and_active_docs_modify_commit"] is True
    assert sorted(
        (row["status"], row["path"]) for row in d139._diff_rows(root, GATE_COMMIT)
    ) == sorted(
        [
            ("A", d139.GATE_PATH.as_posix()),
            *(("M", path.as_posix()) for path in d139.ACTIVE_DOC_PATHS),
        ]
    )


def test_receipt_and_attempt_are_new_only_idempotent_and_require_commits(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)

    receipt = d139.create_d139_activation_receipt(repository=root)
    receipt_again = d139.create_d139_activation_receipt(repository=root)
    assert receipt_again == receipt
    assert receipt["commit_required_before_attempt"] is True
    assert state["observer_calls"] == 0
    state["head"] = RECEIPT_COMMIT
    committed_receipt = d139.validate_d139_activation_receipt(
        repository=root,
        mode="post-commit",
    )
    assert committed_receipt["receipt_commit"]["parents"] == [GATE_COMMIT]
    assert committed_receipt["receipt_commit"]["single_artifact_add_commit"] is True

    attempt = d139.create_d139_sdk_attempt(repository=root)
    attempt_again = d139.create_d139_sdk_attempt(repository=root)
    assert attempt_again == attempt
    assert attempt["commit_required_before_observation"] is True
    assert state["observer_calls"] == 0
    state["head"] = ATTEMPT_COMMIT
    committed_attempt = d139.validate_d139_sdk_attempt(repository=root, mode="post-commit")
    assert committed_attempt["attempt_commit"]["parents"] == [RECEIPT_COMMIT]
    assert committed_attempt["attempt_commit"]["single_artifact_add_commit"] is True


def test_receipt_source_mapping_cannot_diverge_from_its_validated_gate(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_receipt(root, state)
    payload = json.loads((root / d139.RECEIPT_PATH).read_bytes())
    rows = payload["semantic_body"]["source_identity"]["source_bindings"]
    helper = next(row for row in rows if row["path"] == HELPER_PATH.as_posix())
    helper["file_sha256"] = "sha256:" + "9" * 64
    rebuilt = d139._envelope(
        d139.RECEIPT_SCHEMA,
        "d139approval",
        payload["semantic_body"],
    )
    (root / d139.RECEIPT_PATH).write_bytes(d139._pretty_bytes(rebuilt))

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="receipt rebuild"):
        d139.validate_d139_activation_receipt(repository=root, mode="post-commit")


@pytest.mark.parametrize("observation_name", ["ready", "blocked"])
def test_ready_or_blocked_transition_is_marker_first_one_use_and_exactly_committed(
    repository: tuple[Path, dict[str, Any]],
    observation_name: str,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    state["observation"] = state[observation_name]

    pending = d139.run_d139_sdk_no_call_successor(repository=root)

    assert state["observer_calls"] == 1
    assert state["events"].index(f"write:{d139.STARTED_PATH.name}") < state["events"].index(
        "observe-membership"
    )
    assert state["events"].index("observe-membership") < state["events"].index(
        f"write:{d139.TERMINAL_PATH.name}"
    )
    assert pending["phase_consumed"] is True
    assert pending["retry_allowed"] is False
    assert pending["passed"] is (observation_name == "ready")
    assert pending["provider_evaluator_agent_call_count"] == 0
    assert pending["cost_reserved_or_spent_usd"] == "0"
    assert (root / d139.STARTED_PATH).is_file()
    assert (root / d139.TERMINAL_PATH).is_file()
    terminal_body = json.loads((root / d139.TERMINAL_PATH).read_bytes())["semantic_body"]
    assert terminal_body["next_gate"]["status"] == (
        "D140_READY_SDK_NO_CALL_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
        if observation_name == "ready"
        else "D140_SDK_BLOCKED_OFFLINE_SUCCESSOR_APPROVAL_REQUIRED"
    )
    assert terminal_body["next_gate"]["fresh_separate_approval_required"] is True
    assert (
        terminal_body["next_gate"][
            "current_activation_authorizes_execution_hash_candidate_cost_or_ac"
        ]
        is False
    )

    state["head"] = TRANSITION_COMMIT
    post = d139.validate_d139_sdk_terminal(
        repository=root,
        mode="post-transition-commit",
    )
    assert post["transition_commit"]["parents"] == [ATTEMPT_COMMIT]
    assert post["transition_commit"]["exact_action_started_and_terminal_add_commit"] is True
    replay = d139.run_d139_sdk_no_call_successor(repository=root)
    assert replay == post
    assert state["observer_calls"] == 1


def test_rehashed_terminal_cannot_substitute_gate_committed_source_hashes(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    d139.run_d139_sdk_no_call_successor(repository=root)
    payload = json.loads((root / d139.TERMINAL_PATH).read_bytes())
    _substitute_helper_committed_sha(
        payload["semantic_body"]["observation"],
        "sha256:" + "9" * 64,
    )
    rebuilt = d139._envelope(
        d139.TERMINAL_SCHEMA,
        "d139sdk",
        payload["semantic_body"],
    )
    (root / d139.TERMINAL_PATH).write_bytes(d139._pretty_bytes(rebuilt))

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="committed source"):
        d139.validate_d139_sdk_terminal(repository=root)


@pytest.mark.parametrize("role", ["helper", "model", "lock"])
def test_orchestrator_commits_source_blocked_terminal_without_starting_child(
    repository: tuple[Path, dict[str, Any]],
    sdk_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    worker_dependencies, _worker_state = _sdk_dependencies(sdk_repository)
    worker = no_call._run_worker_observation(
        repository=sdk_repository,
        dependencies=worker_dependencies,
    )
    dependencies, parent_state = _isolated_dependencies(
        sdk_repository,
        worker=worker,
        committed_binding_mismatch=role,
    )

    def observe(
        *,
        repository: str | Path | None = None,
        expected_committed_source_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        del repository
        state["observer_calls"] += 1
        state["events"].append("observe-membership")
        assert (root / d139.STARTED_PATH).is_file()
        assert expected_committed_source_bindings == state["expected_source_bindings"]
        return _REAL_PUBLIC_RUNNER(
            repository=sdk_repository,
            dependencies=dependencies,
            expected_committed_source_bindings=expected_committed_source_bindings,
        )

    monkeypatch.setattr(no_call, "run_d139_sdk_no_call_successor_observation", observe)

    terminal = d139.run_d139_sdk_no_call_successor(repository=root)

    assert terminal["passed"] is False
    assert terminal["phase_consumed"] is True
    assert terminal["retry_allowed"] is False
    assert parent_state["child_requests"] == []
    assert parent_state["binding_counts"] == {
        "python": 1,
        "helper": 1,
        "model": 1,
        "lock": 1,
    }
    payload = json.loads((root / d139.TERMINAL_PATH).read_bytes())
    observation = payload["semantic_body"]["observation"]
    assert observation["observation"]["stage"] == "source"
    assert observation["activity"]["child_process_start_count"] == 0


def test_post_marker_failure_is_preservable_consumed_and_never_retried(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    state["observer_error"] = RuntimeError("synthetic post-marker failure")

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="phase is consumed"):
        d139.run_d139_sdk_no_call_successor(repository=root)

    assert state["observer_calls"] == 1
    assert (root / d139.STARTED_PATH).is_file()
    assert not (root / d139.TERMINAL_PATH).exists()
    pending = d139.validate_d139_sdk_action_started(repository=root)
    assert pending["phase_consumed"] is True
    assert pending["retry_allowed"] is False
    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="retry is forbidden"):
        d139.run_d139_sdk_no_call_successor(repository=root)
    assert state["observer_calls"] == 1

    state["head"] = MARKER_COMMIT
    preserved = d139.validate_d139_sdk_action_started(
        repository=root,
        mode="post-preservation-commit",
    )
    assert preserved["marker_preservation_commit"]["parents"] == [ATTEMPT_COMMIT]
    assert preserved["marker_preservation_commit"]["single_artifact_add_commit"] is True


def test_caught_bootstrap_audit_attempt_consumes_marker_and_cannot_publish_terminal(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    state["observer_error"] = no_call.D139SDKNoCallSuccessorError(
        "D-139 bootstrap guard recorded an attempted socket operation"
    )

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="phase is consumed"):
        d139.run_d139_sdk_no_call_successor(repository=root)

    assert state["observer_calls"] == 1
    assert (root / d139.STARTED_PATH).is_file()
    assert not (root / d139.TERMINAL_PATH).exists()
    assert d139.validate_d139_sdk_action_started(repository=root)["retry_allowed"] is False


@pytest.mark.parametrize("mutation", ["attempt", "started", "checkout"])
def test_post_helper_toctou_publishes_no_terminal_and_never_retries(
    repository: tuple[Path, dict[str, Any]],
    mutation: str,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    state["observer_mutation"] = mutation

    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        d139.run_d139_sdk_no_call_successor(repository=root)

    assert state["observer_calls"] == 1
    assert not (root / d139.TERMINAL_PATH).exists()
    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        d139.run_d139_sdk_no_call_successor(repository=root)
    assert state["observer_calls"] == 1


def test_terminal_prepublication_checkout_drift_writes_no_terminal(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    original_write = d139._write_new
    callback_calls = 0

    def drifting_write(
        selected_root: Path,
        path: Path,
        raw: bytes,
        *,
        prepublish: d139.PrepublishCheck | None = None,
    ) -> None:
        nonlocal callback_calls

        def wrapped(temporary: Path, temporary_raw: bytes) -> None:
            nonlocal callback_calls
            callback_calls += 1
            assert prepublish is not None
            state["status_override"] = [
                f"?? {d139.STARTED_PATH.as_posix()}",
                f"?? {temporary.as_posix()}",
                "?? unrelated-terminal-prepublication-drift",
            ]
            prepublish(temporary, temporary_raw)

        original_write(
            selected_root,
            path,
            raw,
            prepublish=wrapped if path == d139.TERMINAL_PATH else prepublish,
        )

    monkeypatch.setattr(d139, "_write_new", drifting_write)

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="prepublication status"):
        d139.run_d139_sdk_no_call_successor(repository=root)

    assert callback_calls == 1
    assert state["observer_calls"] == 1
    assert (root / d139.STARTED_PATH).is_file()
    assert not (root / d139.TERMINAL_PATH).exists()


def test_orphan_terminal_and_started_collision_fail_before_observation(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    (root / d139.TERMINAL_PATH).write_bytes(b"orphan-terminal")

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="terminal is orphaned"):
        d139.run_d139_sdk_no_call_successor(repository=root)

    assert state["observer_calls"] == 0


@pytest.mark.parametrize("phase", ["gate", "receipt", "attempt", "marker"])
def test_prepublication_head_or_status_drift_leaves_new_artifact_absent(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    root, state = repository
    if phase == "gate":
        calls = 0

        def drifting_head(_root: Path) -> str:
            nonlocal calls
            calls += 1
            return SOURCE_COMMIT if calls == 1 else "9" * 40

        monkeypatch.setattr(d139, "_head", drifting_head)

        def action() -> object:
            return d139.run_d139_offline_source_gate(repository=root)

        path = d139.GATE_PATH
    elif phase == "receipt":
        _seal_gate(root, state)
        path = d139.RECEIPT_PATH

        def action() -> object:
            return d139.create_d139_activation_receipt(repository=root)

    elif phase == "attempt":
        _seal_receipt(root, state)
        path = d139.ATTEMPT_PATH

        def action() -> object:
            return d139.create_d139_sdk_attempt(repository=root)

    else:
        _seal_attempt(root, state)
        path = d139.STARTED_PATH

        def action() -> object:
            return d139.run_d139_sdk_no_call_successor(repository=root)

    if phase != "gate":
        calls = 0
        original_status = d139._status_lines

        def drifting_status(selected_root: Path) -> list[str]:
            nonlocal calls
            calls += 1
            value = original_status(selected_root)
            return value if calls == 1 else [*value, "?? unrelated-prepublication-drift"]

        monkeypatch.setattr(d139, "_status_lines", drifting_status)

    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        action()

    assert not (root / path).exists()
    assert state["observer_calls"] == 0


@pytest.mark.parametrize("binding", ["predecessor", "source"])
def test_gate_prepublication_binding_drift_leaves_gate_absent(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    binding: str,
) -> None:
    root, state = repository
    selected_name = "_validate_d138_chain" if binding == "predecessor" else "_source_identity"
    original = getattr(d139, selected_name)
    calls = 0

    def drifting(*args: object, **kwargs: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        value = copy.deepcopy(original(*args, **kwargs))
        if calls > 1:
            value["network_call_count" if binding == "predecessor" else "tree"] = (
                1 if binding == "predecessor" else "9" * 40
            )
        return value

    monkeypatch.setattr(d139, selected_name, drifting)

    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        d139.run_d139_offline_source_gate(repository=root)

    assert calls >= 2
    assert not (root / d139.GATE_PATH).exists()
    assert state["observer_calls"] == 0


@pytest.mark.parametrize("phase", ["receipt", "attempt", "marker"])
def test_artifact_prepublication_binding_drift_leaves_new_artifact_absent(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    root, state = repository
    if phase == "receipt":
        _seal_gate(root, state)
        selected_name = "_gate_for_activation"
        path = d139.RECEIPT_PATH

        def action() -> object:
            return d139.create_d139_activation_receipt(repository=root)

    elif phase == "attempt":
        _seal_receipt(root, state)
        selected_name = "_committed_receipt"
        path = d139.ATTEMPT_PATH

        def action() -> object:
            return d139.create_d139_sdk_attempt(repository=root)

    else:
        _seal_attempt(root, state)
        selected_name = "_single_artifact_commit"
        path = d139.STARTED_PATH

        def action() -> object:
            return d139.run_d139_sdk_no_call_successor(repository=root)

    original = getattr(d139, selected_name)
    calls = 0

    def drifting(*args: object, **kwargs: object) -> Any:
        nonlocal calls
        calls += 1
        value = copy.deepcopy(original(*args, **kwargs))
        if calls > 1:
            if selected_name == "_gate_for_activation":
                value[0]["file_bytes"] += 1
            elif selected_name == "_committed_receipt":
                value[2]["tree"] = "9" * 40
            else:
                value["tree"] = "9" * 40
        return value

    monkeypatch.setattr(d139, selected_name, drifting)

    with pytest.raises(d139.D139SDKBlockedSuccessorError):
        action()

    assert calls >= 2
    assert not (root / path).exists()
    assert state["observer_calls"] == 0


@pytest.mark.parametrize("future_path", list(d139.FUTURE_PATHS))
def test_offline_gate_rejects_any_future_artifact_collision(
    repository: tuple[Path, dict[str, Any]],
    future_path: Path,
) -> None:
    root, state = repository
    (root / future_path).write_bytes(b"synthetic collision")

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="path collision"):
        d139.run_d139_offline_source_gate(repository=root)

    assert state["observer_calls"] == 0
    assert not (root / d139.GATE_PATH).exists()


def test_terminal_semantic_tamper_is_rejected_even_after_envelope_rehash(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    d139.run_d139_sdk_no_call_successor(repository=root)
    payload = json.loads((root / d139.TERMINAL_PATH).read_bytes())
    observation = payload["semantic_body"]["observation"]
    observation["activity"]["environment_value_read_count"] = 1
    tampered = d139._envelope(
        d139.TERMINAL_SCHEMA,
        "d139sdk",
        payload["semantic_body"],
    )
    (root / d139.TERMINAL_PATH).write_bytes(d139._pretty_bytes(tampered))

    with pytest.raises(d139.D139SDKBlockedSuccessorError, match="observation validation"):
        d139.validate_d139_sdk_terminal(repository=root)
