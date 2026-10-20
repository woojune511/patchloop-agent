"""Project-level public operations for probe-environment capability checks.

These exercise ordinary library APIs on pristine public source. They neither
reproduce task bugs nor provide repair guidance or acceptance evidence.
"""

from __future__ import annotations

from textwrap import dedent

from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

SUCCESS_MARKER = "PATCHLOOP_PUBLIC_OPERATION_OK"
OPERATIONS = {
    "marshmallow": """
        from marshmallow import Schema, fields

        class Example(Schema):
            value = fields.Integer(required=True)

        schema = Example()
        assert schema.validate({"value": 7}) == {}
        assert "value" in schema.validate({"value": "invalid"})
    """,
    "pvlib": """
        import numpy as np
        import pandas as pd
        from pvlib.solarposition import get_solarposition

        times = pd.DatetimeIndex(["2020-03-20T12:00:00Z"])
        result = get_solarposition(times, latitude=0, longitude=0)
        assert len(result) == 1
        assert np.isfinite(result["zenith"]).all()
        assert 0 <= result["zenith"].iloc[0] <= 180
    """,
    "pydicom": """
        from io import BytesIO
        from pydicom import dcmread, dcmwrite
        from pydicom.dataset import Dataset

        dataset = Dataset()
        dataset.is_little_endian = True
        dataset.is_implicit_VR = True
        dataset.PatientID = "public-canary"
        stream = BytesIO()
        dcmwrite(stream, dataset, write_like_original=True)
        assert stream.tell() > 0
        stream.seek(0)
        assert dcmread(stream, force=True).PatientID == "public-canary"
    """,
    "astroid": """
        import astroid

        module = astroid.parse("value = 1 + 2\\n")
        value = next(module.body[0].value.infer())
        assert value.value == 3
    """,
    "pyvista": """
        import numpy as np
        import pyvista as pv

        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        triangle = pv.PolyData(points, np.array([3, 0, 1, 2]))
        assert triangle.n_points == 3 and triangle.n_cells == 1
        assert abs(triangle.area - 0.5) < 1e-12
    """,
    "sqlfluff": """
        from sqlfluff.core import Linter

        parsed = Linter(dialect="ansi").parse_string("SELECT 1")
        assert parsed.tree is not None
        assert parsed.tree.raw == "SELECT 1"
        assert not parsed.violations
    """,
}


def operation_program(module: str) -> str:
    try:
        body = OPERATIONS[module]
    except KeyError as exc:
        raise ContractError("no reviewed public operation canary for this project") from exc
    return dedent(body).strip() + f'\nprint("{SUCCESS_MARKER}")\n'


def run_operation_canary(sandbox, source, module: str, *, execution_identity: dict) -> dict:
    program = operation_program(module)
    result = sandbox.run_probe(
        source,
        "Verify an ordinary public library operation in the prepared probe environment.",
        program,
        deadline=None,
        execution_identity=execution_identity,
    )
    passed = (
        result.get("status") == "passed"
        and result.get("exit_code") == 0
        and SUCCESS_MARKER in result.get("stdout", "").splitlines()
        and not any(result.get(key) for key in (
            "cleanup_failed", "deadline_exhausted", "timed_out", "truncated",
        ))
    )
    return {
        "schema": "public-operation-canary-v1",
        "module": module,
        "program": program,
        "program_hash": sha256_bytes(program.encode("utf-8")),
        "passed": passed,
        "result": result,
    }
