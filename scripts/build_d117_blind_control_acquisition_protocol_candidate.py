"""Build or read-only validate the D-117 blind-control protocol candidate."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from patchloop.memory import d117_blind_control_acquisition_protocol as d117
from patchloop.util import sha256_bytes


def _artifact_summary(
    payload: dict[str, Any],
    path: Path,
    *,
    id_field: str,
) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "id": payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _validate_evidence(repository: Path) -> dict[str, Any]:
    repo = repository.resolve(strict=True)
    receipt = d117.validate_d117_receipt(repository=repo)
    preflight = d117.validate_d117_preflight(repository=repo)
    candidate = d117.validate_d117_candidate(repository=repo)
    gate = d117.validate_d117_source_gate(repository=repo)

    receipt_summary = _artifact_summary(
        receipt,
        repo / d117.DEFAULT_RECEIPT_PATH,
        id_field="receipt_id",
    )
    preflight_summary = _artifact_summary(
        preflight,
        repo / d117.DEFAULT_PREFLIGHT_PATH,
        id_field="preflight_id",
    )
    candidate_summary = _artifact_summary(
        candidate,
        repo / d117.DEFAULT_CANDIDATE_PATH,
        id_field="candidate_id",
    )
    gate_summary = _artifact_summary(
        gate,
        repo / d117.DEFAULT_SOURCE_GATE_PATH,
        id_field="gate_id",
    )
    authority = candidate["semantic_body"]["authority"]

    return {
        "receipt": receipt_summary,
        "preflight": preflight_summary,
        "candidate": candidate_summary,
        "gate": gate_summary,
        "candidate_status": candidate["semantic_body"]["candidate_status"],
        "authority": authority,
        "matcher_classifier_calibration_execution_count": (
            authority["matcher_evaluator_execution_count"]
            + authority["classifier_execution_count"]
            + authority["calibration_execution_count"]
        ),
    }


def _print_result(result: dict[str, Any], *, mode: str) -> None:
    print(f"mode={mode}")
    for name in ("receipt", "preflight", "candidate", "gate"):
        summary = result[name]
        print(f"{name}_id={summary['id']}")
        print(f"{name}_semantic_body_hash={summary['semantic_body_hash']}")
        print(f"{name}_file_bytes={summary['file_bytes']}")
        print(f"{name}_file_sha256={summary['file_sha256']}")

    authority = result["authority"]
    print(f"candidate_status={result['candidate_status']}")
    print(
        "blind_control_acquisition_protocol_candidate_ready="
        f"{authority['blind_control_acquisition_protocol_candidate_ready']}"
    )
    for field in (
        "source_pool_public_issue_read_count",
        "held_out_public_issue_or_result_read_count",
        "pool_manifest_count",
        "pool_member_count",
        "role_assignment_count",
        "isolation_session_count",
        "blind_packet_count",
        "selector_result_count",
        "adjudication_result_count",
        "independent_control_count",
        "independent_positive_count",
        "matcher_evaluator_execution_count",
        "classifier_execution_count",
        "calibration_execution_count",
        "runtime_memory_injection_count",
        "agent_runs",
        "provider_calls_made",
        "evaluator_calls_made",
        "network_capable_call_paths_invoked",
    ):
        print(f"{field}={authority[field]}")
    print(
        "matcher_classifier_calibration_execution_count="
        f"{result['matcher_classifier_calibration_execution_count']}"
    )
    for field in (
        "source_pool_discovery_authorized",
        "source_pool_acquisition_authorized",
        "source_pool_identified",
        "source_pool_acquired",
        "source_pool_frozen",
        "trusted_cutoff_anchor_verified",
        "pre_d116_membership_verified",
        "score_policy_mutation_authorized",
        "retrieval_ready",
        "core_campaign_unlocked",
    ):
        print(f"{field}={authority[field]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--validate-evidence",
        action="store_true",
        help="validate the existing four-artifact set without writing files",
    )
    args = parser.parse_args()

    if args.validate_evidence:
        result = _validate_evidence(args.repository)
        mode = "validate-evidence-read-only"
    else:
        d117.run_d117_protocol_candidate(repository=args.repository)
        result = _validate_evidence(args.repository)
        mode = "materialize-protocol-candidate"
    _print_result(result, mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
