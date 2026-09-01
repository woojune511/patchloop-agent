from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.util import ensure_within, sha256_bytes, sha256_json

CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v5.json"
)
EXPECTED_FILE_SHA256 = (
    "sha256:e37686ddd6c8315a1882f417d52a6395b1824e3a6711c57a45f43d64f9ff54c8"
)
EXPECTED_EXECUTION_HASH = (
    "sha256:7174d4b462aceca5fbc82a7248f1bca90b0453bbab6be379f099c01ec4415fe2"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Byte-validate the consumed immutable Rapid candidate-v5."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--output", default=CANDIDATE_PATH.as_posix())
    args = parser.parse_args()

    root = Path(args.repository).resolve()
    output = ensure_within(root, args.output)
    raw = output.read_bytes()
    candidate = json.loads(raw.decode("utf-8"))
    content_body = {
        key: value for key, value in candidate.items() if key != "content_hash"
    }
    if (
        sha256_bytes(raw) != EXPECTED_FILE_SHA256
        or candidate.get("execution_hash") != EXPECTED_EXECUTION_HASH
        or candidate.get("content_hash") != sha256_json(content_body)
    ):
        raise SystemExit("consumed candidate-v5 bytes differ")
    print(
        json.dumps(
            {
                "experiment_id": candidate["experiment_id"],
                "candidate_revision": candidate["candidate_revision"],
                "path": args.output,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": candidate["content_hash"],
                "execution_hash": candidate["execution_hash"],
                "runtime_build_hash": candidate["runtime_build_hash"],
                "config_file_sha256": candidate["config_file_sha256"],
                "schedule_hash": candidate["schedule_hash"],
                "scheduled_rows": len(candidate["schedule"]),
                "full_schedule_reserve_nanos": candidate["cost_control"][
                    "full_schedule_reserve_nanos"
                ],
                "hard_cap_nanos": candidate["cost_control"]["hard_cap_nanos"],
                "source_qualified": candidate["source_qualified"],
                "execution_authorized": candidate["execution_authorized"],
                "rehearsal_required": candidate["rehearsal_required"],
                "provider_calls_made": candidate["provider_calls_made"],
                "docker_calls_made": candidate["docker_calls_made"],
                "added_model_cost_usd": candidate["added_model_cost_usd"],
                "predecessor_candidate_file_sha256": candidate[
                    "predecessor_candidate"
                ]["file_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
