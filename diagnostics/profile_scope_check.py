"""Offline public diagnostic on a clean base and one already supplied patch.

Two fresh workspaces, two fixed checks, no model generation or private evaluation.
The task's existing dependency image is used for this operator-owned program only;
the coding agent's stdlib probe capability and registered checks stay unchanged.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from diagnostics import profile_scope_program as program
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck, TaskEnvironment
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.prepared_source import admission_hash, load_source
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.runner import DockerSandbox, SandboxResult
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_json

TASK = repository_root() / "tasks/dev-train/pydantic-ai-synthetic-tool-reasoning"
PROGRAM = Path(program.__file__)


def registered_check() -> RegisteredCheck:
    public = load_public_task(TASK / "public.yaml")
    template = next(check for check in public.visible_checks
                    if check.id == "synthetic-tool-history-contract")
    return template.model_copy(update={
        "id": "profile-scope-contrast",
        "command": [template.command[0], "-c", PROGRAM.read_text(encoding="utf-8")],
    })


def observations(result: SandboxResult) -> list[dict]:
    """A complete fixed matrix is required; infrastructure loss is never a case FAIL."""
    if (result.timed_out or result.deadline_exhausted or result.cleanup_failed
            or result.truncated or result.exit_code not in {0, 1}):
        raise ContractError("public contrast execution is incomplete or uncertain")
    try:
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        expected_ids = [f"{origin}:{field}" for field in program.FIELDS
                        for origin in program.ORIGINS]
        rows, summary = lines[:-1], lines[-1]
        valid = [row["case"] for row in rows] == expected_ids
        for row in rows:
            expected = program.expected_message(row["field"], row["profile_origin"])
            valid = valid and (
                row["case"] == f"{row['profile_origin']}:{row['field']}"
                and row["mode"] == "field" and row["provider"] == "openai"
                and row["model"] == program.MODEL_NAME
                and row["message_kind"] == "tool_only_without_thinking"
                and row["expected"] == expected
                and row["passed"] is (row["actual"] == expected)
            )
        passed = sum(row["passed"] for row in rows)
        valid = valid and summary["summary"] == {"passed": passed, "failed": 4 - passed}
        valid = valid and result.exit_code == int(passed != 4)
        modules = summary["project_modules"]
        valid = valid and set(modules) == {
            "pydantic_ai", "pydantic_ai.models.openai", "pydantic_ai.profiles.openai",
            "pydantic_ai.providers.deepseek",
        }
        valid = valid and all(path.startswith("/workspace/pydantic_ai_slim/")
                              and ".." not in path.split("/") for path in modules.values())
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ContractError("public contrast output is missing or malformed") from exc
    if not valid:
        raise ContractError("public contrast output does not match the frozen matrix")
    return rows


def run(*, prepared_source: Path, candidate_patch: Path, output: Path) -> dict:
    output = output.resolve()
    if output.is_relative_to(repository_root().resolve()):
        raise ContractError("diagnostic evidence must be outside the repository")
    # Atomic fresh-directory admission: no overwrite, automatic resume or repeat.
    output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(output)
    journal = DevJournal(output, "run_dev_profilescope")

    def save(name, value):
        store.write_text_immutable(output / name, canonical_json(value) + "\n")
        journal.append("diagnostic_artifact_recorded", {
            "path": name, "content_hash": sha256_bytes((output / name).read_bytes()),
        })

    try:
        public = load_public_task(TASK / "public.yaml")
        environment = TaskEnvironment.model_validate(
            load_unique_yaml((TASK / "environment.yaml").read_text(encoding="utf-8")))
        source_hash = admission_hash(prepared_source)
        source, _ = load_source(prepared_source, public.repository.url,
                                public.repository.base_commit, expected_hash=source_hash)
        patch_bytes = candidate_patch.read_bytes()
        changed = WorkspaceManager.patch_changed_files(patch_bytes)
        if (not changed or not set(changed) <= set(public.constraints.allowed_paths)
                or len(changed) > public.constraints.max_changed_files):
            raise ContractError("candidate patch exceeds this public task's source paths")
        patch_copy = output / "candidate.diff"
        store.write_text_immutable(patch_copy, patch_bytes.decode("utf-8"))
        check = registered_check()
        initial = {
            "official": False, "kind": "operator_public_profile_contrast",
            "provider_calls": 0, "input_count_calls": 0, "model_cost_usd": "0",
            "private_evaluation": "NOT_RUN", "task_acceptance": "NOT_ASSESSED",
            "runtime_hash": runtime_content_hash(), "task": public.model_dump(mode="json"),
            "task_public_hash": sha256_bytes((TASK / "public.yaml").read_bytes()),
            "environment": environment.model_dump(mode="json"),
            "operator_hash": sha256_bytes(Path(__file__).read_bytes()),
            "program_hash": sha256_bytes(PROGRAM.read_bytes()),
            "prepared_source_hash": source_hash, "source": source.model_dump(mode="json"),
            "patch_hash": sha256_bytes(patch_bytes), "check": check.model_dump(mode="json"),
            "order": ["base", "candidate"], "no_retry_resume_or_generation": True,
        }
        save("manifest.json", initial)
        sandbox = DockerSandbox(environment.evaluator_image)
        if sandbox.image_identity() != environment.image_digest:
            raise ContractError("the exact existing project image is unavailable")
        save("preflight.json", {"image_digest": environment.image_digest, "official": False})
        manager = WorkspaceManager(
            repository_root() / "fixtures/repos", output / "workspaces",
            prepared_source=prepared_source, prepared_source_hash=source_hash,
        )
        rows = {}
        for label in initial["order"]:
            workspace = manager.create(label, public.repository.url, public.repository.base_commit)
            if label == "candidate":
                manager.apply_patch(workspace, patch_copy)
            diff = manager.diff_summary(workspace)
            if diff.diff_lines > public.constraints.max_diff_lines or diff.untracked_files:
                raise ContractError("diagnostic workspace exceeds the public diff bounds")
            identity = {"run_id": journal.run_id, "action_id": label,
                        "manifest_hash": sha256_json(initial), "output": str(output)}
            journal.append("public_contrast_started", {
                "action_id": label, "input_hash": sha256_json(check.model_dump(mode="json")),
                "workspace": str(workspace), "diff_hash": diff.patch_hash,
                "execution_identity": identity,
            })
            result = sandbox.run_check(workspace, check,
                                       deadline=ExecutionDeadline.from_remaining(50),
                                       execution_identity=identity)
            save(f"{label}-execution.json", asdict(result))
            rows[label] = observations(result)
            if manager.diff_summary(workspace) != diff:
                raise ContractError("diagnostic execution changed its read-only workspace")
            save(f"{label}-observations.json", {"rows": rows[label], "diff_hash": diff.patch_hash})
        load_source(prepared_source, public.repository.url, public.repository.base_commit,
                    expected_hash=source_hash)
        if (runtime_content_hash() != initial["runtime_hash"]
                or sha256_bytes(PROGRAM.read_bytes()) != initial["program_hash"]
                or sha256_bytes(Path(__file__).read_bytes()) != initial["operator_hash"]
                or sha256_bytes((TASK / "public.yaml").read_bytes())
                != initial["task_public_hash"]):
            raise ContractError("diagnostic input bytes changed during execution")
        summary = {"status": "COMPLETE", "official": False, "rows": rows,
                   "checks_executed": 2, "provider_calls": 0, "model_cost_usd": "0",
                   "task_acceptance": "NOT_ASSESSED", "private_evaluation": "NOT_RUN",
                   "interpretation": "Only these public inputs are assessed. This is not an "
                   "agent rerun, hidden-failure diagnosis, acceptance result or probe expansion."}
        save("result.json", summary)
        journal.append("public_contrast_closed", {"status": "COMPLETE", "official": False})
        return summary
    except Exception as exc:
        journal.append("public_contrast_stopped", {
            "status": "STOPPED", "error_type": type(exc).__name__, "error": str(exc),
            "official": False, "retry": False,
        })
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-source", type=Path, required=True)
    parser.add_argument("--candidate-patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(**vars(args))
    print(canonical_json({"status": result["status"], "official": False,
                          "cases": {label: {row["case"]: row["passed"] for row in rows}
                                    for label, rows in result["rows"].items()}}))


if __name__ == "__main__":
    main()
