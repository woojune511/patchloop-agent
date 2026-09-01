from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.rapid_semantic_progress_diagnosis import (
    build_rapid_semantic_progress_diagnosis,
    diagnosis_bytes,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=".patchloop/state.sqlite3")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    value = build_rapid_semantic_progress_diagnosis(
        repository_root=root,
        state_path=args.state,
    )
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(diagnosis_bytes(value))
    print(value["content_hash"])


if __name__ == "__main__":
    main()
