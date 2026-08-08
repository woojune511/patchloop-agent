from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory.d099_review import write_d099_review_proposal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the D-099 public-evidence review and deduplication proposal."
    )
    parser.add_argument("--repo-root", type=Path, default=repository_root())
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    repo_root = arguments.repo_root.resolve()
    runtime_root = (
        arguments.runtime_root.resolve()
        if arguments.runtime_root is not None
        else repo_root / ".patchloop"
    )
    output = write_d099_review_proposal(
        arguments.output,
        repo_root=repo_root,
        root=runtime_root,
    )
    content = output.read_bytes()
    print(output)
    print(f"bytes={len(content)}")
    print(f"sha256={sha256_bytes(content)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
