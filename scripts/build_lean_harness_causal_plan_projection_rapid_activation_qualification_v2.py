from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.agent.workflow_causal_plan_projection_rapid_activation_qualification_v2 import (
    QUALIFICATION_PATH,
    materialize_workflow_causal_plan_projection_rapid_activation_qualification_v2,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the second zero-call Lean V18 Rapid activation qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()

    value = materialize_workflow_causal_plan_projection_rapid_activation_qualification_v2(
        args.repository
    )
    print(
        json.dumps(
            {
                "qualification_path": QUALIFICATION_PATH.as_posix(),
                "content_hash": value["content_hash"],
                "runtime_build_hash": value["runtime_build_hash"],
                "provider_calls": value["evidence_boundary"]["provider_calls"],
                "docker_calls": value["evidence_boundary"]["docker_calls"],
                "evaluator_calls": value["evidence_boundary"]["evaluator_calls"],
                "added_model_cost_usd": value["evidence_boundary"]["added_model_cost_usd"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
