"""Chunked CSV parsing with one audited end-of-input defect."""

import csv


def parse_chunks(chunks: list[str]) -> list[list[str]]:
    """Parse newline-delimited CSV records that may span input chunks."""

    rows: list[list[str]] = []
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        while "\n" in buffer:
            physical_line, buffer = buffer.split("\n", 1)
            if physical_line:
                rows.extend(csv.reader([physical_line]))
    return rows
