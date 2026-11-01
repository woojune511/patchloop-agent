"""One frozen public counterexample check, executed through the normal gateway."""
from __future__ import annotations

import copy
import json
import time

from diagnostics import counterexample_packet as packet_api
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, RegisteredCheck
from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import canonical_json, sha256_bytes, sha256_json

CHECK_ID = "public-path-counterexamples"
PREFIX = "PUBLIC-COUNTEREXAMPLE-CHECK:"
TIMEOUT_SECONDS = 35
OUTPUT_LIMIT_BYTES = 12_000


def _failed_details(packet, assessment, actual):
    result = copy.deepcopy(assessment)
    result.update(failed_case_details=[], failed_case_details_complete=True)
    cases = {row["case"]: row for row in packet["cases"]}
    for name in assessment["preservation"]["failed_case_ids"]:
        case = cases[name]
        result["failed_case_details"].append({
            **{key: case[key] for key in packet_api.INPUT_FIELDS},
            "actual": actual[name], "expected": case["importlib_reference"],
        })
        if len((PREFIX + canonical_json(result) + "\n").encode()) > OUTPUT_LIMIT_BYTES - 1:
            result["failed_case_details"].pop()
            result["failed_case_details_complete"] = False
            break
    return result


def required_check(packet):
    """Bind public observations without pretending an imported failure ran again."""
    from patchloop.dev.required_checks import RequiredPublicCheck

    packet = copy.deepcopy(packet)
    packet_api.require(packet.get("schema") == packet_api.SCHEMA
                       and sha256_bytes(packet["program_text"].encode()) == packet["program_hash"]
                       and packet["program_hash"] == packet_api.SOURCE_HASHES["program"],
                       "public check program changed")
    mandatory = [name for name in packet_api.CASE_IDS if name not in packet_api.PREEXISTING_IDS]
    packet_api.require(packet["mandatory_case_ids"] == mandatory
                       and packet["regressions"] == list(packet_api.REGRESSION_IDS)
                       and packet["preexisting_discrepancies"] == list(packet_api.PREEXISTING_IDS),
                       "public check acceptance partition changed")
    cases = {row["case"]: row for row in packet["cases"]}
    packet_api.require(len(cases) == len(packet["cases"])
                       and set(cases) == set(packet_api.CASE_IDS), "public check cases changed")
    for name in mandatory:
        packet_api.require(cases[name]["base"] == cases[name]["importlib_reference"],
                           "required public case did not pass on base")
    binding = {
        "schema": "frozen-public-counterexample-check-v1",
        "packet_hash": sha256_json(packet), "program_hash": packet["program_hash"],
        "mandatory_cases": [{**{key: cases[name][key] for key in packet_api.INPUT_FIELDS},
                             "expected": cases[name]["importlib_reference"]}
                            for name in mandatory],
        "preexisting_excluded": packet["preexisting_discrepancies"],
        "environment": packet["environment"],
        "source_provenance": packet["evidence_files"],
        "timeout_seconds": TIMEOUT_SECONDS, "output_limit_bytes": OUTPUT_LIMIT_BYTES,
    }
    check = RegisteredCheck(id=CHECK_ID, command=["python", "-c", packet["program_text"]],
                            timeout_seconds=TIMEOUT_SECONDS, output_limit_bytes=OUTPUT_LIMIT_BYTES)

    def group(names):
        failed = [name for name in names
                  if cases[name]["candidate"] != cases[name]["importlib_reference"]]
        return {"status": "FAIL" if failed else "PASS", "case_ids": list(names),
                "passed_case_ids": [name for name in names if name not in failed],
                "failed_case_ids": failed}

    assessment = {"status": "FAIL", "preservation": group(mandatory),
                  "regressions": group(packet["regressions"]),
                  "preexisting": {**group(packet["preexisting_discrepancies"]), "mandatory": False}}
    packet_api.require(assessment["preservation"]["status"] == "FAIL"
                       and assessment["regressions"]["failed_case_ids"] == packet["regressions"],
                       "imported public counterexample is not a confirmed failure")
    assessment = _failed_details(packet, assessment,
                                 {name: case["candidate"] for name, case in cases.items()})
    output = {"check_id": CHECK_ID, "diff_hash": packet["candidate_diff_hash"], "passed": False,
              "failure_signature": sha256_json({"check": binding, "assessment": assessment}),
              "stdout": PREFIX + canonical_json(assessment) + "\n", "stderr": "",
              "exit_code": 1, "timed_out": False, "truncated": False,
              "deadline_exhausted": False, "cleanup_failed": False}
    return RequiredPublicCheck(check=check, binding=binding, observation=output)


class CheckSandbox:
    """Delegate ordinary checks; run only the bound public program in its pinned environment."""
    supports_execution_deadline = True
    supports_public_execution = True

    def __init__(self, delegate, probe, journal, packet):
        self.delegate, self.probe, self.journal = delegate, probe, journal
        self.packet = copy.deepcopy(packet)
        self.entry = required_check(self.packet)
        self.packet_hash = sha256_json(self.packet)
        self.binding_hash = self.entry.binding_hash
        self.store = ArtifactStore(journal.root / "artifacts")
        self.official = getattr(delegate, "official", False)
        self.backend = getattr(delegate, "backend", "docker")

    def run_check(self, workspace, check, *, deadline=None, execution_identity=None,
                  execution_targets=None):
        if check.id != CHECK_ID:
            options = {}
            if getattr(self.delegate, "supports_execution_deadline", False):
                options.update(deadline=deadline, execution_identity=execution_identity)
                if getattr(self.delegate, "supports_public_execution", False):
                    options["execution_targets"] = execution_targets
            return self.delegate.run_check(workspace, check, **options)
        if (check != self.entry.check or self.entry.binding_hash != self.binding_hash
                or sha256_json(self.packet) != self.packet_hash
                or not execution_identity or self.probe is None):
            raise RecoveryError("registered public check binding changed")
        diff = WorkspaceManager.diff_summary(workspace, deadline=deadline).patch_hash
        identity = {"execution_identity": execution_identity, "check_id": CHECK_ID,
                    "binding_hash": self.binding_hash, "diff_hash": diff}
        prior = [event for event in self.journal.events()
                 if event["event_type"] in {"counterexample_check_started",
                                             "counterexample_check_finished"}
                 and event["payload"].get("execution_identity") == execution_identity]
        for event in prior:
            if any(event["payload"].get(key) != value for key, value in identity.items()):
                raise RecoveryError("public check recovery identity changed")
        finished = [event for event in prior
                    if event["event_type"] == "counterexample_check_finished"]
        if finished:
            reference = finished[-1]["payload"]["receipt"]
            receipt = json.loads(self.store.read_bytes(Artifact.model_validate(reference)))
        else:
            if prior:
                raise RecoveryError("public check execution is unsettled",
                                    details={"execution_uncertain": True})
            end = time.monotonic() + check.timeout_seconds
            bounded = ExecutionDeadline(min(end, deadline.expires_at) if deadline else end)
            bounded.check()
            expected = {key: self.packet["environment"][key]
                        for key in ("image_digest", "profile_hash")}
            if self.probe.preflight(deadline=bounded) != expected:
                raise RecoveryError("public check probe environment changed")
            self.journal.append("counterexample_check_started", identity)
            try:
                receipt = self.probe.run_probe(
                    workspace, "Do all frozen required public path cases hold?",
                    self.packet["program_text"], deadline=bounded,
                    execution_identity=execution_identity,
                    **({"execution_targets": execution_targets}
                       if execution_targets is not None else {}),
                )
            except Exception as exc:
                raise RecoveryError("public check execution did not settle",
                                    details={"execution_uncertain": True}) from exc
            reference = self.store.put_json(receipt).model_dump(mode="json")
            self.journal.append("counterexample_check_finished", {**identity, "receipt": reference})
        try:
            packet_api.require(isinstance(receipt, dict), "invalid public check receipt")
            packet_api.require(all(receipt.get(key) == self.packet["environment"][key]
                                   for key in ("image_digest", "profile_hash"))
                               and receipt.get("execution_policy", {}).get("dependencies")
                               == self.packet["environment"]["dependencies"],
                               "public check execution environment changed")
            parsed = packet_api.parse_receipt(receipt, self.packet["program_hash"])
            assessment = packet_api.assess_rows(self.packet, parsed["rows"])
            assessment = _failed_details(
                self.packet, assessment, {row["case"]: row["public_api"] for row in parsed["rows"]})
        except (ContractError, ValueError, TypeError, KeyError) as exc:
            uncertain = isinstance(receipt, dict) and bool(receipt.get("cleanup_failed"))
            raise RecoveryError("public check observation is incomplete or invalid",
                                details={"public_check_receipt": reference,
                                         "execution_uncertain": uncertain,
                                         "diagnostic": str(exc)}) from exc
        stdout = PREFIX + canonical_json(assessment) + "\n"
        return SandboxResult(
            command=list(check.command), exit_code=0 if assessment["status"] == "PASS" else 1,
            stdout=stdout, stderr="", duration_ms=int(receipt.get("duration_ms", 0)),
            timed_out=False, truncated=False, original_output_bytes=len(stdout.encode()),
            execution_policy={**receipt["execution_policy"],
                              "required_public_check_binding_hash": self.binding_hash,
                              "public_check_receipt": reference},
            public_execution=receipt.get("public_execution"),
        )


def summary(journal, packet, diff_hash):
    """Read the current registered result; never execute or infer a stale PASS."""
    latest, imported, starts = None, None, {}
    entry = required_check(packet)
    for event in journal.events():
        if event["event_type"] == "action_started":
            started = event["payload"]
            if started.get("tool") == "run_check":
                starts[started["action_id"]] = started.get("arguments", {}).get("check_id")
        if (event["event_type"] == "public_check_imported"
                and event["payload"].get("observation_id") == entry.observation_id):
            observed = event["payload"]["output"]
            packet_api.require(observed.get("binding_hash") == entry.binding_hash,
                               "imported public check binding changed")
            if observed.get("diff_hash") == diff_hash:
                imported = observed
        if event["event_type"] == "action_finished":
            result = event["payload"]["result"]
            output = result.get("output", {})
            check_id = output.get("check_id") or starts.get(result.get("action_id"))
            observed_diff = output.get("diff_hash") or result.get("workspace_diff_hash")
            if (result.get("tool") == "run_check" and check_id == CHECK_ID
                    and observed_diff == diff_hash):
                latest = (event["sequence"], result)
    if latest is None:
        if imported is None:
            return {"status": "NOT_RUN", "check_id": CHECK_ID, "candidate_diff_hash": diff_hash,
                    "reason": "required check has no result for the current diff"}
        output = imported
        provenance = {"source": "imported_observation", "new_execution": False}
    else:
        seq, result = latest
        output = result["output"]
        provenance = {"source": "registered_check", "action_id": result["action_id"],
                      "sequence": seq, "input_hash": result["input_hash"]}
        if result.get("status") != "succeeded" or type(output.get("passed")) is not bool:
            return {"status": "INCOMPLETE", "check_id": CHECK_ID,
                    "candidate_diff_hash": diff_hash, **provenance}
    reports = [line[len(PREFIX):] for line in output.get("stdout", "").splitlines()
               if line.startswith(PREFIX)]
    packet_api.require(len(reports) == 1, "required public check summary is missing")
    assessment = json.loads(reports[0])
    packet_api.require((assessment["status"] == "PASS") == output["passed"],
                       "required public check summary contradicts its receipt")
    return {**assessment, "check_id": CHECK_ID, "candidate_diff_hash": diff_hash,
            "feedback_before_completion": True, "additional_final_executions": 0, **provenance}
