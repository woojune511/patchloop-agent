from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.agent.workflow_exploration_gate_rapid_activation_qualification import (
    QUALIFICATION_PATH,
    materialize_workflow_exploration_gate_rapid_activation_qualification,
)
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V19 AnyIO-v5 Rapid activation qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()

    value = materialize_workflow_exploration_gate_rapid_activation_qualification(args.repository)
    raw = (args.repository.resolve() / QUALIFICATION_PATH).read_bytes()
    print(
        json.dumps(
            {
                "qualification_path": QUALIFICATION_PATH.as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": value["content_hash"],
                "provider_calls": value["evidence_boundary"]["provider_calls"],
                "docker_calls": value["evidence_boundary"]["docker_calls"],
                "evaluator_calls": value["evidence_boundary"]["evaluator_calls"],
                "added_model_cost_usd": value["evidence_boundary"]["added_model_cost_usd"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
