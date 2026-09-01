from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.fresh_source_availability import (
    OUTPUT_PATH,
    materialize_fresh_source_availability_checkpoint,
)
from patchloop.util import sha256_bytes


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    value = materialize_fresh_source_availability_checkpoint(repository)
    raw = (repository / OUTPUT_PATH).read_bytes()
    print(
        json.dumps(
            {
                "path": OUTPUT_PATH,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": value.content_hash,
                "status": value.status,
                "qualifying_snapshot_observed": value.decision.qualifying_snapshot_observed,
                "candidate_registry_materialized": (
                    value.authority.candidate_registry_materialized
                ),
                "execution_authorized": value.authority.execution_authorized,
                "added_model_cost_usd": value.authority.added_model_cost_usd,
                "next_gate": value.next_gate,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
