"""Materialize AnyIO-v5 and its zero-call source qualification."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.anyio_ordinary_failure_task_successor import (
    QUALIFICATION_PATH,
    SUCCESSOR_PATH,
    materialize_qualification,
    materialize_successor,
)
from patchloop.util import sha256_bytes


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    materialize_successor(root)
    qualification = materialize_qualification(root)
    raw = (root / QUALIFICATION_PATH).read_bytes()
    print(
        json.dumps(
            {
                "successor_path": SUCCESSOR_PATH.as_posix(),
                "qualification_path": QUALIFICATION_PATH.as_posix(),
                "qualification_file_bytes": len(raw),
                "qualification_file_sha256": sha256_bytes(raw),
                "qualification_content_hash": qualification["content_hash"],
                "status": qualification["status"],
                "visible_check_ids": qualification["successor_contract"]["visible_check_ids"],
                "frozen_dataset_member": qualification["successor_contract"][
                    "frozen_dataset_member"
                ],
                "rapid_candidate_created": qualification["rapid_candidate_created"],
                "evidence_boundary": qualification["evidence_boundary"],
                "next_gate": qualification["next_gate"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
