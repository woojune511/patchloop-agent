from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_lifecycle_binding_qualification import (
    materialize_lifecycle_binding_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V28 lifecycle-binding qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_lifecycle_binding_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
