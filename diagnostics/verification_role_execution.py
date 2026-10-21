"""Serial authorized collection, sealed public audit and separate local acceptance."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import verification_role as role
from diagnostics import verification_role_grading as grading
from diagnostics import verification_role_panel as panel
from diagnostics import verification_state_execution as common


def initializer(arm):
    return role.initialize_worker_a if arm == "A" else role.initialize_worker_b


@contextmanager
def configured():
    with (patch.object(common, "panel", panel), patch.object(common, "grading", grading),
          patch.object(common, "worker_initializer", initializer),
          patch.object(common, "COLLECTION", "run_dev_verificationrolecollection49"),
          patch.object(common, "AUDIT", "run_dev_verificationroleaudit49"),
          patch.object(common, "ASSESSMENT", "run_dev_verificationroleassessment49")):
        yield


def collect(root, digest, authorization, rates):
    with configured():
        return common.collect(root, digest, authorization, rates)


def export(root, digest):
    with configured():
        return common.export(root, digest)


def seal(root, digest, annotations):
    with configured():
        return common.seal(root, digest, annotations)


def assess(root, digest):
    with configured():
        return common.assess(root, digest)


if __name__ == "__main__":
    with configured():
        common.main()
