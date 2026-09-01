from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_causal_alternative_rapid_activation_qualification_v2 import (
    materialize_workflow_causal_alternative_rapid_activation_qualification_v2,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the second zero-call Lean V17 Rapid activation qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_workflow_causal_alternative_rapid_activation_qualification_v2(
        args.repository
    )
    print(value["content_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
