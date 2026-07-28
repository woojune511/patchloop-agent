"""Runtime factories and immutable manifest construction."""

from __future__ import annotations

import subprocess
import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from patchloop.contracts import (
    Budget,
    ExperimentRunContext,
    FaultSpec,
    MemoryCondition,
    MemoryConfig,
    ModelConfig,
    RunManifest,
    TaskPackage,
    Usage,
)
from patchloop.util import utc_now


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def runtime_root() -> Path:
    root = repository_root() / ".patchloop"
    root.mkdir(parents=True, exist_ok=True)
    return root


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def make_run_id(prefix: str | None = None) -> str:
    value = uuid.uuid4().hex[:16]
    return f"run_{prefix + '_' if prefix else ''}{value}"


def build_manifest(
    package: TaskPackage,
    *,
    run_id: str | None = None,
    provider: str = "mock",
    model_id: str = "mock-v1",
    memory_condition: MemoryCondition = MemoryCondition.NO_MEMORY,
    sandbox_backend: str = "local",
    fault: FaultSpec | None = None,
    budget: Budget | None = None,
    agent_image_digest: str | None = None,
    evaluator_image_digest: str | None = None,
    input_price_per_million_usd: float | None = None,
    cached_input_price_per_million_usd: float | None = None,
    cache_write_input_price_per_million_usd: float | None = None,
    output_price_per_million_usd: float | None = None,
    reasoning_effort: str = "medium",
    reasoning_mode: str = "standard",
    service_tier: str = "default",
    max_output_tokens: int = 4096,
    replay_hash: str | None = None,
    experiment_context: ExperimentRunContext | None = None,
) -> RunManifest:
    sdk_version = None
    if provider == "openai":
        try:
            sdk_version = version("openai")
        except PackageNotFoundError:
            sdk_version = "not-installed"
    memory_config = MemoryConfig(condition=memory_condition)
    if memory_condition != MemoryCondition.NO_MEMORY:
        frozen = sorted(runtime_root().glob("memory/indexes/*/FROZEN"))
        if frozen:
            marker = frozen[-1]
            memory_config.index_version = marker.parent.name
            memory_config.index_hash = marker.read_text(encoding="utf-8").strip()
    return RunManifest(
        run_id=run_id or make_run_id(),
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        harness_git_commit=git_commit(),
        model=ModelConfig(
            provider=provider,
            model_id=model_id,
            provider_sdk_version=sdk_version,
            replay_hash=replay_hash,
            reasoning_effort=reasoning_effort,
            reasoning_mode=reasoning_mode,
            service_tier=service_tier,
            max_output_tokens=max_output_tokens,
            input_price_per_million_usd=input_price_per_million_usd,
            cached_input_price_per_million_usd=cached_input_price_per_million_usd,
            cache_write_input_price_per_million_usd=(
                cache_write_input_price_per_million_usd
            ),
            output_price_per_million_usd=output_price_per_million_usd,
        ),
        budget=budget or Budget(),
        sandbox_backend=sandbox_backend,
        agent_image_digest=agent_image_digest,
        evaluator_image_digest=evaluator_image_digest,
        fault=fault or FaultSpec(),
        memory=memory_config,
        experiment=experiment_context,
        created_at=utc_now(),
    )


def calculate_model_cost(usage: Usage, config: ModelConfig) -> float:
    """Calculate direct token cost without double-counting cache reads or writes."""

    if (
        config.input_price_per_million_usd is None
        or config.output_price_per_million_usd is None
    ):
        return 0.0
    cached_tokens = min(usage.cached_input_tokens, usage.input_tokens)
    cache_write_tokens = min(
        usage.cache_write_input_tokens,
        max(0, usage.input_tokens - cached_tokens),
    )
    uncached_tokens = max(
        0,
        usage.input_tokens - cached_tokens - cache_write_tokens,
    )
    cached_price = (
        config.cached_input_price_per_million_usd
        if config.cached_input_price_per_million_usd is not None
        else config.input_price_per_million_usd
    )
    cache_write_price = (
        config.cache_write_input_price_per_million_usd
        if config.cache_write_input_price_per_million_usd is not None
        else config.input_price_per_million_usd
    )
    return (
        uncached_tokens * config.input_price_per_million_usd
        + cached_tokens * cached_price
        + cache_write_tokens * cache_write_price
        + usage.output_tokens * config.output_price_per_million_usd
    ) / 1_000_000
