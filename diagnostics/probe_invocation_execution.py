"""Serial authorized collection, sealed public audit and separate local acceptance."""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import probe_invocation_control as role
from diagnostics import probe_invocation_grading as grading
from diagnostics import probe_invocation_panel as panel
from diagnostics import verification_state_execution as common
from diagnostics.positive_verification_panel import require

_SEAL = common.seal


def initializer(arm):
    return role.initialize_worker_a if arm == "A" else role.initialize_worker_b


@contextmanager
def configured():
    with (
        patch.object(common, "panel", panel),
        patch.object(common, "grading", grading),
        patch.object(common, "worker_initializer", initializer),
        patch.object(common, "COLLECTION", "run_dev_probeinvocationcollection53"),
        patch.object(common, "AUDIT", "run_dev_probeinvocationaudit53"),
        patch.object(common, "ASSESSMENT", "run_dev_probeinvocationassessment53"),
        patch.object(common, "seal", seal),
    ):
        yield


def collect(root, digest, authorization, rates):
    with configured():
        return common.collect(root, digest, authorization, rates)


def export(root, digest):
    with configured():
        return common.export(root, digest)


def seal(root, digest, annotations):
    packet = panel.validate(root, digest)
    rows = json.loads(annotations.read_bytes())["rows"]
    require(len(rows) == len(packet["rows"]), "all invocation assignments required")
    for reviewed, assigned in zip(rows, packet["rows"], strict=True):
        require(
            reviewed["public_id"] == assigned["public_id"]
            and reviewed["invocation"]["arm"] == assigned["arm"],
            "invocation audit assignment differs from packet",
        )
    with configured():
        return _SEAL(root, digest, annotations)


def assess(root, digest):
    with configured():
        return common.assess(root, digest)


if __name__ == "__main__":
    with configured():
        common.main()
