"""PatchLoop command-line interface."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


def _with_exact_env_file(
    env_file: Path | None,
    operation: Callable[[], object],
) -> object:
    if env_file is None:
        return operation()
    from patchloop.environment import exact_openai_api_key_environment

    with exact_openai_api_key_environment(env_file):
        return operation()


def _exact_env_file_credential_present(env_file: Path | None) -> bool | None:
    """Validate a credential file for preflight without exporting its value."""

    if env_file is None:
        return None
    from patchloop.environment import exact_openai_api_key_present

    return exact_openai_api_key_present(env_file)


_TRANSIENT_PREFLIGHT_BLOCKERS = {
    "DOCKER_UNAVAILABLE",
    "DOCKER_IMAGE_UNAVAILABLE",
    "DOCKER_NOT_READY",
    "PROCESS_LAUNCH_ERROR",
    "PROCESS_TIMEOUT",
}


def _bounded_preflight(
    operation: Callable[[], dict[str, object]],
    *,
    max_attempts: int,
) -> dict[str, object]:
    """Retry only transient local readiness failures and stop at a candidate."""

    attempts: list[dict[str, object]] = []
    result: dict[str, object] = {}
    for attempt_number in range(1, max_attempts + 1):
        try:
            result = operation()
        except subprocess.TimeoutExpired:
            result = {
                "execution_candidate_ready": False,
                "ready": False,
                "blockers": [
                    {"code": "PROCESS_TIMEOUT", "message": "local preflight process timed out"}
                ],
            }
        except FileNotFoundError:
            result = {
                "execution_candidate_ready": False,
                "ready": False,
                "blockers": [
                    {
                        "code": "PROCESS_LAUNCH_ERROR",
                        "message": "local preflight process could not be launched",
                    }
                ],
            }
        raw_blockers = result.get("blockers")
        blockers = raw_blockers if isinstance(raw_blockers, list) else []
        blocker_codes = sorted(
            str(blocker.get("code"))
            for blocker in blockers
            if isinstance(blocker, dict) and isinstance(blocker.get("code"), str)
        )
        candidate_ready = result.get("execution_candidate_ready") is True
        transient_only = bool(blocker_codes) and all(
            code in _TRANSIENT_PREFLIGHT_BLOCKERS for code in blocker_codes
        )
        attempts.append(
            {
                "attempt": attempt_number,
                "execution_candidate_ready": candidate_ready,
                "blocker_codes": blocker_codes,
                "transient_only": transient_only,
            }
        )
        if candidate_ready or not transient_only:
            break
    return {
        **result,
        "preflight_attempts": attempts,
        "preflight_attempt_count": len(attempts),
    }


def _decode_probe_output(output: bytes) -> str:
    """Decode Windows CLI output without relying on the active code page."""
    if not output:
        return ""
    if output.startswith((b"\xff\xfe", b"\xfe\xff")):
        return output.decode("utf-16", errors="replace")
    if b"\x00" in output:
        return output.decode("utf-16-le", errors="replace")
    return output.decode("utf-8", errors="replace")


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
                timeout=10,
                check=False,
            )
            if wsl_status.returncode == 0:
                wsl_distributions = [
                    line.strip()
                    for line in _decode_probe_output(wsl_status.stdout).splitlines()
                    if line.strip()
                ]
        except (OSError, subprocess.TimeoutExpired):
            wsl_distributions = []
    gh_authenticated = False
    if gh:
        try:
            gh_status = subprocess.run(
                [gh, "auth", "status"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            gh_authenticated = gh_status.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            gh_authenticated = False
    checks = {
        "python": {
            "ok": True,
            "version": f"Python {sys.version.split()[0]}",
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
    self_validation: Annotated[
        bool,
        typer.Option(
            "--self-validation",
            help=("Opt in to tool v3/context v6 temporary probes and structured final review."),
        ),
    ] = False,
) -> None:
    """Run the durable constrained coding agent and hidden evaluator."""
    from patchloop.agent.runner import run_from_cli

    def operation() -> object:
        if model != "mock" and not model.startswith("replay:"):
            raise ContractError(
                "direct live runs are disabled; use `patchloop evaluate --suite ...` "
                "with an approved experiment-v2 execution hash"
            )
        return run_from_cli(
            task,
            model=model,
            memory_condition=memory,
            self_validation=self_validation,
        )

    _guarded(operation)


@app.command()
def resume(run_id: Annotated[str, typer.Option("--run-id")]) -> None:
    """Resume a suspended or abandoned RUNNING run after reconciliation."""
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
    preflight_only: Annotated[
        bool,
        typer.Option(
            "--preflight-only",
            help="Inspect all live gates without constructing an agent or making API calls.",
        ),
    ] = False,
    approve_live_cost: Annotated[
        bool,
        typer.Option(
            "--approve-live-cost",
            help="Authorize paid execution for this invocation only.",
        ),
    ] = False,
    approved_execution_hash: Annotated[
        str | None,
        typer.Option(
            "--approved-execution-hash",
            help="Exact execution hash printed by a clean preflight.",
        ),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            exists=True,
            dir_okay=False,
            help=(
                "Temporarily load a file containing only OPENAI_API_KEY; "
                "the value is never emitted."
            ),
        ),
    ] = None,
) -> None:
    """Execute a seeded experiment suite after all freeze gates pass."""
    from patchloop.evals.runner import evaluate_suite, preflight_suite

    if preflight_only:
        try:
            result = preflight_suite(
                suite,
                approve_live_cost=approve_live_cost,
                approved_execution_hash=approved_execution_hash,
                credential_present=_exact_env_file_credential_present(env_file),
            )
        except PatchLoopError as exc:
            _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
            raise typer.Exit(code=1) from exc
        _emit(result)
        if not result["ready"]:
            raise typer.Exit(code=2)
        return
    _guarded(
        lambda: _with_exact_env_file(
            env_file,
            lambda: evaluate_suite(
                suite,
                approve_live_cost=approve_live_cost,
                approved_execution_hash=approved_execution_hash,
            ),
        )
    )


@app.command("preflight")
def preflight_command(
    suite: Annotated[Path, typer.Option("--suite", exists=True, dir_okay=False)],
    env_file: Annotated[
        Path,
        typer.Option(
            "--env-file",
            exists=True,
            dir_okay=False,
            help=(
                "Credential file containing only OPENAI_API_KEY. "
                "Its value is never emitted."
            ),
        ),
    ] = Path(".env"),
    max_attempts: Annotated[
        int,
        typer.Option(
            "--max-attempts",
            min=1,
            max=3,
            help="Retry transient local readiness failures up to three times.",
        ),
    ] = 1,
) -> None:
    """Build a reusable execution candidate without provider or agent calls."""

    from patchloop.evals.runner import preflight_suite

    try:
        credential_present = _exact_env_file_credential_present(env_file)
        result = _bounded_preflight(
            lambda: preflight_suite(
                suite,
                credential_present=credential_present,
            ),
            max_attempts=max_attempts,
        )
    except PatchLoopError as exc:
        _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        raise typer.Exit(code=1) from exc
    _emit(result)
    if not result["execution_candidate_ready"]:
        raise typer.Exit(code=2)


@app.command()
def report(
    experiment: Annotated[str, typer.Option("--experiment")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Reaggregate raw runs into a portable JSON/CSV/HTML evidence bundle."""
    from patchloop.evals.report import build_report

    _guarded(lambda: build_report(experiment, output))


@app.command("budget")
def budget_diagnose(
    experiment: Annotated[
        str,
        typer.Option(
            "--experiment",
            help="Experiment ID or immutable experiment-result JSON path.",
        ),
    ],
) -> None:
    """Derive read-only per-run budget pressure from durable evidence."""
    from patchloop.evals.budget import derive_experiment_budget_pressure
    from patchloop.state import StateStore

    def operation() -> object:
        requested = Path(experiment)
        source = (
            requested
            if requested.is_file()
            else runtime_root() / "experiments" / f"{experiment}.json"
        )
        if not source.is_file():
            raise ContractError(f"experiment result is unavailable: {experiment}")
        try:
            return derive_experiment_budget_pressure(
                source,
                StateStore(runtime_root() / "state.sqlite3"),
            )
        except (OSError, ValueError) as exc:
            raise ContractError(f"budget pressure evidence is invalid: {exc}") from exc

    _guarded(operation)


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


@memory_app.command("validate-review")
def memory_validate_review(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Validate a structured review proposal without approving or indexing it."""
    from patchloop.memory.review import validate_review_proposal

    _guarded(lambda: validate_review_proposal(proposal_path))


@memory_app.command("validate-d099-review")
def memory_validate_d099_review(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
    require_raw_evidence: Annotated[
        bool,
        typer.Option("--require-raw-evidence"),
    ] = False,
    runtime: Annotated[
        Path | None,
        typer.Option("--runtime-root", file_okay=False, dir_okay=True),
    ] = None,
) -> None:
    """Validate the non-admitting D-099 public review proposal."""
    from patchloop.memory.d099_review import validate_d099_review_proposal

    _guarded(
        lambda: validate_d099_review_proposal(
            proposal_path,
            root=runtime,
            require_raw_evidence=require_raw_evidence,
        )
    )


@memory_app.command("d100-status")
def memory_d100_status(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Report D-100 mechanism readiness without recording a human decision."""
    from patchloop.memory.d100_group_admission import d100_mechanism_status

    _guarded(lambda: d100_mechanism_status(proposal_path))


@memory_app.command("validate-d100-source-gate")
def memory_validate_d100_source_gate(
    source_gate_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Validate the mechanism-only D-100 portable source gate."""
    from patchloop.memory.d100_group_admission import validate_d100_source_gate

    _guarded(lambda: validate_d100_source_gate(source_gate_path))


@memory_app.command("record-d100-decision")
def memory_record_d100_decision(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
    journal: Annotated[Path, typer.Option("--journal", file_okay=True, dir_okay=False)],
    group: Annotated[str, typer.Option("--group")],
    decision: Annotated[str, typer.Option("--decision")],
    reviewer_kind: Annotated[str, typer.Option("--reviewer-kind")],
    reviewer: Annotated[str, typer.Option("--reviewer")],
    rationale: Annotated[str, typer.Option("--rationale")],
    action_id: Annotated[str, typer.Option("--action-id")],
    expected_tail: Annotated[str, typer.Option("--expected-tail")],
) -> None:
    """Append one explicit self-attested group decision with tail-CAS protection."""
    from patchloop.memory.d100_group_admission import record_d100_group_decision

    tail = None if expected_tail == "none" else expected_tail
    _guarded(
        lambda: record_d100_group_decision(
            proposal_path,
            journal,
            semantic_group_id=group,
            decision=decision,
            reviewer_kind=reviewer_kind,
            reviewer=reviewer,
            rationale=rationale,
            action_id=action_id,
            expected_tail=tail,
        )
    )


@memory_app.command("validate-d100-decisions")
def memory_validate_d100_decisions(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
    journal: Annotated[
        Path,
        typer.Option(
            "--journal",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    expected_head: Annotated[str | None, typer.Option("--expected-head")] = None,
    expected_record_count: Annotated[
        int | None,
        typer.Option("--expected-record-count", min=1),
    ] = None,
) -> None:
    """Validate a D-100 group-decision chain without writing state."""
    from patchloop.memory.d100_group_admission import validate_d100_decision_journal

    _guarded(
        lambda: validate_d100_decision_journal(
            proposal_path,
            journal,
            expected_head=expected_head,
            expected_record_count=expected_record_count,
        )
    )


@memory_app.command("preview-d100-entries")
def memory_preview_d100_entries(
    proposal_path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True),
    ],
    journal: Annotated[
        Path,
        typer.Option(
            "--journal",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    expected_head: Annotated[str | None, typer.Option("--expected-head")] = None,
    expected_record_count: Annotated[
        int | None,
        typer.Option("--expected-record-count", min=1),
    ] = None,
) -> None:
    """Project complete decisions into non-indexed MemoryEntry templates."""
    from patchloop.memory.d100_group_admission import project_d100_memory_entry_preview

    _guarded(
        lambda: project_d100_memory_entry_preview(
            proposal_path,
            journal,
            expected_head=expected_head,
            expected_record_count=expected_record_count,
        )
    )


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
