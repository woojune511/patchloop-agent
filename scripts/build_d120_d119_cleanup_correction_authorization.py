"""Build or validate the append-only D-120 cleanup correction candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory.d120_d119_cleanup_correction_authorization import (
    run_d120_cleanup_correction_candidate,
    validate_d120_source_gate,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing artifacts instead of materializing the candidate",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.validate:
        result = validate_d120_source_gate(repository=args.repository)
        mode = "validate"
    else:
        result = run_d120_cleanup_correction_candidate(repository=args.repository)
        mode = "build-or-validate"
    print(json.dumps({"mode": mode, **result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
