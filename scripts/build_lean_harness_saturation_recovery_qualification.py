"""Materialize the public Lean Harness saturation/recovery qualification."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.saturation_recovery_qualification import (
    QUALIFICATION_PATH,
    materialize_saturation_recovery_public_qualification,
)
from patchloop.util import sha256_bytes


def main() -> None:
    repository = Path.cwd().resolve()
    qualification = materialize_saturation_recovery_public_qualification(repository)
    artifact = repository / QUALIFICATION_PATH
    raw = artifact.read_bytes()
    print(
        json.dumps(
            {
                "path": QUALIFICATION_PATH,
                "qualification_id": qualification.qualification_id,
                "status": qualification.status,
                "content_hash": qualification.content_hash,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "semantic_replay_saturation_threshold": (
                    qualification.candidate_semantic_replay_saturation_threshold
                ),
                "no_progress_strategy_threshold": (
                    qualification.candidate_no_progress_strategy_threshold
                ),
                "structured_edit_escalation_rejections": (
                    qualification.candidate_structured_edit_escalation_rejections
                ),
                "provider_calls_authorized": qualification.provider_calls_authorized,
                "added_model_cost_usd": qualification.added_model_cost_usd,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
