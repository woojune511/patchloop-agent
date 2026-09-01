from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.evals.rapid_r12_terminal_diagnosis import (
    build_rapid_r12_terminal_diagnosis,
    diagnosis_bytes,
    prepare_read_only_snapshot,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-state", default=".patchloop/state.sqlite3")
    parser.add_argument(
        "--snapshot",
        default=".tmp/r12-terminal-diagnosis/state.sqlite3",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    snapshot = prepare_read_only_snapshot(
        repository_root=root,
        source_state_path=args.source_state,
        snapshot_path=args.snapshot,
    )
    value = build_rapid_r12_terminal_diagnosis(
        repository_root=root,
        source_state_path=args.source_state,
        state_snapshot_path=snapshot,
    )
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(diagnosis_bytes(value))
    print(value["content_hash"])


if __name__ == "__main__":
    main()
