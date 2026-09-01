from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v2 import (
    QUALIFICATION_PATH,
    materialize_rapid_v2_source_qualification,
)
from patchloop.util import sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the no-call Rapid V2 source qualification."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--output", default=QUALIFICATION_PATH.as_posix())
    args = parser.parse_args()

    qualification = materialize_rapid_v2_source_qualification(
        repository=args.repository,
        output_path=args.output,
    )
    output = (Path(args.repository).resolve() / args.output).resolve()
    raw = output.read_bytes()
    print(
        json.dumps(
            {
                "qualification_id": qualification.qualification_id,
                "status": qualification.status,
                "path": args.output,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": qualification.content_hash,
                "scheduled_rows": qualification.scheduled_rows,
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
