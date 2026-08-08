"""Build or validate approved D-127 blocker-remediation/no-call evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d127_d126_successor_no_call_preflight as d127


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-receipt", action="store_true")
    modes.add_argument("--check-static", action="store_true")
    modes.add_argument("--run-external-preflight", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--validate-post-commit", action="store_true")
    args = parser.parse_args()

    if args.create_receipt:
        result = d127.create_d127_approval_receipt(repository=args.repository)
    elif args.check_static:
        result = d127.check_d127_static_prerequisites(repository=args.repository)
    elif args.run_external_preflight:
        result = d127.run_d127_external_remediation_and_preflight(
            repository=args.repository
        )
    elif args.validate_post_commit:
        result = d127.validate_d127_no_call_gate(
            repository=args.repository,
            mode="post-evidence-commit",
        )
    else:
        result = d127.validate_d127_no_call_gate(repository=args.repository)

    for key in (
        "status",
        "artifact_id",
        "gate_id",
        "semantic_body_hash",
        "file_bytes",
        "file_sha256",
        "source_commit",
        "environment_ready_for_execution_hash",
        "execution_hash_created",
        "execution_candidate_created",
    ):
        if key in result:
            value = result[key]
            print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    if "observed_blockers" in result:
        print("observed_blockers=" + ",".join(result["observed_blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
