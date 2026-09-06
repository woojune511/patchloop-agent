"""Durable provider-input boundaries for synthetic gateway transcripts."""

import json

import patchloop.dev.runner as runner
from patchloop.dev.conversation import history_metadata


def start_turn(journal, store, turn_id, *, context="{}", results=None, **extra):
    if results is None:
        results = journal.latest_tool_batch_results()
    items = runner._build_model_input(
        journal=journal, artifact_store=store, context=context, latest_tool_results=results,
    )
    artifact = store.put_json(items)
    return journal.append("turn_started", {
        "turn_id": turn_id,
        "model_input_artifact": artifact.model_dump(mode="json"),
        "model_input_hash": artifact.content_hash,
        "native_history": history_metadata(items),
        **extra,
    })


def input_context(items):
    assert items[1]["role"] == "developer"
    return json.loads(items[1]["content"])
