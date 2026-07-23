"""Stateless model adapters for deterministic and live agent runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI

from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError

SYSTEM_PROMPT = (
    "You are a constrained coding agent. Use only supplied tools. "
    "Inspect evidence, apply a minimal patch, run registered checks, "
    "review the diff, then answer exactly DONE."
)


@dataclass(frozen=True)
class RequestedTool:
    name: str
    action_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    text: str = ""
    tool_calls: list[RequestedTool] = field(default_factory=list)
    done: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    response_id: str | None = None


class ModelAdapter(Protocol):
    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn: ...


class MockModelAdapter:
    """Deterministic offline adapter; it never reads evaluator-only files."""

    def __init__(self, task_id: str, completed_tools: list[str] | None = None) -> None:
        self.task_id = task_id
        self.completed_tools = list(completed_tools or [])

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        del context, tools
        counts = {name: self.completed_tools.count(name) for name in set(self.completed_tools)}
        if counts.get("read_file", 0) == 0:
            return ModelTurn(
                text="Inspect the implicated parser before editing.",
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        "mock-read-parser",
                        {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 200},
                    )
                ],
            )
        if counts.get("apply_patch", 0) == 0:
            if self.task_id != "csv-quoted-newline":
                raise ContractError(f"no offline mock transcript for task: {self.task_id}")
            patch = (
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
            )
            return ModelTurn(
                text="Use csv.reader over a text stream so quoted records span physical lines.",
                tool_calls=[RequestedTool("apply_patch", "mock-fix-parser", {"patch": patch})],
            )
        if counts.get("run_check", 0) == 0:
            return ModelTurn(
                text="Run the registered regression suite.",
                tool_calls=[
                    RequestedTool(
                        "run_check", "mock-visible-check", {"check_id": "existing-unit-tests"}
                    )
                ],
            )
        if counts.get("get_diff", 0) == 0:
            return ModelTurn(
                text="Review the final scoped diff.",
                tool_calls=[RequestedTool("get_diff", "mock-review-diff", {})],
            )
        return ModelTurn(text="DONE", done=True)

    def record_completed(self, tool_name: str) -> None:
        self.completed_tools.append(tool_name)


class ReplayModelAdapter:
    def __init__(self, replay_path: str | Path, offset: int = 0) -> None:
        lines = Path(replay_path).read_text(encoding="utf-8").splitlines()
        self.turns = [json.loads(line) for line in lines if line.strip()]
        self.offset = offset

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        del context, tools
        if self.offset >= len(self.turns):
            raise ContractError("recorded response replay was exhausted")
        raw = self.turns[self.offset]
        self.offset += 1
        calls = [RequestedTool(**call) for call in raw.get("tool_calls", [])]
        return ModelTurn(
            text=raw.get("text", ""),
            tool_calls=calls,
            done=raw.get("done", False),
            input_tokens=raw.get("input_tokens", 0),
            output_tokens=raw.get("output_tokens", 0),
            response_id=raw.get("response_id"),
        )


class OpenAIResponsesAdapter:
    """One stateless Responses API request per PatchLoop turn."""

    def __init__(self, config: ModelConfig, client: OpenAI | None = None) -> None:
        self.config = config
        self.client = client or OpenAI()

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        response = self.client.responses.create(
            model=self.config.model_id,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {"role": "user", "content": context},
            ],
            tools=tools,
            store=False,
            reasoning={
                "effort": self.config.reasoning_effort,
                "context": "current_turn",
            },
            max_output_tokens=self.config.max_output_tokens,
        )
        calls: list[RequestedTool] = []
        for item in response.output:
            if getattr(item, "type", None) != "function_call":
                continue
            calls.append(
                RequestedTool(
                    name=item.name,
                    action_id=item.call_id,
                    arguments=json.loads(item.arguments),
                )
            )
        usage = getattr(response, "usage", None)
        text = response.output_text or ""
        return ModelTurn(
            text=text,
            tool_calls=calls,
            done=text.strip() == "DONE" and not calls,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            response_id=response.id,
        )
