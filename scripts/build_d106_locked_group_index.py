"""Run the explicitly approved D-106 locked snapshot and unfrozen index build."""

from __future__ import annotations

import argparse
from pathlib import Path

from patchloop.memory import d106_locked_group_index as d106


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--snapshot-directory",
        type=Path,
        default=d106.DEFAULT_SNAPSHOT_DIRECTORY,
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Require the exact snapshot to exist locally without contacting Hugging Face.",
    )
    args = parser.parse_args()

    result = d106.run_d106_authorized_build(
        repository=args.repository,
        snapshot_directory=args.snapshot_directory,
        download_snapshot=not args.no_download,
    )
    print(f"receipt_id={result['receipt']['receipt_id']}")
    print(f"snapshot_manifest_hash={result['snapshot']['snapshot_manifest_hash']}")
    print(f"preflight_id={result['preflight']['preflight_id']}")
    print(f"index_id={result['index']['index_id']}")
    print(f"gate_id={result['gate']['gate_id']}")
    print(f"gate_file_sha256={result['gate']['gate_file_sha256']}")
    print(f"memory_index_frozen={result['frozen']}")
    print(f"retrieval_ready={result['retrieval_ready']}")
    print(f"core_campaign_unlocked={result['core_campaign_unlocked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
