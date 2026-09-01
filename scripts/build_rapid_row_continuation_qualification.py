from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.rapid_row_continuation_qualification import (
    materialize_rapid_row_continuation_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Rapid row-local isolation qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_rapid_row_continuation_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
