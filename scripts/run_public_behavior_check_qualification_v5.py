"""Record exact approval or consume the one-use v5 Docker qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.public_behavior_check_qualification_v5 import (
    materialize_approval,
    run_once,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--approval-message")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.phase == "prepare":
        if not args.approval_message:
            parser.error("--approval-message is required for prepare")
        result = materialize_approval(root, args.approval_message)
    else:
        if args.approval_message:
            parser.error("--approval-message is not accepted for execute")
        result = run_once(root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
