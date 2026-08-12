from __future__ import annotations

import argparse
import json

from patchloop.evals.sanitized_sdk_bootstrap_approval_successor import v10
from patchloop.evals.sanitized_sdk_bootstrap_attempt_successor import (
    _load_qualification,
    _load_v11_approval,
    expected_run_statement,
    load_contract,
    materialize_contract,
    qualify_source,
    run_once,
    validate_attempt_chain,
    validate_source_qualification,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--materialize-contract", action="store_true")
    mode.add_argument("--validate-contract", action="store_true")
    mode.add_argument("--qualify-source", action="store_true")
    mode.add_argument("--validate-source", action="store_true")
    mode.add_argument("--show-run-template", action="store_true")
    mode.add_argument("--run-exact-attempt", action="store_true")
    mode.add_argument("--validate-terminal", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--run-statement")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result: object = materialize_contract()
    elif args.validate_contract:
        contract = load_contract()
        result = {
            "status": "OFFLINE_V12_ATTEMPT_LIFECYCLE_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "predecessor_approval_id": contract.predecessor.approval_id,
            "runtime_artifacts_created": False,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
            "next_gate": contract.next_gate,
        }
    elif args.qualify_source:
        result = qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_source_qualification()
    elif args.show_run_template:
        root = v10._root(None)
        contract = load_contract(repository=root)
        qualification = _load_qualification(root)
        _, _, _, approval, _, _ = _load_v11_approval(root)
        result = {
            "status": "V12_EXACT_RUN_STATEMENT_REQUIRED_ATTEMPT_NOT_STARTED",
            "statement": expected_run_statement(contract, qualification, approval),
            "attempt_started": False,
            "external_observations_made": 0,
            "external_mutations_made": 0,
        }
    elif args.run_exact_attempt:
        if args.run_statement is None:
            raise SystemExit("--run-statement is required")
        result = run_once(statement=args.run_statement)
    else:
        result = validate_attempt_chain()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
