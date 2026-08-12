"""Materialize or validate the offline v10 state-binding successor."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals import sanitized_sdk_bootstrap_state_binding_successor as successor


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize-contract", action="store_true")
    group.add_argument("--validate-contract", action="store_true")
    group.add_argument("--qualify-source", action="store_true")
    group.add_argument("--validate-source", action="store_true")
    group.add_argument("--show-attestation-template", action="store_true")
    group.add_argument("--record-state", action="store_true")
    group.add_argument("--validate-state", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--attestation-statement")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = successor.materialize_contract()
    elif args.validate_contract:
        contract = successor.load_contract()
        result = {
            "status": "OFFLINE_V10_STATE_BINDING_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = successor.qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = successor.validate_source_qualification()
    elif args.show_attestation_template:
        contract = successor.load_contract()
        qualification = successor._load_qualification(successor._root(None))
        result = {
            "status": "V10_EXACT_ATTESTATION_TEMPLATE_ONLY",
            "statement": successor.expected_attestation_statement(contract, qualification),
            "execution_authorized": False,
        }
    elif args.record_state:
        if args.attestation_statement is None:
            raise SystemExit("--record-state requires --attestation-statement")
        result = successor.record_current_state(
            statement=args.attestation_statement,
            recorded_at=datetime.now(UTC),
        )
    else:
        result = successor.validate_current_state()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
