from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.rapid_cli import dispatch_rapid_public_development_cli
from patchloop.evals.rapid_public_development_v20 import (
    rehearse_rapid_public_development_v20,
    run_rapid_public_development_v20,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rehearse or execute the exact AnyIO R17 candidate-v25."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=("rehearse", "execute"), default="rehearse")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--approve-live-cost", action="store_true")
    parser.add_argument("--approved-execution-hash")
    args = parser.parse_args()
    result = dispatch_rapid_public_development_cli(
        mode=args.mode,
        repository=args.repository,
        env_file=args.env_file,
        approve_live_cost=args.approve_live_cost,
        approved_execution_hash=args.approved_execution_hash,
        rehearse=rehearse_rapid_public_development_v20,
        execute=run_rapid_public_development_v20,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
