"""Position-bound reuse of observed complete lines across one exact replacement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from patchloop.dev.context import SOURCE_OUTPUT_CHARS, source_lines, valid_observed_span
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@dataclass(frozen=True)
class SourceReplacement:
    before_bytes: bytes
    after_bytes: bytes
    offset: int
    old_text: str
    new_text: str

    def observed_fragments(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map only previously observed unchanged lines; never search for similar text.

        The caller verifies the admitted complete candidate and current target bytes.
        Raw hashes bind identity; offsets and source comparisons use normalized LF.
        Fragment merging removes overlap before applying the existing eight-span bound.
        """

        before = self.before_bytes.decode("utf-8").replace("\r\n", "\n")
        after = self.after_bytes.decode("utf-8").replace("\r\n", "\n")
        end = self.offset + len(self.old_text)
        if (
            not 0 <= self.offset <= end <= len(before)
            or before[self.offset:end] != self.old_text
            or before[:self.offset] + self.new_text + before[end:] != after
        ):
            raise ContractError("source rebinding does not match the exact replacement")
        before_hash = sha256_bytes(self.before_bytes)
        before_lines, after_lines = source_lines(before), source_lines(after)

        def line_starts(lines: list[str]) -> list[int]:
            starts, cursor = [], 0
            for line in lines:
                starts.append(cursor)
                cursor += len(line) + 1
            return starts

        starts = line_starts(before_lines)
        after_positions = {
            position: number for number, position in enumerate(line_starts(after_lines), 1)
        }
        delta = len(self.new_text) - len(self.old_text)
        observed: dict[int, tuple[str, int]] = {}
        for span in spans:
            if not valid_observed_span(span, before_lines, before_hash):
                continue
            for number in range(span["start_line"], span["end_line"] + 1):
                start = starts[number - 1]
                line_end = starts[number] if number < len(starts) else len(before)
                if line_end <= self.offset:
                    mapped = start
                elif start >= end:
                    mapped = start + delta
                else:
                    continue  # A touched line requires explicit post-image evidence.
                after_number = after_positions.get(mapped)
                content = before_lines[number - 1]
                if after_number is None or after_lines[after_number - 1] != content:
                    continue  # E.g. an insertion joins previously separate lines.
                seq = max(
                    int(span.get("last_observed_seq", 0)),
                    observed.get(after_number, ("", 0))[1],
                )
                observed[after_number] = (content, seq)

        fragments: list[dict[str, Any]] = []
        for number, (content, seq) in sorted(observed.items()):
            if (
                fragments and fragments[-1]["end_line"] + 1 == number
                and len(fragments[-1]["content"]) + 1 + len(content) <= SOURCE_OUTPUT_CHARS
            ):
                fragment = fragments[-1]
                fragment["end_line"] = number
                fragment["content"] += "\n" + content
                fragment["last_observed_seq"] = max(fragment["last_observed_seq"], seq)
            else:
                fragments.append({
                    "start_line": number, "end_line": number, "content": content,
                    "last_observed_seq": seq,
                })
        return sorted(
            fragments, key=lambda item: (-item["last_observed_seq"], item["start_line"]),
        )[:8]
