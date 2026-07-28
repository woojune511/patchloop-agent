"""Cross-process run ownership backed by an OS-held advisory lock."""

from __future__ import annotations

import os
import re
import socket
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from patchloop.errors import RunOwnershipConflict

_RUN_ID_PATTERN = re.compile(r"^run_[a-zA-Z0-9_-]+$")
_PROCESS_GUARD = threading.RLock()
_PROCESS_LOCKS: set[Path] = set()


@dataclass(frozen=True)
class WorkerIdentity:
    owner_id: str
    pid: int
    hostname: str


class RunOwnershipCoordinator:
    """Hold one non-blocking kernel lock for the complete worker lifetime."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def acquire(self, run_id: str) -> Iterator[WorkerIdentity]:
        if _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise RunOwnershipConflict("run ownership requires a valid run ID")
        lock_path = (self.root / f"{run_id}.lock").resolve()
        if lock_path.parent != self.root:
            raise RunOwnershipConflict("run ownership lock escaped its runtime directory")

        stream = None
        with _PROCESS_GUARD:
            if lock_path in _PROCESS_LOCKS:
                raise RunOwnershipConflict(
                    f"run already has an active worker: {run_id}",
                    details={"run_id": run_id},
                )
            stream = lock_path.open("a+b", buffering=0)
            try:
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"\0")
                stream.seek(0)
                self._lock(stream)
            except OSError as exc:
                stream.close()
                raise RunOwnershipConflict(
                    f"run already has an active worker: {run_id}",
                    details={"run_id": run_id},
                ) from exc
            _PROCESS_LOCKS.add(lock_path)

        try:
            identity = WorkerIdentity(
                owner_id=f"worker_{uuid.uuid4().hex}",
                pid=os.getpid(),
                hostname=socket.gethostname(),
            )
            yield identity
        finally:
            with _PROCESS_GUARD:
                try:
                    if stream is not None:
                        stream.seek(0)
                        self._unlock(stream)
                finally:
                    if stream is not None:
                        stream.close()
                    _PROCESS_LOCKS.discard(lock_path)

    @staticmethod
    def _lock(stream) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(stream) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
