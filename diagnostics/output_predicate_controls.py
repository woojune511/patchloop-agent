"""Public-example controls, evaluated only inside the existing probe sandbox."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json

TASK = "swebench-lite-dev-sqlfluff-sqlfluff-1733"


def controls(issue: str) -> list[dict]:
    section = issue.replace("\r", "").split("## Expected Behaviour", 1)[1]
    section = section.split("## Observed Behaviour", 1)[0]
    block = re.search(r"```sql\s*\n(.*?)```", section, re.S)
    if block is None:
        raise ContractError("public expected example is missing")
    expected = block.group(1).strip("\n") + "\n"
    if expected.count("        my_id,") != 1 or expected.count("        one_more\n") != 1:
        raise ContractError("public control anchors changed")
    return [
        {"id": "expected", "actual": expected, "expected_accept": True},
        {"id": "original_symptom", "expected_accept": False,
         "actual": expected.replace("        my_id,", "         my_id,")},
        {"id": "different_wrong_output", "expected_accept": False,
         "actual": expected.replace("        my_id,", "     my_id,")},
        {"id": "missing_field", "expected_accept": False,
         "actual": expected.replace("        one_more\n", "")},
    ]


def program(source: str, panel: list[dict]) -> str:
    # Source is data on the host. Only DockerProbeSandbox executes it.
    rows = [{"id": p["id"], "actual": p["actual"]} for p in panel]
    return f"import json\nns = {{}}\nexec({source!r}, ns)\nrows = {rows!r}\n" + """
observed = []
for row in rows:
    try:
        value = ns['accepts'](row['actual'])
        observed.append({'id': row['id'], 'accepted': value if type(value) is bool else None,
                         'valid_bool': type(value) is bool, 'error': None})
    except Exception as error:
        observed.append({'id': row['id'], 'accepted': None, 'valid_bool': False,
                         'error': type(error).__name__})
print(json.dumps(observed), flush=True)
"""


def classify(result: dict, panel: list[dict]) -> dict:
    if (result["exit_code"] != 0 or result["timed_out"] or result["cleanup_failed"]
            or result["truncated"]):
        return {"status": "EXECUTION_INCOMPLETE", "matches": None}
    try:
        rows = json.loads(result["stdout"])
        valid = isinstance(rows, list) and len(rows) == len(panel) and all(
            isinstance(row, dict) and row.get("id") == expected["id"]
            and row.get("valid_bool") is True and type(row.get("accepted")) is bool
            and row.get("error") is None
            for row, expected in zip(rows, panel, strict=True)
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        return {"status": "INVALID_OUTPUT", "matches": None}
    matches = [row["accepted"] == expected["expected_accept"]
               for row, expected in zip(rows, panel, strict=True)]
    return {"status": "CONTROL_MATCH" if all(matches) else "CONTROL_MISMATCH",
            "matches": matches, "observations": rows,
            "semantic_scope": "four public-example controls; not exhaustive coverage"}


def calibrate(root: Path, *, saved_report: Path | None = None,
              saved_report_hash: str | None = None) -> dict:
    if root.exists() or root.resolve().is_relative_to(repository_root()):
        raise ContractError("calibration needs a fresh external root")
    task = repository_root() / "tasks/dev-train" / TASK / "public.yaml"
    public = load_task_package(task.parent).public
    panel = controls(public.issue.description)
    expected = panel[0]["actual"]
    candidates = {
        "positive_expected": "def accepts(actual):\n    return actual.splitlines() == "
        + repr(expected.splitlines()) + "\n",
        "symptom_only": "def accepts(actual):\n    return '         my_id,' not in actual\n",
        "constant_true": "def accepts(actual):\n    return True\n",
        "predicate_error": "def accepts(actual):\n    raise ValueError('invalid check')\n",
    }
    provenance = {"origin": "operator-authored controls", "provider_calls": 0}
    if saved_report is not None:
        raw = saved_report.read_bytes()
        if sha256_bytes(raw) != saved_report_hash:
            raise ContractError("saved public response hash mismatch")
        response = json.loads(raw)
        calls = response.get("tool_calls", [])
        if len(calls) != 1 or calls[0]["name"] != "submit_predicate":
            raise ContractError("expected one saved predicate")
        args = calls[0]["arguments"]
        candidates["saved_model_predicate"] = args["python_source"]
        provenance["saved_response"] = {
            "path": str(saved_report), "hash": saved_report_hash,
            "source_hash": sha256_bytes(args["python_source"].encode()),
            "quote_valid": args["requirement_quote"] in public.issue.description,
            "original_report_status": response["report_status"],
            "assessment": "new operator replay; original report remains unchanged",
        }
    root.mkdir(parents=True)
    workspace = root / "public-workspace"
    workspace.mkdir()
    (workspace / "README.txt").write_text("Neutral public output controls.\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    subprocess.run(["git", "-C", str(workspace), "add", "README.txt"], check=True)
    store = ArtifactStore(root / "artifacts")
    journal = DevJournal(root, "run_dev_positivecontrols")
    sandbox = DockerProbeSandbox()
    profile = sandbox.preflight()
    journal.append("calibration_prepared", {
        "provenance": provenance, "profile": profile,
        "public_hash": sha256_json(public.model_dump(mode="json")),
        "controls": store.put_json(panel).model_dump(mode="json")})
    outcomes = {}
    for name, source in candidates.items():
        text = program(source, panel)
        journal.append("control_started", {"name": name,
                                           "program": store.put_text(text).model_dump(mode="json")})
        result = sandbox.run_probe(workspace, "Does the predicate distinguish public outputs?",
                                   text, deadline=None,
                                   execution_identity={"run_id": journal.run_id, "action_id": name})
        outcome = {"result": result, "classification": classify(result, panel)}
        journal.append("control_finished", {
            "name": name, "outcome": store.put_json(outcome).model_dump(mode="json")})
        outcomes[name] = outcome
        if result["cleanup_failed"] or result["timed_out"]:
            raise ContractError("sandbox uncertainty; calibration stopped")
    expected_statuses = {"positive_expected": "CONTROL_MATCH", "symptom_only": "CONTROL_MISMATCH",
                         "constant_true": "CONTROL_MISMATCH", "predicate_error": "INVALID_OUTPUT"}
    passed = all(outcomes[name]["classification"]["status"] == status
                 for name, status in expected_statuses.items())
    summary = {"calibration_passed": passed, "provenance": provenance, "rows": outcomes,
               "official": False, "claim_eligible": False, "provider_calls": 0}
    ArtifactStore(root).write_text_immutable(
        root / "calibration.json", canonical_json(summary) + "\n")
    journal.append("calibration_closed", {"summary_hash": sha256_json(summary)})
    return summary
