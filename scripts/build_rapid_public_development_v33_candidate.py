from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v27 import (
    CANDIDATE_PATH,
    materialize_rapid_public_development_v27_candidate,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the deterministic no-call AnyIO R24 candidate-v33."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    candidate = materialize_rapid_public_development_v27_candidate(repository=args.repository)
    print(
        json.dumps(
            {
                "candidate_path": CANDIDATE_PATH.as_posix(),
                "execution_hash": candidate["execution_hash"],
                "content_hash": candidate["content_hash"],
                "runtime_build_hash": candidate["runtime_build_hash"],
                "schedule_hash": candidate["schedule_hash"],
                "cost_control_hash": candidate["cost_control_hash"],
                "provider_calls_made": candidate["provider_calls_made"],
                "docker_calls_made": candidate["docker_calls_made"],
                "added_model_cost_usd": candidate["added_model_cost_usd"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
