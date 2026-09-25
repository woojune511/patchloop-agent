"""One bounded, fixed-candidate comparison phase inside the ordinary dev loop.

Only the optional seeded diagnostic installs these hooks. All provider admission,
action identities, sandbox execution and final evaluation stay in the dev runner.
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, Field

from diagnostics import discovery_case_plan as case_plan
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
    "quote the public requirement, describe each input and its expected JSON observation, "
    "justify both expectations, and say what would refute your interpretation. Different "
    "origins alone do not require different outcomes. The candidate and passing checks "
    "are not the authority for expected behavior. These are concise public test specifications. "
    "For run_probe, exercise current project code and print exactly one JSON object with "
    "keys a and b containing the actual observations for those inputs, at most 2048 UTF-8 "
    "bytes. Use the existing setup helpers to check actual construction and project paths; "
    "do not print your expected values as observations. Expected values stay outside the "
    "executed program. For run_check, identify each case in the selected public check's "
    "command or in an already read current source span using check_excerpt and its read "
    "action ID (null means the selected command). Literal linkage is not semantic coverage. "
    "If no justified pair is available, run a required check with comparison=null and state "
    "the limitation in turn_decision.basis; this records no comparison. After one observation "
    "attempt, or the four-call bound, normal repair/check/finish choices return. Inspect the "
    "actual result before choosing a repair; execution failure, differing values and invalid "
    "expectations are distinct. The result remains evidence about its observed diff only. "
    "No repeat is scheduled automatically and no new acceptance or finish condition is added."
)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    input: str = Field(min_length=1, max_length=600)
    expected_json: str = Field(min_length=1, max_length=2048)
    check_excerpt: str | None = Field(max_length=600)
    evidence_action_id: str | None = Field(max_length=500)


class Design(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    requirement_excerpt: str = Field(min_length=1, max_length=600)
    cases: list[Case] = Field(min_length=2, max_length=2)
    justification: str = Field(min_length=1, max_length=600)
    refutation: str = Field(min_length=1, max_length=600)
    limitations: str = Field(max_length=600)


def design_schema(*, nullable):
    # Inline the one nested type for the existing provider schema validator.
    schema = Design.model_json_schema()
    schema["properties"]["cases"]["items"] = schema.pop("$defs")["Case"]
    if nullable:
        schema["type"] = ["object", "null"]
    return schema


def prepare(value, public_task):
    design = Design.model_validate(value)
    plan = case_plan.CasePlan(cases=[case_plan.ProposedCase(
        case_id=label, purpose="boundary", requirement_excerpt=design.requirement_excerpt,
        applicability=design.justification[:300], setup=case.input,
        expected="See the independently frozen expected_json.",
    ) for label, case in zip(("a", "b"), design.cases, strict=True)],
        limitations=design.limitations)
    binding = case_plan.bind(plan, public_task)
    if not all(row["excerpt_matches_issue"] for row in binding["requirement_bindings"]):
        raise ContractError("comparison requirement_excerpt must quote the public issue")
    expected = expectation.freeze(canonical_json({
        label: json.loads(expectation.freeze(case.expected_json))
        for label, case in zip(("a", "b"), design.cases, strict=True)
    }))
    return {"policy": POLICY, "design": design.model_dump(mode="json"),
            "design_hash": sha256_json(design.model_dump(mode="json")),
            "expected_json": expected, **binding}


def bind_check(prepared, *, check_id, public_task, events, diff_hash):
    check = next((c for c in public_task.visible_checks if c.id == check_id), None)
    if check is None:
        raise ContractError(f"unknown public check: {check_id}")
    command = "\n".join(check.command)
    links = []
    for case in prepared["design"]["cases"]:
        action_id = case["evidence_action_id"]
        excerpt = case["check_excerpt"]
        source = command
        if action_id is not None:
            result = next((e["payload"]["result"] for e in reversed(events)
                           if e["event_type"] == "action_finished"
                           and e["payload"]["result"]["action_id"] == action_id), None)
            if (result is None or result["tool"] != "read_file"
                    or result["status"] != "succeeded"
                    or result["workspace_diff_hash"] != diff_hash):
                raise ContractError("comparison check evidence must be a current completed read")
            source = "\n".join(s["content"] for s in result["output"].get("spans", []))
        if not excerpt or not excerpt.strip() or excerpt not in source:
            raise ContractError("comparison check_excerpt is absent from its public evidence")
        links.append({"evidence_action_id": action_id, "excerpt_found": True})
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
        def _run_probe(self, question, python_source, *, execution_identity, comparison=None):
            prepared = prepare(comparison, self.public_task) if comparison is not None else None
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
            prepared = (prepare(args["comparison"], self.public_task)
                        if args.get("comparison") is not None else None)
            links = (bind_check(prepared, check_id=check_id, public_task=self.public_task,
                                events=events, diff_hash=start["baseline_diff_hash"])
                     if prepared is not None else None)
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


def project(events, diff_hash=None):
    """One journal-derived phase; edits and segment boundaries never re-arm it."""
    seed = next(e["payload"]["seed_hash"] for e in events
                if e["event_type"] == "diagnostic_candidate_seeded")
    starts, turns, result, mutated = {}, 0, None, False
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
                result = observed
                break
    view = {"policy": POLICY, "instruction": GUIDANCE, "subject_diff_hash": seed,
            "phase": "observe", "max_phase_model_calls": MAX_TURNS,
            "phase_calls_started": min(turns, MAX_TURNS), "result": None,
            "interpretation_status": "model_authored_unverified"}
    if result is not None:
        start = starts[result["action_id"]]
        view["phase"] = "returned_to_repair"
        view["result"] = {
            "action_id": result["action_id"], "input_hash": result["input_hash"],
            "tool": result["tool"], "status": result["status"],
            "error_code": result.get("error_code"), "message": result.get("message"),
            "observed_diff_hash": result["workspace_diff_hash"],
            "currency": "current" if diff_hash in (None, result["workspace_diff_hash"])
            else "historical",
            "comparison": copy.deepcopy(result["output"].get(FIELD)),
            "public_basis": (start.get("turn_decision") or {}).get("basis"),
        }
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

    def policy(gateway, *args, **kwargs):
        result = original_policy(gateway, *args, **kwargs)
        snapshot = kwargs.get("snapshot")
        view = project(gateway.journal.events(), snapshot.diff.patch_hash if snapshot else None)
        return restrict(result, view)

    def context(**kwargs):
        nonlocal active
        state = json.loads(original_context(**kwargs))
        view = project(kwargs["journal"].events(), state["current_diff"]["patch_hash"])
        if (view["phase"] == "observe"
                and not set(state["available_tool_names"]) & {"run_check", "run_probe"}):
            view["phase"] = "unobserved_resource_boundary"
        active = view["phase"] == "observe"
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
                        "records a limitation, not a comparison; explain it in your basis.")
                    params = tool["parameters"]
                    params["properties"]["comparison"] = design_schema(
                        nullable=tool["name"] == "run_check")
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
            "max_phase_model_calls": MAX_TURNS, "rearm_after_mutation": False,
            "semantic_verdict": None}
