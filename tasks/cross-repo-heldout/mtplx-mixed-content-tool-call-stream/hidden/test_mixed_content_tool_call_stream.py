from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import mtplx.server.openai as openai_module
import pytest
from fastapi import HTTPException
from mtplx.server.openai import _ToolAwareContentStreamTranslator

WORKSPACE = Path("/workspace")
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "catalog",
            "description": "Search a catalog",
            "parameters": {"type": "object"},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive",
            "description": "Archive one record",
            "parameters": {"type": "object"},
        },
    },
]


def _translator(*, tools: list[dict[str, Any]] | None = None, chunk: int = 3):
    return _ToolAwareContentStreamTranslator(
        tools=TOOLS if tools is None else tools,
        argument_chunk_chars=chunk,
    )


def _block(name: str, **arguments: object) -> str:
    parameters = "".join(
        f"<parameter={key}>\n{json.dumps(value, ensure_ascii=False)}\n</parameter>\n"
        for key, value in arguments.items()
    )
    return (
        f"<tool_call>\n<function={name}>\n{parameters}"
        "</function>\n</tool_call>"
    )


def _run(chunks: list[str], *, tools: list[dict[str, Any]] | None = None):
    translator = _translator(tools=tools)
    deltas: list[dict[str, Any]] = []
    for text in chunks:
        deltas.extend(translator.feed("content", text))
    deltas.extend(translator.finish())
    return translator, deltas


def _content(deltas: list[dict[str, Any]]) -> str:
    return "".join(str(delta["content"]) for delta in deltas if "content" in delta)


def _calls(deltas: list[dict[str, Any]]) -> list[tuple[str, object]]:
    assembled: dict[int, dict[str, str]] = {}
    for delta in deltas:
        for item in delta.get("tool_calls", []):
            slot = assembled.setdefault(
                int(item["index"]),
                {"name": "", "arguments": ""},
            )
            function = item.get("function", {})
            if "name" in function:
                slot["name"] = str(function["name"])
            slot["arguments"] += str(function.get("arguments", ""))
    return [
        (assembled[index]["name"], json.loads(assembled[index]["arguments"]))
        for index in sorted(assembled)
    ]


def test_oracle_imports_the_submitted_streaming_module() -> None:
    module_path = Path(openai_module.__file__ or "").resolve()
    symbol_path = Path(
        inspect.getsourcefile(_ToolAwareContentStreamTranslator) or ""
    ).resolve()
    assert module_path.is_relative_to(WORKSPACE)
    assert symbol_path.is_relative_to(WORKSPACE)


def test_every_two_chunk_boundary_preserves_preamble_and_call() -> None:
    preamble = "Checking the inventory first.\n"
    payload = preamble + _block("catalog", query="café", limit=2)
    for boundary in range(len(payload) + 1):
        translator, deltas = _run([payload[:boundary], payload[boundary:]])
        assert _content(deltas) == preamble, boundary
        assert _calls(deltas) == [("catalog", {"query": "café", "limit": 2})], boundary
        assert translator.has_tool_calls is True
        assert "<tool_call" not in _content(deltas).lower()


def test_adversarial_many_piece_marker_boundaries_do_not_leak_markup() -> None:
    chunks = [
        "First inspect the record.",
        "\n<",
        "TO",
        "ol_",
        "ca",
        "ll>\n<function=catalog>\n<parameter=query>\n",
        '"needle"',
        "\n</parameter>\n</function>\n</tool_call>",
    ]
    _, deltas = _run(chunks)
    assert _content(deltas) == "First inspect the record.\n"
    assert _calls(deltas) == [("catalog", {"query": "needle"})]


def test_marker_matching_is_case_insensitive() -> None:
    block = _block("catalog", query="mixed").replace(
        "<tool_call>", "<ToOl_CaLl>"
    ).replace("</tool_call>", "</ToOl_CaLl>")
    _, deltas = _run(["Context: ", block])
    assert _content(deltas) == "Context: "
    assert _calls(deltas) == [("catalog", {"query": "mixed"})]


def test_disambiguated_lookalike_prefix_is_released_exactly_once() -> None:
    translator = _translator()
    deltas = translator.feed("content", "literal <tool_")
    deltas += translator.feed("content", "box and <tag> remain text")
    deltas += translator.finish()
    assert _content(deltas) == "literal <tool_box and <tag> remain text"
    assert _calls(deltas) == []
    assert translator.has_tool_calls is False


@pytest.mark.parametrize("lookalike", ["<tool_calls>", "<tool_calligraphy>"])
def test_lookalike_markers_round_trip_over_every_boundary(lookalike: str) -> None:
    payload = f"before {lookalike} after"
    for boundary in range(len(payload) + 1):
        translator, deltas = _run([payload[:boundary], payload[boundary:]])
        assert _content(deltas) == payload, boundary
        assert _calls(deltas) == [], boundary
        assert translator.has_tool_calls is False


def test_lookalike_is_content_before_a_later_real_call() -> None:
    preamble = "literal <tool_calls> then dispatch: "
    payload = preamble + _block("catalog", query="real")
    translator, deltas = _run(
        [payload[:12], payload[12:24], payload[24:37], payload[37:]]
    )
    assert _content(deltas) == preamble
    assert _calls(deltas) == [("catalog", {"query": "real"})]
    assert translator.has_tool_calls is True


def test_complete_marker_stem_flushes_as_content() -> None:
    payload = "literal <tool_call"
    translator = _translator()
    deltas = translator.feed("content", payload)
    assert _content(deltas) == "literal "
    deltas += translator.finish()
    assert _content(deltas) == payload
    assert translator.has_tool_calls is False


def test_preamble_and_multiple_calls_preserve_order_and_arguments() -> None:
    payload = (
        "I will perform two operations.\n"
        + _block("catalog", query="alpha", filters=["new", "sale"])
        + "\n"
        + _block("archive", record=17, force=False)
    )
    cuts = [payload[:7], payload[7:31], payload[31:54], payload[54:89], payload[89:]]
    _, deltas = _run(cuts)
    assert _content(deltas) == "I will perform two operations.\n"
    assert _calls(deltas) == [
        ("catalog", {"query": "alpha", "filters": ["new", "sale"]}),
        ("archive", {"record": 17, "force": False}),
    ]
    call_heads = [
        item
        for delta in deltas
        for item in delta.get("tool_calls", [])
        if "id" in item
    ]
    assert [item["index"] for item in call_heads] == [0, 1]
    assert len({item["id"] for item in call_heads}) == 2


def test_pure_text_and_no_tool_passthrough_remain_lossless() -> None:
    plain = "A plain response with literal <tool_box and a final <"
    translator, deltas = _run([plain[:19], plain[19:]])
    assert _content(deltas) == plain
    assert translator.has_tool_calls is False

    no_tools, passthrough = _run(["one ", "two"], tools=[])
    assert _content(passthrough) == "one two"
    assert no_tools.has_tool_calls is False


def test_tool_only_response_drops_only_leading_decoration() -> None:
    translator, deltas = _run(
        [" \n\t<tool_", "call>\n<function=archive>\n", "<parameter=record>\n4\n</parameter>\n"
         "</function>\n</tool_call>"]
    )
    assert _content(deltas) == ""
    assert _calls(deltas) == [("archive", {"record": 4})]
    assert translator.has_tool_calls is True


def test_non_content_fields_pass_through_without_corrupting_pending_text() -> None:
    translator = _translator()
    deltas = translator.feed("content", "Before <tool_")
    meta = translator.feed("reasoning", "observed")
    deltas += translator.feed(
        "content",
        "call>\n<function=catalog>\n<parameter=query>\n\"x\"\n</parameter>\n"
        "</function>\n</tool_call>",
    )
    deltas += translator.finish()
    assert meta == [{"reasoning": "observed"}]
    assert _content(deltas) == "Before "
    assert _calls(deltas) == [("catalog", {"query": "x"})]


def test_finish_flushes_a_dangling_marker_prefix_as_content() -> None:
    translator = _translator()
    deltas = translator.feed("content", "unfinished <tool_ca")
    deltas += translator.finish()
    assert _content(deltas) == "unfinished <tool_ca"
    assert _calls(deltas) == []


def test_completed_calls_allow_whitespace_but_reject_later_text() -> None:
    block = _block("archive", record=9)

    okay = _translator()
    okay.feed("content", block)
    assert _calls(okay.finish()) == [("archive", {"record": 9})]
    assert okay.feed("content", " \n\t") == []
    assert okay.finish() == []

    rejected = _translator()
    rejected.feed("content", block)
    rejected.finish()
    assert rejected.feed("content", "unexpected") == []
    with pytest.raises(HTTPException) as exc_info:
        rejected.finish()
    assert exc_info.value.status_code == 422
    assert "text after tool_call block" in str(exc_info.value.detail)


def test_same_buffer_text_after_a_completed_call_is_rejected() -> None:
    translator = _translator()
    translator.feed("content", _block("archive", record=5) + "unexpected")
    with pytest.raises(HTTPException) as exc_info:
        translator.finish()
    assert exc_info.value.status_code == 422
    assert "text outside tool_call block" in str(exc_info.value.detail)


def test_text_arriving_before_finish_is_rejected() -> None:
    translator = _translator()
    translator.feed("content", _block("archive", record=6))
    translator.feed("content", "unexpected")
    with pytest.raises(HTTPException) as exc_info:
        translator.finish()
    assert exc_info.value.status_code == 422
    assert "text outside tool_call block" in str(exc_info.value.detail)


def test_non_whitespace_between_two_calls_is_rejected() -> None:
    translator = _translator()
    translator.feed(
        "content",
        _block("catalog", query="first")
        + "interleaved prose"
        + _block("archive", record=7),
    )
    with pytest.raises(HTTPException) as exc_info:
        translator.finish()
    assert exc_info.value.status_code == 422
    assert "text outside tool_call block" in str(exc_info.value.detail)


def test_whitespace_residue_around_and_between_calls_remains_valid() -> None:
    payload = (
        _block("catalog", query="first")
        + " \n\t"
        + _block("archive", record=8)
        + "\n "
    )
    translator, deltas = _run([payload])
    assert _content(deltas) == ""
    assert _calls(deltas) == [
        ("catalog", {"query": "first"}),
        ("archive", {"record": 8}),
    ]
    assert translator.has_tool_calls is True


def test_non_streaming_parser_still_allows_an_assistant_preamble() -> None:
    calls = openai_module._parse_generated_tool_calls(
        "non-streaming preamble\n" + _block("catalog", query="direct"),
        tools=TOOLS,
    )
    assert calls is not None
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "catalog"
    assert json.loads(calls[0]["function"]["arguments"]) == {"query": "direct"}


def test_small_argument_deltas_reconstruct_unicode_and_nested_values() -> None:
    payload = "Plan: " + _block(
        "catalog",
        query="서울 café",
        options={"limit": 3, "exact": True},
    )
    translator = _ToolAwareContentStreamTranslator(
        tools=TOOLS,
        argument_chunk_chars=1,
    )
    deltas = translator.feed("content", payload)
    deltas += translator.finish()
    assert _content(deltas) == "Plan: "
    assert _calls(deltas) == [
        (
            "catalog",
            {"query": "서울 café", "options": {"limit": 3, "exact": True}},
        )
    ]
