from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

WORKSPACE = Path("/workspace").resolve()

PROBE = r"""
import datetime as std_datetime
import inspect
import json
import sys
from types import SimpleNamespace

import loguru
import loguru._datetime as target


PROFILES = {
    "east": {
        "utc": (2042, 5, 6, 10, 0),
        "local": (2042, 5, 6, 13, 45),
        "zone": "FALLBACK_EAST",
    },
    "west": {
        "utc": (2042, 5, 6, 10, 15),
        "local": (2042, 5, 6, 3, 45),
        "zone": "FALLBACK_WEST",
    },
    "rollover": {
        "utc": (2042, 5, 5, 23, 30),
        "local": (2042, 5, 6, 1, 0),
        "zone": "FALLBACK_ROLLOVER",
    },
}
profile = PROFILES[sys.argv[2]]


class FrozenNow(std_datetime.datetime):
    def timestamp(self):
        return 4102444800.5


class FrozenDateTime:
    @classmethod
    def now(cls):
        return FrozenNow(2042, 5, 6, 7, 8, 9, 123456)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        if timestamp != 4102444800.5:
            raise AssertionError("unexpected timestamp")
        if tz is target.timezone.utc:
            return std_datetime.datetime(
                *profile["utc"],
                tzinfo=std_datetime.timezone.utc,
            )
        return std_datetime.datetime(*profile["local"])


mode = sys.argv[1]
target.datetime_ = FrozenDateTime
target.strftime = lambda fmt: profile["zone"]

if mode == "valid-negative":
    target.localtime = lambda timestamp: SimpleNamespace(
        tm_gmtoff=-19800,
        tm_zone="VALID_NEGATIVE",
    )
elif mode == "valid-zero":
    target.localtime = lambda timestamp: SimpleNamespace(
        tm_gmtoff=0,
        tm_zone="VALID_ZERO",
    )
elif mode == "valid-positive":
    target.localtime = lambda timestamp: SimpleNamespace(
        tm_gmtoff=20700,
        tm_zone="VALID_POSITIVE",
    )
elif mode == "invalid-positive":
    target.localtime = lambda timestamp: SimpleNamespace(
        tm_gmtoff=172800,
        tm_zone="BROKEN",
    )
elif mode == "invalid-negative":
    target.localtime = lambda timestamp: SimpleNamespace(
        tm_gmtoff=-172800,
        tm_zone="BROKEN",
    )
elif mode == "os-error":
    def localtime(timestamp):
        raise OSError("platform range")

    target.localtime = localtime
elif mode == "overflow-error":
    def localtime(timestamp):
        raise OverflowError("platform range")

    target.localtime = localtime
elif mode == "missing-both":
    target.localtime = lambda timestamp: SimpleNamespace()
elif mode == "missing-zone":
    target.localtime = lambda timestamp: SimpleNamespace(tm_gmtoff=3600)
elif mode == "missing-gmtoff":
    target.localtime = lambda timestamp: SimpleNamespace(tm_zone="INCOMPLETE")
elif mode == "runtime-error":
    def localtime(timestamp):
        raise RuntimeError("unsupported platform failure")

    target.localtime = localtime
else:
    raise AssertionError("unknown mode: %s" % mode)

try:
    value = target.aware_now()
except BaseException as exc:
    result = {
        "ok": False,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "module": inspect.getfile(target),
    }
else:
    result = {
        "ok": True,
        "module": inspect.getfile(target),
        "package": inspect.getfile(loguru),
        "date_time": [
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
        ],
        "offset_seconds": int(value.utcoffset().total_seconds()),
        "zone": value.tzname(),
    }

print(json.dumps(result))
"""


@pytest.fixture(scope="session")
def submitted_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source_root = tmp_path_factory.mktemp("loguru-submitted-source")
    shutil.copytree(WORKSPACE / "loguru", source_root / "loguru")
    return source_root


def _probe(source_root: Path, mode: str, profile: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, mode, profile],
        cwd=source_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, (
        f"probe failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    module_path = Path(result["module"]).resolve()
    package_path = Path(result.get("package", result["module"])).resolve()
    assert module_path.is_relative_to(source_root.resolve())
    assert package_path.is_relative_to(source_root.resolve())
    return result


def _assert_clock_is_preserved(result: dict[str, Any]) -> None:
    assert result["ok"], result
    assert result["date_time"] == [2042, 5, 6, 7, 8, 9, 123456]


@pytest.mark.parametrize(
    ("mode", "offset_seconds", "zone"),
    [
        ("valid-negative", -19800, "VALID_NEGATIVE"),
        ("valid-zero", 0, "VALID_ZERO"),
        ("valid-positive", 20700, "VALID_POSITIVE"),
    ],
)
def test_valid_platform_timezone_remains_the_fast_path(
    submitted_source: Path,
    mode: str,
    offset_seconds: int,
    zone: str,
) -> None:
    result = _probe(submitted_source, mode, "east")
    _assert_clock_is_preserved(result)
    assert result["offset_seconds"] == offset_seconds
    assert result["zone"] == zone


@pytest.mark.parametrize(
    ("mode", "profile", "offset_seconds", "zone"),
    [
        ("invalid-positive", "east", 13500, "FALLBACK_EAST"),
        ("invalid-negative", "west", -23400, "FALLBACK_WEST"),
    ],
)
def test_invalid_platform_offsets_use_datetime_fallback(
    submitted_source: Path,
    mode: str,
    profile: str,
    offset_seconds: int,
    zone: str,
) -> None:
    result = _probe(submitted_source, mode, profile)
    _assert_clock_is_preserved(result)
    assert result["offset_seconds"] == offset_seconds
    assert result["zone"] == zone


@pytest.mark.parametrize(
    ("mode", "profile", "offset_seconds", "zone"),
    [
        ("os-error", "east", 13500, "FALLBACK_EAST"),
        ("overflow-error", "west", -23400, "FALLBACK_WEST"),
    ],
)
def test_platform_range_errors_use_datetime_fallback(
    submitted_source: Path,
    mode: str,
    profile: str,
    offset_seconds: int,
    zone: str,
) -> None:
    result = _probe(submitted_source, mode, profile)
    _assert_clock_is_preserved(result)
    assert result["offset_seconds"] == offset_seconds
    assert result["zone"] == zone


@pytest.mark.parametrize(
    ("mode", "profile", "offset_seconds", "zone"),
    [
        ("missing-both", "east", 13500, "FALLBACK_EAST"),
        ("missing-zone", "west", -23400, "FALLBACK_WEST"),
        ("missing-gmtoff", "rollover", 5400, "FALLBACK_ROLLOVER"),
    ],
)
def test_unavailable_platform_timezone_fields_use_datetime_fallback(
    submitted_source: Path,
    mode: str,
    profile: str,
    offset_seconds: int,
    zone: str,
) -> None:
    result = _probe(submitted_source, mode, profile)
    _assert_clock_is_preserved(result)
    assert result["offset_seconds"] == offset_seconds
    assert result["zone"] == zone


def test_unsupported_platform_error_is_not_silently_swallowed(
    submitted_source: Path,
) -> None:
    result = _probe(submitted_source, "runtime-error", "east")
    assert not result["ok"], result
    assert result["error_type"] == "RuntimeError"
    assert result["message"] == "unsupported platform failure"
