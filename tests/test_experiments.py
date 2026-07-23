from __future__ import annotations

import pytest
from pydantic import ValidationError

from patchloop.evals.runner import ExperimentSuite


def test_live_campaign_requires_explicit_cost_approval() -> None:
    with pytest.raises(ValidationError, match="live_cost_approved"):
        ExperimentSuite(
            experiment_id="live-test",
            tasks=["task"],
            conditions=["no_memory"],
            model="openai",
        )


def test_core_campaign_requires_exact_design() -> None:
    with pytest.raises(ValidationError, match="12 unique"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=["task"],
            conditions=["no_memory"],
            model="mock",
        )
