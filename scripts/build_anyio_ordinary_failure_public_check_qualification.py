"""Build the zero-call AnyIO ordinary-failure public-check qualification."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.anyio_ordinary_failure_public_check import (
    QUALIFICATION_PATH,
    build_qualification,
    qualification_bytes,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository).resolve()
    raw = qualification_bytes(build_qualification(root))
    if args.write:
        path = (root / QUALIFICATION_PATH).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    else:
        print(raw.decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
