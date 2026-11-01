"""Freeze bounded public source observations before a seeded repair comparison.

Workspace content comes from registered reads; dependency content comes only from
the admitted public-wheel inventory and matching captured exception files. This
module never constructs a provider client or executes project code or checks.
"""
from __future__ import annotations

import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

from patchloop.dev.context import bounded_lines, source_lines
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.prepared_probe_dependencies import read_descriptor
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.exception_frames import public as public_frames
from patchloop.util import safe_relative_path, sha256_bytes, sha256_json

SCHEMA = "exception-frame-source-packet-v1"
MAX_SOURCES, MAX_LINES, MAX_CHARS, MAX_FILE_BYTES = 8, 400, 24_000, 2_000_000
_SELECT = frozenset({"origin", "path", "start_line", "end_line"})
_SOURCE = _SELECT | {"file_hash", "content"}
_PACKET = frozenset({"schema", "calibration_hash", "candidate_diff_hash", "public_hash", "sources"})


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _hash(value):
    return type(value) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _selection(value, *, source=False, canonical=False):
    _require(type(value) is dict and set(value) == (_SOURCE if source else _SELECT),
             "source selection fields differ from the public schema")
    _require(type(value["origin"]) is str and value["origin"] in {"workspace", "dependency"},
             "unknown source origin")
    path = value["path"]
    _require(type(path) is str and 0 < len(path) <= 512 and "\x00" not in path
             and not PureWindowsPath(path).drive, "source path must be relative")
    normalized = safe_relative_path(path)
    _require(PurePosixPath(normalized).parts and not any(
        part.casefold() in {".git", ".patchloop-hidden"} or part.casefold().startswith(".env")
        for part in PurePosixPath(normalized).parts), "source path must be public")
    _require(not canonical or normalized == path, "source packet path is not normalized")
    start, end = value["start_line"], value["end_line"]
    _require(type(start) is int and type(end) is int and 1 <= start <= end
             and end - start + 1 <= MAX_LINES, "source range must contain 1-400 lines")
    return {"origin": value["origin"], "path": normalized, "start_line": start, "end_line": end}


def _schema(packet):
    _require(type(packet) is dict and set(packet) == _PACKET and packet["schema"] == SCHEMA,
             "invalid public source packet schema")
    _require(all(_hash(packet[key]) for key in
                 ("calibration_hash", "candidate_diff_hash", "public_hash")),
             "source packet identities must be SHA-256 hashes")
    sources = packet["sources"]
    _require(type(sources) is list and 1 <= len(sources) <= MAX_SOURCES,
             "source packet must contain 1-8 source ranges")
    seen, total = set(), 0
    for row in sources:
        selection = _selection(row, source=True, canonical=True)
        identity = tuple(selection.values())
        _require(identity not in seen, "source packet repeats a range")
        seen.add(identity)
        content = row["content"]
        _require(_hash(row["file_hash"]) and type(content) is str and len(content) <= MAX_CHARS
                 and content.count("\n") + 1 == row["end_line"] - row["start_line"] + 1,
                 "source packet body does not match its declared range")
        total += len(content)
    _require(total <= MAX_CHARS, "source packet exceeds 24000 characters")


def _frame_hashes(loaded):
    hashes = {}
    output = loaded.rows["candidate"]["output"]
    for call in (output.get("exception_diagnostics") or {}).get("calls", []):
        details = public_frames(call.get("details"))
        for error in details["exceptions"]:
            for frame in error["frames"]:
                key = frame["origin"], frame["path"]
                hashes.setdefault(key, set()).add(frame["file_hash"])
    return hashes


def _frame_identity(row, hashes):
    observed = hashes.get((row["origin"], row["path"]), set())
    _require(row["origin"] != "dependency" or observed,
             "dependency source was not captured in the candidate exception frames")
    _require(not observed or observed == {row["file_hash"]},
             "source file hash differs from the candidate exception frames")


def _public_identity(loaded, packet, calibration_hash):
    _require(packet["calibration_hash"] == calibration_hash
             and packet["candidate_diff_hash"] == loaded.data["candidate_diff_hash"]
             and packet["public_hash"] == loaded.source.public_hash,
             "source packet differs from its calibration, candidate or public task")
    _require(sha256_bytes(loaded.source.public_path.read_bytes()) == loaded.source.public_hash,
             "source packet public task changed")


def _workspace_identity(workspace, expected):
    _require(WorkspaceManager.diff_summary(workspace).patch_hash == expected,
             "source packet candidate diff changed")


def _bytes(root, relative):
    path = root / relative
    try:
        for parent in (path, *path.parents):
            info = parent.lstat()
            _require(not parent.is_symlink()
                     and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "source packet refuses symlinks or reparse points")
            if parent == root:
                break
        _require(path.resolve().is_relative_to(root.resolve())
                 and stat.S_ISREG(path.stat().st_mode), "source packet requires a regular file")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        _require(len(raw) <= MAX_FILE_BYTES, "source packet file exceeds 2 MB")
        return raw
    except OSError as exc:
        raise ContractError("source packet file is unavailable") from exc


def _span(selection, raw):
    try:
        lines = source_lines(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ContractError("source packet requires UTF-8 source") from exc
    content, end, clipped = bounded_lines(lines, selection["start_line"], selection["end_line"])
    _require(not clipped and end >= selection["start_line"],
             "source packet range is empty or exceeds the character limit")
    return {**selection, "end_line": end, "file_hash": sha256_bytes(raw), "content": content}


def _dependency(loaded):
    dependency = loaded.dependencies
    _require(dependency is not None, "prepared public dependencies are required")
    descriptor, identity = read_descriptor(dependency.path)
    _require(identity == dependency.identity, "prepared dependency identity changed")
    _require((descriptor["repository_url"], descriptor["base_commit"]) == (
        loaded.public.repository.url, loaded.public.repository.base_commit),
        "prepared dependency public source identity changed")
    return dependency.path.parent / "site-packages", descriptor["files"]


def _dependency_span(selection, dependency):
    root, files = dependency
    _require(selection["path"] in files, "source is not an admitted prepared dependency")
    raw = _bytes(root, selection["path"])
    _require(sha256_bytes(raw) == files[selection["path"]], "prepared dependency source changed")
    return _span(selection, raw)


def _read_workspace(gateway, selection, diff_hash):
    arguments = {key: selection[key] for key in ("path", "start_line", "end_line")}
    identity = sha256_json({"candidate_diff_hash": diff_hash, **arguments}).split(":")[1][:24]
    result = gateway.execute(RequestedTool(
        name="read_file", action_id="source-packet-" + identity, arguments=arguments,
        turn_decision=PublicTurnDecision(mode="inspect", basis="Read the selected public source.",
                                        evidence_goal="Observe the selected source bytes.")))
    output = result.output
    _require(result.status == "succeeded" and result.error_code is None
             and result.workspace_diff_hash == diff_hash and not output.get("truncated")
             and len(output.get("spans", [])) == 1,
             "registered source read did not return one complete current span")
    span = output["spans"][0]
    _require(span["path"] == selection["path"]
             and span["start_line"] == selection["start_line"]
             and selection["start_line"] <= span["end_line"] <= selection["end_line"],
             "registered source read range changed")
    return {"origin": "workspace", **{key: span[key] for key in _SOURCE - {"origin"}}}


def build_packet(loaded, gateway, calibration_hash, selections):
    """Create exact source bytes from registered reads and prepared dependency files."""
    _require(type(selections) is list and 1 <= len(selections) <= MAX_SOURCES,
             "source packet requires 1-8 selections")
    selections = [_selection(value) for value in selections]
    packet = {"schema": SCHEMA, "calibration_hash": calibration_hash,
              "candidate_diff_hash": loaded.data["candidate_diff_hash"],
              "public_hash": loaded.source.public_hash, "sources": []}
    _public_identity(loaded, packet, calibration_hash)
    _workspace_identity(gateway.workspace, packet["candidate_diff_hash"])
    dependency = (_dependency(loaded)
                  if any(s["origin"] == "dependency" for s in selections) else None)
    frames = _frame_hashes(loaded)
    for selection in selections:
        row = (_read_workspace(gateway, selection, packet["candidate_diff_hash"])
               if selection["origin"] == "workspace" else _dependency_span(selection, dependency))
        _frame_identity(row, frames)
        packet["sources"].append(row)
    validate_packet(loaded, packet, calibration_hash, workspace=gateway.workspace)
    return packet


def validate_packet(loaded, packet, calibration_hash, workspace=None):
    """Validate frozen identities; with a workspace, verify its exact current bytes too."""
    _schema(packet)
    _public_identity(loaded, packet, calibration_hash)
    if workspace is not None:
        workspace = Path(workspace)
        _workspace_identity(workspace, packet["candidate_diff_hash"])
    dependency = (_dependency(loaded)
                  if any(row["origin"] == "dependency" for row in packet["sources"]) else None)
    frames = _frame_hashes(loaded)
    for row in packet["sources"]:
        selection = {key: row[key] for key in _SELECT}
        _frame_identity(row, frames)
        if row["origin"] == "dependency":
            actual = _dependency_span(selection, dependency)
        elif workspace is not None:
            tracked = run_git(workspace, "--literal-pathspecs", "ls-files", "--error-unmatch",
                              "--", row["path"], check=False)
            _require(tracked.returncode == 0, "source packet workspace path is not tracked")
            actual = _span(selection, _bytes(workspace, row["path"]))
        else:
            continue  # Collection supplies the fresh candidate before any provider access.
        _require(actual == row, "source packet range, file hash or content changed")


def observe_sources(gateway, packet):
    """Register fresh workspace anchors; reject any mismatch with the frozen packet."""
    _schema(packet)
    _require(gateway.current_diff_hash == packet["candidate_diff_hash"],
             "source packet candidate diff changed")
    for row in packet["sources"]:
        if row["origin"] == "workspace":
            actual = _read_workspace(gateway, {key: row[key] for key in _SELECT},
                                     packet["candidate_diff_hash"])
            _require(actual == row, "registered source observation differs from the packet")
    _require(gateway.current_diff_hash == packet["candidate_diff_hash"],
             "candidate changed during registered source observation")
