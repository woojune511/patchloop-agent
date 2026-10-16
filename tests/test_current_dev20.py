"""Current capability panel preserves original inputs and bounded execution settings."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from diagnostics import current_dev20 as panel
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package


def test_twenty_packages_preserve_issues_and_private_bytes_and_register_tests():
    paths = list((repository_root() / panel.PACKAGES).glob("*/public.yaml"))
    assert len(paths) == 20
    for path in paths:
        current = load_task_package(path.parent)
        original = repository_root() / "tasks/dev-train" / current.public.task_id
        previous = load_task_package(original)
        assert current.public.issue == previous.public.issue
        assert current.public.repository == previous.public.repository
        assert current.environment == previous.environment
        assert current.private_spec_hash == previous.private_spec_hash
        for source in original.rglob("*"):
            if source.is_file() and source.name != "public.yaml":
                assert (
                    source.read_bytes() == (path.parent / source.relative_to(original)).read_bytes()
                )
        assert current.public.visible_checks == previous.public.visible_checks
        assert len(current.public.test_suites) == 1
        suite = current.public.test_suites[0]
        assert suite.test_roots == current.public.constraints.additive_test_roots
        protected = [".patchloop-hidden/**"]
        if current.public.repository.url == "https://github.com/sqlfluff/sqlfluff.git":
            protected.append("src/sqlfluff/testing/**")
        assert current.public.constraints.forbidden_paths == protected


def test_request_enables_dependencies_without_automatic_probe_replay(tmp_path):
    entry = {
        "index": 5,
        "instance_id": "pvlib__pvlib-python-1707",
        "prepared_source": str(tmp_path / "source.json"),
    }
    req = panel.request(entry, tmp_path / "live", tmp_path / "preparation")
    assert req.model == "gpt-5.4-mini-2026-03-17"
    assert req.repeat == 1 and req.resume_run_id is None
    assert req.enable_probes and req.probe_recheck == req.probe_policy == "none"
    assert req.max_cost_usd == panel.old.ROW_CAP
    assert req.prepared_probe_dependencies == (
        tmp_path / "preparation/dependencies/5/prepared-probe-dependencies.json"
    )
    assert req.task == repository_root() / panel.PACKAGES / "5/public.yaml"
    assert req.env_file == Path(".env").resolve()
    assert req.evaluation_reserve_seconds == 330
    assert req.limits.wall_time_seconds == 1800


def test_disagreement_and_unknown_usage_are_not_success_or_zero_billing():
    result = panel.summarize(
        {
            "rows": [
                {
                    "index": 0,
                    "ok": False,
                    "assessment": {"ok": False, "agreement": False, "status": "PASS"},
                    "accounting": {"billing_known": False, "cost_nanos": 17},
                },
            ]
        },
        [{"instance_id": "task-a"}, {"instance_id": "task-b"}],
    )
    assert result["resolved"] == 0 and result["planned"] == 2
    assert not result["billing_known"] and not result["complete_agreeing_evaluation"]
    assert result["recorded_cost_nanos"] == 17
    assert result["rows"][0]["instance_id"] == "task-a"


def test_reduced_allocation_and_external_inputs_reach_actual_requests(tmp_path):
    values = {
        "row_cap_usd": "0.88",
        "dependency_root": str(tmp_path / "existing-dependencies"),
        "env_file": str(tmp_path / "credential.env"),
    }
    (tmp_path / "panel-settings.json").write_text(json.dumps(values), encoding="utf-8")
    entries = [
        {"index": i, "instance_id": "pydicom__pydicom-1413", "prepared_source": "source.json"}
        for i in range(1, 21)
    ]
    requests = [panel.request(entry, tmp_path / "live", tmp_path) for entry in entries]
    assert sum(req.max_cost_usd for req in requests) == Decimal("17.60")
    assert panel.allocation(tmp_path) == {"row_cap_usd": "0.88", "total_cap_usd": "17.60"}
    assert Decimal("6.2666922") + sum(req.max_cost_usd for req in requests) < Decimal("24")
    for req in requests:
        assert req.env_file == Path(values["env_file"])
        assert req.prepared_probe_dependencies.is_relative_to(Path(values["dependency_root"]))
        assert req.repeat == 1 and req.limits.max_model_calls == 40


@pytest.mark.parametrize("cap", ["0", "-0.1", "NaN", "Infinity"])
def test_invalid_panel_allocation_fails_before_execution(tmp_path, cap):
    (tmp_path / "panel-settings.json").write_text(
        json.dumps({"row_cap_usd": cap}), encoding="utf-8"
    )
    with pytest.raises(ContractError, match="positive finite"):
        panel.allocation(tmp_path)
