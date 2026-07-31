"""Stateless model adapters for deterministic and live agent runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI

from patchloop.contracts import ModelConfig
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

SYSTEM_PROMPT_V1 = (
    "You are a constrained coding agent. Use only supplied tools. "
    "Inspect evidence, apply a minimal patch, run registered checks, "
    "review the diff, then answer exactly DONE. "
    "The apply_patch tool accepts only a raw Git unified diff beginning with "
    "'diff --git'; never use '*** Begin Patch' or '*** End Patch' markers."
)
SYSTEM_PROMPT_V2 = (
    "You are a constrained coding agent. Use only supplied tools. "
    "Inspect repository evidence, apply a minimal patch, and run every registered "
    "visible check against the exact current diff. After the checks pass, call "
    "get_diff and review its complete result on the next turn. Then call "
    "finish_task to submit; never use DONE text as a substitute. Any later patch "
    "invalidates prior check and review evidence. "
    "The apply_patch tool accepts only a raw Git unified diff beginning with "
    "'diff --git'; never use '*** Begin Patch' or '*** End Patch' markers."
)
SYSTEM_PROMPT_V3 = (
    SYSTEM_PROMPT_V2
    + " The investigation_ledger is durable within-run repository evidence. "
    "Consult it before searching or reading: do not repeat a recorded search "
    "or a fully covered file range. A semantic-cache replay means no new "
    "evidence was produced; change strategy when requested. Always obey "
    "phase_contract.allowed_next_actions. When exploration is not admitted, "
    "use the recorded evidence to advance to a patch or another allowed "
    "phase-advancing action."
)
SYSTEM_PROMPT_V4 = (
    SYSTEM_PROMPT_V3
    + " When the public issue benefits from executable confirmation and the "
    "phase contract advertises a registered probe profile, use run_probe with "
    "that profile to execute a temporary Python reproducer in the isolated, "
    "read-only sandbox; the probe is evidence, never part of the submitted "
    "patch. Never call an unregistered probe profile. After validation and "
    "get_diff, call review_task with public "
    "requirement assessments, exact evidence event sequences, targeted "
    "validation outcomes, and residual risks. Only then call finish_task. "
    "Do not claim a requirement is verified without cited trace evidence."
)
SYSTEM_PROMPT = SYSTEM_PROMPT_V2


@dataclass(frozen=True)
class RequestedTool:
    name: str
    action_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurnError:
    """A provider response that was billed but cannot be safely executed."""

    code: str
    message: str


@dataclass(frozen=True)
class ModelTurn:
    text: str = ""
    tool_calls: list[RequestedTool] = field(default_factory=list)
    done: bool = False
    requested_input_tokens: int | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0
    input_token_count_match: bool | None = None
    total_token_count_match: bool | None = None
    input_token_count_calls: int = 0
    response_id: str | None = None
    response_model: str | None = None
    response_service_tier: str | None = None
    system_fingerprint: str | None = None
    response_status: str | None = None
    response_truncation: str | None = None
    response_incomplete_reason: str | None = None
    error: ModelTurnError | None = None


class ModelAdapter(Protocol):
    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn: ...


@dataclass(frozen=True)
class MockTaskScript:
    """Public-only scripted behavior for deterministic offline smoke runs."""

    target_path: str
    patch: str
    rationale: str


@dataclass(frozen=True)
class MockProbeScript:
    """Public issue-derived probe for one explicit infrastructure fixture."""

    profile_id: str
    source: str


MOCK_TASK_SCRIPTS: dict[str, MockTaskScript] = {
    "csv-quoted-newline": MockTaskScript(
        target_path="mini_data_utils/csvlite.py",
        rationale="Use csv.reader over a text stream so quoted records span physical lines.",
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
    ),
    "config-falsy-override": MockTaskScript(
        target_path="mini_data_utils/config.py",
        rationale="Apply every explicit override value without using truthiness as presence.",
        patch=(
            "diff --git a/mini_data_utils/config.py b/mini_data_utils/config.py\n"
            "--- a/mini_data_utils/config.py\n"
            "+++ b/mini_data_utils/config.py\n"
            "@@ -8,5 +8,5 @@ def merge_config(\n"
            " \n"
            "     result = dict(base)\n"
            "     for key, value in override.items():\n"
            "-        result[key] = value or result.get(key)\n"
            "+        result[key] = value\n"
            "     return result\n"
        ),
    ),
    "path-prefix-boundary": MockTaskScript(
        target_path="mini_data_utils/pathmatch.py",
        rationale="Normalize dot segments and compare complete path boundaries.",
        patch=(
            "diff --git a/mini_data_utils/pathmatch.py b/mini_data_utils/pathmatch.py\n"
            "--- a/mini_data_utils/pathmatch.py\n"
            "+++ b/mini_data_utils/pathmatch.py\n"
            "@@ -1,9 +1,13 @@\n"
            ' """Path matching helpers with one audited boundary defect."""\n'
            " \n"
            "+import posixpath\n"
            "+\n"
            " \n"
            " def is_path_within(path: str, root: str) -> bool:\n"
            '     """Return whether path is root itself or one of its descendants."""\n'
            " \n"
            '-    normalized_path = path.replace("\\\\", "/").rstrip("/")\n'
            '-    normalized_root = root.replace("\\\\", "/").rstrip("/")\n'
            "-    return normalized_path.startswith(normalized_root)\n"
            '+    normalized_path = posixpath.normpath(path.replace("\\\\", "/"))\n'
            '+    normalized_root = posixpath.normpath(root.replace("\\\\", "/"))\n'
            "+    return normalized_path == normalized_root or normalized_path.startswith(\n"
            '+        f"{normalized_root}/"\n'
            "+    )\n"
        ),
    ),
}

MOCK_PROBE_SCRIPTS: dict[str, MockProbeScript] = {
    "csv-quoted-newline": MockProbeScript(
        profile_id="quoted-newline-case",
        source=(
            "import sys\n"
            "sys.path.insert(0, '/workspace')\n"
            "from mini_data_utils import parse_rows\n"
            "sample = 'key,note\\n1,\"left\\nright\"\\n'\n"
            "expected = [['key', 'note'], ['1', 'left\\nright']]\n"
            "assert parse_rows(sample) == expected\n"
            "print('probe-ok')\n"
        ),
    )
}


class MockModelAdapter:
    """Deterministic offline adapter backed only by public smoke scripts."""

    def __init__(
        self,
        task_id: str,
        completed_tools: list[str] | None = None,
        *,
        structured_finish: bool = True,
        structured_review: bool = False,
        structured_probe: bool = False,
    ) -> None:
        self.task_id = task_id
        self.completed_tools = list(completed_tools or [])
        self.structured_finish = structured_finish
        self.structured_review = structured_review
        self.structured_probe = structured_probe
        try:
            self.script = MOCK_TASK_SCRIPTS[task_id]
        except KeyError as exc:
            raise ContractError(f"no offline mock transcript for task: {task_id}") from exc
        self.probe_script = MOCK_PROBE_SCRIPTS.get(task_id)
        if self.structured_probe and self.probe_script is None:
            raise ContractError(
                f"no offline mock probe transcript for task: {task_id}"
            )

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        counts = {name: self.completed_tools.count(name) for name in set(self.completed_tools)}
        if counts.get("read_file", 0) == 0:
            return ModelTurn(
                text=f"Inspect the implicated implementation at {self.script.target_path}.",
                tool_calls=[
                    RequestedTool(
                        "read_file",
                        f"mock-{self.task_id}-read",
                        {"path": self.script.target_path, "start_line": 1, "end_line": 200},
                    )
                ],
            )
        if counts.get("apply_patch", 0) == 0:
            return ModelTurn(
                text=self.script.rationale,
                tool_calls=[
                    RequestedTool(
                        "apply_patch",
                        f"mock-{self.task_id}-patch",
                        {"patch": self.script.patch},
                    )
                ],
            )
        if counts.get("run_check", 0) == 0:
            return ModelTurn(
                text="Run the registered regression suite.",
                tool_calls=[
                    RequestedTool(
                        "run_check",
                        f"mock-{self.task_id}-check",
                        {"check_id": "existing-unit-tests"},
                    )
                ],
            )
        if counts.get("get_diff", 0) == 0:
            return ModelTurn(
                text="Review the final scoped diff.",
                tool_calls=[
                    RequestedTool("get_diff", f"mock-{self.task_id}-review", {})
                ],
            )
        if self.structured_probe and counts.get("run_probe", 0) == 0:
            try:
                payload = json.loads(context)
                phase_contract = payload["phase_contract"]
                registered_profiles = phase_contract[
                    "registered_probe_profile_ids"
                ]
                optional_actions = phase_contract["optional_actions"]
                allowed_actions = phase_contract[
                    "allowed_next_actions"
                ]
                available_tools = {
                    item["name"]
                    for item in tools
                    if isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                }
            except (
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                raise ContractError(
                    "mock probe requires the v6 registered-profile context"
                ) from exc
            assert self.probe_script is not None
            if (
                self.probe_script.profile_id not in registered_profiles
                or "run_probe" not in optional_actions
                or "run_probe" not in available_tools
            ):
                raise ContractError(
                    "mock probe profile is not registered and advertised"
                )
            if "run_probe" in allowed_actions:
                return ModelTurn(
                    text=(
                        "Run the registered issue-derived multiline CSV probe "
                        "against the read-only current workspace."
                    ),
                    tool_calls=[
                        RequestedTool(
                            "run_probe",
                            f"mock-{self.task_id}-probe",
                            {
                                "probe_id": self.probe_script.profile_id,
                                "source": self.probe_script.source,
                            },
                        )
                    ],
                )
        if self.structured_review and counts.get("review_task", 0) == 0:
            try:
                payload = json.loads(context)
                recent_events = payload["recent_events"]
                check_event = next(
                    item
                    for item in reversed(recent_events)
                    if item.get("type") == "ToolSucceeded"
                    and item["payload"].get("tool") == "run_check"
                )
                diff_event = next(
                    item
                    for item in reversed(recent_events)
                    if item.get("type") == "ToolSucceeded"
                    and item["payload"].get("tool") == "get_diff"
                )
                probe_event = (
                    next(
                        item
                        for item in reversed(recent_events)
                        if item.get("type") == "ToolSucceeded"
                        and item["payload"].get("tool") == "run_probe"
                    )
                    if counts.get("run_probe", 0) > 0
                    else None
                )
            except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ContractError(
                    "mock self-review requires current check and diff evidence"
                ) from exc
            evidence_event_sequences = [
                check_event["sequence"],
                diff_event["sequence"],
            ]
            targeted_validation = [
                {
                    "kind": "registered_check",
                    "event_sequence": check_event["sequence"],
                    "outcome": "passed",
                    "notes": (
                        "Registered public check passed on the current diff."
                    ),
                }
            ]
            requirement_status = "verified"
            requirement_notes = (
                "The current patch passed the registered regression check "
                "and matches the reviewed diff."
            )
            residual_risks = [
                "Private evaluator cases remain unavailable until submission."
            ]
            if probe_event is not None:
                probe_passed = probe_event["payload"].get("passed") is True
                evidence_event_sequences.append(probe_event["sequence"])
                targeted_validation.append(
                    {
                        "kind": "probe",
                        "event_sequence": probe_event["sequence"],
                        "outcome": (
                            "passed" if probe_passed else "failed"
                        ),
                        "notes": (
                            "The registered non-authoritative probe "
                            + (
                                "passed on the current diff."
                                if probe_passed
                                else "did not pass on the current diff."
                            )
                        ),
                    }
                )
                if probe_passed:
                    requirement_notes += (
                        " The registered issue-derived probe also passed."
                    )
                else:
                    requirement_status = "partially_verified"
                    residual_risks.append(
                        "The registered issue-derived probe did not pass."
                    )
            return ModelTurn(
                text="Record requirement-to-evidence review before submission.",
                tool_calls=[
                    RequestedTool(
                        "review_task",
                        f"mock-{self.task_id}-task-review",
                        {
                            "requirements": [
                                {
                                    "requirement": self.script.rationale,
                                    "status": requirement_status,
                                    "evidence_event_sequences": (
                                        evidence_event_sequences
                                    ),
                                    "notes": requirement_notes,
                                }
                            ],
                            "targeted_validation": targeted_validation,
                            "residual_risks": residual_risks,
                        },
                    )
                ],
            )
        if self.structured_finish:
            return ModelTurn(
                text="Submit the reviewed current diff.",
                tool_calls=[
                    RequestedTool(
                        "finish_task",
                        f"mock-{self.task_id}-finish",
                        {},
                    )
                ],
            )
        return ModelTurn(text="DONE", done=True)

    def record_completed(self, tool_name: str) -> None:
        self.completed_tools.append(tool_name)


class ReplayModelAdapter:
    def __init__(
        self,
        replay_path: str | Path,
        offset: int = 0,
        expected_hash: str | None = None,
    ) -> None:
        path = Path(replay_path)
        content = path.read_bytes()
        self.source_hash = sha256_bytes(content)
        if expected_hash is not None and self.source_hash != expected_hash:
            raise ContractError(
                f"replay hash mismatch: expected {expected_hash}, got {self.source_hash}"
            )
        try:
            lines = content.decode("utf-8").splitlines()
            self.turns = [json.loads(line) for line in lines if line.strip()]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError(f"invalid replay JSONL: {path}") from exc
        if not self.turns:
            raise ContractError(f"recorded response replay is empty: {path}")
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
            requested_input_tokens=raw.get("requested_input_tokens"),
            input_tokens=raw.get("input_tokens", 0),
            cached_input_tokens=raw.get("cached_input_tokens", 0),
            cache_write_input_tokens=raw.get("cache_write_input_tokens", 0),
            output_tokens=raw.get("output_tokens", 0),
            reasoning_output_tokens=raw.get("reasoning_output_tokens", 0),
            total_tokens=raw.get(
                "total_tokens",
                raw.get("input_tokens", 0) + raw.get("output_tokens", 0),
            ),
            input_token_count_match=raw.get("input_token_count_match"),
            total_token_count_match=raw.get("total_token_count_match"),
            input_token_count_calls=raw.get("input_token_count_calls", 0),
            response_id=raw.get("response_id"),
            response_model=raw.get("response_model"),
            response_service_tier=raw.get("response_service_tier"),
            system_fingerprint=raw.get("system_fingerprint"),
            response_status=raw.get("response_status"),
            response_truncation=raw.get("response_truncation"),
            response_incomplete_reason=raw.get("response_incomplete_reason"),
        )


class OpenAIResponsesAdapter:
    """One stateless Responses API request per PatchLoop turn."""

    def __init__(self, config: ModelConfig, client: OpenAI | None = None) -> None:
        self.config = config
        self.client = client or OpenAI()

    def request_payload(
        self,
        context: str,
        tools: list[dict[str, Any]],
        *,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> dict[str, Any]:
        reasoning: dict[str, str] = {
            "effort": self.config.reasoning_effort,
        }
        # reasoning.mode and persisted-reasoning context are GPT-5.6 controls.
        # Older GPT-5 reasoning models remain stateless here because PatchLoop
        # does not use previous_response_id and rebuilds every turn from durable
        # public state.
        if self.config.model_id.startswith("gpt-5.6"):
            reasoning.update(
                {
                    "mode": self.config.reasoning_mode,
                    "context": "current_turn",
                }
            )
        return {
            "model": self.config.model_id,
            "input": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": context},
            ],
            "tools": tools,
            "store": False,
            "reasoning": reasoning,
            "service_tier": self.config.service_tier,
            "max_output_tokens": self.config.max_output_tokens,
            "truncation": "disabled",
        }

    @staticmethod
    def _token_count_payload(request: dict[str, Any]) -> dict[str, Any]:
        return {
            key: request[key]
            for key in (
                "model",
                "input",
                "tools",
                "reasoning",
                "truncation",
            )
        }

    def count_input_tokens(self, request: dict[str, Any]) -> int:
        counted = self.client.responses.input_tokens.count(
            **self._token_count_payload(request)
        )
        return int(counted.input_tokens)

    def execute_request(
        self,
        request: dict[str, Any],
        *,
        requested_input_tokens: int,
    ) -> ModelTurn:
        response = self.client.responses.create(**request)
        usage = getattr(response, "usage", None)
        input_details = getattr(usage, "input_tokens_details", None) if usage else None
        output_details = getattr(usage, "output_tokens_details", None) if usage else None
        cached_input_tokens = int(
            (getattr(input_details, "cached_tokens", 0) if input_details else 0)
            or 0
        )
        cache_write_input_tokens = int(
            (getattr(input_details, "cache_write_tokens", 0) if input_details else 0)
            or 0
        )
        if usage is not None:
            cache_write_input_tokens = int(
                getattr(
                    usage,
                    "cache_write_tokens",
                    cache_write_input_tokens,
                )
                or 0
            )
        input_tokens = (
            int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        )
        output_tokens = (
            int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        )
        reasoning_output_tokens = int(
            (getattr(output_details, "reasoning_tokens", 0) if output_details else 0)
            or 0
        )
        raw_total_tokens = getattr(usage, "total_tokens", None) if usage else None
        total_tokens = (
            int(raw_total_tokens)
            if raw_total_tokens is not None
            else input_tokens + output_tokens
        )
        input_token_count_match = bool(
            usage is not None and requested_input_tokens == input_tokens
        )
        total_token_count_match = bool(
            usage is not None and total_tokens == input_tokens + output_tokens
        )
        response_status = getattr(response, "status", None)
        response_truncation = getattr(response, "truncation", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        if isinstance(incomplete_details, dict):
            response_incomplete_reason = incomplete_details.get("reason")
        else:
            response_incomplete_reason = getattr(incomplete_details, "reason", None)

        calls: list[RequestedTool] = []
        parse_error: ModelTurnError | None = None
        if not input_token_count_match:
            parse_error = ModelTurnError(
                code="input_token_count_mismatch",
                message=(
                    "preflight input token count did not match billed response usage"
                ),
            )
        elif response_status not in {None, "completed"} or response_incomplete_reason:
            parse_error = ModelTurnError(
                code="incomplete_response",
                message=(
                    "provider response was incomplete"
                    + (
                        f": {response_incomplete_reason}"
                        if response_incomplete_reason
                        else ""
                    )
                ),
            )
        else:
            for item in response.output:
                if getattr(item, "type", None) != "function_call":
                    continue
                try:
                    arguments = json.loads(item.arguments)
                except (json.JSONDecodeError, TypeError):
                    parse_error = ModelTurnError(
                        code="invalid_tool_arguments_json",
                        message="provider function-call arguments were not valid JSON",
                    )
                    break
                if not isinstance(arguments, dict):
                    parse_error = ModelTurnError(
                        code="invalid_tool_arguments_type",
                        message="provider function-call arguments were not a JSON object",
                    )
                    break
                calls.append(
                    RequestedTool(
                        name=item.name,
                        action_id=item.call_id,
                        arguments=arguments,
                    )
                )
        if parse_error is not None:
            calls = []
        text = response.output_text or ""
        return ModelTurn(
            text=text,
            tool_calls=calls,
            done=parse_error is None and text.strip() == "DONE" and not calls,
            requested_input_tokens=requested_input_tokens,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_write_input_tokens=cache_write_input_tokens,
            output_tokens=output_tokens,
            reasoning_output_tokens=reasoning_output_tokens,
            total_tokens=total_tokens,
            input_token_count_match=input_token_count_match,
            total_token_count_match=total_token_count_match,
            input_token_count_calls=1,
            response_id=response.id,
            response_model=getattr(response, "model", None),
            response_service_tier=getattr(response, "service_tier", None),
            system_fingerprint=getattr(response, "system_fingerprint", None),
            response_status=response_status,
            response_truncation=response_truncation,
            response_incomplete_reason=response_incomplete_reason,
            error=parse_error,
        )

    def next_turn(self, context: str, tools: list[dict[str, Any]]) -> ModelTurn:
        request = self.request_payload(context, tools)
        requested_input_tokens = self.count_input_tokens(request)
        return self.execute_request(
            request,
            requested_input_tokens=requested_input_tokens,
        )
