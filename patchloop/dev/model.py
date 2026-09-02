"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Use only the supplied tools. There is no separate planning phase or planning tool.
You may request either 1-4 search_files/read_file calls in one response, or exactly
one run_check, apply_git_diff, or finish_task call. Never mix those shapes. run_check is
available immediately. Every mutation must include a concise hypothesis, expected
behavior, current evidence span IDs, and an exact source anchor. If the public context
requires a causal alternative, the next mutation must also state which prior hypothesis
was falsified and a materially different mechanism. The apply_git_diff git_diff value
must be a raw Git unified diff beginning exactly with "diff --git a/<path> b/<path>".
Never use "*** Begin Patch", "*** Update File", or another patch wrapper. All visible
checks must pass on the current diff before finish_task is available. The complete
current diff is projected in
context; do not request get_diff. Do not emit raw chain-of-thought. Private tests,
reference patches, and evaluator details are unavailable and must not be inferred.
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
        recent_checks = payload.get("recent_checks", [])
        if not spans and not current_diff.get("patch"):
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="search_files",
                        action_id="mock-search-source",
                        arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
                    ),
                    RequestedTool(
                        name="read_file",
                        action_id="mock-read-source",
                        arguments={
                            "path": self.mutation.path,
                            "start_line": 1,
                            "end_line": 80,
                        },
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
        current_hash = current_diff.get("patch_hash")
        current_checks = [row for row in recent_checks if row.get("diff_hash") == current_hash]
        if not current_checks or not all(row.get("passed") is True for row in current_checks):
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="run_check",
                        action_id="mock-visible-check",
                        arguments={"check_id": "existing-unit-tests"},
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
