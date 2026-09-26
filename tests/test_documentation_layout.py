from __future__ import annotations

import hashlib
import json
import re

from patchloop.runtime import repository_root

HUMAN_DOCS = {
    "README.md",
    "current-status.md",
    "product.md",
    "operations.md",
    "evidence.md",
}
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CURRENT_DOC_BYTE_LIMITS = {
    "README.md": 6_000,
    "AGENTS.md": 8_000,
    "docs/README.md": 4_000,
    "docs/current-status.md": 12_000,
    "docs/product.md": 12_000,
    "docs/operations.md": 16_000,
    "docs/evidence.md": 8_000,
    ".agent/guide.md": 16_000,
    "docs/history/README.md": 6_000,
}


def test_visible_docs_are_small_and_human_facing() -> None:
    root = repository_root()
    docs = root / "docs"
    assert {path.name for path in docs.iterdir() if path.is_file()} == HUMAN_DOCS

    readme = (root / "README.md").read_text(encoding="utf-8")
    for name in HUMAN_DOCS - {"README.md"}:
        assert f"docs/{name}" in readme


def test_agent_detail_is_hidden_but_discoverable() -> None:
    root = repository_root()
    guide = root / ".agent" / "guide.md"
    assert guide.is_file()
    assert ".agent/guide.md" in (root / "AGENTS.md").read_text(encoding="utf-8")


def test_current_guidance_has_bounded_read_cost() -> None:
    root = repository_root()
    oversized = {
        path: (root / path).stat().st_size
        for path, limit in CURRENT_DOC_BYTE_LIMITS.items()
        if (root / path).stat().st_size > limit
    }
    assert oversized == {}, "Move historical detail out of current guidance"


def test_pre_split_documentation_is_preserved_exactly() -> None:
    snapshot_root = repository_root() / "docs" / "history" / "2026-09-26-context-split"
    manifest = json.loads((snapshot_root / "manifest.json").read_text(encoding="utf-8"))
    assert {entry["original_path"] for entry in manifest["entries"]} == {
        "docs/current-status.md",
        ".agent/guide.md",
        "docs/evidence.md",
        "docs/operations.md",
        "docs/product.md",
    }
    for entry in manifest["entries"]:
        content = (snapshot_root / entry["snapshot_path"]).read_bytes()
        assert len(content) == entry["bytes"], entry["original_path"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"], entry["original_path"]


def test_current_local_markdown_links_resolve() -> None:
    root = repository_root()
    sources = [
        root / "README.md",
        root / "AGENTS.md",
        root / ".agent" / "guide.md",
        root / "data" / "STRESS_SENTINELS.md",
        root / "docs" / "history" / "README.md",
        *(root / "docs" / name for name in HUMAN_DOCS),
    ]
    failures: list[str] = []
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK.findall(text):
            if raw_target.startswith(("http://", "https://", "#")):
                continue
            target_text = raw_target.split("#", 1)[0]
            target = (source.parent / target_text).resolve()
            if not target.exists():
                failures.append(f"{source.relative_to(root)} -> {raw_target}")
    assert failures == []
