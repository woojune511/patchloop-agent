"""Public synthetic pytest logs exercise operator-only failure preservation."""

import base64
import hashlib
import os
import re
import subprocess
import sys

import pytest

from diagnostics import swebench_lite_oracle


def retained_failure_bytes(capture):
    return b"".join(
        base64.b64decode(segment["content"])
        for block in capture["blocks"] for segment in block["segments"]
    )


def assert_original_byte_ranges(raw, capture, expected_blocks):
    assert capture["recognized_block_count"] == len(expected_blocks)
    assert capture["retained_block_count"] == len(expected_blocks)
    assert capture["unclosed_block_count"] == capture["omitted_bytes"] == 0
    assert capture["retained_bytes"] <= swebench_lite_oracle.DIAGNOSTIC_FAILURE_LIMIT_BYTES
    for block, expected in zip(capture["blocks"], expected_blocks, strict=True):
        start = raw.index(expected)
        assert block["start_byte"] == start
        assert block["end_byte"] == start + len(expected)
        assert block["closed_by_marker"] is True
        assert block["original_bytes"] == block["retained_bytes"] == len(expected)
        assert block["omitted_bytes"] == 0
        segment, = block["segments"]
        assert segment["start_byte"] == block["start_byte"]
        assert segment["end_byte"] == block["end_byte"]
        assert base64.b64decode(segment["content"]) == raw[
            segment["start_byte"]:segment["end_byte"]
        ] == expected


@pytest.mark.parametrize("delimiter_count", [1, 2])
def test_short_pytest_delimiters_keep_adjacent_failures_and_end_at_capture(delimiter_count):
    delimiter = b"_" * delimiter_count
    boundary = b"-" * delimiter_count
    blocks = [
        delimiter + b" test_synthetic[" + bytes([65 + index]) * 240 + b"] " + delimiter
        + b"\r\n    assert actual == expected\r\n"
        + f"E   AssertionError: synthetic mismatch {index}\r\n".encode()
        for index in range(3)
    ]
    raw = (
        b"================ FAILURES ================\r\n"
        + blocks[0] + blocks[1]
        + boundary + b" Captured stdout call " + boundary + b"\r\n"
        + b"synthetic stdout should be excluded\r\n" + blocks[2]
        + boundary + b" Captured stderr call " + boundary + b"\r\n"
        + b"synthetic stderr should be excluded\r\n"
        + b"================ short test summary info ================\r\n"
    )
    capture = swebench_lite_oracle.execution_log("tests", raw, None)["stdout"][
        "failure_capture"
    ]
    assert retained_failure_bytes(capture) == b"".join(blocks)
    assert_original_byte_ranges(raw, capture, blocks)


def test_ansi_pytest_sections_preserve_raw_offsets_and_close_at_colored_summary():
    first = (
        b"\x1b[31m_ test_synthetic[first] _\x1b[0m\r\n"
        b"\x1b[1mE   AssertionError: actual != expected\x1b[0m\r\n"
    )
    second = (
        b"\x1b[31m__ test_synthetic[second] __\x1b[0m\r\n"
        b"\x1b[31mE   assert 'actual' == 'expected'\x1b[0m\r\n"
    )
    raw = (
        "synthetic UTF-8 prefix: 한글\r\n".encode()
        + b"\x1b[31m=\x1b[0m\x1b[1m FAILURES \x1b[0m\x1b[31m=\x1b[0m\r\n"
        + first
        + b"\x1b[33m- Captured stdout call -\x1b[0m\r\nexcluded capture\r\n"
        + second
        + b"\x1b[31m== short test summary info ==\x1b[0m\r\n"
        + b"_ text outside the failure section _\r\nnot a failure block\r\n"
    )
    stream = swebench_lite_oracle.execution_log("tests", raw, None)["stdout"]
    assert stream["sha256"] == hashlib.sha256(raw).hexdigest()
    assert base64.b64decode(stream["content"]) == raw
    assert retained_failure_bytes(stream["failure_capture"]) == first + second
    assert_original_byte_ranges(raw, stream["failure_capture"], [first, second])


def test_long_parameter_failure_retains_actual_expected_diff_between_megabytes():
    failure = (
        b"_ test_synthetic[" + b"long-public-parameter-" * 20 + b"] _\n"
        b"    actual = 'synthetic-actual-value'\n"
        b"    expected = 'synthetic-expected-value'\n"
        b">   assert actual == expected\n"
        b"E   AssertionError: assert 'synthetic-actual-value' == 'synthetic-expected-value'\n"
        b"E     - synthetic-expected-value\n"
        b"E     + synthetic-actual-value\n"
    )
    raw = (
        b"synthetic verbose setup\n" * 100_000
        + b"================ FAILURES ================\n" + failure
        + b"------------ Captured stdout call ------------\n"
        + b"synthetic bulk captured output\n" * 100_000
        + b"================ short test summary info ================\n"
        + b"FAILED test_synthetic - AssertionError\n"
    )
    stream = swebench_lite_oracle.execution_log("tests", raw, None)["stdout"]
    assert stream["original_bytes"] > 4_000_000
    assert stream["retained_bytes"] == swebench_lite_oracle.DIAGNOSTIC_STREAM_LIMIT_BYTES
    assert stream["sha256"] == hashlib.sha256(raw).hexdigest()
    assert b"synthetic-actual-value" not in base64.b64decode(stream["content"])
    assert b"synthetic-expected-value" not in base64.b64decode(stream["content"])
    assert retained_failure_bytes(stream["failure_capture"]) == failure
    assert_original_byte_ranges(raw, stream["failure_capture"], [failure])


@pytest.mark.parametrize("color", ["no", "yes"])
def test_real_pytest_long_parameter_keeps_failure_and_value_diff(tmp_path, color):
    test_file = tmp_path / "test_synthetic_failure.py"
    test_file.write_text(
        "import pytest\n\n"
        "@pytest.mark.parametrize('actual,expected', "
        "[('synthetic-actual-value', 'synthetic-expected-value')], "
        "ids=['public-synthetic-' + 'x' * 240])\n"
        "def test_synthetic_failure(actual, expected):\n"
        "    print('SYNTHETIC_BULK_CAPTURE\\n' * 100_000)\n"
        "    assert actual == expected\n",
        encoding="utf-8",
    )
    config = tmp_path / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    environment = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="",
                       COLUMNS="80")
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-c", str(config), "-q", "--tb=long",
         f"--color={color}", "-p", "no:cacheprovider", str(test_file)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    assert b"1 failed" in result.stdout
    assert len(result.stdout) > 2_000_000
    if color == "no":
        assert any(
            line.startswith(b"_ test_synthetic_failure[public-synthetic-")
            and line.endswith(b"] _")
            for line in result.stdout.splitlines()
        )
    else:
        assert b"\x1b[" in result.stdout
    stream = swebench_lite_oracle.execution_log("tests", result.stdout, result.stderr)["stdout"]
    assert stream["sha256"] == hashlib.sha256(result.stdout).hexdigest()
    capture = stream["failure_capture"]
    retained = retained_failure_bytes(capture)
    plain = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", retained)
    assert capture["recognized_block_count"] == capture["retained_block_count"] == 1
    assert b"assert actual == expected" in plain
    assert b"- synthetic-expected-value" in plain
    assert b"+ synthetic-actual-value" in plain
    assert b"SYNTHETIC_BULK_CAPTURE\n" not in plain
    tail = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", base64.b64decode(stream["content"]))
    assert b"assert actual == expected" not in tail
    assert re.search(rb"(?m)^E[ \t]+[-+] synthetic-(?:actual|expected)-value\r?$", tail) is None
    assert_original_byte_ranges(result.stdout, capture, [retained])
