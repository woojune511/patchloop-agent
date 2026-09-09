"""Deterministic projection of already observed public source text."""

from __future__ import annotations

import io
import json
import re
import tokenize
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from patchloop.util import sha256_json

SOURCE_OUTPUT_CHARS = 24_000
RETAINED_SOURCE_CHARS = 24_000
OBSERVED_SOURCE_INDEX_ENTRIES = 16
OBSERVED_SOURCE_INDEX_CHARS = 4_000
_PYTHON_HEADER = re.compile(
    r"^\s*(?:(async)\s+)?(def|class)\s+([^\W\d]\w*)\s*(?=[:\[(])"
)
_TRIPLE_QUOTED_TOKEN = re.compile(r"(?i:[rubf]*)(?:\"{3}|'{3})")
_BARE_TRIPLE_QUOTE = re.compile(r"(?:\"{3}|'{3})\s*(?:#.*)?")


def _visible_string_lines(lines: list[str], *, fragment_start_line: int) -> set[int]:
    """Suppress known literal bodies without claiming a fragment's enclosing state."""

    excluded: set[int] = set()
    seen_multiline_delimiter = False
    # Indentation outside the observed fragment is unknown. Flatten only this
    # lexical scratch copy; row numbers and the actual source evidence are unchanged.
    scratch = "\n".join(line.lstrip() for line in lines)
    try:
        for token in tokenize.generate_tokens(io.StringIO(scratch).readline):
            if token.type == tokenize.STRING:
                if _TRIPLE_QUOTED_TOKEN.match(token.string) and not seen_multiline_delimiter:
                    # A bare quote can close a string opened before this fragment.
                    # Choosing the opposite polarity would hide real headers until
                    # EOF. Keep lexical candidates, not a guessed string mask.
                    if fragment_start_line > 1 and _BARE_TRIPLE_QUOTE.fullmatch(
                        lines[token.start[0] - 1].strip()
                    ):
                        return set()
                    seen_multiline_delimiter = True
                excluded.update(range(token.start[0], token.end[0] + 1))
    except tokenize.TokenError as error:
        if error.args[0] == "EOF in multi-line string":
            if (
                not seen_multiline_delimiter and fragment_start_line > 1
                and _BARE_TRIPLE_QUOTE.fullmatch(lines[error.args[1][0] - 1].strip())
            ):
                return set()
            excluded.update(range(error.args[1][0], len(lines) + 1))
    except (IndentationError, SyntaxError):
        # A partial source fragment need not be a parseable Python program.
        pass
    return excluded


def build_observed_source_index(
    spans: Iterable[dict[str, Any]], *, editable_paths: Iterable[str] = ()
) -> dict[str, Any]:
    """Index observed Python header candidates, never unobserved source or extents.

    This is lexical navigation, not a parsed symbol table: a fragment can begin
    inside an unobserved multiline string. Only visibly opened literals can be
    excluded. The caller supplies current delivered spans; no source is reread.
    """

    observed: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    conflicting: set[tuple[str, str, int]] = set()
    for span in spans:
        path, file_hash = span.get("path"), span.get("file_hash")
        start, end, content = span.get("start_line"), span.get("end_line"), span.get("content")
        if (
            not isinstance(path, str) or not path.endswith((".py", ".pyi"))
            or not isinstance(file_hash, str) or not file_hash
            or type(start) is not int or type(end) is not int or not 1 <= start <= end
            or not isinstance(content, str)
        ):
            continue
        # A span's final empty element can be an observed blank line, unlike a
        # whole file's terminal newline. Its explicit range decides the length.
        lines = content.replace("\r\n", "\n").split("\n")
        if len(lines) != end - start + 1:
            continue
        by_line = observed[(path, file_hash)]
        for number, line in enumerate(lines, start):
            if number in by_line and by_line[number] != line:
                conflicting.add((path, file_hash, number))
            by_line[number] = line

    candidates: list[dict[str, Any]] = []
    for (path, file_hash), by_line in sorted(observed.items()):
        chunks: list[list[int]] = []
        for number in sorted(by_line):
            if (path, file_hash, number) in conflicting:
                continue
            if chunks and chunks[-1][-1] + 1 == number:
                chunks[-1].append(number)
            else:
                chunks.append([number])
        for chunk in chunks:
            lines = [by_line[number] for number in chunk]
            excluded = _visible_string_lines(lines, fragment_start_line=chunk[0])
            for offset, line in enumerate(lines):
                if offset + 1 in excluded:
                    continue
                match = _PYTHON_HEADER.match(line)
                if match is None or (match[1] and match[2] != "def"):
                    continue
                candidates.append({
                    "path": path,
                    "file_hash": file_hash,
                    "name": match[3],
                    "kind": "async_def" if match[1] else match[2],
                    "start_line": chunk[offset],
                })
    editable = set(editable_paths)
    candidates.sort(key=lambda item: (
        item["path"] not in editable, item["path"], item["start_line"], item["file_hash"]
    ))
    result: dict[str, Any] = {
        "entries": [],
        "omitted_count": len(candidates),
        "interpretation": (
            "Lexical Python header candidates from current delivered full source lines only. "
            "Not parsed symbols, complete function ranges, or semantic validation; unseen "
            "enclosing string state is unknown. Ambiguous bare-quote fragments retain lexical "
            "candidates. No source was read for this index."
        ),
    }
    for candidate in candidates:
        if len(result["entries"]) >= OBSERVED_SOURCE_INDEX_ENTRIES:
            break
        proposed = {
            **result,
            "entries": [*result["entries"], candidate],
            "omitted_count": result["omitted_count"] - 1,
        }
        if len(json.dumps(proposed, sort_keys=True)) <= OBSERVED_SOURCE_INDEX_CHARS:
            result = proposed
    return result


def normalize_source_text(text: str) -> str:
    """Normalize observed CRLF without imposing mutation-format restrictions."""
    return text.replace("\r\n", "\n")


def source_lines(text: str) -> list[str]:
    """Use one newline representation without inventing an extra EOF line."""

    lines = normalize_source_text(text).split("\n")
    if lines and not lines[-1]:
        lines.pop()
    return lines


def bounded_lines(
    lines: list[str], start: int, end: int, *, max_chars: int = SOURCE_OUTPUT_CHARS
) -> tuple[str, int, bool]:
    """Return only complete lines; the end always describes the returned body."""

    chosen: list[str] = []
    size = 0
    actual_end = start - 1
    requested_end = min(end, len(lines))
    for number in range(start, requested_end + 1):
        line = lines[number - 1]
        cost = len(line) + int(bool(chosen))
        if size + cost > max_chars:
            break
        chosen.append(line)
        size += cost
        actual_end = number
    return "\n".join(chosen), actual_end, actual_end < requested_end


def valid_observed_span(span: dict[str, Any], lines: list[str], file_hash: str) -> bool:
    start, end = span.get("start_line"), span.get("end_line")
    return (
        span.get("file_hash") == file_hash
        and type(start) is int
        and type(end) is int
        and 1 <= start <= end <= len(lines)
        and isinstance(span.get("content"), str)
        and span["content"] == "\n".join(lines[start - 1 : end])
    )


def spans_cover_range(spans: list[dict[str, Any]], start: int, end: int) -> bool:
    """Require a contiguous union, without silently filling an unobserved gap."""

    next_line = start
    for span in sorted(spans, key=lambda item: (item["start_line"], item["end_line"])):
        if span["end_line"] < next_line:
            continue
        if span["start_line"] > next_line:
            return False
        next_line = max(next_line, span["end_line"] + 1)
        if next_line > end:
            return True
    return False


@dataclass(frozen=True)
class SourceProjection:
    source_spans: tuple[dict[str, Any], ...]
    delivered_spans: tuple[dict[str, Any], ...]
    editable_paths: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    retained_content_chars: int
    omitted_observed_line_count: int
    omitted_pinned_ranges: tuple[dict[str, Any], ...] = ()
    omitted_observed_ranges: tuple[dict[str, Any], ...] = ()
    omitted_observed_range_count: int = 0


def project_observed_sources(
    spans: list[dict[str, Any]],
    *,
    native_spans: list[dict[str, Any]],
    priorities: list[tuple[str, int, int, int]],
    editable_paths: set[str],
    max_chars: int = RETAINED_SOURCE_CHARS,
) -> SourceProjection:
    """Merge equal source lines, select pinned ranges, then use remaining recency."""

    native_lines: set[tuple[str, str, int]] = set()
    for span in native_spans:
        native_lines.update(
            (span["path"], span["file_hash"], number)
            for number in range(span["start_line"], span["end_line"] + 1)
        )
    observed: dict[tuple[str, str, int], tuple[str, int, int]] = {}
    for span in spans:
        path, file_hash = span["path"], span["file_hash"]
        sequence = int(span.get("last_observed_seq", 0))
        for offset, line in enumerate(span["content"].split("\n")):
            number = span["start_line"] + offset
            priority = min([
                2 if path in editable_paths else 4,
                *(rank for item_path, lo, hi, rank in priorities if item_path == path
                  and lo <= number <= hi),
            ])
            key = (path, file_hash, number)
            previous = observed.get(key)
            if previous is None or sequence > previous[2]:
                observed[key] = (line, priority, sequence)

    groups: list[list[tuple[tuple[str, str, int], tuple[str, int, int]]]] = []
    for key, value in sorted(observed.items()):
        if key in native_lines:
            continue
        if (
            groups
            and groups[-1][-1][0][:2] == key[:2]
            and groups[-1][-1][0][2] + 1 == key[2]
            and groups[-1][-1][1][1:] == value[1:]
        ):
            groups[-1].append((key, value))
        else:
            groups.append([(key, value)])
    groups.sort(key=lambda group: (group[0][1][1], -group[0][1][2], group[0][0]))
    selected: dict[tuple[str, str, int], tuple[str, int, int]] = {}
    selected_keys: set[tuple[str, str, int]] = set()
    observed_keys = set(observed)
    used = 0
    omitted_pinned: list[dict[str, Any]] = []
    blocked: set[tuple[str, str, int]] = set()

    def incremental_cost(key: tuple[str, str, int], keys: set[tuple[str, str, int]]) -> int:
        path, file_hash, number = key
        return (
            len(observed[key][0])
            + int((path, file_hash, number - 1) in keys)
            + int((path, file_hash, number + 1) in keys)
        )

    for path, start, end, rank in sorted(set(priorities), key=lambda item: (item[3], item[:3])):
        if rank > 1:
            continue
        hashes = {key[1] for key in observed if key[0] == path}
        for file_hash in sorted(hashes):
            anchor_keys = {(path, file_hash, number) for number in range(start, end + 1)}
            if not anchor_keys <= observed_keys or anchor_keys & blocked:
                continue
            additions = sorted(anchor_keys - native_lines - selected_keys)
            proposed_keys = set(selected_keys)
            cost = 0
            for key in additions:
                cost += incremental_cost(key, proposed_keys)
                proposed_keys.add(key)
            if used + cost > max_chars:
                blocked.update(additions)
                omitted_pinned.append({"path": path, "start_line": start, "end_line": end})
                continue
            for key in additions:
                selected[key] = observed[key]
                selected_keys.add(key)
            used += cost
    for group in groups:
        for key, value in group:
            if key in selected or key in blocked:
                continue
            cost = incremental_cost(key, selected_keys)
            if used + cost > max_chars:
                break
            selected[key] = value
            selected_keys.add(key)
            used += cost

    by_source: dict[tuple[str, str], list[int]] = defaultdict(list)
    for path, file_hash, number in selected:
        by_source[(path, file_hash)].append(number)
    retained: list[dict[str, Any]] = []
    for (path, file_hash), numbers in sorted(by_source.items()):
        chunks: list[list[int]] = []
        for number in sorted(numbers):
            if chunks and chunks[-1][-1] + 1 == number:
                chunks[-1].append(number)
            else:
                chunks.append([number])
        for chunk in chunks:
            identity = {
                "path": path,
                "file_hash": file_hash,
                "start_line": chunk[0],
                "end_line": chunk[-1],
                "content": "\n".join(selected[(path, file_hash, n)][0] for n in chunk),
            }
            retained.append(
                {
                    "span_id": f"span_{sha256_json(identity).split(':', 1)[1][:16]}",
                    **identity,
                    "last_observed_seq": max(selected[(path, file_hash, n)][2] for n in chunk),
                }
            )
    retained.sort(
        key=lambda item: (
            min((rank for path, lo, hi, rank in priorities if path == item["path"]
                 and lo <= item["end_line"] and hi >= item["start_line"]),
                default=2 if item["path"] in editable_paths else 4),
            -item["last_observed_seq"], item["path"], item["start_line"],
        )
    )
    delivered = [*native_spans, *retained]
    visible_paths = {span["path"] for span in delivered if span["content"]}
    omitted_keys = observed_keys - native_lines - selected_keys
    omitted_ranges: list[dict[str, Any]] = []
    for path, file_hash, number in sorted(omitted_keys):
        if (
            omitted_ranges
            and omitted_ranges[-1]["path"] == path
            and omitted_ranges[-1]["file_hash"] == file_hash
            and omitted_ranges[-1]["end_line"] + 1 == number
        ):
            omitted_ranges[-1]["end_line"] = number
        else:
            omitted_ranges.append({
                "path": path, "file_hash": file_hash,
                "start_line": number, "end_line": number,
            })
    return SourceProjection(
        source_spans=tuple(retained),
        delivered_spans=tuple(delivered),
        editable_paths=tuple(sorted(visible_paths & editable_paths)),
        evidence_paths=tuple(sorted(visible_paths)),
        retained_content_chars=sum(len(span["content"]) for span in retained),
        omitted_observed_line_count=len(omitted_keys),
        omitted_pinned_ranges=tuple(omitted_pinned),
        omitted_observed_ranges=tuple(omitted_ranges[:12]),
        omitted_observed_range_count=len(omitted_ranges),
    )
