from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_bounded_request_context_successor_qualification import (
    materialize_bounded_request_context_successor_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V24 bounded request-context qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_bounded_request_context_successor_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
