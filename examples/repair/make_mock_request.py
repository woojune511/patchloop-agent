"""Create a public-only, provider-free CLI example outside the repository."""

import json
import sys
from pathlib import Path

# Allow direct execution from a source checkout without installing packages.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from patchloop.git_execution import run_git  # noqa: E402
from patchloop.repository import WorkspaceManager  # noqa: E402
from patchloop.runtime import repository_root  # noqa: E402

root = Path(sys.argv[1]).resolve()
repo = repository_root()
if root == repo or root.is_relative_to(repo):
    raise SystemExit("Example output must be outside PatchLoop")
root.mkdir(parents=True, exist_ok=False)
public = yaml.safe_load((repo / "tasks/smoke/csv-quoted-newline/public.yaml").read_text())
source = WorkspaceManager(repo / "fixtures/repositories", root / "sources").create(
    "example", public["repository"]["url"], public["repository"]["base_commit"],
)
public.update(schema_version="repair-task-v1", split="repair")
public["repository"].update(url="https://example.invalid/public-csv.git",
                            base_commit=run_git(source, "rev-parse", "HEAD").stdout.strip())
(root / "public.yaml").write_text(yaml.safe_dump(public), encoding="utf-8")
(root / "request.json").write_text(json.dumps({
    "task": "public.yaml", "source": str(source), "state_root": str(root / "state"),
    "provider": "mock", "model": "mock-dev", "sandbox": {"backend": "local"},
}, indent=2), encoding="utf-8")
print(root / "request.json")
