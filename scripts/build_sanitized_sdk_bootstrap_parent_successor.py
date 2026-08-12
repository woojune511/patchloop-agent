"""Materialize or validate the offline v9 bootstrap-parent successor."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import sanitized_sdk_bootstrap_parent_successor as successor


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize-contract", action="store_true")
    group.add_argument("--validate-contract", action="store_true")
    group.add_argument("--qualify-source", action="store_true")
    group.add_argument("--validate-source", action="store_true")
    parser.add_argument("--source-commit", default="HEAD")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.materialize_contract:
        result = successor.materialize_contract()
    elif args.validate_contract:
        contract = successor.load_contract()
        result = {
            "status": "OFFLINE_SANITIZED_SDK_BOOTSTRAP_PARENT_CONTRACT_VALID_LIVE_CLOSED",
            "contract_id": contract.contract_id,
            "contract_content_hash": contract.content_hash,
            "external_observations_made": 0,
            "external_mutations_made": 0,
            "execution_authorized": False,
        }
    elif args.qualify_source:
        result = successor.qualify_source(source_commit=args.source_commit)
    else:
        result = successor.validate_source_qualification()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
