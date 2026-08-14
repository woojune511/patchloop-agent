from __future__ import annotations

import argparse
import json
from pathlib import Path

from patchloop.environment import exact_openai_api_key_present
from patchloop.evals.heldout_ac_preflight import preflight_heldout_ac


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the held-out A/C no-call preflight")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()
    result = preflight_heldout_ac(
        credential_present=exact_openai_api_key_present(args.env_file),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["execution_candidate_ready"] else 2)


if __name__ == "__main__":
    main()
