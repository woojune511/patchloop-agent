"""Materialize the public-only Lean Harness context-dedup qualification."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.context_dedup_qualification import (
    QUALIFICATION_PATH,
    materialize_context_dedup_public_qualification,
)
from patchloop.util import sha256_bytes


def main() -> None:
    repository = Path.cwd().resolve()
    qualification = materialize_context_dedup_public_qualification(repository)
    artifact_path = repository / QUALIFICATION_PATH
    artifact_bytes = artifact_path.read_bytes()
    print(
        json.dumps(
            {
                "path": QUALIFICATION_PATH,
                "qualification_id": qualification.qualification_id,
                "status": qualification.status,
                "content_hash": qualification.content_hash,
                "file_bytes": len(artifact_bytes),
                "file_sha256": sha256_bytes(artifact_bytes),
                "observations": len(qualification.observations),
                "aggregate_context_bytes_saved": (qualification.aggregate_context_bytes_saved),
                "aggregate_proxy_input_units_saved": (
                    qualification.aggregate_proxy_input_units_saved
                ),
                "provider_calls_authorized": (qualification.provider_calls_authorized),
                "added_model_cost_usd": qualification.added_model_cost_usd,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
