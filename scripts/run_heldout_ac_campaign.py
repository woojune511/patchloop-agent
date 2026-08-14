from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_dispatcher import (
    prepare_heldout_ac_approved_plan,
    run_heldout_ac_campaign,
)


def _candidate_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("held-out candidate file is invalid") from exc
    if not isinstance(payload, dict):
        raise ContractError("held-out candidate file must contain an object")
    candidate = payload.get("candidate", payload)
    if not isinstance(candidate, dict):
        raise ContractError("held-out candidate file has no candidate object")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one exact approved held-out A/C campaign")
    parser.add_argument("--candidate-file", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--approve-live-cost", action="store_true")
    parser.add_argument("--approved-execution-hash", required=True)
    args = parser.parse_args()

    candidate = _candidate_payload(args.candidate_file)
    prepare_heldout_ac_approved_plan(
        candidate=candidate,
        approve_live_cost=args.approve_live_cost,
        approved_execution_hash=args.approved_execution_hash,
    )
    result = run_heldout_ac_campaign(
        execution_hash=args.approved_execution_hash,
        env_file=args.env_file,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
