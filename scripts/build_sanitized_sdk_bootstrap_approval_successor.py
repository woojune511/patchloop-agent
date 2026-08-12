"""Materialize or validate the offline v11 approval successor."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from patchloop.evals import sanitized_sdk_bootstrap_approval_successor as successor


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize-contract", action="store_true")
    group.add_argument("--validate-contract", action="store_true")
    group.add_argument("--qualify-source", action="store_true")
    group.add_argument("--validate-source", action="store_true")
    group.add_argument("--show-approval-template", action="store_true")
    group.add_argument("--record-approval", action="store_true")
    group.add_argument("--validate-approval", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--approval-statement")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = successor.materialize_contract()
    elif args.validate_contract:
        contract = successor.load_contract()
        result = {
            "status": "OFFLINE_V11_APPROVAL_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "state_change_evidence_id": contract.predecessor.state_change_evidence_id,
            "approval_created": False,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = successor.qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = successor.validate_source_qualification()
    elif args.show_approval_template:
        root = successor.v10._root(None)
        contract = successor.load_contract(repository=root)
        qualification = successor._load_qualification(root)
        result = {
            "status": "V11_EXACT_APPROVAL_TEMPLATE_ONLY",
            "statement": successor.expected_approval_statement(contract, qualification),
            "execution_authorized": False,
        }
    elif args.record_approval:
        if args.approval_statement is None:
            raise SystemExit("--record-approval requires --approval-statement")
        result = successor.record_exact_approval(
            statement=args.approval_statement,
            recorded_at=datetime.now(UTC),
        )
    else:
        result = successor.validate_exact_approval()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
