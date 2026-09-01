"""Materialize the execution-closed PDM task-v6 qualification candidate."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.public_behavior_check_qualification_v7 import (
    CANDIDATE_PATH,
    expected_approval_message,
    materialize_candidate,
)
from patchloop.util import sha256_bytes


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate = materialize_candidate(root)
    raw = (root / CANDIDATE_PATH).read_bytes()
    print(
        json.dumps(
            {
                "candidate_path": CANDIDATE_PATH.as_posix(),
                "candidate_file_bytes": len(raw),
                "candidate_file_sha256": sha256_bytes(raw),
                "content_hash": candidate["content_hash"],
                "execution_hash": candidate["execution_hash"],
                "schedule_hash": candidate["schedule_hash"],
                "scheduled_rows": len(candidate["schedule"]),
                "docker_image_inspect_calls_if_approved": 1,
                "docker_container_runs_if_approved": 2,
                "source_qualified": candidate["source_qualified"],
                "execution_authorized": candidate["execution_authorized"],
                "candidate_build_contract": candidate["candidate_build_contract"],
                "approval_message": expected_approval_message(candidate),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
