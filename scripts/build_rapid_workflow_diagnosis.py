from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.rapid_workflow_diagnosis import (
    build_rapid_workflow_diagnosis,
    diagnosis_bytes,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--state", default=".patchloop/state.sqlite3")
    parser.add_argument("--public-task", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    value = build_rapid_workflow_diagnosis(
        bundle_path=root / args.bundle,
        state_path=root / args.state,
        public_task_path=root / args.public_task,
        repository_root=root,
    )
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(diagnosis_bytes(value))
    print(value["content_hash"])


if __name__ == "__main__":
    main()
