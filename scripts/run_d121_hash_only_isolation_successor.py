"""Prepare or validate the D-121 successor execution candidate."""

from __future__ import annotations

import argparse
import json

from patchloop.memory.d121_hash_only_isolation_successor import (
    prepare_d121_execution_candidate,
    validate_d121_execution,
    validate_d121_preparation,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository")
    parser.add_argument("--docker-path")
    parser.add_argument("--validate-preparation", action="store_true")
    parser.add_argument("--validate-execution", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    selected = sum(
        bool(value)
        for value in (
            args.validate_preparation,
            args.validate_execution,
        )
    )
    if selected > 1:
        raise SystemExit("select only one validation/execution mode")
    if args.validate_preparation:
        result = validate_d121_preparation(repository=args.repository)
    elif args.validate_execution:
        result = validate_d121_execution(repository=args.repository)
    else:
        result = prepare_d121_execution_candidate(
            repository=args.repository,
            docker_path=args.docker_path,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
