"""Read exact historical metadata for a new fork; never authorize ordinary resume."""

from __future__ import annotations

import json

from diagnostics.decision_sampler import require
from patchloop.dev.contracts import DevRunEnvelope
from patchloop.dev.cost import COMPLETION_RECOVERY_POLICY, completion_cost_contract
from patchloop.util import sha256_bytes


def read_checkpoint_envelope(source):
    """Validate the known predecessor contract without rewriting its source bytes.

    The returned historical contract is metadata, not the current execution
    contract. The fork must still construct a new current-runtime envelope.
    Ordinary DevJournal.load_envelope and resume validation remain unchanged.
    """
    path = source.root / "runs" / f"{source.run_id}.envelope.json"
    require(path.is_file() and not path.is_symlink(), "checkpoint envelope unavailable")
    raw = path.read_bytes()
    require(sha256_bytes(raw) == source.envelope_hash, "checkpoint envelope hash changed")
    data = json.loads(raw)
    require(data.get("schema_version") == "dev-run-envelope-v1"
            and data.get("run_id") == source.run_id, "checkpoint envelope identity changed")
    historical_contract = data.get("completion_cost_contract")
    adapted = False
    if data.get("completion_cost_policy") == COMPLETION_RECOVERY_POLICY:
        current = completion_cost_contract(
            COMPLETION_RECOVERY_POLICY,
            max_correction_output_tokens=data.get("max_correction_output_tokens"))
        if historical_contract != current:
            predecessor = {
                **current,
                "horizon": "completion-and-available-bounded-repair-v2",
                "reservation": "role-successors-plus-correction-v3",
                "role_calls": "existing-runner-path-slots-no-extra-calls",
            }
            require(historical_contract == predecessor, "unsupported historical cost contract")
            data = {**data, "completion_cost_contract": current}
            adapted = True
    validated = DevRunEnvelope.model_validate(data)
    if adapted:
        # Retain what the source said, after validating every other field. This
        # historical object still fails ordinary current-contract validation.
        validated = validated.model_copy(update={"completion_cost_contract": historical_contract})
    return validated
