from __future__ import annotations

import copy
import inspect
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.structured_edit import (
    STRUCTURED_EDIT_TOOL_SCHEMA_V1,
    AtomicStructuredEditProjection,
    StructuredEditArguments,
    StructuredFileEdit,
    StructuredReplacement,
    project_atomic_structured_edit,
)
from patchloop.agent.tools import TOOL_SCHEMAS
from patchloop.contracts import TaskConstraints
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]
SHA = "sha256:" + "1" * 64


def _replacement(
    raw: bytes,
    old: str,
    new: str,
    *,
    occurrence: int = 1,
) -> StructuredReplacement:
    old_bytes = old.encode("utf-8")
    cursor = 0
    start = -1
    for _ in range(occurrence):
        start = raw.index(old_bytes, cursor)
        cursor = start + len(old_bytes)
    return StructuredReplacement(
        start_byte=start,
        end_byte=start + len(old_bytes),
        expected_text=old,
        replacement_text=new,
    )


def _arguments(
    files: tuple[tuple[str, bytes, tuple[StructuredReplacement, ...]], ...],
) -> StructuredEditArguments:
    return StructuredEditArguments(
        source_worktree_diff_hash=SHA,
        files=tuple(
            StructuredFileEdit(
                path=path,
                preimage_file_sha256=sha256_bytes(raw),
                replacements=replacements,
            )
            for path, raw, replacements in files
        ),
    )


def _project(
    arguments: StructuredEditArguments,
    preimages: dict[str, bytes],
    *,
    action_id: str = "structured-edit-action",
    constraints: TaskConstraints | None = None,
) -> AtomicStructuredEditProjection:
    return project_atomic_structured_edit(
        action_id=action_id,
        arguments=arguments,
        preimages=preimages,
        constraints=constraints
        or TaskConstraints(
            allowed_paths=["src/**"],
            max_changed_files=4,
            max_diff_lines=120,
        ),
    )


def _rehash(body: dict[str, Any]) -> dict[str, Any]:
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return body


def test_exact_byte_span_builds_reversible_postimage_without_writing() -> None:
    raw = b"alpha\nbeta\ngamma\n"
    arguments = _arguments((("src/example.py", raw, (_replacement(raw, "beta", "delta"),)),))
    preimages = {"src/example.py": raw}
    before = copy.deepcopy(preimages)

    projected = _project(arguments, preimages)

    assert preimages == before
    assert projected.files[0].preimage_text == raw.decode("utf-8")
    assert projected.files[0].postimage_text == "alpha\ndelta\ngamma\n"
    assert projected.files[0].preimage_file_sha256 == sha256_bytes(raw)
    assert projected.files[0].postimage_file_sha256 == sha256_bytes(b"alpha\ndelta\ngamma\n")
    assert projected.files[0].added_lines == 1
    assert projected.files[0].deleted_lines == 1
    assert projected.logical_diff_lines == 2
    assert projected.all_preimages_validated is True
    assert projected.atomic_commit_required is True
    assert projected.rollback_preimages_bound is True
    assert projected.workspace_writes_performed == 0
    assert projected.raw_diff_generation_required is False
    assert projected.runtime_activation_authorized is False
    assert projected.state_mutation_authorized is False
    assert projected.provider_calls_authorized is False


def test_multi_file_projection_validates_all_files_before_returning() -> None:
    first = b"first old\n"
    second = b"second old\n"
    arguments = _arguments(
        (
            ("src/first.py", first, (_replacement(first, "old", "new"),)),
            ("src/second.py", second, (_replacement(second, "old", "new"),)),
        )
    )
    preimages = {"src/first.py": first, "src/second.py": second}

    projected = _project(arguments, preimages)

    assert projected.changed_file_count == 2
    assert projected.replacement_count == 2
    assert tuple(item.path for item in projected.files) == (
        "src/first.py",
        "src/second.py",
    )
    assert projected.preimage_set_hash != projected.postimage_set_hash
    assert preimages == {"src/first.py": first, "src/second.py": second}


def test_stale_hash_or_span_fails_before_any_mutation() -> None:
    raw = b"before target after\n"
    arguments = _arguments((("src/example.py", raw, (_replacement(raw, "target", "fixed"),)),))
    stale = {"src/example.py": b"before changed after\n"}
    stale_before = copy.deepcopy(stale)

    with pytest.raises(ValueError, match="preimage file hash differs"):
        _project(arguments, stale)
    assert stale == stale_before

    body = arguments.model_dump(mode="python")
    body["files"][0]["preimage_file_sha256"] = sha256_bytes(stale["src/example.py"])
    stale_arguments = StructuredEditArguments.model_validate(body)
    with pytest.raises(ValueError, match="text differs from its byte span"):
        _project(stale_arguments, stale)
    assert stale == stale_before


def test_utf8_offsets_and_crlf_bytes_are_preserved_exactly() -> None:
    raw = "첫째\r\n둘째 target\r\n".encode()
    arguments = _arguments((("src/unicode.py", raw, (_replacement(raw, "target", "완료"),)),))

    projected = _project(arguments, {"src/unicode.py": raw})

    assert projected.files[0].postimage_text == "첫째\r\n둘째 완료\r\n"
    assert projected.files[0].postimage_text.encode() == "첫째\r\n둘째 완료\r\n".encode()


def test_unsorted_overlapping_empty_or_noop_spans_are_rejected() -> None:
    with pytest.raises(ValidationError, match="nonempty"):
        StructuredReplacement(
            start_byte=1,
            end_byte=1,
            expected_text="x",
            replacement_text="y",
        )
    with pytest.raises(ValidationError, match="must change"):
        StructuredReplacement(
            start_byte=0,
            end_byte=1,
            expected_text="x",
            replacement_text="x",
        )
    with pytest.raises(ValidationError, match="ordered"):
        StructuredFileEdit(
            path="src/example.py",
            preimage_file_sha256=SHA,
            replacements=(
                StructuredReplacement(
                    start_byte=4,
                    end_byte=5,
                    expected_text="b",
                    replacement_text="B",
                ),
                StructuredReplacement(
                    start_byte=0,
                    end_byte=1,
                    expected_text="a",
                    replacement_text="A",
                ),
            ),
        )
    with pytest.raises(ValidationError, match="must not overlap"):
        StructuredFileEdit(
            path="src/example.py",
            preimage_file_sha256=SHA,
            replacements=(
                StructuredReplacement(
                    start_byte=0,
                    end_byte=3,
                    expected_text="abc",
                    replacement_text="A",
                ),
                StructuredReplacement(
                    start_byte=2,
                    end_byte=4,
                    expected_text="cd",
                    replacement_text="D",
                ),
            ),
        )


@pytest.mark.parametrize(
    ("path", "constraints", "message"),
    [
        ("../escape.py", TaskConstraints(allowed_paths=["**"]), "safe relative"),
        (
            "other/example.py",
            TaskConstraints(allowed_paths=["src/**"]),
            "outside allowed paths",
        ),
        (
            "src/secret.py",
            TaskConstraints(allowed_paths=["src/**"], forbidden_paths=["src/secret.py"]),
            "forbidden",
        ),
    ],
)
def test_path_boundary_is_fail_closed(
    path: str,
    constraints: TaskConstraints,
    message: str,
) -> None:
    raw = b"old\n"
    replacement = _replacement(raw, "old", "new")
    if path.startswith(".."):
        with pytest.raises((ValidationError, ValueError), match=message):
            _arguments(((path, raw, (replacement,)),))
        return
    arguments = _arguments(((path, raw, (replacement,)),))
    with pytest.raises(ValueError, match=message):
        _project(arguments, {path: raw}, constraints=constraints)


def test_changed_file_and_logical_diff_limits_are_enforced() -> None:
    first = b"old one\n"
    second = b"old two\n"
    arguments = _arguments(
        (
            ("src/first.py", first, (_replacement(first, "old", "new"),)),
            ("src/second.py", second, (_replacement(second, "old", "new"),)),
        )
    )
    preimages = {"src/first.py": first, "src/second.py": second}

    with pytest.raises(ValueError, match="changed-file limit"):
        _project(
            arguments,
            preimages,
            constraints=TaskConstraints(allowed_paths=["src/**"], max_changed_files=1),
        )
    with pytest.raises(ValueError, match="logical diff limit"):
        _project(
            arguments,
            preimages,
            constraints=TaskConstraints(
                allowed_paths=["src/**"],
                max_changed_files=2,
                max_diff_lines=3,
            ),
        )


def test_preimage_mapping_must_be_exact_and_utf8_text() -> None:
    raw = b"old\n"
    arguments = _arguments((("src/example.py", raw, (_replacement(raw, "old", "new"),)),))

    with pytest.raises(ValueError, match="exactly match"):
        _project(arguments, {})
    with pytest.raises(ValueError, match="exactly match"):
        _project(arguments, {"src/example.py": raw, "src/extra.py": b"extra\n"})
    invalid = b"\xff\xfe"
    invalid_body = arguments.model_dump(mode="python")
    invalid_body["files"][0]["preimage_file_sha256"] = sha256_bytes(invalid)
    invalid_arguments = StructuredEditArguments.model_validate(invalid_body)
    with pytest.raises(ValueError, match="not UTF-8"):
        _project(invalid_arguments, {"src/example.py": invalid})


def test_projection_is_deterministic_and_action_identity_is_separate() -> None:
    raw = b"old\n"
    arguments = _arguments((("src/example.py", raw, (_replacement(raw, "old", "new"),)),))
    preimages = {"src/example.py": raw}

    first = _project(arguments, preimages)
    replay = _project(arguments, preimages)
    other_action = _project(arguments, preimages, action_id="other-action")

    assert first == replay
    assert first.content_hash == replay.content_hash
    assert first.input_hash == other_action.input_hash
    assert first.action_identity_hash != other_action.action_identity_hash


def test_rehashed_postimage_or_authority_drift_is_rejected() -> None:
    raw = b"old\n"
    projected = _project(
        _arguments((("src/example.py", raw, (_replacement(raw, "old", "new"),)),)),
        {"src/example.py": raw},
    )
    body = projected.model_dump(mode="python")
    files = list(body["files"])
    files[0]["postimage_text"] = "tampered\n"
    files[0]["postimage_bytes"] = len(b"tampered\n")
    files[0]["postimage_file_sha256"] = sha256_bytes(b"tampered\n")
    files[0] = _rehash(files[0])
    body["files"] = tuple(files)
    body["postimage_set_hash"] = sha256_json(
        [
            {
                "path": "src/example.py",
                "file_sha256": sha256_bytes(b"tampered\n"),
                "file_bytes": len(b"tampered\n"),
            }
        ]
    )
    body = _rehash(body)

    with pytest.raises(ValidationError, match="postimage differs"):
        AtomicStructuredEditProjection.model_validate(body)

    authority = projected.model_dump(mode="python")
    authority["runtime_activation_authorized"] = True
    authority = _rehash(authority)
    with pytest.raises(ValidationError):
        AtomicStructuredEditProjection.model_validate(authority)


def test_tool_schema_is_strict_condition_neutral_and_versioned_runtime_only() -> None:
    runner_source = (REPOSITORY / "patchloop/agent/runner.py").read_text(encoding="utf-8")
    gateway_source = (REPOSITORY / "patchloop/agent/tools.py").read_text(encoding="utf-8")
    projector_source = inspect.getsource(project_atomic_structured_edit)

    assert STRUCTURED_EDIT_TOOL_SCHEMA_V1["name"] == "apply_structured_edit"
    assert STRUCTURED_EDIT_TOOL_SCHEMA_V1["strict"] is True
    assert STRUCTURED_EDIT_TOOL_SCHEMA_V1["parameters"]["additionalProperties"] is False
    assert STRUCTURED_EDIT_TOOL_SCHEMA_V1["parameters"]["required"] == [
        "schema_version",
        "source_worktree_diff_hash",
        "files",
    ]
    assert "condition" not in inspect.signature(project_atomic_structured_edit).parameters
    assert "apply_structured_edit" not in {item["name"] for item in TOOL_SCHEMAS}
    assert "patchloop.agent.structured_edit" not in runner_source
    assert "apply_structured_edit requires the exact v7/v12, v8/v13, " in gateway_source
    assert "v9/v13, v9/v14, v10/v15, v10/v16, v11/v17, or " in gateway_source
    assert "v17/v23, v18/v24, v19/v25, v20/v26, v21/v27, v22/v28, " in gateway_source
    assert "or v23/v29 runtime" in gateway_source
    assert '("v7", "phase-evidence-v12")' in gateway_source
    assert '("v8", "phase-evidence-v13")' in gateway_source
    assert '("v9", "phase-evidence-v13")' in gateway_source
    assert '("v9", "phase-evidence-v14")' in gateway_source
    assert '("v10", "phase-evidence-v15")' in gateway_source
    assert '("v10", "phase-evidence-v16")' in gateway_source
    assert '("v21", "phase-evidence-v27")' in gateway_source
    assert '("v22", "phase-evidence-v28")' in gateway_source
    assert '("v23", "phase-evidence-v29")' in gateway_source
    assert "Path(" not in projector_source
    assert "open(" not in projector_source
    assert "subprocess" not in projector_source
