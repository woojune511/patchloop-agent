from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.three_visible_check_runtime_compatibility_qualification import (
    QUALIFICATION_PATH,
    materialize_three_visible_check_runtime_compatibility_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    arguments = parser.parse_args()
    root = Path(arguments.repository).resolve()
    value = materialize_three_visible_check_runtime_compatibility_qualification(root)
    raw = qualification_bytes(value)
    print(
        {
            "path": QUALIFICATION_PATH.as_posix(),
            "bytes": len(raw),
            "file_sha256": sha256_bytes(raw),
            "content_hash": value["content_hash"],
            "status": value["status"],
            "next_gate": value["next_gate"],
        }
    )


if __name__ == "__main__":
    main()
