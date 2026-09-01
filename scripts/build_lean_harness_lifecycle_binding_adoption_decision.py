from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.agent.workflow_lifecycle_binding_adoption_decision import (
    DECISION_PATH,
    build_lifecycle_binding_adoption_decision,
    decision_bytes,
    materialize_lifecycle_binding_adoption_decision,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the zero-call Lean V28 lifecycle-binding adoption decision."
    )
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        value = build_lifecycle_binding_adoption_decision(args.repository)
        raw = decision_bytes(value)
        if raw != decision_bytes(build_lifecycle_binding_adoption_decision(args.repository)):
            raise SystemExit("decision bytes differ")
        if (args.repository / DECISION_PATH).read_bytes() != raw:
            raise SystemExit("stored decision bytes differ")
    else:
        value = materialize_lifecycle_binding_adoption_decision(args.repository)
    print(value["content_hash"])
    print(f"status={value['decision']['adoption_status']} external_calls=0 candidate_created=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
