"""Deterministic projection of already observed public source text."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from patchloop.util import sha256_json

SOURCE_OUTPUT_CHARS = 24_000
RETAINED_SOURCE_CHARS = 24_000


def source_lines(text: str) -> list[str]:
    """Use one newline representation without inventing an extra EOF line."""

    lines = text.replace("\r\n", "\n").split("\n")
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
