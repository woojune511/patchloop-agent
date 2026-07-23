"""Host-only GitHub CLI adapter; credentials never enter run containers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from patchloop.errors import ContractError
from patchloop.runtime import runtime_root
from patchloop.state import StateStore


def _gh(*args: str, cwd: str | Path | None = None) -> str:
    executable = shutil.which("gh")
    if not executable:
        raise ContractError("gh CLI is not installed")
    result = subprocess.run(
        [executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"gh command failed: {result.stderr.strip()}")
    return result.stdout


def import_issue(issue_url: str, output: str | Path) -> dict:
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url)
    if not match:
        raise ContractError("issue URL must be a canonical GitHub issue URL")
    owner, repo, number = match.groups()
    issue = json.loads(_gh("issue", "view", issue_url, "--json", "number,title,body,url"))
    repository = json.loads(
        _gh("repo", "view", f"{owner}/{repo}", "--json", "url,defaultBranchRef")
    )
    branch = repository["defaultBranchRef"]["name"]
    commit = _gh("api", f"repos/{owner}/{repo}/commits/{branch}", "--jq", ".sha").strip()
    task_id = re.sub(r"[^a-z0-9]+", "-", f"{repo}-{number}-{issue['title'].lower()}").strip("-")
    payload = {
        "schema_version": "task-public-v1",
        "task_id": task_id[:80],
        "task_version": 1,
        "split": "dev-validation",
        "repository": {
            "url": repository["url"],
            "base_commit": commit,
            "language": "python",
        },
        "issue": {"title": issue["title"], "description": issue.get("body") or issue["title"]},
        "constraints": {
            "allowed_paths": ["**"],
            "forbidden_paths": [".github/**"],
            "max_changed_files": 4,
            "max_diff_lines": 120,
            "dependency_changes_allowed": False,
            "public_api_changes_allowed": False,
        },
        "visible_checks": [],
        "tags": ["github-import", f"issue-{number}"],
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return {"task_id": payload["task_id"], "path": str(destination), "source": issue["url"]}


def create_draft_pr(run_id: str, repo_dir: str | Path, title: str | None = None) -> dict:
    state = StateStore(runtime_root() / "state.sqlite3")
    rows = [row for row in state.list_runs() if row["run_id"] == run_id]
    if not rows or not rows[0]["result"]:
        raise ContractError("run has no evaluator result")
    result = rows[0]["result"]
    if not result["scope_compliant_success"]:
        raise ContractError("Draft PR creation requires scope-compliant evaluator success")
    manifest = rows[0]["manifest"]
    pr_title = title or f"Fix {manifest['task_id']} via PatchLoop"
    body = (
        f"PatchLoop run: `{run_id}`\n\n"
        f"- SCRR: `{result['scope_compliant_success']}`\n"
        f"- hidden tests: `{result['verdicts']['hidden_tests']}`\n"
        f"- regression tests: `{result['verdicts']['regression_tests']}`\n"
        f"- scope policy: `{result['verdicts']['scope_policy']}`\n"
    )
    url = _gh("pr", "create", "--draft", "--title", pr_title, "--body", body, cwd=repo_dir).strip()
    return {"run_id": run_id, "draft": True, "url": url}
