"""Historical boundary-example helpers; the incompatible paid panel is retired."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

# Retained import API for the separately frozen observation-repair diagnostic.
from patchloop import prepared_probe_dependencies as deps  # noqa: F401
from patchloop.artifacts import ArtifactStore
from patchloop.dev import working_plan
from patchloop.dev.contracts import DevRunRequest
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json

MODEL = "gpt-5.4-2026-03-05"
RUN_CAP = Decimal("2")
CAP = Decimal("48")
TASKS = {
    "P": "pydantic-ai-synthetic-tool-reasoning",
    "H": "hf-hub-xet-endpoint-propagation-v5",
    "F": "fromager-recursive-orphan-removal",
    "L": "loguru-invalid-format-feedback-v3",
    "D": "pdm-ignore-active-venv-resolution-v2",
    "G": "pgmpy-stable-skeleton-order",
}
PREPARED = {
    "P": ("pydantic-ai-registration-20260917-v1/source/prepared-source.json",
          "prepared-probe-dependencies-20260918-v1/dependencies-metadata/"
          "prepared-probe-dependencies.json"),
    "H": ("fixed-config-two-task-20260916-v1/sources/H/prepared-source.json",
          "hf-probe-dependencies-20260926-v1/prepared-probe-dependencies.json"),
    "F": ("fromager-registration-20260917-v1/source/prepared-source.json",
          "mini-xhigh-fixed-harness-panel-20260921-v1/dependencies/F/"
          "prepared-probe-dependencies.json"),
}
TREATMENT = """Before choosing a repair, select a concrete case where the public task
requires changed behavior and a nearby case where existing behavior must be preserved.
Derive their expected outcomes independently from the public requirement, not from
the proposed patch. Trace the source values and conditions that distinguish the cases,
including where those values are created or transformed. If this distinction remains
uncertain, use a small allowed public check or probe that could falsify the proposed
condition. Use the observed result to choose or revise the repair. Record the cases,
distinguishing condition, evidence and unresolved uncertainty briefly in the existing
public plan or action fields. A plausible explanation or a passing unrelated check
does not establish that the two cases are distinguished. Do not invent a boundary
unsupported by the task, add a separate ceremony, or repeat already decisive evidence.
Work within the existing tools, submission rules and total resource budget."""
ORDER = tuple((case, arm, n) for n in (1, 2) for i, case in enumerate(TASKS)
              for arm in (("A", "B") if (i + n) % 2 else ("B", "A")))


def require(ok, message):
    if not ok:
        raise ContractError(message)


@contextmanager
def arm_instructions(arm):
    require(arm in {"A", "B"}, "unknown arm")
    original = working_plan.instructions

    def selected(policy="brief-v1"):
        text = original(policy)
        return text + "\n\n" + TREATMENT if arm == "B" and policy == "brief-v1" else text

    # The existing planning contract hashes these actual instructions into model identity.
    # A keeps the ordinary function. The context is restored even after failures.
    if arm == "A":
        yield
    else:
        with patch.object(working_plan, "instructions", selected):
            yield


def request(case, state_root, *, mock=False):
    root = repository_root()
    prepared = PREPARED.get(case)
    return DevRunRequest(
        provider="mock" if mock else "openai", model="mock-dev" if mock else MODEL,
        task=root / ("tasks/smoke/csv-quoted-newline/public.yaml" if mock else
                     f"tasks/dev-train/{TASKS[case]}/public.yaml"),
        state_root=state_root, env_file=None if mock else root / ".env",
        max_cost_usd=None if mock else RUN_CAP, reasoning_effort="xhigh",
        context_policy="segmented-v1", planning_policy="brief-v1",
        enable_probes=True, repair_recheck=True,
        prepared_source=(Path("C:/pt/analyses/boundarypair-sources-20260928-v1")
                         / case / "prepared-source.json" if not mock else None),
        prepared_probe_dependencies=(Path("C:/pt/analyses") / prepared[1]
                                     if prepared and not mock else None),
    )


def save(root, name, value):
    ArtifactStore(root).write_text_immutable(root / name, canonical_json(value) + "\n")


def require_treatment_delivery(system_prompts, arm):
    """Audit the original all-turn treatment claim without changing any prompt."""
    require(arm in {"A", "B"}, "unknown arm")
    require(bool(system_prompts), "no delivered system prompts")
    for index, prompt in enumerate(system_prompts, start=1):
        require((TREATMENT in prompt) == (arm == "B"),
                f"boundary panel treatment delivery incompatible at turn {index}")


def _retired():
    raise ContractError(
        "boundary-pair-panel-v1 execution is retired: compact phase prompts do not "
        "deliver its planning treatment. Historical results remain closed; a new "
        "comparison requires a new design and exact authorization."
    )


def freeze(root):
    _retired()


def preflight(root, expected):
    _retired()


def run(root, expected):
    _retired()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["freeze", "preflight", "run"])
    cli.add_argument("--root", type=Path, required=True)
    cli.add_argument("--packet-hash")
    args = cli.parse_args()
    if args.action == "freeze":
        print(freeze(args.root))
    elif args.action == "preflight":
        preflight(args.root, args.packet_hash)
    else:
        run(args.root, args.packet_hash)
