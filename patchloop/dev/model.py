"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, PublicWorkingState, RequestedTool
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Use only the supplied tools. There is no separate planning phase or planning tool.
Every response must request at least one supplied tool. Request either 1-4
search_files/read_file calls in one response, or exactly one run_check,
apply_git_diff, finish_task, or stop_task call. Never mix those shapes. Registered
run_check tools are available immediately. Use stop_task only when no valid public
read, check, or safe scoped mutation can make progress; provide a concise conclusion,
not chain-of-thought. Every mutation must include a concise hypothesis, expected
behavior, current evidence span IDs, and an exact source anchor. If the public context
requires a causal alternative, the next mutation must also state which prior hypothesis
was falsified and a materially different mechanism. The apply_git_diff git_diff value
must be a raw Git unified diff beginning exactly with "diff --git a/<path> b/<path>".
Never use "*** Begin Patch", "*** Update File", or another patch wrapper. All visible
checks must pass on the current diff before finish_task is available. The complete
current diff is projected in
context; do not request get_diff. Do not emit raw chain-of-thought. Private tests,
reference patches, and evaluator details are unavailable and must not be inferred.
Every read/search call must carry bounded public working_state. State the current
causal working_hypothesis, one exact evidence_gap that this call can resolve, and a
concrete decision_after_result. This is a concise execution decision, not
chain-of-thought. Update it from the latest public result. When the stated evidence
gap is resolved, follow the recorded decision by mutating or stopping instead of
re-reading the same source.
When last_failed_mutation is present, it is an unresolved public mutation from a
prior stateless turn. Repair or explicitly replace that mutation before unrelated
exploration. Read/search remains available when it is needed for the repair.
"""


@dataclass(frozen=True)
class MockMutation:
    path: str
    anchor: str
    patch: str
    hypothesis: str
    expected_behavior: str


_CSV_MUTATION = MockMutation(
    path="mini_data_utils/csvlite.py",
    anchor=(
        "    rows: list[list[str]] = []\n"
        "    for physical_line in text.splitlines():\n"
        "        rows.extend(csv.reader([physical_line]))\n"
        "    return rows"
    ),
    patch=(
        "diff --git a/mini_data_utils/csvlite.py b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,13 +1,11 @@\n"
        ' """A deliberately small CSV reader with one audited defect."""\n'
        " \n"
        " import csv\n"
        "+import io\n"
        " \n"
        " \n"
        " def parse_rows(text: str) -> list[list[str]]:\n"
        '     """Parse CSV text into rows while preserving quoted values."""\n'
        " \n"
        "-    rows: list[list[str]] = []\n"
        "-    for physical_line in text.splitlines():\n"
        "-        rows.extend(csv.reader([physical_line]))\n"
        "-    return rows\n"
        '+    return list(csv.reader(io.StringIO(text, newline="")))\n'
        " \n"
    ),
    hypothesis="Physical-line splitting resets the CSV parser inside a quoted record.",
    expected_behavior="One csv.reader over a text stream preserves quoted embedded newlines.",
)

MOCK_MUTATIONS = {"csv-quoted-newline": _CSV_MUTATION}


class MockDevAdapter:
    """One public smoke transcript used only for deterministic offline tests."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        try:
            self.mutation = MOCK_MUTATIONS[task_id]
        except KeyError as exc:
            raise ContractError(f"no dev-head mock script for task: {task_id}") from exc

    def next_turn(self, context: str, tools: list[dict]) -> DevModelTurn:
        del tools
        try:
            payload = json.loads(context)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ContractError("dev-head mock received invalid public context") from exc
        latest_spans = [
            span
            for result in payload.get("latest_tool_results", [])
            for span in result.get("output", {}).get("spans", [])
        ]
        spans = [*latest_spans, *payload.get("source_spans", [])]
        current_diff = payload.get("current_diff", {})
        remaining_check_ids = payload.get("remaining_visible_check_ids", [])
        if not spans and not current_diff.get("patch"):
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="search_files",
                        action_id="mock-search-source",
                        arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
                        working_state=PublicWorkingState(
                            working_hypothesis=(
                                "The parser likely loses logical records by iterating "
                                "physical lines."
                            ),
                            evidence_gap="Locate the parser implementation.",
                            decision_after_result=(
                                "Read the located parser body, then mutate if it confirms "
                                "per-line parsing."
                            ),
                        ),
                    ),
                    RequestedTool(
                        name="read_file",
                        action_id="mock-read-source",
                        arguments={
                            "path": self.mutation.path,
                            "start_line": 1,
                            "end_line": 80,
                        },
                        working_state=PublicWorkingState(
                            working_hypothesis=(
                                "The parser likely loses logical records by iterating "
                                "physical lines."
                            ),
                            evidence_gap="Inspect the complete parser body and its return path.",
                            decision_after_result=(
                                "Apply the smallest parser-lifetime mutation if the body confirms "
                                "the "
                                "hypothesis; otherwise inspect its direct caller."
                            ),
                        ),
                    ),
                ]
            )
        if not current_diff.get("patch"):
            spans = [item["span_id"] for item in spans if item.get("path") == self.mutation.path]
            if not spans:
                raise ContractError("mock mutation requires a current source span")
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="apply_git_diff",
                        action_id="mock-apply-mutation",
                        arguments={
                            "git_diff": self.mutation.patch,
                            "hypothesis": self.mutation.hypothesis,
                            "expected_behavior": self.mutation.expected_behavior,
                            "evidence_span_ids": spans[:2],
                            "edit_anchor": {
                                "path": self.mutation.path,
                                "old_text": self.mutation.anchor,
                                "occurrence": 1,
                            },
                            "falsified_prior_hypothesis": None,
                            "alternative_mechanism": None,
                        },
                    )
                ]
            )
        if remaining_check_ids:
            check_id = remaining_check_ids[0]
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="run_check",
                        action_id=f"mock-visible-check-{check_id}",
                        arguments={"check_id": check_id},
                    )
                ]
            )
        return DevModelTurn(
            tool_calls=[
                RequestedTool(
                    name="finish_task",
                    action_id="mock-finish",
                    arguments={},
                )
            ]
        )
