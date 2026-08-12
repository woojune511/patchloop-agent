from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals.sanitized_sdk_parent_integration import (
    load_contract,
    materialize_contract,
    materialize_state_evidence,
    qualify_source,
    record_exact_approval,
    run_once,
    validate_attempt_chain,
    validate_exact_approval,
    validate_source_qualification,
    validate_state_evidence,
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
    parser.add_argument("--state-evidence-id")
    parser.add_argument("--reconfirm-current-manual-start", action="store_true")
    parser.add_argument("--reconfirm-current-dotenv-placement", action="store_true")
    return parser.parse_args()


def _required(value: str | None, *, label: str) -> str:
    if value is None:
        raise SystemExit(f"{label} is required")
    return value


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_contract()
    elif args.validate_contract:
        contract = load_contract()
        result = {
            "status": "OFFLINE_SANITIZED_SDK_PARENT_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_source_qualification()
    elif args.record_state:
        result = materialize_state_evidence(
            current_manual_start_reported=args.reconfirm_current_manual_start,
            current_dotenv_placement_reported=args.reconfirm_current_dotenv_placement,
            recorded_at=datetime.now(UTC),
        )
    elif args.validate_state:
        result = validate_state_evidence()
    elif args.record_exact_approval:
        result = record_exact_approval(
            exact_contract_id=_required(args.contract_id, label="--contract-id"),
            exact_source_qualification_hash=_required(
                args.source_qualification_hash,
                label="--source-qualification-hash",
            ),
            exact_state_evidence_id=_required(
                args.state_evidence_id,
                label="--state-evidence-id",
            ),
            reconfirm_current_manual_start=args.reconfirm_current_manual_start,
            reconfirm_current_dotenv_placement=(args.reconfirm_current_dotenv_placement),
            recorded_at=datetime.now(UTC),
        )
    elif args.validate_exact_approval:
        result = validate_exact_approval()
    elif args.run_exact_attempt:
        result = run_once()
    else:
        result = validate_attempt_chain()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
