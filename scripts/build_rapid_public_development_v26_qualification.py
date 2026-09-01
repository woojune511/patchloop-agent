from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.evals.rapid_public_development_v26_qualification import (
    QUALIFICATION_PATH,
    materialize_rapid_public_development_v26_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the zero-call candidate-v32 V25/V26 package-comparison qualification."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    args = parser.parse_args()
    value = materialize_rapid_public_development_v26_qualification(args.repository)
    raw = qualification_bytes(value)
    print(
        json.dumps(
            {
                "path": QUALIFICATION_PATH.as_posix(),
                "bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
                "content_hash": value["content_hash"],
                "paid_execution_authorized": value["paid_execution_authorized"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
