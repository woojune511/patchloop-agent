"""Materialize, qualify, or bind the receipt-free user-attested preflight."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals.user_attested_no_call_preflight import (
    ATTESTATION_CLAIM,
    materialize_user_attested_no_call_preflight_contract,
    record_user_attested_state_change,
    record_user_exact_approval,
    run_user_attested_source_qualification,
    validate_user_attested_no_call_preflight_contract,
    validate_user_attested_source_qualification,
    validate_user_attested_state_change,
    validate_user_exact_approval,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--validate-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate-source", action="store_true")
    mode.add_argument("--record-user-attested-state", action="store_true")
    mode.add_argument("--validate-user-attested-state", action="store_true")
    mode.add_argument("--record-exact-approval", action="store_true")
    mode.add_argument("--validate-exact-approval", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--state-change-evidence-id")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = materialize_user_attested_no_call_preflight_contract()
    elif args.validate_contract:
        contract = validate_user_attested_no_call_preflight_contract()
        result = {
            "status": "OFFLINE_USER_ATTESTED_CONTRACT_VALID",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = run_user_attested_source_qualification(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_user_attested_source_qualification()
    elif args.record_user_attested_state:
        result = record_user_attested_state_change(
            claim=ATTESTATION_CLAIM,
            recorded_at=datetime.now(UTC),
        )
    elif args.validate_user_attested_state:
        result = validate_user_attested_state_change()
    elif args.record_exact_approval:
        if not args.state_change_evidence_id:
            parser_error = "--record-exact-approval requires --state-change-evidence-id"
            raise SystemExit(parser_error)
        result = record_user_exact_approval(
            exact_state_change_evidence_id=args.state_change_evidence_id,
            recorded_at=datetime.now(UTC),
        )
    else:
        result = validate_user_exact_approval()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
