from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from patchloop.environment import exact_openai_api_key_environment
from patchloop.evals.rapid_public_development_v5 import (
    rehearse_rapid_public_development_v5,
    run_rapid_public_development_v5,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rehearse or execute the exact AnyIO Rapid candidate-v7."
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--mode", choices=("rehearse", "live"), required=True)
    parser.add_argument("--approve-live-cost", action="store_true")
    parser.add_argument("--approved-execution-hash")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args(argv)

    if args.mode == "rehearse":
        if args.approve_live_cost or args.approved_execution_hash is not None:
            parser.error("rehearsal does not accept live approval arguments")
        result = rehearse_rapid_public_development_v5(repository=args.repository)
    else:
        with exact_openai_api_key_environment(args.env_file):
            result = run_rapid_public_development_v5(
                repository=args.repository,
                approve_live_cost=args.approve_live_cost,
                approved_execution_hash=args.approved_execution_hash,
            )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
