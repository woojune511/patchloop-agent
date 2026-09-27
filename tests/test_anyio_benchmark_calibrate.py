import pytest

from diagnostics.anyio_benchmark_calibrate import PROGRAM, selected_source


def test_extracts_only_selected_definitions_without_import_side_effects():
    source = "raise RuntimeError('side effect')\ndef selected(x):\n    return x + 1\n"
    namespace = {}
    exec(selected_source(source, ["selected"]), namespace)
    assert namespace["selected"](2) == 3


def test_missing_upstream_function_fails_closed():
    with pytest.raises(ValueError, match="missing"):
        selected_source("def other(): pass", ["required"])


def test_container_program_is_valid_python():
    compile(PROGRAM, "<container>", "exec")
