from __future__ import annotations

import argparse
import json

from patchloop.evals.d131_d130_local_admission_offline import (
    create_d130_armed_intent,
    create_d130_local_admission_receipt,
    render_d130_external_activation_challenge,
    render_d131_local_admission_template,
    run_d131_offline_source_gate,
    validate_d130_local_admission,
    validate_d131_offline_source_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or validate the D-131 offline admission source"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-gate", action="store_true")
    modes.add_argument("--validate-gate", action="store_true")
    modes.add_argument("--print-local-admission-template", action="store_true")
    modes.add_argument("--create-receipt", action="store_true")
    modes.add_argument("--validate-receipt", action="store_true")
    modes.add_argument("--create-armed-intent", action="store_true")
    modes.add_argument("--validate-armed-intent", action="store_true")
    modes.add_argument("--validate-post-intent-commit", action="store_true")
    modes.add_argument("--print-activation-challenge", action="store_true")
    args = parser.parse_args()
    if args.build_gate:
        value = run_d131_offline_source_gate()
    elif args.validate_gate:
        value = validate_d131_offline_source_gate()
    elif args.print_local_admission_template:
        print(render_d131_local_admission_template())
        return 0
    elif args.create_receipt:
        value = create_d130_local_admission_receipt()
    elif args.validate_receipt:
        value = validate_d130_local_admission(mode="receipt")
    elif args.create_armed_intent:
        value = create_d130_armed_intent()
    elif args.validate_armed_intent:
        value = validate_d130_local_admission(mode="armed-intent")
    elif args.validate_post_intent_commit:
        value = validate_d130_local_admission(mode="post-intent-commit")
    else:
        print(render_d130_external_activation_challenge())
        return 0
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
