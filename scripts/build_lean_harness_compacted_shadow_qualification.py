"""Materialize the public no-call compacted-shadow qualification."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.context_event_shadow_qualification import (
    QUALIFICATION_PATH,
    materialize_compacted_shadow_public_qualification,
)
from patchloop.util import sha256_bytes


def main() -> None:
    repository = Path.cwd().resolve()
    qualification = materialize_compacted_shadow_public_qualification(repository)
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
                "aggregate_counted_input_units_saved": (
                    qualification.aggregate_counted_input_units_saved
                ),
                "observed_phase_proxy_reduction_basis_points_floor": (
                    qualification.observed_phase_proxy_reduction_basis_points_floor
                ),
                "current_phase_policy_requalified": (
                    qualification.current_phase_policy_requalified
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
