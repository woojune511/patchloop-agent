"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Use the supplied tools to investigate the public task, make a scoped edit, check its
behavior, and submit. Every response must request either 1-4 read_file/search_files
calls or exactly one replace_text, run_check, run_probe, finish_task, or stop_task,
using only the tools supplied on this turn. Do not mix
those shapes. Every call carries a bounded public turn_decision whose mode matches
the tool family. Parallel inspections can have different basis and evidence_goal.
Use evidence_goal to name the public question the inspection can answer, including
useful negative searches and rereads. Other modes have evidence_goal=null.

Current tool results and public context are evidence; update your hypothesis when a
check supplies a counterexample. Before inspecting, use the already delivered source
and notes to identify what remains unanswered. Choose another inspection when its answer
could change the edit or next check; do not reread merely to restate an answered question.
Otherwise try the supported edit or a discriminating public experiment.
Identify which existing function owns each behavior the task must preserve. Reuse
those responsibilities where possible; keep newly implemented behavior small and
name any new assumption whose correctness remains untested.
Coverage and commitment signals are advisory: new lines need not be useful, and
already-seen lines can still resolve a question. Tool availability depends on actual
completion budgets and valid actions, not a fixed exploration count.
mutation_readiness.state=ready_to_attempt means only that current editable source
evidence is delivered. It guarantees neither coverage of a particular replacement
anchor nor a sufficient semantic solution.

An optional memory_update in turn_decision can retain concise source-backed public
observations, the current implementation approach, and unverified behavior. Preserve why
the observed code causes a behavior, not just which wrapper delegates to which function.
Distinguish observations from proposed mechanisms and untested assumptions; close an
answered open_question or replace it with the next uncertainty. Cite behavior-bearing
public source ranges or prior tool-result
action IDs. Update an existing note_id when refining a note even if its citations change;
note_id=null creates a separate note. To consolidate duplicates, update one note and use
remove_note_ids for the redundant IDs. Distinct facts may share a source. No update or
three-part plan is required each turn. These are model-authored notes, not verified
semantic facts or reasoning transcripts. A note's status=current only means its cited
evidence is current; its interpretation remains unverified. After an edit, reconsider
behavior claims against the post-image even if unchanged citations let the note survive.
memory_update=null preserves notes and the
question; within an update, open_question=null clears the question. Do not repeat an
update across a parallel batch.
The update is evaluated before the current batch executes. Before observing an
answer, use findings=[] with open_question, or leave memory_update=null. Do not
cite pending or a result from the batch you are requesting. After receiving a
result, create a source-backed note on a later call with note_id=null; update only
IDs actually returned in the stored findings or memory_update_result. Read the
separate memory_update_result: a successful main action does not mean its note
was stored. Correct a rejected annotation on a useful subsequent call, without
repeating a source read merely to retry the annotation. Source-change notices
identify notes that expired; do not treat their former IDs as existing notes.

A mutation requires hypothesis, expected_behavior, and one exact old_text/new_text
replacement in an allowed existing file. The gateway binds observed current evidence
and constructs the Git diff; do not supply evidence span IDs or a patch wrapper.
Use the smallest sufficient unique exact anchor. Avoid copying unchanged signatures or
docstrings for an executable-line edit; preserve the observed line breaks exactly.
The complete current diff is in context. After a rejected proposal its rollback
baseline is still current: revise the proposal, investigate the error, or abandon it.
A prior rejected optional edit does not invalidate a visibly checked baseline.

Treat a visible check failure as an observation about the executed behavior. A
mapped failure location is evidence about that execution, not a prohibition on
investigating other public dependencies. Repeated failures may justify revising the
causal hypothesis; causal_revision is optional explanatory metadata, never a forced
claim that a hypothesis has been falsified. After failure, use current evidence for
a direct edit when sufficient, or inspect any registered public source while the
budget allows. A source read is necessary only to acquire missing exact edit evidence.

All visible checks must pass on the submitted diff. An edit invalidates earlier
checks; finish_task submits the currently checked baseline. When run_probe is supplied,
use a small public behavior experiment to test a concrete uncertainty. Its output is
diagnostic: probe success does not satisfy a visible check, and failure may be in the
experiment itself. Test assumptions introduced by new branches using public input
variations, not just the examples already covered by registered checks.
Distinguish behavior actually tested from remaining assumptions;
passing the available tests does not establish correctness for all paths.
Use stop_task when no
available action supports progress. Keep decisions and findings concise; never emit
raw chain-of-thought. Private tests, reference patches, and evaluator details are
unavailable and must not be inferred.
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
