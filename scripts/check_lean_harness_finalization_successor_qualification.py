from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.agent.finalization_successor_qualification import (
    QUALIFICATION_PATH,
    build_finalization_successor_qualification,
    load_finalization_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the offline post-R4 finalization successor qualification."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    qualification = (
        build_finalization_successor_qualification(args.repository)
        if args.build_only
        else load_finalization_successor_qualification(args.repository)
    )
    raw = qualification_bytes(qualification)
    path = (Path(args.repository).resolve() / QUALIFICATION_PATH).resolve()
    print(
        json.dumps(
            {
                "qualification_id": qualification.qualification_id,
                "status": qualification.status,
                "path": path.relative_to(Path(args.repository).resolve()).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": qualification.content_hash,
                "scenario_count": len(qualification.scenarios),
                "provider_calls_authorized": qualification.provider_calls_authorized,
                "paid_execution_authorized": qualification.paid_execution_authorized,
                "added_model_cost_usd": qualification.added_model_cost_usd,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
