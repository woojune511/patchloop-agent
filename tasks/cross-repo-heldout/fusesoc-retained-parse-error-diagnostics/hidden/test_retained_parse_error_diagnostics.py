from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import fusesoc.coremanager as coremanager_module
import fusesoc.fusesoc as fusesoc_module
import fusesoc.main as main_module
import pytest
from fusesoc.config import Config
from fusesoc.coremanager import CoreManager, DependencyError
from fusesoc.fusesoc import Fusesoc
from fusesoc.librarymanager import Library

WORKSPACE = Path("/workspace")

VALID_CORE = """\
CAPI=2:
name: ::healthy:1
targets:
  default: {}
"""

INVALID_FILESET_CORE = """\
CAPI=2:
name: ::invalid_fileset:1
filesets:
  rtl:
    files: not_an_array
targets:
  default:
    filesets: [rtl]
"""

INVALID_YAML_CORE = """\
CAPI=2:
name: [unterminated
"""


def _config(tmp_path: Path, name: str) -> Config:
    return Config(path=str(tmp_path / f"{name}.conf"))


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _manager_with_mixed_library(tmp_path: Path) -> CoreManager:
    library_root = tmp_path / "mixed"
    library_root.mkdir()
    _write(library_root / "01-invalid-fileset.core", INVALID_FILESET_CORE)
    _write(library_root / "02-invalid-yaml.core", INVALID_YAML_CORE)
    _write(library_root / "03-healthy.core", VALID_CORE)

    manager = CoreManager(_config(tmp_path, "mixed"))
    manager.add_library(Library("mixed", str(library_root)), [])
    return manager


class _MissingCoreManager:
    def __init__(self, parse_errors: list[tuple[str, str]] | None = None) -> None:
        self.parse_errors = [] if parse_errors is None else parse_errors

    def get_cores(self) -> dict[str, object]:
        return {}

    def get_core(self, name: str) -> None:
        raise DependencyError("::required:2")


def _missing_core_message(
    monkeypatch: pytest.MonkeyPatch,
    manager: object,
) -> str:
    messages: list[str] = []
    monkeypatch.setattr(main_module.logger, "error", messages.append)
    with pytest.raises(SystemExit) as exc_info:
        main_module._get_core(manager, "::requested")
    assert exc_info.value.code == 1
    assert len(messages) == 1
    return messages[0]


def test_oracle_imports_all_submitted_production_modules() -> None:
    for module in (coremanager_module, fusesoc_module, main_module):
        module_path = Path(module.__file__ or "").resolve()
        assert module_path.is_relative_to(WORKSPACE), (
            f"{module.__name__} was imported from {module_path}, not {WORKSPACE}"
        )

    for symbol in (CoreManager, Fusesoc, main_module._get_core):
        symbol_path = Path(inspect.getsourcefile(symbol) or "").resolve()
        assert symbol_path.is_relative_to(WORKSPACE), (
            f"{symbol!r} was loaded from {symbol_path}, not {WORKSPACE}"
        )


def test_multiple_parse_failures_are_retained_as_string_tuples(
    tmp_path: Path,
) -> None:
    manager = _manager_with_mixed_library(tmp_path)

    assert len(manager.parse_errors) == 2
    assert all(
        isinstance(item, tuple)
        and len(item) == 2
        and isinstance(item[0], str)
        and isinstance(item[1], str)
        and item[1]
        for item in manager.parse_errors
    )
    retained = {Path(path).name: message for path, message in manager.parse_errors}
    assert set(retained) == {
        "01-invalid-fileset.core",
        "02-invalid-yaml.core",
    }
    assert all("03-healthy.core" not in path for path, _ in manager.parse_errors)


def test_valid_core_is_registered_after_malformed_files(tmp_path: Path) -> None:
    manager = _manager_with_mixed_library(tmp_path)

    core_names = set(manager.get_cores())
    assert "::healthy:1" in core_names
    assert all("invalid" not in name for name in core_names)


def test_parse_failures_accumulate_across_distinct_library_scans(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _write(first_root / "first-bad.core", INVALID_FILESET_CORE)
    _write(second_root / "second-bad.core", INVALID_YAML_CORE)

    manager = CoreManager(_config(tmp_path, "accumulate"))
    manager.add_library(Library("first", str(first_root)), [])
    manager.add_library(Library("second", str(second_root)), [])

    assert {Path(path).name for path, _ in manager.parse_errors} == {
        "first-bad.core",
        "second-bad.core",
    }


def test_core_manager_instances_do_not_share_parse_failures(tmp_path: Path) -> None:
    first_root = tmp_path / "isolated"
    first_root.mkdir()
    _write(first_root / "only-first.core", INVALID_FILESET_CORE)

    first = CoreManager(_config(tmp_path, "first"))
    second = CoreManager(_config(tmp_path, "second"))
    first.add_library(Library("first", str(first_root)), [])

    assert len(first.parse_errors) == 1
    assert second.parse_errors == []


def test_wrapper_property_forwards_current_manager_failures() -> None:
    failures = [("/cores/first.core", "first failure")]
    wrapper = Fusesoc.__new__(Fusesoc)
    wrapper.cm = SimpleNamespace(parse_errors=failures)

    assert wrapper.parse_errors == failures
    failures.append(("/cores/second.core", "second failure"))
    assert wrapper.parse_errors == failures


def test_missing_core_diagnostic_includes_every_retained_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = [
        ("/cores/alpha.core", "alpha validation failed"),
        ("/cores/beta.core", "beta syntax failed"),
    ]

    message = _missing_core_message(monkeypatch, _MissingCoreManager(failures))

    assert (
        "'::requested' or any of its dependencies requires '::required:2', "
        "but this core was not found"
    ) in message
    for path, error in failures:
        assert message.count(path) == 1
        assert message.count(error) == 1
    assert message.index(failures[0][0]) < message.index(failures[1][0])


def test_missing_core_without_parse_failures_keeps_original_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _missing_core_message(monkeypatch, _MissingCoreManager())

    assert message == (
        "'::requested' or any of its dependencies requires '::required:2', "
        "but this core was not found"
    )
    assert "failed to parse" not in message.lower()


def test_missing_core_manager_without_parse_error_api_still_reports_normally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class LegacyManager:
        def get_cores(self) -> dict[str, object]:
            return {}

        def get_core(self, name: str) -> None:
            raise DependencyError("::required:2")

    message = _missing_core_message(monkeypatch, LegacyManager())
    assert message.endswith("but this core was not found")


def test_provider_import_error_is_not_classified_as_a_parse_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    library_root = tmp_path / "provider"
    library_root.mkdir()
    _write(library_root / "provider.core", VALID_CORE)

    class MissingProviderCore:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ImportError("unavailable-provider")

    monkeypatch.setattr(coremanager_module, "Core", MissingProviderCore)
    manager = CoreManager(_config(tmp_path, "provider"))

    with caplog.at_level("WARNING"):
        found = manager.find_cores(Library("provider", str(library_root)), [])

    assert found == []
    assert manager.parse_errors == []
    assert "unknown provider" in caplog.text
    assert "unavailable-provider" in caplog.text
