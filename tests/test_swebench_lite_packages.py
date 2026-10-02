import json
from pathlib import Path

import yaml

from diagnostics.swebench_lite_packages import build_package


def test_public_selection_is_independent_and_private_original_bytes_are_preserved(tmp_path):
    upstream = tmp_path / "site" / "swebench"
    for name in ("__init__.py", "types.py", "harness/constants/__init__.py",
                 "harness/grading.py", "harness/infra_failure.py",
                 "harness/log_parsers/python.py"):
        path = upstream / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# original vendor bytes\n")
    license_file = upstream.parent / "swebench-5.0.2.dist-info/licenses/LICENSE"
    license_file.parent.mkdir(parents=True)
    license_file.write_text("MIT\n")
    row = dict(instance_id="pvlib__pvlib-python-1072", repo="pvlib/pvlib-python",
               base_commit="a" * 40, problem_statement="public requirement",
               image="example/image@sha256:" + "b" * 64, version="0.7",
               FAIL_TO_PASS=["private_case"], PASS_TO_PASS=[],
               log_parser="parse_log_pvlib", eval_type="pass_and_fail",
               test_patch="private test bytes\n", patch="reference answer bytes\n",
               eval_script="pytest -rA private_case\n")
    target = tmp_path / "package"
    package = build_package(row, target, upstream, source_roots=["pvlib"],
                            public_pytest_args=["pvlib/tests/test_temperature.py"])
    public = yaml.safe_load((target / "public.yaml").read_text())
    assert "private_case" not in json.dumps(public)
    assert "reference answer" not in json.dumps(public)
    assert public["visible_checks"][0]["command"][-1] == "pvlib/tests/test_temperature.py"
    assert public["constraints"]["allowed_paths"] == ["pvlib/**"]
    oracle = json.loads((target / "hidden/oracle.json").read_text())
    assert oracle["test_patch"] == row["test_patch"]
    assert oracle["test_command"] == ["pytest", "-rA", "private_case"]
    assert (target / "reference.patch").read_bytes() == row["patch"].encode()
    assert package.public.task_id.endswith("1072")
    assert Path(package.root) == target.resolve()
