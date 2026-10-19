"""Exact execution-field bundles for a frozen history-rendering comparison.

Ranking, record identity and exact-ID paging belong to the existing search. This
renderer never summarizes a program/output or certifies historical behavior.
"""

from __future__ import annotations

import copy

from diagnostics.semantic_history_index import separate
from patchloop.dev.history_search import MAX_RESULT_CHARS, passages, tokens
from patchloop.util import canonical_json

LAYOUT = "execution-fields-v1"
RECEIPTS = {"memory_update_result", "plan_update_result", "working_notes_after_batch"}
READ_ACCOUNTING = {
    "evidence_fingerprint",
    "evidence_gain",
    "evidence_repetition",
    "new_span_count",
    "read_observation_seq",
    "read_request_hash",
    "stagnation_signal",
}
SOURCE_LISTS = {"/result/output/spans", "/result/output/revalidated_spans"}


def at(body, pointer):
    value = body
    for part in pointer.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def execution_fields(body):
    """Whole exact values at owned schema locations, excluding authored intent."""
    split = separate(body)
    observed, omitted = split["observed"], list(split["annotations"])
    fields = {}

    def add(pointer, value):
        if value == at(body, pointer):
            fields[pointer] = copy.deepcopy(value)
        else:  # The mutation receipt can contain separated hypotheses.
            for key, part in value.items():
                add(pointer + "/" + key, part)

    for key, value in observed["call"].items():
        if key == "arguments":
            for name, part in value.items():
                add("/call/arguments/" + name, part)
        else:
            add("/call/" + key, value)
    for key, value in observed["result"].items():
        pointer = "/result/" + key
        if key in RECEIPTS:
            omitted.append(pointer)
        elif key == "output" and isinstance(value, dict):
            for name, part in value.items():
                path = pointer + "/" + name
                if (
                    observed["call"]["tool"] in {"read_file", "search_files"}
                    and name in READ_ACCOUNTING
                ):
                    omitted.append(path)
                else:
                    add(path, part)
        else:
            add(pointer, value)
    return {"fields": fields, "source_excerpts": [], "omitted_fields": sorted(omitted)}


def minimal(bundle, query):
    """Reserve one source window; execution programs/setup/outputs stay atomic."""
    result = copy.deepcopy(bundle)
    candidates = []
    terms = set(tokens(query))
    for pointer in sorted(SOURCE_LISTS):
        spans = result["fields"].get(pointer)
        if not isinstance(spans, list) or not spans:
            continue  # Preserve an observed empty search exactly.
        # Reference-only source has no text to excerpt; do not resolve unseen data.
        if not any(isinstance(s, dict) and isinstance(s.get("content"), str) for s in spans):
            continue
        del result["fields"][pointer]
        result["omitted_fields"].append(pointer)
        for index, span in enumerate(spans):
            content = span.get("content")
            if not isinstance(content, str):
                continue
            for excerpt in passages(content, f"{pointer}/{index}/content"):
                start, end = excerpt["start"], excerpt["end"]
                if start and content[start - 1] != "\n":
                    start = content.find("\n", start, end) + 1 or end
                if end < len(content) and content[end - 1] != "\n":
                    end = content.rfind("\n", start, end) + 1
                if start >= end:
                    continue
                excerpt = {**excerpt, "start": start, "end": end, "text": content[start:end]}
                score = len(terms & set(tokens(excerpt["text"])))
                candidates.append((score, excerpt, pointer, index, span))
    if candidates:
        _, excerpt, pointer, index, span = max(candidates, key=lambda item: item[0])
        result["source_excerpts"] = [excerpt]
        # Preserve the original coordinates; excerpt offsets never masquerade as
        # a complete original span or a current editable source observation.
        result["fields"].update(
            {
                f"{pointer}/{index}/{key}": copy.deepcopy(value)
                for key, value in span.items()
                if key != "content"
            }
        )
    result["omitted_fields"].sort()
    return result if len(canonical_json(result)) < len(canonical_json(bundle)) else bundle


def skeleton(baseline):
    result = copy.deepcopy(baseline)
    result["presentation"] = LAYOUT
    result["evidence_notice"] = (
        "Evidence fields and source excerpts quote exact original JSON pointers. "
        "Omitted fields are not supplied; an execution bundle is not a complete record "
        "or current verification. Fetch the original record by ID when needed."
    )
    for row in result["records"]:
        row.update(
            body=None,
            excerpt=None,
            excerpt_is_complete_record=False,
            delivery="metadata_only_evidence_budget",
        )
        row.pop("page", None)
    return result


def render(baseline, records, *, accept=lambda response: True):
    """Same eight candidates; minimum units first, source expansion second.

    accept is an optional local packing check. Rejected additions do not change
    the query, ranking, boundaries, budgets or reference selection.
    """
    if baseline["query"] in records:  # Explicit ID pages keep the existing contract.
        return copy.deepcopy(baseline), []
    result = skeleton(baseline)
    attempts, upgrades = [], []

    def assign(index, value, stage):
        candidate = copy.deepcopy(result)
        candidate["records"][index].update(value)
        within = len(canonical_json(candidate)) <= MAX_RESULT_CHARS
        admitted = within and accept(candidate)
        attempts.append(
            {
                "record_id": candidate["records"][index]["record_id"],
                "stage": stage,
                "admitted": admitted,
                "reason": "accepted" if admitted else "context" if within else "response",
            }
        )
        if admitted:
            result["records"][index] = candidate["records"][index]
        return admitted

    for index, row in enumerate(result["records"]):
        body = records[row["record_id"]]["body"]
        if "call" not in body or "result" not in body:
            assign(index, {"body": copy.deepcopy(body), "delivery": "complete"}, "minimum")
            continue
        full = execution_fields(body)
        core = minimal(full, result["query"])
        if (
            assign(index, {"evidence": core, "delivery": "evidence_fields"}, "minimum")
            and full != core
        ):
            upgrades.append((index, full))
    for index, full in upgrades:
        assign(index, {"evidence": full}, "source_expansion")
    assert len(canonical_json(result)) <= MAX_RESULT_CHARS and accept(result)
    return result, attempts
