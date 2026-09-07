"""Four independent frozen fresh-state responses; no tools, retries, chaining or resume.

Validation is provider-free. Collection needs a separate exact four-response approval;
the preparation packet stays immutable and is never promoted to execution authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_design as design
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.util import canonical_json, sha256_bytes, sha256_json

# This is an enforced admission ceiling, never a byte/token estimate for either arm.
# Snapshot max input: https://developers.openai.com/api/docs/models/gpt-5.4-mini
INPUT_TOKEN_LIMIT = 272_000
PROTOCOL = shared.CollectionProtocol(
    "fresh-state-sampler-v1",
    {"A": "medium", "B": "medium"},
    (("A", 1), ("B", 1), ("B", 2), ("A", 2)),
    INPUT_TOKEN_LIMIT,
)


def implementation_hashes() -> dict[str, str]:
    return {
        f"diagnostics/{path.name}": sha256_bytes(path.read_bytes())
        for path in sorted((Path(shared.__file__), Path(design.__file__), Path(__file__)))
    }


def sampler_hash() -> str:
    # Bind the shared engine and preparer too; runtime dependencies have a separate hash.
    return sha256_json(implementation_hashes())


@dataclass(frozen=True)
class FreshPlan(shared.FrozenPlan):
    source_packet_path: Path


def load_plan(
    packet_path: Path,
    source_packet_path: Path,
    source_root: Path,
    expected_hash: str,
) -> FreshPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "fresh packet hash mismatch")
    source = shared.load_plan(source_packet_path, source_root, design.SOURCE_PACKET_HASH)
    verified = design.validate_design(source, packet_path)
    shared.require(
        verified["packet_hash"] == expected_hash, "fresh packet changed during validation"
    )
    packet = json.loads(raw)
    shared.require(
        packet["sampling_order_proposal"] == [list(p) for p in PROTOCOL.sampling_order],
        "four-response schedule mismatch",
    )
    source_cell = next(c for c in source.cells if c.case_id == "C3" and c.arm == "A")
    store = ArtifactStore(packet_path.parent)
    requests = {
        arm: store.read_bytes(Artifact.model_validate(ref)).decode("utf-8")
        for arm, ref in packet["request_artifacts"].items()
    }
    cells = tuple(
        shared.Cell(
            "C3",
            arm,
            requests[arm],
            packet["request_metrics"][arm]["canonical_hash"],
            packet["historical_control_input_count"] if arm == "A" else None,
            packet["source_turn_id"],
            source_cell.max_parallel_reads,
            source_cell.read_paths,
            sample_number=number,
        )
        for arm, number in PROTOCOL.sampling_order
    )
    return FreshPlan(
        packet_path.resolve(),
        expected_hash,
        packet,
        cells,
        source_root.resolve(),
        {**packet["reviewer_files"], **{f"source/{k}": v for k, v in source.design_hashes.items()}},
        source_packet_path.resolve(),
    )


def collect(
    plan: FreshPlan,
    approval: shared.Approval,
    *,
    adapter_factory: Callable[[ModelConfig], OpenAIResponsesAdapter] | None = None,
    clock: Callable[[], float] = monotonic,
    checkpoint: Callable[[str], None] = lambda _: None,
) -> dict:
    shared._validate_collection_approval(
        plan,
        approval,
        sampler_hash(),
        protected_roots=(plan.source_packet_path.parent,),
    )
    refreshed = load_plan(
        plan.packet_path,
        plan.source_packet_path,
        plan.source_root,
        approval.packet_hash,
    )
    shared.require(
        refreshed.design_hashes == plan.design_hashes, "review design changed after validation"
    )
    return shared._collect_validated(
        refreshed,
        approval,
        protocol=PROTOCOL,
        adapter_factory=adapter_factory,
        clock=clock,
        checkpoint=checkpoint,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="read a receipt; never resume")
    inspect.add_argument("--result-root", type=Path, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--packet", type=Path, required=True)
        command.add_argument("--packet-hash", required=True)
        command.add_argument("--source-packet", type=Path, required=True)
        command.add_argument("--source-state-root", type=Path, required=True)
        if name == "collect":
            command.add_argument(
                "--approve-four-responses-zero-tools", action="store_true", required=True
            )
            command.add_argument("--sampler-hash", required=True)
            command.add_argument("--result-root", type=Path, required=True)
            command.add_argument("--credential-file", type=Path, required=True)
            command.add_argument("--max-cost-usd", type=Decimal, required=True)
            command.add_argument("--pricing-hash", required=True)
            command.add_argument("--pricing-verified-on", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = shared.inspect_result(args.result_root)
        else:
            plan = load_plan(
                args.packet, args.source_packet, args.source_state_root, args.packet_hash
            )
            if args.command == "validate":
                result = {
                    **shared.BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "packet_hash": plan.packet_hash,
                    "source_packet_hash": plan.packet["source_packet_hash"],
                    "sampler_hash": sampler_hash(),
                    "implementation_hashes": implementation_hashes(),
                    "runtime_hash": plan.packet["runtime_hash"],
                    "design_hashes": plan.design_hashes,
                    "sampling_order": PROTOCOL.sampling_order,
                    "request_metrics": plan.packet["request_metrics"],
                    "fresh_token_counts": {"A": None, "B": None},
                    "input_token_limit": INPUT_TOKEN_LIMIT,
                    "future_cell_reserve_nanos": shared.full_reservation(INPUT_TOKEN_LIMIT),
                    "reservation_basis": "enforced input limit plus full output; not measured cost",
                    "pricing": shared.price_identity(),
                    "pricing_hash": sha256_json(shared.price_identity()),
                    "pricing_status": "REGISTERED_RATES_REQUIRE_FRESH_LIVE_REVIEW",
                    "provider_calls": 0,
                    "input_count_calls": 0,
                }
            else:
                result = collect(
                    plan,
                    shared.Approval(
                        args.packet_hash,
                        args.sampler_hash,
                        args.result_root,
                        args.credential_file,
                        args.max_cost_usd,
                        args.pricing_hash,
                        args.pricing_verified_on,
                    ),
                )
        print(canonical_json(result))
        return 0 if result.get("terminal") in {None, "SAMPLES_COLLECTED"} else 1
    except Exception as exc:
        print(
            canonical_json(
                {
                    **shared.BOUNDARIES,
                    "status": "PREFLIGHT_REJECTED",
                    "error_type": type(exc).__name__,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
