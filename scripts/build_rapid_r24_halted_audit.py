from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.rapid_r24_halted_audit import (
    materialize_rapid_r24_halted_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public-only consumed R24 halted audit.")
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_rapid_r24_halted_audit(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
