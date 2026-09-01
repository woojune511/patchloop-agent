from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.errors import ContractError


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the superseded candidate-v22 entry.")
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=("rehearse", "execute"), default="rehearse")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--approve-live-cost", action="store_true")
    parser.add_argument("--approved-execution-hash")
    args = parser.parse_args()

    del args
    raise ContractError("candidate-v22 is zero-call superseded and cannot be rehearsed or executed")


if __name__ == "__main__":
    main()
