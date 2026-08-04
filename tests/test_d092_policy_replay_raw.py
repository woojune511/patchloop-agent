from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".patchloop/state.sqlite3"
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/artifacts/d092-public-policy-replay-decision.json"
)
BUILDER_PATH = ROOT / "scripts/build_d092_policy_decision.py"


def _builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("d092_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("D-092 builder module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stat(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    value = path.stat()
    return value.st_size, value.st_mtime_ns


def test_d092_builder_source_has_exact_read_only_sql_boundary() -> None:
    source = BUILDER_PATH.read_text(encoding="utf-8")
    select_statements = re.findall(r'"(SELECT [^"]+)"', source)

    assert select_statements == [
        "SELECT manifest_json FROM runs WHERE run_id = ?",
        "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
    ]
    assert '"PRAGMA query_only=ON"' in source
    assert '"PRAGMA query_only"' in source
    assert '?mode=ro&immutable=1"' in source
    for forbidden in (
        "SELECT result_json",
        "StateStore",
        "load_trace_qualification",
        ".patchloop/qualifications",
        "private.yaml",
        "artifacts/objects",
    ):
        assert forbidden not in source


def test_d092_raw_public_replay_exactly_rebuilds_portable_manifest() -> None:
    if not STATE_PATH.is_file():
        pytest.skip("local immutable public run metadata is unavailable")
    payload: dict[str, Any] = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    builder = _builder()
    before = {
        path.name: _stat(path)
        for path in (
            STATE_PATH,
            STATE_PATH.with_name(STATE_PATH.name + "-wal"),
            STATE_PATH.with_name(STATE_PATH.name + "-shm"),
        )
    }

    rebuilt = builder.build_manifest(
        repo_root=ROOT,
        state_path=STATE_PATH,
        recorded_at=payload["semantic_body"]["recorded_at"],
    )

    after = {
        path.name: _stat(path)
        for path in (
            STATE_PATH,
            STATE_PATH.with_name(STATE_PATH.name + "-wal"),
            STATE_PATH.with_name(STATE_PATH.name + "-shm"),
        )
    }
    assert rebuilt == payload
    assert after == before
    projection = rebuilt["semantic_body"]["replay_projection"]
    assert len(projection["runs"]) == 18
    assert sum(row["event_count"] for row in projection["runs"]) == 4_079
    assert all(
        row["evaluation"]["admitted"] is False
        for section in (
            "repeated_rejection",
            "relative_context_growth",
            "absolute_context_sensitivity",
        )
        for row in projection[section]
    )
