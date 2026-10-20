"""Question-focused public history delivery; quoted data, never current proof.

The raw index remains the replay baseline. Runtime lookup ranks execution data,
returns originals first, and reduces only records that exceed the response bound.
"""

from __future__ import annotations

import copy

from patchloop.dev.history_search import MAX_ORIGINAL_CHARS, MAX_RESULT_CHARS, PublicHistory, tokens
from patchloop.dev.question_support import observed_functions
from patchloop.util import canonical_json

MUTATION_ANNOTATIONS = (
    "hypothesis",
    "expected_behavior",
    "causal_revision",
    "requirement_ref",
    "behavior_cases",
)


def separate(body):
    observed = copy.deepcopy(body)
    annotations = {}

    def move(path, keys):
        node = observed
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return
            node = node[key]
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    pointer = "/" + "/".join((*path, key))
                    annotations[pointer] = node.pop(key)

    # Only owned envelopes are classified. Never recursively remove arbitrary
    # keys from source spans, captured JSON, setup checks or supplied observations.
    tool = body.get("call", {}).get("tool")
    if tool in {"read_file", "search_files", "replace_text", "run_probe", "run_check", "run_tests"}:
        move(("call", "arguments"), ("turn_decision", "memory_update"))
    if tool in {"read_file", "search_files"}:
        move(("result", "output"), ("inspection_intent", "inspection_intent_ref"))
    if tool == "replace_text":
        move(("call", "arguments"), MUTATION_ANNOTATIONS)
        move(("result", "output", "mutation"), MUTATION_ANNOTATIONS)
    if tool == "run_probe":
        move(("call", "arguments"), ("question",))
        move(("result", "output"), ("question",))
    if tool:
        move(
            ("result",), ("memory_update_result", "plan_update_result", "working_notes_after_batch")
        )
    return {"observed": observed, "annotations": annotations}


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


def source_candidates(bundle, query):
    """Fallback source units, used only after a complete record fails to fit.

    Function names explicitly present in the query outrank incidental body matches.
    Parseable fragments need an observed dedent boundary to count as functions.
    This is a lexical ordering aid, not a resolved call graph or relevance verdict.
    There is no per-record function count limit. The caller admits as many units as
    actually fit in the serialized response, including lower-ranked functions.
    """
    result = copy.deepcopy(bundle)
    candidates, spans_first, terms = [], [], set(tokens(query))
    for pointer in sorted(SOURCE_LISTS):
        spans = result["fields"].get(pointer)
        if not isinstance(spans, list) or not spans:
            continue
        for index, span in enumerate(spans):
            content = span.get("content")
            if not isinstance(content, str):
                continue
            lines = content.splitlines(keepends=True)
            first = span.get("start_line", 1)
            observed = {
                (span["path"], span["file_hash"], first + i): (line.rstrip("\r\n"), 0, 0)
                for i, line in enumerate(lines)
            }
            functions = observed_functions(observed)
            units = []
            for fn in functions:
                start_line = min([fn.node.lineno, *[d.lineno for d in fn.node.decorator_list]])
                start = sum(map(len, lines[: start_line - first]))
                end = sum(map(len, lines[: fn.node.end_lineno - first + 1]))
                text = content[start:end]
                units.append(
                    (
                        int(fn.node.name.casefold() in terms),
                        len(terms & set(tokens(text))),
                        start,
                        end,
                        "observed_function",
                    )
                )
            # Even under pressure, first try each complete observed span. Function
            # slicing is the last fallback, not a reason to discard module context.
            spans_first.append(
                (
                    (max((u[0] for u in units), default=0), len(terms & set(tokens(content)))),
                    pointer,
                    index,
                    span,
                    {
                        "pointer": f"{pointer}/{index}/content",
                        "start": 0,
                        "end": len(content),
                        "text": content,
                        "unit": "observed_span",
                    },
                )
            )
            for named, overlap, start, end, kind in units:
                candidates.append(
                    (
                        (named, overlap),
                        pointer,
                        index,
                        span,
                        {
                            "pointer": f"{pointer}/{index}/content",
                            "start": start,
                            "end": end,
                            "text": content[start:end],
                            "unit": kind,
                        },
                    )
                )
    if not spans_first:
        return result, []
    for source_list in SOURCE_LISTS:
        if source_list in result["fields"] and result["fields"][source_list]:
            del result["fields"][source_list]
            result["omitted_fields"].append(source_list)
    result["omitted_fields"] = sorted(set(result["omitted_fields"]))
    units = []
    ordered = [
        *sorted(spans_first, key=lambda c: c[0], reverse=True),
        *sorted(candidates, key=lambda c: c[0], reverse=True),
    ]
    for _, pointer, index, span, excerpt in ordered:
        fields = {
            f"{pointer}/{index}/{key}": copy.deepcopy(value)
            for key, value in span.items()
            if key != "content"
        }
        units.append({"fields": fields, "excerpt": excerpt})
    return result, units


def render(baseline, records, *, max_chars=MAX_ORIGINAL_CHARS):
    """Whole originals first; reduce only after actual serialized size overflow.

    Ranking is independent of delivery. Full records get the first pass, followed
    by execution fields and then whole source units for records that could not fit.
    The outer ceiling cannot exceed the request-byte ceiling. The runner counts
    the complete request and only then requests the smaller overflow view if a
    fresh seed still cannot fit. Never estimate tokens or rewrite native history.
    """
    if baseline["query"] in records:
        return copy.deepcopy(baseline)
    result = copy.deepcopy(baseline)
    result["presentation"] = "full-first-evidence-v2"
    result["evidence_notice"] = (
        "Complete bodies are exact originals. model_annotation_paths identify authored intent "
        "or notes, not observations. Only records exceeding the serialized response limit are "
        "reduced; omitted fields are not delivered. Source excerpts are observed fragments, "
        "not the whole file. All records are historical, not current proof. Fetch record_id "
        "for the complete original or exact JSON pages."
    )
    for row in result["records"]:
        body = records.get(row["record_id"], {}).get("body")
        row.update(
            body=None,
            excerpt=None,
            excerpt_is_complete_record=False,
            delivery="metadata_only_evidence_budget",
        )
        row.pop("page", None)
        row.pop("evidence", None)
        if body is None:
            continue  # An overflow view cannot recover an already omitted record.
        row["model_annotation_paths"] = sorted(separate(body)["annotations"])
        call = body.get("call", {})
        row["candidate"] = (
            {
                "action_id": call.get("action_id"),
                "tool": call["tool"],
                "status": body.get("result", {}).get("status"),
            }
            if isinstance(call, dict) and "tool" in call
            else {"field": body.get("field"), "kind": row["kind"]}
        )

    def admit(index, **values):
        nonlocal result
        candidate = copy.deepcopy(result)
        candidate["records"][index].update(values)
        if len(canonical_json(candidate)) <= max_chars:
            result = candidate
            return True
        return False

    # Try every original before spending space on previews. An oversized record
    # must not suppress a smaller complete execution/counterexample ranked below it.
    for i, row in enumerate(result["records"]):
        if row["record_id"] in records:
            admit(i, body=copy.deepcopy(records[row["record_id"]]["body"]), delivery="complete")
    for i, row in enumerate(result["records"]):
        if (
            row["body"] is not None
            or row["kind"] != "public_tool_exchange"
            or row["record_id"] not in records
        ):
            continue
        bundle = execution_fields(records[row["record_id"]]["body"])
        if admit(i, evidence=bundle, delivery="evidence_fields"):
            continue
        partial, units = source_candidates(bundle, result["query"])
        whole_spans = set()
        for unit in units:
            excerpt = unit["excerpt"]
            if excerpt["pointer"] in whole_spans:
                continue
            candidate = copy.deepcopy(partial)
            candidate["fields"].update(unit["fields"])
            candidate["source_excerpts"].append(excerpt)
            if admit(i, evidence=candidate, delivery="evidence_fields"):
                partial = candidate
                if excerpt["unit"] == "observed_span":
                    whole_spans.add(excerpt["pointer"])
    return result


def overflow_result(result):
    """Project only a not-yet-delivered fresh seed after a measured size failure.

    The canonical action result and old native outputs stay immutable. All full
    bodies needed for the smaller view are already inside this public result;
    this neither searches again nor reads the repository or original journal.
    """
    if (
        result.tool != "search_history"
        or not isinstance(result.output, dict)
        or len(canonical_json(result.output)) <= MAX_RESULT_CHARS
    ):
        return result
    originals = {
        r["record_id"]: {"body": r["body"]}
        for r in result.output["records"]
        if r.get("body") is not None
    }
    output = render(result.output, originals, max_chars=MAX_RESULT_CHARS)
    return result.model_copy(update={"output": output})


class EvidenceHistory(PublicHistory):
    """Runtime search; record hashes and exact-ID reads still bind original bodies."""

    def rank(self, query):
        index = PublicHistory()
        index.records = {
            key: {**record, "body": separate(record["body"])["observed"]}
            for key, record in self.records.items()
        }
        order, _ = index.rank(query)
        return [(score, self.records[r["record_id"]]) for score, r in order], {}

    def search(self, query, *, current_diff_hash, offset=None):
        raw = super().search(query, current_diff_hash=current_diff_hash, offset=offset)
        return render(raw, self.records)
