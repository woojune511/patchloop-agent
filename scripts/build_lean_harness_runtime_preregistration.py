from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.lean_runtime_preregistration import (
    PREREGISTRATION_PATH,
    materialize_lean_runtime_integration_preregistration,
)
from patchloop.util import sha256_bytes


def main() -> None:
    repository = Path(__file__).resolve().parents[1]
    preregistration = materialize_lean_runtime_integration_preregistration(repository)
    path = repository / PREREGISTRATION_PATH
    raw = path.read_bytes()
    print(
        json.dumps(
            {
                "path": PREREGISTRATION_PATH,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": preregistration.content_hash,
                "runtime_contract_hash": preregistration.runtime_contract_hash,
                "development_validation_hash": preregistration.development_validation_hash,
                "provider_calls_authorized": preregistration.provider_calls_authorized,
                "added_model_cost_usd": preregistration.added_model_cost_usd,
                "next_gate": preregistration.next_gate,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
