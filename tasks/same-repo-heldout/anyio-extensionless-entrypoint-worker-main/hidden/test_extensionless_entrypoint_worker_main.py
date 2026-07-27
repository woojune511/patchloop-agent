from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

ENTRYPOINT = """
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
from anyio import to_process

PAYLOAD = __PAYLOAD__
LOAD_MARKER = Path(os.environ["PATCHLOOP_LOAD_MARKER"])
with LOAD_MARKER.open("a", encoding="utf-8") as handle:
    handle.write(f"{__name__}\\n")


def inspect_worker() -> dict[str, object]:
    import __main__
    from types import ModuleType

    alias = sys.modules.get("__mp_main__")
    return {
        "payload": __main__.PAYLOAD,
        "same_alias": __main__ is alias,
        "is_module": isinstance(__main__, ModuleType),
        "name": __main__.__name__,
        "file": str(Path(__main__.__file__).resolve()),
        "loads": LOAD_MARKER.read_text(encoding="utf-8").splitlines(),
        "pid": os.getpid(),
    }


async def program() -> None:
    result = await to_process.run_sync(inspect_worker)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    anyio.run(program, backend=sys.argv[1])
"""


REUSE_ENTRYPOINT = """
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
from anyio import to_process

LOAD_MARKER = Path(os.environ["PATCHLOOP_LOAD_MARKER"])
with LOAD_MARKER.open("a", encoding="utf-8") as handle:
    handle.write(f"{__name__}\\n")


def worker_state() -> dict[str, object]:
    import __main__

    return {
        "pid": os.getpid(),
        "same_alias": __main__ is sys.modules.get("__mp_main__"),
        "loads": LOAD_MARKER.read_text(encoding="utf-8").splitlines(),
    }


async def program() -> None:
    first = await to_process.run_sync(worker_state)
    second = await to_process.run_sync(worker_state)
    print(json.dumps({"first": first, "second": second}, sort_keys=True))


if __name__ == "__main__":
    anyio.run(program)
"""


ERROR_ENTRYPOINT = """
from __future__ import annotations

import json

import anyio
from anyio import BrokenWorkerProcess, to_process


def worker_value() -> int:
    return 17


if __name__ == "__mp_main__":
    raise RuntimeError("patchloop-bootstrap-sentinel")


async def program() -> None:
    try:
        await to_process.run_sync(worker_value)
    except BrokenWorkerProcess as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "cause": type(exc.__cause__).__name__,
                    "message": str(exc.__cause__),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    anyio.run(program)
"""


class ExtensionlessEntrypointWorkerMainTests(unittest.TestCase):
    def run_entrypoint(
        self,
        source: str,
        *,
        filename: str,
        backend: str = "asyncio",
        payload: int = 731,
    ) -> tuple[dict[str, Any], Path]:
        with tempfile.TemporaryDirectory(prefix="patchloop-anyio-main-") as temp:
            root = Path(temp)
            script = root / filename
            marker = root / "loads.txt"
            script.write_text(
                textwrap.dedent(source).replace("__PAYLOAD__", str(payload)),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PATCHLOOP_LOAD_MARKER"] = str(marker)
            completed = subprocess.run(
                [sys.executable, str(script), backend],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            diagnostic = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            self.assertEqual(completed.returncode, 0, diagnostic)
            lines = [line for line in completed.stdout.splitlines() if line.strip()]
            self.assertTrue(lines, diagnostic)
            return json.loads(lines[-1]), script.resolve()

    def assert_loaded_entrypoint(
        self, result: dict[str, Any], script: Path, *, payload: int
    ) -> None:
        self.assertEqual(result["payload"], payload)
        self.assertTrue(result["same_alias"])
        self.assertTrue(result["is_module"])
        self.assertEqual(result["name"], "__mp_main__")
        self.assertEqual(Path(result["file"]), script)
        self.assertEqual(result["loads"], ["__main__", "__mp_main__"])

    def test_submitted_source_is_imported(self) -> None:
        import anyio.to_process

        source = Path(anyio.to_process.__file__).resolve()
        self.assertTrue(
            source.is_relative_to(Path("/workspace/src").resolve()),
            f"expected submitted source, got {source}",
        )

    def test_extensionless_asyncio_entrypoint_loads_parent_globals(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="async-launcher", payload=907
        )
        self.assert_loaded_entrypoint(result, script, payload=907)

    def test_extensionless_trio_entrypoint_loads_parent_globals(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="trio-launcher", backend="trio", payload=419
        )
        self.assert_loaded_entrypoint(result, script, payload=419)

    def test_unknown_suffix_entrypoint_is_supported(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="worker.command", payload=283
        )
        self.assert_loaded_entrypoint(result, script, payload=283)

    def test_entrypoint_path_with_spaces_is_supported(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="worker launch tool", payload=641
        )
        self.assert_loaded_entrypoint(result, script, payload=641)

    def test_main_and_mp_main_are_the_same_module(self) -> None:
        result, _ = self.run_entrypoint(ENTRYPOINT, filename="module-alias")
        self.assertTrue(result["same_alias"])
        self.assertTrue(result["is_module"])
        self.assertEqual(result["name"], "__mp_main__")

    def test_worker_main_preserves_entrypoint_file_metadata(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="metadata.entry", payload=353
        )
        self.assertEqual(Path(result["file"]), script)
        self.assertEqual(result["name"], "__mp_main__")

    def test_entrypoint_executes_once_in_each_process(self) -> None:
        result, _ = self.run_entrypoint(
            ENTRYPOINT, filename="single-execution", payload=557
        )
        self.assertEqual(result["loads"], ["__main__", "__mp_main__"])

    def test_reused_worker_does_not_reload_entrypoint(self) -> None:
        result, _ = self.run_entrypoint(
            REUSE_ENTRYPOINT, filename="reuse-worker"
        )
        first = result["first"]
        second = result["second"]
        self.assertEqual(first["pid"], second["pid"])
        self.assertTrue(first["same_alias"])
        self.assertTrue(second["same_alias"])
        self.assertEqual(first["loads"], ["__main__", "__mp_main__"])
        self.assertEqual(second["loads"], ["__main__", "__mp_main__"])

    def test_python_script_entrypoint_remains_compatible(self) -> None:
        result, script = self.run_entrypoint(
            ENTRYPOINT, filename="ordinary_script.py", payload=811
        )
        self.assert_loaded_entrypoint(result, script, payload=811)

    def test_initialization_error_reaches_the_caller(self) -> None:
        result, _ = self.run_entrypoint(
            ERROR_ENTRYPOINT, filename="broken-launcher"
        )
        self.assertEqual(result["error"], "BrokenWorkerProcess")
        self.assertEqual(result["cause"], "RuntimeError")
        self.assertEqual(result["message"], "patchloop-bootstrap-sentinel")
