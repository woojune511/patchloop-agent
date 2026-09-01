from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_activation_qualification import (
    materialize_workflow_semantic_progress_activation_qualification,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    args = parser.parse_args()
    value = materialize_workflow_semantic_progress_activation_qualification(Path(args.repository))
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
