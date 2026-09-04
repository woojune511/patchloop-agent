"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Use only the supplied tools. There is no separate planning phase or planning tool.
Every response must request at least one supplied tool. Request either 1-4
search_files/read_file calls in one response, or exactly one run_check,
replace_text, finish_task, or stop_task call. Never mix those shapes. Registered
tools are derived from the current workflow gate and remaining action horizon; a tool
that is absent is not available this turn. Every tool call must carry turn_decision,
one bounded public decision for that concrete action. Its mode must match the tool
family. Every call in a parallel read batch must use inspect mode, while its basis and
evidence_goal may describe that call's distinct public question. evidence_goal is
required only for inspect; it is null for every other mode. Each decision describes
why you are taking that action now, after the preceding public tool results, rather
than promising a future action.
Use stop_task when no available public action supports safe progress; provide a concise
conclusion, not chain-of-thought. mutation_readiness.state=ready_to_attempt means only
that a current exact mutation anchor exists; it does not claim that the semantic
solution is sufficient. Another read must name a specific uncovered range or unresolved
public symbol in evidence_goal; otherwise prefer replace_text or stop_task. Every
mutation must include a concise hypothesis, expected behavior, and one exact
old_text/new_text replacement. Do not select or serialize evidence span IDs for a
mutation. The gateway binds the exact anchor to the most recently observed current
public span that fully covers it and fails closed when no such span exists; it also
constructs the canonical Git diff. An accepted mutation's bounded post-image becomes
current evidence for a same-file repair automatically. A commitment_signal is
soft guidance, not a tool restriction: when active, use current actionable evidence
to mutate or stop unless one materially different public evidence gap remains. If the
public context requires a causal alternative, the next mutation must also state which
prior hypothesis was falsified and a materially different mechanism in
causal_revision. When current_public_failure is present, treat its mapped public
statement as the current counterexample. A same_public_failure_site comparison means
the prior edit did not move that public failure; a later public source location means
only that the earlier failure no longer stopped this execution first. Tie the next
hypothesis and causal_revision directly to that statement. If later_source_lines_observed
is false, do not use later checks or platform sections as evidence because this execution
did not reach them. Do not write a Git diff or patch wrapper. All visible checks must pass
on the current diff before
finish_task is available. The complete current diff is projected in context; do not
request get_diff. Do not emit raw chain-of-thought. Private tests, reference patches,
and evaluator details are unavailable and must not be inferred.
After a failed visible check, current exact mutation evidence keeps replace_text
available. A targeted read_file may also be offered, but it is optional when the mapped
public failure and current post-image already justify an exact repair. It is required
only when current exact anchor evidence is absent. Do not perform a ceremonial read
when replace_text is already justified.
When last_failed_mutation is present, it is an unresolved public mutation from a
prior tool turn. Repair or explicitly replace that mutation before unrelated
exploration. A scope or replacement-contract failure must be repaired from its
preserved exact replacement without broad inspection. An invalid anchor or evidence
gets exactly one targeted read_file opportunity on the failed path; search_files is
not available in that repair window.
"""


@dataclass(frozen=True)
class MockMutation:
    path: str
    old_text: str
    new_text: str
    hypothesis: str
    expected_behavior: str


_CSV_MUTATION = MockMutation(
    path="mini_data_utils/csvlite.py",
    old_text=(
        "import csv\n"
        "\n"
        "\n"
        "def parse_rows(text: str) -> list[list[str]]:\n"
        '    """Parse CSV text into rows while preserving quoted values."""\n'
        "\n"
        "    rows: list[list[str]] = []\n"
        "    for physical_line in text.splitlines():\n"
        "        rows.extend(csv.reader([physical_line]))\n"
        "    return rows"
    ),
    new_text=(
        "import csv\n"
        "import io\n"
        "\n"
        "\n"
        "def parse_rows(text: str) -> list[list[str]]:\n"
        '    """Parse CSV text into rows while preserving quoted values."""\n'
        "\n"
        '    return list(csv.reader(io.StringIO(text, newline="")))'
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
            decision = PublicTurnDecision(
                mode="inspect",
                basis="Locate and inspect the public parser implementation once.",
                evidence_goal="Identify the parser lifetime and exact mutation anchor.",
            )
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="search_files",
                        action_id="mock-search-source",
                        arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
                        turn_decision=decision,
                    ),
                    RequestedTool(
                        name="read_file",
                        action_id="mock-read-source",
                        arguments={
                            "path": self.mutation.path,
                            "start_line": 1,
                            "end_line": 80,
                        },
                        turn_decision=decision,
                    ),
                ]
            )
        if not current_diff.get("patch"):
            matching_spans = [item for item in spans if item.get("path") == self.mutation.path]
            if not matching_spans:
                raise ContractError("mock mutation requires a current source span")
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="replace_text",
                        action_id="mock-apply-mutation",
                        arguments={
                            "path": self.mutation.path,
                            "old_text": self.mutation.old_text,
                            "new_text": self.mutation.new_text,
                            "occurrence": 1,
                            "hypothesis": self.mutation.hypothesis,
                            "expected_behavior": self.mutation.expected_behavior,
                            "causal_revision": None,
                        },
                        turn_decision=PublicTurnDecision(
                            mode="mutate",
                            basis=(
                                "The public source confirms that physical-line iteration resets "
                                "the CSV parser."
                            ),
                            evidence_goal=None,
                        ),
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
                        turn_decision=PublicTurnDecision(
                            mode="verify",
                            basis="Run the next unexecuted visible check on the current diff.",
                            evidence_goal=None,
                        ),
                    )
                ]
            )
        return DevModelTurn(
            tool_calls=[
                RequestedTool(
                    name="finish_task",
                    action_id="mock-finish",
                    arguments={},
                    turn_decision=PublicTurnDecision(
                        mode="finish",
                        basis="Every visible check passed on the projected current diff.",
                        evidence_goal=None,
                    ),
                )
            ]
        )
