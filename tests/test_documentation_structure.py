from __future__ import annotations

import hashlib
import json
from pathlib import Path

ACTIVE_DOCS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/00-index.md"),
    Path("docs/current-status.md"),
    Path("docs/01-project-spec.md"),
    Path("docs/02-architecture.md"),
    Path("docs/03-contracts.md"),
    Path("docs/04-evaluation-protocol.md"),
    Path("docs/05-implementation-plan.md"),
    Path("docs/06-decisions.md"),
    Path("docs/07-reproduction.md"),
    Path("docs/08-limitations.md"),
    Path("docs/09-evidence.md"),
)
SNAPSHOT_ROOT = Path("docs/archive/snapshots/d121")
SNAPSHOT_MANIFEST = SNAPSHOT_ROOT / "snapshot-manifest.json"
RAPID_HISTORY = Path("docs/archive/rapid-workflow-history-20260830.md")
D121_CANDIDATE_ID = (
    "d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_d121_documentation_snapshot_is_exact_and_historical() -> None:
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "documentation-snapshot-manifest-v1"
    assert manifest["source_worktree_dirty"] is True
    assert manifest["current_authority"] is False
    assert len(manifest["files"]) == 10
    for row in manifest["files"]:
        path = SNAPSHOT_ROOT / row["snapshot_path"]
        assert path.is_file()
        assert path.stat().st_size == row["file_bytes"]
        assert _sha256(path) == row["file_sha256"]


def test_active_documentation_is_small_and_current_focused() -> None:
    for path in ACTIVE_DOCS:
        assert path.is_file()
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200

    active_bytes = sum(path.stat().st_size for path in ACTIVE_DOCS)
    snapshot_bytes = sum(path.stat().st_size for path in SNAPSHOT_ROOT.glob("*.full.md"))
    assert active_bytes <= 90_000
    assert active_bytes * 10 < snapshot_bytes


def test_historical_d121_candidate_is_not_current_authority() -> None:
    owners = [path for path in ACTIVE_DOCS if D121_CANDIDATE_ID in path.read_text(encoding="utf-8")]
    assert owners == []


def test_agent_required_reading_does_not_require_archive() -> None:
    guide = Path("AGENTS.md").read_text(encoding="utf-8")
    required = guide.split("## Required reading", 1)[1].split("## Non-negotiable invariants", 1)[0]

    assert "docs/00-index.md" in required
    assert "docs/current-status.md" in required
    assert "docs/archive/" not in required


def test_current_docs_bind_consumed_r21_and_reviewed_v26_without_authority() -> None:
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    architecture = Path("docs/02-architecture.md").read_text(encoding="utf-8")
    contracts = Path("docs/03-contracts.md").read_text(encoding="utf-8")
    protocol = Path("docs/04-evaluation-protocol.md").read_text(encoding="utf-8")
    roadmap = Path("docs/05-implementation-plan.md").read_text(encoding="utf-8")
    evidence = Path("docs/09-evidence.md").read_text(encoding="utf-8")

    assert "Work Item 70 consumed R20 exactly once" in status
    assert "Work Item 71 is complete offline" in status
    assert "R21 and all earlier approvals are consumed" in architecture
    assert "No current candidate authorizes Docker" in architecture
    assert "lean-harness-v25" in contracts
    assert "phase-evidence-v35" in contracts
    assert "WORK_PLAN_ADMISSION_REPEATED" in contracts
    assert "lean-harness-v26" in contracts
    assert "phase-evidence-v36" in contracts
    assert "MODEL_GENERATION_INCOMPLETE_REPEATED" in contracts
    assert "R23 is now the latest consumed live batch" in protocol
    assert "Work Item 71 created Lean V25 offline" in protocol
    assert "## Completed work — Work Item 72" in roadmap
    assert "## Completed work — Work Item 73" in roadmap
    assert "## Completed work — Work Item 74" in roadmap
    assert "## Next work" in roadmap
    assert "Work Item 75" in roadmap
    assert "Lean V25 offline plan-compatibility evidence" in evidence
    assert "R21 consumed candidate-v29 evidence" in evidence
    assert "590bbd602a34d208256d98b78ea4690f7a4d3a8f8593bd59e30b6173c9a089f4" in evidence
    assert "b22700a13fe823a270c439c9972e21d21eb8d1d53ae6a0431452fc77f8cbc4a9" in evidence
    assert "2c2ca0ae927d42cee7cae6ce3461d55d33d767cdaac54fcb84a5031ada5feae4" in evidence
    assert "54ae5e99226ec8a2d6635e6ece104c87b3ae1ba0e6aca675e20c7d7d339a749a" in evidence
    assert "14663e2ed74a684c3c9d017a8e3c6812b3187b09938cea703a0735b920f4a884" in evidence
    assert "V25 is not promoted" in evidence
    assert "Lean V26 offline R21-reliability evidence" in evidence
    assert "6b0f753f26c7e7d2d303c9b82bc192396bc1fbd312c709534927b7b39a4d38df" in evidence
    assert "afaea6f091497e03219a47496c9f27f177a99061d9329af6a5793d188366d6b5" in evidence
    assert "e7da9667fff6c16e951eb541aeb59985e91af2bcf247b8473c59549b0d16480e" in evidence
    assert "a82f018bd3fdbe638d276844f3773d33c89278cfb254f207039f679aac3b6d8c" in evidence
    assert "eligible-not-adopted" in status
    assert "No paid, held-out or B/D execution is currently authorized" in status


def test_rapid_history_is_archived_and_non_authoritative() -> None:
    index = Path("docs/00-index.md").read_text(encoding="utf-8")
    history = RAPID_HISTORY.read_text(encoding="utf-8")

    assert RAPID_HISTORY.is_file()
    assert RAPID_HISTORY not in ACTIVE_DOCS
    assert "Historical snapshots" in index or "Historical snapshot" in index
    assert "historical audit only" in history
    assert "Rapid R1-R6 are consumed" in history
    assert "R20 settled 6/6" in history
    assert "Lean V25 is the versioned opt-in compatibility successor" in history
    assert "grants no candidate" in history


def test_r22_candidate_is_documented_as_prestart_stopped_not_agent_failure() -> None:
    candidate_path = Path(
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22-candidate-v30.json"
    )
    candidate = json.loads(candidate_path.read_bytes())
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    roadmap = Path("docs/05-implementation-plan.md").read_text(encoding="utf-8")
    evidence = Path("docs/09-evidence.md").read_text(encoding="utf-8")
    protocol = Path("docs/04-evaluation-protocol.md").read_text(encoding="utf-8")

    assert candidate["execution_hash"] in status
    assert candidate["execution_hash"] in evidence
    assert candidate["content_hash"] in evidence
    assert _sha256(candidate_path) in evidence
    assert "No R22 result or promotion exists" in status
    assert "## Completed work — Work Item 76" in roadmap
    assert "V25 control and V26 treatment, three rows each" in protocol
    assert "runner-continuity check stays excluded" in protocol
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    audit_path = candidate_path.with_name(candidate_path.stem + "-prestart-stop-v1.json")
    audit = json.loads(audit_path.read_bytes())
    assert audit["content_hash"] in evidence
    assert _sha256(audit_path) in evidence
    assert audit["execution_observation"]["not_started_rows"] == 6
    assert audit["execution_observation"]["started_rows"] == 0
    assert audit["execution_observation"]["observed_image_identity_check_count"] is None
    assert "Work Item 77" in status
    assert "retry authority is closed" in status


def test_current_roadmap_keeps_confirmatory_and_external_gates_closed() -> None:
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    decisions = Path("docs/06-decisions.md").read_text(encoding="utf-8")
    protocol = Path("docs/04-evaluation-protocol.md").read_text(encoding="utf-8")
    reproduction = Path("docs/07-reproduction.md").read_text(encoding="utf-8")

    assert "source-qualified only, unactivated" in status
    assert "planning disposition is now **deferred**" in status
    assert "R11-R21 approvals are consumed" in status
    assert "R21 candidate-v29 is consumed" in reproduction
    assert "survivor-only fresh confirmation" in decisions
    assert "B/D on a separately frozen fresh panel" in decisions
    assert "Confirmatory successor contract" in protocol
    assert "selected evaluator-reached subsets" in protocol.lower()
    assert "rehearsal or execute mode" in reproduction
    assert "artifact builders report zero provider" in reproduction
    assert "Docker, evaluator, visible-check" in reproduction


def test_documented_evaluator_v1_gap_matches_current_source() -> None:
    evaluator = Path("patchloop/verifier/core.py").read_text(encoding="utf-8")
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    limitations = Path("docs/08-limitations.md").read_text(encoding="utf-8")

    assert "safety_state = VerdictState.PASS" in evaluator
    assert "## Evaluator correctness gap" in status
    assert "## Evaluator-v1 correctness gap" in limitations


def test_r23_consumed_halt_preserves_preparation_without_reopening_authority() -> None:
    prefix = (
        "reports/rapid-development/artifacts/rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23"
    )
    candidate_path = Path(prefix + "-candidate-v32.json")
    rehearsal_path = Path(prefix + "-candidate-v32-rehearsal-v29.json")
    qualification_path = Path(
        "experiments/rapid-candidate-v32-v25-v26-batch-image-ab-public-qualification-20260831-v1.json"
    )
    candidate = json.loads(candidate_path.read_bytes())
    qualification = json.loads(qualification_path.read_bytes())
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    evidence = Path("docs/09-evidence.md").read_text(encoding="utf-8")
    reproduction = Path("docs/07-reproduction.md").read_text(encoding="utf-8")
    assert candidate["execution_hash"] in status and candidate["execution_hash"] in evidence
    for path in (candidate_path, rehearsal_path, qualification_path):
        assert _sha256(path) in evidence
    assert "No paid, held-out or B/D execution is currently authorized" in status
    assert "R23 cannot retry or resume" in status
    assert "R23 candidate-v32 is consumed and halted" in reproduction
    assert "tests/test_rapid_r23_halted_audit.py" in reproduction
    audit_path = Path(prefix + "-candidate-v32-halted-public-audit-v1.json")
    audit = json.loads(audit_path.read_bytes())
    assert _sha256(audit_path) in evidence and audit["content_hash"] in evidence
    assert audit["execution_observation"]["settled_rows"] == 2
    assert audit["execution_observation"]["not_started_rows"] == 4
    assert audit["execution_observation"]["model_cost_nanos"] == 162_854_250
    assert audit["failure_diagnosis"]["failed_provider_requests_lower_bound"] == 1
    assert candidate["image_admission_contract"]["image_inspect_attempts_max"] == 1
    assert candidate["image_admission_contract"]["per_row_image_inspect_calls"] == 0
    assert qualification["production_shaped_image_start_mock"]["real_agent_start_count"] == 6
    assert qualification["real_docker_identity_observed"] is False
    assert qualification["real_agent_performance_measured"] is False
    assert candidate["selection_evidence"]["zero_call_predecessor"]["retry_allowed"] is False
    assert candidate["execution_authorized"] is False
