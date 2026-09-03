from __future__ import annotations

import subprocess

from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MOCK_MUTATIONS
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.sandbox.runner import SandboxResult
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
    spans = [item["span_id"] for item in gateway.spans.values() if item["path"] == mutation.path]
    return RequestedTool(
        name="apply_git_diff",
        action_id=action_id,
        arguments={
            "git_diff": mutation.patch,
            "hypothesis": mutation.hypothesis,
            "expected_behavior": mutation.expected_behavior,
            "evidence_span_ids": spans[:2],
            "edit_anchor": {
                "path": mutation.path,
                "old_text": mutation.anchor,
                "occurrence": 1,
            },
            "falsified_prior_hypothesis": (
                "physical line handling was the only cause" if alternative else None
            ),
            "alternative_mechanism": (
                "parser lifetime, not line normalization, owns record boundaries"
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


def test_mutation_tool_contract_requires_unwrapped_raw_git_diff() -> None:
    schemas = dev_tool_schemas(
        finish_enabled=False,
        check_ids=["contract-check", "regression-check"],
    )
    mutation = next(schema for schema in schemas if schema["name"] == "apply_git_diff")
    reads = [schema for schema in schemas if schema["name"] in {"read_file", "search_files"}]
    check = next(schema for schema in schemas if schema["name"] == "run_check")
    stop = next(schema for schema in schemas if schema["name"] == "stop_task")

    assert all(schema["name"] != "apply_patch" for schema in schemas)
    assert all(schema["name"] != "finish_task" for schema in schemas)
    assert check["parameters"]["properties"]["check_id"]["enum"] == [
        "contract-check",
        "regression-check",
    ]
    assert set(stop["parameters"]["required"]) == set(
        stop["parameters"]["properties"]
    )
    assert stop["parameters"]["additionalProperties"] is False
    assert mutation["parameters"]["required"][0] == "git_diff"
    assert mutation["parameters"]["properties"]["git_diff"]["pattern"] == "^diff --git a/"
    assert set(mutation["parameters"]["required"]) == set(
        mutation["parameters"]["properties"]
    )
    assert mutation["parameters"]["additionalProperties"] is False
    assert "diff --git a/<path> b/<path>" in mutation["description"]
    assert "*** Begin Patch" in mutation["description"]
    assert "bounded post-image" in mutation["description"]
    assert "postimage_evidence_span_id" in mutation["parameters"]["properties"][
        "evidence_span_ids"
    ]["description"]
    for schema in schemas:
        decision = schema["parameters"]["properties"]["turn_decision"]
        assert "turn_decision" in schema["parameters"]["required"]
        assert set(decision["required"]) == set(decision["properties"])
        assert decision["additionalProperties"] is False
        assert decision["properties"]["basis"]["maxLength"] == 800
        expected_mode = "inspect" if schema in reads else {
            "run_check": "verify",
            "apply_git_diff": "mutate",
            "stop_task": "stop",
        }[schema["name"]]
        assert decision["properties"]["mode"]["enum"] == [expected_mode]
    assert "git_diff value must be a raw Git unified diff" in DEV_SYSTEM_PROMPT
    assert "Never use \"*** Begin Patch\"" in DEV_SYSTEM_PROMPT
    assert "When last_failed_mutation is present" in DEV_SYSTEM_PROMPT
    assert "Every response must request at least one supplied tool" in DEV_SYSTEM_PROMPT
    assert "Use stop_task when no available public action" in DEV_SYSTEM_PROMPT
    assert "Every tool call must carry turn_decision" in DEV_SYSTEM_PROMPT
    assert "Every call in a parallel read batch must use inspect mode" in DEV_SYSTEM_PROMPT
    assert "may describe that call's distinct public question" in DEV_SYSTEM_PROMPT
    assert "bounded post-image is current evidence" in DEV_SYSTEM_PROMPT
    gate_schemas = dev_tool_schemas(
        finish_enabled=False,
        check_ids=(),
        allowed_tools=frozenset({"apply_git_diff", "stop_task"}),
    )
    assert [schema["name"] for schema in gate_schemas] == [
        "apply_git_diff",
        "stop_task",
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


def test_stop_task_is_structured_and_rejects_unknown_public_evidence(
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
                "evidence_span_ids": [],
            },
        )
    )

    assert unknown.status == "failed"
    assert "unknown or stale public span" in unknown.message
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


def test_patch_wrapper_from_live_transcript_fails_with_exact_git_diff_guidance(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="wrapped-live-mutation")
    mutation.arguments["git_diff"] = (
        "*** Begin Patch\n"
        "*** Update File: mini_data_utils/csvlite.py\n"
        "@@\n"
        "-    return rows\n"
        "+    return list(csv.reader(io.StringIO(text)))\n"
        "*** End Patch"
    )

    result = gateway.execute(mutation)

    assert result.status == "failed"
    assert result.error_code == "CONTRACT_ERROR"
    assert "must begin exactly with 'diff --git a/<path> b/<path>'" in result.message
    assert gateway.accepted_mutations == 0


def test_failed_mutation_persists_across_reads_and_restart_then_clears_on_success(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()
    gateway.execute_batch(read_calls())
    malformed = mutation_call(gateway, action_id="malformed-mutation")
    malformed.arguments["git_diff"] = malformed.arguments["git_diff"].replace(
        " import csv\n", " import csv_missing\n"
    )

    failed = gateway.execute(malformed)

    assert failed.status == "failed"
    pending = gateway.last_failed_mutation
    assert pending is not None
    assert pending["git_diff"] == malformed.arguments["git_diff"]
    assert pending["git_diff_hash"] == sha256_bytes(
        malformed.arguments["git_diff"].encode("utf-8")
    )
    assert pending["git_diff_truncated"] is False
    assert pending["hypothesis"] == malformed.arguments["hypothesis"]
    assert pending["expected_behavior"] == malformed.arguments["expected_behavior"]
    assert pending["edit_anchor"] == malformed.arguments["edit_anchor"]
    assert pending["error_code"] == "CONTRACT_ERROR"
    assert pending["error_location"] == {"path": "mini_data_utils/csvlite.py", "line": 1}
    assert "Repair or explicitly replace" in pending["next_action"]

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
    replacement.arguments["git_diff"] = replacement.arguments["git_diff"].replace(
        " import csv\n", " import csv_still_missing\n"
    )
    assert restarted.execute(replacement).status == "failed"
    assert restarted.last_failed_mutation["action_id"] == "replacement-failed-mutation"
    assert restarted.last_failed_mutation["git_diff_hash"] != pending["git_diff_hash"]

    accepted = restarted.execute(mutation_call(restarted, action_id="repaired-mutation"))
    assert accepted.status == "succeeded"
    assert restarted.last_failed_mutation is None


def test_git_apply_recounts_hunks_but_keeps_context_fail_closed(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    recounted = mutation_call(gateway, action_id="recounted-mutation")
    recounted.arguments["git_diff"] = recounted.arguments["git_diff"].replace(
        "@@ -1,13 +1,11 @@", "@@ -1,13 +1,10 @@"
    )

    accepted = gateway.execute(recounted)

    assert accepted.status == "succeeded"
    assert accepted.output["patch_hash"] == sha256_bytes(
        recounted.arguments["git_diff"].encode("utf-8")
    )
    assert accepted.output["worktree_diff_hash"] == gateway.current_diff_hash

    stale_gateway, _, stale_workspace = gateway_factory()
    stale_gateway.execute_batch(read_calls())
    stale = mutation_call(stale_gateway, action_id="stale-context-mutation")
    stale.arguments["git_diff"] = stale.arguments["git_diff"].replace(
        " import csv\n", " import csv_missing\n"
    )

    rejected = stale_gateway.execute(stale)

    assert rejected.status == "failed"
    assert "patch failed: mini_data_utils/csvlite.py:1" in rejected.message
    assert stale_gateway.current_diff.changed_files == []
    assert subprocess.run(
        ["git", "status", "--short"],
        cwd=stale_workspace,
        capture_output=True,
        check=True,
        text=True,
    ).stdout == ""


def test_recounted_out_of_scope_mutation_rolls_back_cleanly(gateway_factory) -> None:
    gateway, _, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(
        update={
            "constraints": gateway.public_task.constraints.model_copy(
                update={"max_diff_lines": 1}
            )
        }
    )
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="recounted-scope-rollback")
    mutation.arguments["git_diff"] = mutation.arguments["git_diff"].replace(
        "@@ -1,13 +1,11 @@", "@@ -1,13 +1,10 @@"
    )

    rejected = gateway.execute(mutation)

    assert rejected.status == "failed"
    assert "diff-size constraints" in rejected.message
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


def test_failed_mutation_diff_projection_is_bounded(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    oversized = mutation_call(gateway, action_id="oversized-failed-mutation")
    oversized.arguments["git_diff"] += "+" + ("x" * 25_000) + "\n"

    failed = gateway.execute(oversized)

    assert failed.status == "failed"
    pending = gateway.last_failed_mutation
    assert pending is not None
    assert len(pending["git_diff"]) == 24_000
    assert pending["git_diff_truncated"] is True
    assert pending["git_diff_hash"] == sha256_bytes(
        oversized.arguments["git_diff"].encode("utf-8")
    )


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


def test_allowed_path_and_stale_evidence_fail_closed(gateway_factory) -> None:
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
    test_span = forbidden_read.output["spans"][0]["span_id"]
    forbidden = gateway.execute(
        RequestedTool(
            name="apply_git_diff",
            action_id="forbidden-mutation",
            arguments={
                "git_diff": (
                    "diff --git a/tests/test_csvlite.py b/tests/test_csvlite.py\n"
                    "--- a/tests/test_csvlite.py\n"
                    "+++ b/tests/test_csvlite.py\n"
                    "@@ -1,3 +1,4 @@\n"
                    " import unittest\n"
                    "+# forbidden\n"
                    " \n"
                    " from mini_data_utils import parse_rows\n"
                ),
                "hypothesis": "tests need a bypass",
                "expected_behavior": "tests change",
                "evidence_span_ids": [test_span],
                "edit_anchor": {
                    "path": "tests/test_csvlite.py",
                    "old_text": "import unittest",
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
        )
    )
    assert forbidden.status == "failed"
    assert forbidden.error_code == "CONTRACT_ERROR"

    assert gateway.execute(mutation_call(gateway, action_id="valid-mutation")).status == "succeeded"
    assert stale_call.arguments["evidence_span_ids"][0] not in gateway.spans
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
    assert postimage["span_id"] == accepted.output["mutation"][
        "postimage_evidence_span_id"
    ]
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
    assert restarted.current_mutation_evidence_paths() == (
        "mini_data_utils/csvlite.py",
    )
    unrelated = restarted.execute(
        RequestedTool(
            name="read_file",
            action_id="read-unrelated-allowed-source",
            arguments={
                "path": "mini_data_utils/__init__.py",
                "start_line": 1,
                "end_line": 40,
            },
        )
    )
    unrelated_span_id = unrelated.output["spans"][0]["span_id"]
    repair = RequestedTool(
        name="apply_git_diff",
        action_id="same-hunk-repair",
        arguments={
            "git_diff": (
                "diff --git a/mini_data_utils/csvlite.py "
                "b/mini_data_utils/csvlite.py\n"
                "--- a/mini_data_utils/csvlite.py\n"
                "+++ b/mini_data_utils/csvlite.py\n"
                "@@ -7,5 +7,5 @@\n"
                " def parse_rows(text: str) -> list[list[str]]:\n"
                '     """Parse CSV text into rows while preserving quoted values."""\n'
                " \n"
                '-    return list(csv.reader(io.StringIO(text, newline="")))\n'
                "+    return list(csv.reader(io.StringIO(text)))\n"
                " \n"
            ),
            "hypothesis": "The stream newline override causes the public check failure.",
            "expected_behavior": "The parser keeps one stream without the override.",
            "evidence_span_ids": [unrelated_span_id],
            "edit_anchor": {
                "path": "mini_data_utils/csvlite.py",
                "old_text": '    return list(csv.reader(io.StringIO(text, newline="")))',
                "occurrence": 1,
            },
            "falsified_prior_hypothesis": None,
            "alternative_mechanism": None,
        },
    )

    repaired = restarted.execute(repair)

    assert repaired.status == "succeeded"
    assert repaired.output["mutation"]["anchor_evidence_span_id"] == postimage["span_id"]
    assert unrelated_span_id in repaired.output["mutation"]["evidence_span_ids"]


def test_mutation_postimage_does_not_authorize_an_uncovered_anchor(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    source_span_ids = [
        span_id
        for span_id, span in gateway.spans.items()
        if span["path"] == "mini_data_utils/csvlite.py"
    ]
    narrow_mutation = RequestedTool(
        name="apply_git_diff",
        action_id="narrow-mutation",
        arguments={
            "git_diff": (
                "diff --git a/mini_data_utils/csvlite.py "
                "b/mini_data_utils/csvlite.py\n"
                "--- a/mini_data_utils/csvlite.py\n"
                "+++ b/mini_data_utils/csvlite.py\n"
                "@@ -9,5 +9,5 @@\n"
                "     rows: list[list[str]] = []\n"
                "     for physical_line in text.splitlines():\n"
                "         rows.extend(csv.reader([physical_line]))\n"
                "-    return rows\n"
                "+    return list(rows)\n"
                " \n"
            ),
            "hypothesis": "Materialize the return value.",
            "expected_behavior": "The public return type remains a list.",
            "evidence_span_ids": source_span_ids[:1],
            "edit_anchor": {
                "path": "mini_data_utils/csvlite.py",
                "old_text": "    return rows",
                "occurrence": 1,
            },
            "falsified_prior_hypothesis": None,
            "alternative_mechanism": None,
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
    unrelated_span_id = unrelated.output["spans"][0]["span_id"]
    uncovered = RequestedTool(
        name="apply_git_diff",
        action_id="uncovered-anchor",
        arguments={
            "git_diff": (
                "diff --git a/mini_data_utils/csvlite.py "
                "b/mini_data_utils/csvlite.py\n"
                "--- a/mini_data_utils/csvlite.py\n"
                "+++ b/mini_data_utils/csvlite.py\n"
                "@@ -3 +3 @@\n"
                "-import csv\n"
                "+import csv as csv_module\n"
            ),
            "hypothesis": "The import name should be explicit.",
            "expected_behavior": "The module alias is available.",
            "evidence_span_ids": [unrelated_span_id],
            "edit_anchor": {
                "path": "mini_data_utils/csvlite.py",
                "old_text": "import csv",
                "occurrence": 1,
            },
            "falsified_prior_hypothesis": None,
            "alternative_mechanism": None,
        },
    )

    rejected = gateway.execute(uncovered)

    assert rejected.status == "failed"
    assert "current evidence span must cover the edit-anchor file" in rejected.message


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
    assert refreshed.output["spans"][0]["span_id"] == gateway.last_successful_mutation[
        "postimage_evidence_span_id"
    ]


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
    mutation.arguments["git_diff"] += (
        "diff --git a/mini_data_utils/new_helper.py b/mini_data_utils/new_helper.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/mini_data_utils/new_helper.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
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


def test_repeated_signature_across_two_diffs_requires_alternative(gateway_factory) -> None:
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
    rejected = gateway.execute(mutation_call(gateway, action_id="missing-alternative"))
    assert rejected.status == "failed"
    assert "alternative_mechanism" in rejected.message
    accepted = gateway.execute(
        mutation_call(gateway, action_id="material-alternative", alternative=True)
    )
    assert accepted.status == "succeeded"
    assert gateway.requires_alternative is False


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
    call.arguments["git_diff"] = call.arguments["git_diff"].replace(
        "@@ -1,13 +1,11 @@", "@@ -1,13 +1,10 @@"
    )
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
            "mutation_admitted": True,
        },
    )
    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "--recount", "-"],
        cwd=workspace,
        input=call.arguments["git_diff"].encode("utf-8"),
        capture_output=True,
        check=False,
    )
    assert applied.returncode == 0

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
