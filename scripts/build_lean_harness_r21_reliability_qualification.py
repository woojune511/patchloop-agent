from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_r21_reliability_qualification import (
    materialize_r21_reliability_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V26 R21 reliability qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_r21_reliability_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
