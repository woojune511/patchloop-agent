"""CLI for D-136 offline qualification and future append-only transitions."""

from __future__ import annotations

import argparse
import json

from patchloop.evals import d136_d135_fixed_pricing_successor_offline as d136


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
    actions.add_argument("--create-pricing-attempt", action="store_true")
    actions.add_argument("--validate-pricing-attempt", action="store_true")
    actions.add_argument("--validate-pricing-attempt-postcommit", action="store_true")
    actions.add_argument("--validate-action-started", action="store_true")
    actions.add_argument("--validate-action-started-preservation-postcommit", action="store_true")
    actions.add_argument("--capture-pricing", action="store_true")
    actions.add_argument("--validate-pricing-terminal", action="store_true")
    actions.add_argument("--validate-pricing-terminal-postcommit", action="store_true")
    args = parser.parse_args()

    if args.build_gate:
        result: object = d136.run_d136_offline_source_gate()
    elif args.validate_gate:
        result = d136.validate_d136_offline_source_gate()
    elif args.validate_gate_postcommit:
        result = d136.validate_d136_offline_source_gate(mode="post-evidence-commit")
    elif args.render_activation_template:
        result = d136.render_d136_external_activation_template()
    elif args.create_activation_receipt:
        result = d136.create_d136_activation_receipt()
    elif args.validate_activation_receipt:
        result = d136.validate_d136_activation_receipt()
    elif args.validate_activation_receipt_postcommit:
        result = d136.validate_d136_activation_receipt(mode="post-commit")
    elif args.create_pricing_attempt:
        result = d136.create_d136_pricing_attempt()
    elif args.validate_pricing_attempt:
        result = d136.validate_d136_pricing_attempt()
    elif args.validate_pricing_attempt_postcommit:
        result = d136.validate_d136_pricing_attempt(mode="post-commit")
    elif args.validate_action_started:
        result = d136.validate_d136_action_started()
    elif args.validate_action_started_preservation_postcommit:
        result = d136.validate_d136_action_started(mode="post-preservation-commit")
    elif args.capture_pricing:
        result = d136.run_d136_fixed_pricing_capture()
    else:
        result = d136.validate_d136_pricing_terminal(
            mode=(
                "post-transition-commit" if args.validate_pricing_terminal_postcommit else "pending"
            )
        )

    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
