"""Collector admission and phase ordering with fake metadata/environment/row callbacks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics import host_plan_collection as collection
from diagnostics import host_plan_execution as execution
from diagnostics.declaration_checkpoint import Source
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture
def setup(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path / "evidence")
    source = Source(
        tmp_path / "parent",
        "run_dev_fixture",
        "journal",
        "envelope",
        tmp_path / "public.yaml",
        "public",
    )
    assessment = store.put_json({"environment": {"image": "image@sha256:" + "a" * 64}})
    first = store.put_json({"input": []})
    proof = store.put_json({"provider_free": True})
    plan = {k: "frozen" for k in collection.FROZEN_KEYS}
    plan.update(
        {
            "model": "gpt-5.4-2026-03-05",
            "reasoning_effort": "xhigh",
            "service_tier": "default",
            "source": {"frozen_prefix": True},
            "credential_file": str(tmp_path / "must_not_read.env"),
            "terminal_public_assessment": assessment.model_dump(mode="json"),
        }
    )
    manifest = {
        **{k: plan[k] for k in collection.FROZEN_KEYS},
        "schema": "host-plan-execution-v1",
        "design_hash": checkpoint.DESIGN_HASH,
        "source": source.record(),
        "checkpoint": plan["source"],
        "runtime_hash": "runtime",
        "implementation_hash": "implementation",
        "harness_git_commit": "commit",
        "live_output": str(tmp_path / "live"),
        "executing_probe_identity": {"image_digest": "image", "profile_hash": "profile"},
        "first_requests": {"O1-" + a: first.model_dump(mode="json") for a in "AB"},
        **{
            k: proof.model_dump(mode="json")
            for k in ("rehearsal_result", "validation", "shared_runtime_differences")
        },
    }
    path = tmp_path / "ready" / "manifest.json"
    path.parent.mkdir()
    path.write_text(canonical_json(manifest), encoding="utf-8")
    price = {
        "verified_on": datetime.now(UTC).date().isoformat(),
        "source": "https://developers.openai.com/api/docs/pricing",
        "model": plan["model"],
        "service_tier": "default",
        "usd_per_million": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
    }
    observed = {"metadata": 0, "keys": 0, "rows": []}
    monkeypatch.setattr(checkpoint, "load_design", lambda: (plan, source))
    monkeypatch.setattr(runner, "_runtime_hash", lambda: "runtime")
    monkeypatch.setattr(
        collection.observation_exposure, "implementation_hash", lambda: "implementation"
    )
    monkeypatch.setattr(collection, "git_commit", lambda: "commit")
    monkeypatch.setattr(collection.observation_comparison, "clean_implementation", lambda: None)
    monkeypatch.setattr(
        collection.observation_comparison, "check_environment", lambda *a: {"status": "READY"}
    )
    monkeypatch.setattr(
        collection.DockerSandbox, "image_identity", lambda *a, **k: "sha256:" + "a" * 64
    )

    def key(_):
        observed["keys"] += 1
        return "synthetic key, no file read"

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0 and 0 < kwargs["timeout"] <= 30
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def retrieve(self, model):
            observed["metadata"] += 1
            return SimpleNamespace(id=model)

    def restore(plan, source, output, arm, **kwargs):
        assert kwargs["provider_free"] is False
        assert kwargs["credential_file"] == Path(plan["credential_file"])
        observed["rows"].append((arm, kwargs["started"], kwargs["deadline"].expires_at))
        output.mkdir()
        return SimpleNamespace(
            root=output,
            row={"cell": "O1-" + arm},
            envelope=SimpleNamespace(probe_image_digest="image", probe_profile_hash="profile"),
        )

    monkeypatch.setattr(runner, "load_exact_openai_api_key", key)
    monkeypatch.setattr("openai.OpenAI", Client)
    monkeypatch.setattr(checkpoint, "restore_branch", restore)
    monkeypatch.setattr(
        execution,
        "run_row",
        lambda b, g, **k: {
            "row": b.row["cell"],
            "billing_known": True,
            "stop_remaining": False,
            "status": "synthetic settled ordinary failure",
        },
    )
    return SimpleNamespace(
        path=path,
        hash=sha256_bytes(path.read_bytes()),
        plan=plan,
        manifest=manifest,
        price=price,
        observed=observed,
    )


@pytest.mark.parametrize(
    "bad", ["hash", "cap", "price", "caps", "model", "implementation", "source"]
)
def test_admission_mismatch_stops_before_metadata_key_or_restoration(setup, bad):
    cap, digest = Decimal("11.00"), setup.hash
    if bad == "cap":
        cap = Decimal("11.01")
    elif bad == "hash":
        digest = "wrong"
    elif bad == "price":
        setup.price["usd_per_million"]["input"] = "2.51"
    else:
        setup.manifest["implementation_hash" if bad == "implementation" else bad] = "changed"
        setup.path.write_text(canonical_json(setup.manifest), encoding="utf-8")
        digest = sha256_bytes(setup.path.read_bytes())
    with pytest.raises(ContractError):
        collection.collect(setup.path, digest, cap, pricing_review=setup.price)
    assert setup.observed == {"metadata": 0, "keys": 0, "rows": []}
    assert not Path(setup.manifest["live_output"]).exists()


def test_single_metadata_and_fixed_pair_then_no_resume(setup):
    result = collection.collect(
        setup.path, setup.hash, Decimal("11.00"), pricing_review=setup.price
    )
    assert setup.observed["metadata"] == setup.observed["keys"] == 1
    assert [r[0] for r in setup.observed["rows"]] == ["A", "B"]
    assert setup.observed["rows"][0][1] <= setup.observed["rows"][1][1]
    assert setup.observed["rows"][0][2] == setup.observed["rows"][1][2]
    assert result["comparison"]["interpretation"] == "INCONCLUSIVE"
    with pytest.raises(ContractError):
        collection.collect(setup.path, setup.hash, Decimal("11.00"), pricing_review=setup.price)
    assert setup.observed["metadata"] == 1


def test_readiness_failure_never_loads_key_and_closes_both_rows(setup, monkeypatch):
    monkeypatch.setattr(
        collection.observation_comparison,
        "check_environment",
        lambda *a: {"status": "PREFLIGHT_FAILED"},
    )
    result = collection.collect(
        setup.path, setup.hash, Decimal("11.00"), pricing_review=setup.price
    )
    assert all(r["status"] == "NOT_RUN" for r in result["rows"])
    assert setup.observed == {"metadata": 0, "keys": 0, "rows": []}


def test_metadata_uncertainty_has_no_retry_or_row(setup, monkeypatch):
    class Broken:
        def __init__(self, **kwargs):
            setup.observed["metadata"] += 1
            raise TimeoutError("synthetic metadata uncertainty")

    monkeypatch.setattr("openai.OpenAI", Broken)
    result = collection.collect(
        setup.path, setup.hash, Decimal("11.00"), pricing_review=setup.price
    )
    assert result["model_metadata_reads"] == 1
    assert setup.observed["metadata"] == 1 and not setup.observed["rows"]
    assert all(r["status"] == "NOT_RUN" for r in result["rows"])
