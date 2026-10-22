"""Diagnostic OFF/ON treatment; both arms retain the same-context verification role."""

from __future__ import annotations

import copy
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from diagnostics import verification_role as role
from diagnostics.positive_verification_panel import require
from patchloop.dev import probe_invocation, reproduction, runner
from patchloop.util import sha256_json

BASE = "50b91b511d5a3d64d1365bacfa3203eda3a85aad"
DESCRIPTION = (
    "Choose purpose for each new probe: {kind: helper} explores a helper or uncertain path; "
    "kind=original_requirement verifies a public requirement and must include its literal "
    "requirement_quote, fully qualified Python entrypoint, input_conditions, "
    "environment_conditions and expected_json in that same object. No separate declaration "
    "step is needed. For original_requirement call record_observation(value) exactly once "
    "with the actual JSON-compatible observation (at most 2048 UTF-8 bytes). Print progress "
    "normally: stdout/stderr are logs, never the comparison value. Report an observed bug "
    "as a value, not an assertion against expected behavior; the host compares it. Setup "
    "failures, crashes and incomplete observations remain unverified. "
    "The harness observes the declared Python call and compares the recorded value with the "
    "frozen expectation; neither proves that your chosen call represents the public requirement. "
    + reproduction.REPLAY_DESCRIPTION
    + " Changing them creates a different experiment, "
    "not resolution "
    "of the old one. reproduction_review separates helpers, unobserved calls, changed setup "
    "and same-reproduction comparisons. No extra probe or submission gate is imposed."
)
_SELECTION, _REVIEW = reproduction.selection, reproduction.review
_WORKER_SCOPE = None


def previous_view(review):
    value = copy.deepcopy(review)
    for item in value["items"]:
        item.pop("replay_action_id", None)
        for name in ("baseline", "latest"):
            if item[name] is not None:
                item[name].pop("execution_link", None)
    return value


def selection(arguments):
    raw, channel = _SELECTION(arguments)
    return raw, reproduction.OBSERVATION_CHANNEL if channel == probe_invocation.CHANNEL else channel


def review(*args, **kwargs):
    return previous_view(_REVIEW(*args, **kwargs))


def contract():
    return {
        "comparison": "probe-invocation-v1",
        "off_base": BASE,
        "role_mode": {"A": "A", "B": "A"},
        "role": role.contract(),
        "channels": {"A": reproduction.OBSERVATION_CHANNEL, "B": probe_invocation.CHANNEL},
        "description_hashes": {
            "A": sha256_json(DESCRIPTION),
            "B": sha256_json(reproduction.DESCRIPTION),
        },
        "automatic_baseline": False,
        "references": 2,
    }


@contextmanager
def assigned(arm):
    require(arm in {"A", "B"}, "unknown invocation arm")
    identity = contract()
    with role.assigned("A"), ExitStack() as stack:
        base_hash = runner._model_hash
        stack.enter_context(
            patch.object(
                runner,
                "_model_hash",
                lambda request, pricing: sha256_json(
                    {"base": base_hash(request, pricing), "invocation": identity, "arm": arm}
                ),
            )
        )
        if arm == "A":
            stack.enter_context(patch.object(reproduction, "DESCRIPTION", DESCRIPTION))
            stack.enter_context(patch.object(reproduction, "selection", selection))
            stack.enter_context(patch.object(reproduction, "review", review))
        yield


def initialize_worker_a(stop, admission):
    _initialize(stop, admission, "A")


def initialize_worker_b(stop, admission):
    _initialize(stop, admission, "B")


def _initialize(stop, admission, arm):
    from diagnostics.parallel_dev_batch import initialize_worker

    initialize_worker(stop, admission)
    global _WORKER_SCOPE
    _WORKER_SCOPE = assigned(arm)
    _WORKER_SCOPE.__enter__()
