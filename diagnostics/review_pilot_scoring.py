"""Post-submission operator scoring; never supplies agent context."""

import json
from pathlib import Path

from diagnostics.decision_sampler import require
from diagnostics.review_pilot_manifest import TASKS, score_isort, score_opensandbox
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RegisteredCheck, RunManifest, VerdictState
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now
from patchloop.verifier.core import EvaluationEngine


def require_completed_verdicts(verdicts):
    require(all(v in {VerdictState.PASS.value, VerdictState.FAIL.value}
                for v in verdicts.model_dump(mode="json").values()),
            "v2 evaluation did not complete")


def score(row, episode, episode_root, programs, output):
    output.mkdir()  # A score is single-use, even after a failed evaluator.
    journal = DevJournal(output, "run_dev_reviewscore")
    store = ArtifactStore(output / "artifacts")
    public_result = episode["result"]
    digest = public_result.get("artifact_hashes", {}).get("submitted_patch")
    if digest is None:
        result = {"status": "NOT_RUN", "reason": "no submitted patch"}
        journal.append("scoring_finished", result)
        return result
    workspace = Path(episode["workspace"]).resolve()
    require(workspace.is_relative_to(episode_root.resolve()), "workspace leaves episode")
    diff = WorkspaceManager.diff_summary(workspace)
    require(diff.patch_hash == digest, "submitted workspace changed")
    package = load_task_package(Path(row["evaluation_path"]))
    require(package.task_content_hash == row["evaluation_content_hash"], "evaluator changed")
    journal.append(
        "scoring_started",
        {
            "candidate_hash": digest,
            "evaluation_content_hash": package.task_content_hash,
            "model_calls": 0,
        },
    )
    result = {
        "candidate_hash": digest,
        "source_evaluation": public_result.get("evaluator"),
        "public_matrix": "NOT_APPLICABLE",
        "evaluation_version": package.public.task_version,
    }
    deadline = ExecutionDeadline.from_remaining(300)
    sandbox = DockerSandbox(package.environment.evaluator_image)
    require(
        sandbox.image_identity(deadline=deadline) == package.environment.image_digest,
        "scoring image changed",
    )
    if row["task"] in TASKS[:2]:
        program = programs[row["task"]]
        raw = Path(program["path"]).read_bytes()
        require(sha256_bytes(raw) == program["hash"], "public scoring program changed")
        check = RegisteredCheck(
            id="frozen-public-matrix",
            command=["/opt/conda/envs/testbed/bin/python", "-B", "-c", raw.decode()],
            timeout_seconds=60,
            environment={
                "PYTHONPATH": "/workspace/server" if row["task"] == TASKS[0] else "/workspace"
            },
        )
        observed = sandbox.run_check(workspace, check, deadline=deadline)
        journal.append(
            "public_matrix_executed",
            {
                "receipt": store.put_json(observed.__dict__).model_dump(mode="json"),
                "candidate_hash": digest,
            },
        )
        require(
            not observed.timed_out
            and not observed.cleanup_failed
            and not observed.deadline_exhausted
            and observed.exit_code == 0,
            "public scoring execution failed",
        )
        data = json.loads(observed.stdout)
        result["public_matrix"] = (
            score_opensandbox(data) if row["task"] == TASKS[0] else score_isort(data)
        )
    if row["task"] == TASKS[2]:
        # A new isolated v2 replay; the source v1 verdict above stays intact.
        parent = DevJournal(Path(row["source"]["root"]), row["source"]["run_id"]).load_envelope()
        manager = WorkspaceManager(
            repository_root() / "fixtures/repositories",
            output / "workspaces",
            prepared_source=Path(parent.prepared_source_path),
            prepared_source_hash=parent.prepared_source_hash,
        )
        submitted = store.put_text(diff.patch, "text/x-diff")
        model = ModelConfig(provider="mock", model_id="operator-final-patch-no-model")
        manifest = RunManifest(
            run_id="run_dev_reviewscorev2",
            task_id=package.public.task_id,
            task_version=package.public.task_version,
            base_commit=package.public.repository.base_commit,
            public_spec_hash=package.public_spec_hash,
            private_spec_hash=package.private_spec_hash,
            task_content_hash=package.task_content_hash,
            runtime_content_hash=runtime_content_hash(),
            model_hash=sha256_json(model.model_dump(mode="json")),
            tool_surface_hash=dev_tool_surface_hash(),
            sandbox_identity_hash=sha256_json(
                {
                    "backend": "docker",
                    "evaluator_image": package.environment.evaluator_image,
                    "image_digest": package.environment.image_digest,
                }
            ),
            submitted_patch_content_hash=digest,
            visible_check_diff_hash=digest,
            submitted_changed_files=diff.changed_files,
            harness_git_commit=git_commit(),
            model=model,
            sandbox_backend="docker",
            evaluator_image_digest=package.environment.image_digest,
            created_at=utc_now(),
        )
        store.write_text_immutable(
            store.root / "runs" / manifest.run_id / "manifest.json",
            canonical_json(manifest.model_dump(mode="json")) + "\n",
        )
        evaluation = EvaluationEngine(manager, sandbox, store).evaluate(
            Path(row["evaluation_path"]),
            submitted.path,
            manifest,
            submitted_patch_artifact=submitted,
            deadline=deadline,
        )
        result["separate_evaluation"] = evaluation.model_dump(mode="json")
        journal.append("separate_evaluation_finished", result["separate_evaluation"])
        require_completed_verdicts(evaluation.verdicts)
    require(
        WorkspaceManager.diff_summary(workspace).patch_hash == digest,
        "scoring altered submitted workspace",
    )
    result["status"] = "SCORED"
    journal.append("scoring_finished", result)
    return result
