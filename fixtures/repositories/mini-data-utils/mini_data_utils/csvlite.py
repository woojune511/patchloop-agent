"""A deliberately small CSV reader with one audited defect."""

import csv


def parse_rows(text: str) -> list[list[str]]:
    """Parse CSV text into rows while preserving quoted values."""

    rows: list[list[str]] = []
    for physical_line in text.splitlines():
        rows.extend(csv.reader([physical_line]))
    return rows

