"""Build, qualify, bind, or run the exact executable no-call preflight."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals.executable_no_call_preflight import (
    load_executable_no_call_preflight_contract,
    materialize_executable_no_call_preflight_contract,
    record_executable_exact_approval,
    record_executable_state_change,
    run_executable_no_call_preflight_once,
    run_executable_source_qualification,
    validate_executable_attempt_chain,
    validate_executable_exact_approval,
    validate_executable_source_qualification,
    validate_executable_state_change,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--validate-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate-source", action="store_true")
    mode.add_argument("--record-state", action="store_true")
    mode.add_argument("--validate-state", action="store_true")
    mode.add_argument("--record-exact-approval", action="store_true")
    mode.add_argument("--validate-exact-approval", action="store_true")
    mode.add_argument("--run-exact-attempt", action="store_true")
    mode.add_argument("--validate-terminal", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--contract-id")
    parser.add_argument("--source-qualification-hash")
    parser.add_argument("--state-change-evidence-id")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_executable_no_call_preflight_contract()
    elif args.validate_contract:
        contract = load_executable_no_call_preflight_contract()
        result = {
            "status": "OFFLINE_EXECUTABLE_CONTRACT_VALID",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = run_executable_source_qualification(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_executable_source_qualification()
    elif args.record_state:
        result = record_executable_state_change(recorded_at=datetime.now(UTC))
    elif args.validate_state:
        result = validate_executable_state_change()
    elif args.record_exact_approval:
        missing = [
            name
            for name, value in (
                ("--contract-id", args.contract_id),
                ("--source-qualification-hash", args.source_qualification_hash),
                ("--state-change-evidence-id", args.state_change_evidence_id),
            )
            if not value
        ]
        if missing:
            raise SystemExit("--record-exact-approval requires " + ", ".join(missing))
        result = record_executable_exact_approval(
            exact_contract_id=args.contract_id,
            exact_source_qualification_hash=args.source_qualification_hash,
            exact_state_change_evidence_id=args.state_change_evidence_id,
            recorded_at=datetime.now(UTC),
        )
    elif args.validate_exact_approval:
        result = validate_executable_exact_approval()
    elif args.run_exact_attempt:
        result = run_executable_no_call_preflight_once()
    else:
        result = validate_executable_attempt_chain()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
