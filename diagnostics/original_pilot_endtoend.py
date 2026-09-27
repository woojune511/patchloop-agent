"""Submit known reference controls through the actual isolated evaluation engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from diagnostics.original_pilot_packages import NAMES
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RunManifest
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_json, utc_now
from patchloop.verifier.core import EvaluationEngine


def run(output):
    output = output.resolve()
    root = repository_root()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("external output required")
    output.mkdir(exist_ok=False)
    store = ArtifactStore(output / "artifacts")
    journal = DevJournal(output, "run_dev_originalpilotendtoend")
    manager = WorkspaceManager(root / "fixtures", output / "workspaces")
    for name, _, _ in NAMES.values():
        task = root / "tasks/dev-train" / name
        package = load_task_package(task)
        workspace = manager.create(
            "submission-" + name,
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        manager.apply_patch(workspace, task / "reference.patch")
        diff = manager.diff_summary(workspace)
        artifact = store.put_text(diff.patch, "text/x-diff")
        image = package.environment.evaluator_image
        digest = package.environment.image_digest
        run_id = "run_dev_" + name.replace("-", "")
        manifest = RunManifest(
            run_id=run_id,
            task_id=name,
            task_version=1,
            base_commit=package.public.repository.base_commit,
            public_spec_hash=package.public_spec_hash,
            private_spec_hash=package.private_spec_hash,
            task_content_hash=package.task_content_hash,
            runtime_content_hash=runtime_content_hash(),
            model_hash=sha256_json({"provider": "mock", "model": "mock-dev"}),
            tool_surface_hash=dev_tool_surface_hash(),
            sandbox_identity_hash=sha256_json(
                {"backend": "docker", "evaluator_image": image, "image_digest": digest}
            ),
            submitted_patch_content_hash=artifact.content_hash,
            visible_check_diff_hash=artifact.content_hash,
            submitted_changed_files=diff.changed_files,
            harness_git_commit=git_commit(),
            model=ModelConfig(provider="mock", model_id="mock-dev"),
            sandbox_backend="docker",
            evaluator_image_digest=digest,
            created_at=utc_now(),
        )
        store.write_text_immutable(
            store.root / "runs" / run_id / "manifest.json",
            canonical_json(manifest.model_dump(mode="json")) + "\n",
        )
        journal.append(
            "reference_submission", {"task": name, "manifest": manifest.model_dump(mode="json")}
        )
        result = EvaluationEngine(manager, DockerSandbox(image), store).evaluate(
            task, artifact.path, manifest, submitted_patch_artifact=artifact
        )
        journal.append(
            "reference_evaluated",
            {
                "task": name,
                "artifact": store.put_json(result.model_dump(mode="json")).model_dump(mode="json"),
            },
        )
        print(
            name,
            result.evaluation_status,
            result.scope_compliant_success,
            result.verdicts.model_dump(mode="json"),
            flush=True,
        )
    journal.append("completed", {"model_execution": "NOT_RUN", "official": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
