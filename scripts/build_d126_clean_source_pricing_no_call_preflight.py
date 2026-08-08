"""Create or validate D-126 approval and no-call preflight evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d126_clean_source_pricing_no_call_preflight as d126


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-receipt", action="store_true")
    modes.add_argument("--run-preflight", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--validate-post-commit", action="store_true")
    args = parser.parse_args()

    if args.create_receipt:
        result = d126.create_d126_approval_receipt(repository=args.repository)
    elif args.run_preflight:
        result = d126.run_d126_preflight(repository=args.repository)
    elif args.validate_post_commit:
        result = d126.validate_d126_preflight_gate(
            repository=args.repository,
            mode="post-evidence-commit",
        )
    else:
        result = d126.validate_d126_preflight_gate(repository=args.repository)

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
        "provider_calls_made",
        "docker_workload_calls_made",
    ):
        if key not in result:
            continue
        value = result[key]
        rendered = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}={rendered}")
    if "observed_blockers" in result:
        print("observed_blockers=" + ",".join(result["observed_blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
