from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import dagster as dg
import pytest
from dagster._check import CheckError
from dagster._core.execution.context.system import StepExecutionContext


def _mixed_assets(
    first: dg.PartitionsDefinition,
    second: dg.PartitionsDefinition | None = None,
) -> dg.AssetsDefinition:
    specs = [
        dg.AssetSpec("plain"),
        dg.AssetSpec("partitioned", partitions_def=first),
    ]
    if second is not None:
        specs.append(dg.AssetSpec("other_partitioned", partitions_def=second))

    @dg.multi_asset(specs=specs, can_subset=True)
    def mixed_assets():
        pass

    return mixed_assets


def _subset(
    assets_def: dg.AssetsDefinition,
    *asset_names: str,
    check_keys: set[dg.AssetCheckKey] | None = None,
) -> dg.AssetsDefinition:
    return assets_def.subset_for(
        {dg.AssetKey(name) for name in asset_names},
        selected_asset_check_keys=check_keys or set(),
    )


def _entity_partitions_def(assets_def: object | None) -> object | None:
    fake_context = SimpleNamespace(assets_def=assets_def)
    descriptor = StepExecutionContext.__dict__["entity_partitions_def"]
    return descriptor.__get__(fake_context, StepExecutionContext)


def test_oracle_imports_the_submitted_source_copy() -> None:
    source = Path(inspect.getfile(dg)).resolve().as_posix()

    assert "/tmp/patchloop-dagster-hidden-" in source
    assert source.endswith("/python_modules/dagster/dagster/__init__.py")


def test_unselected_partitioned_asset_does_not_define_plain_subset() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    selected = _subset(_mixed_assets(daily), "plain")

    assert selected.partitions_def is None


def test_selected_partitioned_asset_keeps_its_definition() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    selected = _subset(_mixed_assets(daily), "partitioned")

    assert selected.partitions_def is daily


def test_only_selected_partition_definition_participates_in_conflict_check() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    monthly = dg.MonthlyPartitionsDefinition(start_date="2024-01-01")
    assets_def = _mixed_assets(daily, monthly)

    assert _subset(assets_def, "partitioned").partitions_def is daily

    with pytest.raises(CheckError, match="different PartitionsDefinitions"):
        _subset(assets_def, "partitioned", "other_partitioned").partitions_def


def test_selected_partitioned_check_defines_partition_context() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    monthly = dg.MonthlyPartitionsDefinition(start_date="2024-01-01")
    plain = dg.AssetKey("plain")
    daily_check = dg.AssetCheckKey(plain, "daily_check")
    monthly_check = dg.AssetCheckKey(plain, "monthly_check")

    @dg.multi_asset(
        specs=[dg.AssetSpec(plain)],
        check_specs=[
            dg.AssetCheckSpec("daily_check", asset=plain, partitions_def=daily),
            dg.AssetCheckSpec("monthly_check", asset=plain, partitions_def=monthly),
        ],
        can_subset=True,
    )
    def checked_asset():
        pass

    selected = _subset(checked_asset, check_keys={daily_check})
    assert selected.partitions_def is daily

    with pytest.raises(CheckError, match="different PartitionsDefinitions"):
        _subset(
            checked_asset,
            check_keys={daily_check, monthly_check},
        ).partitions_def


def test_unselected_partitioned_check_does_not_poison_asset_subset() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    plain = dg.AssetKey("plain")

    @dg.multi_asset(
        specs=[dg.AssetSpec(plain)],
        check_specs=[
            dg.AssetCheckSpec("partitioned_check", asset=plain, partitions_def=daily),
        ],
        can_subset=True,
    )
    def checked_asset():
        pass

    assert _subset(checked_asset, "plain").partitions_def is None


def test_compatible_selected_asset_and_check_share_definition() -> None:
    daily = dg.DailyPartitionsDefinition(start_date="2024-01-01")
    asset_key = dg.AssetKey("partitioned")
    check_key = dg.AssetCheckKey(asset_key, "freshness")

    @dg.multi_asset(
        specs=[dg.AssetSpec(asset_key, partitions_def=daily)],
        check_specs=[
            dg.AssetCheckSpec(
                "freshness",
                asset=asset_key,
                partitions_def=daily,
            ),
        ],
        can_subset=True,
    )
    def checked_asset():
        pass

    selected = _subset(
        checked_asset,
        "partitioned",
        check_keys={check_key},
    )

    assert selected.partitions_def is daily


def test_execution_context_uses_selection_aware_assets_definition() -> None:
    sentinel = object()

    class DelegatingAssetsDefinition:
        partitions_def = sentinel

        @property
        def specs(self) -> None:
            raise AssertionError("execution context duplicated asset selection")

        @property
        def check_specs(self) -> None:
            raise AssertionError("execution context duplicated check selection")

    result = _entity_partitions_def(DelegatingAssetsDefinition())

    assert result is sentinel


def test_execution_context_without_assets_definition_remains_unpartitioned() -> None:
    assert _entity_partitions_def(None) is None
