"""Funded-entry authorization/readiness tests use only inert key and SDK doubles."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_isort_uptake_execution import source as source  # noqa: F401

from diagnostics import isort_table_collection as collection
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
    ref = store.put_json({"synthetic": True}).model_dump(mode="json")
    oracle = store.put_text("SYNTHETIC_ORACLE").model_dump(mode="json")
    plan = {
        "model": "gpt-5.4-2026-03-05",
        "reasoning_effort": "xhigh",
        "service_tier": "default",
        "task_path": str(source.public_path),
        "credential_file": str(tmp_path / "absent.env"),
        "caps": {"generations": 6, "input_counts": 6, "provider_usd": "3.50"},
        "cost_basis": {"type": "repository_registered_rates_not_live_price_verification"},
        "feedback": ref,
        "grading": ref,
        "static_parity": ref,
        "terminal_public_oracle": oracle,
        "inheritance": {"prepared_cut_sequence": 1},
    }
    feedback = {
        "snapshots": [{}, {"receipt": {"image_digest": "fixture", "profile_hash": "fixture"}}]
    }
    monkeypatch.setattr(collection.checkpoint, "load_design", lambda: (plan, source, feedback))
    monkeypatch.setattr(collection.observation_comparison, "clean_implementation", lambda: None)
    monkeypatch.setattr(collection, "git_commit", lambda: "committed-fixture")
    monkeypatch.setattr(collection.runner, "_runtime_hash", lambda: "fixture-runtime")
    expected = {
        "input": [
            {
                "role": "user",
                "content": canonical_json(
                    {"state": {"remaining_budget": {"active_wall_time_seconds": 270}}}
                ),
            }
        ]
    }
    monkeypatch.setattr(collection.checkpoint, "expected_first_request", lambda _: expected)
    first_ref = store.put_json(expected).model_dump(mode="json")
    parity = collection.checkpoint.compare_first_request(expected, expected)
    rehearsal = tmp_path / "rehearsal"
    journal = DevJournal(rehearsal, "run_dev_isorttablebridge")
    journal.append(
        "isort_table_mock_started",
        {
            "diagnostic_implementation_hash": collection.observation_exposure.implementation_hash(),
        },
    )
    result = {
        "provider_free": True,
        "design_hash": collection.checkpoint.DESIGN_HASH,
        "provider_calls": 0,
        "credential_reads": 0,
        "metadata_calls": 0,
        "first_request": first_ref,
        "row": {
            "first_input_parity": parity,
            "first_input_verified": True,
            "stop_remaining": False,
            "result": {"terminal": "AGENT_STOPPED"},
            "new_counts": 2,
            "new_generations": 2,
            "new_tool_actions": 2,
            "accepted_new_edits": 0,
        },
    }
    (rehearsal / "result.json").write_text(canonical_json(result), encoding="utf-8")
    validation = tmp_path / "validation.json"
    validation.write_text(
        canonical_json(
            {
                "provider_free": True,
                "status": "PASS",
                "implementation_hash": collection.observation_exposure.implementation_hash(),
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "ready" / "manifest.json"
    prepared = collection.prepare(rehearsal, tmp_path / "live", manifest, validation)
    observed = {
        "keys": 0,
        "metadata": 0,
        "environments": 0,
        "rows": 0,
        "metadata_failure": False,
        "environment_failure": False,
    }

    def environment(*args):
        observed["environments"] += 1
        return {"status": "PREFLIGHT_FAILED" if observed["environment_failure"] else "READY"}

    def key(_):
        observed["keys"] += 1
        return "inert-test-key"

    class MetadataClient:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            assert kwargs["base_url"] == "https://api.openai.com/v1"
            observed["metadata_timeout"] = kwargs["timeout"]
            self.models = SimpleNamespace(retrieve=self.retrieve)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def retrieve(self, model):
            observed["metadata"] += 1
            if observed["metadata_failure"]:
                raise TimeoutError("inert metadata uncertainty")
            return SimpleNamespace(id=model)

    def fork(*args, **kwargs):
        assert kwargs["provider_free"] is False
        assert kwargs["credential_file"] == tmp_path / "absent.env"
        deadline = kwargs["deadline"]
        assert deadline.expires_at <= deadline.clock() + 720
        return SimpleNamespace()

    def row(branch, group, oracle, *, reviewer):
        observed["rows"] += 1
        assert callable(reviewer)
        assert group.ledger.cap_nanos == 3_500_000_000
        return {
            "row": "I2",
            "billing_known": True,
            "stop_remaining": False,
            "result": {"terminal": "EVALUATOR_FAIL", "evaluator": "inert private verdict"},
        }

    monkeypatch.setattr(collection.observation_comparison, "check_environment", environment)
    monkeypatch.setattr(collection.runner, "load_exact_openai_api_key", key)
    monkeypatch.setattr("openai.OpenAI", MetadataClient)
    monkeypatch.setattr(collection.checkpoint, "restore_branch", fork)
    monkeypatch.setattr(collection.execution, "run_row", row)
    review = {
        "verified_on": datetime.now(UTC).date().isoformat(),
        "source": "https://developers.openai.com/api/docs/pricing",
        "usd_per_million": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
        "model": plan["model"],
        "service_tier": "default",
    }
    return SimpleNamespace(manifest=manifest, prepared=prepared, observed=observed, review=review)


@pytest.mark.parametrize(
    "invalid", ["cap", "hash", "price", "scope", "runtime", "evidence", "parity", "table_binding"]
)
def test_reject_before_credentials_or_any_provider_work(setup, invalid):
    digest, cap, review = setup.prepared["manifest_hash"], Decimal("3.50"), setup.review
    if invalid == "cap":
        cap = Decimal("3.51")
    elif invalid == "hash":
        digest = "sha256:" + "a" * 64
    elif invalid == "price":
        review = {**review, "verified_on": "2000-01-01"}
    else:
        manifest = json.loads(setup.manifest.read_bytes())
        if invalid == "scope":
            manifest["repeat"] = 2
        elif invalid == "runtime":
            manifest["implementation_hash"] = "changed"
        elif invalid == "parity":
            manifest["first_input_parity"]["difference_seconds"] = 5
        elif invalid == "table_binding":
            manifest["feedback"]["content_hash"] = "changed"
        else:
            manifest["validation"]["content_hash"] = "changed"
        setup.manifest.write_text(canonical_json(manifest), encoding="utf-8")
        digest = sha256_bytes(setup.manifest.read_bytes())
    with pytest.raises(Exception, match="approval|changed|review"):
        collection.collect(setup.manifest, digest, cap, pricing_review=review)
    assert setup.observed["keys"] == setup.observed["metadata"] == setup.observed["rows"] == 0


def test_one_row_metadata_once_no_repeat_and_private_verdict_excluded(setup):
    result = collection.collect(
        setup.manifest,
        setup.prepared["manifest_hash"],
        Decimal("3.50"),
        pricing_review=setup.review,
    )
    assert setup.observed["rows"] == setup.observed["metadata"] == setup.observed["keys"] == 1
    assert "inert private verdict" not in canonical_json(result)
    with pytest.raises(Exception, match="fresh output root"):
        collection.collect(
            setup.manifest,
            setup.prepared["manifest_hash"],
            Decimal("3.50"),
            pricing_review=setup.review,
        )
    assert setup.observed["metadata"] == 1


@pytest.mark.parametrize("failure", ["metadata_failure", "environment_failure"])
def test_readiness_uncertainty_never_retries_or_runs_row(setup, failure):
    setup.observed[failure] = True
    result = collection.collect(
        setup.manifest,
        setup.prepared["manifest_hash"],
        Decimal("3.50"),
        pricing_review=setup.review,
    )
    assert result["row"]["status"] == "STOPPED"
    assert setup.observed["rows"] == 0
    assert setup.observed["metadata"] == (failure == "metadata_failure")


@pytest.mark.parametrize("elapsed", [280, 282])
def test_preparation_time_also_bounds_metadata_and_solver(setup, monkeypatch, elapsed):
    now = [1000]
    monkeypatch.setattr(collection, "monotonic", lambda: now[0])
    original = collection.observation_comparison.check_environment

    def environment(*args):
        result = original(*args)
        now[0] += elapsed
        return result

    monkeypatch.setattr(collection.observation_comparison, "check_environment", environment)
    result = collection.collect(
        setup.manifest,
        setup.prepared["manifest_hash"],
        Decimal("3.50"),
        pricing_review=setup.review,
    )
    if elapsed == 280:
        assert setup.observed["metadata_timeout"] == 1
        assert setup.observed["metadata"] == setup.observed["rows"] == 1
    else:
        assert result["row"]["status"] == "STOPPED"
        assert setup.observed["keys"] == setup.observed["metadata"] == setup.observed["rows"] == 0
