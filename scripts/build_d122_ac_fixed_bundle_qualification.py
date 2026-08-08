"""Build or validate the D-122 offline A/C source-qualification gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d122_ac_fixed_bundle_qualification as d122


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--validate-sealed-historical", action="store_true")
    args = parser.parse_args()
    if args.validate and args.validate_sealed_historical:
        parser.error("choose only one validation mode")
    result = (
        d122.validate_d122_source_gate(
            repository=args.repository,
            mode=(
                "sealed-historical"
                if args.validate_sealed_historical
                else "current-source"
            ),
        )
        if args.validate or args.validate_sealed_historical
        else d122.run_d122_offline_source_gate(repository=args.repository)
    )
    print(f"status={result['status']}")
    print(f"gate_id={result['gate_id']}")
    print(f"semantic_body_hash={result['semantic_body_hash']}")
    print(f"file_bytes={result['file_bytes']}")
    print(f"file_sha256={result['file_sha256']}")
    print(
        "execution_authorization_candidate_ready="
        f"{str(result['execution_authorization_candidate_ready']).lower()}"
    )
    print(f"provider_calls_made={result['provider_calls_made']}")
    print(f"evaluator_calls_made={result['evaluator_calls_made']}")
    print(f"docker_calls_made={result['docker_calls_made']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
