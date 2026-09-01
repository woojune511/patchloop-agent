from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.util import sha256_bytes

CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-hard-panel-20260822-r3-candidate-v4.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read the audit-only Rapid candidate-v4; do not activate it."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--input", default=CANDIDATE_PATH.as_posix())
    args = parser.parse_args()

    selected = (Path(args.repository).resolve() / args.input).resolve(strict=True)
    raw = selected.read_bytes()
    candidate = json.loads(raw)
    print(
        json.dumps(
            {
                "historical_audit_only": True,
                "rehearsal_reproducible": False,
                "path": args.input,
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": candidate["content_hash"],
                "execution_hash": candidate["execution_hash"],
                "provider_calls_made": candidate["provider_calls_made"],
                "docker_calls_made": candidate["docker_calls_made"],
                "added_model_cost_usd": candidate["added_model_cost_usd"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
