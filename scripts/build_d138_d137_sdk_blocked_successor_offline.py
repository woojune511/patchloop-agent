"""CLI for D-138 offline qualification and future fresh SDK transition."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import d138_d137_sdk_blocked_successor_offline as d138


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
        result: object = d138.run_d138_offline_source_gate()
    elif args.validate_gate:
        result = d138.validate_d138_offline_source_gate()
    elif args.validate_gate_postcommit:
        result = d138.validate_d138_offline_source_gate(mode="post-evidence-commit")
    elif args.render_activation_template:
        result = d138.render_d138_external_activation_template()
    elif args.create_activation_receipt:
        result = d138.create_d138_activation_receipt()
    elif args.validate_activation_receipt:
        result = d138.validate_d138_activation_receipt()
    elif args.validate_activation_receipt_postcommit:
        result = d138.validate_d138_activation_receipt(mode="post-commit")
    elif args.create_sdk_attempt:
        result = d138.create_d138_sdk_attempt()
    elif args.validate_sdk_attempt:
        result = d138.validate_d138_sdk_attempt()
    elif args.validate_sdk_attempt_postcommit:
        result = d138.validate_d138_sdk_attempt(mode="post-commit")
    elif args.validate_sdk_action_started:
        result = d138.validate_d138_sdk_action_started()
    elif args.validate_sdk_action_started_preservation_postcommit:
        result = d138.validate_d138_sdk_action_started(mode="post-preservation-commit")
    elif args.run_sdk_preflight:
        result = d138.run_d138_sdk_no_call_successor()
    elif args.validate_sdk_terminal:
        result = d138.validate_d138_sdk_terminal()
    else:
        result = d138.validate_d138_sdk_terminal(mode="post-transition-commit")

    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
