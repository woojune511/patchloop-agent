"""CLI for D-137 offline qualification and future two-phase transitions."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import d137_d136_no_call_preflight_successor_offline as d137


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
    actions.add_argument("--create-docker-attempt", action="store_true")
    actions.add_argument("--validate-docker-attempt", action="store_true")
    actions.add_argument("--validate-docker-attempt-postcommit", action="store_true")
    actions.add_argument("--validate-docker-action-started", action="store_true")
    actions.add_argument(
        "--validate-docker-action-started-preservation-postcommit", action="store_true"
    )
    actions.add_argument("--run-docker-preflight", action="store_true")
    actions.add_argument("--validate-docker-terminal", action="store_true")
    actions.add_argument("--validate-docker-terminal-postcommit", action="store_true")
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
        result: object = d137.run_d137_offline_source_gate()
    elif args.validate_gate:
        result = d137.validate_d137_offline_source_gate()
    elif args.validate_gate_postcommit:
        result = d137.validate_d137_offline_source_gate(mode="post-evidence-commit")
    elif args.render_activation_template:
        result = d137.render_d137_external_activation_template()
    elif args.create_activation_receipt:
        result = d137.create_d137_activation_receipt()
    elif args.validate_activation_receipt:
        result = d137.validate_d137_activation_receipt()
    elif args.validate_activation_receipt_postcommit:
        result = d137.validate_d137_activation_receipt(mode="post-commit")
    elif args.create_docker_attempt:
        result = d137.create_d137_docker_attempt()
    elif args.validate_docker_attempt:
        result = d137.validate_d137_docker_attempt()
    elif args.validate_docker_attempt_postcommit:
        result = d137.validate_d137_docker_attempt(mode="post-commit")
    elif args.validate_docker_action_started:
        result = d137.validate_d137_docker_action_started()
    elif args.validate_docker_action_started_preservation_postcommit:
        result = d137.validate_d137_docker_action_started(mode="post-preservation-commit")
    elif args.run_docker_preflight:
        result = d137.run_d137_docker_no_call_preflight()
    elif args.validate_docker_terminal:
        result = d137.validate_d137_docker_terminal()
    elif args.validate_docker_terminal_postcommit:
        result = d137.validate_d137_docker_terminal(mode="post-transition-commit")
    elif args.create_sdk_attempt:
        result = d137.create_d137_sdk_attempt()
    elif args.validate_sdk_attempt:
        result = d137.validate_d137_sdk_attempt()
    elif args.validate_sdk_attempt_postcommit:
        result = d137.validate_d137_sdk_attempt(mode="post-commit")
    elif args.validate_sdk_action_started:
        result = d137.validate_d137_sdk_action_started()
    elif args.validate_sdk_action_started_preservation_postcommit:
        result = d137.validate_d137_sdk_action_started(mode="post-preservation-commit")
    elif args.run_sdk_preflight:
        result = d137.run_d137_sdk_no_call_preflight()
    elif args.validate_sdk_terminal:
        result = d137.validate_d137_sdk_terminal()
    else:
        result = d137.validate_d137_sdk_terminal(mode="post-transition-commit")

    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
