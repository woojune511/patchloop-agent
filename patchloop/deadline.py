"""One process-local deadline for the remaining active execution budget."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic

from patchloop.errors import PatchLoopError


class ExecutionDeadlineExceeded(PatchLoopError):
    code = "RUN_DEADLINE_EXHAUSTED"


@dataclass(frozen=True)
class ExecutionDeadline:
    expires_at: float
    clock: Callable[[], float] = field(default=monotonic, repr=False, compare=False)

    @classmethod
    def from_remaining(
        cls, seconds: float, *, clock: Callable[[], float] = monotonic
    ) -> ExecutionDeadline:
        return cls(clock() + max(0.0, seconds), clock)

    def remaining_seconds(self) -> float:
        return max(0.0, self.expires_at - self.clock())

    def check(self, *, reserve_seconds: float = 0.0) -> float:
        remaining = self.remaining_seconds() - reserve_seconds
        if remaining <= 0:
            raise ExecutionDeadlineExceeded("active execution deadline exhausted")
        return remaining

    def bounded_timeout(self, requested: float, *, reserve_seconds: float = 0.0) -> float:
        return min(requested, self.check(reserve_seconds=reserve_seconds))
