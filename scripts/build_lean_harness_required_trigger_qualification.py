from __future__ import annotations

from pathlib import Path

from patchloop.agent.workflow_required_trigger_successor_qualification import (
    QUALIFICATION_PATH,
    materialize_workflow_required_trigger_successor_qualification,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    value = materialize_workflow_required_trigger_successor_qualification(root)
    print(QUALIFICATION_PATH.as_posix())
    print(value["content_hash"])


if __name__ == "__main__":
    main()
