"""Operator-only, provider-free review pilot identities and public scoring.

Nothing from this module is projected into reviewer or repair inputs.
"""
from __future__ import annotations

from dataclasses import asdict

from diagnostics.decision_sampler import require
from diagnostics.review_context_offline import load
from patchloop.dev.cost import pricing_for_model
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json

TASKS = ("original-opensandbox-816", "original-isort-2491",
         "original-pyinfra-1679", "original-conan-19735")
ORDER = ("CAB", "ABC", "BCA", "CBA")
# Bind transitive diagnostic helpers as well as the direct entry point.
IMPLEMENTATION = tuple(sorted(p.relative_to(repository_root()).as_posix()
                             for p in (repository_root() / "diagnostics").glob("*.py"))) + (
    ".agent/review-context-pilot.md",)


def score_opensandbox(observations):
    expected = {name: "REJECT" for name in (
        "helper_symlink", "backend_symlink_no_subpath", "sequence_symlink_no_subpath",
        "sequence_symlink_subpath_allowlist", "sequence_symlink_subpath_no_allowlist",
        "backend_after_interstage_swap")}
    expected.update(helper_clean="ACCEPT", backend_clean_no_subpath="ACCEPT")
    require(isinstance(observations, list) and len(observations) == len(expected),
            "incomplete OpenSandbox matrix")
    require({r["case"] for r in observations} == set(expected), "unexpected diagnostic cases")
    require(all(r["outcome"] in {"ACCEPT", "REJECT"} for r in observations),
            "unclassified diagnostic outcome")
    return {r["case"]: r["outcome"] == expected[r["case"]] for r in observations}


def score_isort(observations):
    cases = observations["cases"]
    expected = {(profile, comment, placement) for profile in ("default", "black")
                for comment in ("type: ignore[attr-defined]", "explanation")
                for placement in ("opening", "member")}
    require(len(cases) == 8 and {
        (r["profile"], r["comment"], r["placement"]) for r in cases} == expected,
        "incomplete isort matrix")
    scores = {}
    for row in cases:
        lines = row["output"].splitlines()
        comment_lines = [i for i, line in enumerate(lines) if "# " + row["comment"] in line]
        require(comment_lines == row["comment_lines"], "comment observation changed")
        require(type(row["idempotent"]) is bool, "missing idempotence result")
        owned = (comment_lines == [0] if row["placement"] == "opening" else
                 len(comment_lines) == 1 and comment_lines[0] > 0
                 and "renamed_random_attribute" in lines[comment_lines[0]])
        scores["/".join((row["profile"], row["comment"], row["placement"]))] = (
            owned and row["idempotent"])
    return scores


def build(cases, programs, *, env_file, result_root):
    """Freeze identities without reading credentials or starting any execution."""
    require(tuple(cases) == TASKS, "exact ordered four-case panel required")
    require(set(programs) == set(TASKS[:2]), "both public diagnostic programs required")
    rows = []
    for task, order in zip(TASKS, ORDER, strict=True):
        case = cases[task]
        loaded = load(case["source"], case["sequence"], conan_materialization=True)
        require(loaded.package.public.task_id == task, "task mismatch")
        require(loaded.envelope.model == "gpt-5.4-2026-03-05"
                and loaded.envelope.reasoning_effort == "xhigh"
                and loaded.envelope.max_output_tokens == 25000, "model mismatch")
        evaluation = load_task_package(case["evaluation_path"])
        public = loaded.package.public.model_dump(mode="json")
        evaluation_public = evaluation.public.model_dump(mode="json")
        require(evaluation_public == {**public, "task_version": 2 if task == TASKS[2] else 1},
                "evaluation public contract differs")
        require(bool(evaluation.private.hidden_checks), "hidden evaluation required")
        require(sha256_bytes(str(env_file.resolve()).encode()) ==
                loaded.envelope.credential_file_path_hash, "credential path differs")
        binding = {
            "task": task, "source": case["source"].record(), "sequence": case["sequence"],
            "candidate_hash": loaded.diff["patch_hash"],
            "source_runtime_hash": loaded.envelope.runtime_hash,
            "prepared_request_hash": sha256_json(loaded.bundle["request"]),
            "evaluation_path": str(case["evaluation_path"].resolve()),
            "evaluation_content_hash": evaluation.task_content_hash,
            "source_package_hash": loaded.package.task_content_hash,
            "required_checks": [c.model_dump(mode="json")
                                for c in loaded.package.public.visible_checks],
        }
        for arm in order:
            rows.append({**binding, "arm": arm, "new_cap_nanos": 2_000_000_000})
    return {
        "schema": "review-pilot-execution-v1", "official": False,
        "paid_execution_authorized": False, "collector_ready": True,
        "runtime_hash": runtime_content_hash(),
        "implementation": {p: sha256_bytes((repository_root() / p).read_bytes())
                           for p in IMPLEMENTATION},
        "model": "gpt-5.4-2026-03-05", "reasoning_effort": "xhigh",
        "max_output_tokens": 25000, "env_file": str(env_file.resolve()),
        "result_root": str(result_root.resolve()), "repeat_per_arm": 1,
        "new_cap_nanos": 24_000_000_000, "rows": rows,
        "pricing": {k: str(v) for k, v in asdict(
            pricing_for_model("gpt-5.4-2026-03-05")).items()},
        "operator_scoring_seconds": 300,
        "limits": {"seconds": 900, "calls": 16, "actions": 48, "accepted_edits": 2,
                   "review_seconds": 180, "review_calls": 4, "review_actions": 12},
        "operator_only_programs": {k: {"path": str(p.resolve()),
                                      "hash": sha256_bytes(p.read_bytes())}
                                   for k, p in programs.items()},
        "scoring": "review_pilot_manifest.score_opensandbox/score_isort plus isolated evaluation",
        "pyinfra_original_v1_verdict": "preserve separately from v2",
        "no_submission_acceptance": "NOT_RUN", "automatic_retry": False,
        "automatic_resume": False, "sdk_retries": 0,
    }
