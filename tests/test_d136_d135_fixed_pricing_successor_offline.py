from __future__ import annotations

import ast
import base64
import copy
import inspect
import json
import shutil
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

from patchloop.evals import d136_d135_fixed_pricing_successor_offline as d136
from patchloop.evals import d136_fixed_pricing_capture as pricing_capture
from patchloop.util import canonical_json, sha256_bytes, sha256_text

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = Path("patchloop/evals/d136_d135_fixed_pricing_successor_offline.py")
HELPER_PATH = Path("patchloop/evals/d136_fixed_pricing_capture.py")
SCRIPT_PATH = Path("scripts/build_d136_d135_fixed_pricing_successor_offline.py")
TEST_PATH = Path("tests/test_d136_d135_fixed_pricing_successor_offline.py")

D135_GATE_PATH = Path(
    "reports/live-pilot/artifacts/d135-d134-ambiguous-gate-correction-offline-source-gate.json"
)
D135_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d135-d132-pricing-consumed-incident-procedural-terminal.json"
)
D135_GATE_COMMIT = "e0a26f0134b811fca2cd76d3d8a69ec2a484cabb"
D135_GATE_TREE = "b0af863e7d541242916784a2c851636c12bdac63"
D135_GATE_PARENT = "ca50402aa8d3965ea384563262c713c6090d2ecf"
D135_GATE_BLOB = "fa88c0b3f1655ada2e54faf2421e781fc68aad4a"
D135_GATE_ID = "d135_7e67561d187cfb44440790052a95fc8b95a4006fe886e0f7c3dce9bae437e8c6"
D135_GATE_BODY_SHA = "sha256:7e67561d187cfb44440790052a95fc8b95a4006fe886e0f7c3dce9bae437e8c6"
D135_GATE_FILE_SHA = "sha256:37639f8327d1f29a5ce2321c0f2ba79e3ada7821c1bac1995770faea5237cce0"
D135_GATE_FILE_BYTES = 22_922
D135_TERMINAL_COMMIT = "98f4560e718145bc7465732c1a3d2f5a4ea8d786"
D135_TERMINAL_TREE = "901c123f425733ee77e5c8db926ffa4f98edd431"
D135_TERMINAL_BLOB = "8efce4a2508cddd32b59d9be92f3eb65517b1552"
D135_TERMINAL_ID = (
    "d135pricingincident_7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75"
)
D135_TERMINAL_BODY_SHA = "sha256:7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75"
D135_TERMINAL_FILE_SHA = "sha256:ac0f8a6a8d3282f14d3d6b5ab8176e0fe4f64a8bb509e4cd1380ca6a76b2438a"
D135_TERMINAL_FILE_BYTES = 22_084

SOURCE_COMMIT = "a" * 40
SOURCE_TREE = "b" * 40
GATE_COMMIT = "c" * 40
GATE_TREE = "d" * 40
RECEIPT_COMMIT = "e" * 40
RECEIPT_TREE = "f" * 40
ATTEMPT_COMMIT = "1" * 40
ATTEMPT_TREE = "2" * 40
STARTED_COMMIT = "3" * 40
STARTED_TREE = "4" * 40
TERMINAL_COMMIT = "5" * 40
TERMINAL_TREE = "6" * 40
MARKER_ONLY_COMMIT = "9" * 40
MARKER_ONLY_TREE = "0" * 40

MODEL_PAGE = (
    b"# GPT-5.4 mini\n"
    b"Default snapshot: `gpt-5.4-mini-2026-03-17`\n"
    b"| Input | $0.75 | 1M tokens |\n"
    b"| Cached input | $0.075 | 1M tokens |\n"
    b"| Output | $4.5 | 1M tokens |\n"
    b"| Responses | `v1/responses` | Supported |\n"
    b"| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |\n"
)


@dataclass
class ResponsePlan:
    status_code: int = 200
    url: str = pricing_capture.OFFICIAL_MODEL_PAGE_URL
    headers: dict[str, str] = field(
        default_factory=lambda: {
            "Content-Type": "text/markdown; charset=utf-8",
            "ETag": '"d136-test-etag"',
        }
    )
    chunks: tuple[bytes, ...] = (MODEL_PAGE,)
    iteration_error: Exception | None = None
    bind_exact_request: bool = True


class NoContextResponse:
    """Minimal streaming Response that intentionally has no context-manager API."""

    def __init__(self, plan: ResponsePlan, request: httpx.Request) -> None:
        self.status_code = plan.status_code
        self.url = httpx.URL(plan.url)
        self.headers = httpx.Headers(plan.headers)
        self.request = (
            request
            if plan.bind_exact_request
            else httpx.Request(request.method, str(request.url), headers=request.headers)
        )
        self._chunks = plan.chunks
        self._iteration_error = plan.iteration_error
        self.iteration_count = 0
        self.close_count = 0

    def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
        assert chunk_size == pricing_capture.STREAM_CHUNK_BYTES
        for chunk in self._chunks:
            self.iteration_count += 1
            yield chunk
        if self._iteration_error is not None:
            raise self._iteration_error

    def close(self) -> None:
        self.close_count += 1


class FakeClient:
    def __init__(self, plans: list[ResponsePlan]) -> None:
        self.plans = plans
        self.constructor_calls: list[dict[str, Any]] = []
        self.send_calls: list[httpx.Request] = []
        self.responses: list[NoContextResponse] = []
        self.cookies = httpx.Cookies()
        self.close_count = 0

    def factory(self, **kwargs: Any) -> FakeClient:
        self.constructor_calls.append(dict(kwargs))
        return self

    def build_request(self, method: str, url: str, *, headers: dict[str, str]) -> httpx.Request:
        request = httpx.Request(method, url, headers=headers)
        self.cookies.set_cookie_header(request)
        return request

    def send(
        self,
        request: httpx.Request,
        *,
        stream: bool,
        follow_redirects: bool,
    ) -> NoContextResponse:
        assert stream is True
        assert follow_redirects is False
        self.send_calls.append(request)
        if not self.plans:
            raise AssertionError("unexpected HTTP request")
        response = NoContextResponse(self.plans.pop(0), request)
        self.responses.append(response)
        return response

    def close(self) -> None:
        self.close_count += 1


def _install_httpx(monkeypatch: pytest.MonkeyPatch, *plans: ResponsePlan) -> FakeClient:
    client = FakeClient(list(plans))
    monkeypatch.setattr(pricing_capture.httpx, "Client", client.factory)
    return client


def _forbidden(label: str):
    def fail(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError(f"D-136 crossed forbidden {label} boundary")

    return fail


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


def _fake_d135_terminal_binding() -> dict[str, Any]:
    payload = json.loads((REPOSITORY / D135_TERMINAL_PATH).read_bytes())
    return {
        "path": D135_TERMINAL_PATH.as_posix(),
        "artifact_id": D135_TERMINAL_ID,
        "semantic_body_hash": D135_TERMINAL_BODY_SHA,
        "file_sha256": D135_TERMINAL_FILE_SHA,
        "file_bytes": D135_TERMINAL_FILE_BYTES,
        "status": payload["semantic_body"]["status"],
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "terminal_body_status": payload["semantic_body"]["status"],
        "commit_binding": {
            "commit": D135_TERMINAL_COMMIT,
            "tree": D135_TERMINAL_TREE,
            "parents": [D135_GATE_COMMIT],
            "artifact_path": D135_TERMINAL_PATH.as_posix(),
            "artifact_blob_oid": D135_TERMINAL_BLOB,
            "artifact_file_sha256": D135_TERMINAL_FILE_SHA,
            "artifact_file_bytes": D135_TERMINAL_FILE_BYTES,
            "single_artifact_add_commit": True,
        },
    }


@pytest.fixture
def repository(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    root = REPOSITORY / f"tmp-d136-test-{uuid.uuid4().hex}"
    assert not root.exists()
    root.mkdir()
    (root / d136.GATE_PATH.parent).mkdir(parents=True)
    source_blobs: dict[str, bytes] = {}
    for relative in d136.SOURCE_BINDING_PATHS:
        source = REPOSITORY / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        target.write_bytes(raw)
        source_blobs[relative.as_posix()] = raw

    state: dict[str, Any] = {
        "head": SOURCE_COMMIT,
        "time_index": 0,
        "writes": [],
        "extra_diff": {},
        "identity_overrides": {},
        "status_override": None,
    }
    identities: dict[str, dict[str, object]] = {
        SOURCE_COMMIT: {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "parents": [D135_TERMINAL_COMMIT],
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
        STARTED_COMMIT: {
            "commit": STARTED_COMMIT,
            "tree": STARTED_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
        TERMINAL_COMMIT: {
            "commit": TERMINAL_COMMIT,
            "tree": TERMINAL_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
        MARKER_ONLY_COMMIT: {
            "commit": MARKER_ONLY_COMMIT,
            "tree": MARKER_ONLY_TREE,
            "parents": [ATTEMPT_COMMIT],
        },
    }

    def commit_identity(_root: Path, commit: str) -> dict[str, object]:
        return copy.deepcopy(state["identity_overrides"].get(commit, identities[commit]))

    def diff_rows(_root: Path, commit: str) -> list[dict[str, str]]:
        if commit == SOURCE_COMMIT:
            rows = [{"status": "A", "path": path.as_posix()} for path in d136.IMPLEMENTATION_PATHS]
        elif commit == GATE_COMMIT:
            rows = [
                {"status": "A", "path": d136.GATE_PATH.as_posix()},
                *({"status": "M", "path": path.as_posix()} for path in d136.ACTIVE_DOC_PATHS),
            ]
        elif commit == RECEIPT_COMMIT:
            rows = [{"status": "A", "path": d136.RECEIPT_PATH.as_posix()}]
        elif commit == ATTEMPT_COMMIT:
            rows = [{"status": "A", "path": d136.ATTEMPT_PATH.as_posix()}]
        elif commit in (STARTED_COMMIT, MARKER_ONLY_COMMIT):
            rows = [{"status": "A", "path": d136.STARTED_PATH.as_posix()}]
        elif commit == TERMINAL_COMMIT:
            rows = [
                {"status": "A", "path": d136.STARTED_PATH.as_posix()},
                {"status": "A", "path": d136.TERMINAL_PATH.as_posix()},
            ]
        else:
            raise AssertionError(f"unexpected commit diff: {commit}")
        return [*rows, *copy.deepcopy(state["extra_diff"].get(commit, []))]

    def commit_blob(_root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
        if commit == SOURCE_COMMIT and relative.as_posix() in source_blobs:
            index = d136.SOURCE_BINDING_PATHS.index(relative) + 1
            return f"{index:x}"[-1] * 40, source_blobs[relative.as_posix()]
        artifact_commits = {
            (GATE_COMMIT, d136.GATE_PATH): "a" * 40,
            (RECEIPT_COMMIT, d136.RECEIPT_PATH): "b" * 40,
            (ATTEMPT_COMMIT, d136.ATTEMPT_PATH): "c" * 40,
            (STARTED_COMMIT, d136.STARTED_PATH): "d" * 40,
            (MARKER_ONLY_COMMIT, d136.STARTED_PATH): "e" * 40,
            (TERMINAL_COMMIT, d136.STARTED_PATH): "f" * 40,
            (TERMINAL_COMMIT, d136.TERMINAL_PATH): "1" * 40,
        }
        oid = artifact_commits.get((commit, relative))
        if oid is not None:
            return oid, (root / relative).read_bytes()
        raise AssertionError(f"unexpected committed blob: {commit}:{relative}")

    def status_lines(_root: Path) -> list[str]:
        if state["status_override"] is not None:
            return list(state["status_override"])
        head = state["head"]
        if head == SOURCE_COMMIT and (root / d136.GATE_PATH).exists():
            return [f"?? {d136.GATE_PATH.as_posix()}"]
        if head == GATE_COMMIT and (root / d136.RECEIPT_PATH).exists():
            return [f"?? {d136.RECEIPT_PATH.as_posix()}"]
        if head == RECEIPT_COMMIT and (root / d136.ATTEMPT_PATH).exists():
            return [f"?? {d136.ATTEMPT_PATH.as_posix()}"]
        if head == ATTEMPT_COMMIT:
            paths = [
                path for path in (d136.STARTED_PATH, d136.TERMINAL_PATH) if (root / path).exists()
            ]
            return [f"?? {path.as_posix()}" for path in paths]
        return []

    real_write_new = d136._write_new

    def write_new(selected_root: Path, relative: Path, raw: bytes) -> None:
        state["writes"].append(relative)
        real_write_new(selected_root, relative, raw)

    def loaded_module_bindings(selected_root: Path, commit: str) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for relative, module_name in d136.LOADED_MODULE_PATHS:
            key = (relative.as_posix(), module_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    **d136._file_binding(selected_root, commit, relative),
                    "module_name": module_name,
                    "loaded_path": relative.as_posix(),
                    "loaded_path_matches_repository": True,
                }
            )
        return result

    def now() -> str:
        index = int(state["time_index"])
        state["time_index"] = index + 1
        return f"2026-08-09T17:{index:02d}:00Z"

    monkeypatch.setattr(d136, "_assert_runtime_import_boundary", lambda _root: None)
    monkeypatch.setattr(d136, "_exact_d135_terminal", lambda _root: _fake_d135_terminal_binding())
    monkeypatch.setattr(d136, "_now", now)
    monkeypatch.setattr(d136, "_commit_identity", commit_identity)
    monkeypatch.setattr(d136, "_diff_rows", diff_rows)
    monkeypatch.setattr(d136, "_commit_blob", commit_blob)
    monkeypatch.setattr(d136, "_status_lines", status_lines)
    monkeypatch.setattr(d136, "_head", lambda _root: state["head"])
    monkeypatch.setattr(d136, "_write_new", write_new)
    monkeypatch.setattr(d136, "_loaded_module_bindings", loaded_module_bindings)
    monkeypatch.setattr(
        d136.d135.d131,
        "_git_cli_observation",
        lambda _root: _fake_git_observation(),
    )
    try:
        yield root, state
    finally:
        if root.exists():
            assert root.resolve(strict=True).parent == REPOSITORY.resolve(strict=True)
            shutil.rmtree(root)


def _build_gate(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result = d136.run_d136_offline_source_gate(repository=root)
    raw = (root / d136.GATE_PATH).read_bytes()
    return result, json.loads(raw), raw


def _seal_gate(root: Path, state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    result, payload, raw = _build_gate(root)
    state["head"] = GATE_COMMIT
    return result, payload, raw


def _seal_receipt(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    _seal_gate(root, state)
    result = d136.create_d136_activation_receipt(repository=root)
    raw = (root / d136.RECEIPT_PATH).read_bytes()
    payload = json.loads(raw)
    state["head"] = RECEIPT_COMMIT
    committed = d136.validate_d136_activation_receipt(repository=root, mode="post-commit")
    assert committed["receipt_commit"] is not None
    return result, payload, raw


def _seal_attempt(
    root: Path, state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    _seal_receipt(root, state)
    result = d136.create_d136_pricing_attempt(repository=root)
    raw = (root / d136.ATTEMPT_PATH).read_bytes()
    payload = json.loads(raw)
    state["head"] = ATTEMPT_COMMIT
    committed = d136.validate_d136_pricing_attempt(repository=root, mode="post-commit")
    assert committed["attempt_commit"] is not None
    return result, payload, raw


def _mock_pricing_evidence(
    monkeypatch: pytest.MonkeyPatch,
    *,
    observed_at: str = "2026-08-09T17:03:30Z",
) -> dict[str, Any]:
    with monkeypatch.context() as capture_patch:
        client = _install_httpx(capture_patch, ResponsePlan())
        capture_patch.setattr(pricing_capture, "_utc_now_text", lambda: observed_at)
        value = pricing_capture.capture_official_pricing_evidence()
        assert client.close_count == 1
        assert client.responses[0].close_count == 1
        return value


def test_fixed_capture_accepts_response_without_context_manager_and_closes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (
        tuple(inspect.signature(pricing_capture.capture_official_pricing_evidence).parameters) == ()
    )
    client = _install_httpx(monkeypatch, ResponsePlan())

    evidence = pricing_capture.capture_official_pricing_evidence()

    assert len(client.responses) == 1
    assert not hasattr(client.responses[0], "__enter__")
    assert client.responses[0].close_count == 1
    assert client.close_count == 1
    assert client.constructor_calls == [
        {
            "trust_env": False,
            "follow_redirects": False,
            "timeout": pricing_capture.REQUEST_TIMEOUT_SECONDS,
            "auth": None,
            "cookies": None,
        }
    ]
    assert len(client.send_calls) == 1
    request = client.send_calls[0]
    assert request.method == "GET"
    assert str(request.url) == pricing_capture.OFFICIAL_MODEL_PAGE_URL
    assert not {"authorization", "cookie", "proxy-authorization"}.intersection(
        {name.lower() for name in request.headers}
    )
    assert evidence["public_get_request_count"] == 1
    assert evidence["redirect_count"] == 0
    assert base64.b64decode(evidence["decoded_entity_base64"], validate=True) == MODEL_PAGE
    assert pricing_capture.validate_official_pricing_evidence(evidence) is evidence


def test_fixed_capture_closes_every_redirect_response_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_httpx(
        monkeypatch,
        ResponsePlan(
            status_code=302,
            headers={"Location": pricing_capture.OFFICIAL_MODEL_PAGE_URL},
            chunks=(b"redirect body must not be read",),
        ),
        ResponsePlan(),
    )

    evidence = pricing_capture.capture_official_pricing_evidence()

    assert evidence["redirect_count"] == 1
    assert evidence["public_get_request_count"] == 2
    assert [response.close_count for response in client.responses] == [1, 1]
    assert [response.iteration_count for response in client.responses] == [0, 1]
    assert client.close_count == 1


@pytest.mark.parametrize(
    ("plan", "match"),
    [
        (ResponsePlan(status_code=503), "status differs"),
        (
            ResponsePlan(iteration_error=RuntimeError("stream exploded")),
            "stream exploded",
        ),
        (
            ResponsePlan(
                status_code=302,
                headers={"Location": "https://example.com/not-official.md"},
                chunks=(),
            ),
            "official docs URL differs",
        ),
        (
            ResponsePlan(
                status_code=302,
                headers={"Location": "https://developers.openai.com/api/docs/models/wrong.md"},
                chunks=(),
            ),
            "official docs URL differs",
        ),
        (
            ResponsePlan(headers={"Content-Type": "text/html"}),
            "content type differs",
        ),
        (
            ResponsePlan(
                headers={
                    "Content-Type": "text/markdown",
                    "Content-Encoding": "gzip",
                }
            ),
            "content encoding is not identity",
        ),
        (
            ResponsePlan(
                chunks=(
                    MODEL_PAGE,
                    b"x" * (pricing_capture.MAX_DECODED_ENTITY_BYTES - len(MODEL_PAGE)),
                    b"y",
                )
            ),
            "exceeds the 128KB bound",
        ),
        (
            ResponsePlan(bind_exact_request=False),
            "response request binding differs",
        ),
    ],
)
def test_fixed_capture_closes_response_and_client_on_every_error(
    monkeypatch: pytest.MonkeyPatch,
    plan: ResponsePlan,
    match: str,
) -> None:
    client = _install_httpx(monkeypatch, plan)

    with pytest.raises((pricing_capture.D136PricingCaptureError, RuntimeError), match=match):
        pricing_capture.capture_official_pricing_evidence()

    assert len(client.responses) == 1
    assert client.responses[0].close_count == 1
    assert client.close_count == 1


def test_fixed_capture_redirect_cap_closes_all_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirects = [
        ResponsePlan(
            status_code=307,
            headers={"Location": pricing_capture.OFFICIAL_MODEL_PAGE_URL},
            chunks=(),
        )
        for _ in range(pricing_capture.MAX_REDIRECTS + 1)
    ]
    client = _install_httpx(monkeypatch, *redirects)

    with pytest.raises(pricing_capture.D136PricingCaptureError, match="redirect limit exceeded"):
        pricing_capture.capture_official_pricing_evidence()

    assert len(client.responses) == pricing_capture.MAX_REDIRECTS + 1
    assert all(response.close_count == 1 for response in client.responses)
    assert client.close_count == 1


def test_fixed_capture_send_failure_still_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_httpx(monkeypatch, ResponsePlan())

    def send_failure(*_args: object, **_kwargs: object) -> NoContextResponse:
        raise RuntimeError("send failed before response")

    monkeypatch.setattr(client, "send", send_failure)
    with pytest.raises(RuntimeError, match="send failed before response"):
        pricing_capture.capture_official_pricing_evidence()

    assert client.responses == []
    assert client.close_count == 1


def test_fixed_capture_validator_rejects_rehashed_boundary_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_httpx(monkeypatch, ResponsePlan())
    evidence = pricing_capture.capture_official_pricing_evidence()
    assert client.close_count == 1

    for mutate in (
        lambda value: value.__setitem__("request_auth_or_cookie_sent", True),
        lambda value: value.__setitem__("proxy_use_disabled", False),
        lambda value: value.__setitem__("public_get_request_count", 0),
        lambda value: value.__setitem__("decoded_entity_base64", "%%%"),
        lambda value: value.__setitem__("decoded_entity_bytes", value["decoded_entity_bytes"] + 1),
        lambda value: value.__setitem__("decoded_entity_sha256", "sha256:" + "0" * 64),
        lambda value: value["facts"].__setitem__("input_usd", "0.76"),
    ):
        tampered = copy.deepcopy(evidence)
        mutate(tampered)
        if tampered["facts"] != evidence["facts"]:
            tampered["facts_sha256"] = sha256_text(canonical_json(tampered["facts"]))
        with pytest.raises(pricing_capture.D136PricingCaptureError):
            pricing_capture.validate_official_pricing_evidence(tampered)


def test_exact_d135_terminal_bytes_topology_and_consumed_boundary_are_bound() -> None:
    gate_raw = (REPOSITORY / D135_GATE_PATH).read_bytes()
    terminal_raw = (REPOSITORY / D135_TERMINAL_PATH).read_bytes()
    gate = json.loads(gate_raw)
    terminal = json.loads(terminal_raw)

    assert gate["gate_id"] == D135_GATE_ID
    assert gate["semantic_body_hash"] == D135_GATE_BODY_SHA
    assert (sha256_bytes(gate_raw), len(gate_raw)) == (
        D135_GATE_FILE_SHA,
        D135_GATE_FILE_BYTES,
    )
    assert terminal["artifact_id"] == D135_TERMINAL_ID
    assert terminal["semantic_body_hash"] == D135_TERMINAL_BODY_SHA
    assert (sha256_bytes(terminal_raw), len(terminal_raw)) == (
        D135_TERMINAL_FILE_SHA,
        D135_TERMINAL_FILE_BYTES,
    )
    assert d136.D135_TERMINAL_PATH == D135_TERMINAL_PATH
    assert d136.D135_TERMINAL_ID == D135_TERMINAL_ID
    assert d136.D135_TERMINAL_BODY_SHA256 == D135_TERMINAL_BODY_SHA
    assert d136.D135_TERMINAL_FILE_SHA256 == D135_TERMINAL_FILE_SHA
    assert d136.D135_TERMINAL_FILE_BYTES == D135_TERMINAL_FILE_BYTES
    assert d136.D135_TERMINAL_BLOB_OID == D135_TERMINAL_BLOB
    assert d136.D135_TERMINAL_COMMIT == D135_TERMINAL_COMMIT
    assert d136.D135_TERMINAL_TREE == D135_TERMINAL_TREE
    assert d136.D135_TERMINAL_PARENT == D135_GATE_COMMIT

    gate_binding = terminal["semantic_body"]["d135_gate_binding"]
    assert gate_binding["artifact_id"] == D135_GATE_ID
    assert gate_binding["semantic_body_hash"] == D135_GATE_BODY_SHA
    assert gate_binding["file_sha256"] == D135_GATE_FILE_SHA
    assert gate_binding["file_bytes"] == D135_GATE_FILE_BYTES
    assert gate_binding["evidence_commit_binding"] == {
        "commit": D135_GATE_COMMIT,
        "tree": D135_GATE_TREE,
        "parents": [D135_GATE_PARENT],
        "artifact_path": D135_GATE_PATH.as_posix(),
        "artifact_blob_oid": D135_GATE_BLOB,
        "artifact_file_sha256": D135_GATE_FILE_SHA,
        "artifact_file_bytes": D135_GATE_FILE_BYTES,
        "exact_gate_add_and_active_docs_modify_commit": True,
    }
    incident = terminal["semantic_body"]["incident_observation"]
    assert incident["activation_and_pricing_attempt_consumed"] is True
    assert incident["application_level_client_send_returned_response_count"] == 1
    assert incident["underlying_http_request_count"] == "unknown"
    assert incident["completed_replayable_canonical_pricing_evidence_count"] == 0
    assert incident["canonical_pricing_evidence_artifact_created"] is False
    assert incident["canonical_http_exchange_completed"] == "unknown"
    assert incident["retry_resume_repair_or_backfill_allowed"] is False

    assert d136.d135._commit_identity(REPOSITORY, D135_TERMINAL_COMMIT) == {
        "commit": D135_TERMINAL_COMMIT,
        "tree": D135_TERMINAL_TREE,
        "parents": [D135_GATE_COMMIT],
    }
    assert d136.d135._diff_rows(REPOSITORY, D135_TERMINAL_COMMIT) == [
        {"status": "A", "path": D135_TERMINAL_PATH.as_posix()}
    ]
    oid, committed = d136.d135._commit_blob(REPOSITORY, D135_TERMINAL_COMMIT, D135_TERMINAL_PATH)
    assert (oid, committed) == (D135_TERMINAL_BLOB, terminal_raw)


def test_public_paths_statuses_signatures_and_future_absence_are_exact() -> None:
    assert (
        Path(
            "reports/live-pilot/artifacts/"
            "d136-d135-fixed-pricing-successor-offline-source-gate.json"
        )
        == d136.GATE_PATH
    )
    assert (
        Path("reports/live-pilot/artifacts/d136-fixed-pricing-successor-activation-receipt.json")
        == d136.RECEIPT_PATH
    )
    assert (
        Path("reports/live-pilot/artifacts/d136-fixed-pricing-capture-attempt-intent.json")
        == d136.ATTEMPT_PATH
    )
    assert (
        Path("reports/live-pilot/artifacts/d136-fixed-pricing-capture-action-started.json")
        == d136.STARTED_PATH
    )
    assert (
        Path("reports/live-pilot/artifacts/d136-replayable-official-pricing-evidence.json")
        == d136.TERMINAL_PATH
    )
    assert d136.GATE_STATUS == (
        "D136_D135_FIXED_PRICING_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED"
    )
    assert d136.RECEIPT_STATUS == (
        "D136_FIXED_PRICING_SUCCESSOR_ACTIVATION_RECEIPT_RECORDED_COMMIT_REQUIRED"
    )
    assert d136.ATTEMPT_STATUS == ("D136_FIXED_PRICING_CAPTURE_ATTEMPT_RECORDED_COMMIT_REQUIRED")
    assert d136.STARTED_STATUS == (
        "D136_FIXED_PRICING_CAPTURE_ACTION_STARTED_RECORDED_TRANSITION_COMMIT_REQUIRED"
    )
    assert d136.TERMINAL_STATUS == (
        "D136_FIXED_PRICING_SUCCESSOR_CAPTURED_TRANSITION_COMMIT_REQUIRED"
    )
    assert d136.IMPLEMENTATION_PATHS == (HELPER_PATH, MODULE_PATH, SCRIPT_PATH, TEST_PATH)
    assert d136.FUTURE_PATHS == (
        d136.RECEIPT_PATH,
        d136.ATTEMPT_PATH,
        d136.STARTED_PATH,
        d136.TERMINAL_PATH,
    )
    assert not hasattr(d136, "FINAL_GATE_PATH")
    assert not hasattr(d136, "create_d136_action_started")
    assert not hasattr(d136, "run_d136_fixed_pricing_successor_gate")
    assert not hasattr(d136, "validate_d136_fixed_pricing_successor_gate")
    assert len(d136.ACTIVE_DOC_PATHS) == 10
    assert all(not (REPOSITORY / path).exists() for path in d136.FUTURE_PATHS)

    functions = (
        d136.run_d136_offline_source_gate,
        d136.validate_d136_offline_source_gate,
        d136.render_d136_external_activation_template,
        d136.create_d136_activation_receipt,
        d136.validate_d136_activation_receipt,
        d136.create_d136_pricing_attempt,
        d136.validate_d136_pricing_attempt,
        d136.run_d136_fixed_pricing_capture,
        d136.validate_d136_pricing_terminal,
    )
    assert all("repository" in inspect.signature(function).parameters for function in functions)


def test_source_imports_no_consumed_runner_and_helper_reimplements_capture() -> None:
    module_tree = ast.parse((REPOSITORY / MODULE_PATH).read_text(encoding="utf-8"))
    helper_tree = ast.parse((REPOSITORY / HELPER_PATH).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for tree in (module_tree, helper_tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    assert "patchloop.evals.d132_d130_external_activation_offline" not in imported
    assert "patchloop.evals.d127_pricing_capture" not in imported


def test_runtime_loaded_module_provenance_rejects_outside_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in d136.PYTHON_ROUTING_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    d136._assert_runtime_import_boundary(REPOSITORY)

    outside = REPOSITORY.parent / f"outside-d136-helper-{uuid.uuid4().hex}.py"
    assert not outside.exists()
    outside.write_text("# outside repository\n", encoding="utf-8")
    try:
        monkeypatch.setattr(pricing_capture, "__file__", str(outside))
        with pytest.raises(d136.D136FixedPricingSuccessorError, match="outside repository"):
            d136._assert_runtime_import_boundary(REPOSITORY)
    finally:
        outside.unlink(missing_ok=True)


def test_source_commit_is_exact_d135_terminal_child_with_loaded_module_bindings(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    source = d136._source_identity_for_gate(root)

    assert source["commit"] == SOURCE_COMMIT
    assert source["tree"] == SOURCE_TREE
    assert source["parents"] == [D135_TERMINAL_COMMIT]
    assert source["implementation_paths"] == [path.as_posix() for path in d136.IMPLEMENTATION_PATHS]
    assert [row["path"] for row in source["source_file_bindings"]] == [
        path.as_posix() for path in d136.SOURCE_BINDING_PATHS
    ]
    assert [row["loaded_path"] for row in source["loaded_module_bindings"]] == list(
        dict.fromkeys(path.as_posix() for path, _module_name in d136.LOADED_MODULE_PATHS)
    )
    assert all(
        row["loaded_path_matches_repository"] is True and row["current_bytes_match_commit"] is True
        for row in source["loaded_module_bindings"]
    )
    assert source["python_routing_env_presence"] == {
        "PYTHONHOME": False,
        "PYTHONPATH": False,
    }
    assert source["git_cli_observation"] == _fake_git_observation()
    file_bindings = {row["path"]: row for row in source["source_file_bindings"]}
    for relative in (Path("pyproject.toml"), Path("uv.lock")):
        raw = (root / relative).read_bytes()
        binding = file_bindings[relative.as_posix()]
        assert binding["file_sha256"] == sha256_bytes(raw)
        assert binding["file_bytes"] == len(raw)
        assert binding["current_bytes_match_commit"] is True
    assert source["exact_source_only_commit"] is True

    state["identity_overrides"][SOURCE_COMMIT] = {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "parents": ["0" * 40],
    }
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="source parent"):
        d136._source_identity_for_gate(root)
    state["identity_overrides"].clear()

    state["extra_diff"][SOURCE_COMMIT] = [{"status": "M", "path": "README.md"}]
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="source commit scope"):
        d136._source_identity_for_gate(root)


def test_offline_gate_builder_is_idempotent_and_invokes_no_future_or_external_helper(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    for name in (
        "create_d136_activation_receipt",
        "create_d136_pricing_attempt",
        "run_d136_fixed_pricing_capture",
    ):
        monkeypatch.setattr(d136, name, _forbidden(name))
    monkeypatch.setattr(
        pricing_capture,
        "capture_official_pricing_evidence",
        _forbidden("pricing helper"),
    )
    monkeypatch.setattr(
        pricing_capture,
        "validate_official_pricing_evidence",
        _forbidden("pricing helper validator"),
    )

    first, payload, raw = _build_gate(root)
    second = d136.run_d136_offline_source_gate(repository=root)
    third = d136.validate_d136_offline_source_gate(repository=root)

    assert first == second == third
    assert state["writes"] == [d136.GATE_PATH]
    assert tuple(payload) == d136.GATE_ROOT_KEYS
    assert tuple(payload["semantic_body"]) == d136.GATE_BODY_KEYS
    assert payload["semantic_body_hash"] == sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["gate_id"] == (f"d136_{payload['semantic_body_hash'].removeprefix('sha256:')}")
    assert first["file_sha256"] == sha256_bytes(raw)
    assert first["file_bytes"] == len(raw)
    assert first["future_artifacts_created"] is False
    assert first["external_call_count"] == 0
    assert all(not (root / path).exists() for path in d136.FUTURE_PATHS)

    body = payload["semantic_body"]
    helper = body["fixed_pricing_helper_contract"]
    assert helper["sealed_d127_helper_imported_or_invoked"] is False
    assert helper["consumed_d132_runner_imported_or_invoked"] is False
    assert helper["response_context_manager_protocol_required"] is False
    assert helper["response_closed_explicitly_in_finally"] is True
    assert helper["maximum_application_level_public_get_send_count"] == 4
    future = body["future_activation_contract"]
    assert future["receipt_only_commit_required"] is True
    assert future["attempt_only_commit_required"] is True
    assert future["action_started_written_and_fsynced_immediately_before_helper"] is True
    assert future["action_started_and_terminal_two_artifact_commit_required_on_success"] is True
    assert (
        future["action_started_only_preservation_commit_authorized_on_post_marker_failure"] is True
    )
    assert future["post_marker_failure_consumes_activation_and_forbids_retry"] is True
    assert (
        body["evidence_boundary"]["d132_completed_replayable_canonical_pricing_evidence_count"] == 0
    )
    assert body["evidence_boundary"]["d132_canonical_pricing_evidence_artifact_created"] is False
    assert body["evidence_boundary"]["d132_canonical_replay_bytes_retained"] == 0
    assert body["evidence_boundary"]["d136_pricing_evidence_created"] is False
    assert body["evidence_boundary"]["mocked_transport_tests_are_not_official_pricing_evidence"]
    authority = body["authority"]
    assert all(value == 0 for key, value in authority.items() if key.endswith("_count"))
    assert authority["activation_receipt_created"] is False
    assert authority["pricing_attempt_created"] is False
    assert authority["action_started_created"] is False
    assert authority["pricing_terminal_created"] is False
    assert authority["execution_hash_or_candidate_created"] is False
    assert authority["cost_reserved_or_spent_usd"] == "0"
    assert authority["four_row_ac_executed"] is False


def test_offline_gate_chronology_collision_and_future_orphans_are_preserved(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    gate = root / d136.GATE_PATH
    predecessor_time = _fake_d135_terminal_binding()["recorded_at"]
    future_now = d136._now
    for invalid_time in (predecessor_time, "2026-08-09T16:54:26Z"):
        monkeypatch.setattr(d136, "_now", lambda selected=invalid_time: selected)
        with pytest.raises(d136.D136FixedPricingSuccessorError, match="gate chronology"):
            d136.run_d136_offline_source_gate(repository=root)
        assert not gate.exists()
        assert state["writes"] == []
    monkeypatch.setattr(d136, "_now", future_now)

    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_bytes(b"foreign-d136-gate")
    with pytest.raises(d136.D136FixedPricingSuccessorError):
        d136.run_d136_offline_source_gate(repository=root)
    assert gate.read_bytes() == b"foreign-d136-gate"
    gate.unlink()

    receipt = root / d136.RECEIPT_PATH
    receipt.write_bytes(b"orphan-activation-receipt")
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="unexpected path"):
        d136.run_d136_offline_source_gate(repository=root)
    assert receipt.read_bytes() == b"orphan-activation-receipt"
    assert not gate.exists()


def test_gate_postcommit_topology_is_exact_and_rejects_extra_scope(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, payload, raw = _build_gate(root)
    gate = root / d136.GATE_PATH
    provenance_tampers = (
        lambda value: value["semantic_body"]["source_identity"][
            "python_routing_env_presence"
        ].__setitem__("PYTHONPATH", True),
        lambda value: value["semantic_body"]["source_identity"]["git_cli_observation"].__setitem__(
            "version", "git version tampered"
        ),
    )
    for mutate in provenance_tampers:
        tampered = copy.deepcopy(payload)
        mutate(tampered)
        body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
        tampered["semantic_body_hash"] = body_hash
        tampered["gate_id"] = f"d136_{body_hash.removeprefix('sha256:')}"
        tampered_raw = d136._pretty_bytes(tampered)
        gate.write_bytes(tampered_raw)
        with pytest.raises(d136.D136FixedPricingSuccessorError, match="source identity rebuild"):
            d136.validate_d136_offline_source_gate(repository=root)
        assert gate.read_bytes() == tampered_raw
        gate.write_bytes(raw)
    state["head"] = GATE_COMMIT

    post = d136.validate_d136_offline_source_gate(repository=root, mode="post-evidence-commit")
    assert post["gate_evidence_commit"] == {
        "commit": GATE_COMMIT,
        "tree": GATE_TREE,
        "parents": [SOURCE_COMMIT],
        "artifact_path": d136.GATE_PATH.as_posix(),
        "artifact_blob_oid": "a" * 40,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }
    assert len(d136.ACTIVE_DOC_PATHS) == 10

    state["extra_diff"][GATE_COMMIT] = [{"status": "M", "path": "patchloop/agent/model.py"}]
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="evidence scope"):
        d136.validate_d136_offline_source_gate(repository=root, mode="post-evidence-commit")


def test_activation_template_is_exact_read_only_and_pre_authorizes_marker_preservation(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _result, payload, raw = _seal_gate(root, state)
    before_writes = list(state["writes"])

    template = d136.render_d136_external_activation_template(repository=root)
    post = d136.validate_d136_offline_source_gate(repository=root, mode="post-evidence-commit")

    assert f"Gate ID: {payload['gate_id']}" in template
    assert f"Gate body SHA: {payload['semantic_body_hash']}" in template
    assert f"Gate file SHA: {sha256_bytes(raw)}" in template
    assert f"Gate file bytes: {len(raw)}" in template
    assert (
        "Gate evidence commit tuple: "
        + json.dumps(
            post["gate_evidence_commit"],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        in template
    )
    assert f"Source commit: {SOURCE_COMMIT}" in template
    assert f"Source tree: {SOURCE_TREE}" in template
    assert f"D-135 terminal commit: {D135_TERMINAL_COMMIT}" in template
    assert all(f"- {item}" in template for item in d136.ACTIVATION_SCOPE)
    assert all(f"- {item}" in template for item in d136.ACTIVATION_EXCLUSIONS)
    assert "written and fsynced immediately before" in template
    assert "sole artifact in the attempt commit's direct child" in template
    assert "must never be retried" in template
    assert "later offline successor" in template
    assert "not approval" in template.lower()
    assert state["writes"] == before_writes
    assert (root / d136.GATE_PATH).read_bytes() == raw
    assert all(not (root / path).exists() for path in d136.FUTURE_PATHS)


def test_receipt_and_attempt_are_idempotent_committed_sole_artifact_boundaries(
    repository: tuple[Path, dict[str, Any]],
) -> None:
    root, state = repository
    _seal_gate(root, state)

    receipt_first = d136.create_d136_activation_receipt(repository=root)
    receipt_second = d136.create_d136_activation_receipt(repository=root)
    receipt_raw = (root / d136.RECEIPT_PATH).read_bytes()
    assert receipt_first == receipt_second
    assert receipt_first["status"] == d136.RECEIPT_STATUS
    assert receipt_first["receipt_commit"] is None
    assert receipt_first["commit_required_before_next_action"] is True
    assert receipt_first["external_call_count"] == 0
    assert state["writes"] == [d136.GATE_PATH, d136.RECEIPT_PATH]

    state["head"] = RECEIPT_COMMIT
    receipt_post = d136.validate_d136_activation_receipt(repository=root, mode="post-commit")
    assert receipt_post["receipt_commit"] == {
        "commit": RECEIPT_COMMIT,
        "tree": RECEIPT_TREE,
        "parents": [GATE_COMMIT],
        "artifact_path": d136.RECEIPT_PATH.as_posix(),
        "artifact_blob_oid": "b" * 40,
        "artifact_file_sha256": sha256_bytes(receipt_raw),
        "artifact_file_bytes": len(receipt_raw),
        "single_artifact_add_commit": True,
    }

    attempt_first = d136.create_d136_pricing_attempt(repository=root)
    attempt_second = d136.create_d136_pricing_attempt(repository=root)
    attempt_raw = (root / d136.ATTEMPT_PATH).read_bytes()
    assert attempt_first == attempt_second
    assert attempt_first["status"] == d136.ATTEMPT_STATUS
    assert attempt_first["attempt_commit"] is None
    assert attempt_first["commit_required_before_next_action"] is True
    assert attempt_first["external_call_count"] == 0
    assert state["writes"] == [d136.GATE_PATH, d136.RECEIPT_PATH, d136.ATTEMPT_PATH]

    state["head"] = ATTEMPT_COMMIT
    attempt_post = d136.validate_d136_pricing_attempt(repository=root, mode="post-commit")
    assert attempt_post["attempt_commit"] == {
        "commit": ATTEMPT_COMMIT,
        "tree": ATTEMPT_TREE,
        "parents": [RECEIPT_COMMIT],
        "artifact_path": d136.ATTEMPT_PATH.as_posix(),
        "artifact_blob_oid": "c" * 40,
        "artifact_file_sha256": sha256_bytes(attempt_raw),
        "artifact_file_bytes": len(attempt_raw),
        "single_artifact_add_commit": True,
    }
    assert all(not (root / path).exists() for path in (d136.STARTED_PATH, d136.TERMINAL_PATH))


def test_post_marker_failure_is_consumed_and_second_invocation_calls_helper_zero_times(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    calls = 0

    def fail_after_marker() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise RuntimeError("mocked post-marker failure")

    monkeypatch.setattr(pricing_capture, "capture_official_pricing_evidence", fail_after_marker)
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="failed after ACTION_STARTED"):
        d136.run_d136_fixed_pricing_capture(repository=root)

    marker = root / d136.STARTED_PATH
    marker_raw = marker.read_bytes()
    assert calls == 1
    assert not (root / d136.TERMINAL_PATH).exists()
    assert d136._status_lines(root) == [f"?? {d136.STARTED_PATH.as_posix()}"]
    pending = d136.validate_d136_action_started(repository=root, mode="pending-marker")
    assert pending["activation_consumed"] is True
    assert pending["retry_allowed"] is False
    assert pending["marker_preservation_commit"] is None

    with pytest.raises(d136.D136FixedPricingSuccessorError, match="retry is forbidden"):
        d136.run_d136_fixed_pricing_capture(repository=root)
    assert calls == 1
    assert marker.read_bytes() == marker_raw

    state["head"] = MARKER_ONLY_COMMIT
    preserved = d136.validate_d136_action_started(repository=root, mode="post-preservation-commit")
    assert preserved["marker_preservation_commit"] == {
        "commit": MARKER_ONLY_COMMIT,
        "tree": MARKER_ONLY_TREE,
        "parents": [ATTEMPT_COMMIT],
        "artifact_path": d136.STARTED_PATH.as_posix(),
        "artifact_blob_oid": "e" * 40,
        "artifact_file_sha256": sha256_bytes(marker_raw),
        "artifact_file_bytes": len(marker_raw),
        "single_artifact_add_commit": True,
    }
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="retry is forbidden"):
        d136.run_d136_fixed_pricing_capture(repository=root)
    assert calls == 1


@pytest.mark.parametrize("mutation", ("attempt", "started", "checkout"))
def test_post_helper_toctou_never_publishes_terminal_or_allows_retry(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    observation = _mock_pricing_evidence(monkeypatch)
    calls = 0

    def capture_then_mutate() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if mutation == "attempt":
            (root / d136.ATTEMPT_PATH).write_bytes(b"post-helper-attempt-tamper")
        elif mutation == "started":
            (root / d136.STARTED_PATH).write_bytes(b"post-helper-started-tamper")
        else:
            state["status_override"] = [
                f"?? {d136.STARTED_PATH.as_posix()}",
                "?? unrelated-checkout-drift",
            ]
        return copy.deepcopy(observation)

    monkeypatch.setattr(
        pricing_capture,
        "capture_official_pricing_evidence",
        capture_then_mutate,
    )
    with pytest.raises(d136.D136FixedPricingSuccessorError):
        d136.run_d136_fixed_pricing_capture(repository=root)

    marker = root / d136.STARTED_PATH
    assert marker.exists()
    assert not (root / d136.TERMINAL_PATH).exists()
    assert calls == 1

    with pytest.raises(d136.D136FixedPricingSuccessorError):
        d136.run_d136_fixed_pricing_capture(repository=root)
    assert calls == 1
    assert marker.exists()
    assert not (root / d136.TERMINAL_PATH).exists()


def test_success_capture_is_idempotent_and_exact_two_artifact_transition(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    observation = _mock_pricing_evidence(monkeypatch)
    calls = 0

    def capture_once() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return copy.deepcopy(observation)

    monkeypatch.setattr(pricing_capture, "capture_official_pricing_evidence", capture_once)
    first = d136.run_d136_fixed_pricing_capture(repository=root)
    second = d136.run_d136_fixed_pricing_capture(repository=root)
    third = d136.validate_d136_pricing_terminal(repository=root, mode="pending")

    assert first == second == third
    assert calls == 1
    assert first["status"] == d136.TERMINAL_STATUS
    assert first["success_transition_commit"] is None
    assert first["commit_required_before_successor"] is True
    assert first["official_public_get_send_count"] == 1
    assert first["provider_evaluator_agent_call_count"] == 0
    assert first["cost_reserved_or_spent_usd"] == "0"
    assert d136._status_lines(root) == sorted(
        [f"?? {d136.STARTED_PATH.as_posix()}", f"?? {d136.TERMINAL_PATH.as_posix()}"]
    )
    assert state["writes"] == [
        d136.GATE_PATH,
        d136.RECEIPT_PATH,
        d136.ATTEMPT_PATH,
        d136.STARTED_PATH,
        d136.TERMINAL_PATH,
    ]

    terminal_raw = (root / d136.TERMINAL_PATH).read_bytes()
    terminal = json.loads(terminal_raw)
    body = terminal["semantic_body"]
    assert body["observation"] == observation
    assert body["activity_accounting"]["pricing_helper_invocation_count"] == 1
    assert body["activity_accounting"]["official_public_get_send_count"] == 1
    assert body["activity_accounting"]["docker_cli_call_count"] == 0
    assert (
        body["activity_accounting"][
            "sdk_credential_dotenv_environment_value_or_endpoint_observation_count"
        ]
        == 0
    )
    assert body["activity_accounting"]["provider_evaluator_agent_call_count"] == 0
    assert body["authority"]["docker_or_sdk_no_call_preflight_authorized"] is False
    assert body["authority"]["execution_hash_or_candidate_created"] is False
    assert body["authority"]["cost_reserved_or_spent_usd"] == "0"
    assert body["authority"]["four_row_ac_executed"] is False
    assert body["next_gate"] == {
        "status": "D137_NO_CALL_PREFLIGHT_SUCCESSOR_OFFLINE_SOURCE_APPROVAL_REQUIRED",
        "fresh_separate_approval_required": True,
        "current_activation_authorizes_next_gate": False,
    }

    state["head"] = TERMINAL_COMMIT
    post = d136.validate_d136_pricing_terminal(repository=root, mode="post-transition-commit")
    assert post["success_transition_commit"] == {
        "commit": TERMINAL_COMMIT,
        "tree": TERMINAL_TREE,
        "parents": [ATTEMPT_COMMIT],
        "artifact_paths": [d136.STARTED_PATH.as_posix(), d136.TERMINAL_PATH.as_posix()],
        "artifact_blob_oids": {
            d136.STARTED_PATH.as_posix(): "f" * 40,
            d136.TERMINAL_PATH.as_posix(): "1" * 40,
        },
        "exact_action_started_and_terminal_add_commit": True,
    }
    assert d136.run_d136_fixed_pricing_capture(repository=root) == post
    assert calls == 1

    state["extra_diff"][TERMINAL_COMMIT] = [{"status": "M", "path": "README.md"}]
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="transition scope"):
        d136.validate_d136_pricing_terminal(repository=root, mode="post-transition-commit")


def test_future_artifact_collisions_and_orphans_fail_closed_without_helper(
    repository: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state = repository
    _seal_attempt(root, state)
    monkeypatch.setattr(
        pricing_capture,
        "capture_official_pricing_evidence",
        _forbidden("pricing helper"),
    )

    terminal = root / d136.TERMINAL_PATH
    terminal.write_bytes(b"orphan-pricing-terminal")
    with pytest.raises(d136.D136FixedPricingSuccessorError, match="terminal is orphaned"):
        d136.run_d136_fixed_pricing_capture(repository=root)
    assert terminal.read_bytes() == b"orphan-pricing-terminal"
    terminal.unlink()

    started = root / d136.STARTED_PATH
    started.write_bytes(b"foreign-action-started")
    with pytest.raises(d136.D136FixedPricingSuccessorError):
        d136.run_d136_fixed_pricing_capture(repository=root)
    assert started.read_bytes() == b"foreign-action-started"
    assert not terminal.exists()
