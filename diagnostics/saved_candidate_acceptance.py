"""One opaque saved-candidate evaluation, invoked as an isolated host subprocess.

The caller owns public check receipts. ``--public-checks-passed`` attests that the
registered public regression checks passed on this exact diff; diagnostic cases
may fail independently. This is a synthetic operator submission, not agent finish.
No evaluator output is returned to the model. Never import task packages in the
parent: this module loads them only inside its redirected evaluation function.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

RUN_ID = "run_dev_saved_candidate_acceptance"
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ENVIRONMENT = (
    "PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "COMSPEC", "PATHEXT",
    "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "USERPROFILE", "HOME",
    "APPDATA", "LOCALAPPDATA", "SYSTEMDRIVE", "HOMEDRIVE", "HOMEPATH",
)


def sanitized_environment():
    """Read only OS/runtime allowlisted values, never provider credentials."""
    return {key: os.environ[key] for key in _ENVIRONMENT if key in os.environ}


def _runtime():
    # Called only after environment sanitization and private-output redirection.
    from patchloop.artifacts import ArtifactStore
    from patchloop.contracts import ModelConfig, RunManifest
    from patchloop.deadline import ExecutionDeadline
    from patchloop.dev.contracts import dev_tool_surface_hash
    from patchloop.dev.state import DevJournal
    from patchloop.git_execution import run_git
    from patchloop.prepared_source import load_source
    from patchloop.repository import WorkspaceManager
    from patchloop.runtime import git_commit, repository_root, runtime_content_hash
    from patchloop.sandbox.runner import DockerSandbox
    from patchloop.task_loader import load_task_package
    from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
    from patchloop.verifier.core import EvaluationEngine

    return SimpleNamespace(ArtifactStore=ArtifactStore, ModelConfig=ModelConfig,
        RunManifest=RunManifest, ExecutionDeadline=ExecutionDeadline, DevJournal=DevJournal,
        dev_tool_surface_hash=dev_tool_surface_hash, run_git=run_git, load_source=load_source,
        WorkspaceManager=WorkspaceManager, git_commit=git_commit, repository_root=repository_root,
        runtime_content_hash=runtime_content_hash, DockerSandbox=DockerSandbox,
        load_task_package=load_task_package, canonical_json=canonical_json,
        sha256_bytes=sha256_bytes, sha256_json=sha256_json, utc_now=utc_now,
        EvaluationEngine=EvaluationEngine)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _paths(args):
    repo = Path(__file__).resolve().parents[1]
    public = Path(args.public_task).resolve()
    workspace = Path(args.workspace).resolve()
    prepared = Path(args.prepared_source).resolve()
    root = Path(args.output_root).resolve()
    _require(public.name == "public.yaml" and public.is_file()
             and public.is_relative_to(repo / "tasks/dev-train"), "unregistered public task")
    _require(workspace.is_dir() and prepared.is_file(), "saved source is unavailable")
    _require(all(not root.is_relative_to(path) and not path.is_relative_to(root)
                 for path in (repo, workspace, prepared.parent)), "output overlaps an input")
    _require(_HASH.fullmatch(args.expected_diff_hash)
             and _HASH.fullmatch(args.prepared_source_hash), "invalid input hash")
    _require(1 <= args.deadline_seconds <= 390, "invalid deadline")
    return public, workspace, prepared, root


def _evaluate(args, paths, runtime, journal, store, summary):
    public_path, workspace, prepared, _ = paths
    deadline = runtime.ExecutionDeadline.from_remaining(args.deadline_seconds)
    package = runtime.load_task_package(public_path.parent)
    _require(package.public.split == "dev-train", "task is not dev-train")
    expected = args.expected_diff_hash
    source, _ = runtime.load_source(prepared, package.public.repository.url,
                                   package.public.repository.base_commit,
                                   expected_hash=args.prepared_source_hash, deadline=deadline)
    head = runtime.run_git(workspace, "rev-parse", "HEAD", deadline=deadline).stdout.strip()
    _require(head == source.git_commit, "saved candidate base changed")
    diff = runtime.WorkspaceManager.diff_summary(workspace, deadline=deadline)
    _require(diff.patch_hash == expected and diff.changed_files and not diff.untracked_files,
             "saved candidate differs from the sealed patch")
    sandbox = runtime.DockerSandbox(package.environment.evaluator_image)
    _require(sandbox.image_identity(deadline=deadline) == package.environment.image_digest,
             "existing evaluator image is unavailable or changed")
    manager = runtime.WorkspaceManager(
        runtime.repository_root() / "fixtures/repositories", paths[3] / "workspaces",
        prepared_source=prepared, prepared_source_hash=args.prepared_source_hash)
    submitted = store.put_text(diff.patch, "text/x-diff")
    _require(submitted.content_hash == expected, "patch artifact does not match candidate")
    model = runtime.ModelConfig(provider="mock", model_id="operator-saved-candidate-no-model")
    manifest = runtime.RunManifest(
        run_id=RUN_ID, task_id=package.public.task_id, task_version=package.public.task_version,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash, private_spec_hash=package.private_spec_hash,
        task_content_hash=package.task_content_hash,
        runtime_content_hash=runtime.runtime_content_hash(),
        model_hash=runtime.sha256_json(model.model_dump(mode="json")),
        tool_surface_hash=runtime.dev_tool_surface_hash(),
        sandbox_identity_hash=runtime.sha256_json({"backend": "docker",
            "evaluator_image": package.environment.evaluator_image,
            "image_digest": package.environment.image_digest}),
        submitted_patch_content_hash=expected, visible_check_diff_hash=expected,
        submitted_changed_files=diff.changed_files, harness_git_commit=runtime.git_commit(
            deadline=deadline), model=model, sandbox_backend="docker",
        evaluator_image_digest=package.environment.image_digest,
        wall_time_seconds=args.deadline_seconds, created_at=runtime.utc_now())
    manifest_raw = runtime.canonical_json(manifest.model_dump(mode="json")) + "\n"
    store.write_text_immutable(store.root / "runs" / RUN_ID / "manifest.json", manifest_raw)
    summary.update({"manifest_hash": runtime.sha256_bytes(manifest_raw.encode()),
                    "patch_artifact_hash": submitted.content_hash,
                    "public_source_hash": runtime.sha256_bytes(public_path.read_bytes()),
                    "task_content_hash": package.task_content_hash,
                    "evaluator_image_digest": package.environment.image_digest})
    journal.append("evaluation_bound", summary.copy())
    journal.append("evaluation_started", {"candidate_patch_hash": expected, "attempt": 1})
    summary["evaluator_dispatches"] = 1
    evaluation = runtime.EvaluationEngine(manager, sandbox, store).evaluate(
        public_path.parent, submitted.path, manifest, submitted_patch_artifact=submitted,
        deadline=deadline)
    artifact = store.put_json(evaluation.model_dump(mode="json"))
    summary["evaluation_artifact_hash"] = artifact.content_hash
    summary["evaluation_artifact_path"] = artifact.path
    verdicts = evaluation.verdicts.model_dump(mode="json")
    for public, internal in (("acceptance", "hidden_tests"), ("regression", "regression_tests"),
                             ("scope", "scope_policy"), ("safety", "safety_policy")):
        value = verdicts.get(internal)
        summary[public] = value if value in {"pass", "fail", "error", "not_run"} else "error"
    complete = evaluation.evaluation_status == "completed"
    summary.update({"evaluation_status": "completed" if complete else "not_completed",
                    "scope_compliant_success": evaluation.scope_compliant_success is True,
                    "saved_candidate_unchanged": runtime.WorkspaceManager.diff_summary(
                        workspace, deadline=deadline).patch_hash == expected})
    summary["stop_remaining"] = not (complete and summary["saved_candidate_unchanged"]
        and all(summary[key] in {"pass", "fail"}
                for key in ("acceptance", "regression", "scope", "safety")))
    summary["status"] = "COMPLETED" if not summary["stop_remaining"] else "EVALUATION_UNSETTLED"


def evaluate_saved_candidate(args):
    """Host-only entry; drop inherited credentials before loading runtime code."""
    environment = sanitized_environment()
    os.environ.clear()
    os.environ.update(environment)
    summary = {"schema": "saved-candidate-acceptance-v1", "official": False,
        "run_id": RUN_ID, "synthetic_operator_submission": True,
        "provider_calls": 0, "credential_reads": 0, "evaluator_dispatches": 0,
        "candidate_patch_hash": args.expected_diff_hash,
        "prepared_source_hash": args.prepared_source_hash,
        "public_checks_passed": args.public_checks_passed,
        "acceptance": "not_run", "regression": "not_run", "scope": "not_run",
        "safety": "not_run", "scope_compliant_success": False, "evaluation_status": "not_run",
        "public_checks_evidence": "caller_attested", "stop_remaining": True,
        "status": "PRECHECK_FAILED"}
    try:
        paths = _paths(args)
        root = paths[3]
        root.mkdir(parents=True, exist_ok=False)
    except Exception as error:
        return {**summary, "error_type": type(error).__name__}
    # A root is single-use even if preparation or execution is interrupted.
    (root / "invoked.once").write_text(RUN_ID + "\n", encoding="utf-8")
    runtime = journal = None
    with ((root / "engine-private.log").open("x", encoding="utf-8") as log,
          contextlib.redirect_stdout(log), contextlib.redirect_stderr(log)):
        try:
            runtime = _runtime()
            journal = runtime.DevJournal(root, RUN_ID)
            store = runtime.ArtifactStore(root / "artifacts")
            journal.append("evaluation_requested", {**summary,
                "operator_hash": runtime.sha256_bytes(Path(__file__).read_bytes())})
            if args.public_checks_passed:
                _evaluate(args, paths, runtime, journal, store, summary)
            else:
                summary.update(status="NOT_RUN_PUBLIC_CHECKS", stop_remaining=False)
        except BaseException as error:
            traceback.print_exc()
            summary.update(status="EVALUATION_UNCERTAIN" if summary["evaluator_dispatches"]
                           else "PRECHECK_FAILED", error_type=type(error).__name__,
                           stop_remaining=True)
        if journal is not None:
            try:
                journal.append("evaluation_finished", summary.copy())
                summary["journal_hash"] = runtime.sha256_bytes(journal.path.read_bytes())
            except BaseException as error:
                traceback.print_exc()
                summary.update(status="JOURNAL_UNCERTAIN", stop_remaining=True,
                               error_type=type(error).__name__)
    with (root / "summary.json").open("x", encoding="utf-8") as out:
        out.write(json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n")
    return summary


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    for name in ("public-task", "workspace", "expected-diff-hash", "prepared-source",
                 "prepared-source-hash", "output-root"):
        result.add_argument("--" + name, required=True)
    result.add_argument("--deadline-seconds", type=int, default=390)
    result.add_argument("--public-checks-passed", action="store_true",
                        help="Caller attests registered public regression PASS on this diff.")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        summary = evaluate_saved_candidate(args)
    except BaseException as error:
        # Output/log persistence can itself fail. Never emit an exception message
        # or traceback to the parent, and never invite a retry of that root.
        summary = {"schema": "saved-candidate-acceptance-v1", "official": False,
                   "status": "OPERATOR_UNCERTAIN", "stop_remaining": True,
                   "error_type": type(error).__name__}
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True), flush=True)
    return 2 if summary["stop_remaining"] else 0


if __name__ == "__main__":
    sys.exit(main())
