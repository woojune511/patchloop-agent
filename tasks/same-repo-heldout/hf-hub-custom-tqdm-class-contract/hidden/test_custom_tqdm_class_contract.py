from __future__ import annotations

import importlib
import inspect
import io
import logging
import sys
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest
from tqdm.auto import tqdm as upstream_tqdm

file_download_module = importlib.import_module("huggingface_hub.file_download")
snapshot_module = importlib.import_module("huggingface_hub._snapshot_download")
tqdm_module = importlib.import_module("huggingface_hub.utils.tqdm")

WORKSPACE = Path("/workspace").resolve()


class StrictProgress:
    """A foreign progress implementation that accepts no HF-only keywords."""

    created: list[StrictProgress] = []

    def __init__(
        self,
        *,
        desc: str = "",
        total: int | float | None = None,
        initial: int | float = 0,
        unit: str = "B",
        unit_scale: bool = True,
        marker: str | None = None,
    ) -> None:
        self.desc = desc
        self.total = total
        self.n = initial
        self.unit = unit
        self.unit_scale = unit_scale
        self.marker = marker
        self.closed = False
        self.refresh_count = 0
        type(self).created.append(self)

    def __enter__(self) -> StrictProgress:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.closed = True

    def update(self, amount: int | float | None = 1) -> None:
        self.n += 1 if amount is None else amount

    def refresh(self) -> None:
        self.refresh_count += 1

    def set_description(self, description: str) -> None:
        self.desc = description


class KeywordRecordingProgress(StrictProgress):
    """A permissive foreign class used to inspect constructor ownership."""

    created: list[KeywordRecordingProgress] = []

    def __init__(
        self,
        *,
        desc: str = "",
        total: int | float | None = None,
        initial: int | float = 0,
        unit: str = "B",
        unit_scale: bool = True,
        **extra: object,
    ) -> None:
        self.extra = dict(extra)
        super().__init__(
            desc=desc,
            total=total,
            initial=initial,
            unit=unit,
            unit_scale=unit_scale,
        )


@pytest.fixture(autouse=True)
def _isolate_progress_policy(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    previous_states = dict(tqdm_module.progress_bar_states)
    StrictProgress.created.clear()
    KeywordRecordingProgress.created.clear()
    monkeypatch.setattr(tqdm_module, "HF_HUB_DISABLE_PROGRESS_BARS", None)
    monkeypatch.delenv("TQDM_POSITION", raising=False)
    tqdm_module.progress_bar_states.clear()
    tqdm_module.progress_bar_states["_global"] = True
    yield
    tqdm_module.progress_bar_states.clear()
    tqdm_module.progress_bar_states.update(previous_states)


def _progress_context(
    *,
    progress_factory: object,
    name: str = "patchloop.hidden",
    log_level: int = logging.INFO,
    existing: object | None = None,
) -> object:
    return tqdm_module._get_progress_bar_context(
        desc="hidden-contract",
        log_level=log_level,
        total=12,
        initial=2,
        unit="B",
        unit_scale=True,
        name=name,
        tqdm_class=progress_factory,
        _tqdm_bar=existing,
    )


def test_submitted_progress_modules_are_imported() -> None:
    module_paths = {
        "utils.tqdm": Path(tqdm_module.__file__ or "").resolve(),
        "_snapshot_download": Path(snapshot_module.__file__ or "").resolve(),
        "file_download": Path(file_download_module.__file__ or "").resolve(),
        "_get_progress_bar_context": Path(
            inspect.getsourcefile(tqdm_module._get_progress_bar_context) or ""
        ).resolve(),
    }
    for label, module_path in module_paths.items():
        assert module_path.is_relative_to(WORKSPACE), (
            f"{label} was imported from {module_path}, not {WORKSPACE}"
        )


def test_foreign_class_owns_name_and_disable_policy() -> None:
    with _progress_context(progress_factory=StrictProgress) as progress:
        assert progress.desc == "hidden-contract"
        assert progress.total == 12
        assert progress.n == 2
        progress.update(5)
        assert progress.n == 7

    assert progress.closed


def test_foreign_upstream_subclass_owns_constructor_and_updates() -> None:
    class ForeignUpstreamProgress(upstream_tqdm):
        constructor_calls: list[dict[str, object]] = []

        def __init__(self, *args: object, **kwargs: object) -> None:
            assert "disable" not in kwargs
            assert "name" not in kwargs
            type(self).constructor_calls.append(dict(kwargs))
            super().__init__(
                *args,
                disable=False,
                file=io.StringIO(),
                **kwargs,
            )

    with _progress_context(progress_factory=ForeignUpstreamProgress) as progress:
        progress.update(10)
        assert progress.n == 12

    assert len(ForeignUpstreamProgress.constructor_calls) == 1


def test_function_factory_is_supported_without_hf_keywords() -> None:
    calls: list[str] = []

    def foreign_factory(
        *,
        desc: str,
        total: int | float | None,
        initial: int | float,
        unit: str,
        unit_scale: bool,
    ) -> StrictProgress:
        calls.append(desc)
        return StrictProgress(
            desc=desc,
            total=total,
            initial=initial,
            unit=unit,
            unit_scale=unit_scale,
            marker="function",
        )

    with _progress_context(progress_factory=foreign_factory) as progress:
        progress.update(3)
        assert progress.n == 5
        assert progress.marker == "function"

    assert calls == ["hidden-contract"]


def test_partial_factory_is_supported_without_issubclass_failure() -> None:
    foreign_factory = partial(StrictProgress, marker="partial")

    with _progress_context(progress_factory=foreign_factory) as progress:
        progress.update(4)
        assert progress.n == 6
        assert progress.marker == "partial"


def test_foreign_class_ignores_hf_global_and_group_disable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tqdm_module, "HF_HUB_DISABLE_PROGRESS_BARS", True)
    tqdm_module.progress_bar_states["patchloop.hidden"] = False

    with _progress_context(progress_factory=KeywordRecordingProgress) as progress:
        progress.update(2)

    assert progress.extra == {}
    assert progress.n == 4


def test_hf_subclass_preserves_named_group_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HiddenHfProgress(tqdm_module.tqdm):
        pass

    tqdm_module.disable_progress_bars("patchloop.hidden")
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    with _progress_context(
        progress_factory=HiddenHfProgress,
        name="patchloop.hidden.child",
    ) as progress:
        assert progress.disable


def test_hf_subclass_preserves_log_and_position_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HiddenHfProgress(tqdm_module.tqdm):
        pass

    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with _progress_context(
        progress_factory=HiddenHfProgress,
        name="patchloop.log",
        log_level=logging.NOTSET,
    ) as progress:
        assert progress.disable

    monkeypatch.setenv("TQDM_POSITION", "-1")
    with _progress_context(
        progress_factory=HiddenHfProgress,
        name="patchloop.position",
        log_level=logging.INFO,
    ) as progress:
        assert not progress.disable


def test_shared_existing_bar_is_reused_without_construction_or_close() -> None:
    existing = StrictProgress(desc="shared", total=20)
    factory_called = False

    def rejecting_factory(**kwargs: object) -> StrictProgress:
        nonlocal factory_called
        factory_called = True
        raise AssertionError(f"unexpected factory call: {kwargs}")

    with _progress_context(
        progress_factory=rejecting_factory,
        existing=existing,
    ) as progress:
        assert progress is existing
        progress.update(6)

    assert not factory_called
    assert existing.n == 6
    assert not existing.closed


def test_http_download_path_uses_foreign_progress_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OfflineResponse:
        status_code = 200
        headers = {"Content-Length": "6"}

        def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
            assert chunk_size > 0
            yield b"ab"
            yield b"cdef"

    @contextmanager
    def offline_stream(**kwargs: object) -> Iterator[OfflineResponse]:
        assert kwargs["url"] == "https://offline.invalid/artifact.bin"
        yield OfflineResponse()

    def accept_status(response: object) -> None:
        assert isinstance(response, OfflineResponse)

    monkeypatch.setattr(
        file_download_module,
        "http_stream_backoff",
        offline_stream,
    )
    monkeypatch.setattr(file_download_module, "hf_raise_for_status", accept_status)

    target = io.BytesIO()
    file_download_module.http_get(
        "https://offline.invalid/artifact.bin",
        target,
        expected_size=6,
        displayed_filename="artifact.bin",
        tqdm_class=StrictProgress,
    )

    assert target.getvalue() == b"abcdef"
    assert len(StrictProgress.created) == 1
    progress = StrictProgress.created[0]
    assert progress.n == 6
    assert progress.total == 6
    assert progress.closed


def _run_snapshot_fully_offline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_factory: object,
) -> tuple[Path, list[dict[str, object]], list[dict[str, object]]]:
    commit_hash = "a" * 40
    api_calls: list[dict[str, object]] = []
    download_calls: list[dict[str, object]] = []

    class OfflineApi:
        def __init__(self, **kwargs: object) -> None:
            api_calls.append({"constructor": kwargs})

        def repo_info(self, **kwargs: object) -> SimpleNamespace:
            api_calls.append({"repo_info": kwargs})
            return SimpleNamespace(
                sha=commit_hash,
                siblings=[SimpleNamespace(rfilename="weights.bin")],
            )

        def list_repo_tree(self, **kwargs: object) -> Iterable[object]:
            raise AssertionError(f"unexpected tree request: {kwargs}")

    def run_inline(
        function: Callable[[str], object],
        items: Iterable[str],
        **kwargs: object,
    ) -> list[object]:
        assert kwargs["tqdm_class"] is progress_factory
        return [function(item) for item in items]

    def offline_download(
        repo_id: str,
        *,
        filename: str,
        **kwargs: object,
    ) -> str:
        download_calls.append(
            {"repo_id": repo_id, "filename": filename, "kwargs": kwargs}
        )
        aggregate_factory = kwargs["tqdm_class"]
        with aggregate_factory(total=7, initial=2) as aggregate:
            aggregate.update(5)
        return str(tmp_path / filename)

    monkeypatch.setattr(snapshot_module, "HfApi", OfflineApi)
    monkeypatch.setattr(snapshot_module, "thread_map", run_inline)
    monkeypatch.setattr(snapshot_module, "hf_hub_download", offline_download)

    result = snapshot_module.snapshot_download(
        repo_id="org/offline-repo",
        revision=commit_hash,
        cache_dir=tmp_path,
        tqdm_class=progress_factory,
        max_workers=1,
    )

    expected = (
        tmp_path
        / "models--org--offline-repo"
        / "snapshots"
        / commit_hash
    )
    assert Path(result) == expected
    assert len(api_calls) == 2
    assert len(download_calls) == 1
    assert download_calls[0]["filename"] == "weights.bin"
    return expected, api_calls, download_calls


def test_snapshot_download_uses_custom_progress_fully_offline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_snapshot_fully_offline(monkeypatch, tmp_path, StrictProgress)

    assert len(StrictProgress.created) == 1
    parent_progress = StrictProgress.created[0]
    assert parent_progress.total == 7
    assert parent_progress.n == 7
    assert parent_progress.refresh_count == 1
    assert parent_progress.desc == "Download complete"


@pytest.mark.parametrize("factory_kind", ["function", "partial"])
def test_snapshot_download_supports_callable_factories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    factory_kind: str,
) -> None:
    if factory_kind == "function":

        def progress_factory(**kwargs: object) -> StrictProgress:
            return StrictProgress(marker="function", **kwargs)

    else:
        progress_factory = partial(StrictProgress, marker="partial")

    _run_snapshot_fully_offline(monkeypatch, tmp_path, progress_factory)

    assert len(StrictProgress.created) == 1
    assert StrictProgress.created[0].marker == factory_kind


@pytest.mark.parametrize("policy", ["group", "log"])
def test_snapshot_hf_subclass_preserves_group_and_log_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    policy: str,
) -> None:
    class SnapshotHfProgress(tqdm_module.tqdm):
        created: list[SnapshotHfProgress] = []

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            type(self).created.append(self)

    monkeypatch.setattr(sys, "stderr", io.StringIO())
    if policy == "group":
        tqdm_module.disable_progress_bars(
            "huggingface_hub.snapshot_download"
        )
        log_level = logging.INFO
    else:
        log_level = logging.NOTSET
    monkeypatch.setattr(
        snapshot_module.logger,
        "getEffectiveLevel",
        lambda: log_level,
    )

    _run_snapshot_fully_offline(
        monkeypatch,
        tmp_path,
        SnapshotHfProgress,
    )

    assert len(SnapshotHfProgress.created) == 1
    assert SnapshotHfProgress.created[0].disable
