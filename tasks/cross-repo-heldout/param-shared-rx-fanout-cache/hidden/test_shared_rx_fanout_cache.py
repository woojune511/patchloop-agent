from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import param
import param.reactive as reactive_module
import pytest
from param.reactive import rx

WORKSPACE = Path("/workspace")


@dataclass(frozen=True)
class Payload:
    source: int
    plus: int
    square: int
    negated: int


@dataclass(frozen=True)
class Token:
    value: int

    @property
    def doubled(self) -> int:
        return self.value * 2

    def render(self, prefix: str) -> str:
        return f"{prefix}:{self.value}"


def _payload(value: int) -> Payload:
    return Payload(
        source=value,
        plus=value + 11,
        square=value * value,
        negated=-value,
    )


def _read(branches: tuple[rx, ...]) -> list[object]:
    return [branch.rx.value for branch in branches]


async def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("reactive values did not settle before the timeout")


def test_submitted_reactive_module_is_imported() -> None:
    module_path = Path(reactive_module.__file__ or "").resolve()
    symbol_path = Path(inspect.getsourcefile(rx) or "").resolve()
    assert module_path.is_relative_to(WORKSPACE), (
        f"param.reactive was imported from {module_path}, not {WORKSPACE}"
    )
    assert symbol_path.is_relative_to(WORKSPACE), (
        f"rx was imported from {symbol_path}, not {WORKSPACE}"
    )


def test_sync_three_way_fanout_reuses_each_generation() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=2)

    inputs = Inputs()
    calls: list[int] = []

    def produce(value: int) -> Payload:
        calls.append(value)
        return _payload(value)

    shared = rx(produce)(inputs.param.signal)
    branches = (
        shared.rx.pipe(lambda payload: payload.plus),
        shared.rx.pipe(lambda payload: payload.square),
        shared.rx.pipe(lambda payload: payload.negated),
    )

    assert _read(branches) == [13, 4, -2]
    assert calls == [2]
    assert _read((branches[2], branches[0], branches[0], branches[1])) == [-2, 13, 13, 4]
    assert calls == [2]

    inputs.signal = 5
    assert _read((branches[2], branches[0], branches[1])) == [-5, 16, 25]
    assert calls == [2, 5]

    inputs.signal = 8
    assert _read((branches[1], branches[2], branches[0])) == [64, -8, 19]
    assert calls == [2, 5, 8]


def test_nested_fanout_reuses_each_shared_stage() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=3)

    inputs = Inputs()
    source_calls: list[int] = []
    normalize_calls: list[int] = []

    def source(value: int) -> tuple[int, int, int]:
        source_calls.append(value)
        return (value, value + 2, value + 4)

    def normalize(values: tuple[int, int, int]) -> dict[str, int]:
        normalize_calls.append(values[0])
        return {
            "minimum": min(values),
            "maximum": max(values),
            "total": sum(values),
        }

    shared_source = rx(source)(inputs.param.signal)
    shared_normalized = shared_source.rx.pipe(normalize)
    branches = (
        shared_normalized.rx.pipe(lambda values: values["maximum"]),
        shared_normalized.rx.pipe(lambda values: values["total"]),
        shared_normalized.rx.pipe(lambda values: values["minimum"]),
    )

    assert _read(branches) == [7, 15, 3]
    assert source_calls == [3]
    assert normalize_calls == [3]

    inputs.signal = 9
    assert _read((branches[1], branches[2], branches[0])) == [33, 9, 13]
    assert source_calls == [3, 9]
    assert normalize_calls == [3, 9]


def test_independent_reactive_graphs_do_not_share_cached_values() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer()

    first = Inputs(signal=1)
    second = Inputs(signal=10)
    first_calls: list[int] = []
    second_calls: list[int] = []

    def first_source(value: int) -> Payload:
        first_calls.append(value)
        return _payload(value)

    def second_source(value: int) -> Payload:
        second_calls.append(value)
        return _payload(value)

    first_shared = rx(first_source)(first.param.signal)
    second_shared = rx(second_source)(second.param.signal)
    first_branches = (
        first_shared.rx.pipe(lambda payload: payload.plus),
        first_shared.rx.pipe(lambda payload: payload.square),
    )
    second_branches = (
        second_shared.rx.pipe(lambda payload: payload.plus),
        second_shared.rx.pipe(lambda payload: payload.square),
    )

    assert _read((first_branches[0], second_branches[1])) == [12, 100]
    assert first_calls == [1]
    assert second_calls == [10]

    first.signal = 4
    assert _read(first_branches) == [15, 16]
    assert _read(second_branches) == [21, 100]
    assert first_calls == [1, 4]
    assert second_calls == [10]

    second.signal = 12
    assert _read((second_branches[1], first_branches[0])) == [144, 15]
    assert first_calls == [1, 4]
    assert second_calls == [10, 12]


def test_property_accessor_branch_preserves_divergent_semantics() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=4)

    inputs = Inputs()
    shared = rx(lambda value: Token(value))(inputs.param.signal)
    doubled = shared.doubled

    assert doubled.rx.value == 8
    inputs.signal = 7
    assert doubled.rx.value == 14


def test_method_accessor_branch_preserves_divergent_semantics() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=6)

    inputs = Inputs()
    shared = rx(lambda value: Token(value))(inputs.param.signal)
    rendered = shared.render("node")

    assert rendered.rx.value == "node:6"
    inputs.signal = 13
    assert rendered.rx.value == "node:13"


def test_source_error_is_reused_and_next_generation_recovers() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=1)

    inputs = Inputs()
    calls: list[int] = []

    def produce(value: int) -> Payload:
        calls.append(value)
        if value < 0:
            raise RuntimeError(f"negative:{value}")
        return _payload(value)

    shared = rx(produce)(inputs.param.signal)
    branches = (
        shared.rx.pipe(lambda payload: payload.plus),
        shared.rx.pipe(lambda payload: payload.square),
    )

    assert _read(branches) == [12, 1]
    assert calls == [1]

    inputs.signal = -2
    for branch in branches:
        with pytest.raises(RuntimeError, match=r"^negative:-2$"):
            _ = branch.rx.value
    assert calls == [1, -2]

    inputs.signal = 3
    assert _read((branches[1], branches[0])) == [9, 14]
    assert calls == [1, -2, 3]


def test_consumer_error_does_not_invalidate_a_healthy_sibling() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=2)

    inputs = Inputs()
    calls: list[int] = []

    def produce(value: int) -> Payload:
        calls.append(value)
        return _payload(value)

    def reject(payload: Payload) -> int:
        raise ValueError(f"consumer:{payload.source}")

    shared = rx(produce)(inputs.param.signal)
    healthy = shared.rx.pipe(lambda payload: payload.plus)
    failing = shared.rx.pipe(reject)

    with pytest.raises(ValueError, match=r"^consumer:2$"):
        _ = failing.rx.value
    assert healthy.rx.value == 13
    assert calls == [2]

    inputs.signal = 5
    assert healthy.rx.value == 16
    with pytest.raises(ValueError, match=r"^consumer:5$"):
        _ = failing.rx.value
    assert calls == [2, 5]


async def test_async_three_way_fanout_reuses_each_generation() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=7)

    inputs = Inputs()
    calls: list[int] = []

    async def produce(value: int) -> Payload:
        calls.append(value)
        await asyncio.sleep(0)
        return _payload(value)

    shared = inputs.param.signal.rx.pipe(produce)
    branches = (
        shared.rx.pipe(lambda payload: payload.plus),
        shared.rx.pipe(lambda payload: payload.square),
        shared.rx.pipe(lambda payload: payload.negated),
    )

    _read(branches)
    await _wait_until(lambda: calls == [7])

    inputs.signal = 8
    _read((branches[2], branches[0], branches[1]))
    await _wait_until(lambda: calls == [7, 8])
    await _wait_until(lambda: _read(branches) == [19, 64, -8])

    inputs.signal = 9
    _read((branches[1], branches[2], branches[0]))
    await _wait_until(lambda: calls == [7, 8, 9])
    await _wait_until(lambda: _read(branches) == [20, 81, -9])


async def test_generator_backed_fanout_reuses_each_generation() -> None:
    class Inputs(param.Parameterized):
        signal = param.Integer(default=3)

    inputs = Inputs()
    calls: list[int] = []

    def produce(value: int):
        calls.append(value)
        yield _payload(value)

    shared = inputs.param.signal.rx.pipe(produce)
    branches = (
        shared.rx.pipe(lambda payload: payload.plus),
        shared.rx.pipe(lambda payload: payload.square),
        shared.rx.pipe(lambda payload: payload.negated),
    )

    _read(branches)
    await _wait_until(lambda: calls == [3])

    inputs.signal = 6
    _read((branches[1], branches[0], branches[2]))
    await _wait_until(lambda: calls == [3, 6])
    await _wait_until(lambda: _read(branches) == [17, 36, -6])
