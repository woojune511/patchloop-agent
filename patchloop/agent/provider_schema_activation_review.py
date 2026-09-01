"""Offline review of the frozen V27 package; never enables a live run.

Source call-site observations are not a control-flow proof. Behavioral evidence
comes from the separately executed, source-bound fake-provider runner tests.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from patchloop.agent.provider_schema_qualification import (
    QUALIFICATION_PATH,
    build_qualification,
    qualification_bytes,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

REVIEW_PATH = Path("experiments/lean-harness-provider-schema-activation-review-20260901-v2.json")
SUPERSEDED_REVIEW_PATH = Path(
    "experiments/lean-harness-provider-schema-activation-review-20260901-v1.json"
)
SUPERSEDED_REVIEW_HASH = "sha256:aa938a4291436b91a1dde78bb21bf448aefd2c4ec1f86a0abb1c511474d22ffd"
QUALIFICATION_FILE_HASH = "sha256:cb80ed051f37fa50a601462510fdc866b3bf40d18c0df6fb027bdb75e286bcc2"
QUALIFICATION_CONTENT_HASH = (
    "sha256:acc5a10184db11e9611b91d68d28b94907dd89d7c0a11e363b137abaab77e276"
)
SOURCE_FILES = (
    "patchloop/agent/provider_schema_activation_review.py",
    "scripts/build_lean_harness_provider_schema_activation_review.py",
    "tests/test_provider_schema_activation_review.py",
    "patchloop/evals/live_verifier_registry.py",
)
RUNTIME_IDENTITY = {
    "runtime_policy_version": "lean-harness-v27",
    "tool_schema_version": "v28",
    "context_policy_version": "phase-evidence-v37",
    "request_evidence_schema": "lean-harness-request-evidence-v27",
}


def _identity(root: Path, relative: str) -> dict[str, Any]:
    lexical = root / relative
    resolved = ensure_within(root, relative)
    if lexical.is_symlink() or not resolved.is_file():
        raise ContractError(f"V27 review input is unavailable: {relative}")
    raw = resolved.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _qualification(root: Path) -> dict[str, Any]:
    raw = ensure_within(root, QUALIFICATION_PATH.as_posix()).read_bytes()
    if sha256_bytes(raw) != QUALIFICATION_FILE_HASH:
        raise ContractError("frozen V27 qualification bytes differ")
    value = build_qualification(root)
    if raw != qualification_bytes(value) or value["content_hash"] != QUALIFICATION_CONTENT_HASH:
        raise ContractError("frozen V27 qualification source binding differs")
    return value


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    found = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise ContractError(f"V27 review source function is ambiguous: {name}")
    return found[0]


def _calls(node: ast.AST) -> list[dict[str, Any]]:
    return sorted(
        (
            {"call": ast.unparse(n.func), "line": n.lineno}
            for n in ast.walk(node)
            if isinstance(n, ast.Call)
        ),
        key=lambda row: (row["line"], row["call"]),
    )


def source_observations(root: Path) -> dict[str, Any]:
    specifications = (
        (
            "adapter_count",
            "patchloop/agent/provider_schema_adapter.py",
            "count_input_tokens_v3",
            ("self.admit_request_v3", "self.client.responses.input_tokens.count"),
        ),
        (
            "adapter_generate",
            "patchloop/agent/provider_schema_adapter.py",
            "execute_request",
            ("self.admit_request_v3", "super().execute_request"),
        ),
        (
            "assembler_count",
            "patchloop/agent/lean_runtime.py",
            "count_request_body",
            ("validate_provider_tool_schemas", "provider_input_token_counter"),
        ),
        (
            "runner_count",
            "patchloop/agent/runner.py",
            "lean_provider_input_token_counter",
            (
                "adapter.admit_request_v3",
                "_provider_input_count_boundary",
                "counted_request_with_receipts",
            ),
        ),
        (
            "durable_count",
            "patchloop/agent/provider_count_accounting.py",
            "counted_request_with_receipts",
            (
                "validate_provider_tool_schemas",
                "assert_input_token_count_recoverable",
                "state.append_event",
                "count",
                "state.append_event",
            ),
        ),
    )
    trees: dict[str, ast.AST] = {}

    def tree(path: str) -> ast.AST:
        if path not in trees:
            trees[path] = ast.parse(ensure_within(root, path).read_text(encoding="utf-8"))
        return trees[path]

    gates = {}
    for label, path, function_name, expected_calls in specifications:
        node = _function(tree(path), function_name)
        calls = _calls(node)
        cursor = 0
        selected = []
        for expected in expected_calls:
            match = next(
                (i for i in range(cursor, len(calls)) if calls[i]["call"] == expected), None
            )
            if match is None:
                raise ContractError(f"V27 reviewed call-site sequence differs: {label}")
            selected.append(calls[match])
            cursor = match + 1
        gates[label] = {"path": path, "function": function_name, "ordered_call_sites": selected}

    rehearsal = _function(tree("patchloop/agent/runner.py"), "rehearse_provider_dispatch")
    names = {row["call"] for row in _calls(rehearsal)}
    if (
        not {
            "_consume_row_execution_authorization",
            "validate_row_batch_image",
            "_provider_dispatch_boundary",
        }
        <= names
    ):
        raise ContractError("legacy rehearsal boundary differs")
    constructs_request = bool(
        names
        & {
            "assemble_lean_harness_request",
            "validate_provider_tool_schemas",
            "_provider_input_count_boundary",
            "counted_request_with_receipts",
        }
    )
    contract_tree = tree("patchloop/contracts.py")
    pairs = [
        n
        for n in ast.walk(contract_tree)
        if isinstance(n, ast.Tuple)
        and [v.value if isinstance(v, ast.Constant) else None for v in n.elts]
        == ["v28", "phase-evidence-v37"]
    ]
    parents = {
        child: node for node in ast.walk(contract_tree) for child in ast.iter_child_nodes(node)
    }
    mock_guarded = []
    for pair in pairs:
        current = pair
        while current in parents and not (
            isinstance(current, ast.BoolOp) and isinstance(current.op, ast.And)
        ):
            current = parents[current]
        mock_guarded.append(
            any(
                isinstance(n, ast.Compare) and ast.unparse(n) == "self.model.provider == 'mock'"
                for n in ast.walk(current)
            )
        )
    if len(pairs) != 1 or mock_guarded != [True]:
        raise ContractError("V27 mock-only runtime admission boundary differs")
    return {
        "kind": "static-call-site-observation-not-control-flow-proof",
        "gates": gates,
        "legacy_rehearsal": {
            "path": "patchloop/agent/runner.py",
            "function": rehearsal.name,
            "line": rehearsal.lineno,
            "checks_row_image_provider_capability": True,
            "covers_request_construction_and_count_gate": constructs_request,
            "executed_by_review_builder": False,
        },
        "live_integration": {
            "admitted_runtime_pair_occurrences": len(pairs),
            "all_occurrences_require_mock_provider": all(mock_guarded),
            "live_manifest_admitted": False,
        },
    }


def activation_criteria(
    qualification: dict[str, Any], observations: dict[str, Any]
) -> dict[str, bool]:
    boundary = qualification.get("evidence_boundary", {})
    counts = qualification.get("synthetic_count_scenarios", {})
    schemas = qualification.get("schema_scenarios", {})
    count_expectations = {
        "completed": (1, 1, 0, 0),
        "failed": (1, 0, 1, 0),
        "outcome_unknown": (1, 0, 0, 1),
        "schema_blocked": (0, 0, 0, 0),
    }
    return {
        "exact_qualified_runtime": qualification.get("runtime_identity") == RUNTIME_IDENTITY,
        "strict_static_and_projected_plan_schemas": all(
            schemas.get(key, {}).get("provider_acceptance_observed") is False
            and schemas.get(key, {}).get("policy_version") == "responses-strict-tool-admission-v1"
            for key in ("static_surface", "production_projected_synthetic_initial_plan")
        ),
        "ambiguous_reads_rejected": schemas.get("ambiguous_or_missing_modes_rejected") == 3,
        "count_outcomes_not_conflated": all(
            tuple(
                counts.get(name, {}).get("summary", {}).get(k)
                for k in ("logical_attempts", "completed", "failed", "outcome_unknown")
            )
            == expected
            for name, expected in count_expectations.items()
        ),
        "failed_and_uncertain_count_retry_closed": all(
            counts.get(name, {}).get("automatic_retry_blocked") is True
            for name in ("failed", "outcome_unknown")
        ),
        "five_source_gate_sequences_reviewed": set(observations.get("gates", {}))
        == {
            "adapter_count",
            "adapter_generate",
            "assembler_count",
            "runner_count",
            "durable_count",
        },
        "remaining_rehearsal_gap_explicit": observations.get("legacy_rehearsal", {}).get(
            "covers_request_construction_and_count_gate"
        )
        is False,
        "live_admission_stays_closed": observations.get("live_integration", {}).get(
            "all_occurrences_require_mock_provider"
        )
        is True,
        "qualification_zero_call_noncreating": (
            qualification.get("status") == "offline-qualified"
            and qualification.get("candidate_created") is False
            and qualification.get("rehearsal_created") is False
            and qualification.get("external_calls") == 0
            and all(
                boundary.get(k) == 0
                for k in (
                    "provider_calls",
                    "docker_calls",
                    "evaluator_calls",
                    "visible_check_calls",
                    "network_calls",
                )
            )
            and boundary.get("added_cost_usd") == "0"
            and all(
                boundary.get(k) is False
                for k in (
                    "raw_reasoning_read",
                    "private_task_spec_read",
                    "hidden_evaluator_content_read",
                    "reference_patch_read",
                )
            )
        ),
    }


def build_activation_review(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification = _qualification(root)
    observations = source_observations(root)
    criteria = activation_criteria(qualification, observations)
    eligible = all(criteria.values())
    prior = _identity(root, SUPERSEDED_REVIEW_PATH.as_posix())
    if prior["file_sha256"] != SUPERSEDED_REVIEW_HASH:
        raise ContractError("superseded V27 review bytes differ")
    prior_content = json.loads((root / SUPERSEDED_REVIEW_PATH).read_bytes())
    body = {
        "schema_version": "lean-provider-schema-activation-review-v1",
        "generated_at": "2026-09-01T00:00:00+00:00",
        "status": "activation-reviewed-candidate-decision-ready"
        if eligible
        else "activation-review-blocked",
        "scope": "frozen-v27-offline-package-not-live-activation",
        "runtime_identity": qualification["runtime_identity"],
        "qualification": {
            **_identity(root, QUALIFICATION_PATH.as_posix()),
            "content_hash": qualification["content_hash"],
        },
        "qualified_source_files": qualification["source_files"],
        "review_source_files": [_identity(root, path) for path in SOURCE_FILES],
        "predecessor_preservation": qualification["predecessor_preservation"],
        "superseded_review": {
            **prior,
            "content_hash": prior_content["content_hash"],
            "disposition": "zero-call-superseded",
            "reason": "Review-only formatting and check-only verification finalized after v1; "
            "qualified runtime unchanged and v1 retained without adoption.",
        },
        "source_observations": observations,
        "activation_criteria": criteria,
        "decision": {
            "adoption_status": "eligible-not-adopted" if eligible else "blocked",
            "eligible_for_separate_candidate_integration_decision": eligible,
            "candidate_design_authorized_by_review": False,
            "live_execution_ready": False,
            "provider_acceptance_observed": False,
        },
        "required_before_candidate_freeze": [
            "Separate adoption decision and versioned V27 live manifest/registry integration.",
            "Construct the actual public task/model request without calls; enter its pre-count "
            "schema and authority gate.",
            "Cover final dynamic surfaces, including plan/revision, with guarded tests.",
            "Retain one batch image inspection, none per row, with equal limits for both arms.",
            "Freeze runtime/config/task/image/schedule/cost hashes; rehearse twice identically.",
        ],
        "future_comparison_constraints": {
            "recommended_control_runtime": "lean-harness-v25",
            "recommended_treatment_runtime": "lean-harness-v27",
            "comparison_is_one_versioned_package_not_single_policy_effect": True,
            "same_task_image_model_memory_total_budget_evaluator_required": True,
            "task_version_change_allowed": False,
            "runner_continuity_check_allowed": False,
            "historical_retry_or_resume_allowed": False,
            "input_count_attempts_not_directly_comparable_to_legacy_success_only_counts": True,
            "fresh_exact_schedule_reserve_cap_approval_required": True,
            "schedule_and_cost_not_selected_by_review": True,
            "official": False,
        },
        "validation_limits": [
            "Rebuilt qualification and static call sites prove neither live provider acceptance "
            "nor full control flow.",
            "Fake-provider runner/correction/review/recovery tests run separately.",
            "Runner tests use public-calibration mock manifests; synthetic row-receipt tests "
            "issue no live authority.",
            "Legacy rehearsal is capability-only. V27 live admission and exact-request rehearsal "
            "remain unimplemented.",
            "Synthetic schema scenarios are bounded, not exhaustive task-derived catalog coverage.",
            "Count receipts are logical attempts, not HTTP totals, billing or idempotency proof.",
            "No hidden cause, quality, efficiency or generalization improvement is established.",
        ],
        "official_documentation": [
            {
                "url": "https://developers.openai.com/api/docs/guides/function-calling#strict-mode",
                "reviewed_on": "2026-09-01",
                "rule": "All object properties are required; optional values use nullable types.",
                "fetched_by_builder": False,
            }
        ],
        "evidence_boundary": dict(qualification["evidence_boundary"]),
        "runtime_source_modified": False,
        "candidate_created": False,
        "rehearsal_created": False,
        "external_calls": 0,
        "paid_execution_authorized": False,
        "next_gate": "separate-v27-candidate-integration-adoption-decision",
    }
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    if value.get("content_hash") != sha256_json(
        {k: v for k, v in value.items() if k != "content_hash"}
    ):
        raise ContractError("V27 activation-review content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_activation_review(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    first = build_activation_review(root)
    raw = review_bytes(first)
    if raw != review_bytes(build_activation_review(root)):
        raise ContractError("V27 activation reviews are not byte-identical")
    path = ensure_within(root, REVIEW_PATH.as_posix())
    if path.exists():
        if path.read_bytes() != raw:
            raise ContractError("existing V27 review differs; never overwrite evidence")
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return first
