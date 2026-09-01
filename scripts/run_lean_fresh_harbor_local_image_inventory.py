"""Prepare or consume the approval-gated local-image inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.fresh_harbor_local_image_inventory import (
    materialize_approval,
    run_once,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "observe"))
    parser.add_argument("--approval-message")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.phase == "prepare":
        if not args.approval_message:
            parser.error("--approval-message is required for prepare")
        value = materialize_approval(root, args.approval_message).model_dump(mode="json")
    else:
        if args.approval_message:
            parser.error("--approval-message is not accepted for observe")
        value = run_once(root).model_dump(mode="json")
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
