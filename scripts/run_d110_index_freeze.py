"""Prepare, preflight, execute, or validate the exact D-110 index freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d110_index_freeze_execution as d110


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--verify-live-runtime",
        action="store_true",
        help="Also compare the current runtime index and marker during --validate.",
    )
    parser.add_argument(
        "--verify-current-implementation",
        action="store_true",
        help="Also compare the current code and test files with the executed snapshot.",
    )
    args = parser.parse_args()

    if args.prepare_approval:
        result = d110.materialize_d110_approval_receipt(repository=args.repository)
    elif args.preflight:
        result = d110.preflight_d110_execution(repository=args.repository)
    elif args.execute:
        if args.verify_live_runtime or args.verify_current_implementation:
            parser.error("validation flags are only valid with --validate")
        result = d110.execute_d110_index_freeze(repository=args.repository)
    else:
        result = d110.validate_d110_completion_gate(
            repository=args.repository,
            verify_live_runtime=args.verify_live_runtime,
            verify_current_implementation=args.verify_current_implementation,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
