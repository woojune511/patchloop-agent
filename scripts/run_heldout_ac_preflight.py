from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from patchloop.environment import exact_openai_api_key_present
from patchloop.evals.heldout_ac_preflight import preflight_heldout_ac


def _write_canonical_output(path: Path, payload: dict[str, object]) -> bytes:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"held-out preflight output already exists: {path}")
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return encoded


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the held-out A/C no-call preflight")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New-only UTF-8 JSON handoff path",
    )
    args = parser.parse_args()
    result = preflight_heldout_ac(
        credential_present=exact_openai_api_key_present(args.env_file),
    )
    encoded = _write_canonical_output(args.output.resolve(strict=False), result)
    print(encoded.decode("utf-8"), end="")
    raise SystemExit(0 if result["execution_candidate_ready"] else 2)


if __name__ == "__main__":
    main()
