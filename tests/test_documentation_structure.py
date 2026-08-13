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
    assert active_bytes <= 75_000
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


def test_current_docs_bind_the_consumed_four_run_result_without_new_live_authority() -> None:
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    protocol = Path("docs/04-evaluation-protocol.md").read_text(encoding="utf-8")
    plan = Path("experiments/ac-structured-pilot.plan.yaml").read_text(encoding="utf-8")

    assert "four-run A/C readiness" in status
    assert "Moto #7208" in protocol
    assert "Babel #1042" in protocol
    assert "candidate `sha256:60c67908...cff9e`" in status
    assert "All four Moto A/C + Babel C/A rows resolved" in status
    assert "No paid, held-out or B/D execution is currently authorized" in status
    assert "expected_runs: 4" in plan
    assert "provider_execution_authorized: false" in plan
    assert "runtime_memory_injection_authorized: false" in plan


def test_current_roadmap_defers_d142_and_uses_the_fast_track() -> None:
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    decisions = Path("docs/06-decisions.md").read_text(encoding="utf-8")

    assert "source-qualified only, unactivated" in status
    assert "planning disposition is now **deferred**" in status
    assert "D-142 and the V25 one-use" in status
    assert "R8 is the first complete receipt-qualified four-row" in status
    assert "Reusable no-call preflight" in status
    assert "per-attempt approval prose" in status

    ordered_stages = (
        "evaluator correctness v2",
        "successor A/C qualification",
        "local preflight",
        "exact campaign approval",
        "four-run development A/C readiness",
        "preregister held-out A/C",
        "B/D",
    )
    positions = [decisions.index(stage) for stage in ordered_stages]
    assert positions == sorted(positions)


def test_documented_evaluator_v1_gap_matches_current_source() -> None:
    evaluator = Path("patchloop/verifier/core.py").read_text(encoding="utf-8")
    status = Path("docs/current-status.md").read_text(encoding="utf-8")
    limitations = Path("docs/08-limitations.md").read_text(encoding="utf-8")

    assert "safety_state = VerdictState.PASS" in evaluator
    assert "## Evaluator correctness gap" in status
    assert "## Evaluator-v1 correctness gap" in limitations
