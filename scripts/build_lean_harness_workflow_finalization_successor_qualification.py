from __future__ import annotations

from pathlib import Path

from patchloop.agent.workflow_finalization_successor_qualification import (
    materialize_workflow_finalization_successor_qualification,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    value = materialize_workflow_finalization_successor_qualification(root)
    print(value["content_hash"])


if __name__ == "__main__":
    main()
