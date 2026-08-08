"""Materialize or read-only validate the D-118 external-source evidence set."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from patchloop.memory import d118_external_source_evidence as d118


def _print_result(result: dict[str, Any], *, mode: str) -> None:
    print(f"mode={mode}")
    print(f"receipt_id={result['receipt_id']}")
    print(f"preflight_id={result['preflight_id']}")
    print(f"evidence_pack_id={result['evidence_pack_id']}")
    print(f"evidence_pack_semantic_body_hash={result['evidence_pack_semantic_body_hash']}")
    print(f"evidence_pack_file_bytes={result['evidence_pack_file_bytes']}")
    print(f"evidence_pack_file_sha256={result['evidence_pack_file_sha256']}")
    print(f"gate_id={result['gate_id']}")
    print(f"gate_semantic_body_hash={result['gate_semantic_body_hash']}")
    print(f"gate_file_bytes={result['gate_file_bytes']}")
    print(f"gate_file_sha256={result['gate_file_sha256']}")
    print(f"aggregate_disposition={result['aggregate_disposition']}")
    print(f"validation_mode={result['validation_mode']}")
    print(f"current_external_objects_reverified={result['current_external_objects_reverified']}")
    print(f"record_read_count={result['record_read_count']}")
    print(
        "matcher_classifier_calibration_execution_count="
        f"{result['matcher_classifier_calibration_execution_count']}"
    )
    print(
        "retrieval_agent_provider_evaluator_call_count="
        f"{result['retrieval_agent_provider_evaluator_call_count']}"
    )
    print(f"trusted_cutoff_anchor_verified={result['trusted_cutoff_anchor_verified']}")
    print(
        "execution_authorization_candidate_ready="
        f"{result['execution_authorization_candidate_ready']}"
    )
    if "complete_exact_set_preexisted" in result:
        print(f"complete_exact_set_preexisted={result['complete_exact_set_preexisted']}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="PatchLoop repository root (default: the parent of scripts/)",
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help=(
            "explicitly materialize the approved four-artifact evidence set; "
            "without this flag the command only validates existing artifacts"
        ),
    )
    parser.add_argument(
        "--current-object",
        action="store_true",
        help=(
            "during read-only validation, also re-hash the ignored local snapshots; "
            "the default sealed-historical mode does not require raw snapshot bytes"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.materialize:
        result = d118.run_d118_external_source_evidence(repository=args.repository)
        mode = "materialize-approved-evidence"
    else:
        result = d118.validate_d118_artifacts(
            repository=args.repository,
            mode="current-object" if args.current_object else "sealed-historical",
        )
        mode = f"validate-existing-{result['validation_mode']}"
    _print_result(result, mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
