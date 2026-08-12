"""Build, qualify, or activate the v18 supervised-frame wrapper."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import supervised_frame_activation_successor as successor


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
        result = successor.materialize_contract()
    elif args.validate_contract:
        contract = successor.load_contract()
        result = {
            "status": "OFFLINE_V18_ACTIVATION_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "predecessor_source_qualification_hash": (
                contract.predecessor.source_qualification_hash
            ),
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = successor.qualify_source(source_commit=args.source_commit)
    elif args.validate_source:
        result = successor.validate_source_qualification()
    elif args.show_state_template:
        contract = successor.load_contract()
        qualification = successor._load_qualification(successor.v10._root(None))
        result = {
            "status": "V18_EXACT_STATE_STATEMENT_REQUIRED",
            "statement": successor.expected_state_statement(contract, qualification),
            "attempt_started": False,
        }
    elif args.record_state:
        if args.statement is None:
            raise SystemExit("--record-state requires --statement")
        result = successor.record_state(statement=args.statement)
    elif args.show_approval_template:
        root = successor.v10._root(None)
        contract = successor.load_contract(repository=root)
        qualification = successor._load_qualification(root)
        state = successor._load_state(root)
        result = {
            "status": "V18_EXACT_APPROVAL_STATEMENT_REQUIRED",
            "statement": successor.expected_approval_statement(contract, qualification, state),
            "attempt_started": False,
        }
    elif args.record_approval:
        if args.statement is None:
            raise SystemExit("--record-approval requires --statement")
        result = successor.record_approval(statement=args.statement)
    elif args.show_run_template:
        root = successor.v10._root(None)
        contract = successor.load_contract(repository=root)
        qualification = successor._load_qualification(root)
        state = successor._load_state(root)
        approval = successor._load_approval(root)
        result = {
            "status": "V18_EXACT_RUN_STATEMENT_REQUIRED",
            "statement": successor.expected_run_statement(contract, qualification, state, approval),
            "attempt_started": False,
        }
    elif args.run_exact_attempt:
        if args.statement is None:
            raise SystemExit("--run-exact-attempt requires --statement")
        result = successor.run_once(statement=args.statement)
    else:
        result = successor.validate_attempt_chain()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
