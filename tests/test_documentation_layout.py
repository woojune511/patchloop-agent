from __future__ import annotations

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


def test_current_local_markdown_links_resolve() -> None:
    root = repository_root()
    sources = [
        root / "README.md",
        root / "AGENTS.md",
        root / ".agent" / "guide.md",
        root / "data" / "STRESS_SENTINELS.md",
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
