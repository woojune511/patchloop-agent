"""Read-only preparation/receipt audit for actual inputs, including public handoffs.

Dependency identities are public execution provenance. They belong in verified probe
receipts, whereas preparation host paths and prepared-source identities stay absent.
This audit does not replace request/usage, public-state or annotation audits.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.conversation import SEGMENT_RULES
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.probe_observation import project_probe_result
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

_ANNOTATIONS = {"memory_update_result", "plan_update_result", "working_notes_after_batch"}


def _strings(value):
    """Also inspect JSON inside content/output strings, where paths are escaped."""
    if isinstance(value, dict):
        for key, part in value.items():
            yield key
            yield from _strings(part)
    elif isinstance(value, list):
        for part in value:
            yield from _strings(part)
    elif isinstance(value, str):
        yield value
        if value.lstrip().startswith(("{", "[")):
            try:
                decoded = json.loads(value)
            except ValueError:
                return
            yield from _strings(decoded)


def _absent(value, forbidden, label, *, paths=False):
    def normalize(text):
        return text.replace("\\", "/").casefold() if paths else text
    needles = [normalize(v) for v in forbidden if v]
    if any(needle in normalize(text) for text in _strings(value) for needle in needles):
        raise ContractError(f"{label} in actual model input")


def audit_preparation_delivery(
    native: list[dict], *, probe_results: dict[str, dict],
    probe_dependencies: dict | None = None, probe_profile_hash: str | None = None,
    prepared_source_hash: str | None = None, preparation_paths=(),
) -> list[dict]:
    """Match supplied preceding receipts; never substitute them for missing input.

    Callers must validate input hashes and journal order first. Only native outputs
    and registered public archive exchanges are receipt locations. Annotation delivery
    has its own audit; annotations cannot carry otherwise forbidden preparation data.
    """
    _absent(native, preparation_paths, "preparation host path", paths=True)
    _absent(native, [prepared_source_hash, "prepared_source"], "prepared-source metadata")
    residual = copy.deepcopy(native)
    deliveries = []

    def receipt(item, position, location):
        if item.get("type") != "function_call_output":
            return
        action_id = item.get("call_id")
        try:
            value = json.loads(item["output"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("malformed public tool output") from exc
        if not isinstance(value, dict):
            raise ContractError("malformed public tool result")
        if value.get("tool") != "run_probe" and action_id not in probe_results:
            return
        raw = probe_results.get(action_id)
        if raw is None:
            raise ContractError("probe delivery has no preceding durable receipt")
        expected = project_probe_result(raw)
        if (value.get("action_id") != action_id
                or {k: v for k, v in value.items() if k not in _ANNOTATIONS} != expected):
            raise ContractError("probe delivery differs from its durable public receipt")
        output = value["output"]
        policy = output.get("execution_policy")
        dependencies = None
        if policy is not None:
            dependencies = policy.get("dependencies")
            if (dependencies != probe_dependencies
                    or output.get("execution_policy_hash") != sha256_json(policy)
                    or output.get("profile_hash") != probe_profile_hash
                    or policy.get("profile_hash") != probe_profile_hash):
                raise ContractError("probe execution policy differs from admitted identity")
            if dependencies is not None:
                # Remove only these verified fields from the audit's private copy.
                # Hashes in stdout, plans, arbitrary JSON or other fields still fail.
                dependencies.pop("manifest_hash")
                dependencies.pop("content_hash")
        elif raw["status"] != "failed":
            raise ContractError("executed probe is missing its execution policy")
        deliveries.append({
            "action_id": action_id, "native_index": position, "location": location,
            "execution_status": expected["observation"]["execution_status"],
            "dependency_identity_verified": dependencies is not None,
        })
        item["output"] = canonical_json(value)

    for position, item in enumerate(residual):
        receipt(item, position, "function_call_output")
        archive = SEGMENT_RULES.payload(item)
        if archive is None or archive["kind"] != PUBLIC_EVIDENCE_KIND:
            continue
        # Use the same public-exchange parser as the runtime and other diagnostics.
        exchanges = list(public_exchanges([item], archive_kind=PUBLIC_EVIDENCE_KIND))
        for exchange in exchanges:
            receipt(exchange, position, "quoted_public_exchange")
        archive["referenced_public_exchanges"] = exchanges
        item["content"] = canonical_json(archive)
    if probe_dependencies is not None:
        _absent(residual, [probe_dependencies["manifest_hash"], probe_dependencies["content_hash"]],
                "dependency identity outside a verified probe execution policy")
    return deliveries


def audit_run(state_root: Path, run_id: str) -> dict:
    """Audit a settled run without loading source, evaluator details or credentials."""
    state_root = state_root.resolve()
    if (not (state_root / "runs").is_dir()
            or not (state_root / "artifacts/objects/sha256").is_dir()):
        raise ContractError("audit requires an existing run and artifact store")
    journal = DevJournal(state_root, run_id)
    original = journal.path.read_bytes()
    envelope = journal.load_envelope()
    events = journal.events()
    terminal = journal.terminal()
    if terminal is None:
        raise ContractError("audit requires a settled run")
    dispatches = {e["payload"]["turn_id"] for e in events
                  if e["event_type"] == "provider_call_started"}
    dependencies = (envelope.probe_dependencies.model_dump(mode="json")
                    if envelope.probe_dependencies is not None else None)
    paths = [p for p in (envelope.prepared_source_path,
                         envelope.prepared_probe_dependencies_path) if p]
    paths += [str(Path(p).parent) for p in paths]
    store = ArtifactStore(state_root / "artifacts")
    preceding, rows = {}, []
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_finished":
            result = DevToolResult.model_validate(payload["result"])
            if result.tool == "run_probe":
                preceding[result.action_id] = result.model_dump(mode="json", exclude={"replayed"})
        if event["event_type"] != "turn_started":
            continue
        if envelope.provider != "mock" and payload["turn_id"] not in dispatches:
            continue
        native = runner._load_active_model_input(payload, store,
                                                context_policy=envelope.context_policy)
        delivered = audit_preparation_delivery(
            native, probe_results=preceding, probe_dependencies=dependencies,
            probe_profile_hash=envelope.probe_profile_hash,
            prepared_source_hash=envelope.prepared_source_hash, preparation_paths=paths,
        )
        rows.append({"turn_id": payload["turn_id"], "model_input_hash": payload["model_input_hash"],
                     "probe_deliveries": delivered})
    if len(rows) != terminal["payload"]["call_counts"]["model"]:
        raise ContractError("actual input count differs from settled model count")
    if journal.path.read_bytes() != original:
        raise ContractError("journal changed during read-only audit")
    return {"run_id": run_id, "journal_hash": sha256_bytes(original), "official": False,
            "actual_inputs_verified": len(rows), "inputs": rows,
            "preparation_paths_absent": True, "prepared_source_metadata_absent": True,
            "dependency_identity_scope_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_root", type=Path)
    parser.add_argument("run_id")
    args = parser.parse_args()
    print(canonical_json(audit_run(args.state_root, args.run_id)))


if __name__ == "__main__":
    main()
