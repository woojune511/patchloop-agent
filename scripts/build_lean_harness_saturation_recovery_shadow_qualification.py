from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.agent.saturation_recovery_shadow_qualification import (
    QUALIFICATION_PATH,
    materialize_saturation_recovery_shadow_public_qualification,
)
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the public no-call saturation/recovery shadow qualification."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--output", default=QUALIFICATION_PATH)
    args = parser.parse_args()

    repository = Path(args.repository).resolve()
    qualification = materialize_saturation_recovery_shadow_public_qualification(
        repository,
        args.output,
    )
    output = (repository / args.output).resolve()
    raw = output.read_bytes()
    print(
        json.dumps(
            {
                "qualification_id": qualification.qualification_id,
                "status": qualification.status,
                "path": output.relative_to(repository).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": qualification.content_hash,
                "provider_calls_authorized": qualification.provider_calls_authorized,
                "runner_activation_authorized": qualification.runner_activation_authorized,
                "added_model_cost_usd": qualification.added_model_cost_usd,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
