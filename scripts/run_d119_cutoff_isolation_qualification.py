"""Execute or validate the D-119 cutoff/isolation qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.memory.d119_cutoff_isolation_qualification import (
    run_d119_cutoff_isolation_qualification,
    validate_d119_artifacts,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
        help="PatchLoop repository root",
    )
    parser.add_argument(
        "--docker-path",
        help="Exact Docker CLI path; only used with --execute",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Consume the repository-local one-use capability and run two containers",
    )
    mode.add_argument(
        "--validate-sealed",
        action="store_true",
        help="Validate checked-in evidence without raw objects or Docker",
    )
    mode.add_argument(
        "--validate-current-objects",
        action="store_true",
        help="Also re-hash the two ignored opaque source objects",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.execute:
        result = run_d119_cutoff_isolation_qualification(
            repository=args.repository,
            docker_path=args.docker_path,
        )
        mode = "execute-one-use"
    else:
        result = validate_d119_artifacts(
            repository=args.repository,
            current_objects=args.validate_current_objects,
        )
        mode = "validate-current-objects" if args.validate_current_objects else "validate-sealed"
    print(json.dumps({"mode": mode, **result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
