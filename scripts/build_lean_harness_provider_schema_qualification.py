from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.provider_schema_qualification import (
    build_qualification,
    materialize_qualification,
    qualification_bytes,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or audit Lean V27 offline schema qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument(
        "--check-only", action="store_true", help="Compare two builds without writing."
    )
    args = parser.parse_args()
    first = build_qualification(args.repository)
    second = build_qualification(args.repository)
    if qualification_bytes(first) != qualification_bytes(second):
        raise SystemExit("qualification builds are not byte-identical")
    if not args.check_only:
        materialize_qualification(args.repository)
    print(first["content_hash"])
    print(f"bytes={len(qualification_bytes(first))} external_calls=0 candidate_created=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
