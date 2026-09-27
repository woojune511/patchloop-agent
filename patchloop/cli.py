"""PatchLoop's small active command surface."""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import ValidationError

from patchloop.dev.cost import (
    DEFAULT_OUTPUT_CEILING,
    MAX_OUTPUT_CEILING,
    MINIMUM_OUTPUT_CEILING,
)
from patchloop.errors import ContractError, PatchLoopError
from patchloop.task_loader import load_task_package

app = typer.Typer(no_args_is_help=True, help="PatchLoop mutable development harness")
task_app = typer.Typer(no_args_is_help=True, help="Validate tasks and prepare audited sources")
app.add_typer(task_app, name="task")


def _emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _guarded(operation: Callable[[], object]) -> None:
    try:
        value = operation()
    except ValidationError as exc:
        error = ContractError(str(exc))
        _emit({"ok": False, "error": error.code, "message": str(error), "details": {}})
        raise typer.Exit(code=1) from exc
    except PatchLoopError as exc:
        _emit({"ok": False, "error": exc.code, "message": str(exc), "details": exc.details})
        raise typer.Exit(code=1) from exc
    _emit(value)


def _parse_cost(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError("--max-cost-usd must be a decimal") from exc
    if not parsed.is_finite():
        raise ContractError("--max-cost-usd must be finite")
    return parsed


@app.command()
def dev(
    provider: Annotated[Literal["mock", "openai"], typer.Option("--provider")],
    task: Annotated[Path, typer.Option("--task", exists=True, dir_okay=False)],
    model: Annotated[str, typer.Option("--model")],
    reasoning_effort: Annotated[
        Literal["none", "low", "medium", "high", "xhigh"],
        typer.Option("--reasoning-effort"),
    ] = "medium",
    max_output_tokens: Annotated[
        int, typer.Option(
            "--max-output-tokens", min=MINIMUM_OUTPUT_CEILING, max=MAX_OUTPUT_CEILING,
            help="Desired output cap per call, including reasoning; cost admission may lower it.",
        ),
    ] = DEFAULT_OUTPUT_CEILING,
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", exists=True, dir_okay=False),
    ] = None,
    max_cost_usd: Annotated[
        str | None,
        typer.Option("--max-cost-usd"),
    ] = None,
    repeat: Annotated[int, typer.Option("--repeat", min=1, max=6)] = 1,
    prepared_source: Annotated[
        Path | None, typer.Option("--prepared-source", help="Use an immutable prepared source.")
    ] = None,
    prepared_probe_dependencies: Annotated[
        Path | None, typer.Option("--prepared-probe-dependencies",
                                  help="Use immutable public wheel dependencies for probes.")
    ] = None,
    enable_probes: Annotated[
        bool, typer.Option("--enable-probes", help="Enable bounded clean-Python diagnostics.")
    ] = False,
    probe_policy: Annotated[
        Literal["none", "cases-v1"],
        typer.Option("--probe-policy", help="Opt-in reusable reference/candidate experiments."),
    ] = "none",
    repair_recheck: Annotated[
        bool, typer.Option(
            "--repair-recheck", help="After a repair, rerun its prior failed public check."
        )
    ] = False,
    repair_inspection_policy: Annotated[
        Literal["protected-v1", "current-failure-v1"],
        typer.Option("--repair-inspection-policy",
                     help="Opt-in use of future check-recovery reserves for failed-diff reads."),
    ] = "protected-v1",
    context_policy: Annotated[
        Literal["append-v1", "native-window-v1", "segmented-v1"],
        typer.Option("--context-policy", help="Opt-in snapshot window or bounded public handoffs."),
    ] = "append-v1",
    segment_boundary_policy: Annotated[
        Literal["result-or-size-v1", "size-only-v1"],
        typer.Option("--segment-boundary-policy", help="Segmented-v1 transition condition."),
    ] = "result-or-size-v1",
    completion_cost_policy: Annotated[
        Literal["per-call-v1", "completion-reserve-v1"],
        typer.Option("--completion-cost-policy",
                     help="Opt-in future-call cost reservation; requires segmented-v1."),
    ] = "per-call-v1",
    planning_policy: Annotated[
        Literal["none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
                "brief-after-source-v1"],
        typer.Option("--planning-policy", help="Public planning; append-v1 or segmented-v1."),
    ] = "none",
    compact_at_input_tokens: Annotated[
        int | None, typer.Option("--compact-at-input-tokens", min=1, max=271_999,
                                 help="Opt-in one compact at this counted-input threshold.")
    ] = None,
    accept_compaction_model_limit_reservation: Annotated[
        bool, typer.Option("--accept-compaction-model-limit-reservation",
                           help="Accept a conditional reservation, not an enforced invoice cap.")
    ] = False,
    resume_run_id: Annotated[
        str | None,
        typer.Option("--resume-run-id"),
    ] = None,
) -> None:
    """Run the unofficial mutable dev-head lane."""

    from patchloop.dev.contracts import DevRunRequest
    from patchloop.dev.runner import run_dev

    _guarded(
        lambda: run_dev(
            DevRunRequest(
                provider=provider,
                task=task,
                model=model,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
                env_file=env_file,
                max_cost_usd=_parse_cost(max_cost_usd),
                repeat=repeat,
                prepared_source=prepared_source,
                prepared_probe_dependencies=prepared_probe_dependencies,
                enable_probes=enable_probes,
                probe_policy=probe_policy,
                repair_recheck=repair_recheck,
                repair_inspection_policy=repair_inspection_policy,
                context_policy=context_policy,
                segment_boundary_policy=segment_boundary_policy,
                completion_cost_policy=completion_cost_policy,
                planning_policy=planning_policy,
                compact_at_input_tokens=compact_at_input_tokens,
                accept_compaction_model_limit_reservation=accept_compaction_model_limit_reservation,
                resume_run_id=resume_run_id,
            )
        )
    )


@task_app.command("validate")
def validate_task(task_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Validate public/private identity, schema, paths, and reference artifact."""

    def operation() -> object:
        package = load_task_package(task_dir)
        return {
            "ok": True,
            "task_id": package.public.task_id,
            "task_version": package.public.task_version,
            "split": package.public.split,
            "public_spec_hash": package.public_spec_hash,
            "private_spec_hash": package.private_spec_hash,
            "task_content_hash": package.task_content_hash,
        }

    _guarded(operation)


@task_app.command("prepare-source")
def prepare_task_source(
    task_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Option("--output", help="New directory outside the repository")],
) -> None:
    """Fetch an audited base once; publish a descriptor for offline independent clones."""
    from patchloop.deadline import ExecutionDeadline
    from patchloop.prepared_source import admission_hash, prepare_source
    from patchloop.runtime import repository_root

    def operation() -> object:
        package = load_task_package(task_dir)
        path = prepare_source(
            repository_url=package.public.repository.url,
            base_commit=package.public.repository.base_commit, output=output,
            fixture_root=repository_root() / "fixtures/repositories",
            deadline=ExecutionDeadline.from_remaining(120),
        )
        return {"ok": True, "prepared_source": str(path), "content_hash": admission_hash(path)}

    _guarded(operation)


@task_app.command("prepare-probe-dependencies")
def prepare_task_probe_dependencies(
    task_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    prepared_source: Annotated[Path, typer.Option("--prepared-source")],
    output: Annotated[Path, typer.Option("--output")],
    wheel_lock: Annotated[Path | None, typer.Option("--wheel-lock")] = None,
    resolve: Annotated[bool, typer.Option("--resolve")] = False,
    group: Annotated[list[str] | None, typer.Option("--group")] = None,
    extra: Annotated[list[str] | None, typer.Option("--extra")] = None,
    source_root: Annotated[list[str] | None, typer.Option("--source-root")] = None,
    generated_wheel_receipt: Annotated[Path | None, typer.Option(
        "--generated-wheel-receipt",
    )] = None,
    generated_wheel_receipt_hash: Annotated[str | None, typer.Option(
        "--generated-wheel-receipt-hash",
    )] = None,
    select_dependency: Annotated[list[str] | None, typer.Option(
        "--select-dependency",
        help="Limit selected group/extra roots by package name; retain runtime dependencies.",
    )] = None,
) -> None:
    """Prepare locked public wheels, optionally resolving static public project dependencies."""
    from patchloop.prepared_probe_dependencies import prepare_dependencies
    from patchloop.task_loader import load_public_task

    def operation():
        path = prepare_dependencies(
            public=load_public_task(task_dir / "public.yaml"), prepared_source=prepared_source,
            wheel_lock=wheel_lock, output=output, resolve=resolve, groups=group,
            extras=extra, source_roots=source_root, selected_dependencies=select_dependency,
            generated_wheel_receipt=generated_wheel_receipt,
            generated_wheel_receipt_hash=generated_wheel_receipt_hash,
        )
        return {"ok": True, "prepared_probe_dependencies": str(path)}

    _guarded(operation)


@app.command()
def doctor() -> None:
    """Inspect local prerequisites without starting, pulling, or building anything."""

    from patchloop.sandbox import DockerSandbox

    docker_cli = DockerSandbox.cli_path()
    checks = {
        "python": {"ok": True, "version": f"Python {sys.version.split()[0]}"},
        "uv": {"ok": bool(shutil.which("uv")), "path": shutil.which("uv")},
        "git": {"ok": bool(shutil.which("git")), "path": shutil.which("git")},
        "docker_cli": {"ok": bool(docker_cli), "path": docker_cli},
        "docker_server": {"ok": DockerSandbox.available() if docker_cli else False},
    }
    _emit(checks)


if __name__ == "__main__":
    app()
