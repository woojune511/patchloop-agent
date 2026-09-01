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

from patchloop.errors import ContractError, PatchLoopError
from patchloop.task_loader import load_task_package

app = typer.Typer(no_args_is_help=True, help="PatchLoop mutable development harness")
task_app = typer.Typer(no_args_is_help=True, help="Validate audited task packages")
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
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", exists=True, dir_okay=False),
    ] = None,
    max_cost_usd: Annotated[
        str | None,
        typer.Option("--max-cost-usd"),
    ] = None,
    repeat: Annotated[int, typer.Option("--repeat", min=1, max=6)] = 1,
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
                env_file=env_file,
                max_cost_usd=_parse_cost(max_cost_usd),
                repeat=repeat,
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
        }

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
