"""Registered file transactions using the existing mutation journal and budget."""

from __future__ import annotations

from dataclasses import dataclass

from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import file_transaction as transaction
from patchloop.dev.contracts import FileEditIntent
from patchloop.dev.source_rebinding import SourceReplacement
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import GitExecutionUncertain
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.policy import _is_test_path, validate_test_addition, verify_scope


def schema():
    raw = FileEditIntent.model_json_schema()
    definitions = raw.pop("$defs", {})

    def project(value):
        if isinstance(value, list):
            return [project(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            return project(definitions[value["$ref"].rsplit("/", 1)[1]])
        result = {key: project(item) for key, item in value.items()
                  if key not in {"title", "default"}}
        if result.get("type") == "object":
            result["required"] = list(result["properties"])
        return result

    raw["properties"].pop("repair_prediction")
    return {"type": "function", "name": "edit_files", "strict": True,
            "description": (
                "Apply one atomic transaction across up to 16 allowed files, or undo an "
                "earlier accepted mutation by action ID. Set edits or undo_action_id, "
                "and set the other to null. Each path appears once. For an existing file, "
                "old_text is an exact observed anchor; occurrence is an integer or all. "
                "For a new file, old_text is null, occurrence is 1, and new_text is its "
                "complete content. Never overwrite an existing file with a create. "
                "New pytest modules must match the project's python_files naming rules; "
                "explicit-file execution alone does not ensure directory discovery. "
                "Undo requires the affected files still match that action's result; "
                "unrelated later edits remain. Each accepted batch or undo consumes one "
                "edit slot and invalidates checks for the old diff. Scope and preservation "
                "of original tests still apply. No shell, rename or arbitrary deletion."
            ), "parameters": project(raw)}


@dataclass(frozen=True)
class PreparedEdit:
    intent: FileEditIntent
    changes: list[transaction.FileChange]
    packet: dict
    candidate: DiffSummary
    patch: str
    anchor_ids: tuple[str, ...]
    test_only: bool


def _store(gateway):
    return ArtifactStore(gateway.journal.root / "artifacts")


def _undo(gateway, action_id):
    starts = {}
    for event in gateway.journal.events():
        payload = event["payload"]
        if event["event_type"] == "action_started":
            starts[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            if result["action_id"] != action_id:
                continue
            start = starts.get(action_id, {})
            if (result["status"] != "succeeded" or not start.get("file_transaction")
                    or start.get("input_hash") != result["input_hash"]
                    or result["workspace_diff_hash"] != start.get(
                        "mutation_expected_worktree_diff_hash")):
                raise ContractError("undo requires an accepted mutation with durable file images")
            return transaction.reverse_changes(transaction.load_changes(
                _store(gateway), start["file_transaction"]))
    raise ContractError("undo_action_id does not name a completed mutation in this run")


def _check_path(gateway, path):
    if not gateway._path_allowed(path):
        raise ContractError(f"file transaction path is outside the mutation scope: {path}")


def _check_test(gateway, change):
    constraints = gateway.public_task.constraints
    if not (_is_test_path(change.path) or any(
            change.path.startswith(root + "/") for root in constraints.additive_test_roots)):
        return
    if change.after is None:
        # Undo may remove only a file whose recorded preimage was absent.
        from patchloop.git_execution import run_git

        base = run_git(gateway.workspace, "show", f"HEAD:{change.path}", text=False,
                       check=False, deadline=gateway.deadline)
        if base.returncode == 0:
            raise ContractError("undo cannot remove an original test file")
        return
    validate_test_addition(gateway.workspace, change.path, change.after, constraints,
                           deadline=gateway.deadline)


def prepare(gateway, arguments, baseline):
    if gateway.accepted_mutations >= gateway.limits.max_accepted_mutations:
        raise ContractError("accepted mutation limit reached")
    intent = FileEditIntent.model_validate(arguments)
    if gateway.current_diff.untracked_files:
        raise ContractError("file transaction refuses unrelated untracked files")
    anchors = []
    if intent.undo_action_id:
        changes = _undo(gateway, intent.undo_action_id)
    else:
        changes = []
        for edit in intent.edits:
            path = safe_relative_path(edit.path)
            _check_path(gateway, path)
            if edit.old_text is None:
                if edit.occurrence != 1:
                    raise ContractError("new file creation requires occurrence=1")
                changes.append(transaction.FileChange(path, None, edit.new_text.encode("utf-8")))
            else:
                validated = gateway._validate_replacement_intent({
                    **edit.model_dump(), "hypothesis": intent.hypothesis,
                    "expected_behavior": intent.expected_behavior,
                })
                anchors.extend(validated.anchor_evidence_span_ids)
                changes.append(transaction.FileChange(
                    path, validated.before_bytes, validated.after_bytes))
    for change in changes:
        _check_path(gateway, change.path)
        _check_test(gateway, change)
    from patchloop.dev.test_discovery import validate_new_test_names

    validate_new_test_names(gateway, changes)
    candidate, patch = transaction.preview_transaction(
        gateway.workspace, changes, baseline_diff_hash=baseline, deadline=gateway.deadline)
    scope = verify_scope(candidate, gateway.public_task.constraints)
    if not scope.passed:
        raise ContractError("mutation violates scope: " + "; ".join(scope.violations),
                            details={"violations": scope.details.get("typed_violations", [])})
    packet = transaction.save_changes(_store(gateway), changes, workspace=gateway.workspace)
    return PreparedEdit(intent, transaction.load_changes(_store(gateway), packet), packet,
                        candidate, patch, tuple(dict.fromkeys(anchors)),
                        all(gateway._validated_test_only(c.path) for c in changes))


def prediction_arguments(arguments):
    """A bounded test prediction still selects exactly one edited test file."""
    edits = arguments.get("edits")
    return {**arguments, "path": edits[0].get("path")} if (
        isinstance(edits, list) and len(edits) == 1 and isinstance(edits[0], dict)
    ) else arguments


def admission(prepared):
    paths = [change.path for change in prepared.changes]
    first = prepared.changes[0]
    return {"file_transaction": prepared.packet,
            "mutation_target_paths": paths,
            "mutation_target_path": first.path if len(paths) == 1 else None,
            "mutation_preimage_file_hash": sha256_bytes(first.before)
            if len(paths) == 1 and first.before is not None else None,
            "mutation_expected_postimage_file_hash": sha256_bytes(first.after)
            if len(paths) == 1 and first.after is not None else None,
            "mutation_generated_patch": prepared.patch,
            "mutation_test_only": prepared.test_only,
            "mutation_anchor_evidence_span_ids": list(prepared.anchor_ids)}


def apply(gateway, arguments, start, *, deadline=None, recovering=False):
    if start.get("mutation_admitted") is not True or not start.get("file_transaction"):
        raise RecoveryError("file transaction was not admitted before execution")
    intent = FileEditIntent.model_validate(arguments)
    changes = transaction.load_changes(_store(gateway), start["file_transaction"])
    transaction.validate_recovery(
        gateway.workspace, changes, baseline_diff_hash=start["baseline_diff_hash"],
        candidate_diff_hash=start["mutation_expected_worktree_diff_hash"], deadline=deadline)
    if recovering and gateway.deadline is not None:
        def before_image(change):
            _, target = transaction.checked_target(gateway.workspace, change.path)
            return (target.read_bytes() if target.exists() else None) == change.before

        if all(before_image(change) for change in changes):
            # A receipt alone does not authorize starting new work after expiry.
            gateway.deadline.check()
    executor = transaction.reconcile_changes if recovering else transaction.apply_changes
    executor(gateway.workspace, changes, deadline=deadline)
    try:
        return result(gateway, intent, arguments, start, changes, deadline=deadline)
    except GitExecutionUncertain:
        raise
    except Exception:
        try:
            transaction.reconcile_changes(gateway.workspace, transaction.reverse_changes(changes),
                                          deadline=ExecutionDeadline.from_remaining(5))
        except Exception as exc:
            raise transaction.FileTransactionUncertain(
                "file transaction result failed and rollback could not be confirmed",
                details={"file_transaction_uncertain": True},
            ) from exc
        raise


def result(gateway, intent, arguments, start, changes, *, deadline=None):
    summary = WorkspaceManager.diff_summary(gateway.workspace, deadline=deadline)
    if summary.patch_hash != start["mutation_expected_worktree_diff_hash"]:
        raise RecoveryError("file transaction differs from admitted candidate")
    evidence, rebound = [], []
    for change in changes:
        if change.after is not None:
            replacement = SourceReplacement.from_file_images(change.before or b"", change.after)
            before = replacement.before_bytes.decode("utf-8").replace("\r\n", "\n")
            focus = before[:replacement.offset].count("\n") + 1
            span = gateway._mutation_postimage_evidence(
                path=change.path, focus_start_line=focus,
                focus_line_count=max(1, replacement.new_text.count("\n") + 1),
                diff_hash=summary.patch_hash, deadline=deadline)
            if span is not None:
                evidence.append(span)
            # Reuse the existing eight-fragment bound for the whole transaction,
            # while preserving one bounded explicit postimage for every edited file.
            if change.before is not None and len(rebound) < 8:
                rebound.extend(gateway._revalidated_spans(
                    paths=[change.path], diff_hash=summary.patch_hash, replacement=replacement,
                    deadline=deadline,
                )[:8 - len(rebound)])
    patch = start["mutation_generated_patch"]
    return {"patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": [change.path for change in changes],
            "mutation_evidence": evidence[0] if evidence else None,
            "revalidated_spans": [*evidence[1:], *rebound],
            "file_transaction_hash": sha256_json(start["file_transaction"]),
            "mutation": {"hypothesis": intent.hypothesis,
                "expected_behavior": intent.expected_behavior,
                "plan_hash": sha256_json(arguments), "changed_hunk": patch,
                "postimage_evidence_span_id": evidence[0]["span_id"] if evidence else None,
                "evidence_binding": "gateway_current_observation",
                "replacement_hash": sha256_json(arguments), "causal_revision": None,
                "changed_files": summary.changed_files, "diff_hash": summary.patch_hash,
                "undo_action_id": intent.undo_action_id}}


def validate_pending(workspace, journal, start, *, deadline=None):
    changes = transaction.load_changes(ArtifactStore(journal.root / "artifacts"),
                                       start["file_transaction"])
    transaction.validate_recovery(
        workspace, changes, baseline_diff_hash=start["baseline_diff_hash"],
        candidate_diff_hash=start["mutation_expected_worktree_diff_hash"], deadline=deadline)
