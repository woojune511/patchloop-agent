"""Static diff policy checks."""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from patchloop.contracts import TaskConstraints
from patchloop.deadline import ExecutionDeadline
from patchloop.git_execution import run_git
from patchloop.repository import DiffSummary

DEPENDENCY_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
}


@dataclass
class PolicyOutcome:
    passed: bool
    violations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    if pattern == "**":
        return True
    return fnmatch.fnmatchcase(path, pattern) or PurePosixPath(path).match(pattern)


def verify_scope(summary: DiffSummary, constraints: TaskConstraints) -> PolicyOutcome:
    violations: list[str] = []
    typed_violations: list[dict] = []
    if summary.untracked_files:
        violations.append("untracked files are unsupported: " + ", ".join(summary.untracked_files))
        typed_violations.append(
            {
                "code": "untracked_files",
                "paths": summary.untracked_files,
            }
        )
    for path in summary.changed_files:
        if not any(_matches(path, pattern) for pattern in constraints.allowed_paths):
            violations.append(f"path is outside allowed_paths: {path}")
            typed_violations.append({"code": "path_outside_allowed", "path": path})
        if any(_matches(path, pattern) for pattern in constraints.forbidden_paths):
            violations.append(f"path matches forbidden_paths: {path}")
            typed_violations.append({"code": "path_forbidden", "path": path})
    if len(summary.changed_files) > constraints.max_changed_files:
        changed_file_count = len(summary.changed_files)
        violations.append(
            f"changed file count {changed_file_count} exceeds {constraints.max_changed_files}"
        )
        typed_violations.append(
            {
                "code": "max_changed_files",
                "actual": changed_file_count,
                "limit": constraints.max_changed_files,
                "over_by": changed_file_count - constraints.max_changed_files,
            }
        )
    if summary.diff_lines > constraints.max_diff_lines:
        violations.append(
            f"diff line count {summary.diff_lines} exceeds {constraints.max_diff_lines}"
        )
        typed_violations.append(
            {
                "code": "max_diff_lines",
                "actual": summary.diff_lines,
                "limit": constraints.max_diff_lines,
                "over_by": summary.diff_lines - constraints.max_diff_lines,
            }
        )
    return PolicyOutcome(
        passed=not violations,
        violations=violations,
        details={
            "changed_files": summary.changed_files,
            "untracked_files": summary.untracked_files,
            "changed_file_count": len(summary.changed_files),
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
            "diff_lines": summary.diff_lines,
            "typed_violations": typed_violations,
        },
    )


def verify_dependencies(summary: DiffSummary, constraints: TaskConstraints) -> PolicyOutcome:
    changed = [
        path for path in summary.changed_files if PurePosixPath(path).name in DEPENDENCY_FILES
    ]
    violations = []
    if changed and not constraints.dependency_changes_allowed:
        violations.append(f"dependency files changed: {', '.join(changed)}")
    return PolicyOutcome(not violations, violations, {"dependency_files": changed})


def _is_test_path(path: str) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/"))
    directories = normalized.parts[:-1]
    filename = normalized.name
    return (
        any(
            part in {"test", "tests", ".patchloop-hidden"} or part.endswith("_tests")
            for part in directories
        )
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    )


def verify_test_tampering(summary: DiffSummary) -> PolicyOutcome:
    changed = [path for path in summary.changed_files if _is_test_path(path)]
    violations = [f"test files changed: {', '.join(changed)}"] if changed else []
    return PolicyOutcome(not violations, violations, {"test_files": changed})


def _signature_map(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    signatures = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            signatures[node.name] = ast.dump(node.args, include_attributes=False)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            signatures[node.name] = "class"
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not child.name.startswith("_"):
                    signatures[f"{node.name}.{child.name}"] = ast.dump(
                        child.args, include_attributes=False
                    )
    return signatures


def verify_public_api(
    summary: DiffSummary, constraints: TaskConstraints, workspace: Path,
    *, deadline: ExecutionDeadline | None = None,
) -> PolicyOutcome:
    if constraints.public_api_changes_allowed:
        return PolicyOutcome(True, [], {"changes_allowed": True, "changed_symbols": []})
    changed_symbols = []
    violations = []
    for path in summary.changed_files:
        if not path.endswith(".py") or path.startswith("tests/"):
            continue
        base = run_git(workspace, "show", f"HEAD:{path}", check=False, deadline=deadline)
        target = workspace / path
        if base.returncode != 0 or not target.exists():
            violations.append(f"public Python module added or removed: {path}")
            continue
        try:
            before = _signature_map(base.stdout)
            after = _signature_map(target.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            violations.append(f"cannot inspect public API for {path}: {exc}")
            continue
        for symbol in sorted(set(before) | set(after)):
            if before.get(symbol) != after.get(symbol):
                changed_symbols.append(f"{path}:{symbol}")
    if changed_symbols:
        violations.append(f"public API changed: {', '.join(changed_symbols)}")
    return PolicyOutcome(
        not violations,
        violations,
        {"changes_allowed": False, "changed_symbols": changed_symbols},
    )
