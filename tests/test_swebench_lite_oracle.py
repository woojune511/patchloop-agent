import json
import subprocess
import sys

from diagnostics import swebench_lite_oracle


def test_missing_private_runtime_is_infrastructure_error_not_wrong_patch():
    # The template's diagnostic directory deliberately has no vendor/oracle bundle.
    result = subprocess.run(
        [sys.executable, swebench_lite_oracle.__file__],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "ERROR"
