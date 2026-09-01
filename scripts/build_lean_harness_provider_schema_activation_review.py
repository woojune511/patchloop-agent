from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.provider_schema_activation_review import (
    REVIEW_PATH,
    build_activation_review,
    materialize_activation_review,
    review_bytes,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Lean V27 activation without creating a candidate or calling a provider."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        value = build_activation_review(args.repository)
        raw = review_bytes(value)
        if raw != review_bytes(build_activation_review(args.repository)):
            raise SystemExit("review bytes differ")
        if (args.repository / REVIEW_PATH).read_bytes() != raw:
            raise SystemExit("stored review bytes differ")
    else:
        value = materialize_activation_review(args.repository)
    print(value["content_hash"])
    print(f"status={value['decision']['adoption_status']} external_calls=0 candidate_created=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
