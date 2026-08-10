"""D-141 fresh SDK no-call successor observation.

Importing this module performs no environment, credential, SDK, endpoint, or
network observation.  The future runner is deliberately dependency-injected so
offline qualification can exercise every branch without importing an SDK.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

MILESTONE = "D-141"
SDK_PHASE = "sdk"
SDK_OBSERVATION_SCHEMA = "d141-d140-sdk-no-call-successor-observation-v1"
SDK_WORKER_OBSERVATION_SCHEMA = "d141-isolated-sdk-no-call-worker-observation-v1"
SDK_READY_STATUS = "D141_SDK_NO_CALL_SUCCESSOR_READY_OFFLINE_SUCCESSOR_REQUIRED"
SDK_BLOCKED_STATUS = "D141_SDK_NO_CALL_SUCCESSOR_OBSERVED_BLOCKED"

OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"
SDK_ENVIRONMENT_NAMES = ("OPENAI_API_KEY", "PYTHONHOME", "PYTHONPATH")
D141_FIXED_TEMP_ROOT = Path(r"C:\Users\geonj\AppData\Local\Temp")
EXACT_LAUNCH_CONTRACT = {
    "ignore_python_environment": True,
    "user_site_disabled": True,
    "bytecode_writes_disabled": True,
    "isolated_mode": False,
    "safe_path_mode": False,
}
LAUNCHER_SOURCE_CONTRACT = {
    "required_python_flags": ["-E", "-s", "-B"],
    "ambient_environment_policy": "inherit-unchanged-required-not-runtime-observed",
    "environment_override_count": 0,
    "exact_cli_action": "--run-sdk-preflight",
}
ISOLATED_CHILD_WORKER_ACTION = "_d141_isolated_sdk_worker"
ISOLATED_CHILD_ELIGIBILITY_TOKEN = "d141-presence-ready-no-value"
ISOLATED_CHILD_TIMEOUT_SECONDS = 20
ISOLATED_CHILD_STDOUT_LIMIT_BYTES = 65_536
ISOLATED_CHILD_STDERR_LIMIT_BYTES = 16_384
ISOLATED_CHILD_CWD_PREFIX = "patchloop-d141-sdk-child-"
ISOLATED_CHILD_BOOTSTRAP = r"""
import sys

if not sys.path or sys.path[0] != "":
    raise SystemExit(71)
del sys.path[0]
repo = sys.argv[1]
repo_key = repo.casefold().replace("/", "\\").rstrip("\\")
venv_key = repo_key + "\\.venv"
base_key = sys.base_prefix.casefold().replace("/", "\\").rstrip("\\")
base_candidates = []
venv_candidates = []
venv_entry_retained = False
for entry in sys.path:
    if not isinstance(entry, str) or not entry:
        continue
    key = entry.casefold().replace("/", "\\").rstrip("\\")
    if key == venv_key or key.startswith(venv_key + "\\"):
        venv_candidates.append(entry)
        venv_entry_retained = True
        continue
    if key == base_key or key.startswith(base_key + "\\"):
        if "\\site-packages" in key or "\\dist-packages" in key:
            continue
        base_candidates.append(entry)
if not venv_entry_retained:
    raise SystemExit(78)
sys.path[:] = base_candidates
import os

repo = os.path.abspath(repo)
venv = os.path.abspath(os.path.join(repo, ".venv"))
base = os.path.abspath(sys.base_prefix)

def _d141_bootstrap_nonlink_chain(path):
    current = path
    while True:
        try:
            metadata = os.stat(current, follow_symlinks=False)
        except (OSError, TypeError, ValueError):
            return False
        if (metadata.st_mode & 0o170000) == 0o120000 or bool(
            getattr(metadata, "st_file_attributes", 0) & 0x400
        ):
            return False
        parent = os.path.dirname(current)
        if parent == current:
            return True
        current = parent

validated_base = []
validated_venv = []
venv_entry_retained = False
for entry in [*base_candidates, *venv_candidates]:
    if (
        not isinstance(entry, str)
        or not entry
        or not os.path.isabs(entry)
        or entry != os.path.abspath(entry)
        or entry != os.path.realpath(entry)
        or not _d141_bootstrap_nonlink_chain(entry)
    ):
        continue
    if entry == venv or entry.startswith(venv + os.sep):
        validated_venv.append(entry)
        venv_entry_retained = True
        continue
    if entry == repo or entry.startswith(repo + os.sep):
        continue
    if not (entry == base or entry.startswith(base + os.sep)):
        continue
    lowered = entry.casefold().replace("\\", "/")
    if "/site-packages" in lowered or "/dist-packages" in lowered:
        continue
    validated_base.append(entry)
if not venv_entry_retained:
    raise SystemExit(81)
sys.path[:] = validated_base
import hashlib
import stat
sys.path[:] = [*validated_base, *validated_venv]

if len(os.environ) != 0:
    raise SystemExit(72)

_d141_bootstrap_counters = {
    "environment_value_read_attempt_count": 0,
    "environment_mutation_attempt_count": 0,
    "dotenv_open_attempt_count": 0,
    "network_denied_attempt_count": 0,
    "subprocess_denied_attempt_count": 0,
}

class _D141BootstrapEnvironment:
    def _deny_read(self, *_args, **_kwargs):
        _d141_bootstrap_counters["environment_value_read_attempt_count"] += 1
        raise RuntimeError("D-141 bootstrap environment access denied")
    def _deny_mutation(self, *_args, **_kwargs):
        _d141_bootstrap_counters["environment_mutation_attempt_count"] += 1
        raise RuntimeError("D-141 bootstrap environment mutation denied")
    __getitem__ = _deny_read
    __setitem__ = _deny_mutation
    __delitem__ = _deny_mutation
    get = _deny_read
    setdefault = _deny_mutation
    pop = _deny_mutation
    popitem = _deny_mutation
    update = _deny_mutation
    clear = _deny_mutation
    __ior__ = _deny_mutation
    keys = _deny_read
    items = _deny_read
    values = _deny_read
    copy = _deny_read
    __or__ = _deny_read
    __ror__ = _deny_read
    def __contains__(self, _key):
        return self._deny_read()
    def __iter__(self):
        return self._deny_read()
    def __len__(self):
        return 0

def _d141_bootstrap_audit(event, args):
    if event == "open" and args:
        candidate = args[0]
        if isinstance(candidate, (str, bytes, os.PathLike)):
            parts = os.fsdecode(candidate).replace("\\", "/").split("/")
            if any(
                part.casefold() == ".env" or part.casefold().startswith(".env.")
                for part in parts
            ):
                _d141_bootstrap_counters["dotenv_open_attempt_count"] += 1
                raise RuntimeError("D-141 bootstrap dotenv open denied")
    if event.startswith("socket.") or event in {"http.client.connect", "urllib.Request"}:
        _d141_bootstrap_counters["network_denied_attempt_count"] += 1
        raise RuntimeError("D-141 bootstrap network denied")
    if event in {"os.putenv", "os.unsetenv"}:
        _d141_bootstrap_counters["environment_mutation_attempt_count"] += 1
        raise RuntimeError("D-141 bootstrap environment mutation denied")
    if event in {"subprocess.Popen", "os.system"} or event.startswith(("os.spawn", "os.exec")):
        _d141_bootstrap_counters["subprocess_denied_attempt_count"] += 1
        raise RuntimeError("D-141 bootstrap mutation denied")

sys.addaudithook(_d141_bootstrap_audit)
_d141_denied = _D141BootstrapEnvironment()
os.environ = _d141_denied
os.getenv = _d141_denied._deny_read
if hasattr(os, "environb"):
    os.environb = _d141_denied
if hasattr(os, "getenvb"):
    os.getenvb = _d141_denied._deny_read
os.putenv = _d141_denied._deny_mutation
os.unsetenv = _d141_denied._deny_mutation

if len(sys.argv) != 11:
    raise SystemExit(79)
(
    repo,
    helper,
    temp_root,
    token,
    helper_sha,
    helper_bytes,
    model_sha,
    model_bytes,
    lock_sha,
    lock_bytes,
) = sys.argv[1:11]
if not all(
    os.path.isabs(item) and item == os.path.abspath(item)
    for item in (repo, helper, temp_root)
):
    raise SystemExit(73)
if (
    os.path.realpath(repo) != os.path.abspath(repo)
    or os.path.realpath(helper) != os.path.abspath(helper)
    or os.path.realpath(helper)
    != os.path.realpath(os.path.join(repo, "patchloop", "evals", "d141_sdk_no_call_successor.py"))
):
    raise SystemExit(74)
for expected_sha, expected_bytes in (
    (helper_sha, helper_bytes),
    (model_sha, model_bytes),
    (lock_sha, lock_bytes),
):
    if (
        len(expected_sha) != 71
        or not expected_sha.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in expected_sha[7:])
        or not expected_bytes.isdigit()
        or int(expected_bytes) <= 0
    ):
        raise SystemExit(80)
before = os.stat(helper, follow_symlinks=False)
if stat.S_ISLNK(before.st_mode) or bool(getattr(before, "st_file_attributes", 0) & 0x400):
    raise SystemExit(75)
with open(helper, "rb") as stream:
    source = stream.read()
after = os.stat(helper, follow_symlinks=False)
if (
    stat.S_ISLNK(after.st_mode)
    or bool(getattr(after, "st_file_attributes", 0) & 0x400)
    or (before.st_size, before.st_mtime_ns, before.st_ino)
    != (after.st_size, after.st_mtime_ns, after.st_ino)
):
    raise SystemExit(76)
if (
    len(source) != int(helper_bytes)
    or "sha256:" + hashlib.sha256(source).hexdigest() != helper_sha
):
    raise SystemExit(77)
sys.argv = [helper, "_d141_isolated_sdk_worker", repo, temp_root, token]
namespace = {
    "__name__": "__main__",
    "__file__": helper,
    "__builtins__": __builtins__,
    "__d141_bootstrap_counters__": _d141_bootstrap_counters,
    "__d141_bootstrap_helper_binding_verified__": True,
    "__d141_bootstrap_audit_hook_installed__": True,
    "__d141_bootstrap_expected_source_bindings__": {
        "helper": {
            "repository_relative_path": "patchloop/evals/d141_sdk_no_call_successor.py",
            "file_bytes": int(helper_bytes),
            "file_sha256": helper_sha,
            "linklike": False,
        },
        "model": {
            "repository_relative_path": "patchloop/agent/model.py",
            "file_bytes": int(model_bytes),
            "file_sha256": model_sha,
            "linklike": False,
        },
        "lock": {
            "repository_relative_path": "uv.lock",
            "file_bytes": int(lock_bytes),
            "file_sha256": lock_sha,
            "linklike": False,
        },
    },
}
exec(compile(source, helper, "exec"), namespace, namespace)
""".strip()
ISOLATED_CHILD_CONTRACT = {
    "worker_action": ISOLATED_CHILD_WORKER_ACTION,
    "eligibility_token_kind": "fixed-boolean-no-value",
    "required_python_flags": ["-E", "-s", "-B"],
    "absolute_repository_venv_interpreter": True,
    "shell": False,
    "stdin": "DEVNULL",
    "child_process_start_limit": 1,
    "child_environment_entries": [],
    "child_environment_override_count": 1,
    "child_environment_entry_count": 0,
    "ambient_environment_entry_forward_count": 0,
    "credential_value_forward_count": 0,
    "startup_confidentiality_boundary": "fixed-empty-secret-free-environment",
    "worker_entry_environment_value_access": "deny",
    "worker_entry_dotenv_open": "audit-deny",
    "worker_entry_socket_network": "audit-deny",
    "worker_entry_subprocess": "audit-deny",
    "bootstrap_sys_path_policy": "exact-nonlink-base-prefix-before-repository-venv-only",
    "worker_sys_path_policy": "exact-nonlink-base-prefix-before-repository-venv-only",
    "repository_source_sys_path_entry_forward_count": 0,
    "outside_venv_site_packages_entry_forward_count": 0,
    "cwd_policy": "fresh-nonlink-fixed-root-outside-repository",
    "fixed_temp_root": str(D141_FIXED_TEMP_ROOT),
    "timeout_seconds": ISOLATED_CHILD_TIMEOUT_SECONDS,
    "stdout_limit_bytes": ISOLATED_CHILD_STDOUT_LIMIT_BYTES,
    "stderr_limit_bytes": ISOLATED_CHILD_STDERR_LIMIT_BYTES,
    "stdout_contract": "one-canonical-json-line",
    "stderr_contract": "empty",
    "raw_captured_output_persistence_authorized": False,
    "validated_parsed_worker_observation_persistence_authorized": True,
    "bootstrap_sha256": (
        "sha256:" + hashlib.sha256(ISOLATED_CHILD_BOOTSTRAP.encode("utf-8")).hexdigest()
    ),
    "audit_hook_coverage_boundary": "bootstrap-after-cpython-and-site-startup",
    "pre_bootstrap_startup_network_coverage": "not-observed-not-claimed",
    "argv_layout": [
        "absolute-repository-venv-python",
        "-E",
        "-s",
        "-B",
        "-c",
        "fixed-bootstrap",
        "absolute-repository-root",
        "absolute-helper-source",
        "absolute-fixed-temp-root",
        "fixed-eligibility-token",
        "expected-helper-sha256",
        "expected-helper-file-bytes",
        "expected-model-sha256",
        "expected-model-file-bytes",
        "expected-lock-sha256",
        "expected-lock-file-bytes",
    ],
}

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_GUARD_COUNTER_KEYS = (
    "environment_value_read_attempt_count",
    "environment_mutation_attempt_count",
    "dotenv_open_attempt_count",
    "network_denied_attempt_count",
    "subprocess_denied_attempt_count",
)
_ROOT_KEYS = (
    "schema_version",
    "phase",
    "status",
    "observer_contract",
    "observation",
    "blockers",
    "activity",
    "passed",
)
_ACTIVITY_KEYS = (
    "launch_contract_check_count",
    "eligibility_token_validation_count",
    "bootstrap_audit_hook_installed_count",
    "bootstrap_environment_value_read_attempt_count",
    "bootstrap_environment_mutation_attempt_count",
    "bootstrap_dotenv_open_attempt_count",
    "bootstrap_network_denied_attempt_count",
    "bootstrap_subprocess_denied_attempt_count",
    "worker_audit_hook_installed_count",
    "committed_helper_bootstrap_verification_count",
    "committed_model_binding_verification_count",
    "committed_lock_binding_verification_count",
    "environment_presence_check_count",
    "environment_value_read_count",
    "environment_value_read_attempt_count",
    "environment_mutation_attempt_count",
    "startup_environment_entry_count",
    "dotenv_read_count",
    "dotenv_open_attempt_count",
    "python_executable_file_binding_count",
    "preloaded_module_membership_check_count",
    "find_module_spec_count",
    "sdk_module_file_binding_count",
    "distribution_version_observation_count",
    "locked_version_source_read_count",
    "checked_in_factory_source_read_count",
    "dynamic_module_import_count",
    "synthetic_transport_dispatch_count",
    "network_call_count",
    "network_denied_attempt_count",
    "subprocess_denied_attempt_count",
    "provider_evaluator_or_agent_call_count",
    "openai_client_close_call_count",
    "http_client_fallback_close_call_count",
    "http_client_closed",
)
_OBSERVATION_KEYS = (
    "stage",
    "launch_contract",
    "parent_eligibility_bits",
    "committed_source_bindings",
    "python",
    "modules",
    "production_client_factory",
    "synthetic_probe",
    "checks",
)
_PYTHON_KEYS = (
    "version",
    "repository_relative_path",
    "under_repository_venv",
    "file_binding_before",
    "file_binding_preimport_recheck",
    "file_binding_after",
    "preimport_binding_stable",
    "binding_stable",
    "under_repository_venv_after_probe",
)
_MODULE_KEYS = (
    "distribution_name",
    "distribution_version",
    "module_version",
    "locked_version",
    "repository_relative_path",
    "under_repository_venv",
    "file_binding_before",
    "file_binding_preimport_recheck",
    "file_binding_immediate_import_recheck",
    "file_binding_after",
    "preimport_binding_stable",
    "immediate_import_binding_stable",
    "binding_stable",
    "distribution_version_preimport_recheck",
    "locked_version_preimport_recheck",
    "preimport_versions_stable",
    "distribution_version_immediate_import_recheck",
    "locked_version_immediate_import_recheck",
    "immediate_import_versions_stable",
    "distribution_version_after",
    "locked_version_after",
    "versions_stable_after_probe",
    "origin_stable_before_import",
    "origin_stable_immediately_before_import",
    "origin_stable_after_probe",
    "versions_match",
)
_FACTORY_KEYS = (
    "checked_in_official_base_url",
    "official_base_url_exact",
    "factory_found",
    "single_httpx_client_constructor",
    "httpx_client_assigned_to_http_client",
    "httpx_trust_env_false",
    "single_constructor_kwargs_assignment",
    "explicit_official_base_url",
    "constructor_kwargs_http_client_binding",
    "single_openai_constructor",
    "openai_exact_constructor_kwargs_expansion",
)
_PROBE_KEYS = (
    "transport_kind",
    "fixed_nonsecret_placeholder_used",
    "ambient_credential_value_used",
    "official_base_url",
    "base_url_exact",
    "trust_env",
    "max_retries",
    "observed_max_retries_zero",
    "transport_dispatch_count",
    "openai_client_close_call_count",
    "http_client_fallback_close_call_count",
    "http_client_closed",
    "passed",
)
_PARENT_OBSERVATION_KEYS = (
    "stage",
    "launch_contract",
    "environment_presence_bits",
    "python",
    "source_bindings",
    "isolated_child",
    "checks",
)
_PARENT_PYTHON_KEYS = (
    "version",
    "repository_relative_path",
    "under_repository_venv",
    "file_binding_before",
    "file_binding_after",
    "binding_stable",
)
_PARENT_ACTIVITY_KEYS = (
    "launch_contract_check_count",
    "environment_presence_check_count",
    "environment_value_read_count",
    "dotenv_read_count",
    "parent_sdk_dynamic_import_count",
    "parent_file_binding_count",
    "child_process_start_count",
    "child_process_kill_count",
    "child_timeout_count",
    "child_stdout_overflow_count",
    "child_stderr_overflow_count",
    "child_stdout_bytes",
    "child_stderr_bytes",
    "child_environment_entry_forward_count",
    "child_credential_value_forward_count",
    "parent_network_call_count",
    "provider_evaluator_or_agent_call_count",
)


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


class D141SDKNoCallSuccessorError(RuntimeError):
    """Raised when a D-141 observation cannot be represented safely."""


FileBindingReader = Callable[[Path], dict[str, Any]]


@dataclass(frozen=True)
class SDKWorkerDependencies:
    python_executable: Path
    python_version: str
    launch_contract: Callable[[], Mapping[str, Any]]
    file_binding: FileBindingReader
    distribution_version: Callable[[str], str | None]
    find_module_spec: Callable[[str], Any]
    module_is_preloaded: Callable[[str], bool]
    import_module: Callable[[str], ModuleType]
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]]
    bootstrap_helper_binding_verified: bool
    bootstrap_audit_hook_installed: bool
    bootstrap_guard_counters: Mapping[str, int]


@dataclass(frozen=True)
class _ResolvedOrigin:
    name: str
    path: Path | None
    relative_path: str | None
    safe: bool
    find_spec_performed: bool


@dataclass(frozen=True)
class IsolatedChildRequest:
    command: tuple[str, ...]
    cwd: Path
    environment_entries: tuple[tuple[str, str], ...]
    timeout_seconds: int
    stdout_limit_bytes: int
    stderr_limit_bytes: int


@dataclass(frozen=True)
class IsolatedChildExecution:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    stdout_overflow: bool
    stderr_overflow: bool
    process_start_count: int
    process_kill_count: int


@dataclass(frozen=True)
class SDKIsolatedSuccessorDependencies:
    python_executable: Path
    python_version: str
    launch_contract: Callable[[], Mapping[str, Any]]
    file_binding: FileBindingReader
    environment_present: Callable[[str], bool]
    child_temp_root: Path
    run_isolated_child: Callable[[IsolatedChildRequest], IsolatedChildExecution]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D141SDKNoCallSuccessorError(message)


def _zero_guard_counters() -> dict[str, int]:
    return {key: 0 for key in _GUARD_COUNTER_KEYS}


def _validate_zero_guard_counters(value: Any, *, label: str) -> dict[str, int]:
    _require(
        isinstance(value, Mapping)
        and set(value) == set(_GUARD_COUNTER_KEYS)
        and all(type(value[key]) is int and value[key] == 0 for key in _GUARD_COUNTER_KEYS),
        f"D-141 {label} guard recorded an attempt",
    )
    return {key: value[key] for key in _GUARD_COUNTER_KEYS}


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(__file__).resolve().parents[2] if repository is None else Path(repository)
    return root.resolve(strict=True)


def _stable_read(path: Path) -> bytes:
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    _require(
        (before.st_size, before.st_mtime_ns, before.st_ino)
        == (after.st_size, after.st_mtime_ns, after.st_ino),
        f"D-141 file changed during read: {path.name}",
    )
    return raw


def _file_binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    metadata = path.lstat()
    linklike = stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )
    _require(not linklike, f"D-141 link-like file is forbidden: {path.name}")
    raw = _stable_read(resolved)
    return {
        "file_name": resolved.name,
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "linklike": False,
    }


def _is_linklike(path: Path) -> bool:
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )


def _assert_nonlink_absolute_chain(path: Path, *, label: str) -> Path:
    _require(path.is_absolute(), f"D-141 {label} is not absolute")
    lexical = Path(os.path.abspath(path))
    resolved = lexical.resolve(strict=True)
    _require(lexical == resolved, f"D-141 {label} lexical and resolved paths differ")
    current = lexical
    while True:
        _require(not _is_linklike(current), f"D-141 {label} ancestor is link-like")
        if current.parent == current:
            break
        current = current.parent
    return resolved


def _canonical_repo_venv(root: Path) -> tuple[Path, Path]:
    resolved_root = _assert_nonlink_absolute_chain(root, label="repository root")
    lexical_venv = resolved_root / ".venv"
    venv = _assert_nonlink_absolute_chain(lexical_venv, label="repository venv")
    _require(
        venv.is_dir() and venv.parent == resolved_root and venv.is_relative_to(resolved_root),
        "D-141 canonical repository venv differs",
    )
    return resolved_root, venv


def _exact_absolute_path_text(value: Any, *, label: str) -> Path:
    _require(
        isinstance(value, str)
        and bool(value)
        and os.path.isabs(value)
        and value == os.path.abspath(value),
        f"D-141 {label} absolute lexical spelling differs",
    )
    return Path(value)


def _strict_nonlink_repo_path(
    root: Path,
    path: Path,
    *,
    boundary: Path,
    label: str,
) -> Path:
    resolved_root = _assert_nonlink_absolute_chain(root, label="repository root")
    resolved_boundary = _assert_nonlink_absolute_chain(boundary, label=f"{label} boundary")
    _require(path.is_absolute(), f"D-141 {label} is not absolute")
    lexical = Path(os.path.abspath(path))
    _require(
        path == lexical
        and "." not in path.parts
        and ".." not in path.parts
        and lexical.is_relative_to(resolved_boundary)
        and lexical.is_relative_to(resolved_root),
        f"D-141 {label} is lexically outside its repository boundary",
    )
    selected = _assert_nonlink_absolute_chain(lexical, label=label)
    _require(
        resolved_boundary.is_relative_to(resolved_root)
        and selected.is_relative_to(resolved_boundary)
        and selected.is_relative_to(resolved_root),
        f"D-141 {label} is outside its strict repository boundary",
    )
    return selected


@contextmanager
def _isolated_child_cwd(fixed_root: Path, repository: Path) -> Any:
    resolved_root = _assert_nonlink_absolute_chain(fixed_root, label="fixed child temp root")
    resolved_repository = repository.resolve(strict=True)
    _require(resolved_root.is_dir(), "D-141 fixed child temp root is not a directory")
    _require(not _is_linklike(fixed_root), "D-141 fixed child temp root is link-like")
    _require(
        not resolved_root.is_relative_to(resolved_repository),
        "D-141 child temp root is inside repository",
    )
    with tempfile.TemporaryDirectory(
        prefix=ISOLATED_CHILD_CWD_PREFIX,
        dir=resolved_root,
    ) as raw:
        child = Path(raw)
        resolved_child = _assert_nonlink_absolute_chain(child, label="isolated child cwd")
        _require(
            child.parent.resolve(strict=True) == resolved_root
            and resolved_child.parent == resolved_root
            and resolved_child.name.startswith(ISOLATED_CHILD_CWD_PREFIX)
            and resolved_child.is_dir()
            and not _is_linklike(child),
            "D-141 isolated child cwd contract differs",
        )
        _require(
            not resolved_child.is_relative_to(resolved_repository)
            and not resolved_repository.is_relative_to(resolved_child),
            "D-141 isolated child cwd and repository overlap",
        )
        yield resolved_child
        _require(
            child.exists()
            and _assert_nonlink_absolute_chain(child, label="isolated child cwd after execution")
            == resolved_child
            and child.parent.resolve(strict=True) == resolved_root
            and child.is_dir()
            and not any(child.iterdir())
            and not _is_linklike(child)
            and _assert_nonlink_absolute_chain(
                fixed_root, label="fixed child temp root after execution"
            )
            == resolved_root
            and not _is_linklike(fixed_root),
            "D-141 isolated child cwd drifted during execution",
        )


def _run_isolated_child_process(request: IsolatedChildRequest) -> IsolatedChildExecution:
    _require(
        isinstance(request, IsolatedChildRequest)
        and len(request.command) == 16
        and request.command[1:6] == ("-E", "-s", "-B", "-c", ISOLATED_CHILD_BOOTSTRAP)
        and request.command[9] == ISOLATED_CHILD_ELIGIBILITY_TOKEN
        and _SHA256.fullmatch(request.command[10]) is not None
        and request.command[11].isdigit()
        and int(request.command[11]) > 0
        and _SHA256.fullmatch(request.command[12]) is not None
        and request.command[13].isdigit()
        and int(request.command[13]) > 0
        and _SHA256.fullmatch(request.command[14]) is not None
        and request.command[15].isdigit()
        and int(request.command[15]) > 0,
        "D-141 child argv contract differs",
    )
    command_root_text = _exact_absolute_path_text(
        request.command[6], label="child command repository root"
    )
    command_root, command_venv = _canonical_repo_venv(command_root_text)
    command_python = _strict_nonlink_repo_path(
        command_root,
        _exact_absolute_path_text(request.command[0], label="child command Python executable"),
        boundary=command_venv,
        label="child command Python executable",
    )
    command_helper = _strict_nonlink_repo_path(
        command_root,
        _exact_absolute_path_text(request.command[7], label="child command helper"),
        boundary=command_root,
        label="child command helper",
    )
    command_temp_root = _exact_absolute_path_text(
        request.command[8], label="child command temp root"
    ).resolve(strict=True)
    request_cwd = _assert_nonlink_absolute_chain(request.cwd, label="child request cwd")
    _require(
        command_venv.is_relative_to(command_root)
        and command_python.is_relative_to(command_venv)
        and command_python.is_relative_to(command_root)
        and command_helper
        == (command_root / "patchloop/evals/d141_sdk_no_call_successor.py").resolve(strict=True)
        and command_temp_root == D141_FIXED_TEMP_ROOT.resolve(strict=True)
        and request_cwd.parent == command_temp_root
        and request_cwd.name.startswith(ISOLATED_CHILD_CWD_PREFIX)
        and not request_cwd.is_relative_to(command_root)
        and not command_root.is_relative_to(request_cwd),
        "D-141 child argv provenance differs",
    )
    _require(request.environment_entries == (), "D-141 child environment is not empty")
    _require(
        request.cwd.is_dir() and not any(request.cwd.iterdir()),
        "D-141 isolated child cwd is not fresh and empty",
    )
    _require(request.timeout_seconds == ISOLATED_CHILD_TIMEOUT_SECONDS, "D-141 child timeout")
    _require(
        request.stdout_limit_bytes == ISOLATED_CHILD_STDOUT_LIMIT_BYTES
        and request.stderr_limit_bytes == ISOLATED_CHILD_STDERR_LIMIT_BYTES,
        "D-141 child output bounds differ",
    )
    process: subprocess.Popen[bytes]
    try:
        process = subprocess.Popen(
            list(request.command),
            cwd=str(request.cwd),
            env={},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
        )
    except Exception:
        raise D141SDKNoCallSuccessorError("D-141 isolated child process could not start") from None
    _require(process.stdout is not None and process.stderr is not None, "D-141 child pipes")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    overflows = {"stdout": False, "stderr": False}
    drain_failures = {"stdout": False, "stderr": False}
    kill_count = 0
    lock = threading.Lock()

    def kill_once() -> None:
        nonlocal kill_count
        with lock:
            if process.poll() is None:
                try:
                    process.kill()
                    kill_count += 1
                except OSError:
                    pass

    def drain(name: str, stream: Any, limit: int) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                remaining = limit + 1 - len(buffers[name])
                if remaining > 0:
                    buffers[name].extend(chunk[:remaining])
                if len(buffers[name]) > limit or len(chunk) > remaining:
                    overflows[name] = True
                    kill_once()
        except Exception:
            drain_failures[name] = True
            kill_once()

    stdout_thread = threading.Thread(
        target=drain,
        args=("stdout", process.stdout, request.stdout_limit_bytes),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=drain,
        args=("stderr", process.stderr, request.stderr_limit_bytes),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        process.wait(timeout=request.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_once()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.stdout.close()
            process.stderr.close()
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            raise D141SDKNoCallSuccessorError(
                "D-141 isolated child did not exit after bounded kill"
            ) from None
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    if stdout_thread.is_alive() or stderr_thread.is_alive():
        kill_once()
        try:
            process.stdout.close()
            process.stderr.close()
        finally:
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
    _require(
        not stdout_thread.is_alive() and not stderr_thread.is_alive(),
        "D-141 isolated child pipe drain did not terminate",
    )
    _require(
        not drain_failures["stdout"] and not drain_failures["stderr"],
        "D-141 isolated child pipe drain failed",
    )
    return IsolatedChildExecution(
        returncode=process.returncode,
        stdout=bytes(buffers["stdout"]),
        stderr=bytes(buffers["stderr"]),
        timed_out=timed_out,
        stdout_overflow=overflows["stdout"],
        stderr_overflow=overflows["stderr"],
        process_start_count=1,
        process_kill_count=kill_count,
    )


def _validate_file_binding(value: Any, *, label: str) -> None:
    fields = ("file_name", "file_bytes", "file_sha256", "linklike")
    _require(
        isinstance(value, dict) and tuple(value) in {fields, tuple(sorted(fields))},
        f"D-141 {label} binding fields differ",
    )
    _require(isinstance(value["file_name"], str) and bool(value["file_name"]), label)
    _require(type(value["file_bytes"]) is int and value["file_bytes"] > 0, label)
    _require(
        isinstance(value["file_sha256"], str)
        and _SHA256.fullmatch(value["file_sha256"]) is not None,
        label,
    )
    _require(value["linklike"] is False, f"D-141 {label} is link-like")


def current_d141_sdk_launch_contract() -> dict[str, Any]:
    """Return flag booleans only; this does not read environment variables."""

    return {
        "ignore_python_environment": bool(sys.flags.ignore_environment),
        "user_site_disabled": bool(sys.flags.no_user_site),
        "bytecode_writes_disabled": bool(sys.flags.dont_write_bytecode),
        "isolated_mode": bool(sys.flags.isolated),
        "safe_path_mode": bool(getattr(sys.flags, "safe_path", False)),
    }


def validate_d141_sdk_launch_contract(value: Any) -> dict[str, Any]:
    _require(isinstance(value, dict), "D-141 launch contract is not an object")
    _require(value == EXACT_LAUNCH_CONTRACT, "D-141 launch contract differs")
    return value


def _default_isolated_dependencies() -> SDKIsolatedSuccessorDependencies:
    def environment_present(name: str) -> bool:
        _require(name in SDK_ENVIRONMENT_NAMES, "D-141 unexpected environment name")
        return name in os.environ

    return SDKIsolatedSuccessorDependencies(
        python_executable=Path(sys.executable),
        python_version=".".join(str(value) for value in sys.version_info[:3]),
        launch_contract=current_d141_sdk_launch_contract,
        file_binding=_file_binding,
        environment_present=environment_present,
        child_temp_root=D141_FIXED_TEMP_ROOT,
        run_isolated_child=_run_isolated_child_process,
    )


def _observer_contract() -> dict[str, Any]:
    return {
        "exact_launch_contract": EXACT_LAUNCH_CONTRACT,
        "launcher_source_contract": LAUNCHER_SOURCE_CONTRACT,
        "parent_eligibility_presence_names": list(SDK_ENVIRONMENT_NAMES),
        "parent_eligibility_token_validation_count": 1,
        "worker_environment_presence_check_count": 0,
        "environment_value_access_authorized": False,
        "environment_value_read_count": 0,
        "environment_value_read_attempt_count": 0,
        "environment_mutation_attempt_count": 0,
        "startup_environment_entry_count": 0,
        "dotenv_read_authorized": False,
        "worker_guard_start": "after-secret-free-child-startup-before-sdk-resolution",
        "bootstrap_audit_hook_required": True,
        "bootstrap_guard_attempt_counts_required": {key: 0 for key in _GUARD_COUNTER_KEYS},
        "worker_audit_hook_required": True,
        "worker_environment_value_access": "deny",
        "worker_dotenv_open": "audit-deny",
        "worker_socket_network": "audit-deny",
        "worker_subprocess": "audit-deny",
        "dynamic_import_names": ["httpx", "openai"],
        "official_base_url": OFFICIAL_API_BASE_URL,
        "synthetic_transport": "httpx.MockTransport-reject-dispatch",
        "synthetic_transport_dispatch_limit": 0,
        "trust_env": False,
        "max_retries": 0,
        "ambient_credential_value_used": False,
    }


def _empty_activity() -> dict[str, Any]:
    return {
        "launch_contract_check_count": 1,
        "eligibility_token_validation_count": 1,
        "bootstrap_audit_hook_installed_count": 1,
        "bootstrap_environment_value_read_attempt_count": 0,
        "bootstrap_environment_mutation_attempt_count": 0,
        "bootstrap_dotenv_open_attempt_count": 0,
        "bootstrap_network_denied_attempt_count": 0,
        "bootstrap_subprocess_denied_attempt_count": 0,
        "worker_audit_hook_installed_count": 1,
        "committed_helper_bootstrap_verification_count": 1,
        "committed_model_binding_verification_count": 0,
        "committed_lock_binding_verification_count": 0,
        "environment_presence_check_count": 0,
        "environment_value_read_count": 0,
        "environment_value_read_attempt_count": 0,
        "environment_mutation_attempt_count": 0,
        "startup_environment_entry_count": 0,
        "dotenv_read_count": 0,
        "dotenv_open_attempt_count": 0,
        "python_executable_file_binding_count": 0,
        "preloaded_module_membership_check_count": 0,
        "find_module_spec_count": 0,
        "sdk_module_file_binding_count": 0,
        "distribution_version_observation_count": 0,
        "locked_version_source_read_count": 0,
        "checked_in_factory_source_read_count": 0,
        "dynamic_module_import_count": 0,
        "synthetic_transport_dispatch_count": 0,
        "network_call_count": 0,
        "network_denied_attempt_count": 0,
        "subprocess_denied_attempt_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
        "openai_client_close_call_count": 0,
        "http_client_fallback_close_call_count": 0,
        "http_client_closed": None,
    }


def _worker_committed_source_facts(
    dependencies: SDKWorkerDependencies,
    *,
    model_verification_count: int,
    lock_verification_count: int,
) -> dict[str, Any]:
    expected = _validate_expected_committed_source_bindings(
        dependencies.expected_committed_source_bindings
    )
    _require(
        dependencies.bootstrap_helper_binding_verified is True,
        "D-141 bootstrap helper binding was not verified",
    )
    _require(
        dependencies.bootstrap_audit_hook_installed is True,
        "D-141 bootstrap audit hook was not installed",
    )
    _validate_zero_guard_counters(
        dependencies.bootstrap_guard_counters,
        label="bootstrap",
    )
    return {
        name: {
            "repository_relative_path": expected[name]["repository_relative_path"],
            "expected_committed_file_bytes": expected[name]["file_bytes"],
            "expected_committed_file_sha256": expected[name]["file_sha256"],
            "expected_committed_linklike": False,
            "verification_count": (
                1
                if name == "helper"
                else model_verification_count
                if name == "model"
                else lock_verification_count
            ),
            "every_verification_matched": (
                True
                if name == "helper"
                else True
                if (model_verification_count if name == "model" else lock_verification_count) > 0
                else None
            ),
        }
        for name in ("helper", "model", "lock")
    }


def _result(
    *,
    stage: str,
    launch: dict[str, Any],
    presence: dict[str, bool] | None,
    committed_sources: dict[str, Any],
    python: dict[str, Any] | None,
    modules: dict[str, Any] | None,
    factory: dict[str, Any] | None,
    probe: dict[str, Any] | None,
    checks: dict[str, bool],
    blockers: list[str],
    activity: dict[str, Any],
) -> dict[str, Any]:
    passed = not blockers and stage == "complete"
    value = {
        "schema_version": SDK_WORKER_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS,
        "observer_contract": _observer_contract(),
        "observation": {
            "stage": stage,
            "launch_contract": launch,
            "parent_eligibility_bits": presence,
            "committed_source_bindings": committed_sources,
            "python": python,
            "modules": modules,
            "production_client_factory": factory,
            "synthetic_probe": probe,
            "checks": checks,
        },
        "blockers": blockers,
        "activity": activity,
        "passed": passed,
    }
    return _validate_worker_observation(_canonicalize_json(value))


def _canonicalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonicalize_json(item) for item in value]
    return value


def _require_canonical_mapping_order(value: Any, *, label: str) -> None:
    if isinstance(value, dict):
        _require(tuple(value) == tuple(sorted(value)), f"D-141 {label} key order differs")
        for item in value.values():
            _require_canonical_mapping_order(item, label=label)
    elif isinstance(value, list):
        for item in value:
            _require_canonical_mapping_order(item, label=label)


def _stable_committed_read(
    root: Path,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> bytes:
    relative = expected["repository_relative_path"]
    _require(isinstance(relative, str), f"D-141 committed {label} path differs")
    resolved_root = _assert_nonlink_absolute_chain(root, label="repository root")
    selected = _strict_nonlink_repo_path(
        resolved_root,
        resolved_root / Path(relative),
        boundary=resolved_root,
        label=f"committed {label}",
    )
    before = selected.lstat()
    _require(
        not stat.S_ISLNK(before.st_mode)
        and not bool(getattr(before, "st_file_attributes", 0) & 0x400),
        f"D-141 committed {label} became link-like",
    )
    raw = selected.read_bytes()
    after = selected.lstat()
    _require(
        not stat.S_ISLNK(after.st_mode)
        and not bool(getattr(after, "st_file_attributes", 0) & 0x400)
        and (before.st_size, before.st_mtime_ns, before.st_ino)
        == (after.st_size, after.st_mtime_ns, after.st_ino),
        f"D-141 committed {label} changed during read",
    )
    _require(
        len(raw) == expected["file_bytes"]
        and sha256_bytes(raw) == expected["file_sha256"]
        and expected["linklike"] is False,
        f"D-141 committed {label} binding differs",
    )
    return raw


def _locked_version(
    root: Path,
    package: str,
    expected_lock_binding: Mapping[str, Any],
) -> str | None:
    text = _stable_committed_read(
        root,
        expected_lock_binding,
        label="lock",
    ).decode("utf-8")
    match = re.search(
        rf'\[\[package\]\]\s+name = "{re.escape(package)}"\s+version = "([^"]+)"', text
    )
    return match.group(1) if match else None


def _python_observation(
    root: Path, dependencies: SDKWorkerDependencies
) -> tuple[dict[str, Any], Path | None]:
    safe = False
    relative: str | None = None
    selected: Path | None = None
    try:
        resolved_root, venv = _canonical_repo_venv(root)
        candidate = _strict_nonlink_repo_path(
            resolved_root,
            dependencies.python_executable,
            boundary=venv,
            label="worker Python executable",
        )
        safe = (
            venv.is_relative_to(resolved_root)
            and candidate.is_relative_to(venv)
            and candidate.is_relative_to(resolved_root)
        )
        if safe:
            selected = candidate
            relative = candidate.relative_to(resolved_root).as_posix()
    except (OSError, RuntimeError, ValueError):
        pass
    return (
        {
            "version": dependencies.python_version,
            "repository_relative_path": relative,
            "under_repository_venv": safe,
            "file_binding_before": None,
            "file_binding_preimport_recheck": None,
            "file_binding_after": None,
            "preimport_binding_stable": None,
            "binding_stable": None,
            "under_repository_venv_after_probe": None,
        },
        selected,
    )


def _resolve_origin(root: Path, name: str, dependencies: SDKWorkerDependencies) -> _ResolvedOrigin:
    performed = False
    try:
        resolved_root, venv = _canonical_repo_venv(root)
        performed = True
        spec = dependencies.find_module_spec(name)
        origin = getattr(spec, "origin", None)
        if not isinstance(origin, str) or not origin or origin in {"built-in", "frozen"}:
            raise ValueError("unsafe module origin")
        selected = _strict_nonlink_repo_path(
            resolved_root,
            _exact_absolute_path_text(origin, label=f"{name} module origin"),
            boundary=venv,
            label=f"{name} module origin",
        )
        safe = True
        relative = selected.relative_to(resolved_root).as_posix() if safe else None
    except Exception:
        return _ResolvedOrigin(name, None, None, False, performed)
    return _ResolvedOrigin(name, selected if safe else None, relative, safe, performed)


def _bind_preimport_module(
    root: Path, origin: _ResolvedOrigin, dependencies: SDKWorkerDependencies
) -> dict[str, Any]:
    _require(origin.safe and origin.path is not None and origin.relative_path is not None, "origin")
    binding = dependencies.file_binding(origin.path)
    _validate_file_binding(binding, label=f"{origin.name} module")
    installed = dependencies.distribution_version(origin.name)
    locked = _locked_version(
        root,
        origin.name,
        dependencies.expected_committed_source_bindings["lock"],
    )
    return {
        "distribution_name": origin.name,
        "distribution_version": installed,
        "module_version": None,
        "locked_version": locked,
        "repository_relative_path": origin.relative_path,
        "under_repository_venv": True,
        "file_binding_before": binding,
        "file_binding_preimport_recheck": None,
        "file_binding_immediate_import_recheck": None,
        "file_binding_after": None,
        "preimport_binding_stable": None,
        "immediate_import_binding_stable": None,
        "binding_stable": None,
        "distribution_version_preimport_recheck": None,
        "locked_version_preimport_recheck": None,
        "preimport_versions_stable": None,
        "distribution_version_immediate_import_recheck": None,
        "locked_version_immediate_import_recheck": None,
        "immediate_import_versions_stable": None,
        "distribution_version_after": None,
        "locked_version_after": None,
        "versions_stable_after_probe": None,
        "origin_stable_before_import": None,
        "origin_stable_immediately_before_import": None,
        "origin_stable_after_probe": None,
        "versions_match": isinstance(installed, str) and installed == locked,
    }


def _loaded_module(
    root: Path, name: str, module: ModuleType, preimport: dict[str, Any]
) -> dict[str, Any]:
    value = getattr(module, "__file__", None)
    _require(isinstance(value, str) and bool(value), f"D-141 {name} loaded file missing")
    resolved_root, venv = _canonical_repo_venv(root)
    actual = _strict_nonlink_repo_path(
        resolved_root,
        _exact_absolute_path_text(value, label=f"loaded {name} module"),
        boundary=venv,
        label=f"loaded {name} module",
    )
    expected = _strict_nonlink_repo_path(
        resolved_root,
        resolved_root / Path(preimport["repository_relative_path"]),
        boundary=venv,
        label=f"expected {name} module",
    )
    _require(
        venv.is_relative_to(resolved_root)
        and expected.is_relative_to(venv)
        and expected.is_relative_to(resolved_root)
        and actual.is_relative_to(venv)
        and actual.is_relative_to(resolved_root)
        and actual == expected,
        f"D-141 {name} loaded origin differs",
    )
    result = dict(preimport)
    result["module_version"] = getattr(module, "__version__", None)
    result["versions_match"] = (
        isinstance(result["distribution_version"], str)
        and result["distribution_version"] == result["module_version"] == result["locked_version"]
    )
    return result


def _revalidate_before_import(
    root: Path,
    dependencies: SDKWorkerDependencies,
    *,
    python: dict[str, Any],
    python_path: Path,
    origins: Mapping[str, _ResolvedOrigin],
    modules: Mapping[str, dict[str, Any]],
) -> dict[str, _ResolvedOrigin]:
    fresh_python, fresh_python_path = _python_observation(root, dependencies)
    _require(
        fresh_python_path == python_path
        and fresh_python["under_repository_venv"] is True
        and fresh_python["repository_relative_path"] == python["repository_relative_path"],
        "D-141 Python provenance drifted before SDK import",
    )
    python_recheck = dependencies.file_binding(python_path)
    _validate_file_binding(python_recheck, label="Python executable before import")
    python["file_binding_preimport_recheck"] = python_recheck
    python["preimport_binding_stable"] = python["file_binding_before"] == python_recheck
    _require(python["preimport_binding_stable"] is True, "D-141 Python binding drifted")

    fresh_origins = {
        "httpx": _resolve_origin(root, "httpx", dependencies),
        "openai": _resolve_origin(root, "openai", dependencies),
    }
    for name in ("httpx", "openai"):
        fresh = fresh_origins[name]
        original = origins[name]
        _require(
            fresh.safe
            and fresh.path == original.path
            and fresh.relative_path == original.relative_path,
            f"D-141 {name} origin drifted before SDK import",
        )
        binding = dependencies.file_binding(fresh.path)
        _validate_file_binding(binding, label=f"{name} module before import")
        modules[name]["file_binding_preimport_recheck"] = binding
        modules[name]["preimport_binding_stable"] = modules[name]["file_binding_before"] == binding
        installed = dependencies.distribution_version(name)
        locked = _locked_version(
            root,
            name,
            dependencies.expected_committed_source_bindings["lock"],
        )
        modules[name]["distribution_version_preimport_recheck"] = installed
        modules[name]["locked_version_preimport_recheck"] = locked
        modules[name]["preimport_versions_stable"] = (
            installed == modules[name]["distribution_version"]
            and locked == modules[name]["locked_version"]
            and isinstance(installed, str)
            and installed == locked
        )
        modules[name]["origin_stable_before_import"] = True
        _require(
            modules[name]["preimport_binding_stable"] is True
            and modules[name]["preimport_versions_stable"] is True,
            f"D-141 {name} binding or version drifted before SDK import",
        )
    return fresh_origins


def _revalidate_module_immediately_before_import(
    root: Path,
    name: str,
    dependencies: SDKWorkerDependencies,
    *,
    origin: _ResolvedOrigin,
    module: dict[str, Any],
) -> _ResolvedOrigin:
    fresh = _resolve_origin(root, name, dependencies)
    _require(
        fresh.safe and fresh.path == origin.path and fresh.relative_path == origin.relative_path,
        f"D-141 {name} origin drifted immediately before SDK import",
    )
    binding = dependencies.file_binding(fresh.path)
    _validate_file_binding(binding, label=f"{name} module immediately before import")
    installed = dependencies.distribution_version(name)
    locked = _locked_version(
        root,
        name,
        dependencies.expected_committed_source_bindings["lock"],
    )
    module["file_binding_immediate_import_recheck"] = binding
    module["immediate_import_binding_stable"] = module["file_binding_before"] == binding
    module["distribution_version_immediate_import_recheck"] = installed
    module["locked_version_immediate_import_recheck"] = locked
    module["immediate_import_versions_stable"] = (
        installed == module["distribution_version"]
        and locked == module["locked_version"]
        and isinstance(installed, str)
        and installed == locked
    )
    module["origin_stable_immediately_before_import"] = True
    _require(
        module["immediate_import_binding_stable"] is True
        and module["immediate_import_versions_stable"] is True,
        f"D-141 {name} binding or version drifted immediately before SDK import",
    )
    return fresh


def _revalidate_after_probe(
    root: Path,
    dependencies: SDKWorkerDependencies,
    *,
    python: dict[str, Any],
    python_path: Path,
    origins: Mapping[str, _ResolvedOrigin],
    modules: Mapping[str, dict[str, Any]],
) -> None:
    fresh_python, fresh_python_path = _python_observation(root, dependencies)
    _require(
        fresh_python_path == python_path
        and fresh_python["under_repository_venv"] is True
        and fresh_python["repository_relative_path"] == python["repository_relative_path"],
        "D-141 Python provenance drifted after SDK probe",
    )
    python_after = dependencies.file_binding(python_path)
    _validate_file_binding(python_after, label="Python executable after probe")
    python["file_binding_after"] = python_after
    python["binding_stable"] = python["file_binding_before"] == python_after
    python["under_repository_venv_after_probe"] = True

    fresh_origins = {
        "openai": _resolve_origin(root, "openai", dependencies),
        "httpx": _resolve_origin(root, "httpx", dependencies),
    }
    for name in ("openai", "httpx"):
        fresh = fresh_origins[name]
        original = origins[name]
        _require(
            fresh.safe
            and fresh.path == original.path
            and fresh.relative_path == original.relative_path,
            f"D-141 {name} origin drifted after SDK probe",
        )
        after = dependencies.file_binding(fresh.path)
        _validate_file_binding(after, label=f"{name} module after probe")
        installed = dependencies.distribution_version(name)
        locked = _locked_version(
            root,
            name,
            dependencies.expected_committed_source_bindings["lock"],
        )
        modules[name]["file_binding_after"] = after
        modules[name]["binding_stable"] = modules[name]["file_binding_before"] == after
        modules[name]["distribution_version_after"] = installed
        modules[name]["locked_version_after"] = locked
        modules[name]["versions_stable_after_probe"] = (
            installed == modules[name]["distribution_version"]
            and locked == modules[name]["locked_version"]
            and isinstance(installed, str)
            and installed == locked
        )
        modules[name]["origin_stable_after_probe"] = True


def _factory_contract(
    root: Path,
    expected_model_binding: Mapping[str, Any],
) -> dict[str, Any]:
    source = _stable_committed_read(
        root,
        expected_model_binding,
        label="model",
    ).decode("utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise D141SDKNoCallSuccessorError("D-141 model source cannot be parsed") from exc
    checked_url: str | None = None
    factory: ast.FunctionDef | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "OFFICIAL_API_BASE_URL"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            checked_url = node.value.value
        if isinstance(node, ast.FunctionDef) and node.name == "create_openai_client":
            factory = node
    http_calls: list[ast.Call] = []
    openai_calls: list[ast.Call] = []
    http_assignment = False
    base_binding = False
    client_binding = False
    kwargs_assignments = 0
    if factory is not None:
        for node in ast.walk(factory):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "httpx"
                and node.func.attr == "Client"
            ):
                http_calls.append(node)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "OpenAI"
            ):
                openai_calls.append(node)
        for node in factory.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "http_client"
                and isinstance(node.value, ast.Call)
                and node.value in http_calls
            ):
                http_assignment = True
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "constructor_kwargs"
                and isinstance(node.value, ast.Dict)
            ):
                kwargs_assignments += 1
                pairs = {
                    key.value: item
                    for key, item in zip(node.value.keys, node.value.values, strict=True)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                base = pairs.get("base_url")
                client = pairs.get("http_client")
                base_binding = isinstance(base, ast.Name) and base.id == "OFFICIAL_API_BASE_URL"
                client_binding = isinstance(client, ast.Name) and client.id == "http_client"
    trust_false = len(http_calls) == 1 and any(
        keyword.arg == "trust_env"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is False
        for keyword in http_calls[0].keywords
    )
    exact_openai = len(openai_calls) == 1 and (
        not openai_calls[0].args
        and len(openai_calls[0].keywords) == 1
        and openai_calls[0].keywords[0].arg is None
        and isinstance(openai_calls[0].keywords[0].value, ast.Name)
        and openai_calls[0].keywords[0].value.id == "constructor_kwargs"
    )
    return {
        "checked_in_official_base_url": checked_url,
        "official_base_url_exact": checked_url == OFFICIAL_API_BASE_URL,
        "factory_found": factory is not None,
        "single_httpx_client_constructor": len(http_calls) == 1,
        "httpx_client_assigned_to_http_client": http_assignment,
        "httpx_trust_env_false": trust_false,
        "single_constructor_kwargs_assignment": kwargs_assignments == 1,
        "explicit_official_base_url": base_binding,
        "constructor_kwargs_http_client_binding": client_binding,
        "single_openai_constructor": len(openai_calls) == 1,
        "openai_exact_constructor_kwargs_expansion": exact_openai,
    }


def _synthetic_probe(openai_module: ModuleType, httpx_module: ModuleType) -> dict[str, Any]:
    dispatch_count = 0

    def reject_dispatch(_request: Any) -> Any:
        nonlocal dispatch_count
        dispatch_count += 1
        raise D141SDKNoCallSuccessorError("D-141 synthetic transport dispatch is forbidden")

    transport = httpx_module.MockTransport(reject_dispatch)
    http_client = httpx_module.Client(transport=transport, trust_env=False)
    openai_client: Any = None
    openai_close_count = 0
    fallback_close_count = 0
    base_exact = False
    retries_zero = False
    closed = False
    try:
        openai_client = openai_module.OpenAI(
            api_key="d141-fixed-nonsecret-placeholder",
            organization="d141-none",
            project="d141-none",
            webhook_secret="d141-none",
            base_url=OFFICIAL_API_BASE_URL,
            max_retries=0,
            http_client=http_client,
        )
        base_exact = str(openai_client.base_url).rstrip("/") == OFFICIAL_API_BASE_URL
        retries_zero = openai_client.max_retries == 0
    finally:
        try:
            if openai_client is not None:
                openai_client.close()
                openai_close_count += 1
        finally:
            if not http_client.is_closed:
                http_client.close()
                fallback_close_count += 1
            closed = http_client.is_closed
    passed = (
        base_exact
        and retries_zero
        and dispatch_count == 0
        and openai_close_count == 1
        and fallback_close_count in (0, 1)
        and closed is True
    )
    return {
        "transport_kind": "httpx.MockTransport-reject-dispatch",
        "fixed_nonsecret_placeholder_used": True,
        "ambient_credential_value_used": False,
        "official_base_url": OFFICIAL_API_BASE_URL,
        "base_url_exact": base_exact,
        "trust_env": False,
        "max_retries": 0,
        "observed_max_retries_zero": retries_zero,
        "transport_dispatch_count": dispatch_count,
        "openai_client_close_call_count": openai_close_count,
        "http_client_fallback_close_call_count": fallback_close_count,
        "http_client_closed": closed,
        "passed": passed,
    }


class _DeniedWorkerEnvironment(MutableMapping[str, str]):
    def __init__(self, counters: dict[str, int]) -> None:
        self._counters = counters

    def _deny(self) -> Any:
        self._counters["environment_value_read_attempt_count"] += 1
        raise D141SDKNoCallSuccessorError(
            "D-141 isolated worker environment value access was denied"
        )

    def _deny_mutation(self) -> Any:
        self._counters["environment_mutation_attempt_count"] += 1
        raise D141SDKNoCallSuccessorError("D-141 isolated worker environment mutation was denied")

    def __getitem__(self, _key: str) -> str:
        return self._deny()

    def __setitem__(self, _key: str, _value: str) -> None:
        self._deny_mutation()

    def __delitem__(self, _key: str) -> None:
        self._deny_mutation()

    def __iter__(self) -> Any:
        return self._deny()

    def __len__(self) -> int:
        return 0

    def __contains__(self, _key: object) -> bool:
        return self._deny()

    def get(self, _key: str, _default: Any = None) -> Any:
        return self._deny()

    def setdefault(self, _key: str, _default: str | None = None) -> str:
        return self._deny_mutation()

    def pop(self, _key: str, _default: Any = None) -> str:
        return self._deny_mutation()

    def popitem(self) -> tuple[str, str]:
        return self._deny_mutation()

    def update(self, *_args: Any, **_kwargs: Any) -> None:
        self._deny_mutation()

    def clear(self) -> None:
        self._deny_mutation()

    def __ior__(self, _other: object) -> Any:
        return self._deny_mutation()

    def keys(self) -> Any:
        return self._deny()

    def items(self) -> Any:
        return self._deny()

    def values(self) -> Any:
        return self._deny()

    def copy(self) -> Any:
        return self._deny()

    def __or__(self, _other: object) -> Any:
        return self._deny()

    def __ror__(self, _other: object) -> Any:
        return self._deny()


def _install_worker_guards() -> dict[str, int]:
    counters = {
        "environment_value_read_attempt_count": 0,
        "environment_mutation_attempt_count": 0,
        "dotenv_open_attempt_count": 0,
        "network_denied_attempt_count": 0,
        "subprocess_denied_attempt_count": 0,
    }

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and args:
            candidate = args[0]
            if isinstance(candidate, (str, bytes, os.PathLike)):
                try:
                    parts = Path(os.fsdecode(candidate)).parts
                except (TypeError, ValueError):
                    parts = ()
                if any(
                    part.casefold() == ".env" or part.casefold().startswith(".env.")
                    for part in parts
                ):
                    counters["dotenv_open_attempt_count"] += 1
                    raise D141SDKNoCallSuccessorError(
                        "D-141 isolated worker dotenv open was denied"
                    )
        if event.startswith("socket.") or event in {
            "http.client.connect",
            "urllib.Request",
        }:
            counters["network_denied_attempt_count"] += 1
            raise D141SDKNoCallSuccessorError("D-141 isolated worker network operation was denied")
        if event in {"os.putenv", "os.unsetenv"}:
            counters["environment_mutation_attempt_count"] += 1
            raise D141SDKNoCallSuccessorError(
                "D-141 isolated worker environment mutation was denied"
            )
        if (
            event == "subprocess.Popen"
            or event == "os.system"
            or event.startswith(("os.spawn", "os.exec"))
        ):
            counters["subprocess_denied_attempt_count"] += 1
            raise D141SDKNoCallSuccessorError(
                "D-141 isolated worker subprocess operation was denied"
            )

    _require(len(os.environ) == 0, "D-141 isolated worker startup environment is not empty")
    sys.addaudithook(audit)
    denied = _DeniedWorkerEnvironment(counters)
    os.environ = denied  # type: ignore[assignment]  # noqa: B003
    os.getenv = denied.get  # type: ignore[assignment]
    if hasattr(os, "environb"):
        os.environb = denied  # type: ignore[attr-defined,assignment]
    if hasattr(os, "getenvb"):
        os.getenvb = denied.get  # type: ignore[attr-defined,assignment]
    os.putenv = lambda *_args: denied._deny_mutation()  # type: ignore[assignment]
    os.unsetenv = lambda *_args: denied._deny_mutation()  # type: ignore[assignment]
    return counters


def _remove_repository_from_sys_path(root: Path) -> None:
    resolved_root, venv = _canonical_repo_venv(root)
    base_prefix = _assert_nonlink_absolute_chain(Path(sys.base_prefix), label="Python base prefix")
    retained_base: list[str] = []
    retained_venv: list[str] = []
    venv_entry_retained = False
    for entry in sys.path:
        if (
            not isinstance(entry, str)
            or not entry
            or not os.path.isabs(entry)
            or entry != os.path.abspath(entry)
        ):
            continue
        lexical = Path(entry)
        if lexical == venv or lexical.is_relative_to(venv):
            try:
                selected = _strict_nonlink_repo_path(
                    resolved_root,
                    lexical,
                    boundary=venv,
                    label="repository venv sys.path entry",
                )
            except (OSError, RuntimeError, ValueError):
                continue
            retained_venv.append(str(selected))
            venv_entry_retained = True
            continue
        if lexical == resolved_root or lexical.is_relative_to(resolved_root):
            continue
        if not (lexical == base_prefix or lexical.is_relative_to(base_prefix)):
            continue
        try:
            selected = _assert_nonlink_absolute_chain(lexical, label="Python base sys.path entry")
        except (OSError, RuntimeError, ValueError):
            continue
        if any(part.casefold() in {"site-packages", "dist-packages"} for part in selected.parts):
            continue
        retained_base.append(str(selected))
    _require(venv_entry_retained, "D-141 repository venv sys.path entry is missing")
    sys.path[:] = [*retained_base, *retained_venv]


def _worker_dependencies(
    root: Path,
    *,
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]],
    bootstrap_helper_binding_verified: bool,
    bootstrap_audit_hook_installed: bool,
    bootstrap_guard_counters: Mapping[str, int],
) -> SDKWorkerDependencies:
    def distribution_version(name: str) -> str | None:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    return SDKWorkerDependencies(
        python_executable=Path(sys.executable),
        python_version=".".join(str(value) for value in sys.version_info[:3]),
        launch_contract=current_d141_sdk_launch_contract,
        file_binding=_file_binding,
        distribution_version=distribution_version,
        find_module_spec=importlib.util.find_spec,
        module_is_preloaded=lambda name: name in sys.modules,
        import_module=importlib.import_module,
        expected_committed_source_bindings=expected_committed_source_bindings,
        bootstrap_helper_binding_verified=bootstrap_helper_binding_verified,
        bootstrap_audit_hook_installed=bootstrap_audit_hook_installed,
        bootstrap_guard_counters=bootstrap_guard_counters,
    )


def _compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _run_isolated_worker_entry(
    repository: str,
    fixed_temp_root: str,
    token: str,
    *,
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]],
    bootstrap_helper_binding_verified: bool,
    bootstrap_audit_hook_installed: bool,
    bootstrap_guard_counters: Mapping[str, int],
) -> dict[str, Any]:
    _require(token == ISOLATED_CHILD_ELIGIBILITY_TOKEN, "D-141 worker token differs")
    root = _exact_absolute_path_text(repository, label="worker repository root").resolve(
        strict=True
    )
    temp_root = _assert_nonlink_absolute_chain(
        _exact_absolute_path_text(fixed_temp_root, label="worker fixed child temp root"),
        label="worker fixed child temp root",
    )
    _require(
        temp_root == D141_FIXED_TEMP_ROOT.resolve(strict=True),
        "D-141 worker fixed child temp root differs",
    )
    cwd = _assert_nonlink_absolute_chain(Path.cwd(), label="worker isolated child cwd")
    helper = _strict_nonlink_repo_path(
        root,
        Path(__file__),
        boundary=root,
        label="isolated worker helper source",
    )
    _require(
        helper
        == _strict_nonlink_repo_path(
            root,
            root / "patchloop/evals/d141_sdk_no_call_successor.py",
            boundary=root,
            label="expected isolated worker helper source",
        ),
        "D-141 isolated worker source differs",
    )
    _require(
        temp_root.is_dir()
        and not _is_linklike(Path(fixed_temp_root))
        and cwd.parent == temp_root
        and cwd.name.startswith(ISOLATED_CHILD_CWD_PREFIX)
        and not _is_linklike(Path.cwd())
        and not cwd.is_relative_to(root)
        and not root.is_relative_to(cwd),
        "D-141 isolated worker cwd differs",
    )
    expected = _validate_expected_committed_source_bindings(expected_committed_source_bindings)
    _require(
        bootstrap_helper_binding_verified is True,
        "D-141 bootstrap helper binding was not verified",
    )
    _require(
        bootstrap_audit_hook_installed is True,
        "D-141 bootstrap audit hook was not installed",
    )
    _validate_zero_guard_counters(bootstrap_guard_counters, label="bootstrap before worker")
    _remove_repository_from_sys_path(root)
    counters = _install_worker_guards()
    result = _run_worker_observation(
        repository=root,
        dependencies=_worker_dependencies(
            root,
            expected_committed_source_bindings=expected,
            bootstrap_helper_binding_verified=bootstrap_helper_binding_verified,
            bootstrap_audit_hook_installed=bootstrap_audit_hook_installed,
            bootstrap_guard_counters=bootstrap_guard_counters,
        ),
    )
    _validate_zero_guard_counters(counters, label="isolated worker")
    _validate_zero_guard_counters(bootstrap_guard_counters, label="bootstrap after worker")
    return result


def _isolated_worker_main() -> int:
    if len(sys.argv) != 5 or sys.argv[1] != ISOLATED_CHILD_WORKER_ACTION:
        return 64
    try:
        expected = globals().get("__d141_bootstrap_expected_source_bindings__")
        bootstrap_counters = globals().get("__d141_bootstrap_counters__")
        helper_verified = globals().get("__d141_bootstrap_helper_binding_verified__")
        audit_installed = globals().get("__d141_bootstrap_audit_hook_installed__")
        value = _run_isolated_worker_entry(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            expected_committed_source_bindings=expected,
            bootstrap_helper_binding_verified=helper_verified,
            bootstrap_audit_hook_installed=audit_installed,
            bootstrap_guard_counters=bootstrap_counters,
        )
    except Exception:
        return 70
    sys.stdout.buffer.write(_compact_json_bytes(value) + b"\n")
    sys.stdout.buffer.flush()
    return 0


_FULL_BLOCKERS = {
    "exact_launch_contract": "exact-launch-contract-differs",
    "openai_api_key_present": "openai-api-key-presence-bit-is-false",
    "pythonhome_absent": "pythonhome-presence-bit-is-true",
    "pythonpath_absent": "pythonpath-presence-bit-is-true",
    "httpx_not_preloaded": "httpx-module-was-preloaded-before-marked-import",
    "openai_not_preloaded": "openai-module-was-preloaded-before-marked-import",
    "python_under_repository_venv": "python-interpreter-is-not-repository-venv",
    "python_preimport_binding_stable": "python-executable-binding-changed-before-import",
    "python_binding_stable": "python-executable-binding-changed-during-probe",
    "openai_under_repository_venv": "openai-module-is-not-repository-venv",
    "httpx_under_repository_venv": "httpx-module-is-not-repository-venv",
    "openai_origin_stable_before_import": "openai-module-origin-changed-before-import",
    "httpx_origin_stable_before_import": "httpx-module-origin-changed-before-import",
    "openai_preimport_binding_stable": "openai-module-binding-changed-before-import",
    "httpx_preimport_binding_stable": "httpx-module-binding-changed-before-import",
    "openai_preimport_versions_stable": "openai-module-version-changed-before-import",
    "httpx_preimport_versions_stable": "httpx-module-version-changed-before-import",
    "openai_immediate_import_binding_stable": (
        "openai-module-binding-changed-immediately-before-import"
    ),
    "httpx_immediate_import_binding_stable": (
        "httpx-module-binding-changed-immediately-before-import"
    ),
    "openai_immediate_import_versions_stable": (
        "openai-module-version-changed-immediately-before-import"
    ),
    "httpx_immediate_import_versions_stable": (
        "httpx-module-version-changed-immediately-before-import"
    ),
    "openai_origin_stable_after_probe": "openai-module-origin-changed-during-probe",
    "httpx_origin_stable_after_probe": "httpx-module-origin-changed-during-probe",
    "openai_binding_stable": "openai-module-binding-changed-during-probe",
    "httpx_binding_stable": "httpx-module-binding-changed-during-probe",
    "openai_versions_stable_after_probe": "openai-module-version-changed-during-probe",
    "httpx_versions_stable_after_probe": "httpx-module-version-changed-during-probe",
    "openai_versions_match": "openai-module-version-does-not-match-lock",
    "httpx_versions_match": "httpx-module-version-does-not-match-lock",
    "production_factory_exact": "production-openai-factory-contract-differs",
    "synthetic_probe_passed": "synthetic-no-call-probe-did-not-pass",
    "transport_dispatch_zero": "synthetic-transport-dispatch-was-not-zero",
}


def _run_full(
    root: Path,
    dependencies: SDKWorkerDependencies,
    launch: dict[str, Any],
    presence: dict[str, bool],
    python: dict[str, Any],
    python_path: Path,
    origins: dict[str, _ResolvedOrigin],
    preimport: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    import_origins = _revalidate_before_import(
        root,
        dependencies,
        python=python,
        python_path=python_path,
        origins=origins,
        modules=preimport,
    )
    httpx_not_preloaded = dependencies.module_is_preloaded("httpx") is False
    _require(httpx_not_preloaded, "D-141 httpx became preloaded before marked import")
    import_origins["httpx"] = _revalidate_module_immediately_before_import(
        root,
        "httpx",
        dependencies,
        origin=import_origins["httpx"],
        module=preimport["httpx"],
    )
    httpx_module = dependencies.import_module("httpx")
    openai_not_preloaded = dependencies.module_is_preloaded("openai") is False
    _require(openai_not_preloaded, "D-141 openai became preloaded before marked import")
    import_origins["openai"] = _revalidate_module_immediately_before_import(
        root,
        "openai",
        dependencies,
        origin=import_origins["openai"],
        module=preimport["openai"],
    )
    openai_module = dependencies.import_module("openai")
    modules = {
        "openai": _loaded_module(root, "openai", openai_module, preimport["openai"]),
        "httpx": _loaded_module(root, "httpx", httpx_module, preimport["httpx"]),
    }
    factory = _factory_contract(
        root,
        dependencies.expected_committed_source_bindings["model"],
    )
    probe = _synthetic_probe(openai_module, httpx_module)
    _revalidate_after_probe(
        root,
        dependencies,
        python=python,
        python_path=python_path,
        origins=import_origins,
        modules=modules,
    )
    _stable_committed_read(
        root,
        dependencies.expected_committed_source_bindings["model"],
        label="model final",
    )
    factory_exact = all(
        value is True for key, value in factory.items() if key != "checked_in_official_base_url"
    )
    checks = {
        "exact_launch_contract": launch == EXACT_LAUNCH_CONTRACT,
        "openai_api_key_present": presence["OPENAI_API_KEY"],
        "pythonhome_absent": not presence["PYTHONHOME"],
        "pythonpath_absent": not presence["PYTHONPATH"],
        "httpx_not_preloaded": httpx_not_preloaded,
        "openai_not_preloaded": openai_not_preloaded,
        "python_under_repository_venv": python["under_repository_venv"],
        "python_preimport_binding_stable": python["preimport_binding_stable"],
        "python_binding_stable": python["binding_stable"],
        "openai_under_repository_venv": modules["openai"]["under_repository_venv"],
        "httpx_under_repository_venv": modules["httpx"]["under_repository_venv"],
        "openai_origin_stable_before_import": modules["openai"]["origin_stable_before_import"],
        "httpx_origin_stable_before_import": modules["httpx"]["origin_stable_before_import"],
        "openai_preimport_binding_stable": modules["openai"]["preimport_binding_stable"],
        "httpx_preimport_binding_stable": modules["httpx"]["preimport_binding_stable"],
        "openai_preimport_versions_stable": modules["openai"]["preimport_versions_stable"],
        "httpx_preimport_versions_stable": modules["httpx"]["preimport_versions_stable"],
        "openai_immediate_import_binding_stable": modules["openai"][
            "immediate_import_binding_stable"
        ],
        "httpx_immediate_import_binding_stable": modules["httpx"][
            "immediate_import_binding_stable"
        ],
        "openai_immediate_import_versions_stable": modules["openai"][
            "immediate_import_versions_stable"
        ],
        "httpx_immediate_import_versions_stable": modules["httpx"][
            "immediate_import_versions_stable"
        ],
        "openai_origin_stable_after_probe": modules["openai"]["origin_stable_after_probe"],
        "httpx_origin_stable_after_probe": modules["httpx"]["origin_stable_after_probe"],
        "openai_binding_stable": modules["openai"]["binding_stable"],
        "httpx_binding_stable": modules["httpx"]["binding_stable"],
        "openai_versions_stable_after_probe": modules["openai"]["versions_stable_after_probe"],
        "httpx_versions_stable_after_probe": modules["httpx"]["versions_stable_after_probe"],
        "openai_versions_match": modules["openai"]["versions_match"],
        "httpx_versions_match": modules["httpx"]["versions_match"],
        "production_factory_exact": factory_exact,
        "synthetic_probe_passed": probe["passed"],
        "transport_dispatch_zero": probe["transport_dispatch_count"] == 0,
    }
    blockers = [message for name, message in _FULL_BLOCKERS.items() if not checks[name]]
    activity = _empty_activity()
    activity.update(
        {
            "eligibility_token_validation_count": 1,
            "committed_model_binding_verification_count": 2,
            "committed_lock_binding_verification_count": 8,
            "python_executable_file_binding_count": 3,
            "preloaded_module_membership_check_count": 4,
            "find_module_spec_count": 8,
            "sdk_module_file_binding_count": 8,
            "distribution_version_observation_count": 8,
            "locked_version_source_read_count": 8,
            "checked_in_factory_source_read_count": 1,
            "dynamic_module_import_count": 2,
            "synthetic_transport_dispatch_count": probe["transport_dispatch_count"],
            "openai_client_close_call_count": probe["openai_client_close_call_count"],
            "http_client_fallback_close_call_count": probe["http_client_fallback_close_call_count"],
            "http_client_closed": probe["http_client_closed"],
        }
    )
    return _result(
        stage="complete",
        launch=launch,
        presence=presence,
        committed_sources=_worker_committed_source_facts(
            dependencies,
            model_verification_count=2,
            lock_verification_count=8,
        ),
        python=python,
        modules=modules,
        factory=factory,
        probe=probe,
        checks=checks,
        blockers=blockers,
        activity=activity,
    )


def _run_worker_observation(
    *,
    repository: str | Path | None = None,
    dependencies: SDKWorkerDependencies | None = None,
) -> dict[str, Any]:
    """Run the fresh D-141 observation after its durable ACTION_STARTED marker."""

    _require(dependencies is not None, "D-141 worker dependencies are required")
    active = dependencies
    _validate_expected_committed_source_bindings(active.expected_committed_source_bindings)
    _require(
        active.bootstrap_helper_binding_verified is True
        and active.bootstrap_audit_hook_installed is True,
        "D-141 bootstrap evidence differs",
    )
    _validate_zero_guard_counters(active.bootstrap_guard_counters, label="bootstrap")
    launch = dict(active.launch_contract())
    if launch != EXACT_LAUNCH_CONTRACT:
        return _result(
            stage="launch",
            launch=launch,
            presence=None,
            committed_sources=_worker_committed_source_facts(
                active,
                model_verification_count=0,
                lock_verification_count=0,
            ),
            python=None,
            modules=None,
            factory=None,
            probe=None,
            checks={"exact_launch_contract": False},
            blockers=["exact-python-launch-flags-differ"],
            activity=_empty_activity(),
        )
    presence = {"OPENAI_API_KEY": True, "PYTHONHOME": False, "PYTHONPATH": False}
    root = _repo_root(repository)
    python, python_path = _python_observation(root, active)
    if python_path is None:
        activity = _empty_activity()
        activity["eligibility_token_validation_count"] = 1
        return _result(
            stage="python",
            launch=launch,
            presence=presence,
            committed_sources=_worker_committed_source_facts(
                active,
                model_verification_count=0,
                lock_verification_count=0,
            ),
            python=python,
            modules=None,
            factory=None,
            probe=None,
            checks={"python_under_repository_venv": False},
            blockers=[
                "python-interpreter-is-not-repository-venv",
                "sdk-import-and-probe-suppressed-by-python-provenance",
            ],
            activity=activity,
        )
    python_before = active.file_binding(python_path)
    _validate_file_binding(python_before, label="Python executable")
    python["file_binding_before"] = python_before
    preloaded = {
        "httpx_preloaded_before_phase_import": active.module_is_preloaded("httpx"),
        "openai_preloaded_before_phase_import": active.module_is_preloaded("openai"),
    }
    _require(all(type(bit) is bool for bit in preloaded.values()), "D-141 preloaded bits differ")
    if any(preloaded.values()):
        activity = _empty_activity()
        activity.update(
            {
                "eligibility_token_validation_count": 1,
                "python_executable_file_binding_count": 1,
                "preloaded_module_membership_check_count": 2,
            }
        )
        return _result(
            stage="module-preloaded",
            launch=launch,
            presence=presence,
            committed_sources=_worker_committed_source_facts(
                active,
                model_verification_count=0,
                lock_verification_count=0,
            ),
            python=python,
            modules=preloaded,
            factory=None,
            probe=None,
            checks={
                "httpx_not_preloaded": not preloaded["httpx_preloaded_before_phase_import"],
                "openai_not_preloaded": not preloaded["openai_preloaded_before_phase_import"],
            },
            blockers=[
                *(
                    f"{name}-module-was-preloaded-before-marked-import"
                    for name in ("httpx", "openai")
                    if preloaded[f"{name}_preloaded_before_phase_import"]
                ),
                "sdk-import-suppressed-by-preloaded-module-state",
            ],
            activity=activity,
        )
    origins = {
        "httpx": _resolve_origin(root, "httpx", active),
        "openai": _resolve_origin(root, "openai", active),
    }
    if not all(origin.safe for origin in origins.values()):
        activity = _empty_activity()
        activity.update(
            {
                "eligibility_token_validation_count": 1,
                "python_executable_file_binding_count": 1,
                "preloaded_module_membership_check_count": 2,
                "find_module_spec_count": sum(
                    origin.find_spec_performed for origin in origins.values()
                ),
            }
        )
        module_bits = {
            f"{name}_origin_is_repository_venv": origins[name].safe for name in ("openai", "httpx")
        } | {
            f"{name}_find_module_spec_performed": origins[name].find_spec_performed
            for name in ("openai", "httpx")
        }
        return _result(
            stage="module-origin",
            launch=launch,
            presence=presence,
            committed_sources=_worker_committed_source_facts(
                active,
                model_verification_count=0,
                lock_verification_count=0,
            ),
            python=python,
            modules=module_bits,
            factory=None,
            probe=None,
            checks={
                key: value for key, value in module_bits.items() if key.endswith("repository_venv")
            },
            blockers=[
                *(
                    f"{name}-module-origin-is-not-repository-venv"
                    for name in ("openai", "httpx")
                    if not origins[name].safe
                ),
                "sdk-import-and-probe-suppressed-by-module-origin-provenance",
            ],
            activity=activity,
        )
    preimport = {
        "httpx": _bind_preimport_module(root, origins["httpx"], active),
        "openai": _bind_preimport_module(root, origins["openai"], active),
    }
    if not all(module["versions_match"] for module in preimport.values()):
        activity = _empty_activity()
        activity.update(
            {
                "eligibility_token_validation_count": 1,
                "python_executable_file_binding_count": 1,
                "preloaded_module_membership_check_count": 2,
                "find_module_spec_count": 2,
                "sdk_module_file_binding_count": 2,
                "distribution_version_observation_count": 2,
                "locked_version_source_read_count": 2,
                "committed_lock_binding_verification_count": 2,
            }
        )
        return _result(
            stage="module-version",
            launch=launch,
            presence=presence,
            committed_sources=_worker_committed_source_facts(
                active,
                model_verification_count=0,
                lock_verification_count=2,
            ),
            python=python,
            modules=preimport,
            factory=None,
            probe=None,
            checks={
                f"{name}_versions_match": preimport[name]["versions_match"]
                for name in ("openai", "httpx")
            },
            blockers=[
                *(
                    f"{name}-module-version-does-not-match-lock"
                    for name in ("openai", "httpx")
                    if not preimport[name]["versions_match"]
                ),
                "sdk-import-and-probe-suppressed-by-module-version-provenance",
            ],
            activity=activity,
        )
    return _run_full(
        root,
        active,
        launch,
        presence,
        python,
        python_path,
        origins,
        preimport,
    )


def _expected_activity(**updates: Any) -> dict[str, Any]:
    value = _empty_activity()
    value.update(updates)
    return value


def _validate_activity_shape(value: Any) -> None:
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_ACTIVITY_KEYS)),
        "D-141 worker activity fields differ",
    )
    for key, count in value.items():
        if key == "http_client_closed":
            _require(count is None or type(count) is bool, "D-141 worker close flag differs")
        else:
            _require(
                type(count) is int and count >= 0,
                f"D-141 worker activity differs: {key}",
            )


def _validate_safe_relative(value: Any, *, label: str) -> None:
    _require(isinstance(value, str) and bool(value) and "\\" not in value, label)
    path = PurePosixPath(value)
    _require(
        not path.is_absolute()
        and len(path.parts) >= 2
        and path.parts[0] == ".venv"
        and ".." not in path.parts,
        f"D-141 {label} escapes repository venv",
    )


def _validate_python_observation(value: Any, *, stage: str) -> None:
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_PYTHON_KEYS)),
        "D-141 worker Python fields differ",
    )
    _require(isinstance(value["version"], str) and bool(value["version"]), "D-141 Python version")
    if stage == "python":
        _require(
            value["repository_relative_path"] is None
            and value["under_repository_venv"] is False
            and all(value[key] is None for key in _PYTHON_KEYS[3:]),
            "D-141 unsafe Python observation differs",
        )
        return
    _validate_safe_relative(value["repository_relative_path"], label="Python relative path")
    _require(value["under_repository_venv"] is True, "D-141 Python venv bit differs")
    _validate_file_binding(value["file_binding_before"], label="Python before")
    if stage != "complete":
        _require(
            all(value[key] is None for key in _PYTHON_KEYS[4:]),
            "D-141 pre-import Python observation differs",
        )
        return
    _validate_file_binding(value["file_binding_preimport_recheck"], label="Python preimport")
    _validate_file_binding(value["file_binding_after"], label="Python after")
    expected_preimport = value["file_binding_before"] == value["file_binding_preimport_recheck"]
    expected_after = value["file_binding_before"] == value["file_binding_after"]
    _require(
        value["preimport_binding_stable"] is expected_preimport
        and expected_preimport is True
        and value["binding_stable"] is expected_after
        and value["under_repository_venv_after_probe"] is True,
        "D-141 Python stability facts differ",
    )


def _validate_module_observation(value: Any, *, name: str, complete: bool) -> None:
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_MODULE_KEYS)),
        f"D-141 {name} module fields differ",
    )
    _require(value["distribution_name"] == name, f"D-141 {name} distribution differs")
    for key in ("distribution_version", "module_version", "locked_version"):
        _require(value[key] is None or isinstance(value[key], str), f"D-141 {name} {key}")
    _validate_safe_relative(
        value["repository_relative_path"], label=f"{name} repository relative path"
    )
    _require(value["under_repository_venv"] is True, f"D-141 {name} venv bit differs")
    _validate_file_binding(value["file_binding_before"], label=f"{name} before")
    if not complete:
        _require(value["module_version"] is None, f"D-141 {name} imported too early")
        nullable = (
            "file_binding_preimport_recheck",
            "file_binding_immediate_import_recheck",
            "file_binding_after",
            "preimport_binding_stable",
            "immediate_import_binding_stable",
            "binding_stable",
            "distribution_version_preimport_recheck",
            "locked_version_preimport_recheck",
            "preimport_versions_stable",
            "distribution_version_immediate_import_recheck",
            "locked_version_immediate_import_recheck",
            "immediate_import_versions_stable",
            "distribution_version_after",
            "locked_version_after",
            "versions_stable_after_probe",
            "origin_stable_before_import",
            "origin_stable_immediately_before_import",
            "origin_stable_after_probe",
        )
        _require(all(value[key] is None for key in nullable), f"D-141 {name} early facts differ")
        expected = (
            isinstance(value["distribution_version"], str)
            and value["distribution_version"] == value["locked_version"]
        )
        _require(value["versions_match"] is expected, f"D-141 {name} versions differ")
        return
    for key, label in (
        ("file_binding_preimport_recheck", "preimport"),
        ("file_binding_immediate_import_recheck", "immediate import"),
        ("file_binding_after", "after"),
    ):
        _validate_file_binding(value[key], label=f"{name} {label}")
    for key in (
        "distribution_version_preimport_recheck",
        "locked_version_preimport_recheck",
        "distribution_version_immediate_import_recheck",
        "locked_version_immediate_import_recheck",
        "distribution_version_after",
        "locked_version_after",
    ):
        _require(value[key] is None or isinstance(value[key], str), f"D-141 {name} {key}")
    expected_pre_binding = value["file_binding_before"] == value["file_binding_preimport_recheck"]
    expected_immediate_binding = (
        value["file_binding_before"] == value["file_binding_immediate_import_recheck"]
    )
    expected_after_binding = value["file_binding_before"] == value["file_binding_after"]
    expected_pre_versions = (
        isinstance(value["distribution_version_preimport_recheck"], str)
        and value["distribution_version_preimport_recheck"]
        == value["distribution_version"]
        == value["locked_version"]
        == value["locked_version_preimport_recheck"]
    )
    expected_immediate_versions = (
        isinstance(value["distribution_version_immediate_import_recheck"], str)
        and value["distribution_version_immediate_import_recheck"]
        == value["distribution_version"]
        == value["locked_version"]
        == value["locked_version_immediate_import_recheck"]
    )
    expected_after_versions = (
        isinstance(value["distribution_version_after"], str)
        and value["distribution_version_after"]
        == value["distribution_version"]
        == value["locked_version"]
        == value["locked_version_after"]
    )
    expected_versions = (
        isinstance(value["distribution_version"], str)
        and value["distribution_version"] == value["module_version"] == value["locked_version"]
    )
    _require(
        value["preimport_binding_stable"] is expected_pre_binding
        and expected_pre_binding is True
        and value["immediate_import_binding_stable"] is expected_immediate_binding
        and expected_immediate_binding is True
        and value["binding_stable"] is expected_after_binding
        and value["preimport_versions_stable"] is expected_pre_versions
        and expected_pre_versions is True
        and value["immediate_import_versions_stable"] is expected_immediate_versions
        and expected_immediate_versions is True
        and value["versions_stable_after_probe"] is expected_after_versions
        and value["origin_stable_before_import"] is True
        and value["origin_stable_immediately_before_import"] is True
        and value["origin_stable_after_probe"] is True
        and value["versions_match"] is expected_versions,
        f"D-141 {name} canonical provenance differs",
    )


def _validate_factory_observation(value: Any) -> bool:
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_FACTORY_KEYS)),
        "D-141 factory fields differ",
    )
    checked = value["checked_in_official_base_url"]
    _require(checked is None or isinstance(checked, str), "D-141 factory URL fact differs")
    _require(
        all(type(value[key]) is bool for key in _FACTORY_KEYS[1:]),
        "D-141 factory booleans differ",
    )
    _require(
        value["official_base_url_exact"] is (checked == OFFICIAL_API_BASE_URL),
        "D-141 factory URL derivation differs",
    )
    return all(value[key] is True for key in _FACTORY_KEYS[1:])


def _validate_probe_observation(value: Any) -> bool:
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_PROBE_KEYS)),
        "D-141 probe fields differ",
    )
    _require(
        value["transport_kind"] == "httpx.MockTransport-reject-dispatch"
        and value["fixed_nonsecret_placeholder_used"] is True
        and value["ambient_credential_value_used"] is False
        and value["official_base_url"] == OFFICIAL_API_BASE_URL
        and type(value["base_url_exact"]) is bool
        and value["trust_env"] is False
        and type(value["max_retries"]) is int
        and value["max_retries"] == 0
        and type(value["observed_max_retries_zero"]) is bool
        and type(value["transport_dispatch_count"]) is int
        and value["transport_dispatch_count"] == 0
        and type(value["openai_client_close_call_count"]) is int
        and value["openai_client_close_call_count"] == 1
        and type(value["http_client_fallback_close_call_count"]) is int
        and value["http_client_fallback_close_call_count"] in (0, 1)
        and value["http_client_closed"] is True
        and type(value["passed"]) is bool,
        "D-141 probe contract differs",
    )
    expected = value["base_url_exact"] and value["observed_max_retries_zero"]
    _require(value["passed"] is expected, "D-141 probe pass derivation differs")
    return expected


def _validate_worker_committed_source_facts(
    value: Any,
    activity: Mapping[str, Any],
) -> None:
    _require(
        isinstance(value, dict) and tuple(value) == ("helper", "lock", "model"),
        "D-141 worker committed source names differ",
    )
    expected_counts = {
        "helper": activity["committed_helper_bootstrap_verification_count"],
        "model": activity["committed_model_binding_verification_count"],
        "lock": activity["committed_lock_binding_verification_count"],
    }
    for name in ("helper", "model", "lock"):
        fact = value[name]
        _require(
            isinstance(fact, dict)
            and tuple(fact)
            == (
                "every_verification_matched",
                "expected_committed_file_bytes",
                "expected_committed_file_sha256",
                "expected_committed_linklike",
                "repository_relative_path",
                "verification_count",
            )
            and fact["repository_relative_path"] == _PARENT_SOURCE_PATHS[name]
            and type(fact["expected_committed_file_bytes"]) is int
            and fact["expected_committed_file_bytes"] > 0
            and isinstance(fact["expected_committed_file_sha256"], str)
            and _SHA256.fullmatch(fact["expected_committed_file_sha256"]) is not None
            and fact["expected_committed_linklike"] is False
            and type(fact["verification_count"]) is int
            and fact["verification_count"] == expected_counts[name]
            and fact["every_verification_matched"] is (True if expected_counts[name] > 0 else None),
            f"D-141 worker committed {name} source facts differ",
        )
    _require(expected_counts["helper"] == 1, "D-141 helper bootstrap verification count differs")


def _validate_worker_observation(value: Any) -> dict[str, Any]:
    """Replay exact stage facts without reading environment values or importing an SDK."""

    _require_canonical_mapping_order(value, label="worker canonical JSON")
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_ROOT_KEYS)),
        "D-141 worker fields differ",
    )
    _require(value["schema_version"] == SDK_WORKER_OBSERVATION_SCHEMA, "D-141 worker schema")
    _require(value["phase"] == SDK_PHASE, "D-141 worker phase differs")
    _require(value["observer_contract"] == _observer_contract(), "D-141 worker contract")
    observation = value["observation"]
    _require(
        isinstance(observation, dict) and tuple(observation) == tuple(sorted(_OBSERVATION_KEYS)),
        "D-141 worker observation fields differ",
    )
    stage = observation["stage"]
    _require(
        stage
        in {
            "launch",
            "python",
            "module-preloaded",
            "module-origin",
            "module-version",
            "complete",
        },
        "D-141 worker stage differs",
    )
    launch = observation["launch_contract"]
    _require(
        isinstance(launch, dict)
        and tuple(launch) == tuple(sorted(EXACT_LAUNCH_CONTRACT))
        and all(type(bit) is bool for bit in launch.values()),
        "D-141 worker launch fields differ",
    )
    activity = value["activity"]
    _validate_activity_shape(activity)
    presence = observation["parent_eligibility_bits"]
    committed_sources = observation["committed_source_bindings"]
    python = observation["python"]
    modules = observation["modules"]
    factory = observation["production_client_factory"]
    probe = observation["synthetic_probe"]
    checks = observation["checks"]
    _validate_worker_committed_source_facts(committed_sources, activity)
    if stage == "launch":
        _require(launch != EXACT_LAUNCH_CONTRACT, "D-141 worker launch lacks mismatch")
        expected_checks = {"exact_launch_contract": False}
        expected_blockers = ["exact-python-launch-flags-differ"]
        expected_activity = _expected_activity()
        _require(
            presence is None
            and python is None
            and modules is None
            and factory is None
            and probe is None,
            "D-141 worker launch branch observed later facts",
        )
    else:
        validate_d141_sdk_launch_contract(launch)
        _require(
            isinstance(presence, dict)
            and tuple(presence) == tuple(sorted(SDK_ENVIRONMENT_NAMES))
            and all(type(bit) is bool for bit in presence.values()),
            "D-141 worker presence fields differ",
        )
        _require(
            presence == {"OPENAI_API_KEY": True, "PYTHONHOME": False, "PYTHONPATH": False},
            "D-141 worker eligibility token facts differ",
        )
        presence_checks = {
            "openai_api_key_present": presence["OPENAI_API_KEY"],
            "pythonhome_absent": not presence["PYTHONHOME"],
            "pythonpath_absent": not presence["PYTHONPATH"],
        }
        if True:
            _require(python is not None, "D-141 worker Python observation missing")
            _validate_python_observation(python, stage=stage)
            if stage == "python":
                expected_checks = {"python_under_repository_venv": False}
                expected_blockers = [
                    "python-interpreter-is-not-repository-venv",
                    "sdk-import-and-probe-suppressed-by-python-provenance",
                ]
                expected_activity = _expected_activity(eligibility_token_validation_count=1)
                _require(
                    modules is None and factory is None and probe is None,
                    "D-141 worker Python branch observed later facts",
                )
            elif stage == "module-preloaded":
                expected_module_keys = (
                    "httpx_preloaded_before_phase_import",
                    "openai_preloaded_before_phase_import",
                )
                _require(
                    isinstance(modules, dict)
                    and tuple(modules) == tuple(sorted(expected_module_keys))
                    and all(type(bit) is bool for bit in modules.values())
                    and any(modules.values()),
                    "D-141 worker preloaded facts differ",
                )
                expected_checks = {
                    "httpx_not_preloaded": not modules[expected_module_keys[0]],
                    "openai_not_preloaded": not modules[expected_module_keys[1]],
                }
                expected_blockers = [
                    *(
                        f"{name}-module-was-preloaded-before-marked-import"
                        for name in ("httpx", "openai")
                        if modules[f"{name}_preloaded_before_phase_import"]
                    ),
                    "sdk-import-suppressed-by-preloaded-module-state",
                ]
                expected_activity = _expected_activity(
                    eligibility_token_validation_count=1,
                    python_executable_file_binding_count=1,
                    preloaded_module_membership_check_count=2,
                )
                _require(factory is None and probe is None, "D-141 worker preloaded tail differs")
            elif stage == "module-origin":
                expected_module_keys = (
                    "openai_origin_is_repository_venv",
                    "httpx_origin_is_repository_venv",
                    "openai_find_module_spec_performed",
                    "httpx_find_module_spec_performed",
                )
                _require(
                    isinstance(modules, dict)
                    and tuple(modules) == tuple(sorted(expected_module_keys))
                    and all(type(bit) is bool for bit in modules.values()),
                    "D-141 worker module-origin facts differ",
                )
                for name in ("openai", "httpx"):
                    _require(
                        not modules[f"{name}_origin_is_repository_venv"]
                        or modules[f"{name}_find_module_spec_performed"],
                        f"D-141 worker {name} safe origin lacks spec query",
                    )
                _require(
                    not modules["openai_origin_is_repository_venv"]
                    or not modules["httpx_origin_is_repository_venv"],
                    "D-141 worker module-origin stage lacks unsafe origin",
                )
                expected_checks = {
                    "openai_origin_is_repository_venv": modules["openai_origin_is_repository_venv"],
                    "httpx_origin_is_repository_venv": modules["httpx_origin_is_repository_venv"],
                }
                expected_blockers = [
                    *(
                        f"{name}-module-origin-is-not-repository-venv"
                        for name in ("openai", "httpx")
                        if not modules[f"{name}_origin_is_repository_venv"]
                    ),
                    "sdk-import-and-probe-suppressed-by-module-origin-provenance",
                ]
                expected_activity = _expected_activity(
                    eligibility_token_validation_count=1,
                    python_executable_file_binding_count=1,
                    preloaded_module_membership_check_count=2,
                    find_module_spec_count=sum(
                        int(modules[f"{name}_find_module_spec_performed"])
                        for name in ("openai", "httpx")
                    ),
                )
                _require(factory is None and probe is None, "D-141 worker origin tail differs")
            elif stage == "module-version":
                _require(
                    isinstance(modules, dict) and tuple(modules) == ("httpx", "openai"),
                    "D-141 worker module-version fields differ",
                )
                for name in ("httpx", "openai"):
                    _validate_module_observation(modules[name], name=name, complete=False)
                expected_checks = {
                    f"{name}_versions_match": modules[name]["versions_match"]
                    for name in ("openai", "httpx")
                }
                _require(
                    not all(expected_checks.values()),
                    "D-141 worker module-version stage lacks mismatch",
                )
                expected_blockers = [
                    *(
                        f"{name}-module-version-does-not-match-lock"
                        for name in ("openai", "httpx")
                        if not modules[name]["versions_match"]
                    ),
                    "sdk-import-and-probe-suppressed-by-module-version-provenance",
                ]
                expected_activity = _expected_activity(
                    eligibility_token_validation_count=1,
                    committed_lock_binding_verification_count=2,
                    python_executable_file_binding_count=1,
                    preloaded_module_membership_check_count=2,
                    find_module_spec_count=2,
                    sdk_module_file_binding_count=2,
                    distribution_version_observation_count=2,
                    locked_version_source_read_count=2,
                )
                _require(factory is None and probe is None, "D-141 worker version tail differs")
            else:
                _require(
                    isinstance(modules, dict) and tuple(modules) == ("httpx", "openai"),
                    "D-141 worker complete module fields differ",
                )
                for name in ("openai", "httpx"):
                    _validate_module_observation(modules[name], name=name, complete=True)
                factory_exact = _validate_factory_observation(factory)
                probe_passed = _validate_probe_observation(probe)
                expected_checks = {
                    "exact_launch_contract": True,
                    **presence_checks,
                    "httpx_not_preloaded": True,
                    "openai_not_preloaded": True,
                    "python_under_repository_venv": True,
                    "python_preimport_binding_stable": python["preimport_binding_stable"],
                    "python_binding_stable": python["binding_stable"],
                    "openai_under_repository_venv": True,
                    "httpx_under_repository_venv": True,
                    "openai_origin_stable_before_import": modules["openai"][
                        "origin_stable_before_import"
                    ],
                    "httpx_origin_stable_before_import": modules["httpx"][
                        "origin_stable_before_import"
                    ],
                    "openai_preimport_binding_stable": modules["openai"][
                        "preimport_binding_stable"
                    ],
                    "httpx_preimport_binding_stable": modules["httpx"]["preimport_binding_stable"],
                    "openai_preimport_versions_stable": modules["openai"][
                        "preimport_versions_stable"
                    ],
                    "httpx_preimport_versions_stable": modules["httpx"][
                        "preimport_versions_stable"
                    ],
                    "openai_immediate_import_binding_stable": modules["openai"][
                        "immediate_import_binding_stable"
                    ],
                    "httpx_immediate_import_binding_stable": modules["httpx"][
                        "immediate_import_binding_stable"
                    ],
                    "openai_immediate_import_versions_stable": modules["openai"][
                        "immediate_import_versions_stable"
                    ],
                    "httpx_immediate_import_versions_stable": modules["httpx"][
                        "immediate_import_versions_stable"
                    ],
                    "openai_origin_stable_after_probe": modules["openai"][
                        "origin_stable_after_probe"
                    ],
                    "httpx_origin_stable_after_probe": modules["httpx"][
                        "origin_stable_after_probe"
                    ],
                    "openai_binding_stable": modules["openai"]["binding_stable"],
                    "httpx_binding_stable": modules["httpx"]["binding_stable"],
                    "openai_versions_stable_after_probe": modules["openai"][
                        "versions_stable_after_probe"
                    ],
                    "httpx_versions_stable_after_probe": modules["httpx"][
                        "versions_stable_after_probe"
                    ],
                    "openai_versions_match": modules["openai"]["versions_match"],
                    "httpx_versions_match": modules["httpx"]["versions_match"],
                    "production_factory_exact": factory_exact,
                    "synthetic_probe_passed": probe_passed,
                    "transport_dispatch_zero": True,
                }
                expected_blockers = [
                    message for name, message in _FULL_BLOCKERS.items() if not expected_checks[name]
                ]
                expected_activity = _expected_activity(
                    eligibility_token_validation_count=1,
                    committed_model_binding_verification_count=2,
                    committed_lock_binding_verification_count=8,
                    python_executable_file_binding_count=3,
                    preloaded_module_membership_check_count=4,
                    find_module_spec_count=8,
                    sdk_module_file_binding_count=8,
                    distribution_version_observation_count=8,
                    locked_version_source_read_count=8,
                    checked_in_factory_source_read_count=1,
                    dynamic_module_import_count=2,
                    synthetic_transport_dispatch_count=0,
                    openai_client_close_call_count=probe["openai_client_close_call_count"],
                    http_client_fallback_close_call_count=probe[
                        "http_client_fallback_close_call_count"
                    ],
                    http_client_closed=True,
                )
    _require(checks == expected_checks, "D-141 worker checks differ")
    _require(value["blockers"] == expected_blockers, "D-141 worker blockers differ")
    _require(activity == expected_activity, "D-141 worker activity differs")
    passed = stage == "complete" and not expected_blockers
    _require(value["passed"] is passed, "D-141 worker pass flag differs")
    _require(
        value["status"] == (SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS),
        "D-141 worker status differs",
    )
    return value


def _parent_observer_contract() -> dict[str, Any]:
    return _canonicalize_json(
        {
            "exact_launch_contract": EXACT_LAUNCH_CONTRACT,
            "launcher_source_contract": LAUNCHER_SOURCE_CONTRACT,
            "parent_environment_contract": {
                "presence_names": list(SDK_ENVIRONMENT_NAMES),
                "membership_check_count": 3,
                "value_access_authorized": False,
                "value_read_count": 0,
                "dotenv_read_authorized": False,
                "environment_override_count": 0,
            },
            "parent_sdk_dynamic_import_count": 0,
            "isolated_child_contract": ISOLATED_CHILD_CONTRACT,
        }
    )


def _parent_empty_activity() -> dict[str, Any]:
    return {
        "launch_contract_check_count": 1,
        "environment_presence_check_count": 0,
        "environment_value_read_count": 0,
        "dotenv_read_count": 0,
        "parent_sdk_dynamic_import_count": 0,
        "parent_file_binding_count": 0,
        "child_process_start_count": 0,
        "child_process_kill_count": 0,
        "child_timeout_count": 0,
        "child_stdout_overflow_count": 0,
        "child_stderr_overflow_count": 0,
        "child_stdout_bytes": 0,
        "child_stderr_bytes": 0,
        "child_environment_entry_forward_count": 0,
        "child_credential_value_forward_count": 0,
        "parent_network_call_count": 0,
        "provider_evaluator_or_agent_call_count": 0,
    }


def _parent_result(
    *,
    stage: str,
    launch: dict[str, Any],
    presence: dict[str, bool] | None,
    python: dict[str, Any] | None,
    source_bindings: dict[str, Any] | None,
    isolated_child: dict[str, Any] | None,
    checks: dict[str, bool],
    blockers: list[str],
    activity: dict[str, Any],
) -> dict[str, Any]:
    passed = stage == "complete" and not blockers
    value = {
        "schema_version": SDK_OBSERVATION_SCHEMA,
        "phase": SDK_PHASE,
        "status": SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS,
        "observer_contract": _parent_observer_contract(),
        "observation": {
            "stage": stage,
            "launch_contract": launch,
            "environment_presence_bits": presence,
            "python": python,
            "source_bindings": source_bindings,
            "isolated_child": isolated_child,
            "checks": checks,
        },
        "blockers": blockers,
        "activity": activity,
        "passed": passed,
    }
    return validate_d141_sdk_no_call_successor_observation(_canonicalize_json(value))


def _parent_python_observation(
    root: Path,
    dependencies: SDKIsolatedSuccessorDependencies,
) -> tuple[dict[str, Any], Path | None]:
    safe = False
    relative: str | None = None
    selected: Path | None = None
    try:
        resolved_root, venv = _canonical_repo_venv(root)
        candidate = _strict_nonlink_repo_path(
            resolved_root,
            dependencies.python_executable,
            boundary=venv,
            label="parent Python executable",
        )
        safe = True
        if safe:
            selected = candidate
            relative = candidate.relative_to(resolved_root).as_posix()
    except (OSError, RuntimeError, ValueError):
        pass
    return (
        {
            "version": dependencies.python_version,
            "repository_relative_path": relative,
            "under_repository_venv": safe,
            "file_binding_before": None,
            "file_binding_after": None,
            "binding_stable": None,
        },
        selected,
    )


_PARENT_SOURCE_PATHS = {
    "helper": "patchloop/evals/d141_sdk_no_call_successor.py",
    "model": "patchloop/agent/model.py",
    "lock": "uv.lock",
}


def _validate_expected_committed_source_bindings(
    value: Any,
) -> dict[str, dict[str, Any]]:
    _require(
        isinstance(value, dict) and set(value) == {"helper", "model", "lock"},
        "D-141 expected committed source binding names differ",
    )
    expected: dict[str, dict[str, Any]] = {}
    for name in ("helper", "model", "lock"):
        binding = value[name]
        _require(
            isinstance(binding, dict)
            and set(binding)
            == {"repository_relative_path", "file_bytes", "file_sha256", "linklike"}
            and binding["repository_relative_path"] == _PARENT_SOURCE_PATHS[name]
            and type(binding["file_bytes"]) is int
            and binding["file_bytes"] > 0
            and isinstance(binding["file_sha256"], str)
            and _SHA256.fullmatch(binding["file_sha256"]) is not None
            and binding["linklike"] is False,
            f"D-141 expected committed {name} source binding differs",
        )
        expected[name] = dict(binding)
    return expected


def _bind_parent_sources(
    root: Path,
    dependencies: SDKIsolatedSuccessorDependencies,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    resolved_root = root.resolve(strict=True)
    for name, relative in _PARENT_SOURCE_PATHS.items():
        selected = _strict_nonlink_repo_path(
            resolved_root,
            resolved_root / Path(relative),
            boundary=resolved_root,
            label=f"parent {name} source",
        )
        binding = dependencies.file_binding(selected)
        _validate_file_binding(binding, label=f"parent {name} source")
        result[name] = {
            "repository_relative_path": relative,
            "file_binding": binding,
        }
    return result


def _source_binding_facts_before_child(
    expected: Mapping[str, Mapping[str, Any]],
    before: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        name: {
            "repository_relative_path": _PARENT_SOURCE_PATHS[name],
            "expected_committed_file_bytes": expected[name]["file_bytes"],
            "expected_committed_file_sha256": expected[name]["file_sha256"],
            "expected_committed_linklike": False,
            "file_binding_before": before[name]["file_binding"],
            "file_binding_after": None,
            "committed_binding_match_before": (
                before[name]["file_binding"]["file_bytes"] == expected[name]["file_bytes"]
                and before[name]["file_binding"]["file_sha256"] == expected[name]["file_sha256"]
                and before[name]["file_binding"]["linklike"] is False
            ),
            "binding_stable": None,
        }
        for name in ("helper", "model", "lock")
    }


def _complete_parent_sources(
    expected: Mapping[str, Mapping[str, Any]],
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        name: {
            "repository_relative_path": _PARENT_SOURCE_PATHS[name],
            "expected_committed_file_bytes": expected[name]["file_bytes"],
            "expected_committed_file_sha256": expected[name]["file_sha256"],
            "expected_committed_linklike": False,
            "file_binding_before": before[name]["file_binding"],
            "file_binding_after": after[name]["file_binding"],
            "committed_binding_match_before": (
                before[name]["file_binding"]["file_bytes"] == expected[name]["file_bytes"]
                and before[name]["file_binding"]["file_sha256"] == expected[name]["file_sha256"]
                and before[name]["file_binding"]["linklike"] is False
            ),
            "binding_stable": before[name]["file_binding"] == after[name]["file_binding"],
        }
        for name in ("helper", "model", "lock")
    }


def _child_request(
    *,
    root: Path,
    helper: Path,
    python_path: Path,
    temp_root: Path,
    cwd: Path,
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]],
) -> IsolatedChildRequest:
    expected = _validate_expected_committed_source_bindings(expected_committed_source_bindings)
    return IsolatedChildRequest(
        command=(
            str(python_path),
            "-E",
            "-s",
            "-B",
            "-c",
            ISOLATED_CHILD_BOOTSTRAP,
            str(root),
            str(helper),
            str(temp_root),
            ISOLATED_CHILD_ELIGIBILITY_TOKEN,
            expected["helper"]["file_sha256"],
            str(expected["helper"]["file_bytes"]),
            expected["model"]["file_sha256"],
            str(expected["model"]["file_bytes"]),
            expected["lock"]["file_sha256"],
            str(expected["lock"]["file_bytes"]),
        ),
        cwd=cwd,
        environment_entries=(),
        timeout_seconds=ISOLATED_CHILD_TIMEOUT_SECONDS,
        stdout_limit_bytes=ISOLATED_CHILD_STDOUT_LIMIT_BYTES,
        stderr_limit_bytes=ISOLATED_CHILD_STDERR_LIMIT_BYTES,
    )


def _parse_isolated_child_execution(
    execution: IsolatedChildExecution,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(
        isinstance(execution, IsolatedChildExecution)
        and type(execution.returncode) is int
        and execution.returncode == 0
        and type(execution.stdout) is bytes
        and type(execution.stderr) is bytes
        and len(execution.stdout) <= ISOLATED_CHILD_STDOUT_LIMIT_BYTES
        and len(execution.stderr) <= ISOLATED_CHILD_STDERR_LIMIT_BYTES
        and execution.stderr == b""
        and execution.timed_out is False
        and execution.stdout_overflow is False
        and execution.stderr_overflow is False
        and type(execution.process_start_count) is int
        and execution.process_start_count == 1
        and type(execution.process_kill_count) is int
        and execution.process_kill_count == 0,
        "D-141 isolated child execution was not canonical",
    )
    try:
        decoded = execution.stdout.decode("utf-8")
        parsed = json.loads(decoded)
        worker = _validate_worker_observation(parsed)
        canonical = _compact_json_bytes(worker) + b"\n"
    except Exception:
        raise D141SDKNoCallSuccessorError("D-141 isolated child output was not canonical") from None
    _require(
        execution.stdout == canonical,
        "D-141 isolated child stdout canonical replay differs",
    )
    facts = {
        "contract": ISOLATED_CHILD_CONTRACT,
        "process_start_count": 1,
        "process_kill_count": 0,
        "returncode": 0,
        "timed_out": False,
        "stdout_overflow": False,
        "stderr_overflow": False,
        "stdout_bytes": len(execution.stdout),
        "stderr_bytes": 0,
        "canonical_stdout_replay": True,
        "environment_entry_forward_count": 0,
        "credential_value_forward_count": 0,
        "worker_observation": worker,
    }
    return worker, facts


def run_d141_sdk_no_call_successor_observation(
    *,
    repository: str | Path | None = None,
    dependencies: SDKIsolatedSuccessorDependencies | None = None,
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run parent membership checks and one isolated no-call SDK worker."""

    active = dependencies or _default_isolated_dependencies()
    launch = dict(active.launch_contract())
    if launch != EXACT_LAUNCH_CONTRACT:
        return _parent_result(
            stage="launch",
            launch=launch,
            presence=None,
            python=None,
            source_bindings=None,
            isolated_child=None,
            checks={"exact_launch_contract": False},
            blockers=["exact-python-launch-flags-differ"],
            activity=_parent_empty_activity(),
        )
    presence = {name: active.environment_present(name) for name in SDK_ENVIRONMENT_NAMES}
    _require(all(type(bit) is bool for bit in presence.values()), "D-141 presence bit type differs")
    presence_checks = {
        "openai_api_key_present": presence["OPENAI_API_KEY"],
        "pythonhome_absent": not presence["PYTHONHOME"],
        "pythonpath_absent": not presence["PYTHONPATH"],
    }
    presence_blockers = [
        *(["openai-api-key-presence-bit-is-false"] if not presence["OPENAI_API_KEY"] else []),
        *(["pythonhome-presence-bit-is-true"] if presence["PYTHONHOME"] else []),
        *(["pythonpath-presence-bit-is-true"] if presence["PYTHONPATH"] else []),
    ]
    if presence_blockers:
        activity = _parent_empty_activity()
        activity["environment_presence_check_count"] = 3
        return _parent_result(
            stage="presence",
            launch=launch,
            presence=presence,
            python=None,
            source_bindings=None,
            isolated_child=None,
            checks=presence_checks,
            blockers=[*presence_blockers, "isolated-sdk-worker-suppressed-by-presence-checks"],
            activity=activity,
        )
    root = _repo_root(repository)
    python, python_path = _parent_python_observation(root, active)
    if python_path is None:
        activity = _parent_empty_activity()
        activity["environment_presence_check_count"] = 3
        return _parent_result(
            stage="python",
            launch=launch,
            presence=presence,
            python=python,
            source_bindings=None,
            isolated_child=None,
            checks={"python_under_repository_venv": False},
            blockers=[
                "python-interpreter-is-not-repository-venv",
                "isolated-sdk-worker-suppressed-by-python-provenance",
            ],
            activity=activity,
        )
    python_before = active.file_binding(python_path)
    _validate_file_binding(python_before, label="parent Python before child")
    python["file_binding_before"] = python_before
    expected_sources = _validate_expected_committed_source_bindings(
        expected_committed_source_bindings
    )
    sources_before = _bind_parent_sources(root, active)
    source_bindings_before = _source_binding_facts_before_child(
        expected_sources,
        sources_before,
    )
    source_checks = {
        f"{name}_committed_binding_match_before": source_bindings_before[name][
            "committed_binding_match_before"
        ]
        for name in ("helper", "model", "lock")
    }
    if not all(source_checks.values()):
        activity = _parent_empty_activity()
        activity.update(
            {
                "environment_presence_check_count": 3,
                "parent_file_binding_count": 4,
            }
        )
        return _parent_result(
            stage="source",
            launch=launch,
            presence=presence,
            python=python,
            source_bindings=source_bindings_before,
            isolated_child=None,
            checks=source_checks,
            blockers=[
                *(
                    f"{name}-source-does-not-match-committed-binding"
                    for name in ("helper", "model", "lock")
                    if not source_checks[f"{name}_committed_binding_match_before"]
                ),
                "isolated-sdk-worker-suppressed-by-committed-source-binding",
            ],
            activity=activity,
        )
    helper = _strict_nonlink_repo_path(
        root,
        root / _PARENT_SOURCE_PATHS["helper"],
        boundary=root,
        label="parent helper source",
    )
    temp_root = active.child_temp_root.resolve(strict=True)
    _require(
        temp_root == D141_FIXED_TEMP_ROOT.resolve(strict=True),
        "D-141 fixed child temp root differs",
    )
    with _isolated_child_cwd(temp_root, root) as cwd:
        execution = active.run_isolated_child(
            _child_request(
                root=root,
                helper=helper,
                python_path=python_path,
                temp_root=temp_root,
                cwd=cwd,
                expected_committed_source_bindings=expected_sources,
            )
        )
    worker, child_facts = _parse_isolated_child_execution(execution)
    fresh_python, fresh_python_path = _parent_python_observation(root, active)
    _require(
        fresh_python_path == python_path
        and fresh_python["repository_relative_path"] == python["repository_relative_path"]
        and fresh_python["under_repository_venv"] is True,
        "D-141 parent Python provenance drifted after child",
    )
    python_after = active.file_binding(python_path)
    _validate_file_binding(python_after, label="parent Python after child")
    python["file_binding_after"] = python_after
    python["binding_stable"] = python_before == python_after
    sources_after = _bind_parent_sources(root, active)
    source_bindings = _complete_parent_sources(
        expected_sources,
        sources_before,
        sources_after,
    )
    checks = {
        "exact_launch_contract": True,
        **presence_checks,
        "python_under_repository_venv": True,
        "python_binding_stable": python["binding_stable"],
        **source_checks,
        "helper_source_binding_stable": source_bindings["helper"]["binding_stable"],
        "model_source_binding_stable": source_bindings["model"]["binding_stable"],
        "lock_source_binding_stable": source_bindings["lock"]["binding_stable"],
        "isolated_child_observation_passed": worker["passed"],
    }
    blockers = [
        *(
            ["python-executable-binding-changed-during-isolated-child"]
            if not checks["python_binding_stable"]
            else []
        ),
        *(
            f"{name}-source-binding-changed-during-isolated-child"
            for name in ("helper", "model", "lock")
            if not source_bindings[name]["binding_stable"]
        ),
        *worker["blockers"],
    ]
    activity = _parent_empty_activity()
    activity.update(
        {
            "environment_presence_check_count": 3,
            "parent_file_binding_count": 8,
            "child_process_start_count": 1,
            "child_process_kill_count": 0,
            "child_stdout_bytes": child_facts["stdout_bytes"],
            "child_stderr_bytes": 0,
        }
    )
    return _parent_result(
        stage="complete",
        launch=launch,
        presence=presence,
        python=python,
        source_bindings=source_bindings,
        isolated_child=child_facts,
        checks=checks,
        blockers=blockers,
        activity=activity,
    )


def _validate_parent_activity(value: Any) -> None:
    _require(
        isinstance(value, dict)
        and tuple(value) == tuple(sorted(_PARENT_ACTIVITY_KEYS))
        and all(type(count) is int and count >= 0 for count in value.values()),
        "D-141 parent activity differs",
    )


def _validate_parent_python(value: Any, *, complete: bool) -> None:
    _require(
        isinstance(value, dict)
        and tuple(value) == tuple(sorted(_PARENT_PYTHON_KEYS))
        and isinstance(value["version"], str)
        and bool(value["version"]),
        "D-141 parent Python fields differ",
    )
    if not value["under_repository_venv"]:
        _require(
            complete is False
            and value["repository_relative_path"] is None
            and value["file_binding_before"] is None
            and value["file_binding_after"] is None
            and value["binding_stable"] is None,
            "D-141 parent unsafe Python facts differ",
        )
        return
    _validate_safe_relative(value["repository_relative_path"], label="parent Python path")
    _validate_file_binding(value["file_binding_before"], label="parent Python before")
    if not complete:
        _require(
            value["file_binding_after"] is None and value["binding_stable"] is None,
            "D-141 parent Python blocked facts differ",
        )
        return
    _validate_file_binding(value["file_binding_after"], label="parent Python after")
    _require(
        value["binding_stable"] is (value["file_binding_before"] == value["file_binding_after"]),
        "D-141 parent Python stability differs",
    )


def _validate_parent_sources(
    value: Any,
    *,
    complete: bool,
) -> dict[str, dict[str, bool]]:
    _require(
        isinstance(value, dict) and tuple(value) == ("helper", "lock", "model"),
        "D-141 parent source fields differ",
    )
    committed: dict[str, bool] = {}
    stable: dict[str, bool] = {}
    for name in ("helper", "model", "lock"):
        fact = value[name]
        _require(
            isinstance(fact, dict)
            and tuple(fact)
            == (
                "binding_stable",
                "committed_binding_match_before",
                "expected_committed_file_bytes",
                "expected_committed_file_sha256",
                "expected_committed_linklike",
                "file_binding_after",
                "file_binding_before",
                "repository_relative_path",
            )
            and fact["repository_relative_path"] == _PARENT_SOURCE_PATHS[name],
            f"D-141 parent {name} source facts differ",
        )
        _require(
            type(fact["expected_committed_file_bytes"]) is int
            and fact["expected_committed_file_bytes"] > 0
            and isinstance(fact["expected_committed_file_sha256"], str)
            and _SHA256.fullmatch(fact["expected_committed_file_sha256"]) is not None
            and fact["expected_committed_linklike"] is False,
            f"D-141 parent {name} committed source facts differ",
        )
        _validate_file_binding(fact["file_binding_before"], label=f"parent {name} before")
        expected_committed = (
            fact["file_binding_before"]["file_bytes"] == fact["expected_committed_file_bytes"]
            and fact["file_binding_before"]["file_sha256"] == fact["expected_committed_file_sha256"]
            and fact["file_binding_before"]["linklike"] is False
        )
        _require(
            fact["committed_binding_match_before"] is expected_committed,
            f"D-141 parent {name} committed binding derivation differs",
        )
        committed[name] = expected_committed
        if not complete:
            _require(
                fact["file_binding_after"] is None and fact["binding_stable"] is None,
                f"D-141 parent {name} blocked source tail differs",
            )
            stable[name] = False
            continue
        _validate_file_binding(fact["file_binding_after"], label=f"parent {name} after")
        expected_stable = fact["file_binding_before"] == fact["file_binding_after"]
        _require(
            fact["binding_stable"] is expected_stable,
            f"D-141 parent {name} stability differs",
        )
        stable[name] = expected_stable
    return {"committed": committed, "stable": stable}


def validate_d141_sdk_no_call_successor_observation(value: Any) -> dict[str, Any]:
    """Replay the public parent/isolated-child observation exactly."""

    _require_canonical_mapping_order(value, label="parent canonical JSON")
    _require(
        isinstance(value, dict) and tuple(value) == tuple(sorted(_ROOT_KEYS)),
        "D-141 parent fields differ",
    )
    _require(value["schema_version"] == SDK_OBSERVATION_SCHEMA, "D-141 parent schema differs")
    _require(value["phase"] == SDK_PHASE, "D-141 parent phase differs")
    _require(
        value["observer_contract"] == _parent_observer_contract(),
        "D-141 parent observer contract differs",
    )
    observation = value["observation"]
    _require(
        isinstance(observation, dict)
        and tuple(observation) == tuple(sorted(_PARENT_OBSERVATION_KEYS)),
        "D-141 parent observation fields differ",
    )
    launch = observation["launch_contract"]
    _require(
        isinstance(launch, dict)
        and tuple(launch) == tuple(sorted(EXACT_LAUNCH_CONTRACT))
        and all(type(bit) is bool for bit in launch.values()),
        "D-141 parent launch fields differ",
    )
    activity = value["activity"]
    _validate_parent_activity(activity)
    stage = observation["stage"]
    _require(
        stage in {"launch", "presence", "python", "source", "complete"},
        "D-141 parent stage",
    )
    presence = observation["environment_presence_bits"]
    python = observation["python"]
    sources = observation["source_bindings"]
    child = observation["isolated_child"]
    if stage == "launch":
        _require(launch != EXACT_LAUNCH_CONTRACT, "D-141 parent launch lacks mismatch")
        expected_checks = {"exact_launch_contract": False}
        expected_blockers = ["exact-python-launch-flags-differ"]
        expected_activity = _parent_empty_activity()
        _require(
            presence is None and python is None and sources is None and child is None,
            "D-141 parent launch branch observed later facts",
        )
    else:
        validate_d141_sdk_launch_contract(launch)
        _require(
            isinstance(presence, dict)
            and tuple(presence) == tuple(sorted(SDK_ENVIRONMENT_NAMES))
            and all(type(bit) is bool for bit in presence.values()),
            "D-141 parent presence fields differ",
        )
        presence_checks = {
            "openai_api_key_present": presence["OPENAI_API_KEY"],
            "pythonhome_absent": not presence["PYTHONHOME"],
            "pythonpath_absent": not presence["PYTHONPATH"],
        }
        if stage == "presence":
            expected_checks = presence_checks
            expected_blockers = [
                *(
                    ["openai-api-key-presence-bit-is-false"]
                    if not presence["OPENAI_API_KEY"]
                    else []
                ),
                *(["pythonhome-presence-bit-is-true"] if presence["PYTHONHOME"] else []),
                *(["pythonpath-presence-bit-is-true"] if presence["PYTHONPATH"] else []),
                "isolated-sdk-worker-suppressed-by-presence-checks",
            ]
            _require(len(expected_blockers) > 1, "D-141 parent presence lacks blocker")
            expected_activity = _parent_empty_activity()
            expected_activity["environment_presence_check_count"] = 3
            _require(
                python is None and sources is None and child is None,
                "D-141 parent presence branch observed later facts",
            )
        elif stage == "python":
            _require(
                presence == {"OPENAI_API_KEY": True, "PYTHONHOME": False, "PYTHONPATH": False},
                "D-141 parent advanced with failing presence",
            )
            _validate_parent_python(python, complete=False)
            _require(python["under_repository_venv"] is False, "D-141 parent Python stage safe")
            expected_checks = {"python_under_repository_venv": False}
            expected_blockers = [
                "python-interpreter-is-not-repository-venv",
                "isolated-sdk-worker-suppressed-by-python-provenance",
            ]
            expected_activity = _parent_empty_activity()
            expected_activity["environment_presence_check_count"] = 3
            _require(sources is None and child is None, "D-141 parent Python tail differs")
        elif stage == "source":
            _require(
                presence == {"OPENAI_API_KEY": True, "PYTHONHOME": False, "PYTHONPATH": False},
                "D-141 parent source presence differs",
            )
            _validate_parent_python(python, complete=False)
            _require(
                python["under_repository_venv"] is True,
                "D-141 parent source stage has unsafe Python",
            )
            source_outcome = _validate_parent_sources(sources, complete=False)
            expected_checks = {
                f"{name}_committed_binding_match_before": source_outcome["committed"][name]
                for name in ("helper", "model", "lock")
            }
            _require(
                not all(expected_checks.values()),
                "D-141 parent source stage lacks committed mismatch",
            )
            expected_blockers = [
                *(
                    f"{name}-source-does-not-match-committed-binding"
                    for name in ("helper", "model", "lock")
                    if not expected_checks[f"{name}_committed_binding_match_before"]
                ),
                "isolated-sdk-worker-suppressed-by-committed-source-binding",
            ]
            expected_activity = _parent_empty_activity()
            expected_activity.update(
                {
                    "environment_presence_check_count": 3,
                    "parent_file_binding_count": 4,
                }
            )
            _require(child is None, "D-141 parent source branch started child")
        else:
            _require(
                presence == {"OPENAI_API_KEY": True, "PYTHONHOME": False, "PYTHONPATH": False},
                "D-141 parent complete presence differs",
            )
            _validate_parent_python(python, complete=True)
            source_outcome = _validate_parent_sources(sources, complete=True)
            _require(
                all(source_outcome["committed"].values()),
                "D-141 parent complete source lacks committed match",
            )
            _require(
                isinstance(child, dict)
                and tuple(child)
                == (
                    "canonical_stdout_replay",
                    "contract",
                    "credential_value_forward_count",
                    "environment_entry_forward_count",
                    "process_kill_count",
                    "process_start_count",
                    "returncode",
                    "stderr_bytes",
                    "stderr_overflow",
                    "stdout_bytes",
                    "stdout_overflow",
                    "timed_out",
                    "worker_observation",
                ),
                "D-141 parent child execution facts differ",
            )
            worker = _validate_worker_observation(child["worker_observation"])
            worker_sources = worker["observation"]["committed_source_bindings"]
            for name in ("helper", "model", "lock"):
                outer = sources[name]
                nested = worker_sources[name]
                _require(
                    nested["repository_relative_path"] == outer["repository_relative_path"]
                    and nested["expected_committed_file_bytes"]
                    == outer["expected_committed_file_bytes"]
                    and nested["expected_committed_file_sha256"]
                    == outer["expected_committed_file_sha256"]
                    and nested["expected_committed_linklike"]
                    is outer["expected_committed_linklike"],
                    f"D-141 nested worker {name} committed source differs",
                )
            expected_stdout_bytes = len(_compact_json_bytes(worker) + b"\n")
            _require(
                child["contract"] == _canonicalize_json(ISOLATED_CHILD_CONTRACT)
                and child["process_start_count"] == 1
                and type(child["process_start_count"]) is int
                and child["process_kill_count"] == 0
                and type(child["process_kill_count"]) is int
                and child["returncode"] == 0
                and type(child["returncode"]) is int
                and child["timed_out"] is False
                and child["stdout_overflow"] is False
                and child["stderr_overflow"] is False
                and type(child["stdout_bytes"]) is int
                and child["stdout_bytes"] == expected_stdout_bytes
                and child["stderr_bytes"] == 0
                and type(child["stderr_bytes"]) is int
                and child["canonical_stdout_replay"] is True
                and child["environment_entry_forward_count"] == 0
                and type(child["environment_entry_forward_count"]) is int
                and child["credential_value_forward_count"] == 0
                and type(child["credential_value_forward_count"]) is int,
                "D-141 parent child execution contract differs",
            )
            expected_checks = {
                "exact_launch_contract": True,
                **presence_checks,
                "python_under_repository_venv": True,
                "python_binding_stable": python["binding_stable"],
                **{
                    f"{name}_committed_binding_match_before": source_outcome["committed"][name]
                    for name in ("helper", "model", "lock")
                },
                "helper_source_binding_stable": source_outcome["stable"]["helper"],
                "model_source_binding_stable": source_outcome["stable"]["model"],
                "lock_source_binding_stable": source_outcome["stable"]["lock"],
                "isolated_child_observation_passed": worker["passed"],
            }
            expected_blockers = [
                *(
                    ["python-executable-binding-changed-during-isolated-child"]
                    if not python["binding_stable"]
                    else []
                ),
                *(
                    f"{name}-source-binding-changed-during-isolated-child"
                    for name in ("helper", "model", "lock")
                    if not source_outcome["stable"][name]
                ),
                *worker["blockers"],
            ]
            expected_activity = _parent_empty_activity()
            expected_activity.update(
                {
                    "environment_presence_check_count": 3,
                    "parent_file_binding_count": 8,
                    "child_process_start_count": 1,
                    "child_process_kill_count": 0,
                    "child_stdout_bytes": expected_stdout_bytes,
                    "child_stderr_bytes": 0,
                }
            )
    _require(observation["checks"] == expected_checks, "D-141 parent checks differ")
    _require(value["blockers"] == expected_blockers, "D-141 parent blockers differ")
    _require(activity == expected_activity, "D-141 parent activity differs")
    passed = stage == "complete" and not expected_blockers
    _require(value["passed"] is passed, "D-141 parent pass flag differs")
    _require(
        value["status"] == (SDK_READY_STATUS if passed else SDK_BLOCKED_STATUS),
        "D-141 parent status differs",
    )
    return value


def validate_d141_sdk_no_call_successor_committed_source_bindings(
    value: Any,
    expected_committed_source_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Cross-bind a replayed source/complete result to immutable gate bindings."""

    validated = validate_d141_sdk_no_call_successor_observation(value)
    expected = _validate_expected_committed_source_bindings(expected_committed_source_bindings)
    sources = validated["observation"]["source_bindings"]
    if sources is None:
        return validated
    for name in ("helper", "model", "lock"):
        fact = sources[name]
        _require(
            fact["repository_relative_path"] == expected[name]["repository_relative_path"]
            and fact["expected_committed_file_bytes"] == expected[name]["file_bytes"]
            and fact["expected_committed_file_sha256"] == expected[name]["file_sha256"]
            and fact["expected_committed_linklike"] is expected[name]["linklike"],
            f"D-141 parent {name} committed source does not match immutable gate binding",
        )
    return validated


__all__ = [
    "D141SDKNoCallSuccessorError",
    "D141_FIXED_TEMP_ROOT",
    "EXACT_LAUNCH_CONTRACT",
    "ISOLATED_CHILD_CONTRACT",
    "IsolatedChildExecution",
    "IsolatedChildRequest",
    "LAUNCHER_SOURCE_CONTRACT",
    "OFFICIAL_API_BASE_URL",
    "SDK_BLOCKED_STATUS",
    "SDK_ENVIRONMENT_NAMES",
    "SDK_OBSERVATION_SCHEMA",
    "SDK_PHASE",
    "SDK_READY_STATUS",
    "SDKIsolatedSuccessorDependencies",
    "SDKWorkerDependencies",
    "current_d141_sdk_launch_contract",
    "run_d141_sdk_no_call_successor_observation",
    "validate_d141_sdk_launch_contract",
    "validate_d141_sdk_no_call_successor_committed_source_bindings",
    "validate_d141_sdk_no_call_successor_observation",
]


if __name__ == "__main__":
    raise SystemExit(_isolated_worker_main())
