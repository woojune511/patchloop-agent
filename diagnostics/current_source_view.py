"""Offline, single-factor current-source presentation prototype; never dispatches."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from patchloop.dev.conversation import history_metadata, validate_model_input
from patchloop.dev.native_sources import _SourceIndex
from patchloop.dev.native_sources import resolve_source_group as _inline_group
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_json

SCHEMA = "current-source-inline-prototype-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def wire(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()




def inline_current_sources(request: dict) -> tuple[dict, dict]:
    """Change only the latest state catalog; preserve all prior native wire items."""
    require(isinstance(request, dict) and isinstance(request.get("input"), list), "invalid request")
    items = request["input"]
    validate_model_input(items, history_metadata(items))
    require(len(items) > 3 and items[-1].get("role") == "developer", "latest state required")
    record = json.loads(items[-1]["content"])
    require(wire(record).decode() == items[-1]["content"], "noncanonical state wire")
    state = record["state"]
    groups = state.get("current_sources")
    require(isinstance(groups, list), "current source catalog required")
    for item in items:
        if item.get("type") == "reasoning":
            require(isinstance(item.get("encrypted_content"), str)
                    and bool(item["encrypted_content"]) and item.get("summary") == []
                    and not item.get("text") and not item.get("content"), "invalid reasoning item")
    index = _SourceIndex(items[:-1])
    projected, selected, identities, removed = [], [], set(), 0
    for group in groups:
        changed, lines, count = _inline_group(group, index)
        identity = (group["path"], group["file_hash"])
        require(identity not in identities, "duplicate source identity")
        identities.add(identity)
        projected.append(changed)
        selected.extend([*identity, n, line] for n, line in sorted(lines.items()))
        removed += count
    result = copy.deepcopy(request)
    record["state"]["current_sources"] = projected
    result["input"][-1]["content"] = wire(record).decode()
    # Independent resolution of the inline view proves identical selected line coverage.
    after = []
    for group in projected:
        _, lines, count = _inline_group(group, index)
        require(count == 0, "unresolved current source reference")
        after.extend([group["path"], group["file_hash"], n, line]
                     for n, line in sorted(lines.items()))
    require(selected == after, "current source selection changed")
    return result, {
        "schema_version": SCHEMA, "official": False, "claim_eligible": False,
        "provider_calls": 0, "input_count_calls": 0, "tool_executions": 0,
        "original_request_bytes": len(wire(request)), "prototype_request_bytes": len(wire(result)),
        "input_item_count": len(items), "unchanged_prefix_item_count": len(items) - 1,
        "selected_line_count": len(selected), "selected_lines_hash": sha256_json(selected),
        "selected_ranges_equal": True, "removed_current_reference_ranges": removed,
        "reasoning_item_count": sum(i.get("type") == "reasoning" for i in items),
        "scope": "latest current_sources delivery only; no token or model-effect claim",
    }


def prepare(input_path: Path, expected_hash: str, output_root: Path) -> dict:
    require(input_path.is_absolute() and output_root.is_absolute(), "absolute paths required")
    source, root = input_path.resolve(), output_root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    require(not root.is_relative_to(repository_root().resolve())
            and not source.is_relative_to(root),
            "output root overlaps protected input or repository")
    original = source.read_bytes()
    require(sha256_bytes(original) == expected_hash, "input hash mismatch")
    request = json.loads(original)
    require(wire(request) == original, "noncanonical request wire")
    candidate, metrics = inline_current_sources(request)
    body = wire(candidate)
    manifest = {
        **metrics, "input_path": str(source), "input_hash": expected_hash,
        "prototype_hash": sha256_bytes(body),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
    }
    root.mkdir()
    (root / "request.json").write_bytes(body)
    (root / "manifest.json").write_bytes(wire(manifest))
    return manifest


def validate(root: Path) -> dict:
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest["implementation_hash"] == sha256_bytes(Path(__file__).read_bytes()),
            "prototype changed")
    original = Path(manifest["input_path"]).read_bytes()
    require(sha256_bytes(original) == manifest["input_hash"], "input changed")
    request, metrics = inline_current_sources(json.loads(original))
    require((root / "request.json").read_bytes() == wire(request), "prototype request changed")
    require(manifest == {
        **metrics, "input_path": manifest["input_path"], "input_hash": manifest["input_hash"],
        "prototype_hash": sha256_bytes(wire(request)),
        "implementation_hash": manifest["implementation_hash"],
    }, "manifest changed")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--input-request", type=Path, required=True)
    prepare_parser.add_argument("--input-hash", required=True)
    prepare_parser.add_argument("--output-root", type=Path, required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.input_request, args.input_hash, args.output_root)
              if args.mode == "prepare" else validate(args.root))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
