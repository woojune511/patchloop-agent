from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_epoch_parity_rapid_activation_qualification import (
    materialize_workflow_semantic_progress_epoch_parity_rapid_activation_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V20 Rapid activation qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_workflow_semantic_progress_epoch_parity_rapid_activation_qualification(
        args.repository
    )
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
