"""Stage only the static walkthrough, with source links bound to a Git commit."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output == root or output.is_relative_to(root):
        parser.error("Site output must be outside the source checkout")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SystemExit("Expected a full Git commit identity")
    output.mkdir(parents=True, exist_ok=False)
    source = root / "docs" / "showcase"
    html = (source / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        "https://github.com/woojune511/patchloop-agent/blob/main/",
        f"https://github.com/woojune511/patchloop-agent/blob/{revision}/",
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(source / "styles.css", output / "styles.css")
    (output / ".nojekyll").touch()
    print(f"Staged 3 static files at {output}; source revision {revision}")


if __name__ == "__main__":
    main()
