from __future__ import annotations

import argparse
import json

from patchloop.evals import d132_d130_external_activation_offline as d132


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or validate the D-132 D-130 activation successor"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-offline-gate", action="store_true")
    modes.add_argument("--validate-offline-gate", action="store_true")
    modes.add_argument("--validate-offline-gate-post-commit", action="store_true")
    modes.add_argument("--print-fresh-activation-template", action="store_true")
    modes.add_argument("--create-activation-receipt", action="store_true")
    modes.add_argument("--validate-activation-receipt", action="store_true")
    modes.add_argument("--validate-activation-receipt-post-commit", action="store_true")
    modes.add_argument("--run-external-preflight", action="store_true")
    modes.add_argument("--validate-external-preflight", action="store_true")
    modes.add_argument("--validate-external-preflight-post-commit", action="store_true")
    args = parser.parse_args()

    if args.build_offline_gate:
        value = d132.run_d132_offline_source_gate()
    elif args.validate_offline_gate:
        value = d132.validate_d132_offline_source_gate()
    elif args.validate_offline_gate_post_commit:
        value = d132.validate_d132_offline_source_gate(mode="post-evidence-commit")
    elif args.print_fresh_activation_template:
        print(d132.render_d132_external_activation_template())
        return 0
    elif args.create_activation_receipt:
        value = d132.create_d130_external_activation_receipt()
    elif args.validate_activation_receipt:
        value = d132.validate_d130_external_activation_receipt()
    elif args.validate_activation_receipt_post_commit:
        value = d132.validate_d130_external_activation_receipt(mode="post-receipt-commit")
    elif args.run_external_preflight:
        value = d132.run_d130_external_no_call_preflight()
    elif args.validate_external_preflight:
        value = d132.validate_d130_external_no_call_gate()
    else:
        value = d132.validate_d130_external_no_call_gate(mode="post-evidence-commit")
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
