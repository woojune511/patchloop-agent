"""PatchLoop command-line interface."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import MemoryCondition
from patchloop.errors import ContractError, PatchLoopError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest, repository_root, runtime_root
from patchloop.sandbox import DockerSandbox, LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine

app = typer.Typer(no_args_is_help=True, help="Trace-driven coding agent reliability harness")
task_app = typer.Typer(no_args_is_help=True, help="Validate and inspect task packages")
memory_app = typer.Typer(no_args_is_help=True, help="Build and freeze failure-memory indexes")
github_app = typer.Typer(no_args_is_help=True, help="Host-only GitHub issue and Draft PR adapter")
dataset_app = typer.Typer(no_args_is_help=True, help="Audit dataset split completeness")
app.add_typer(task_app, name="task")
app.add_typer(memory_app, name="memory")
app.add_typer(github_app, name="github")
app.add_typer(dataset_app, name="dataset")


def _emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _guarded(operation: Callable[[], object]) -> None:
    try:
        value = operation()
    except PatchLoopError as exc:
        _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        raise typer.Exit(code=1) from exc
    _emit(value)


@app.command()
def doctor() -> None:
    """Check local prerequisites without mutating external configuration."""
    uv = shutil.which("uv")
    git = shutil.which("git")
    gh = shutil.which("gh")
    docker_cli = DockerSandbox.cli_path()
    docker_server = DockerSandbox.available()
    docker_sandbox = DockerSandbox()
    docker_image = docker_sandbox.image_identity() if docker_server else None
    wsl = shutil.which("wsl") or shutil.which("wsl.exe")
    wsl_distributions: list[str] = []
    if wsl:
        try:
            wsl_status = subprocess.run(
                [wsl, "--list", "--quiet"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if wsl_status.returncode == 0:
                wsl_distributions = [
                    line.replace("\x00", "").strip()
                    for line in wsl_status.stdout.splitlines()
                    if line.replace("\x00", "").strip()
                ]
        except subprocess.TimeoutExpired:
            wsl_distributions = []
    gh_authenticated = False
    if gh:
        gh_status = subprocess.run(
            [gh, "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        gh_authenticated = gh_status.returncode == 0
    checks = {
        "python": {
            "ok": True,
            "version": subprocess.check_output(
                [shutil.which("python") or "python", "--version"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip(),
        },
        "uv": {"ok": bool(uv), "path": uv},
        "git": {"ok": bool(git), "path": git},
        "github_cli": {"ok": bool(gh), "path": gh, "authenticated": gh_authenticated},
        "wsl": {
            "ok": bool(wsl_distributions),
            "path": wsl,
            "distributions": wsl_distributions,
        },
        "docker_cli": {"ok": bool(docker_cli), "path": docker_cli},
        "docker_server": {"ok": docker_server},
        "docker_image": {
            "ok": bool(docker_image),
            "name": docker_sandbox.image,
            "identity": docker_image,
        },
    }
    checks["official_evaluation_ready"] = {"ok": docker_server and bool(docker_image) and bool(git)}
    _emit(checks)
    if not checks["official_evaluation_ready"]["ok"]:
        raise typer.Exit(code=2)


@task_app.command("validate")
def validate_task(task_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Validate public/private identity, schema, paths, and reference artifact."""
    try:
        package = load_task_package(task_dir)
    except PatchLoopError as exc:
        _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        raise typer.Exit(code=1) from exc
    _emit(
        {
            "ok": True,
            "task_id": package.public.task_id,
            "task_version": package.public.task_version,
            "split": package.public.split,
            "public_spec_hash": package.public_spec_hash,
            "private_spec_hash": package.private_spec_hash,
        }
    )


@dataset_app.command("audit")
def dataset_audit() -> None:
    """Audit calibration, research-role admission, and stress-lane readiness."""
    from patchloop.dataset import audit_dataset

    result = audit_dataset()
    _emit(result)
    if not result["complete"]:
        raise typer.Exit(code=1)


@app.command("eval-task")
def eval_task(
    task_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    patch: Annotated[Path, typer.Option("--patch", exists=True, dir_okay=False)],
    backend: Annotated[str, typer.Option("--backend", help="local or docker")] = "docker",
) -> None:
    """Apply a submitted patch to a clean checkout and run isolated verification."""
    try:
        package = load_task_package(task_dir)
        if backend not in {"local", "docker"}:
            raise typer.BadParameter("backend must be local or docker")
        evaluator_image = (
            package.environment.evaluator_image if package.environment is not None else None
        )
        sandbox = (
            LocalSandbox()
            if backend == "local"
            else DockerSandbox(evaluator_image)
            if evaluator_image
            else DockerSandbox()
        )
        if backend == "docker" and not DockerSandbox.available():
            _emit({"ok": False, "error": "DOCKER_UNAVAILABLE"})
            raise typer.Exit(code=2)
        if backend == "docker" and not sandbox.image_identity():
            _emit(
                {
                    "ok": False,
                    "error": "DOCKER_IMAGE_UNAVAILABLE",
                    "image": sandbox.image,
                }
            )
            raise typer.Exit(code=2)
        root = runtime_root()
        image_identity = sandbox.image_identity() if isinstance(sandbox, DockerSandbox) else None
        if (
            package.environment is not None
            and backend == "docker"
            and image_identity != package.environment.image_digest
        ):
            raise ContractError(
                "task evaluator image identity does not match environment.yaml: "
                f"{image_identity} != {package.environment.image_digest}"
            )
        manifest = build_manifest(
            package,
            sandbox_backend=backend,
            evaluator_image_digest=image_identity,
        )
        manager = WorkspaceManager(
            repository_root() / "fixtures" / "repositories", root / "workspaces"
        )
        engine = EvaluationEngine(manager, sandbox, ArtifactStore(root / "artifacts"))
        result = engine.evaluate(task_dir, patch, manifest)
    except PatchLoopError as exc:
        _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        raise typer.Exit(code=1) from exc
    _emit(result.model_dump(mode="json"))
    if not result.scope_compliant_success:
        raise typer.Exit(code=1)


@app.command()
def run(
    task: Annotated[Path, typer.Option("--task", exists=True, dir_okay=False)],
    model: Annotated[str, typer.Option("--model")] = "mock",
    memory: Annotated[MemoryCondition, typer.Option("--memory")] = MemoryCondition.NO_MEMORY,
) -> None:
    """Run the durable constrained coding agent and hidden evaluator."""
    from patchloop.agent.runner import run_from_cli

    _guarded(lambda: run_from_cli(task, model=model, memory_condition=memory))


@app.command()
def resume(run_id: Annotated[str, typer.Option("--run-id")]) -> None:
    """Resume a suspended run after checkpoint/worktree reconciliation."""
    from patchloop.agent.runner import resume_from_cli

    _guarded(lambda: resume_from_cli(run_id))


@app.command("inject-fault")
def inject_fault(
    run_id: Annotated[str, typer.Option("--run")],
    fault: Annotated[str, typer.Option("--fault")],
) -> None:
    """Create and execute a new fault-derived run without changing the baseline."""
    from patchloop.evals.faults import clone_with_fault

    _guarded(lambda: clone_with_fault(run_id, fault))


@app.command()
def evaluate(
    suite: Annotated[Path, typer.Option("--suite", exists=True, dir_okay=False)],
) -> None:
    """Execute a seeded experiment suite after all freeze gates pass."""
    from patchloop.evals.runner import evaluate_suite

    _guarded(lambda: evaluate_suite(suite))


@app.command()
def report(
    experiment: Annotated[str, typer.Option("--experiment")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Reaggregate raw runs into a portable JSON/CSV/HTML evidence bundle."""
    from patchloop.evals.report import build_report

    _guarded(lambda: build_report(experiment, output))


@memory_app.command("build")
def memory_build(
    split: Annotated[str, typer.Option("--split")] = "dev-train",
    embedding_revision: Annotated[str | None, typer.Option("--embedding-revision")] = None,
) -> None:
    """Build an unfrozen index from reviewed dev-train failures only."""
    from patchloop.memory.store import build_index_from_failures

    _guarded(lambda: build_index_from_failures(split, embedding_revision))


@memory_app.command("review")
def memory_review(
    failure_id: Annotated[str, typer.Option("--failure-id")],
    approve: Annotated[bool, typer.Option("--approve/--reject")],
    split: Annotated[str, typer.Option("--split")] = "dev-train",
    reviewer: Annotated[str, typer.Option("--reviewer")] = "human",
) -> None:
    """Record an explicit human approval or rejection before memory construction."""
    from patchloop.memory.store import review_failure

    _guarded(lambda: review_failure(failure_id, split=split, approve=approve, reviewer=reviewer))


@memory_app.command("freeze")
def memory_freeze(
    index_id: Annotated[str, typer.Option("--index")],
    embedding_revision: Annotated[str | None, typer.Option("--embedding-revision")] = None,
) -> None:
    """Freeze an index after recording the exact embedding revision."""
    from patchloop.memory.store import freeze_index

    _guarded(lambda: freeze_index(index_id, embedding_revision))


@github_app.command("import-issue")
def github_import_issue(
    issue_url: Annotated[str, typer.Argument()],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Import public GitHub Issue metadata as a task-authoring draft."""
    from patchloop.github_adapter import import_issue

    _guarded(lambda: import_issue(issue_url, output))


@github_app.command("draft-pr")
def github_draft_pr(
    run_id: Annotated[str, typer.Option("--run-id")],
    repo_dir: Annotated[Path, typer.Option("--repo", exists=True, file_okay=False)],
    title: Annotated[str | None, typer.Option("--title")] = None,
) -> None:
    """Create a Draft PR only for a completed scope-compliant run."""
    from patchloop.github_adapter import create_draft_pr

    _guarded(lambda: create_draft_pr(run_id, repo_dir, title))


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Serve the read-only trace viewer."""
    import uvicorn

    uvicorn.run("patchloop.web:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
