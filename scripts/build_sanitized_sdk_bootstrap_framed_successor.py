from __future__ import annotations

import argparse
import json

from patchloop.evals.sanitized_sdk_bootstrap_framed_successor import (
    _load_approval,
    _load_qualification,
    _load_state,
    expected_approval_statement,
    expected_run_statement,
    expected_state_statement,
    load_contract,
    materialize_contract,
    qualify_source,
    record_approval,
    record_state,
    run_once,
    v10,
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
    mode.add_argument("--show-state-template", action="store_true")
    mode.add_argument("--record-state", action="store_true")
    mode.add_argument("--show-approval-template", action="store_true")
    mode.add_argument("--record-approval", action="store_true")
    mode.add_argument("--show-run-template", action="store_true")
    mode.add_argument("--run-exact-attempt", action="store_true")
    mode.add_argument("--validate-terminal", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    parser.add_argument("--statement")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result: object = materialize_contract()
    elif args.validate_contract:
        contract = load_contract()
        result = {
            "status": "OFFLINE_V13_FRAMED_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "predecessor_terminal_id": contract.predecessor.terminal_id,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
            "next_gate": contract.next_gate,
        }
    elif args.qualify_source:
        result = qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = validate_source_qualification()
    else:
        root = v10._root(None)
        contract = load_contract(repository=root)
        qualification = _load_qualification(root)
        if args.show_state_template:
            result = {
                "status": "V13_EXACT_STATE_STATEMENT_REQUIRED",
                "statement": expected_state_statement(contract, qualification),
                "external_observations_made": 0,
                "execution_authorized": False,
            }
        elif args.record_state:
            if args.statement is None:
                raise SystemExit("--statement is required")
            result = record_state(statement=args.statement)
        else:
            state = _load_state(root)
            if args.show_approval_template:
                result = {
                    "status": "V13_EXACT_APPROVAL_STATEMENT_REQUIRED",
                    "statement": expected_approval_statement(contract, qualification, state),
                    "attempt_started": False,
                }
            elif args.record_approval:
                if args.statement is None:
                    raise SystemExit("--statement is required")
                result = record_approval(statement=args.statement)
            else:
                approval = _load_approval(root)
                if args.show_run_template:
                    result = {
                        "status": "V13_EXACT_RUN_STATEMENT_REQUIRED",
                        "statement": expected_run_statement(
                            contract, qualification, state, approval
                        ),
                        "attempt_started": False,
                    }
                elif args.run_exact_attempt:
                    if args.statement is None:
                        raise SystemExit("--statement is required")
                    result = run_once(statement=args.statement)
                else:
                    result = validate_attempt_chain()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
