"""Build the zero-call public exploration-gate qualification."""

from __future__ import annotations

import argparse

from patchloop.agent.workflow_exploration_gate_successor_qualification import (
    materialize_workflow_exploration_gate_successor_qualification,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    args = parser.parse_args()
    value = materialize_workflow_exploration_gate_successor_qualification(args.repository)
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
