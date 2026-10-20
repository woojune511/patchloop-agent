"""Authorization/readiness seams with inert metadata, key and executor doubles."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import uptake_collection as collection
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture
def setup(source, tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("provider network forbidden")

    monkeypatch.setattr("socket.socket.connect", no_network)
    monkeypatch.setattr("socket.create_connection", no_network)
    store = ArtifactStore(tmp_path / "inputs")
    prices = {
        "source": "https://developers.openai.com/api/docs/pricing",
        "usd_per_million": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
    }
    price_ref = store.put_json(prices).model_dump(mode="json")
    oracle = store.put_text("print('synthetic oracle')").model_dump(mode="json")
    plan = {
        "model": "gpt-5.4-2026-03-05",
        "task_path": str(source.public_path),
        "credential_file": str(tmp_path / "absent.env"),
        "order": ["B1", "B2"],
        "rows": [{"cell": "B1"}, {"cell": "B2"}],
        "caps": {"generations": 12},
        "cost": {"row_cap_usd": "3.50", "invocation_cap_usd": "7.00", "pricing": price_ref},
        "inheritance": {"prepared_cut_sequence": 1},
        "terminal_public_oracle": oracle,
    }
    monkeypatch.setattr(collection.checkpoint, "load_design", lambda: (plan, source, {}))
    monkeypatch.setattr(collection.observation_comparison, "clean_implementation", lambda: None)
    monkeypatch.setattr(collection, "git_commit", lambda: "committed-fixture")
    monkeypatch.setattr(collection.runner, "_runtime_hash", lambda: "fixture-runtime")
    rehearsal = tmp_path / "rehearsal"
    journal = DevJournal(rehearsal, "run_dev_uptakebridge")
    journal.append(
        "uptake_mock_started",
        {"diagnostic_implementation_hash": collection.observation_exposure.implementation_hash()},
    )
    result = {
        "provider_free": True,
        "design_hash": collection.checkpoint.DESIGN_HASH,
        "provider_calls": 0,
        "credential_reads": 0,
        "rows": [
            {"cell": c, "first_input_verified": True, "stop_remaining": False} for c in ["B1", "B2"]
        ],
    }
    (rehearsal / "result.json").write_text(canonical_json(result), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    prepared = collection.prepare(rehearsal, tmp_path / "live", manifest)
    observed = {"keys": 0, "metadata": 0, "environments": 0, "rows": [], "failure": False}

    def environment(*args):
        observed["environments"] += 1
        return {"status": "READY"}

    def key(_):
        observed["keys"] += 1
        return "inert-test-key"

    class MetadataClient:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            assert kwargs["base_url"] == "https://api.openai.com/v1"
            self.models = SimpleNamespace(retrieve=self.retrieve)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def retrieve(self, model):
            observed["metadata"] += 1
            if observed["failure"]:
                raise TimeoutError("inert metadata failure")
            return SimpleNamespace(id=model)

    def fork(*args, **kwargs):
        assert kwargs["provider_free"] is False
        return SimpleNamespace(row=args[5])

    def row(branch, group, oracle):
        observed["rows"].append(branch.row["cell"])
        return {
            "cell": branch.row["cell"],
            "billing_known": True,
            "stop_remaining": False,
            "result": {"terminal": "EVALUATOR_FAIL", "evaluator": "inert private verdict"},
        }

    monkeypatch.setattr(collection.observation_comparison, "check_environment", environment)
    monkeypatch.setattr(collection.runner, "load_exact_openai_api_key", key)
    monkeypatch.setattr("openai.OpenAI", MetadataClient)
    monkeypatch.setattr(collection.checkpoint, "saved_turn", lambda *args: (None, None))
    monkeypatch.setattr(collection.checkpoint, "restore_branch", fork)
    monkeypatch.setattr(collection.execution, "run_row", row)
    review = {
        "verified_on": datetime.now(UTC).date().isoformat(),
        **prices,
        "model": plan["model"],
        "service_tier": "default",
    }
    return SimpleNamespace(manifest=manifest, prepared=prepared, observed=observed, review=review)


@pytest.mark.parametrize("invalid", ["cap", "hash", "price"])
def test_approval_rejection_precedes_credentials_and_provider(setup, invalid):
    digest, cap, review = setup.prepared["manifest_hash"], Decimal("7.00"), setup.review
    if invalid == "cap":
        cap = Decimal("7.01")
    elif invalid == "hash":
        digest = "sha256:" + "a" * 64
    else:
        review = {**review, "verified_on": "2000-01-01"}
    with pytest.raises(Exception, match="approval|changed|review"):
        collection.collect(setup.manifest, digest, cap, pricing_review=review)
    assert setup.observed["keys"] == setup.observed["metadata"] == 0
    assert setup.observed["rows"] == []


def test_metadata_once_and_private_verdict_not_in_automatic_summary(setup):
    result = collection.collect(
        setup.manifest,
        setup.prepared["manifest_hash"],
        Decimal("7.00"),
        pricing_review=setup.review,
    )
    assert setup.observed["metadata"] == setup.observed["environments"] == 1
    assert setup.observed["rows"] == ["B1", "B2"]
    assert "inert private verdict" not in canonical_json(result)
    assert "EVALUATOR_FAIL" not in canonical_json(result)
    assert result["counts"] == result["generations"] == 0  # executor double
    with pytest.raises(Exception, match="fresh output root"):
        collection.collect(
            setup.manifest,
            setup.prepared["manifest_hash"],
            Decimal("7.00"),
            pricing_review=setup.review,
        )
    assert setup.observed["metadata"] == 1


def test_metadata_uncertainty_stops_both_without_retry(setup):
    setup.observed["failure"] = True
    result = collection.collect(
        setup.manifest,
        setup.prepared["manifest_hash"],
        Decimal("7.00"),
        pricing_review=setup.review,
    )
    assert setup.observed["metadata"] == 1 and setup.observed["rows"] == []
    assert [r["status"] for r in result["rows"]] == ["NOT_RUN", "NOT_RUN"]


def test_manifest_scope_tampering_is_rejected_even_with_a_new_hash(setup):
    manifest = json.loads(setup.manifest.read_bytes())
    manifest["rows"] = [{"cell": "B2"}, {"cell": "B1"}]
    setup.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    with pytest.raises(Exception, match="scope changed"):
        collection.collect(
            setup.manifest,
            sha256_bytes(setup.manifest.read_bytes()),
            Decimal("7.00"),
            pricing_review=setup.review,
        )
    assert setup.observed["metadata"] == setup.observed["keys"] == 0
