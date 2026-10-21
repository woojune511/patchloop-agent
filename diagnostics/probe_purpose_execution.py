"""Purpose comparison using the existing serial ledger and sealed assessment flow."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import probe_purpose_control as control
from diagnostics import probe_purpose_grading as grading
from diagnostics import probe_purpose_panel as panel
from diagnostics import verification_state_execution as common


@contextmanager
def configured():
    with (patch.object(common, "panel", panel), patch.object(common, "off", control),
          patch.object(common, "grading", grading),
          patch.object(common, "COLLECTION", "run_dev_probepurposecollection46"),
          patch.object(common, "AUDIT", "run_dev_probepurposeaudit46"),
          patch.object(common, "ASSESSMENT", "run_dev_probepurposeassessment46")):
        yield


if __name__ == "__main__":
    with configured():
        common.main()
