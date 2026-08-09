"""Create or validate the non-retroactive D-129 sequence-block evidence."""

from __future__ import annotations

import argparse
import json

from patchloop.evals.d129_external_sequence_block import (
    create_d129_approval_receipt,
    record_d129_sequence_block_terminal,
    validate_d129_sequence_block,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-receipt", action="store_true")
    modes.add_argument("--record-procedural-terminal", action="store_true")
    modes.add_argument("--validate-receipt", action="store_true")
    modes.add_argument("--validate-terminal", action="store_true")
    modes.add_argument("--validate-post-commit", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.create_receipt:
        result = create_d129_approval_receipt()
    elif args.record_procedural_terminal:
        result = record_d129_sequence_block_terminal()
    elif args.validate_receipt:
        result = validate_d129_sequence_block(mode="receipt")
    elif args.validate_terminal:
        result = validate_d129_sequence_block(mode="terminal")
    else:
        result = validate_d129_sequence_block(mode="post-evidence")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
