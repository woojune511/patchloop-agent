from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.errors import ContractError
from patchloop.evals import qualification as qualification_module
from patchloop.evals import qualification_corrections as correction_module
from patchloop.evals.qualification import qualify_run
from patchloop.evals.qualification_corrections import (
    create_qualification_correction,
)
from patchloop.util import canonical_json, sha256_text

TASK = Path("tasks/smoke/csv-quoted-newline")
HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)


def _qualification(*, corrected: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "trace-qualification-v2",
        "run_id": "run_correction_test",
        "source_evidence_hash": HASH_A,
        "harness_git_commit": "1" * 40,
        "qualified": corrected,
        "trace_integrity_passed": corrected,
        "checks": [
            {
                "check_id": "task_identity",
                "passed": True,
                "details": {},
            },
            {
                "check_id": "investigation_evidence",
                "passed": corrected,
                "details": {},
            },
        ],
    }
    payload["qualification_hash"] = sha256_text(canonical_json(payload))
    return payload


def _arrange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, object], Path, bytes]:
    original = _qualification()
    corrected = _qualification(corrected=True)
    original_path = (
        tmp_path / "qualifications" / "run_correction_test.json"
    )
    original_path.parent.mkdir(parents=True)
    original_path.write_text(
        json.dumps(original, indent=2),
        encoding="utf-8",
    )
    original_bytes = original_path.read_bytes()
    monkeypatch.setattr(
        correction_module,
        "load_trace_qualification",
        lambda *_args, **_kwargs: original,
    )
    monkeypatch.setattr(
        correction_module,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: HASH_A,
    )

    def recompute(*_args, **kwargs):
        assert kwargs["persist"] is False
        return corrected

    monkeypatch.setattr(correction_module, "qualify_run", recompute)
    monkeypatch.setattr(
        correction_module,
        "_current_harness_identity",
        lambda: {
            "git_commit": "2" * 40,
            "package_version": "0.1.0",
        },
    )
    return original, corrected, original_path, original_bytes


def test_correction_is_append_only_content_addressed_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original, corrected, original_path, original_bytes = _arrange(
        tmp_path,
        monkeypatch,
    )

    first = create_qualification_correction(
        "run_correction_test",
        task_dir=TASK,
        expected_original_qualification_hash=str(
            original["qualification_hash"]
        ),
        expected_source_evidence_hash=HASH_A,
        reason="v7 verifier reserve drift",
        root=tmp_path,
    )
    second = create_qualification_correction(
        "run_correction_test",
        task_dir=TASK,
        expected_original_qualification_hash=str(
            original["qualification_hash"]
        ),
        expected_source_evidence_hash=HASH_A,
        reason="v7 verifier reserve drift",
        root=tmp_path,
    )

    assert second == first
    assert original_path.read_bytes() == original_bytes
    correction_files = list(
        (tmp_path / "qualification-corrections").rglob("*.json")
    )
    assert len(correction_files) == 1
    assert correction_files[0].stem == first["correction_id"]
    assert first["schema_version"] == (
        "trace-qualification-correction-v1"
    )
    assert first["run_id"] == "run_correction_test"
    assert first["source_evidence_hash"] == HASH_A
    assert first["original_qualification_hash"] == original[
        "qualification_hash"
    ]
    assert first["reason"] == "v7 verifier reserve drift"
    assert isinstance(first["created_at"], str)
    assert first["correction_harness"] == {
        "git_commit": "2" * 40,
        "package_version": "0.1.0",
    }
    assert first["original_failed_check_ids"] == [
        "investigation_evidence"
    ]
    assert first["corrected_failed_check_ids"] == []
    assert first["corrected_qualification_hash"] == corrected[
        "qualification_hash"
    ]
    assert "qualification_hash" not in first[
        "corrected_qualification_semantics"
    ]
    unhashed = {
        key: value
        for key, value in first.items()
        if key != "correction_hash"
    }
    assert first["correction_hash"] == sha256_text(
        canonical_json(unhashed)
    )


def test_correction_rejects_wrong_original_approval_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, original_path, original_bytes = _arrange(tmp_path, monkeypatch)

    with pytest.raises(
        ContractError,
        match="original qualification hash does not match approval",
    ):
        create_qualification_correction(
            "run_correction_test",
            task_dir=TASK,
            expected_original_qualification_hash=HASH_B,
            expected_source_evidence_hash=HASH_A,
            reason="v7 verifier reserve drift",
            root=tmp_path,
        )

    assert original_path.read_bytes() == original_bytes
    assert not (tmp_path / "qualification-corrections").exists()


def test_correction_rejects_changed_source_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original, _, original_path, original_bytes = _arrange(
        tmp_path,
        monkeypatch,
    )
    monkeypatch.setattr(
        correction_module,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: HASH_B,
    )

    with pytest.raises(
        ContractError,
        match="qualification source evidence changed",
    ):
        create_qualification_correction(
            "run_correction_test",
            task_dir=TASK,
            expected_original_qualification_hash=str(
                original["qualification_hash"]
            ),
            expected_source_evidence_hash=HASH_A,
            reason="v7 verifier reserve drift",
            root=tmp_path,
        )

    assert original_path.read_bytes() == original_bytes
    assert not (tmp_path / "qualification-corrections").exists()


def test_correction_never_overwrites_tampered_existing_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original, _, original_path, original_bytes = _arrange(
        tmp_path,
        monkeypatch,
    )
    kwargs = {
        "task_dir": TASK,
        "expected_original_qualification_hash": original[
            "qualification_hash"
        ],
        "expected_source_evidence_hash": HASH_A,
        "reason": "v7 verifier reserve drift",
        "root": tmp_path,
    }
    created = create_qualification_correction(
        "run_correction_test",
        **kwargs,
    )
    path = next(
        (tmp_path / "qualification-corrections").rglob("*.json")
    )
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(
        ContractError,
        match="correction artifact integrity failed",
    ):
        create_qualification_correction(
            "run_correction_test",
            **kwargs,
        )

    assert path.read_text(encoding="utf-8") == "{}"
    assert original_path.read_bytes() == original_bytes
    assert created["correction_id"] == path.stem


def test_qualify_run_persist_false_recomputes_without_touching_original(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(TASK / "public.yaml", model="mock")
    first = qualify_run(
        result["run_id"],
        task_dir=TASK,
        root=runner.root,
    )
    path = runner.root / "qualifications" / f"{result['run_id']}.json"
    original_bytes = path.read_bytes()
    monkeypatch.setattr(
        qualification_module,
        "_v4_investigation_lifecycle_evidence",
        lambda **_kwargs: (
            False,
            {
                "semantic_replay_count": 0,
                "verified_semantic_replay_count": 0,
                "failed_semantic_replay_sequences": [],
                "admission_block_count": 0,
                "verified_admission_block_count": 0,
                "failed_admission_block_sequences": [1],
            },
        ),
    )

    recomputed = qualify_run(
        result["run_id"],
        task_dir=TASK,
        root=runner.root,
        persist=False,
    )

    assert recomputed["qualification_hash"] != first["qualification_hash"]
    assert path.read_bytes() == original_bytes
    with pytest.raises(ContractError, match="trace qualification is immutable"):
        qualify_run(
            result["run_id"],
            task_dir=TASK,
            root=runner.root,
        )
