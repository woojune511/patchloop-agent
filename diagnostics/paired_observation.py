"""One bounded, fixed-candidate comparison phase inside the ordinary dev loop.

Only the optional seeded diagnostic installs these hooks. All provider admission,
action identities, sandbox execution and final evaluation stay in the dev runner.
"""

from __future__ import annotations

import copy
import json
import re
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from diagnostics import discovery_probe_expectation as expectation
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json, sha256_text

POLICY = "paired-observation-v1"
FIELD = "paired_observation"
EVENT = "diagnostic_paired_observation_policy"
MAX_TURNS = 4
SYSTEM_SUFFIX = (
    "\nThis run opts into the bounded paired_observation diagnostic described in current "
    "state. Its initial comparison phase temporarily offers only inspection, observation "
    "and stop actions. Follow its comparison schema during that phase; afterward all "
    "ordinary repair and completion rules apply. A limitation is not a verified comparison."
)
GUIDANCE = (
    "This optional diagnostic begins with one fixed-candidate comparison phase, using at "
    "most four of the existing model calls and the same total action/time/cost budgets. "
    "Use registered reads/searches to construct two concrete public cases. In comparison, "
    "select requirement_ids from evidence_catalog, describe each input and its expected "
    "JSON observation, "
    "justify both expectations, and say what would refute your interpretation. Different "
    "origins alone do not require different outcomes. The candidate and passing checks "
    "are not the authority for expected behavior. These are concise public test specifications. "
    "For run_probe, exercise current project code and print exactly one JSON object with "
    "keys a and b containing the actual observations for those inputs, at most 2048 UTF-8 "
    "bytes. Use the existing setup helpers to check actual construction and project paths; "
    "do not print your expected values as observations. Expected values stay outside the "
    "executed program. For run_check, select each case's evidence_ref from evidence_catalog: "
    "the selected registered check or a current successful read. Describe the concrete "
    "case in input; do not copy or reconstruct source quotations. IDs establish source "
    "identity, not whether the check exercises the proposed cases. For run_probe use "
    "evidence_ref=null; the program supplies the observations. "
    "If no justified pair is available, run a required check with comparison=null and state "
    "the limitation in turn_decision.basis; this records no comparison. A declaration rejected "
    "before execution remains correctable with a new action ID within the same four-call "
    "bound; it adds no calls and schedules no retry. Use the returned error and catalog to "
    "correct it, or record a limitation. Once admitted, an observation attempt (including "
    "execution failure) ends the phase. The four-call or resource bound also returns normal "
    "repair/check/finish choices. Inspect the "
    "actual result before choosing a repair; execution failure, differing values and invalid "
    "expectations are distinct. The result remains evidence about its observed diff only. "
    "No repeat is scheduled automatically and no new acceptance or finish condition is added."
)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    input: str = Field(min_length=1, max_length=600)
    expected_json: str = Field(min_length=1, max_length=2048)
    evidence_ref: str | None = Field(max_length=600)


class Design(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    requirement_ids: list[str] = Field(min_length=1, max_length=4)
    cases: list[Case] = Field(min_length=2, max_length=2)
    justification: str = Field(min_length=1, max_length=600)
    refutation: str = Field(min_length=1, max_length=600)
    limitations: str = Field(max_length=600)


def design_schema(*, nullable, catalog=None):
    # Inline the one nested type for the existing provider schema validator.
    schema = Design.model_json_schema()
    schema["properties"]["cases"]["items"] = schema.pop("$defs")["Case"]
    if catalog is not None:
        schema["properties"]["requirement_ids"]["items"]["enum"] = [
            r["id"] for r in catalog["requirements"]]
        schema["properties"]["cases"]["items"]["properties"]["evidence_ref"]["enum"] = (
            [r["id"] for r in catalog["checks"] + catalog["reads"]] if nullable else [None])
    if nullable:
        schema["type"] = ["object", "null"]
    return schema


def evidence_catalog(public_task, events=(), diff_hash=None):
    """References to existing public inputs, with no extra repository reads or case inference."""
    requirements = [{"id": "issue-title", "field": "issue.title",
                     "text": public_task["issue"]["title"]}]
    paragraphs = re.split(r"\n\s*\n", public_task["issue"]["description"].strip())
    requirements.extend({"id": f"issue-{index}", "field": "issue.description",
                         "paragraph": index, "text": text}
                        for index, text in enumerate(paragraphs, 1) if text)
    reads = []
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if (result["tool"] == "read_file" and result["status"] == "succeeded"
                and diff_hash is not None and result["workspace_diff_hash"] == diff_hash
                and result["output"].get("spans")):
            reads.append({"id": "read:" + result["action_id"], "action_id": result["action_id"],
                          "result_hash": sha256_json(result),
                          "spans": [{k: s[k] for k in ("path", "start_line", "end_line")}
                                    for s in result["output"]["spans"]]})
    return {"public_task_hash": sha256_json(public_task), "requirements": requirements,
            "checks": [{"id": "check:" + c["id"], "check_id": c["id"],
                        "command_hash": sha256_json(c["command"])}
                       for c in public_task["visible_checks"]],
            "reads": reads[-MAX_TURNS * 4:], "validation_scope": "source_identity_only"}


def prepare(value, public_task):
    design = Design.model_validate(value)
    catalog = evidence_catalog(public_task.model_dump(mode="json"))
    references = {r["id"]: r for r in catalog["requirements"]}
    if any(ref not in references for ref in design.requirement_ids):
        raise ContractError("unknown requirement ID; choose from evidence_catalog.requirements")
    expected = expectation.freeze(canonical_json({
        label: json.loads(expectation.freeze(case.expected_json))
        for label, case in zip(("a", "b"), design.cases, strict=True)
    }))
    return {"policy": POLICY, "design": design.model_dump(mode="json"),
            "design_hash": sha256_json(design.model_dump(mode="json")),
            "expected_json": expected, "public_task_hash": catalog["public_task_hash"],
            "requirement_references": [references[ref] for ref in design.requirement_ids],
            "interpretation_status": "model_authored_unverified", "coverage_status": "not_assessed"}


def bind_check(prepared, *, check_id, public_task, events, diff_hash):
    catalog = evidence_catalog(public_task.model_dump(mode="json"), events, diff_hash)
    selected = next((c for c in catalog["checks"] if c["check_id"] == check_id), None)
    if selected is None:
        raise ContractError(f"unknown public check: {check_id}")
    references = {r["id"]: r for r in [selected, *catalog["reads"]]}
    links = []
    for case in prepared["design"]["cases"]:
        ref = case["evidence_ref"]
        if ref not in references:
            raise ContractError("evidence_ref must select this check or a current read from "
                                "evidence_catalog")
        links.append(copy.deepcopy(references[ref]))
    return links


def probe_comparison(prepared, output):
    result = expectation.compare(prepared["expected_json"], output)
    observed = result["observed_json"]
    if observed is not None:
        value = json.loads(observed)
        if not isinstance(value, dict) or set(value) != {"a", "b"}:
            result.update(status="not_compared", reason="both_case_observations_required")
    return {**prepared, "observation": result,
            "execution_does_not_certify_case_construction": True}


def gateway_type(base):
    class ComparisonGateway(base):
        def _prepare_comparison(self, value, *, check_id=None, diff_hash=None):
            # Only declaration validation gets this marker. Execution exceptions retain
            # the normal failure path and must not silently re-open the observation phase.
            try:
                prepared = prepare(value, self.public_task) if value is not None else None
                links = (bind_check(prepared, check_id=check_id, public_task=self.public_task,
                                    events=self.journal.events(), diff_hash=diff_hash)
                         if prepared is not None and check_id is not None else None)
                if prepared is not None and check_id is None and any(
                    c["evidence_ref"] is not None for c in prepared["design"]["cases"]
                ):
                    raise ContractError("run_probe comparison uses evidence_ref=null")
                return prepared, links
            except (ContractError, ValidationError, ValueError) as exc:
                raise ContractError(str(exc), details={FIELD: {
                    "policy": POLICY, "status": "declaration_rejected", "execution_started": False,
                    "semantic_verdict": None,
                }}) from exc

        def _run_probe(self, question, python_source, *, execution_identity, comparison=None):
            prepared, _ = self._prepare_comparison(comparison)
            output = super()._run_probe(question, python_source,
                                        execution_identity=execution_identity)
            if prepared is not None:
                output[FIELD] = probe_comparison(prepared, output)
            return output

        def _run_check(self, check_id, *, execution_identity):
            events = self.journal.events()
            start = next(e["payload"] for e in reversed(events)
                         if e["event_type"] == "action_started"
                         and e["payload"]["action_id"] == execution_identity["action_id"])
            args = start["arguments"]
            prepared, links = self._prepare_comparison(
                args.get("comparison"), check_id=check_id, diff_hash=start["baseline_diff_hash"])
            output = super()._run_check(check_id, execution_identity=execution_identity)
            if "comparison" in args:
                output[FIELD] = {
                    **(prepared or {"policy": POLICY, "design": None}),
                    "observation": {
                        "status": "check_passed" if output.get("passed") else "check_failed",
                        "comparison_status": "model_interpretation_required"
                        if prepared else "not_requested",
                        "check_id": check_id, "case_links": links,
                        "diff_hash": output["diff_hash"],
                        "semantic_verdict": None, "coverage_status": "not_assessed",
                    },
                }
            return output

    return ComparisonGateway


def _result_view(result, starts, diff_hash):
    return {
        "action_id": result["action_id"], "input_hash": result["input_hash"],
        "tool": result["tool"], "status": result["status"],
        "error_code": result.get("error_code"), "message": result.get("message"),
        "observed_diff_hash": result["workspace_diff_hash"],
        "currency": "current" if diff_hash in (None, result["workspace_diff_hash"])
        else "historical",
        "comparison": copy.deepcopy(result["output"].get(FIELD)),
        "public_basis": (starts[result["action_id"]].get("turn_decision") or {}).get("basis"),
    }


def project(events, diff_hash=None):
    """One journal-derived phase; edits and segment boundaries never re-arm it."""
    seed = next(e["payload"]["seed_hash"] for e in events
                if e["event_type"] == "diagnostic_candidate_seeded")
    starts, turns, result, mutated = {}, 0, None, False
    rejection, rejected_count = None, 0
    for event in events:
        kind, payload = event["event_type"], event["payload"]
        turns += kind == "turn_started"
        if kind == "action_started":
            starts[payload["action_id"]] = payload
        if kind == "action_finished":
            observed = payload["result"]
            if (observed["tool"] == "replace_text" and observed["status"] == "succeeded"
                    and observed.get("output", {}).get("worktree_diff_hash", seed) != seed):
                mutated = True
            start = starts.get(observed["action_id"], {})
            if (observed["tool"] in {"run_probe", "run_check"}
                    and "comparison" in start.get("arguments", {})):
                comparison = observed["output"].get(FIELD) or {}
                if (observed["status"] == "failed"
                        and comparison.get("status") == "declaration_rejected"
                        and comparison.get("execution_started") is False):
                    rejection = observed
                    rejected_count += 1
                    continue
                result = observed
                break
    view = {"policy": POLICY, "instruction": GUIDANCE, "subject_diff_hash": seed,
            "phase": "observe", "max_phase_model_calls": MAX_TURNS,
            "phase_calls_started": min(turns, MAX_TURNS), "result": None,
            "rejected_declarations": rejected_count,
            "last_declaration_error": (_result_view(rejection, starts, diff_hash)
                                       if rejection is not None else None),
            "interpretation_status": "model_authored_unverified"}
    if result is not None:
        view["phase"] = "returned_to_repair"
        view["result"] = _result_view(result, starts, diff_hash)
    elif turns >= MAX_TURNS:
        view["phase"] = "unobserved_limit"
    elif mutated or (diff_hash is not None and diff_hash != seed):
        view["phase"] = "unobserved_candidate_changed"
    return view


def restrict(policy, view):
    if view["phase"] != "observe" or not policy.allowed_tools & {"run_check", "run_probe"}:
        return policy
    return replace(policy, allowed_tools=policy.allowed_tools & {
        "read_file", "search_files", "run_check", "run_probe", "stop_task",
    })


@contextmanager
def install(loop, *, enabled):
    """Scoped sequential hooks, with the complete new wire schema counted by run_dev."""
    if not enabled:
        yield
        return
    original_policy, original_context = loop._tool_policy, loop._build_context
    original_schemas = loop.dev_tool_schemas
    active = False
    catalog = None

    def policy(gateway, *args, **kwargs):
        result = original_policy(gateway, *args, **kwargs)
        snapshot = kwargs.get("snapshot")
        view = project(gateway.journal.events(), snapshot.diff.patch_hash if snapshot else None)
        return restrict(result, view)

    def context(**kwargs):
        nonlocal active, catalog
        state = json.loads(original_context(**kwargs))
        view = project(kwargs["journal"].events(), state["current_diff"]["patch_hash"])
        if (view["phase"] == "observe"
                and not set(state["available_tool_names"]) & {"run_check", "run_probe"}):
            view["phase"] = "unobserved_resource_boundary"
        active = view["phase"] == "observe"
        catalog = (evidence_catalog(state["public_task"], kwargs["journal"].events(),
                                    state["current_diff"]["patch_hash"]) if active else None)
        if catalog is not None:
            view["evidence_catalog"] = catalog
        state[FIELD] = view
        return canonical_json(state)

    def schemas(**kwargs):
        result = original_schemas(**kwargs)
        if active:
            for tool in result:
                if tool["name"] in {"run_check", "run_probe"}:
                    tool["description"] += (
                        " During the initial paired_observation phase, supply comparison "
                        "before execution as described in current state. Null on run_check "
                        "records a limitation, not a comparison; explain it in your basis. "
                        "Select evidence IDs from the current evidence_catalog; declarations "
                        "rejected before execution remain correctable within this phase.")
                    params = tool["parameters"]
                    params["properties"]["comparison"] = design_schema(
                        nullable=tool["name"] == "run_check", catalog=catalog)
                    params["required"].append("comparison")
        return result

    with patch.object(loop, "_tool_policy", policy), \
            patch.object(loop, "_build_context", context), \
            patch.object(loop, "dev_tool_schemas", schemas), \
            patch.object(loop, "DEV_SYSTEM_PROMPT", loop.DEV_SYSTEM_PROMPT + SYSTEM_SUFFIX):
        yield


def identity():
    return {"official": False, "policy": POLICY, "instruction_hash": sha256_text(GUIDANCE),
            "system_suffix_hash": sha256_text(SYSTEM_SUFFIX),
            "schema_hash": sha256_json(design_schema(nullable=False)),
            "evidence_interface": "public_reference_ids",
            "declaration_correction_within_phase": True,
            "max_phase_model_calls": MAX_TURNS, "rearm_after_mutation": False,
            "semantic_verdict": None}
