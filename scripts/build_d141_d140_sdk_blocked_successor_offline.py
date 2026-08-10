"""CLI for D-141 offline qualification and future fresh SDK transition."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import d141_d140_sdk_blocked_successor_offline as d141


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--build-gate", action="store_true")
    actions.add_argument("--validate-gate", action="store_true")
    actions.add_argument("--validate-gate-postcommit", action="store_true")
    actions.add_argument("--render-activation-template", action="store_true")
    actions.add_argument("--create-activation-receipt", action="store_true")
    actions.add_argument("--validate-activation-receipt", action="store_true")
    actions.add_argument("--validate-activation-receipt-postcommit", action="store_true")
    actions.add_argument("--create-sdk-attempt", action="store_true")
    actions.add_argument("--validate-sdk-attempt", action="store_true")
    actions.add_argument("--validate-sdk-attempt-postcommit", action="store_true")
    actions.add_argument("--validate-sdk-action-started", action="store_true")
    actions.add_argument(
        "--validate-sdk-action-started-preservation-postcommit", action="store_true"
    )
    actions.add_argument("--run-sdk-preflight", action="store_true")
    actions.add_argument("--validate-sdk-terminal", action="store_true")
    actions.add_argument("--validate-sdk-terminal-postcommit", action="store_true")
    args = parser.parse_args()

    if args.build_gate:
        result: object = d141.run_d141_offline_source_gate()
    elif args.validate_gate:
        result = d141.validate_d141_offline_source_gate()
    elif args.validate_gate_postcommit:
        result = d141.validate_d141_offline_source_gate(mode="post-evidence-commit")
    elif args.render_activation_template:
        result = d141.render_d141_external_activation_template()
    elif args.create_activation_receipt:
        result = d141.create_d141_activation_receipt()
    elif args.validate_activation_receipt:
        result = d141.validate_d141_activation_receipt()
    elif args.validate_activation_receipt_postcommit:
        result = d141.validate_d141_activation_receipt(mode="post-commit")
    elif args.create_sdk_attempt:
        result = d141.create_d141_sdk_attempt()
    elif args.validate_sdk_attempt:
        result = d141.validate_d141_sdk_attempt()
    elif args.validate_sdk_attempt_postcommit:
        result = d141.validate_d141_sdk_attempt(mode="post-commit")
    elif args.validate_sdk_action_started:
        result = d141.validate_d141_sdk_action_started()
    elif args.validate_sdk_action_started_preservation_postcommit:
        result = d141.validate_d141_sdk_action_started(mode="post-preservation-commit")
    elif args.run_sdk_preflight:
        result = d141.run_d141_sdk_no_call_successor()
    elif args.validate_sdk_terminal:
        result = d141.validate_d141_sdk_terminal()
    else:
        result = d141.validate_d141_sdk_terminal(mode="post-transition-commit")

    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
