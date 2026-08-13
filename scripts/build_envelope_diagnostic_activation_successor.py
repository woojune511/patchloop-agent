"""Build or validate the source-only v22 activation boundary."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import envelope_diagnostic_activation_successor as successor


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--show-contract", action="store_true")
    modes.add_argument("--materialize-contract", action="store_true")
    modes.add_argument("--validate-contract", action="store_true")
    modes.add_argument("--qualify-source", metavar="COMMIT")
    modes.add_argument("--validate-source", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    root = successor.v10._root(None)
    if args.show_contract:
        result = successor._build_contract(root).model_dump(mode="json")
    elif args.materialize_contract:
        result = successor.materialize_contract()
    elif args.validate_contract:
        value = successor.load_contract()
        result = {
            "status": "V22_TYPED_DIAGNOSTIC_CHANNEL_CONTRACT_VALID_ACTIVATION_CLOSED",
            "contract_id": value.contract_id,
            "contract_content_hash": value.content_hash,
            "diagnostic_or_mock_processes_launched": 0,
            "local_git_provenance_subprocesses_may_run": True,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
            "next_gate": "exact-source-commit-and-offline-qualification",
        }
    elif args.qualify_source:
        result = successor.qualify_source(source_commit=args.qualify_source)
    else:
        result = successor.validate_source_qualification()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
