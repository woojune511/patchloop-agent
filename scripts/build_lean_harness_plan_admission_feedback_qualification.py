from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_plan_admission_feedback_successor_qualification import (
    materialize_workflow_plan_admission_feedback_successor_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V22 bounded plan-feedback qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_workflow_plan_admission_feedback_successor_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
