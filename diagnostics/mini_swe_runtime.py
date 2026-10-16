"""Operator adapter for pinned mini-SWE-agent; no PatchLoop solving policy."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from contextlib import suppress
from decimal import Decimal
from pathlib import Path

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.usage_diagnostics import provider_usage_evidence, usage_token_value
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_json

MODEL = "gpt-5.4-mini-2026-03-17"
UPSTREAM_REVISION = "a83fcae82d2a08f0ee0c688f9d137b3566c097f8"
ROW_CAP = Decimal("1.20")
SOLVER_SECONDS = 1470


class OperationalStop(RuntimeError):
    """Stop the entire panel, including after missing usage or uncertain cleanup."""


def command(args, *, timeout=60, merge=False, **kwargs):
    # Never inherit provider credentials into Docker, Git, or evaluator processes.
    from diagnostics.portfolio_dev20 import native_env

    return subprocess.run(
        list(map(str, args)),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge else subprocess.PIPE,
        timeout=timeout,
        env=native_env(),
        **kwargs,
    )


def load_upstream(preparation: Path):
    """Use the exact upstream loop/parsers, with dependencies isolated outside the repo."""
    upstream = preparation / "upstream"
    revision = command(["git", "-C", upstream, "rev-parse", "HEAD"]).stdout.decode().strip()
    dirty = command(["git", "-C", upstream, "status", "--porcelain"]).stdout
    if revision != UPSTREAM_REVISION or dirty:
        raise ValueError("mini-SWE-agent source differs from the pinned release")
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(preparation / "empty-config")
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(preparation / "python-libs"), str(upstream / "src")]
    from minisweagent.agents.default import DefaultAgent

    return DefaultAgent


def flatten_messages(messages):
    """Same stateless linear-history projection as upstream LitellmResponseModel."""
    return [
        {k: v for k, v in item.items() if k != "extra"}
        for message in messages
        for item in (
            message.get("output", []) if message.get("object") == "response" else [message]
        )
    ]


class CountedModel:
    """Direct Responses transport; upstream prompt, action parser and observations."""

    def __init__(self, client, config, root: Path, deadline: ExecutionDeadline):
        if client.max_retries != 0:
            raise ValueError("zero SDK retries required")
        self.client, self.config, self.deadline = client, config, deadline
        self.ledger = DevCostLedger(ROW_CAP, pricing_for_model(MODEL))
        self.journal = DevJournal(root, "run_dev_minimodel")
        self.store = ArtifactStore(root / "artifacts")
        self.calls = 0
        self.uncertain = False

    def get_template_vars(self, **kwargs):
        return self.config

    def serialize(self):
        return {
            "info": {"config": {"model": self.config, "transport": "counted-responses-zero-retry"}}
        }

    def format_message(self, **kwargs):
        return kwargs

    def format_observation_messages(self, message, outputs, template_vars=None):
        from minisweagent.models.utils.actions_toolcall_response import (
            format_toolcall_observation_messages,
        )

        return format_toolcall_observation_messages(
            actions=message.get("extra", {}).get("actions", []),
            outputs=outputs,
            observation_template=self.config["observation_template"],
            template_vars=template_vars,
        )

    def query(self, messages):
        from minisweagent.exceptions import FormatError, LimitsExceeded
        from minisweagent.models.utils.actions_toolcall_response import (
            BASH_TOOL_RESPONSE_API,
            finish_reason_from_responses_api,
            parse_toolcall_actions_response,
        )

        if self.uncertain:
            raise OperationalStop("provider accounting is uncertain")
        if self.calls >= 40:
            raise LimitsExceeded({"role": "exit", "extra": {"exit_status": "CallLimit"}})
        self.deadline.check()
        request = {
            "model": MODEL,
            "input": flatten_messages(messages),
            "tools": [BASH_TOOL_RESPONSE_API],
            "reasoning": {"effort": "xhigh"},
            "parallel_tool_calls": True,
            "truncation": "disabled",
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "service_tier": "default",
        }
        identity = self.store.put_json(request).content_hash
        self.journal.append("external_count_started", {"request_hash": identity})
        try:
            count = self.client.responses.input_tokens.count(
                **OpenAIResponsesAdapter._count_payload(request),
                timeout=self.deadline.bounded_timeout(120),
            ).input_tokens
            if type(count) is not int or count < 0:
                raise ValueError("invalid input count")
        except Exception as exc:
            self.uncertain = True
            self.journal.append("external_count_failed", {"error_type": type(exc).__name__})
            raise OperationalStop("input counting failed; no retry") from exc
        admitted = self.ledger.admit(count, desired_output_ceiling=25000)
        self.journal.append("external_count_finished", {"input_tokens": count})
        if admitted is None or count + admitted.output_ceiling > 400000:
            raise LimitsExceeded({"role": "exit", "extra": {"exit_status": "CostOrContextLimit"}})
        request["max_output_tokens"] = admitted.output_ceiling
        self.deadline.check()
        self.calls += 1
        self.journal.append(
            "external_dispatch_started",
            {
                "request_hash": self.store.put_json(request).content_hash,
                "reservation_nanos": admitted.reserved_cost_nanos,
                "call": self.calls,
            },
        )
        # Any failure between dispatch and durable settlement leaves billing uncertain.
        self.uncertain = True
        try:
            response = self.client.responses.create(
                **request,
                timeout=self.deadline.bounded_timeout(180),
            )
        except Exception as exc:
            self.uncertain = True
            self.journal.append("external_dispatch_uncertain", {"error_type": type(exc).__name__})
            raise OperationalStop("provider transport failed; billing unknown; no retry") from exc
        raw = response.model_dump(mode="json")
        response_hash = self.store.put_json(raw).content_hash
        usage = provider_usage_evidence(response, count)
        self.journal.append("external_response", {"response_hash": response_hash, "usage": usage})
        if usage["failure_kind"] is not None:
            self.uncertain = True
            raise OperationalStop("provider usage is missing, invalid, or disagrees with count")
        cost = self.ledger.settle(
            input_tokens=usage_token_value(usage, "input_tokens"),
            cached_input_tokens=usage_token_value(usage, "cached_input_tokens"),
            output_tokens=usage_token_value(usage, "output_tokens"),
        )
        self.journal.append("external_usage_settled", {"cost_nanos": cost})
        if (
            cost > admitted.reserved_cost_nanos
            or response.model != MODEL
            or response.service_tier not in (None, "default")
        ):
            self.uncertain = True
            raise OperationalStop("provider identity or reservation mismatch")
        self.uncertain = False
        extra = {"cost": cost / 1e9, "timestamp": time.time()}
        try:
            actions = parse_toolcall_actions_response(
                response.output,
                format_error_template=self.config["format_error_template"],
                template_kwargs={"finish_reason": finish_reason_from_responses_api(response)},
            )
        except FormatError as exc:
            exc.messages[0]["extra"].update(extra | {"response": raw})
            raise
        return raw | {"extra": extra | {"actions": actions}}


class PublicContainer:
    """Bash only in an offline, read-only-root container with no host mounts."""

    def __init__(self, row, root: Path, deadline: ExecutionDeadline):
        self.row, self.root, self.deadline = row, root, deadline
        self.name = "pl-mini-" + uuid.uuid4().hex[:12]
        self.journal = DevJournal(root, "run_dev_minienvironment")
        self.store = ArtifactStore(root / "artifacts")
        self.actions = 0
        self.closed = False
        self.env = {
            "PATH": "/opt/miniconda3/envs/testbed/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONPATH": "/testbed/src:/testbed",
            "HOME": "/tmp",
            "PAGER": "cat",
            "MANPAGER": "cat",
            "PIP_PROGRESS_BAR": "off",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        }
        args = [
            "docker",
            "run",
            "-d",
            "--pull=never",
            "--name",
            self.name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--memory=2g",
            "--cpus=2",
            "--pids-limit=128",
            "--tmpfs",
            "/testbed:rw,exec,size=768m",
            "--tmpfs",
            "/tmp:rw,exec,size=768m",
            "--workdir=/testbed",
            "--entrypoint=sleep",
            row["image"],
            "1800",
        ]
        self.journal.append("external_container_requested", {"name": self.name, "args": args})
        try:
            command(args, timeout=deadline.bounded_timeout(60))
            command(
                ["docker", "exec", "-i", self.name, "tar", "-xf", "-", "-C", "/testbed"],
                input=Path(row["source_archive"]).read_bytes(),
                timeout=deadline.bounded_timeout(60),
            )
            setup = (
                "git init -q /testbed && git config user.name Benchmark && "
                "git config user.email benchmark@localhost && git add -A && "
                "git commit -qm base"
            )
            self.operator_command(setup, timeout=60)
            self.journal.append("external_container_ready", {"name": self.name})
        except BaseException:
            self.cleanup()
            raise

    def operator_command(self, script, *, timeout=60):
        args = ["docker", "exec", "-w", "/testbed"]
        for key, value in self.env.items():
            args.extend(["-e", f"{key}={value}"])
        # timeout runs inside the container: killing docker.exe alone leaves bash alive.
        seconds = max(1, int(self.deadline.bounded_timeout(timeout)))
        args.extend([self.name, "timeout", "-k", "2", str(seconds), "bash", "-c", script])
        return command(args, timeout=seconds + 8, merge=True)

    def execute(self, action, cwd=""):
        from minisweagent.exceptions import LimitsExceeded, Submitted

        if self.actions >= 100:
            raise LimitsExceeded({"role": "exit", "extra": {"exit_status": "ActionLimit"}})
        self.deadline.check()
        self.actions += 1
        identity = {"action_id": f"bash_{self.actions}", "input_hash": sha256_json(action)}
        self.journal.append("external_action_started", identity | {"action": action})
        try:
            result = self.operator_command(action["command"])
            output = {
                "returncode": 0,
                "output": result.stdout.decode("utf-8", "replace"),
                "exception_info": "",
            }
        except subprocess.CalledProcessError as exc:
            if exc.returncode in (124, 137):
                raise OperationalStop("shell timeout; terminate container") from exc
            output = {
                "returncode": exc.returncode,
                "output": exc.stdout.decode("utf-8", "replace"),
                "exception_info": "",
            }
        self.journal.append(
            "external_action_finished",
            identity
            | {
                "output_hash": self.store.put_json(output).content_hash,
            },
        )
        lines = output["output"].lstrip().splitlines(keepends=True)
        if (
            lines
            and lines[0].strip() == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
            and output["returncode"] == 0
        ):
            raise Submitted(
                {
                    "role": "exit",
                    "content": "".join(lines[1:]),
                    "extra": {"exit_status": "Submitted", "submission": "".join(lines[1:])},
                }
            )
        return output

    def get_template_vars(self, **kwargs):
        return {"cwd": "/testbed", "timeout": 60, "env": self.env}

    def serialize(self):
        return {"info": {"config": {"environment": self.get_template_vars()}}}

    def cleanup(self):
        if self.closed:
            return
        # Remove only this invocation's randomly named container, never images/volumes.
        with suppress(subprocess.CalledProcessError):
            command(["docker", "rm", "-f", self.name], timeout=30)
        remaining = command(["docker", "ps", "-aq", "--filter", f"name=^/{self.name}$"])
        if remaining.stdout.strip():
            raise OperationalStop("container cleanup unconfirmed")
        self.closed = True
        self.journal.append("external_cleanup_confirmed", {"name": self.name})
