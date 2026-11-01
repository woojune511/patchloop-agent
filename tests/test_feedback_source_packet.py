"""Small offline checks of the public-only feedback projection."""
from __future__ import annotations

import copy
import json

import pytest

from diagnostics import feedback_source_packet as p
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def observation(*, base=False):
    return {"schema_version": "public-changed-line-feedback-v1",
            "status": "not_applicable" if base else "collected",
            "scope": "python_launch_thread",
            "diff_hash": p.selection.EMPTY_DIFF if base else "seed",
            "diagnostic_only": True, "deleted_line_count": 0, "omitted_file_count": 0,
            "files": [], "interpretation": "OPERATOR_HINT_DO_NOT_PROJECT"}


def test_original_projection_omits_authored_judgment_and_operator_interpretation():
    raw = {"workspace_diff_hash": "seed", "output": {
        "reproduction": {"call_observation": {"calls": [{"capture": {"stdout": "F0010"}}]},
                         "judgment": "PRIVATE_SENTINEL", "interpretation": "OPERATOR_HINT"},
        "exception_diagnostics": {"status": "complete"},
        "public_execution": observation(), "acceptance": "PRIVATE_SENTINEL"}}
    before = copy.deepcopy(raw)
    value = p.original_public(raw)
    serialized = canonical_json(value)
    assert "PRIVATE_SENTINEL" not in serialized and "OPERATOR_HINT" not in serialized
    assert "F0010" in serialized and raw == before
    assert value["changed_line_observation"]["scope"] == "python_launch_thread"


def test_base_trace_is_inapplicable_but_candidate_trace_must_be_collected():
    result = p.changed_lines({"public_execution": observation(base=True)})
    assert result["status"] == "not_applicable"
    bad = observation()
    bad["status"] = "not_applicable"
    with pytest.raises(ContractError, match="incomplete"):
        p.changed_lines({"public_execution": bad})


def test_receipt_requires_public_store_and_exact_bytes(tmp_path):
    path = tmp_path / "artifacts/objects/sha256/aa/receipt"
    path.parent.mkdir(parents=True)
    raw = b'{"measured":true}'
    path.write_bytes(raw)
    ref = {"path": str(path), "content_hash": sha256_bytes(raw), "size_bytes": len(raw)}
    bindings = {}
    assert p.read_receipt(ref, bindings, root=tmp_path) == {"measured": True}
    assert len(bindings) == 1
    with pytest.raises(ContractError, match="outside"):
        p.read_receipt({**ref, "path": str(tmp_path / "acceptance.json")}, bindings, root=tmp_path)
    path.write_text(json.dumps({"measured": False}), encoding="utf-8")
    with pytest.raises(ContractError, match="changed"):
        p.read_receipt(ref, bindings, root=tmp_path)


def test_complete_source_is_contiguous_and_hunk_does_not_hide_append(monkeypatch):
    lines = [f"line_{number}" for number in range(1, 677)]
    lines[264] = "        modpath.append(part)"
    raw = ("\n".join(lines) + "\n").encode()
    monkeypatch.setattr(p, "FILE_HASH", sha256_bytes(raw))
    packets = p.make_sources(raw)
    assert [(s["start_line"], s["end_line"]) for s in packets["R1"]] == [(1, 400), (401, 676)]
    combined = "\n".join(s["content"] for s in packets["R1"])
    assert combined.splitlines() == lines
    assert [(s["start_line"], s["end_line"]) for s in packets["R0"]] == [(265, 273)]
    assert "modpath.append(part)" in packets["R0"][0]["content"]
    with pytest.raises(ContractError, match="source changed"):
        p.make_sources(raw + b"changed")
