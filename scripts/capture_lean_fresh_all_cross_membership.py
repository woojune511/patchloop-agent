"""Capture the exact public Harbor membership response for the all-cross successor.

This is a public metadata capture only.  It reads the publishable Harbor Hub
configuration from an exact local Harbor source checkout, performs one GET on
first materialization, and writes the response bytes new-only.  A second call
validates the existing bytes without contacting the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATASET_VERSION_ID = "574acb72-70aa-46fb-8758-0a814a5eb213"
EXPECTED_ROWS = 111
EXPECTED_BYTES = 21_512
EXPECTED_SHA256 = "b0e489931259f8643a94d47b6b52d9b3e467571c0ad3bcf80d97f0c5069b2527"
EXPECTED_HARBOR_COMMIT = "f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e"
DEFAULT_OUTPUT = Path("reports/fresh-panel/raw/harbor-swe-rebench-07-2026-r1-membership.json")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate(raw: bytes) -> dict[str, object]:
    if len(raw) != EXPECTED_BYTES or _sha256(raw) != EXPECTED_SHA256:
        raise RuntimeError("Harbor membership response differs from the observed public snapshot")
    try:
        rows = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Harbor membership response is not valid UTF-8 JSON") from exc
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS:
        raise RuntimeError("Harbor membership response row count differs")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"task_version"}:
            raise RuntimeError("Harbor membership response shape differs")
        task_version = row["task_version"]
        if not isinstance(task_version, dict) or set(task_version) != {"content_hash", "package"}:
            raise RuntimeError("Harbor membership task-version shape differs")
        package = task_version["package"]
        if not isinstance(package, dict) or set(package) != {"name", "org"}:
            raise RuntimeError("Harbor membership package shape differs")
        org = package["org"]
        if not isinstance(org, dict) or set(org) != {"name"}:
            raise RuntimeError("Harbor membership organization shape differs")
        if not all(
            isinstance(value, str) and value
            for value in (task_version["content_hash"], package["name"], org["name"])
        ):
            raise RuntimeError("Harbor membership public identity is invalid")
    return {
        "dataset_version_id": DATASET_VERSION_ID,
        "rows": len(rows),
        "bytes": len(raw),
        "sha256": f"sha256:{_sha256(raw)}",
    }


def _parse_public_configuration(harbor_source: Path) -> tuple[str, str]:
    config_path = harbor_source / "src" / "harbor" / "auth" / "constants.py"
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("Harbor public Hub configuration is unavailable") from exc
    url_match = re.search(r'DEFAULT_SUPABASE_URL\s*=\s*"([^"]+)"', text)
    key_match = re.search(r'DEFAULT_SUPABASE_PUBLISHABLE_KEY\s*=\s*"([^"]+)"', text)
    if url_match is None or key_match is None:
        raise RuntimeError("Harbor public Hub configuration shape differs")
    return url_match.group(1), key_match.group(1)


def _fetch(harbor_source: Path) -> bytes:
    base_url, publishable_key = _parse_public_configuration(harbor_source)
    query = urlencode(
        {
            "select": (
                "task_version:task_version_id(content_hash,"
                "package:package_id(name,org:org_id(name)))"
            ),
            "dataset_version_id": f"eq.{DATASET_VERSION_ID}",
            "order": "task_version_id.asc",
        }
    )
    request = Request(
        f"{base_url}/rest/v1/dataset_version_task?{query}",
        headers={
            "apikey": publishable_key,
            "Authorization": f"Bearer {publishable_key}",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - exact frozen HTTPS source
        if response.status != 200:
            raise RuntimeError(f"Harbor membership capture returned HTTP {response.status}")
        return response.read()


def _resolved_output(repository: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("capture output must be repository-relative")
    allowed = (repository / "reports" / "fresh-panel" / "raw").resolve()
    output = (repository / relative).resolve()
    if output != allowed / output.name or output.suffix != ".json":
        raise RuntimeError("capture output must be a direct JSON child of reports/fresh-panel/raw")
    cursor = output.parent
    while cursor != repository.parent:
        if cursor.exists() and cursor.is_symlink():
            raise RuntimeError("capture output parent must not be a symlink")
        if cursor == repository:
            break
        cursor = cursor.parent
    return output


def capture(repository: Path, harbor_source: Path, output_relative: Path) -> dict[str, object]:
    repository = repository.resolve()
    harbor_source = harbor_source.resolve()
    output = _resolved_output(repository, output_relative)
    if output.exists():
        summary = _validate(output.read_bytes())
        return {**summary, "network_calls": 0, "existing_file_validated": True}

    raw = _fetch(harbor_source)
    summary = _validate(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if output.read_bytes() != raw:
            raise RuntimeError(
                "capture output appeared concurrently with different bytes"
            ) from None
    return {**summary, "network_calls": 1, "existing_file_validated": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--harbor-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = capture(args.repository, args.harbor_source, args.output)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
