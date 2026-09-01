from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_candidate_registry import (
    materialize_qualified_fresh_candidate_registry,
)
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an offline source-qualified fresh public-candidate registry."
    )
    parser.add_argument("--source-qualification", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    value = materialize_qualified_fresh_candidate_registry(
        repository,
        source_qualification_path=args.source_qualification,
        output_path=args.output,
    )
    raw = (repository / args.output).read_bytes()
    print(
        json.dumps(
            {
                "path": args.output,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": value.content_hash,
                "status": value.status,
                "source_rows": value.projection.source_row_count,
                "queued_candidates": value.projection.queued_candidate_count,
                "rejected_rows": value.projection.rejected_row_count,
                "public_pool_sufficient_for_admission": (
                    value.projection.public_pool_sufficient_for_admission
                ),
                "source_snapshot_externally_qualified": (
                    value.authority.source_snapshot_externally_qualified
                ),
                "execution_authorized": value.authority.execution_authorized,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
