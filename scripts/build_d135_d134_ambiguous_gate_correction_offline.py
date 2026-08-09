from __future__ import annotations

import argparse
import json

from patchloop.evals import d135_d134_ambiguous_gate_correction_offline as d135


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or validate the D-135 ambiguous-gate correction boundary"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-offline-gate", action="store_true")
    modes.add_argument("--validate-offline-gate", action="store_true")
    modes.add_argument("--validate-offline-gate-post-commit", action="store_true")
    modes.add_argument("--print-terminalization-template", action="store_true")
    modes.add_argument("--create-procedural-terminal", action="store_true")
    modes.add_argument("--validate-procedural-terminal", action="store_true")
    modes.add_argument("--validate-procedural-terminal-post-commit", action="store_true")
    args = parser.parse_args()

    if args.build_offline_gate:
        value = d135.run_d135_corrected_offline_source_gate()
    elif args.validate_offline_gate:
        value = d135.validate_d135_corrected_offline_source_gate()
    elif args.validate_offline_gate_post_commit:
        value = d135.validate_d135_corrected_offline_source_gate(mode="post-evidence-commit")
    elif args.print_terminalization_template:
        print(d135.render_d135_terminalization_approval_template())
        return 0
    elif args.create_procedural_terminal:
        value = d135.create_d135_procedural_terminal()
    elif args.validate_procedural_terminal:
        value = d135.validate_d135_procedural_terminal()
    else:
        value = d135.validate_d135_procedural_terminal(mode="post-terminal-commit")
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
