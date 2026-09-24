from __future__ import annotations

import subprocess

from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MOCK_MUTATIONS
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json


class CountingFailSandbox:
    official = False

    def __init__(self) -> None:
        self.calls = 0

    def run_check(self, workspace, check):
        del workspace, check
        self.calls += 1
        return SandboxResult(
            command=["fake-check"],
            exit_code=1,
            stdout="same public failure",
            stderr="",
            duration_ms=1,
            timed_out=False,
            truncated=False,
            original_output_bytes=19,
        )


class InlineFailureSandbox:
    official = False

    def __init__(self, line: int) -> None:
        self.line = line

    def run_check(self, workspace, check):
        del workspace, check
        return SandboxResult(
            command=["python", "-c", "public-check"],
            exit_code=1,
            stdout="",
            stderr=(
                "Traceback (most recent call last):\n"
                f'  File "<string>", line {self.line}, in <module>\n'
                "AssertionError\n"
            ),
            duration_ms=1,
            timed_out=False,
            truncated=False,
            original_output_bytes=96,
        )


def inspection_decision(label: str = "source") -> PublicTurnDecision:
    return PublicTurnDecision(
        mode="inspect",
        basis=f"inspect-basis-{label}",
        evidence_goal=f"inspect-goal-{label}",
    )


def read_calls() -> list[RequestedTool]:
    decision = inspection_decision()
    return [
        RequestedTool(
            name="search_files",
            action_id="search-source",
            arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
            turn_decision=decision,
        ),
        RequestedTool(
            name="read_file",
            action_id="read-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 80,
            },
            turn_decision=decision,
        ),
    ]


def mutation_call(gateway, *, action_id: str = "mutation-1", alternative: bool = False):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    return RequestedTool(
        name="replace_text",
        action_id=action_id,
        arguments={
            "path": mutation.path,
            "old_text": mutation.old_text,
            "new_text": mutation.new_text,
            "occurrence": 1,
            "hypothesis": mutation.hypothesis,
            "expected_behavior": mutation.expected_behavior,
            "causal_revision": (
                {
                    "falsified_prior_hypothesis": ("physical line handling was the only cause"),
                    "alternative_mechanism": (
                        "parser lifetime, not line normalization, owns record boundaries"
                    ),
                }
                if alternative
                else None
            ),
        },
        turn_decision=PublicTurnDecision(
            mode="mutate",
            basis="The inspected public source supports this scoped mutation.",
            evidence_goal=None,
        ),
    )


def test_mutation_tool_contract_is_one_exact_gateway_generated_replacement() -> None:
    schemas = dev_tool_schemas(
        finish_enabled=False,
        check_ids=["contract-check", "regression-check"],
    )
    mutation = next(schema for schema in schemas if schema["name"] == "replace_text")
    reads = [schema for schema in schemas if schema["name"] in {"read_file", "search_files"}]
    check = next(schema for schema in schemas if schema["name"] == "run_check")
    stop = next(schema for schema in schemas if schema["name"] == "stop_task")

    assert all(schema["name"] not in {"apply_patch", "apply_git_diff"} for schema in schemas)
    assert all(schema["name"] != "finish_task" for schema in schemas)
    assert check["parameters"]["properties"]["check_id"]["enum"] == [
        "contract-check",
        "regression-check",
    ]
    assert set(stop["parameters"]["required"]) == set(stop["parameters"]["properties"])
    assert stop["parameters"]["additionalProperties"] is False
    assert mutation["parameters"]["required"][0] == "path"
    assert "git_diff" not in mutation["parameters"]["properties"]
    assert set(mutation["parameters"]["required"]) == set(mutation["parameters"]["properties"])
    assert mutation["parameters"]["additionalProperties"] is False
    assert "constructs the canonical Git diff" in mutation["description"]
    assert "never provide diff syntax" in mutation["description"]
    assert "bounded post-image" in mutation["description"]
    assert "evidence_span_ids" not in mutation["parameters"]["properties"]
    for schema in schemas:
        decision = schema["parameters"]["properties"]["turn_decision"]
        assert "turn_decision" in schema["parameters"]["required"]
        assert set(decision["required"]) == set(decision["properties"])
        assert decision["additionalProperties"] is False
        assert decision["properties"]["basis"]["maxLength"] == 800
        expected_mode = (
            "inspect"
            if schema in reads
            else {
                "run_check": "verify",
                "replace_text": "mutate",
                "stop_task": "stop",
            }[schema["name"]]
        )
        assert decision["properties"]["mode"]["enum"] == [expected_mode]
        evidence_goal = decision["properties"]["evidence_goal"]
        if expected_mode == "inspect":
            assert evidence_goal["type"] == "string"
        else:
            assert evidence_goal["type"] == "null"
    assert "binds observed evidence" in DEV_SYSTEM_PROMPT
    assert "do not supply evidence span IDs or a patch wrapper" in DEV_SYSTEM_PROMPT
    assert "Every response must request either" in DEV_SYSTEM_PROMPT
    assert "Every call carries a bounded public turn_decision" in DEV_SYSTEM_PROMPT
    assert "memory_update" in DEV_SYSTEM_PROMPT
    assert "Coverage and commitment signals are advisory" in DEV_SYSTEM_PROMPT
    assert "causal_revision is optional" in DEV_SYSTEM_PROMPT
    assert (
        "source read is required for edit admission only when exact evidence is missing"
        in DEV_SYSTEM_PROMPT
    )
    assert "behavioral questions can still justify inspection" in DEV_SYSTEM_PROMPT
    gate_schemas = dev_tool_schemas(
        finish_enabled=False,
        check_ids=(),
        allowed_tools=frozenset({"replace_text", "stop_task"}),
    )
    assert [schema["name"] for schema in gate_schemas] == [
        "replace_text",
        "stop_task",
    ]

    targeted = dev_tool_schemas(
        finish_enabled=False,
        allowed_tools=frozenset({"read_file", "stop_task"}),
        read_paths=("mini_data_utils/csvlite.py",),
    )
    targeted_read = next(schema for schema in targeted if schema["name"] == "read_file")
    assert targeted_read["parameters"]["properties"]["path"]["enum"] == [
        "mini_data_utils/csvlite.py"
    ]


def test_empty_diff_is_never_ready_even_with_remembered_passing_checks(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway._remember_check(  # noqa: SLF001 - reconstruct impossible stale evidence
        {
            "check_id": "existing-unit-tests",
            "diff_hash": gateway.current_diff_hash,
            "passed": True,
            "failure_signature": None,
        }
    )

    assert gateway.visible_checks_pass() is True
    assert gateway.ready_to_submit() is False
    schemas = dev_tool_schemas(finish_enabled=gateway.ready_to_submit())
    assert all(schema["name"] != "finish_task" for schema in schemas)


def test_stop_task_is_structured_and_rejects_retired_citation_field(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    unknown = gateway.execute(
        RequestedTool(
            name="stop_task",
            action_id="stop-with-unknown-evidence",
            arguments={
                "reason_code": "insufficient_public_evidence",
                "summary": "The cited evidence is unavailable.",
                "evidence_span_ids": ["span_unknown"],
            },
        )
    )
    stopped = gateway.execute(
        RequestedTool(
            name="stop_task",
            action_id="stop-without-submission",
            arguments={
                "reason_code": "no_safe_scoped_mutation",
                "summary": "No safe mutation follows from the public evidence.",
            },
        )
    )

    assert unknown.status == "failed"
    assert "evidence_span_ids" in unknown.message
    assert "Extra inputs are not permitted" in unknown.message
    assert stopped.status == "succeeded"
    assert stopped.output["reason_code"] == "no_safe_scoped_mutation"
    assert stopped.output["diff_hash"] == gateway.current_diff_hash


def test_mutation_error_location_parses_git_diagnostics() -> None:
    assert DevToolGateway._mutation_error_location(  # noqa: SLF001
        "git apply check failed: error: corrupt patch at <stdin>:27"
    ) == {"patch_line": 27}
    assert DevToolGateway._mutation_error_location(  # noqa: SLF001
        "git apply check failed: error: patch failed: mini_data_utils/csvlite.py:1"
    ) == {"path": "mini_data_utils/csvlite.py", "line": 1}


def test_legacy_patch_argument_is_rejected_by_exact_replacement_contract(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="wrapped-live-mutation")
    mutation.arguments["git_diff"] = "*** Begin Patch\n*** End Patch"

    result = gateway.execute(mutation)

    assert result.status == "failed"
    assert result.error_code == "TOOL_CONTRACT_ERROR"
    assert "Extra inputs are not permitted" in result.message
    assert gateway.accepted_mutations == 0


def test_failed_mutation_persists_across_reads_and_restart_then_clears_on_success(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.execute_batch(read_calls())
    malformed = mutation_call(gateway, action_id="malformed-mutation")
    malformed.arguments["old_text"] = malformed.arguments["old_text"].replace(
        "import csv\n", "import csv_missing\n"
    )

    failed = gateway.execute(malformed)

    assert failed.status == "failed"
    pending = gateway.last_failed_mutation
    assert pending is not None
    assert pending["replacement"]["old_text"] == malformed.arguments["old_text"]
    assert pending["replacement_hash"] == sha256_json(
        {
            "path": malformed.arguments["path"],
            "old_text": malformed.arguments["old_text"],
            "new_text": malformed.arguments["new_text"],
            "occurrence": malformed.arguments["occurrence"],
        }
    )
    assert pending["replacement_truncated"] is False
    assert pending["hypothesis"] == malformed.arguments["hypothesis"]
    assert pending["expected_behavior"] == malformed.arguments["expected_behavior"]
    assert pending["replacement"]["path"] == malformed.arguments["path"]
    assert pending["error_code"] == "CONTRACT_ERROR"
    assert pending["error_location"] == {"path": "mini_data_utils/csvlite.py"}
    assert "budget permits" in pending["next_action"]
    assert pending["mutation_failure"]["class"] == "anchor_invalid"

    read_after_failure = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-after-failed-mutation",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 20,
            },
        )
    )
    assert read_after_failure.status == "succeeded"
    assert gateway.last_failed_mutation == pending

    restarted = type(gateway)(
        workspace=workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=journal,
        limits=gateway.limits,
    )
    assert restarted.last_failed_mutation == pending

    replacement = mutation_call(restarted, action_id="replacement-failed-mutation")
    replacement.arguments["old_text"] = replacement.arguments["old_text"].replace(
        "import csv\n", "import csv_still_missing\n"
    )
    assert restarted.execute(replacement).status == "failed"
    assert restarted.last_failed_mutation["action_id"] == "replacement-failed-mutation"
    assert restarted.last_failed_mutation["replacement_hash"] != pending["replacement_hash"]

    accepted = restarted.execute(mutation_call(restarted, action_id="repaired-mutation"))
    assert accepted.status == "succeeded"
    assert restarted.last_failed_mutation is None


def test_gateway_generates_canonical_diff_and_keeps_stale_anchor_fail_closed(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    replacement = mutation_call(gateway, action_id="generated-diff-mutation")

    accepted = gateway.execute(replacement)

    assert accepted.status == "succeeded"
    assert accepted.output["patch_hash"] == sha256_bytes(
        accepted.output["mutation"]["changed_hunk"].encode("utf-8")
    )
    assert accepted.output["mutation"]["changed_hunk"].startswith(
        "diff --git a/mini_data_utils/csvlite.py b/mini_data_utils/csvlite.py\n"
    )
    assert accepted.output["worktree_diff_hash"] == gateway.current_diff_hash

    stale_gateway, _, stale_workspace = gateway_factory()
    stale_gateway.execute_batch(read_calls())
    stale = mutation_call(stale_gateway, action_id="stale-context-mutation")
    stale.arguments["old_text"] = stale.arguments["old_text"].replace(
        "import csv\n", "import csv_missing\n"
    )

    rejected = stale_gateway.execute(stale)

    assert rejected.status == "failed"
    assert "exact edit anchor is stale" in rejected.message
    assert stale_gateway.current_diff.changed_files == []
    assert (
        subprocess.run(
            ["git", "status", "--short"],
            cwd=stale_workspace,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        == ""
    )


def test_out_of_scope_replacement_rolls_back_cleanly(gateway_factory) -> None:
    gateway, _, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(
        update={
            "constraints": gateway.public_task.constraints.model_copy(update={"max_diff_lines": 1})
        }
    )
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="replacement-scope-rollback")

    rejected = gateway.execute(mutation)

    assert rejected.status == "failed"
    assert "mutation violates scope" in rejected.message
    failure = rejected.output["mutation_failure"]
    assert failure["class"] == "scope_violation"
    assert failure["candidate"]["diff_lines"] == 6
    assert failure["violations"] == [
        {"code": "max_diff_lines", "actual": 6, "limit": 1, "over_by": 5}
    ]
    assert failure["rolled_back"] is True
    assert rejected.workspace_diff_hash == gateway.current_diff_hash
    assert gateway.current_diff.changed_files == []
    assert (
        subprocess.run(
            ["git", "diff", "--exit-code"],
            cwd=workspace,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    worktree_blob = subprocess.run(
        ["git", "hash-object", "mini_data_utils/csvlite.py"],
        cwd=workspace,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    head_blob = subprocess.run(
        ["git", "rev-parse", "HEAD:mini_data_utils/csvlite.py"],
        cwd=workspace,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert worktree_blob == head_blob


def test_scope_failure_reports_complete_49_to_56_candidate_and_survives_restart(
    gateway_factory,
    monkeypatch,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(
        update={
            "constraints": gateway.public_task.constraints.model_copy(
                update={"max_diff_lines": 50}
            )
        }
    )
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="49-to-56-scope-failure")
    target = workspace / "mini_data_utils" / "csvlite.py"
    baseline_bytes = target.read_bytes()
    baseline = DiffSummary(
        changed_files=["mini_data_utils/csvlite.py"],
        added_lines=49,
        deleted_lines=0,
        patch="baseline-49-lines",
        untracked_files=[],
    )
    candidate = DiffSummary(
        changed_files=["mini_data_utils/csvlite.py"],
        added_lines=56,
        deleted_lines=0,
        patch="candidate-56-lines",
        untracked_files=[],
    )

    def synthetic_summary(selected_workspace, *, deadline=None):
        del selected_workspace
        if deadline is not None:
            deadline.check()
        return baseline if target.read_bytes() == baseline_bytes else candidate

    monkeypatch.setattr(WorkspaceManager, "diff_summary", staticmethod(synthetic_summary))
    monkeypatch.setattr(
        WorkspaceManager, "preview_text_replacement",
        staticmethod(lambda *args, **kwargs: candidate),
    )

    assert gateway.mutation_scope_budget() == {
        "current_diff_lines": 49,
        "max_diff_lines": 50,
        "remaining_diff_line_headroom": 1,
        "current_changed_file_count": 1,
        "max_changed_files": 1,
        "remaining_changed_file_headroom": 0,
        "rule": (
            "Headroom is not the replacement line count; the gateway validates the "
            "complete candidate diff."
        ),
    }

    rejected = gateway.execute(mutation)

    assert rejected.status == "failed"
    assert target.read_bytes() == baseline_bytes
    assert rejected.workspace_diff_hash == baseline.patch_hash
    failure = rejected.output["mutation_failure"]
    assert isinstance(failure["recovery_key"], str)
    assert failure["recovery_key"].startswith("sha256:")
    assert {key: value for key, value in failure.items() if key != "recovery_key"} == {
        "class": "scope_violation",
        "baseline": {
            "diff_hash": baseline.patch_hash,
            "diff_lines": 49,
            "changed_files": ["mini_data_utils/csvlite.py"],
        },
        "candidate": {
            "diff_hash": candidate.patch_hash,
            "diff_lines": 56,
            "changed_files": ["mini_data_utils/csvlite.py"],
        },
        "delta_from_baseline": {"diff_lines": 7, "changed_file_count": 0},
        "violations": [
            {"code": "max_diff_lines", "actual": 56, "limit": 50, "over_by": 6}
        ],
        "rolled_back": True,
    }
    assert gateway.last_failed_mutation["mutation_failure"] == rejected.output[
        "mutation_failure"
    ]

    restarted = DevToolGateway(
        workspace=workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=journal,
        limits=gateway.limits,
    )
    assert restarted.last_failed_mutation == gateway.last_failed_mutation


def test_failed_mutation_diff_projection_is_bounded(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    oversized = mutation_call(gateway, action_id="oversized-failed-mutation")
    oversized.arguments["new_text"] = "x" * 25_000

    failed = gateway.execute(oversized)

    assert failed.status == "failed"
    pending = gateway.last_failed_mutation
    assert pending is not None
    assert len(pending["replacement"]["new_text"]) == 20_000
    assert pending["replacement_truncated"] is True
    assert pending["replacement_hash"] == sha256_json(
        {
            "path": oversized.arguments["path"],
            "old_text": oversized.arguments["old_text"],
            "new_text": oversized.arguments["new_text"],
            "occurrence": oversized.arguments["occurrence"],
        }
    )

    combined = mutation_call(gateway, action_id="combined-oversized-failed-mutation")
    combined.arguments["old_text"] = "o" * 20_000
    combined.arguments["new_text"] = "n" * 20_000
    assert gateway.execute(combined).status == "failed"
    bounded = gateway.last_failed_mutation
    assert bounded is not None
    assert len(bounded["replacement"]["old_text"]) == 20_000
    assert len(bounded["replacement"]["new_text"]) == 4_000
    assert (
        len(bounded["replacement"]["old_text"]) + len(bounded["replacement"]["new_text"]) == 24_000
    )
    assert bounded["replacement_truncated"] is True


def test_parallel_read_mutation_check_and_finish(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    read_results = gateway.execute_batch(read_calls())
    assert [result.status for result in read_results] == ["succeeded", "succeeded"]
    mutation = gateway.execute(mutation_call(gateway))
    assert mutation.status == "succeeded"
    check = gateway.execute(
        RequestedTool(
            name="run_check",
            action_id="visible-check",
            arguments={"check_id": "existing-unit-tests"},
        )
    )
    assert check.output["passed"] is True
    assert gateway.visible_checks_pass() is True
    finish = gateway.execute(RequestedTool(name="finish_task", action_id="finish", arguments={}))
    assert finish.status == "succeeded"
    assert finish.output["patch_hash"] == gateway.current_diff_hash


def test_allowed_path_and_stale_anchor_fail_closed(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    stale_call = mutation_call(gateway, action_id="stale-mutation")
    forbidden_read = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-test",
            arguments={"path": "tests/test_csvlite.py", "start_line": 1, "end_line": 20},
        )
    )
    assert forbidden_read.status == "succeeded"
    forbidden = gateway.execute(
        RequestedTool(
            name="replace_text",
            action_id="forbidden-mutation",
            arguments={
                "path": "tests/test_csvlite.py",
                "old_text": "import unittest",
                "new_text": "import unittest\n# forbidden",
                "occurrence": 1,
                "hypothesis": "tests need a bypass",
                "expected_behavior": "tests change",
                "causal_revision": None,
            },
        )
    )
    assert forbidden.status == "failed"
    assert forbidden.error_code == "CONTRACT_ERROR"

    assert gateway.execute(mutation_call(gateway, action_id="valid-mutation")).status == "succeeded"
    stale = gateway.execute(stale_call)
    assert stale.status == "failed"
    assert "stale" in stale.message


def test_mutation_postimage_is_current_repair_evidence_across_restart(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.execute_batch(read_calls())
    old_source_span_ids = {
        span_id
        for span_id, span in gateway.spans.items()
        if span["path"] == "mini_data_utils/csvlite.py"
    }

    accepted = gateway.execute(mutation_call(gateway, action_id="initial-mutation"))

    assert accepted.status == "succeeded"
    postimage = accepted.output["mutation_evidence"]
    assert postimage["origin"] == "accepted_mutation"
    assert postimage["file_hash"] == sha256_bytes(
        (workspace / "mini_data_utils" / "csvlite.py").read_bytes()
    )
    assert postimage["span_id"] == accepted.output["mutation"]["postimage_evidence_span_id"]
    assert old_source_span_ids.isdisjoint(gateway.spans)
    assert postimage["span_id"] in gateway.spans

    restarted = DevToolGateway(
        workspace=workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=journal,
        limits=gateway.limits,
    )
    assert postimage["span_id"] in restarted.spans
    assert restarted.current_mutation_evidence_paths() == ("mini_data_utils/csvlite.py",)
    projected_mutation = restarted.actionable_last_successful_mutation()
    assert projected_mutation is not None
    assert projected_mutation["postimage_evidence_available"] is True
    assert "postimage_evidence_span_id" not in projected_mutation
    assert "actionable_evidence_span_ids" not in projected_mutation
    assert "evidence_span_ids" not in projected_mutation
    assert "anchor_evidence_span_id" not in projected_mutation
    assert "edit_anchor" not in projected_mutation
    repair = RequestedTool(
        name="replace_text",
        action_id="same-hunk-repair",
        arguments={
            "path": "mini_data_utils/csvlite.py",
            "old_text": '    return list(csv.reader(io.StringIO(text, newline="")))',
            "new_text": "    return list(csv.reader(io.StringIO(text)))",
            "occurrence": 1,
            "hypothesis": "The stream newline override causes the public check failure.",
            "expected_behavior": "The parser keeps one stream without the override.",
            "causal_revision": None,
        },
    )

    repaired = restarted.execute(repair)

    assert repaired.status == "succeeded"
    repaired_mutation = repaired.output["mutation"]
    assert repaired_mutation["evidence_binding"] == "gateway_current_observation"
    assert "actionable_evidence_span_ids" not in repaired_mutation
    assert "input_evidence_counts" not in repaired_mutation
    assert "evidence_span_ids" not in repaired_mutation
    assert "anchor_evidence_span_id" not in repaired_mutation
    started = next(
        event["payload"]
        for event in journal.events()
        if event["event_type"] == "action_started"
        and event["payload"]["action_id"] == repair.action_id
    )
    assert started["mutation_anchor_evidence_span_id"] == postimage["span_id"]
    assert "evidence_span_ids" not in started["arguments"]


def test_gateway_selects_a_covering_span_without_model_evidence_ids(
    gateway_factory,
) -> None:
    gateway, journal, _ = gateway_factory()
    full = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-complete-mutation-anchor",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 80,
            },
        )
    ).output["spans"][0]
    short = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-newer-short-anchor",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 8,
            },
        )
    ).output["spans"][0]

    result = gateway.execute(mutation_call(gateway, action_id="auto-bound-mutation"))

    assert result.status == "succeeded"
    started = next(
        event["payload"]
        for event in journal.events()
        if event["event_type"] == "action_started"
        and event["payload"]["action_id"] == "auto-bound-mutation"
    )
    assert started["mutation_anchor_evidence_span_id"] == short["span_id"]
    assert set(started["mutation_anchor_evidence_span_ids"]) == {
        full["span_id"], short["span_id"],
    }
    assert "evidence_span_ids" not in started["arguments"]


def test_mutation_postimage_does_not_authorize_an_uncovered_anchor(
    gateway_factory,
) -> None:
    gateway, _, workspace = gateway_factory()
    # The import must genuinely be unobserved, not an unchanged part of a broad
    # earlier read that positional rebinding now correctly preserves.
    return_line = next(
        number for number, line in enumerate(
            (workspace / "mini_data_utils/csvlite.py").read_text().splitlines(), 1,
        ) if line.strip() == "return rows"
    )
    gateway.execute(RequestedTool(
        name="read_file", action_id="observe-return-only",
        arguments={
            "path": "mini_data_utils/csvlite.py",
            "start_line": return_line, "end_line": return_line,
        },
    ))
    narrow_mutation = RequestedTool(
        name="replace_text",
        action_id="narrow-mutation",
        arguments={
            "path": "mini_data_utils/csvlite.py",
            "old_text": "    return rows",
            "new_text": "    return list(rows)",
            "occurrence": 1,
            "hypothesis": "Materialize the return value.",
            "expected_behavior": "The public return type remains a list.",
            "causal_revision": None,
        },
    )
    assert gateway.execute(narrow_mutation).status == "succeeded"
    unrelated = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-init-for-uncovered-anchor",
            arguments={
                "path": "mini_data_utils/__init__.py",
                "start_line": 1,
                "end_line": 40,
            },
        )
    )
    assert unrelated.status == "succeeded"
    uncovered = RequestedTool(
        name="replace_text",
        action_id="uncovered-anchor",
        arguments={
            "path": "mini_data_utils/csvlite.py",
            "old_text": "import csv",
            "new_text": "import csv as csv_module",
            "occurrence": 1,
            "hypothesis": "The import name should be explicit.",
            "expected_behavior": "The module alias is available.",
            "causal_revision": None,
        },
    )

    rejected = gateway.execute(uncovered)

    assert rejected.status == "failed"
    assert "evidence spans do not cover" in rejected.message
    assert rejected.output["mutation_failure"]["required_anchor"] == {
        "path": "mini_data_utils/csvlite.py",
        "start_line": 3,
        "end_line": 3,
    }


def test_read_cache_promotes_evidence_and_resets_after_mutation(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    first_call = read_calls()[1]
    first = gateway.execute(first_call)
    repeated = gateway.execute(first_call.model_copy(update={"action_id": "read-source-again"}))
    assert first.evidence_cache_hit is False
    assert repeated.evidence_cache_hit is True
    assert repeated.output["new_span_count"] == 0
    assert repeated.output["evidence_repetition"] == 2
    assert repeated.output["stagnation_signal"] is True

    interleaved = gateway.execute(
        first_call.model_copy(
            update={
                "action_id": "interleaved-new-range",
                "arguments": {
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": 2,
                    "end_line": 7,
                },
            }
        )
    )
    assert interleaved.output["new_span_count"] == 1

    reframed_decision = inspection_decision("reframed-after-result")
    reframed = gateway.execute(
        first_call.model_copy(
            update={
                "action_id": "read-source-with-reframed-state",
                "turn_decision": reframed_decision,
            }
        )
    )
    assert reframed.evidence_cache_hit is True
    assert reframed.input_hash != first.input_hash
    assert reframed.output["read_request_hash"] == first.output["read_request_hash"]
    assert reframed.output["evidence_repetition"] == 3
    assert reframed.output["stagnation_signal"] is True
    assert "turn_decision" not in reframed.output

    restarted = type(gateway)(
        workspace=gateway.workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=gateway.journal,
        limits=gateway.limits,
    )
    resumed_decision = inspection_decision("reframed-after-restart")
    resumed = restarted.execute(
        first_call.model_copy(
            update={
                "action_id": "read-source-after-restart",
                "turn_decision": resumed_decision,
            }
        )
    )
    assert resumed.evidence_cache_hit is True
    assert "turn_decision" not in resumed.output

    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    refreshed = gateway.execute(
        first_call.model_copy(update={"action_id": "read-source-after-mutation"})
    )
    assert refreshed.evidence_cache_hit is False
    assert refreshed.output["new_span_count"] == 0
    assert (
        refreshed.output["spans"][0]["span_id"]
        == gateway.last_successful_mutation["postimage_evidence_span_id"]
    )


def test_evidence_ledger_counts_uncovered_ranges_and_zero_result_search_once(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()

    def read(action_id: str, start: int, end: int):
        return gateway.execute(
            RequestedTool(
                name="read_file",
                action_id=action_id,
                arguments={
                    "path": "mini_data_utils/csvlite.py",
                    "start_line": start,
                    "end_line": end,
                },
                turn_decision=inspection_decision(action_id),
            )
        )

    first = read("coverage-first", 1, 8)
    shifted = read("coverage-shifted", 2, 9)
    contained = read("coverage-contained", 3, 8)

    assert first.output["evidence_gain"]["new_task_relevant_line_count"] == 8
    assert shifted.output["new_span_count"] == 1
    assert shifted.output["evidence_gain"]["new_task_relevant_line_count"] == 1
    assert contained.output["new_span_count"] == 1
    assert contained.output["evidence_gain"]["marginal_evidence_gain"] is False

    search = RequestedTool(
        name="search_files",
        action_id="zero-search-first",
        arguments={"query": "definitely-not-present", "path_glob": "**/*.py"},
        turn_decision=inspection_decision("zero-search-first"),
    )
    first_zero = gateway.execute(search)
    repeated_zero = gateway.execute(search.model_copy(update={"action_id": "zero-search-repeat"}))
    assert first_zero.output["spans"] == []
    assert first_zero.output["evidence_gain"]["first_search_observation"] is True
    assert first_zero.output["evidence_gain"]["marginal_evidence_gain"] is False
    assert first_zero.output["evidence_gain"]["marginal_evidence_gain_units"] == 0
    assert repeated_zero.evidence_cache_hit is True
    assert repeated_zero.output["evidence_gain"]["first_search_observation"] is False
    assert repeated_zero.output["evidence_gain"]["marginal_evidence_gain"] is False

    ledger = gateway.evidence_ledger()
    source = next(
        row for row in ledger["covered_files"] if row["path"] == "mini_data_utils/csvlite.py"
    )
    assert source["ranges"] == [[1, 9]]
    assert source["covered_line_count"] == 9
    assert ledger["search_summary"] == {
        "total_search_count": 2,
        "unique_query_count": 1,
        "zero_match_count": 2,
        "covered_only_count": 0,
        "new_coverage_count": 0,
        "supporting_coverage_count": 0,
        "unique_result_fingerprint_count": 1,
    }
    assert len(ledger["canonical_searches"]) == 2
    assert all(row["outcome"] == "zero_match" for row in ledger["canonical_searches"])
    assert all(row["evidence_goal"] for row in ledger["canonical_searches"])
    assert len({row["result_fingerprint"] for row in ledger["canonical_searches"]}) == 1

    restarted = DevToolGateway(
        workspace=workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=journal,
        limits=gateway.limits,
    )
    assert restarted.evidence_ledger() == ledger


def test_evidence_gain_splits_editable_supporting_and_covered_only_searches(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    supporting = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="supporting-public-source",
            arguments={"path": "tests/test_csvlite.py", "start_line": 1, "end_line": 3},
            turn_decision=inspection_decision("supporting-public-source"),
        )
    )
    gain = supporting.output["evidence_gain"]
    assert gain["new_covered_line_count"] == 3
    assert gain["new_editable_line_count"] == 0
    assert gain["new_supporting_line_count"] == 3
    assert gain["new_task_relevant_line_count"] == 0
    assert gain["marginal_evidence_gain"] is True

    first = gateway.execute(
        RequestedTool(
            name="search_files",
            action_id="first-query-same-result",
            arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
            turn_decision=inspection_decision("first-query-same-result"),
        )
    )
    second = gateway.execute(
        RequestedTool(
            name="search_files",
            action_id="new-query-same-result",
            arguments={"query": "def parse_rows(", "path_glob": "**/*.py"},
            turn_decision=inspection_decision("new-query-same-result"),
        )
    )
    assert first.output["evidence_gain"]["new_editable_line_count"] > 0
    assert second.output["evidence_gain"]["first_search_observation"] is True
    assert second.output["evidence_gain"]["new_covered_line_count"] == 0
    assert second.output["evidence_gain"]["marginal_evidence_gain"] is False
    assert gateway.evidence_ledger()["canonical_searches"][0]["outcome"] == "covered_only"


def test_search_summary_outlives_the_twelve_item_recent_window(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    for index in range(13):
        gateway.execute(
            RequestedTool(
                name="search_files",
                action_id=f"bounded-search-{index}",
                arguments={"query": f"missing-public-symbol-{index}", "path_glob": "**/*.py"},
                turn_decision=inspection_decision(f"bounded-search-{index}"),
            )
        )

    ledger = gateway.evidence_ledger()
    assert len(ledger["canonical_searches"]) == 12
    assert ledger["search_summary"]["total_search_count"] == 13
    assert ledger["search_summary"]["unique_query_count"] == 13
    assert ledger["search_summary"]["zero_match_count"] == 13
    assert ledger["search_summary"]["unique_result_fingerprint_count"] == 1


def test_mutation_revalidates_unchanged_unique_source_spans(gateway_factory) -> None:
    gateway, journal, workspace = gateway_factory()
    unchanged = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-unchanged-import",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 4,
            },
            turn_decision=inspection_decision("unchanged-import"),
        )
    ).output["spans"][0]
    gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-narrow-return",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 8,
                "end_line": 13,
            },
            turn_decision=inspection_decision("narrow-return"),
        )
    )
    accepted = gateway.execute(
        RequestedTool(
            name="replace_text",
            action_id="narrow-revalidation-mutation",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "old_text": "    return rows",
                "new_text": "    return list(rows)",
                "occurrence": 1,
                "hypothesis": "Materializing the result preserves the declared return type.",
                "expected_behavior": "The parser returns a concrete list.",
                "causal_revision": None,
            },
            turn_decision=PublicTurnDecision(
                mode="mutate",
                basis="The exact return anchor is visible.",
                evidence_goal=None,
            ),
        )
    )

    assert accepted.status == "succeeded"
    assert unchanged["span_id"] not in gateway.spans
    rebound = next(
        span
        for span in accepted.output["revalidated_spans"]
        if span["content"] == unchanged["content"]
    )
    assert rebound["origin"] == "revalidated_after_mutation"
    assert rebound["file_hash"] == sha256_bytes(
        (workspace / "mini_data_utils" / "csvlite.py").read_bytes()
    )
    assert rebound["span_id"] in gateway.spans

    restarted = DevToolGateway(
        workspace=workspace,
        public_task=gateway.public_task,
        sandbox=gateway.sandbox,
        journal=journal,
        limits=gateway.limits,
    )
    assert rebound["span_id"] in restarted.spans


def test_new_files_and_untracked_submission_fail_closed(gateway_factory) -> None:
    gateway, _, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(
        update={
            "constraints": gateway.public_task.constraints.model_copy(
                update={"allowed_paths": ["mini_data_utils/**"], "max_changed_files": 2}
            )
        }
    )
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="mixed-new-file")
    mutation.arguments.update(
        {
            "path": "mini_data_utils/new_helper.py",
            "old_text": "VALUE = 0",
            "new_text": "VALUE = 1",
        }
    )
    rejected = gateway.execute(mutation)
    assert rejected.status == "failed"
    assert "tracked public file" in rejected.message
    assert not (workspace / "mini_data_utils" / "new_helper.py").exists()

    assert gateway.execute(mutation_call(gateway, action_id="tracked-only")).status == "succeeded"
    check = gateway.execute(
        RequestedTool(
            name="run_check",
            action_id="untracked-visible-check",
            arguments={"check_id": "existing-unit-tests"},
        )
    )
    assert check.output["passed"] is True
    (workspace / "unexpected.txt").write_text("not submitted\n", encoding="utf-8")
    finish = gateway.execute(
        RequestedTool(name="finish_task", action_id="untracked-finish", arguments={})
    )
    assert finish.status == "failed"
    assert "untracked files" in finish.message


def test_repeated_signature_across_two_diffs_keeps_causal_revision_optional(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory(sandbox=CountingFailSandbox())
    gateway.execute_batch(read_calls())
    gateway._remember_check(  # noqa: SLF001 - direct reconstruction of durable public history
        {
            "check_id": "existing-unit-tests",
            "diff_hash": "sha256:diff-one",
            "passed": False,
            "failure_signature": "sha256:same-failure",
        }
    )
    gateway._remember_check(  # noqa: SLF001
        {
            "check_id": "existing-unit-tests",
            "diff_hash": "sha256:diff-two",
            "passed": False,
            "failure_signature": "sha256:same-failure",
        }
    )
    assert gateway.requires_alternative is True
    accepted = gateway.execute(mutation_call(gateway, action_id="optional-alternative"))
    assert accepted.status == "succeeded"
    assert gateway.requires_alternative is False


def test_inline_public_failure_is_mapped_and_survives_read_and_restart(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory(sandbox=InlineFailureSandbox(2))
    source = "value = 0\nassert value == 1\nnot_reached = True"
    check = RegisteredCheck(
        id="inline-contract",
        command=["/usr/local/bin/python", "-c", source],
    )
    public = gateway.public_task.model_copy(update={"visible_checks": [check]})
    gateway.public_task = public

    failed = gateway.execute(
        RequestedTool(
            name="run_check",
            action_id="inline-failure",
            arguments={"check_id": check.id},
        )
    )
    focus = failed.output["public_check_failure"]
    assert focus["mapping_status"] == "mapped_public_inline_python"
    assert focus["public_location"]["line"] == 2
    assert focus["public_location"]["statement"] == "assert value == 1"
    assert focus["execution_boundary"]["later_source_lines_observed"] is None
    assert focus["comparison_with_previous_failure"]["relation"] == "first_observation"
    assert focus["recurrence_across_distinct_diffs"] == 1

    read = gateway.execute(read_calls()[1])
    assert read.status == "succeeded"
    projected = gateway.current_public_failure()
    assert projected is not None
    assert projected["phase"] == "repair_current_diff"
    assert projected["public_location"]["statement"] == "assert value == 1"
    assert projected["mutation_pressure"] == {
        "same_public_failure_site": False,
        "accepted_mutations_remaining": 4,
        "guidance": "This check failed on the current diff.",
    }

    restarted = DevToolGateway(
        workspace=workspace,
        public_task=public,
        sandbox=InlineFailureSandbox(2),
        journal=journal,
        limits=gateway.limits,
    )
    assert restarted.current_public_failure() == projected
    restarted._remember_check(  # noqa: SLF001 - successful recheck clears active focus
        {
            "check_id": check.id,
            "diff_hash": restarted.current_diff_hash,
            "passed": True,
            "failure_signature": None,
        }
    )
    assert restarted.current_public_failure() is None


def test_public_failure_progress_and_recurrence_use_mapped_site(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    source = (
        "first = 0\n"
        "assert first == 1\n"
        "second = 0\n"
        "assert second == 1\n"
        "windows_behavior_not_reached = True"
    )
    check = RegisteredCheck(id="inline-progress", command=["python", "-c", source])

    def remember(diff_hash: str, line: int) -> dict:
        stderr = (
            "Traceback (most recent call last):\n"
            f'  File "<string>", line {line}, in <module>\n'
            "AssertionError\n"
        )
        signature = sha256_json({"diff_hash": diff_hash, "stderr": stderr})
        focus = gateway._public_check_failure(  # noqa: SLF001 - focused mapping contract
            check=check,
            diff_hash=diff_hash,
            failure_signature=signature,
            stdout="",
            stderr=stderr,
        )
        gateway._remember_check(  # noqa: SLF001 - construct durable check history
            {
                "check_id": check.id,
                "diff_hash": diff_hash,
                "passed": False,
                "failure_signature": signature,
                "public_check_failure": focus,
            }
        )
        return focus

    first = remember("sha256:diff-one", 2)
    later = remember("sha256:diff-two", 4)
    repeated = remember("sha256:diff-three", 4)

    assert first["comparison_with_previous_failure"]["relation"] == "first_observation"
    assert (
        later["comparison_with_previous_failure"]["relation"]
        == "public_failure_location_moved_later"
    )
    assert later["comparison_with_previous_failure"]["previous_public_line"] == 2
    assert later["recurrence_across_distinct_diffs"] == 1
    assert (
        repeated["comparison_with_previous_failure"]["relation"]
        == "same_public_failure_site"
    )
    assert repeated["recurrence_across_distinct_diffs"] == 2
    assert gateway.requires_alternative is True
    projected = gateway.current_public_failure(diff_hash="sha256:diff-three")
    assert projected is not None
    assert projected["mutation_pressure"]["same_public_failure_site"] is True


def test_row_seventeen_public_failure_pattern_localizes_causal_pivot(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    package = load_task_package(
        repository_root()
        / "tasks"
        / "dev-train"
        / "pyfakefs-makedirs-parent-traversal-v2"
    )
    check = next(
        item for item in package.public.visible_checks if item.id == "parent-traversal-contract"
    )
    gateway.public_task = package.public

    def remember(diff_hash: str, line: int) -> dict:
        stderr = (
            "Traceback (most recent call last):\n"
            f'  File "<string>", line {line}, in <module>\n'
            "AssertionError\n"
        )
        signature = sha256_json({"diff_hash": diff_hash, "stderr": stderr})
        focus = gateway._public_check_failure(  # noqa: SLF001 - live-pattern regression
            check=check,
            diff_hash=diff_hash,
            failure_signature=signature,
            stdout="",
            stderr=stderr,
        )
        gateway._remember_check(  # noqa: SLF001 - reconstruct public check sequence
            {
                "check_id": check.id,
                "diff_hash": diff_hash,
                "passed": False,
                "failure_signature": signature,
                "public_check_failure": focus,
            }
        )
        return focus

    traversal_failure = remember("sha256:row17-diff-one", 12)
    mode_failure = remember("sha256:row17-diff-two", 23)
    repeated_mode_failure = remember("sha256:row17-diff-three", 23)

    assert traversal_failure["public_location"]["statement"] == (
        "assert fake_os.path.isdir(path), path"
    )
    assert mode_failure["public_location"]["statement"] == (
        'assert stat.S_IMODE(fake_os.stat("/permissions/transient").st_mode) == 0o755'
    )
    assert (
        mode_failure["comparison_with_previous_failure"]["relation"]
        == "public_failure_location_moved_later"
    )
    assert (
        repeated_mode_failure["comparison_with_previous_failure"]["relation"]
        == "same_public_failure_site"
    )
    assert repeated_mode_failure["recurrence_across_distinct_diffs"] == 2
    assert repeated_mode_failure["execution_boundary"]["later_source_lines_observed"] is None
    projected = gateway.current_public_failure(diff_hash="sha256:row17-diff-three")
    assert projected is not None
    assert projected["mutation_pressure"]["guidance"].startswith(
        "This check failed on the current diff."
    )


def test_action_replay_and_crash_reconciliation_do_not_duplicate_mutation(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()
    read = read_calls()[1]
    first = gateway.execute(read)
    replay = gateway.execute(read)
    assert first.output == replay.output
    assert replay.replayed is True

    call = mutation_call(gateway, action_id="crash-mutation")
    validated = gateway._validate_replacement_intent(call.arguments)  # noqa: SLF001
    input_hash = sha256_json(
        {
            "tool": call.name,
            "arguments": call.arguments,
            "turn_decision": call.turn_decision.model_dump(mode="json"),
        }
    )
    journal.append(
        "action_started",
        {
            "action_id": call.action_id,
            "input_hash": input_hash,
            "tool": call.name,
            "arguments": call.arguments,
            "turn_decision": call.turn_decision.model_dump(mode="json"),
            "baseline_diff_hash": gateway.current_diff_hash,
            "baseline_changed_files": gateway.current_diff.changed_files,
            "mutation_expected_worktree_diff_hash": WorkspaceManager.preview_text_replacement(
                workspace, validated.path, validated.after_bytes,
                baseline_diff_hash=gateway.current_diff_hash,
            ).patch_hash,
            "mutation_preimage_file_hash": sha256_bytes(validated.before_bytes),
            "mutation_preimage_newline": gateway._source_text(validated.before_bytes)[1],
            "mutation_anchor_offset": validated.before_bytes.decode("utf-8").replace(
                "\r\n", "\n"
            ).index(call.arguments["old_text"]),
            "mutation_admitted": True,
            "mutation_target_path": validated.path,
            "mutation_expected_postimage_file_hash": sha256_bytes(validated.after_bytes),
            "mutation_generated_patch": validated.generated_patch,
            "mutation_postimage_start_line": validated.postimage_start_line,
            "mutation_anchor_evidence_span_id": validated.anchor_evidence_span_id,
            "mutation_anchor_evidence_span_ids": list(validated.anchor_evidence_span_ids),
            "mutation_anchor_start_line": validated.anchor_start_line,
            "mutation_anchor_end_line": validated.anchor_end_line,
        },
    )
    (workspace / validated.path).write_bytes(validated.after_bytes)

    restarted, _, _ = gateway_factory()
    # Rebind to the durable workspace/journal to simulate a process restart.
    restarted.workspace = workspace
    restarted.journal = journal
    restarted.spans.clear()
    restarted._hydrate()  # noqa: SLF001
    recovered = restarted.execute(call)
    assert recovered.status == "succeeded"
    assert recovered.output["recovered_after_crash"] is True
    assert len([e for e in journal.events() if e["event_type"] == "action_finished"]) == 2


def test_completed_check_replays_after_restart_without_execution(gateway_factory) -> None:
    sandbox = CountingFailSandbox()
    gateway, journal, workspace = gateway_factory(sandbox=sandbox)
    call = RequestedTool(
        name="run_check",
        action_id="restart-check",
        arguments={"check_id": "existing-unit-tests"},
    )
    first = gateway.execute(call)
    assert first.status == "succeeded"
    assert sandbox.calls == 1

    restarted, _, _ = gateway_factory(sandbox=sandbox)
    restarted.workspace = workspace
    restarted.journal = journal
    restarted._hydrate()  # noqa: SLF001 - simulate process reconstruction
    replay = restarted.execute(call)
    assert replay.replayed is True
    assert sandbox.calls == 1
