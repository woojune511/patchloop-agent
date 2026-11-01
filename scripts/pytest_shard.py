"""Partition the actual pytest collection by file; retain every collected test."""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


def select_nodes(nodes: list[str], index: int, total: int) -> list[str]:
    if total < 1 or not 0 <= index < total:
        raise ValueError("shard index must be within a positive shard count")
    files = sorted({node.split("::", 1)[0] for node in nodes})
    selected = set(files[index::total])
    return [node for node in nodes if node.split("::", 1)[0] in selected]


class Collection:
    def __init__(self) -> None:
        self.nodes: list[str] = []

    def pytest_collection_finish(self, session) -> None:
        self.nodes = [item.nodeid for item in session.items]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--total", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Validate before collection or writing an argfile. An empty argfile can
    # accidentally select the repository root, so it must never be admitted.
    select_nodes([], args.index, args.total)
    # Match `python -m pytest`: a shared editable environment may otherwise
    # import a different checkout before this worktree during collection.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    collection, captured = Collection(), io.StringIO()
    with redirect_stdout(captured):
        code = pytest.main(["tests", "--collect-only", "-q"], plugins=[collection])
    if code != 0:
        print(captured.getvalue())
        return int(code)
    nodes = select_nodes(collection.nodes, args.index, args.total)
    if not nodes:
        raise ValueError("selected shard has no tests")
    args.output.write_text("\n".join(nodes) + "\n", encoding="utf-8")
    print(f"Shard {args.index + 1}/{args.total}: {len(nodes)}/{len(collection.nodes)} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
