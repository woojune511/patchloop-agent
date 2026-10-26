"""Shared registered pytest copy launcher and its bounded reporting adapter."""

from patchloop.errors import ContractError

PUBLIC_RUNNER = """import os, shutil, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="lite-public-") as temporary:
    checkout = Path(temporary) / "repo"
    shutil.copytree(Path.cwd(), checkout,
                   ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(checkout / "src"), str(checkout)])
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    env["HOME"] = temporary
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
                            cwd=checkout, env=env)
    raise SystemExit(result.returncode)
"""


def reporting_copy_command(command, script, marker, working_directory):
    """Instrument only the exact registered wrapper; preserve its copy/env/exit behavior."""
    index = next((i for i, arg in enumerate(command[:-1]) if arg == "-c"), None)
    if index is None or command[index + 1] != PUBLIC_RUNNER:
        raise ContractError("test comparison requires direct Python pytest or the registered "
                            "public copy wrapper")
    reporter = ("import sys\n" + script + "\nmain(['-q', *sys.argv[1:]], None, "
                + repr(working_directory) + ", " + repr(marker) + ")")
    original = '[sys.executable, "-m", "pytest", "-q", *sys.argv[1:]]'
    replacement = '[sys.executable, "-c", ' + repr(reporter) + ', *sys.argv[1:]]'
    instrumented = PUBLIC_RUNNER.replace(original, replacement, 1)
    return [*command[:index + 1], instrumented, *command[index + 2:]]
