"""Provider-free A/B identity checks and interception of real initial payload construction."""
from __future__ import annotations

import configparser
import copy
import csv
import io
import json
import zipfile
from contextlib import suppress
from time import monotonic
from unittest.mock import patch

from packaging.utils import parse_wheel_filename

from diagnostics.caller_uptake import COMMON, request
from diagnostics.positive_verification_panel import require
from patchloop import prepared_probe_dependencies as deps
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.dev import runner, segments
from patchloop.dev.conversation import reconstruct_state
from patchloop.probe_callers import description
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes


def compare_dependencies(a, b):
    public = load_public_task(
        runner.repository_root() / "tasks/dev-train/current-dev20/13/public.yaml")
    for path in (a, b):
        deps.load_dependencies(path, public, deps.admit(path)).verify()
    left, right = (json.loads(path.read_bytes()) for path in (a, b))
    def wheels(value):
        return {str(parse_wheel_filename(w["url"].rsplit("/", 1)[-1])[0]): w
                for w in value["wheel_lock"]["wheels"]}
    aw, bw = wheels(left), wheels(right)
    require(set(bw) - set(aw) == {"pylint"} and set(aw) <= set(bw)
            and all(w == bw[name] for name, w in aw.items()), "common wheels changed")
    require({name + "==" + str(parse_wheel_filename(w["url"].rsplit("/", 1)[-1])[1])
             for name, w in aw.items()} == set(COMMON), "common pins changed")
    require(left["workspace_metadata"] == right["workspace_metadata"], "source metadata differs")
    for key in ("image", "platform", "python", "runtime_profile", "source_roots", "import_roots",
                "repository_url", "base_commit", "prepared_source_content_hash"):
        require(left.get(key) == right.get(key), "common identity differs: " + key)
    require(all(right["files"].get(p) == h for p, h in left["files"].items()),
            "common installed files differ")
    # Derive the exact permitted additions from the frozen wheel, before capability outcomes.
    wheel_name = bw["pylint"]["url"].rsplit("/", 1)[-1]
    wheel_path = b.parent / "wheels" / wheel_name
    require(sha256_bytes(wheel_path.read_bytes()) == bw["pylint"]["hash"], "caller wheel changed")
    with zipfile.ZipFile(wheel_path) as wheel:
        record_name = next(n for n in wheel.namelist() if n.endswith(".dist-info/RECORD"))
        folder = record_name.rsplit("/", 1)[0]
        allowed = {row[0] for row in csv.reader(io.StringIO(wheel.read(record_name).decode()))}
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(wheel.read(folder + "/entry_points.txt").decode())
        scripts = set(config["console_scripts"])
        # uv on this Windows preparation host installs Windows launchers. The probe
        # invokes the distribution's Python console entry; no launcher is substituted.
        allowed |= {"bin/" + name + ".exe" for name in scripts}
        allowed |= {folder + "/" + name for name in ("INSTALLER", "REQUESTED", "direct_url.json")}
    extra = set(right["files"]) - set(left["files"])
    require(extra == allowed, "non-caller additions or incomplete caller installation")
    require(left["wheel_lock"].get("operator_caller_requirements", []) == []
            and right["wheel_lock"]["operator_caller_requirements"] == ["pylint==2.12.2"],
            "caller arm drift")
    return {"passed": True, "common_files": len(left["files"]), "common_wheels": len(aw),
            "extra_files": sorted(extra), "allowlist": sorted(allowed),
            "descriptors": {"A": sha256_bytes(a.read_bytes()), "B": sha256_bytes(b.read_bytes())},
            "workspace_metadata_equal": True}


def capability_program(arm):
    require(arm in "AB", "unknown arm")
    return '''import importlib, importlib.metadata as md, importlib.util, json, sys
from pathlib import Path
pins = ''' + repr(list(COMMON)) + '''
rows = []
for pin in pins:
    name, version = pin.split("==")
    dist = md.distribution(name)
    origin = str(dist.locate_file(""))
    check_setup(name, dist.version + "@" + origin, version + "@/opt/patchloop-dependencies")
    rows.append({"name": name, "version": dist.version, "origin": origin})
import astroid
check_setup("current source", astroid.__file__, "/workspace/astroid/__init__.py")
check_setup("python", sys.version.split()[0], "3.9.25")
caller = importlib.util.find_spec("pylint")
check_setup("caller available", caller is not None, ''' + repr(arm == "B") + ''')
try:
    dist = md.distribution("pylint")
except md.PackageNotFoundError:
    dist = None
check_setup("caller metadata", dist is not None, ''' + repr(arm == "B") + ''')
caller_record = None
if dist is not None:
    entry = next(e for e in dist.entry_points if e.name == "pylint")
    import pylint
    check_setup("caller version", dist.version, "2.12.2")
    check_setup("caller source", pylint.__file__, "/opt/patchloop-dependencies/pylint/__init__.py")
    check_setup("entry", entry.value, "pylint:run_pylint")
    caller_record = {"version": dist.version, "origin": pylint.__file__, "entry": entry.value}
print(json.dumps({"common": rows, "source": astroid.__file__, "source_version": astroid.__version__,
                  "python": sys.version, "sys_path": sys.path, "caller": caller_record}))
'''


class Captured(BaseException):
    """Stop before any input-token count or generation admission."""


def capture_initial(dependencies, state, arm):
    captured = []
    class Capture(OpenAIResponsesAdapter):
        def __init__(self, config, *, api_key):
            self.config = config  # No SDK/client or credential contents.

        def request_payload(self, *args, **kwargs):
            captured.append(super().request_payload(*args, **kwargs))
            raise Captured

    # A fixed runner clock isolates request construction from host preparation
    # jitter. Real sandbox preflight deadlines remain bounded. This is not a solve.
    with (patch.object(runner, "OpenAIResponsesAdapter", Capture),
          patch.object(runner, "load_exact_openai_api_key", return_value="offline-unused"),
          patch.object(runner, "monotonic", return_value=monotonic()), suppress(Captured)):
        runner.run_dev(request(dependencies, state, f"{arm}-r1-t13"))
    require(len(captured) == 1, "first request was not captured")
    return captured[0]


def initial_signature(wire, *, arm):
    """Keep every state field and tool byte except the declared treatment and derived ID."""
    state = reconstruct_state(wire["input"], context_policy=segments.POLICY)
    require(not state["current_diff"]["patch"] and state["working_plan"]["plan"] is None
            and not state["working_notes"]["findings"]
            and all(c["status"] == "NOT_RUN" for c in state["visible_check_status"]),
            "not a fresh solve")
    state = copy.deepcopy(state)
    mapping = {"segment_id": state["segment_handoff"].pop("segment_id")}
    # Environment discovery is delivered by run_probe.description, not injected
    # elsewhere. Any new differences in state fail the paired equality check.
    tools = copy.deepcopy(wire["tools"])
    probe = next(t for t in tools if t["name"] == "run_probe")
    addition = description(["pylint==2.12.2"]) if arm == "B" else ""
    if addition:
        require(probe["description"].count(addition) == 1, "caller disclosure differs")
        probe["description"] = probe["description"].replace(addition, "", 1)
    mapping["caller_description"] = addition
    def normalized(value):
        if isinstance(value, str):
            return value.replace(mapping["segment_id"], "<derived-segment-id>")
        if isinstance(value, list):
            return [normalized(v) for v in value]
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        return value
    # Compare the entire wire, not only reconstructed state: an additional message
    # or field must not disappear merely because state reconstruction ignores it.
    return normalized({**wire, "tools": tools}), mapping


def compare_initial(a, b):
    sa, ma = initial_signature(a, arm="A")
    sb, mb = initial_signature(b, arm="B")
    require(sa == sb, "initial requests differ outside the declared caller treatment")
    return {"passed": True, "normalized_hash": sha256_bytes(canonical_json(sa).encode()),
            "normalization": {"A": ma, "B": mb}, "fixed_offline_runner_clock": True,
            "provider_calls": 0, "input_count_calls": 0, "credential_reads": 0}
