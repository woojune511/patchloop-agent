"""Public fixture source reads only; no model, target, Docker or evaluator execution."""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from diagnostics import source_ready_packet as source
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.probe_runtime import runtime
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

CALIBRATION = sha256_bytes(b"calibration")
WORKSPACE_PATH = "mini_data_utils/csvlite.py"
DEPENDENCY_PATH = "public_package/helper.py"


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("source packets may only read public source")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("patchloop.agent.model.create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.environment.load_exact_openai_api_key", forbidden)
    monkeypatch.setattr("patchloop.sandbox.probes.DockerProbeSandbox.run_probe", forbidden)
    monkeypatch.setattr("patchloop.sandbox.DockerSandbox.run_check", forbidden)
    monkeypatch.setattr("patchloop.sandbox.LocalSandbox.run_check", forbidden)


def _selection(origin="workspace", path=WORKSPACE_PATH, start=1, end=400):
    return {"origin": origin, "path": path, "start_line": start, "end_line": end}


def _frames(rows):
    return {"calls": [{"details": {
        "policy": "public-exception-frames-v1",
        "scope": "public_workspace_and_prepared_dependencies", "status": "complete",
        "exceptions": [{"relation": "escaped", "type": "builtins.RuntimeError",
                        "message": "failure", "message_source": "safe_exception_args",
                        "frames": rows, "excluded_frame_count": 0, "omitted_frame_count": 0}],
        "omissions": {},
    }}]}


def _loaded(gateway):
    public_path = repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml"
    return SimpleNamespace(
        public=gateway.public_task,
        data={"candidate_diff_hash": gateway.current_diff_hash}, dependencies=None,
        source=SimpleNamespace(public_path=public_path,
                               public_hash=sha256_bytes(public_path.read_bytes())),
        rows={"candidate": {"output": {"exception_diagnostics": _frames([{
            "origin": "workspace", "path": WORKSPACE_PATH, "line": 1, "function": "parse_rows",
            "file_hash": sha256_bytes((gateway.workspace / WORKSPACE_PATH).read_bytes()),
        }])}}},
    )


def _dependency(loaded, root):
    path = root / "site-packages" / DEPENDENCY_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(b"def helper():\r\n    return 42\r\n")
    files = {DEPENDENCY_PATH: sha256_bytes(path.read_bytes())}
    python, image = runtime("python312-v1")
    descriptor = root / "prepared-probe-dependencies.json"
    descriptor.write_text(canonical_json({
        "schema_version": "prepared-probe-dependencies-v1", "image": image,
        "python": python, "platform": "linux/amd64", "source_roots": [],
        "repository_url": loaded.public.repository.url,
        "base_commit": loaded.public.repository.base_commit,
        "content_hash": sha256_json(files), "files": files,
    }), encoding="utf-8")
    loaded.dependencies = PreparedDependencies(
        descriptor, read_descriptor(descriptor)[1], loaded.public.repository.url,
        loaded.public.repository.base_commit)
    frames = loaded.rows["candidate"]["output"]["exception_diagnostics"]["calls"][0]["details"]
    frames["exceptions"][0]["frames"].append({
        "origin": "dependency", "path": DEPENDENCY_PATH, "line": 2, "function": "helper",
        "file_hash": files[DEPENDENCY_PATH],
    })
    return path


def test_builder_normalizes_actual_registered_range_and_rechecks_hashes(gateway_factory, tmp_path):
    gateway, journal, _ = gateway_factory()
    loaded = _loaded(gateway)
    path = _dependency(loaded, tmp_path / "prepared")
    selections = [_selection(path=WORKSPACE_PATH.replace("/", "\\")),
                  _selection("dependency", DEPENDENCY_PATH, 1, 20)]
    before = copy.deepcopy(selections)
    packet = source.build_packet(loaded, gateway, CALIBRATION, selections)
    assert selections == before
    assert set(packet) == {"schema", "calibration_hash", "candidate_diff_hash",
                           "public_hash", "sources"}
    workspace, dependency = packet["sources"]
    assert workspace["path"] == WORKSPACE_PATH and workspace["end_line"] < 400
    assert dependency["start_line"] == 1 and dependency["end_line"] == 2
    assert dependency["content"] == "def helper():\n    return 42"
    assert dependency["file_hash"] == sha256_bytes(path.read_bytes())
    reads = [event["payload"]["result"] for event in journal.events()
             if event["event_type"] == "action_finished"]
    assert [row["tool"] for row in reads] == ["read_file"]
    span = reads[0]["output"]["spans"][0]
    assert workspace == {"origin": "workspace", **{key: span[key] for key in
        ("path", "start_line", "end_line", "content", "file_hash")}}
    assert source.validate_packet(loaded, packet, CALIBRATION, gateway.workspace) is None
    path.write_bytes(b"def helper():\n    return 99\n")
    with pytest.raises(ContractError, match="dependency source changed"):
        source.validate_packet(loaded, packet, CALIBRATION)


def test_candidate_and_packet_drift_fail_without_mutating_packet(gateway_factory):
    gateway, _, workspace = gateway_factory()
    loaded = _loaded(gateway)
    packet = source.build_packet(loaded, gateway, CALIBRATION, [_selection()])
    before = copy.deepcopy(packet)
    assert source.validate_packet(loaded, packet, CALIBRATION) is None
    assert packet == before
    with pytest.raises(ContractError, match="calibration"):
        source.validate_packet(loaded, packet, sha256_bytes(b"other"))
    changed = copy.deepcopy(packet)
    changed["sources"][0]["content"] = changed["sources"][0]["content"].replace("def ", "xxx ", 1)
    with pytest.raises(ContractError, match="content changed"):
        source.validate_packet(loaded, changed, CALIBRATION, workspace)
    with pytest.raises(ContractError, match="observation differs"):
        source.observe_sources(gateway, changed)
    path = workspace / WORKSPACE_PATH
    path.write_bytes(path.read_bytes() + b"# drift\n")
    with pytest.raises(ContractError, match="candidate diff changed"):
        source.validate_packet(loaded, packet, CALIBRATION, workspace)
    with pytest.raises(ContractError, match="candidate diff changed"):
        source.observe_sources(gateway, packet)


def test_traversal_private_and_unprepared_dependencies_are_rejected(gateway_factory, tmp_path):
    gateway, journal, _ = gateway_factory()
    loaded = _loaded(gateway)
    for path in ("../secret.py", "/secret.py", "C:/secret.py", ".", ".git/config",
                 ".patchloop-hidden/private.py", ".env"):
        with pytest.raises(ContractError):
            source.build_packet(loaded, gateway, CALIBRATION, [_selection(path=path)])
    assert not journal.events()
    _dependency(loaded, tmp_path / "prepared")
    outside = loaded.dependencies.path.parent / "site-packages/unprepared.py"
    outside.write_text("PRIVATE = 'not admitted'\n", encoding="utf-8")
    with pytest.raises(ContractError, match="not an admitted"):
        source.build_packet(loaded, gateway, CALIBRATION,
                            [_selection("dependency", "unprepared.py")])


def test_dependency_requires_candidate_frame_and_matching_inventory_identity(gateway_factory,
                                                                           tmp_path):
    gateway, _, _ = gateway_factory()
    loaded = _loaded(gateway)
    _dependency(loaded, tmp_path / "prepared")
    selection = [_selection("dependency", DEPENDENCY_PATH)]
    packet = source.build_packet(loaded, gateway, CALIBRATION, selection)
    frames = loaded.rows["candidate"]["output"]["exception_diagnostics"]["calls"][0]["details"]
    dependency_frame = frames["exceptions"][0]["frames"].pop()
    with pytest.raises(ContractError, match="not captured"):
        source.validate_packet(loaded, packet, CALIBRATION)
    dependency_frame["file_hash"] = sha256_bytes(b"wrong frame")
    frames["exceptions"][0]["frames"].append(dependency_frame)
    with pytest.raises(ContractError, match="candidate exception frames"):
        source.validate_packet(loaded, packet, CALIBRATION)
    loaded.dependencies.path.write_text(loaded.dependencies.path.read_text() + "\n")
    with pytest.raises(ContractError, match="dependency identity changed"):
        source.validate_packet(loaded, packet, CALIBRATION)


def test_source_limits_and_exact_schema_are_enforced(gateway_factory):
    gateway, _, _ = gateway_factory()
    loaded = _loaded(gateway)
    for selections in ([_selection()] * 9, [_selection(end=401)]):
        with pytest.raises(ContractError):
            source.build_packet(loaded, gateway, CALIBRATION, selections)
    packet = source.build_packet(loaded, gateway, CALIBRATION, [_selection()])
    for extra in ("instructions", "repair_hint", "command"):
        changed = {**packet, extra: "not source"}
        with pytest.raises(ContractError, match="schema"):
            source.validate_packet(loaded, changed, CALIBRATION)
    changed = copy.deepcopy(packet)
    changed["sources"] = [copy.deepcopy(packet["sources"][0]) for _ in range(8)]
    for index, row in enumerate(changed["sources"]):
        row.update(start_line=index + 1, end_line=index + 1, content="x" * 3001)
    with pytest.raises(ContractError, match="24000"):
        source.validate_packet(loaded, changed, CALIBRATION)


def test_fresh_registered_observation_allows_the_existing_exact_edit(gateway_factory):
    prepared, _, _ = gateway_factory()
    loaded = _loaded(prepared)
    packet = source.build_packet(loaded, prepared, CALIBRATION, [_selection()])
    gateway, journal, workspace = gateway_factory()
    assert not gateway.spans
    source.validate_packet(loaded, packet, CALIBRATION, workspace)
    assert source.observe_sources(gateway, packet) is None
    assert gateway.spans
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    result = gateway.execute(RequestedTool(name="replace_text", action_id="source-ready-edit",
        arguments={"path": mutation.path, "old_text": mutation.old_text,
                   "new_text": mutation.new_text, "occurrence": 1,
                   "hypothesis": mutation.hypothesis,
                   "expected_behavior": mutation.expected_behavior}))
    assert result.status == "succeeded", result.message
    assert gateway.accepted_mutations == 1
    actions = [event["payload"]["result"]["tool"] for event in journal.events()
               if event["event_type"] == "action_finished"]
    assert actions == ["read_file", "replace_text"]
