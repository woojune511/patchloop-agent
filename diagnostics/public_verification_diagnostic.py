"""Operator-only synthetic controls; no solver, default policy or quality claim.

The fixture is trusted, locally authored code. Its observed entry/expectation fields
illustrate judgment errors; they are not tamper-resistant attestations for arbitrary
candidate code. Expected values come from the frozen public fixture specification.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repair_verification import _compare, _observation
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SPEC = {
    "origin": "operator-authored synthetic public contract; not a benchmark oracle",
    "requirement": "report(record) preserves id and returns ratio=value/reference. "
                   "Records need an id and a positive reference; "
                   "quotient is a different entry point.",
    "entry_point": "report",
    "cases": [
        {"id": "alpha", "input": {"id": "alpha", "value": 8, "reference": 4},
         "expected": {"id": "alpha", "ratio": 2}},
        {"id": "beta", "input": {"id": "beta", "value": 3, "reference": 6},
         "expected": {"id": "beta", "ratio": 0.5}},
    ],
}
PREFIX = """def quotient(record):
    return {'id': record['id'], 'ratio': record['value'] / record['reference']}

def report(record):
    if 'id' not in record:
        raise ValueError('missing id')
"""
SOURCES = {
    "base": PREFIX + "    return {'id': record['id'], 'ratio': record['value']}\n",
    "correct": PREFIX + "    return quotient(record)\n",
    "raw_value": PREFIX + "    return {'id': record['id'], 'ratio': float(record['value'])}\n",
    "constant": PREFIX + "    return {'id': record['id'], 'ratio': 1}\n",
}
CONTROLS = {
    "correct": ("correct", "contract"),
    "raw_value": ("raw_value", "contract"),
    "constant": ("constant", "contract"),
    "self_confirming": ("raw_value", "candidate_derived_expectation"),
    "wrong_entry": ("raw_value", "wrong_entry"),
    "caught_setup": ("correct", "caught_setup"),
}
TEST_SOURCE = '''import json
from pathlib import Path
import pytest
import sample

plan = json.loads(Path("plan.json").read_text())

@pytest.mark.parametrize("case", plan["cases"], ids=lambda case: case["id"])
def test_contract(case):
    record = dict(case["input"])
    mode = plan["mode"]
    if mode == "caught_setup":
        record.pop("id")
    target = sample.quotient if mode == "wrong_entry" else sample.report
    expected = case["expected"]
    if mode == "candidate_derived_expectation":
        expected = {"id": record["id"], "ratio": record["value"]}
    observed = {"id": case["id"], "entry": target.__name__, "input": record,
                "expected": expected, "actual": None, "error": None}
    try:
        observed["actual"] = target(record)
    except ValueError as error:
        observed["error"] = type(error).__name__
    print("\\nPUBLIC_OBSERVATION:" + json.dumps(observed), flush=True)
    if mode == "caught_setup":
        return  # Intentional weak control: caught exception, normal pytest/process exit.
    assert observed["error"] is None
    assert observed["actual"] == expected
'''
SELECTORS = [{"path": "test_contract.py", "function": "test_contract",
              "parameter_names": ["case"], "indices": [0, 1]}]


def judge(observation, stdout):
    """Separate execution from fitness to assess this frozen synthetic requirement."""
    result = {"execution": observation["status"], "readiness": "UNKNOWN",
              "behavior": "NOT_ASSESSED"}
    if observation["status"] != "COMPLETED":
        return result
    try:
        rows = [json.loads(line.removeprefix("PUBLIC_OBSERVATION:"))
                for line in stdout.splitlines() if line.startswith("PUBLIC_OBSERVATION:")]
        if [row["id"] for row in rows] != [case["id"] for case in SPEC["cases"]]:
            raise ValueError("missing/duplicate observation")
        for row, case in zip(rows, SPEC["cases"], strict=True):
            if row["input"] != case["input"]:
                return {**result, "readiness": "SETUP_ERROR"}
            if row["error"] is not None:
                return {**result, "readiness": "TARGET_ERROR"}
            if row["entry"] != SPEC["entry_point"]:
                return {**result, "readiness": "ENTRY_POINT_MISMATCH"}
            if row["expected"] != case["expected"]:
                return {**result, "readiness": "EXPECTATION_MISMATCH"}
        return {**result, "readiness": "READY", "behavior": "PASS" if all(
            row["actual"] == case["expected"]
            for row, case in zip(rows, SPEC["cases"], strict=True)
        ) else "FAIL"}
    except (ValueError, KeyError, TypeError):
        return {**result, "readiness": "INVALID_OBSERVATION"}


def run(root: Path):
    root, repo = root.resolve(), repository_root().resolve()
    if root.exists() or root.is_relative_to(repo) or repo.is_relative_to(root):
        raise ContractError("diagnostic requires a fresh external root")
    root.mkdir(parents=True)
    store, journal = ArtifactStore(root), DevJournal(root, "run_dev_publicjudgment")
    frozen = {"spec": SPEC, "test_source_hash": sha256_bytes(TEST_SOURCE.encode()),
              "controls": CONTROLS, "sources": SOURCES,
              "code_hashes": {name: sha256_bytes((repo / name).read_bytes()) for name in (
                  "diagnostics/public_verification_diagnostic.py",
                  "patchloop/repair_verification.py", "patchloop/sandbox/pytest_report.py")}}
    freeze = store.put_json(frozen)
    journal.append("public_judgment_frozen", {"artifact": freeze.model_dump(mode="json")})
    wrapper = (repo / "patchloop/sandbox/pytest_report.py").read_text(encoding="utf-8")
    deadline, results = ExecutionDeadline.from_remaining(90), {}
    for name, (candidate, mode) in CONTROLS.items():
        plan = canonical_json({"cases": SPEC["cases"], "mode": mode})
        rows = []
        for phase, source in (
            ("base_with_tests", SOURCES["base"]), ("patched", SOURCES[candidate]),
        ):
            workspace = root / "workspaces" / name / phase
            workspace.mkdir(parents=True)
            for path, text in {"sample.py": source, "test_contract.py": TEST_SOURCE,
                               "plan.json": plan}.items():
                (workspace / path).write_text(text, encoding="utf-8", newline="\n")
            args = (["-q", "-s", "test_contract.py"], SELECTORS, ".", "PYTEST_REPORT:")
            check = RegisteredCheck(id="synthetic-public-contract", timeout_seconds=10,
                command=["python", "-c", wrapper + "\nmain(*" + repr(args) + ")"],
                environment={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", **(
                    {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if os.name == "nt" else {})})
            identity = {"control": name, "phase": phase, "plan_hash": sha256_bytes(plan.encode()),
                        "source_hash": sha256_bytes(source.encode()),
                        "test_source_hash": sha256_bytes(
                            (workspace / "test_contract.py").read_bytes())}
            journal.append("public_judgment_started", identity)
            raw = asdict(LocalSandbox().run_check(workspace, check, deadline=deadline))
            observation = _observation(raw, "PYTEST_REPORT:")
            row = {**identity, "check_id": check.id, "pytest": True,
                   "observation": observation, "judgment": judge(observation, raw["stdout"]),
                   "receipt": store.put_json(raw).model_dump(mode="json")}
            rows.append(row)
            journal.append("public_judgment_finished", row)
        results[name] = {"phases": rows, "comparison": _compare(rows, SELECTORS)}
    summary = {"scope": "synthetic controls only; not semantic proof for arbitrary code",
               "model_behavior_improvement": "NOT_RUN", "acceptance": "NOT_RUN",
               "model_calls": 0, "official": False, "claim_eligible": False,
               "freeze_hash": freeze.content_hash, "controls": results}
    store.write_text_immutable(root / "result.json", canonical_json(summary) + "\n")
    journal.append("public_judgment_closed", {"summary_hash": sha256_json(summary)})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    print(canonical_json(run(parser.parse_args().root)))
