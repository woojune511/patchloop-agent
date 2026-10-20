"""Separate schema-owned intent from public execution data for a fixed ablation.

This changes ranking text only. The source body, its identity, returned body and
excerpt renderer stay untouched. It does not certify that observed text is true.
"""
from __future__ import annotations

import copy

from patchloop.dev.history_search import PublicHistory

PROJECTION = "execution-evidence-v1"
MUTATION_ANNOTATIONS = (
    "hypothesis", "expected_behavior", "causal_revision", "requirement_ref", "behavior_cases",
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
    return {"observed": observed, "annotations": annotations}


def observed_body(record):
    return separate(record["body"])["observed"]


class EvidenceHistory(PublicHistory):
    """Same BM25 math and raw response bodies; only the indexed fields change."""

    def rank(self, query):
        index = PublicHistory()
        index.records = {key: {**record, "body": observed_body(record)}
                         for key, record in self.records.items()}
        # Keep the original excerpt selection fixed to isolate ranking-text effects.
        index._passages = self._passages
        order, excerpts = index.rank(query)
        return [(score, self.records[r["record_id"]]) for score, r in order], excerpts
