"""Check new test module names against readable public pytest configuration.

This is a filename check before a file transaction, not a collection/coverage
claim. Unknown commands/configuration remain unknown; no pytest code runs here.
"""

from __future__ import annotations

import configparser
import fnmatch
import shlex
import tomllib
from pathlib import PurePosixPath

from patchloop.dev.check_review import _inline_prefix, _registered_selection
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

POLICY = "new-pytest-module-public-filename-v1"
MAX_CONFIG_BYTES = 65_536
DEFAULT_PATTERNS = ["test_*.py", "*_test.py"]
CONFIG_NAMES = ("pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg")


def _overrides(arguments):
    return any(arg in {"-c", "-o", "--override-ini", "--rootdir"}
               or arg.startswith(("-c", "-o", "--override-ini=", "--rootdir="))
               for arg in arguments)


def _settings(name, raw):
    if name == "pyproject.toml":
        section = tomllib.loads(raw.decode("utf-8")).get("tool", {}).get("pytest", {})
        if section and "ini_options" not in section:
            raise ValueError("native pytest TOML settings require runtime resolution")
        return section.get("ini_options")
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.read_string(raw.decode("utf-8"))
    section = "tool:pytest" if name == "setup.cfg" else "pytest"
    if parser.has_section(section):
        return dict(parser[section])
    if name in {"pytest.ini", ".pytest.ini"}:
        return {}
    return None


def filename_rule(directory, tracked, read):
    """Resolve only ordinary public INI settings, bounded inside the repository."""
    for folder in (PurePosixPath(directory), *PurePosixPath(directory).parents):
        # These newer native formats have version-dependent precedence/settings.
        if any(str(folder / name) in tracked for name in ("pytest.toml", ".pytest.toml")):
            return None
        for name in CONFIG_NAMES:
            path = str(folder / name)
            if path not in tracked:
                continue
            raw = read(path)
            if len(raw) > MAX_CONFIG_BYTES:
                return None
            try:
                settings = _settings(name, raw)
                if settings is None:
                    continue
                if _overrides(shlex.split(settings.get("addopts", ""))):
                    return None
                patterns = settings.get("python_files", DEFAULT_PATTERNS)
                if isinstance(patterns, str):
                    patterns = shlex.split(patterns)
                if (not isinstance(patterns, list) or len(patterns) > 16
                        or not all(isinstance(p, str) and 0 < len(p) <= 128
                                   and "/" not in p and "\\" not in p for p in patterns)):
                    return None
            except (ValueError, TypeError, AttributeError, configparser.Error, UnicodeError):
                return None
            return {"python_files": patterns, "config_path": path,
                    "config_hash": sha256_bytes(raw)}
    return {"python_files": DEFAULT_PATTERNS, "config_path": None, "config_hash": None}


def validate_new_test_names(gateway, changes):
    """Reject a known filename omission, without guessing about unknown runners."""
    if any(PurePosixPath(change.path).name in (*CONFIG_NAMES, "pytest.toml", ".pytest.toml")
           for change in changes):
        return  # The transaction changes configuration; its current rule is not the candidate rule.
    paths = [change.path for change in changes
             if change.before is None and change.after is not None
             and gateway._validated_test_only(change.path)]
    suites = [suite.model_dump(mode="json") for suite in gateway.public_task.test_suites]
    if not paths or not suites:
        return
    tracked = gateway._tracked_paths()

    def read(path):
        _, file = gateway._tracked_path(path, tracked_paths=tracked)
        with file.open("rb") as stream:
            return stream.read(MAX_CONFIG_BYTES + 1)

    rules = {}
    for path in paths:
        candidates = []
        unknown = False
        for suite in suites:
            directory = suite.get("working_directory", ".")
            if (suite.get("runner") != "pytest"
                    or not PurePosixPath(path).is_relative_to(directory)
                    or not any(PurePosixPath(path).is_relative_to(root)
                               for root in suite.get("test_roots", []))):
                continue
            kind, _ = _registered_selection(suite, suites)
            prefix = _inline_prefix(suite["command"])
            arguments = suite["command"][len(prefix):] if prefix else suite["command"]
            nested_config = any(
                str(parent / name) in tracked
                for parent in PurePosixPath(path).parents
                if parent != PurePosixPath(directory) and parent.is_relative_to(directory)
                for name in (*CONFIG_NAMES, "pytest.toml", ".pytest.toml")
            )
            if (kind == "unresolved" or nested_config or _overrides(arguments)
                    or suite.get("environment", {}).get("PYTEST_ADDOPTS")):
                unknown = True
                continue
            if directory not in rules:
                rules[directory] = filename_rule(directory, tracked, read)
            rule = rules[directory]
            if rule is None:
                unknown = True
                continue
            candidates.append({"suite_id": suite["id"], **rule})
        if unknown or not candidates or any(
            fnmatch.fnmatchcase(PurePosixPath(path).name, pattern)
            for rule in candidates for pattern in rule["python_files"]
        ):
            continue
        raise ContractError(
            f"New test module {path!r} does not match the public pytest python_files "
            f"patterns: {candidates!r}. Choose a matching new filename, or add the test "
            "to an existing collected module. Running this file explicitly does not "
            "make directory discovery include it. The transaction was not applied.",
            details={"test_discovery": {"policy": POLICY, "path": path,
                                        "status": "filename_mismatch", "rules": candidates}},
        )
