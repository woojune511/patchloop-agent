from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v2 import (
    CANDIDATE_PATH,
    materialize_rapid_public_development_v2_candidate,
)
from patchloop.util import sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-qualified exact Rapid V2 candidate."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--output", default=CANDIDATE_PATH.as_posix())
    args = parser.parse_args()

    candidate = materialize_rapid_public_development_v2_candidate(
        repository=args.repository,
        output_path=args.output,
    )
    output = (Path(args.repository).resolve() / args.output).resolve()
    raw = output.read_bytes()
    print(
        json.dumps(
            {
                "experiment_id": candidate["experiment_id"],
                "path": args.output,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": candidate["content_hash"],
                "execution_hash": candidate["execution_hash"],
                "schedule_hash": candidate["schedule_hash"],
                "scheduled_rows": len(candidate["schedule"]),
                "full_schedule_reserve_nanos": candidate["cost_control"][
                    "full_schedule_reserve_nanos"
                ],
                "hard_cap_nanos": candidate["cost_control"]["hard_cap_nanos"],
                "execution_authorized": candidate["execution_authorized"],
                "provider_calls_made": candidate["provider_calls_made"],
                "docker_calls_made": candidate["docker_calls_made"],
                "added_model_cost_usd": candidate["added_model_cost_usd"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
