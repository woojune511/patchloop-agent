"""Build, validate, or render the offline D-128 successor source gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals import d128_d127_terminal_successor_offline as d128


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--validate", action="store_true")
    group.add_argument("--print-approval-template", action="store_true")
    args = parser.parse_args()
    if args.print_approval_template:
        print(d128.render_d128_successor_approval_template(repository=args.repository))
        return 0
    result = (
        d128.validate_d128_offline_source_gate(repository=args.repository)
        if args.validate
        else d128.run_d128_offline_source_gate(repository=args.repository)
    )
    for key in (
        "status",
        "gate_id",
        "semantic_body_hash",
        "file_bytes",
        "file_sha256",
        "user_approval_required",
        "approval_receipt_created",
        "docker_calls_made",
        "pricing_public_get_count",
        "provider_calls_made",
        "execution_hash_created",
        "execution_candidate_created",
    ):
        value = result[key]
        rendered = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
