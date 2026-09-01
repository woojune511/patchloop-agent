"""Prepare or consume the single approved read-only Docker preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_harbor_partial_preflight import (
    materialize_approval_and_attempt,
    run_preflight_once,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "observe"))
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    if args.phase == "prepare":
        approval, attempt = materialize_approval_and_attempt(repository)
        value = {
            "approval": approval.model_dump(mode="json"),
            "attempt": attempt.model_dump(mode="json"),
        }
    else:
        value = run_preflight_once(repository).model_dump(mode="json")
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
