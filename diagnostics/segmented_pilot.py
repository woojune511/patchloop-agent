"""Prepare/inspect a four-run context-policy pilot. No execution or credential API.

The old planning cycle is closed. This packet proposes a separate budget; preparing
it does not authorize calls. Actual execution must use the existing dev-head runner.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, segments, working_plan
from patchloop.dev.contracts import (
    DEV_READ_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    DevRunRequest,
    dev_tool_surface_hash,
)
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.cost import DEFAULT_OUTPUT_CEILING, pricing_for_model, usd_to_nanos
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import RecoveryError
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SCHEMA = "segmented-context-pilot-packet-v1"
MODEL = "gpt-5.4-mini-2026-03-17"
TASK = "tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2/public.yaml"
ORDER = ("A1", "B1", "B2", "A2")
ORDERS = {"a-first": ORDER, "b-first": ("B1", "A1", "A2", "B2")}
POLICIES = {"A": "append-v1", "B": "segmented-v1"}
RUN_CAP = Decimal("1.20")
CAP = RUN_CAP * len(ORDER)
PRICE = {
    "source": "https://developers.openai.com/api/docs/pricing",
    "model": MODEL,
    "service_tier": "default",
    "region": "global",
    "input_per_million_usd": "0.75",
    "cached_input_per_million_usd": "0.075",
    "output_per_million_usd": "4.5",
}


def require(ok, message):
    if not ok:
        raise RecoveryError(message)


def arm_request(arm):
    repo = repository_root().resolve()
    return DevRunRequest(
        provider="openai", task=repo / TASK, model=MODEL, reasoning_effort="medium",
        env_file=repo / ".env", max_cost_usd=RUN_CAP, repeat=1,
        enable_probes=True, repair_recheck=True, planning_policy="brief-v1",
        context_policy=POLICIES[arm],
    )


def freeze():
    """Read only committed inputs; never load .env, create a workspace or call Docker."""
    requests = {arm: arm_request(arm) for arm in POLICIES}
    task_dir, package = runner._resolve_task_file(requests["A"].task)
    runner._live_task_is_admitted(task_dir, package)
    runner._live_source_preflight(task_dir, package)
    pricing = pricing_for_model(MODEL)
    for field in ("input_per_million_usd", "cached_input_per_million_usd",
                  "output_per_million_usd"):
        require(getattr(pricing, field) == Decimal(PRICE[field]), "reviewed model price changed")
    configs = {a: r.model_dump(mode="json") for a, r in requests.items()}
    require({k: v for k, v in configs["A"].items() if k != "context_policy"} ==
            {k: v for k, v in configs["B"].items() if k != "context_policy"},
            "context policy must be the only arm configuration difference")
    public_task = package.public.model_dump(mode="json")
    # This is a serialization rehearsal, NOT a counted/live first-turn request.
    state = {"public_task": public_task}
    prompt = runner.DEV_SYSTEM_PROMPT + "\n\n" + working_plan.INSTRUCTIONS
    examples = {a: assemble_model_input(
        system_prompt=prompt, state=state, history=[], context_policy=POLICIES[a],
    ) for a in POLICIES}
    require(all(reconstruct_state(items, context_policy=POLICIES[a]) == state
                for a, items in examples.items()), "public task serialization diverged")
    require(examples["B"][0]["content"] ==
            examples["A"][0]["content"] + "\n" + segments.INSTRUCTIONS,
            "unexpected system prompt contrast")
    schemas = dev_tool_schemas(
        finish_enabled=True, check_ids=[c.id for c in package.public.visible_checks],
        allowed_tools=sorted(DEV_READ_TOOLS | DEV_SINGLE_ACTION_TOOLS),
        planning_policy="brief-v1",
    )
    return {
        "runtime_hash": runner._runtime_hash(),
        "preparer_hash": sha256_bytes(Path(__file__).read_bytes()),
        "installed_libraries": {n: version(n) for n in ("openai", "httpx")},
        "task_id": package.public.task_id, "task_version": package.public.task_version,
        "base_commit": package.public.repository.base_commit,
        "task_content_hash": package.task_content_hash,
        "public_spec_hash": package.public_spec_hash,
        "private_spec_hash": package.private_spec_hash,
        "public_task": public_task,
        "credential_file_path_hash": runner._credential_file_path_hash(requests["A"]),
        "evaluator_image": package.environment.evaluator_image,
        "evaluator_image_digest": package.environment.image_digest,
        "probe_image_digest": runner.PROBE_IMAGE_DIGEST,
        "probe_profile_hash": runner.probe_profile_hash(),
        "sandbox_identity_hash": runner._sandbox_identity_hash(requests["A"], package),
        "requests": configs,
        "model_hashes": {a: runner._model_hash(r, pricing) for a, r in requests.items()},
        "tool_surface_hash": dev_tool_surface_hash(planning_policy="brief-v1"),
        "registered_schema_catalog": schemas,
        "schema_catalog_scope": "all registered tools, not the initial action mask",
        "planning_contract": working_plan.contract(), "segment_contract": segments.contract(),
        "task_only_serialization_rehearsal": examples,
        "request_freeze_boundary": "The runner journals and counts each actual final request "
        "at dispatch. These examples contain no workspace, dynamic budget or observed source.",
        "output_ceiling": DEFAULT_OUTPUT_CEILING,
        "output_admission": "unchanged uncached reservation; may lower ceiling for remaining cap",
    }


def prepare(root, *, pricing_verified_on, order="a-first"):
    require(order in ORDERS, "unknown pilot order")
    sequence = ORDERS[order]
    root = root.resolve()
    require(not root.is_relative_to(repository_root().resolve()), "packet root must be external")
    require(not root.exists(), "packet preparation requires an unused directory")
    reviewed = date.fromisoformat(pricing_verified_on)
    require(reviewed <= utc_now().date(), "pricing review cannot be in the future")
    frozen = freeze()
    packet = {
        "schema": SCHEMA, "official": False, "created_at": utc_now().isoformat(),
        "prepared_at_commit": git_commit(), "root": str(root),
        "authorization": "NOT_AUTHORIZED; separate exact-packet approval required",
        "old_grants": "closed planning/compact grants are not reused",
        "pricing": {**PRICE, "verified_on": pricing_verified_on},
        "cap_nanos": usd_to_nanos(CAP), "run_cap_nanos": usd_to_nanos(RUN_CAP),
        "order_policy": order, "order": list(sequence), "frozen": frozen,
        "order_scope": "Predeclared balanced mirror order; two fresh samples per arm. "
        "No adaptive reordering, prior sample reuse or replacement of stopped slots.",
        "slots": [{"label": label, "arm": label[0], "request": {
            **frozen["requests"][label[0]], "state_root": str(root / "state" / label),
        }} for label in sequence],
        "hypothesis": "Bounded current working state with short native reasoning segments "
        "may avoid oversized replay and improve useful repair/recheck/submission behavior.",
        "inference_limit": "Two fresh runs per arm are exploratory. This compares the combined "
        "segmented policy (state replacement, detail selection, reasoning boundaries and handoff "
        "instructions), not any one mechanism. Historical B4 is not a control sample.",
        "starting_state": "Fresh base workspace per slot. No previous run, checkpoint, memory, "
        "plan, reasoning, candidate or extra reproduction is injected. Empty notes are allowed.",
        "metrics": {
            "outcome": ["task_acceptance PASS / planned and / started (both denominators)",
                        "submitted / started", "terminal", "safety_state separately"],
            "behavior": ["calls to first accepted edit", "zero-coverage inspections",
                         "public-evidence-supported repair and recheck", "submission"],
            "memory": ["plan created/revised/null/rejected", "major-result review opportunities",
                       "plan and validated notes present in the next actual request",
                       "empty notes and omitted evidence reported, not filled in"],
            "context": ["segment count/reasons", "actual request UTF-8 bytes",
                        "largest encrypted item bytes", "counted input tokens",
                        "native/public reference integrity and required-state preservation"],
            "cost": ["durable settled usage", "cached and uncached input/output tokens",
                     "SDK usage field presence, count relation/delta and billing_state",
                     "noncached-equivalent model-rate cost; not an invoice claim"],
        },
        "execution_protocol": [
            "Re-inspect exact packet hash and fresh official pricing before the approved group; "
            f"reserve all four invocation caps ($4.80) before {sequence[0]}.",
            "Use the existing runner with each exact slot request, sequentially. A single "
            "operator owns this group; do not invoke the closed planning-cycle executor.",
            "Before each slot verify runtime/task/config identity and existing local Docker "
            "images. Never start Docker or pull/build. No previous results in agent context.",
            "Reuse completed receipts, never replace a poor sample. A started pending slot "
            "is not a new run; only existing exact-match recovery is eligible.",
            "Count/transport/billing/cleanup or execution-state uncertainty, integrity failure "
            "or mismatch stops the whole group. No retry, fallback, replacement or extra sample.",
            "Preserve bounded provider_usage_failure diagnostics. Distinguish absent/null/zero "
            "usage from a proven count mismatch; an UNKNOWN bill is not zero-cost output.",
            "Settled normal task failures proceed to the next independent planned slot. "
            "Run visible checks and isolated evaluator only through the existing runner.",
            "Non-submissions have task_acceptance NOT_RUN, not evaluator FAIL. Hidden details "
            "never reach agents, plan prompts or causal diagnoses; use public trace only.",
            "Report an incomplete group and unstarted slots explicitly; do not claim superiority "
            "from ties, early stopping, small samples or lower cache-discounted cost alone.",
        ],
        "preparation_scope": {"provider": "NOT_RUN", "count": "NOT_RUN",
                              "credential": "NOT_READ", "docker": "NOT_CHECKED",
                              "task_acceptance": "NOT_RUN"},
    }
    # A unique directory is also a preparation claim. No existing packet is overwritten.
    root.mkdir(parents=True, exist_ok=False)
    ArtifactStore(root).write_text_immutable(root / "packet.json", canonical_json(packet) + "\n")
    return {"packet_hash": sha256_json(packet), "root": str(root), "authorized": False}


def inspect(root, *, packet_hash):
    root = root.resolve()
    packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
    require(sha256_json(packet) == packet_hash, "packet content hash mismatch")
    require(packet["schema"] == SCHEMA and packet["root"] == str(root), "packet identity mismatch")
    sequence = ORDERS.get(packet.get("order_policy"))
    require(sequence is not None and packet["order"] == list(sequence), "packet order mismatch")
    require(packet["slots"] == [{"label": label, "arm": label[0], "request": {
        **packet["frozen"]["requests"][label[0]], "state_root": str(root / "state" / label),
    }} for label in sequence], "packet slot/order contract mismatch")
    require(packet["run_cap_nanos"] == usd_to_nanos(RUN_CAP) and
            packet["cap_nanos"] == usd_to_nanos(CAP), "packet budget contract mismatch")
    require(packet["frozen"] == freeze(), "frozen runtime/task/config contract changed")
    return {"packet_hash": packet_hash, "integrity": "PASS", "authorized": False,
            "order": packet["order"], "cap_nanos": packet["cap_nanos"],
            "provider_calls": 0, "count_calls": 0, "credential_read": False,
            "docker_checked": False, "actual_input_fit": "NOT_MEASURED", "official": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--pricing-verified-on", required=True)
    prep.add_argument("--order", choices=tuple(ORDERS), default="a-first")
    check = commands.add_parser("inspect")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--packet-hash", required=True)
    args = parser.parse_args()
    result = (prepare(args.root, pricing_verified_on=args.pricing_verified_on, order=args.order)
              if args.command == "prepare" else inspect(args.root, packet_hash=args.packet_hash))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
