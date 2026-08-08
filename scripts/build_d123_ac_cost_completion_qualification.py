"""Build or validate the offline D-123 A/C cost/completion source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d123_ac_cost_completion_qualification as d123


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
        d123.validate_d123_source_gate(
            repository=args.repository,
            mode=(
                "sealed-historical"
                if args.validate_sealed_historical
                else "current-source"
            ),
        )
        if args.validate or args.validate_sealed_historical
        else d123.run_d123_offline_source_gate(repository=args.repository)
    )
    for key in (
        "status",
        "gate_id",
        "semantic_body_hash",
        "file_bytes",
        "file_sha256",
        "execution_authorization_candidate_ready",
        "provider_calls_made",
        "evaluator_calls_made",
        "docker_calls_made",
    ):
        value = result[key]
        rendered = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
