"""Build, validate, or render the offline D-130 successor gate."""

from __future__ import annotations

import argparse
import json

from patchloop.evals.d130_d129_sequence_block_successor_offline import (
    render_d130_two_stage_admission_template,
    run_d130_offline_source_gate,
    validate_d130_offline_source_gate,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--print-admission-template", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.build:
        result = run_d130_offline_source_gate()
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    elif args.validate:
        result = validate_d130_offline_source_gate()
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    else:
        print(render_d130_two_stage_admission_template())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
