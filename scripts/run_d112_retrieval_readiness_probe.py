"""Preflight, execute once, or validate the exact D-112 scoring diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory import d112_retrieval_readiness_probe as d112


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--verify-current-implementation",
        action="store_true",
        help="With --validate, compare module, script, and test bytes to the execution binding.",
    )
    parser.add_argument(
        "--skip-current-input-verification",
        action="store_true",
        help=(
            "With --validate, validate portable evidence without re-reading current immutable "
            "inputs."
        ),
    )
    args = parser.parse_args()

    if args.preflight:
        if args.verify_current_implementation or args.skip_current_input_verification:
            parser.error("validation flags are only valid with --validate")
        result = d112.preflight_d112_execution(repository=args.repository)
    elif args.execute:
        if args.verify_current_implementation or args.skip_current_input_verification:
            parser.error("validation flags are only valid with --validate")
        result = d112.execute_d112_scoring_diagnostic(repository=args.repository)
    else:
        result = d112.validate_d112_completion_gate(
            repository=args.repository,
            verify_current_implementation=args.verify_current_implementation,
            verify_current_inputs=not args.skip_current_input_verification,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
