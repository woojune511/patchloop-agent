"""Build, validate, or render the offline D-129 terminal-successor gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d129_d128_terminal_successor_offline as d129


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--print-approval-template", action="store_true")
    args = parser.parse_args()
    if args.print_approval_template:
        print(d129.render_d129_successor_approval_template(repository=args.repository))
        return 0
    result = (
        d129.run_d129_offline_source_gate(repository=args.repository)
        if args.build
        else d129.validate_d129_offline_source_gate(repository=args.repository)
    )
    for key in (
        "status",
        "gate_id",
        "semantic_body_hash",
        "file_bytes",
        "file_sha256",
        "source_commit",
        "evidence_commit",
        "user_approval_required",
        "approval_receipt_created",
        "manual_readiness_attestation_recorded",
        "agent_docker_calls_made",
        "network_calls_made",
        "execution_hash_created",
        "execution_candidate_created",
    ):
        value = result[key]
        rendered = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
