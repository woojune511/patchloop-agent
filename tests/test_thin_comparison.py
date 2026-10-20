"""Provider-free checks for the frozen policy comparison and public verdicts."""

import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from diagnostics import parallel_dev_batch as batch
from diagnostics import thin_comparison as panel
from diagnostics.thin_comparison_public import classify_public
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

ORDER = [
    (18, "A", 1), (2, "B", 1), (20, "B", 1), (9, "A", 1),
    (9, "B", 1), (20, "A", 1), (2, "A", 1), (18, "B", 1),
    (20, "A", 2), (9, "B", 2), (18, "B", 2), (2, "A", 2),
    (2, "B", 2), (18, "A", 2), (9, "A", 2), (20, "B", 2),
]


def packet(tmp_path):
    rows = []
    for number, (index, arm, repetition) in enumerate(ORDER, 1):
        row_id = f"{number:02}-task{index}-{arm}-rep{repetition}"
        request = DevRunRequest(
            task=tmp_path / "tasks" / str(index) / "public.yaml",
            state_root=tmp_path / "live" / row_id,
            provider="openai", model="gpt-5.4-2026-03-05",
            env_file=tmp_path / "unused.env", max_cost_usd=Decimal("4.00"),
            reasoning_effort="xhigh", max_output_tokens=25000,
            prepared_source=tmp_path / "source" / str(index) / "prepared-source.json",
            prepared_probe_dependencies=(
                tmp_path / "deps" / str(index) / "prepared-probe-dependencies.json"
            ),
            context_policy="segmented-v1", segment_boundary_policy="result-or-size-v1",
            agent_policy="current" if arm == "A" else "thin",
            planning_policy="brief-v1" if arm == "A" else "none",
            enable_probes=True, probe_policy="none", probe_recheck="none",
            repair_recheck=True, repair_inspection_policy="protected-v1",
            completion_cost_policy="per-call-v1", evaluation_reserve_seconds=330,
        )
        rows.append({
            "row": number, "row_id": row_id, "wave": (number - 1) // 4 + 1,
            "position_in_wave": (number - 1) % 4 + 1, "task_index": index,
            "instance_id": f"instance-{index}", "arm": arm, "repetition": repetition,
            "request": request.model_dump(mode="json"),
        })
    return {
        "rows": rows, "live_root": str(tmp_path / "live"),
        "model": "gpt-5.4-2026-03-05", "credential_file": str(tmp_path / "unused.env"),
        "native_entries": {str(index): {"index": index} for index in (18, 20, 2, 9)},
    }


@pytest.fixture(autouse=True)
def frozen_proposal(tmp_path, monkeypatch):
    """Production validation uses a frozen proposal without requiring local evidence."""
    planned = packet(tmp_path)
    monkeypatch.setattr(panel, "proposal", lambda: deepcopy(planned))
    return planned


@pytest.mark.parametrize("stop_wave", [None, 1, 2, 4])
def test_actual_wave_driver_preserves_schedule_caps_and_permanent_stop(tmp_path, stop_wave):
    planned = packet(tmp_path)
    calls, assessed = [], []

    def assess(root, entry, value, request):
        assessed.append((root, entry["index"], request))
        return {"ok": True, "status": "PASS", "agreement": True}

    def dispatch(rows, *, total_cap, workers, journal, after_row):
        calls.append(rows)
        assert total_cap == Decimal("16.00") and workers == 2
        assert len({row["task_index"] for row in rows}) == 4
        values = []
        for index, row in enumerate(rows):
            request = DevRunRequest.model_validate(row["request"])
            assert request.max_cost_usd == Decimal("4.00")
            value = {
                "index": index, "ok": True,
                "accounting": {
                    "cost_nanos": 17, "billing_known": True, "counting_known": True,
                },
            }
            value["assessment"] = after_row(index, value, request)
            values.append(value)
        return {"rows": values, "stopped": len(calls) == stop_wave, "not_started": 0}

    journal = DevJournal(tmp_path / "journal", "run_dev_thintest")
    outcome = panel.execute_waves(tmp_path, planned, journal, dispatch=dispatch, assess=assess)
    started = (stop_wave or 4) * 4
    assert len(calls) == (stop_wave or 4)
    assert outcome["started"] == started and outcome["not_started"] == 16 - started
    assert outcome["stopped"] == (stop_wave is not None)
    assert outcome["allocation"] == "CLOSED"
    assert outcome["recorded_cost_nanos"] == started * 17
    assert [row["row_id"] for row in outcome["rows"]] == [
        row["row_id"] for row in planned["rows"][:started]
    ]
    assert len({root for root, _, _ in assessed}) == started
    for (_, index, request), row in zip(assessed, planned["rows"], strict=False):
        assert index == row["task_index"]
        assert request.model == "gpt-5.4-2026-03-05"
        assert request.agent_policy == ("current" if row["arm"] == "A" else "thin")
        assert request.planning_policy == ("brief-v1" if row["arm"] == "A" else "none")
        assert request.model_dump(mode="json") == row["request"]
    reservations = [event for event in journal.events()
                    if event["event_type"] == "allocation_reserved"]
    assert len(reservations) == 1
    assert reservations[0]["payload"]["transfer"] is False


@pytest.mark.parametrize("change", [
    "cap", "confound", "resume", "repeat", "order", "state", "nested_state", "policy", "model",
])
def test_expansion_or_confounded_comparison_rejected_before_dispatch(tmp_path, change):
    rows = packet(tmp_path)["rows"]
    request = rows[0]["request"]
    if change == "cap":
        request["max_cost_usd"] = "4.01"
    elif change == "confound":
        request["retained_source_chars"] = 48000
    elif change == "resume":
        request["resume_run_id"] = "run_dev_previous"
    elif change == "repeat":
        request["repeat"] = 2
    elif change == "order":
        rows.reverse()
    elif change == "state":
        request["state_root"] = rows[1]["request"]["state_root"]
    elif change == "nested_state":
        request["state_root"] = rows[1]["request"]["state_root"] + "/nested"
    elif change == "policy":
        request["agent_policy"], request["planning_policy"] = "thin", "none"
    else:
        request["model"] = "gpt-5.4-mini-2026-03-17"
    with pytest.raises((ContractError, ValueError)):
        panel.validate_rows(rows)


def synthetic_worker(serialized):
    """Execute no solver, provider, sandbox, or evaluator in the spawned process."""
    request = DevRunRequest.model_validate(serialized)
    request.state_root.mkdir(parents=True)
    return {
        "ok": True,
        "result": {"synthetic": True, "model": request.model,
                   "agent_policy": request.agent_policy},
        "accounting": {"cost_nanos": 17, "billing_known": True, "counting_known": True},
    }


def test_production_driver_and_worker_pool_continue_after_settled_task_limit(tmp_path):
    planned = packet(tmp_path)
    dispatches = []

    def assess(root, entry, value, request):
        assert value["result"]["agent_policy"] == request.agent_policy
        if Path(root).name == planned["rows"][0]["row_id"]:
            return {"ok": False, "status": "NOT_RUN", "disposition": "task_limit"}
        return {"ok": True, "status": "PASS", "agreement": True}

    def dispatch(rows, **kwargs):
        dispatches.append([row["row_id"] for row in rows])
        return batch.run_parallel_rows(rows, **kwargs, execute=synthetic_worker)

    outcome = panel.execute_waves(
        tmp_path, planned, DevJournal(tmp_path / "journal", "run_dev_thinspawntest"),
        dispatch=dispatch, assess=assess,
    )
    assert len(dispatches) == 4
    assert outcome["started"] == 16 and outcome["not_started"] == 0
    assert not outcome["stopped"]
    assert outcome["recorded_cost_nanos"] == 16 * 17
    assert outcome["rows"][0]["assessment"]["disposition"] == "task_limit"
    assert outcome["rows"][0]["ok"] is False
    assert all(row["ok"] for row in outcome["rows"][1:])


@pytest.mark.parametrize("problem", ["unstarted", "over_cap"])
def test_incomplete_wave_or_row_overspend_never_admits_later_waves(tmp_path, problem):
    dispatches = []

    def dispatch(rows, **kwargs):
        dispatches.append(rows)
        return {
            "rows": [{
                "index": 0, "ok": True, "accounting": {
                    "cost_nanos": 4_000_000_001 if problem == "over_cap" else 17,
                    "billing_known": True, "counting_known": True,
                },
            }],
            "not_started": 3, "stopped": False,
        }

    def execute():
        return panel.execute_waves(
            tmp_path, packet(tmp_path), DevJournal(tmp_path / "journal", "run_dev_thinpartial"),
            dispatch=dispatch,
        )

    if problem == "over_cap":
        with pytest.raises((ContractError, ValueError)):
            execute()
    else:
        outcome = execute()
        assert outcome["started"] == 1 and outcome["not_started"] == 15
        assert outcome["stopped"]
    assert len(dispatches) == 1


def authorization(planned, tmp_path):
    digest = sha256_json(planned)
    return {
        "approved": True, "packet_hash": digest,
        "human_message": "Execute these 16 frozen rows with a total cap of USD 64.",
        "model": "gpt-5.4-2026-03-05", "credential_file": str(tmp_path / "unused.env"),
        "repetitions": 2, "row_count": 16,
        "total_cap_usd": "64.00",
    }


@pytest.mark.parametrize("problem", [
    None, "no_approval", "wrong_hash", "empty_message", "wrong_model", "wrong_credentials",
    "wrong_repetitions", "wrong_count", "cap_argument",
])
def test_explicit_authorization_binds_exact_scope_and_positive_invocation_cap(tmp_path, problem):
    planned = packet(tmp_path)
    approval = authorization(planned, tmp_path)
    digest = sha256_json(planned)
    cap = Decimal("64.00")
    if problem == "no_approval":
        approval["approved"] = False
    elif problem == "wrong_hash":
        approval["packet_hash"] = "sha256:" + "0" * 64
    elif problem == "empty_message":
        approval["human_message"] = ""
    elif problem == "wrong_model":
        approval["model"] = "gpt-5.4-mini-2026-03-17"
    elif problem == "wrong_credentials":
        approval["credential_file"] = str(tmp_path / "other.env")
    elif problem == "wrong_repetitions":
        approval["repetitions"] = 3
    elif problem == "wrong_count":
        approval["row_count"] = 17
    elif problem == "cap_argument":
        cap = Decimal("63.99")

    def validate():
        return panel.validate_authorization(
            planned, approval, approved_manifest_hash=digest, approved_cap_usd=cap,
            credential_file=tmp_path / "unused.env",
        )

    if problem is None:
        validate()
    else:
        with pytest.raises((ContractError, ValueError)):
            validate()


@pytest.mark.parametrize("problem", [
    "missing_authorization", "missing_preflight", "unbound_preflight", "manifest_drift",
    "preflight_drift",
])
def test_execute_rejects_missing_or_changed_admission_evidence_before_dispatch(
    tmp_path, monkeypatch, problem,
):
    root = tmp_path / "preparation"
    root.mkdir()
    prepared = packet(tmp_path)
    receipt = {"passed": True, "provider_calls": 0, "preparation_hash": sha256_json(prepared)}
    validation_path = root / "validation.json"
    validation_path.write_text('{"passed": true}', encoding="utf8")
    manifest = {
        **prepared, "preparation_hash": sha256_json(prepared),
        "preflight_hash": sha256_json(receipt),
        "validation": {"path": str(validation_path),
                       "file_hash": sha256_bytes(validation_path.read_bytes())},
    }
    digest = sha256_json(manifest)
    approval = authorization(manifest, tmp_path)
    for name, value in (("manifest.json", manifest), ("preparation.json", prepared),
                        ("preflight.json", receipt), ("authorization.json", approval)):
        if (problem == "missing_authorization" and name == "authorization.json"
                or problem == "missing_preflight" and name == "preflight.json"):
            continue
        if problem == "manifest_drift" and name == "manifest.json":
            value = {**manifest, "model": "changed-after-approval"}
        elif problem == "preflight_drift" and name == "preflight.json":
            value = {**receipt, "passed": False}
        (root / name).write_text(json.dumps(value), encoding="utf8")
    journal = DevJournal(root, panel.JOURNAL)
    if problem != "unbound_preflight":
        journal.append("preflight_passed", {
            "preparation_hash": sha256_json(prepared), "receipt_hash": sha256_json(receipt),
        })
    monkeypatch.setattr(panel, "validate_inputs", lambda *args, **kwargs: None)

    def forbidden(*args, **kwargs):
        pytest.fail("admission failure reached execution")

    monkeypatch.setattr(panel, "execute_waves", forbidden)
    with pytest.raises((ContractError, ValueError, FileNotFoundError)):
        panel.execute(root, approved_manifest_hash=digest, approved_cap_usd=Decimal("64.00"),
                      credential_file=tmp_path / "unused.env")
    assert not Path(prepared["live_root"]).exists()
    assert not any(event["event_type"] == "panel_started" for event in journal.events())


@pytest.mark.parametrize("submitted", [False, True])
def test_unsubmitted_or_unavailable_native_result_never_runs_public_probe(
    tmp_path, monkeypatch, submitted,
):
    request = DevRunRequest.model_validate(packet(tmp_path)["rows"][0]["request"])
    run = {"run_id": "run_dev_synthetic", "terminal": "LIMIT_REACHED", "artifact_hashes": {}}
    value = {"accounting": {"billing_known": True}, "result": {"runs": [run]}}

    def forbidden(*args, **kwargs):
        pytest.fail("unsubmitted or unavailable row reached evaluator/probe")

    monkeypatch.setattr(panel.environments, "environment", forbidden)
    monkeypatch.setattr(panel.current_dev20.old, "native_assessment", forbidden)
    if submitted:
        run["artifact_hashes"]["submitted_patch"] = "sha256:" + "0" * 64
        monkeypatch.setattr(panel.current_dev20, "assess", lambda *args: {
            "ok": False, "status": "NOT_RUN", "disposition": "task_limit",
        })
    outcome = panel.assess_submission(tmp_path / "assessment", {"index": 18}, value, request)
    assert outcome["status"] == "NOT_RUN" and outcome["public"]["status"] == "NOT_RUN"
    assert outcome["ok"] is not submitted
    assert not (tmp_path / "assessment").exists()


def bound_packet(tmp_path, monkeypatch):
    expected = packet(tmp_path)
    expected.update(head="frozen-commit", runtime_hash="frozen-runtime",
                    implementation={"driver.py": "frozen-driver"},
                    native_identity={"harness": "frozen-harness"})
    expected["row_identities"] = {row["row_id"]: {"model": "bound-model", "tool": "bound-tool"}
                                  for row in expected["rows"]}
    expected["cases"] = {}
    for key, entry in expected["native_entries"].items():
        source = tmp_path / f"native-{key}.json"
        source.write_text("frozen native input", encoding="utf8")
        entry.update(native_row=str(source), native_row_hash=sha256_bytes(source.read_bytes()))
        expected["cases"][key] = {
            "rubric": {"task_index": int(key), "program": "frozen-public-program"},
            "dependencies": {"content": "frozen-dependencies"}, "source": "frozen-source",
        }
    current = deepcopy(expected)
    monkeypatch.setattr(panel, "proposal", lambda: deepcopy(expected))
    monkeypatch.setattr(panel, "git_commit", lambda: current["head"])
    monkeypatch.setattr(panel, "runtime_content_hash", lambda: current["runtime_hash"])
    monkeypatch.setattr(panel, "bindings", lambda: current["implementation"])
    monkeypatch.setattr(panel, "_row_identities", lambda rows: {
        row["row_id"]: current["row_identities"][row["row_id"]] for row in rows
    })
    monkeypatch.setattr(panel, "rubric_packet", lambda: {"rubrics": {
        key: case["rubric"] for key, case in current["cases"].items()
    }})
    monkeypatch.setattr(panel, "_case_environment", lambda req, case, rubric: (
        {key: value for key, value in current["cases"][str(rubric["task_index"])].items()
         if key != "rubric"}, None, None,
    ))
    monkeypatch.setattr(panel.portfolio_dev20, "native_identity",
                        lambda: current["native_identity"])
    return expected, current


@pytest.mark.parametrize("drift", [
    None, "head", "runtime_hash", "implementation", "model_tool", "dependencies", "rubric",
    "native_input", "request",
])
def test_bound_worker_rejects_execution_drift_before_solver_admission(tmp_path, monkeypatch, drift):
    expected, current = bound_packet(tmp_path, monkeypatch)
    serialized = deepcopy(expected["rows"][0]["request"])
    if drift in {"head", "runtime_hash", "implementation"}:
        current[drift] = {"driver.py": "changed"} if drift == "implementation" else "changed"
    elif drift == "model_tool":
        current["row_identities"][expected["rows"][0]["row_id"]]["model"] = "changed"
    elif drift in {"dependencies", "rubric"}:
        field = "content" if drift == "dependencies" else "program"
        current["cases"]["18"][drift][field] = "changed"
    elif drift == "native_input":
        Path(expected["native_entries"]["18"]["native_row"]).write_text("changed", encoding="utf8")
    elif drift == "request":
        serialized["max_cost_usd"] = "4.01"
    solved, stopped = [], []
    monkeypatch.setattr(batch, "stop_workers", lambda: stopped.append(True))
    monkeypatch.setattr(batch, "solve_row", lambda serialized: solved.append(serialized) or "ok")
    if drift is None:
        assert panel.solve_frozen_row(serialized, expected=expected) == "ok"
        assert solved == [serialized] and not stopped
    else:
        with pytest.raises((ContractError, ValueError), match="changed|drift"):
            panel.solve_frozen_row(serialized, expected=expected)
        assert not solved and stopped == [True]


def test_production_wave_driver_rechecks_identity_before_later_wave(tmp_path, monkeypatch):
    planned, current = bound_packet(tmp_path, monkeypatch)
    dispatches, solves = [], []

    def solve(serialized):
        solves.append(serialized)
        return {"ok": True, "accounting": {
            "cost_nanos": 17, "billing_known": True, "counting_known": True,
        }}

    def dispatch(rows, *, execute, after_row, **kwargs):
        dispatches.append(rows)
        values = []
        for index, row in enumerate(rows):
            value = execute(row["request"])
            value["index"] = index
            value["assessment"] = after_row(
                index, value, DevRunRequest.model_validate(row["request"]),
            )
            values.append(value)
        current["implementation"]["driver.py"] = "modified-after-wave-one"
        return {"rows": values, "stopped": False, "not_started": 0}

    monkeypatch.setattr(batch, "solve_row", solve)
    monkeypatch.setattr(batch, "run_parallel_rows", dispatch)
    monkeypatch.setattr(panel, "validate_inputs",
                        lambda value, **kwargs: panel._execution_identity(value))
    journal = DevJournal(tmp_path / "journal", "run_dev_thindrift")
    outcome = panel.execute_waves(
        tmp_path, planned, journal, assess=lambda *args: {"ok": True, "status": "PASS"},
    )
    assert outcome["stopped"] and outcome["allocation"] == "CLOSED"
    assert outcome["started"] == 4 and outcome["not_started"] == 12
    assert outcome["recorded_cost_nanos"] == 4 * 17
    assert len(dispatches) == 1 and len(solves) == 4
    assert [event["payload"]["wave"] for event in journal.events()
            if event["event_type"] == "wave_started"] == [1]
    assert any(event["event_type"] == "identity_stop" and event["payload"]["phase"] == "after"
               for event in journal.events())
    assert json.loads((tmp_path / "result.json").read_bytes()) == outcome


def test_assessment_rechecks_frozen_inputs_before_evaluation(tmp_path, monkeypatch):
    planned, current = bound_packet(tmp_path, monkeypatch)
    current["cases"]["18"]["dependencies"]["content"] = "changed-before-assessment"

    def forbidden(*args, **kwargs):
        pytest.fail("changed binding reached native/public evaluation")

    monkeypatch.setattr(panel.current_dev20, "assess", forbidden)
    request = DevRunRequest.model_validate(planned["rows"][0]["request"])
    with pytest.raises((ContractError, ValueError), match="environment drift"):
        panel.assess_submission(tmp_path / "assessment", {"index": 18}, {}, request, packet=planned)


def observation(rows, *, setup="passed"):
    return {
        "exit_code": 0, "stdout": json.dumps(rows), "setup_checks": {"status": setup},
        "execution_policy": {"cleanup_status": "confirmed"}, "timed_out": False,
        "cleanup_failed": False, "truncated": False, "deadline_exhausted": False,
    }


def public_example(case):
    if case == "1733":
        spec = {
            "case": case, "cte_input": "WITH a AS (SELECT x FROM t) SELECT * FROM a;",
            "top_input": "SELECT x FROM t;", "expected_lines": ["WITH a AS (", "    SELECT x", ")"],
            "ordinary_expected_lines": ["SELECT x", "FROM t;"],
        }
        rows = [
            {"stage": "before_fix", "cte_sql": spec["cte_input"], "top_sql": spec["top_input"]},
            {"stage": "after_fix", "cte_fixed": "\n".join(spec["expected_lines"]),
             "top_fixed": "\n".join(spec["ordinary_expected_lines"])},
            {"cte_has_extra_space": False, "top_has_extra_space": False},
        ]
        result = observation(rows)
        result["stdout"] = "\n".join(map(repr, rows))
        return spec, rows, result
    if case == "2419":
        spec = {"case": case, "expected_messages": {
            name: f"Use 'COALESCE' instead of '{name}'." for name in ("IFNULL", "NVL")
        }}
        rows = [{
            "name": name, "sql": f"SELECT {name}(a, b) FROM t;",
            "violations": [] if name == "COALESCE" else [{
                "code": "L060", "description": spec["expected_messages"][name],
            }],
        } for name in ("IFNULL", "NVL", "COALESCE")]
    elif case == "1072":
        spec = {"case": case, "expected_rounded_values": [47.85, 50.85, 50.85]}
        rows = [{"case": name, "values": [47.85, 50.85, 50.85], "index_preserved": True,
                 "name": "tmod"} for name in ("naive", "aware")]
    else:
        spec = {"case": case}
        rows = [{"suppress": value, "raw_before": True, "raw_value": "2.0 ",
                 "conversion_rejected": True, "completed": value} for value in (True, False)]
        rows[0].update(invalid_omitted=True, valid_preserved=True)
        rows[1]["error"] = "ValueError"
    return spec, rows, observation(rows, setup="not_checked" if case in {"1072", "1694"}
                                   else "passed")


@pytest.mark.parametrize("case", ["1733", "2419", "1072", "1694"])
def test_public_classifiers_accept_full_example_but_reject_control_regressions(case):
    spec, rows, result = public_example(case)
    assert classify_public(spec["case"], result, spec)["status"] == "PASS"
    if case == "1733":
        rows[1]["top_fixed"] = "SELECT missing_column;"
        result["stdout"] = "\n".join(map(repr, rows))
    elif case == "2419":
        rows[2]["violations"] = [{"code": "L060", "description": "wrong control"}]
        result["stdout"] = json.dumps(rows)
    elif case == "1072":
        rows[1]["index_preserved"] = False
        result["stdout"] = json.dumps(rows)
    else:
        rows[0]["valid_preserved"] = False
        result["stdout"] = json.dumps(rows)
    assert classify_public(spec["case"], result, spec)["status"] == "FAIL"


@pytest.mark.parametrize("case", ["1733", "2419", "1072", "1694"])
@pytest.mark.parametrize("problem", [
    "timed_out", "cleanup_failed", "truncated", "deadline_exhausted", "cleanup_unknown",
    "missing_cleanup", "setup_failed", "bad_output", "exception",
])
def test_uncertain_public_execution_never_becomes_behavior_pass_or_fail(case, problem):
    spec, _, result = public_example(case)
    if problem == "cleanup_unknown":
        result["execution_policy"]["cleanup_status"] = "unknown"
    elif problem == "missing_cleanup":
        result.pop("execution_policy")
    elif problem == "setup_failed":
        result["setup_checks"]["status"] = "failed"
    elif problem == "bad_output":
        result["stdout"] = "this is not a probe result"
    elif problem == "exception":
        result["exit_code"] = 1
    else:
        result[problem] = True
    assert classify_public(spec["case"], result, spec)["status"] == "UNASSESSED"


@pytest.mark.parametrize("case", ["1733", "2419"])
def test_sql_public_checks_require_completed_setup(case):
    spec, _, result = public_example(case)
    result["setup_checks"]["status"] = "not_checked"
    assert classify_public(spec["case"], result, spec)["status"] == "UNASSESSED"


def test_pvlib_output_values_must_match_and_both_timezones_must_exist():
    spec, rows, result = public_example("1072")
    rows[1]["values"] = [0, 0, 0]
    result["stdout"] = json.dumps(rows)
    assert classify_public(spec["case"], result, spec)["status"] == "FAIL"
    result["stdout"] = json.dumps(rows[:1])
    assert classify_public(spec["case"], result, spec)["status"] == "UNASSESSED"


def test_sql_classifiers_do_not_accept_removed_symptoms_or_wrong_quote_messages():
    spec, rows, result = public_example("1733")
    rows[1]["cte_fixed"] = "WITH a AS (\n)"
    result["stdout"] = "\n".join(map(repr, rows))
    assert classify_public("1733", result, spec)["status"] == "FAIL"
    spec, rows, result = public_example("2419")
    rows[0]["violations"][0]["description"] = "Use `COALESCE` instead of `IFNULL`."
    result["stdout"] = json.dumps(rows)
    assert classify_public("2419", result, spec)["status"] == "FAIL"


def test_pydicom_requires_reproduced_invalid_conversion_before_suppression():
    spec, rows, result = public_example("1694")
    rows[0]["conversion_rejected"] = False
    result["stdout"] = json.dumps(rows)
    assert classify_public("1694", result, spec)["status"] == "UNASSESSED"


def test_public_spec_and_observation_are_not_mutated_by_assessment():
    for case in ("1733", "2419", "1072", "1694"):
        spec, _, result = public_example(case)
        before = deepcopy((spec, result))
        classify_public(spec["case"], result, spec)
        assert (spec, result) == before
