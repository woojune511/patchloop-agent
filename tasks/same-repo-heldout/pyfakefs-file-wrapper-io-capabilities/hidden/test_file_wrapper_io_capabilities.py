from __future__ import annotations

import inspect
import io
from pathlib import Path

import pytest

from pyfakefs.fake_file import FakeFileWrapper
from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_io import FakeIoModule


SUBMITTED_MODULE = Path("/workspace/pyfakefs/fake_file.py")


def make_handle(
    mode: str, *, contents: str = "alpha\nbeta\n"
) -> tuple[FakeFilesystem, FakeIoModule, FakeFileWrapper]:
    filesystem = FakeFilesystem(path_separator="/")
    fake_io = FakeIoModule(filesystem)
    path = "/capability-target"
    if mode.startswith("r"):
        filesystem.create_file(path, contents=contents)
    handle = fake_io.open(path, mode)
    assert isinstance(handle, FakeFileWrapper)
    return filesystem, fake_io, handle


def test_imports_submitted_fake_file_module() -> None:
    source = Path(inspect.getsourcefile(FakeFileWrapper) or "").resolve()
    assert source == SUBMITTED_MODULE.resolve()


@pytest.mark.parametrize(
    ("mode", "expected_readable", "expected_writable"),
    [
        ("r", True, False),
        ("rb", True, False),
        ("w", False, True),
        ("wb", False, True),
        ("a", False, True),
        ("ab", False, True),
        ("x", False, True),
        ("xb", False, True),
        ("r+", True, True),
        ("r+b", True, True),
        ("w+", True, True),
        ("w+b", True, True),
        ("a+", True, True),
        ("a+b", True, True),
        ("x+", True, True),
        ("x+b", True, True),
    ],
)
def test_capabilities_match_open_mode(
    mode: str, expected_readable: bool, expected_writable: bool
) -> None:
    _, _, handle = make_handle(mode)
    try:
        assert handle.readable() is expected_readable
        assert handle.writable() is expected_writable
    finally:
        handle.close()


def test_text_io_wrapper_accepts_write_only_text_handle() -> None:
    _, fake_io, handle = make_handle("w")
    wrapper = fake_io.TextIOWrapper(handle)
    try:
        assert wrapper.readable() is False
        assert wrapper.writable() is True
        assert wrapper.detach() is handle
    finally:
        handle.close()


def test_text_io_wrapper_writes_through_binary_handle() -> None:
    filesystem, fake_io, handle = make_handle("wb")
    wrapper = fake_io.TextIOWrapper(handle, encoding="utf-8", newline="")
    try:
        assert wrapper.write("name,value\nalpha,1\n") == 19
        wrapper.flush()
        assert filesystem.get_object("/capability-target").byte_contents == (
            b"name,value\nalpha,1\n"
        )
        assert wrapper.detach() is handle
    finally:
        handle.close()


def test_readable_override_controls_dynamic_read_dispatch() -> None:
    _, _, handle = make_handle("w")
    try:
        handle.readable = lambda: True
        assert handle.read(0) == ""
    finally:
        handle.close()


def test_readable_override_controls_iterator_guard() -> None:
    _, _, handle = make_handle("r")
    try:
        handle.readable = lambda: False
        with pytest.raises(io.UnsupportedOperation, match="not open for reading"):
            next(handle)
    finally:
        handle.close()


@pytest.mark.parametrize("mode", ["w", "a", "x"])
def test_actual_read_from_write_only_handle_still_fails(mode: str) -> None:
    _, _, handle = make_handle(mode)
    try:
        with pytest.raises(io.UnsupportedOperation, match="not open for reading"):
            handle.read()
    finally:
        handle.close()


def test_actual_write_to_read_only_handle_still_fails() -> None:
    _, _, handle = make_handle("r")
    try:
        with pytest.raises(io.UnsupportedOperation, match="not open for writing"):
            handle.write("forbidden")
    finally:
        handle.close()


@pytest.mark.parametrize("mode", ["r+", "w+", "a+"])
def test_update_modes_allow_both_operations(mode: str) -> None:
    _, _, handle = make_handle(mode)
    try:
        assert handle.read(0) == ""
        assert handle.write("") == 0
    finally:
        handle.close()


def test_readable_handle_remains_iterable() -> None:
    _, _, handle = make_handle("r")
    try:
        assert next(handle) == "alpha\n"
    finally:
        handle.close()
