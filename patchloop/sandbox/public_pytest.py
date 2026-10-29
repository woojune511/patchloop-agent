"""Shared registered pytest copy launcher and its bounded reporting adapter."""

from patchloop.errors import ContractError

PUBLIC_RUNNER = """import os, shutil, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="lite-public-") as temporary:
    checkout = Path(temporary) / "repo"
    shutil.copytree(Path.cwd(), checkout,
                   ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(checkout / "src"), str(checkout)])
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    env["HOME"] = temporary
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
                            cwd=checkout, env=env)
    raise SystemExit(result.returncode)
"""


def projected_public_runner(*, test_path, target_name, target_ast_sha256, old, new):
    """Project one registered expectation while retaining admitted test additions.

    The shared test-addition policy protects the module's original tests, imports
    and fixtures. This adapter separately pins the function whose expectation it
    projects, and edits only that function in the temporary checkout.
    """
    projection = dict(test_path=test_path, target_name=target_name,
                      target_ast_sha256=target_ast_sha256, old=old, new=new)
    adapter = """    import ast, hashlib, json
    projection = PROJECTION
    def fail_projection(reason):
        print('public regression ' + reason + ': ' + projection['test_path'], flush=True)
        raise SystemExit(2)
    def canonical_ast(node):
        if isinstance(node, ast.AST):
            return [type(node).__name__, {key: canonical_ast(value)
                    for key, value in ast.iter_fields(node) if value is not None and value != []}]
        if isinstance(node, list):
            return [canonical_ast(value) for value in node]
        return node
    public_test = checkout / projection['test_path']
    test_text = public_test.read_text(encoding='utf-8')
    try:
        module = ast.parse(test_text)
    except SyntaxError:
        fail_projection('input syntax drift')
    def target_definitions(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return [node] if node.name == projection['target_name'] else []
        return [found for child in ast.iter_child_nodes(node)
                for found in target_definitions(child)]
    targets = target_definitions(module)
    if (len(targets) != 1 or not isinstance(targets[0], ast.FunctionDef)
            or targets[0] not in module.body):
        fail_projection('target mismatch')
    target = targets[0]
    # Literal parameter additions are validated by the shared admission policy.
    target.decorator_list = []
    target_bytes = json.dumps(canonical_ast(target), sort_keys=True,
                             separators=(',', ':')).encode('utf-8')
    if hashlib.sha256(target_bytes).hexdigest() != projection['target_ast_sha256']:
        fail_projection('target drift')
    lines = test_text.splitlines(keepends=True)
    target_text = ''.join(lines[target.lineno - 1:target.end_lineno])
    if target_text.count(projection['old']) != 1:
        fail_projection('anchor mismatch')
    lines[target.lineno - 1:target.end_lineno] = [
        target_text.replace(projection['old'], projection['new'], 1)]
    public_test.write_text(''.join(lines), encoding='utf-8')
    print('public regression projection: isolate issue-conflicting expectation in '
          + projection['test_path'], flush=True)
""".replace("PROJECTION", repr(projection), 1)
    return PUBLIC_RUNNER.replace("    env = dict(os.environ)\n",
                                 adapter + "    env = dict(os.environ)\n", 1)


PVLIB_REINDL_PUBLIC_RUNNER = projected_public_runner(
    test_path="pvlib/tests/test_irradiance.py",
    target_name="test_reindl",
    target_ast_sha256="c0f2626dfe1dde3244bf735e585f8fb88d6209ad6100fc4a5dceaa830f0c7f16",
    old="    assert_allclose(result, [np.nan, 27.9412, 104.1317, 34.1663], atol=1e-4)",
    new="""    # GHI == 0 is the requested behavior change, not a base regression.
    unchanged = irrad_data['ghi'].to_numpy() != 0
    assert_allclose(np.asarray(result)[unchanged],
                    np.array([np.nan, 27.9412, 104.1317, 34.1663])[unchanged],
                    atol=1e-4)""",
)


def reporting_copy_command(command, script, marker, working_directory):
    """Instrument only the exact registered wrapper; preserve its copy/env/exit behavior."""
    index = next((i for i, arg in enumerate(command[:-1]) if arg == "-c"), None)
    if index is None or command[index + 1] != PUBLIC_RUNNER:
        raise ContractError("test comparison requires direct Python pytest or the registered "
                            "public copy wrapper")
    reporter = ("import sys\n" + script + "\nmain(['-q', *sys.argv[1:]], None, "
                + repr(working_directory) + ", " + repr(marker) + ")")
    original = '[sys.executable, "-m", "pytest", "-q", *sys.argv[1:]]'
    replacement = '[sys.executable, "-c", ' + repr(reporter) + ', *sys.argv[1:]]'
    instrumented = PUBLIC_RUNNER.replace(original, replacement, 1)
    return [*command[:index + 1], instrumented, *command[index + 2:]]
