"""Bounded public exception locations; never inspect locals or render source lines.

This stdlib-only module is copied into the trusted probe wrapper. ``roots`` must
name the exported public snapshot and verified prepared dependency copy, not a
host checkout or arbitrary import paths. In-process feedback is not attestation.
"""

from __future__ import annotations

import builtins
import copy
import hashlib
import json
import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

POLICY = "public-exception-frames-v1"
SCOPE = "public_workspace_and_prepared_dependencies"
MAX_EXCEPTIONS = 3
MAX_FRAMES = 16
MAX_FRAMES_PER_EXCEPTION = 12
MAX_TRACEBACK_SCAN = 128
MAX_PACKET_BYTES = 6_144
MAX_FILE_BYTES = 2_000_000
MAX_PATH_CHARS = 256
MAX_FUNCTION_CHARS = 128
MAX_MESSAGE_CHARS = 256
MAX_TYPE_CHARS = 256
_GROUP = getattr(builtins, "BaseExceptionGroup", None)
_REASONS = frozenset({
    "not_exception", "chain_limit", "chain_cycle", "traceback_limit", "frame_limit",
    "frame_text_limit", "source_unavailable", "source_size_limit", "dependency_not_prepared",
    "source_hash_mismatch", "unsafe_public_path", "message_unavailable", "message_limit",
    "type_limit", "exception_group_unsupported", "packet_byte_limit", "capture_error",
    "invalid_packet", "not_available",
})


def _size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8"))


def _unavailable(reason):
    return {"policy": POLICY, "scope": SCOPE, "status": "unavailable",
            "exceptions": [], "omissions": {reason: 1}}


def _omit(packet, reason, count=1):
    packet["omissions"][reason] = packet["omissions"].get(reason, 0) + count


def _status(packet):
    if not any(row["frames"] for row in packet["exceptions"]):
        return "unavailable"
    return "partial" if packet["omissions"] else "complete"


def _message(error):
    """Do not call a model-defined exception's __str__ or an argument's repr."""
    args = BaseException.args.__get__(error)
    if (type(args) is not tuple or any(type(value) not in (str, bool, int, float, type(None))
                                     for value in args[:4])
            or any(type(value) is int and value.bit_length() > 1024 for value in args[:4])):
        return None, "omitted"
    shortened = len(args) > 4 or any(type(value) is str and len(value) > MAX_MESSAGE_CHARS
                                   for value in args[:4])
    values = [value[:MAX_MESSAGE_CHARS] if type(value) is str else value for value in args[:4]]
    message = (values[0] if len(values) == 1 and type(values[0]) is str
               else "" if not values else ", ".join(repr(value) for value in values))
    shortened |= len(message) > MAX_MESSAGE_CHARS
    return message[:MAX_MESSAGE_CHARS], (
        "truncated_safe_exception_args" if shortened else "safe_exception_args")


class ExceptionFrames:
    def __init__(self, roots, dependency_files=None):
        self.roots = {origin: Path(path).resolve() for origin, path in roots.items()
                      if origin in {"workspace", "dependency"} and path is not None}
        self.dependency_files = dict(dependency_files or {})

    def _location(self, tb):
        code = tb.tb_frame.f_code
        path = Path(code.co_filename)
        if not path.is_absolute():
            return None, None  # Includes observer/helper virtual filenames.
        origin = next((origin for origin, root in self.roots.items()
                       if path.is_relative_to(root)), None)
        if origin is None:
            return None, None
        root = self.roots[origin]
        if ".." in path.parts:
            return None, "unsafe_public_path"
        try:
            for part in (path, *path.parents):
                if part == root:
                    break
                info = part.lstat()
                if part.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    return None, "unsafe_public_path"
            if not path.resolve().is_relative_to(root) or not stat.S_ISREG(path.stat().st_mode):
                return None, "unsafe_public_path"
        except (OSError, ValueError, RuntimeError):
            return None, "source_unavailable"
        relative = path.relative_to(root).as_posix()
        if len(relative) > MAX_PATH_CHARS or len(code.co_name) > MAX_FUNCTION_CHARS:
            return None, "frame_text_limit"
        if origin == "dependency" and relative not in self.dependency_files:
            return None, "dependency_not_prepared"
        return {"origin": origin, "path": relative, "function": code.co_name,
                "line": tb.tb_lineno}, None

    def _file_hash(self, frame, cache):
        key = frame["origin"], frame["path"]
        if key not in cache:
            try:
                with (self.roots[key[0]] / key[1]).open("rb") as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    cache[key] = None, "source_size_limit"
                else:
                    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
                    cache[key] = ((None, "source_hash_mismatch") if key[0] == "dependency"
                                  and self.dependency_files[key[1]] != digest else (digest, None))
            except (OSError, ValueError):
                cache[key] = None, "source_unavailable"
        return cache[key]

    def capture(self, error):
        """Capture the escaped exception and effective cause/context chain only.

        Cause takes precedence; suppressed context is not traversed. The bounded
        innermost public frames are kept. Excluded nonpublic frames disclose only
        a count. Unsupported groups keep their own locations, never child trees.
        """
        if not isinstance(error, BaseException):
            return _unavailable("not_exception")
        packet = {"policy": POLICY, "scope": SCOPE, "status": "unavailable",
                  "exceptions": [], "omissions": {}}
        seen, hashes, total_frames = set(), {}, 0
        relation = "escaped"
        try:
            while error is not None:
                if id(error) in seen:
                    _omit(packet, "chain_cycle")
                    break
                if len(packet["exceptions"]) == MAX_EXCEPTIONS:
                    _omit(packet, "chain_limit")
                    break
                seen.add(id(error))
                kind = type(error)
                module = type.__getattribute__(kind, "__module__")
                name = type.__getattribute__(kind, "__qualname__")
                name = f"{module}.{name}" if type(module) is str else name
                message, message_source = _message(error)
                row = {"relation": relation, "type": name[:MAX_TYPE_CHARS],
                       "message": message, "message_source": message_source, "frames": [],
                       "excluded_frame_count": 0, "omitted_frame_count": 0}
                packet["exceptions"].append(row)
                if len(name) > MAX_TYPE_CHARS:
                    _omit(packet, "type_limit")
                if message_source != "safe_exception_args":
                    _omit(packet, "message_unavailable" if message is None else "message_limit")
                if _GROUP is not None and isinstance(error, _GROUP):
                    _omit(packet, "exception_group_unsupported",
                          len(_GROUP.exceptions.__get__(error)))
                tb = BaseException.__traceback__.__get__(error)
                locations = []
                for _ in range(MAX_TRACEBACK_SCAN):
                    if tb is None:
                        break
                    location, reason = self._location(tb)
                    if location is not None:
                        locations.append(location)
                    elif reason:
                        row["omitted_frame_count"] += 1
                        _omit(packet, reason)
                    else:
                        row["excluded_frame_count"] += 1
                    tb = tb.tb_next
                if tb is not None:
                    _omit(packet, "traceback_limit")
                allowance = min(MAX_FRAMES_PER_EXCEPTION, MAX_FRAMES - total_frames)
                omitted = max(0, len(locations) - allowance)
                if omitted:
                    row["omitted_frame_count"] += omitted
                    _omit(packet, "frame_limit", omitted)
                for location in locations[-allowance:] if allowance else []:
                    digest, reason = self._file_hash(location, hashes)
                    if reason:
                        row["omitted_frame_count"] += 1
                        _omit(packet, reason)
                    else:
                        row["frames"].append({**location, "file_hash": digest})
                total_frames += len(row["frames"])
                cause = BaseException.__cause__.__get__(error)
                context = BaseException.__context__.__get__(error)
                suppressed = BaseException.__suppress_context__.__get__(error)
                error, relation = ((cause, "cause") if cause is not None else
                                   (context, "context") if not suppressed else (None, "context"))
        except Exception:
            # Optional location collection cannot replace the already captured error.
            _omit(packet, "capture_error")
        # Only diagnostic data is reduced. The caller owns core exception/capture
        # and serializes it independently, even when this packet is unavailable.
        while _size(packet) > MAX_PACKET_BYTES:
            row = next((row for row in packet["exceptions"] if row["message"] is not None), None)
            if row is not None:
                row["message"], row["message_source"] = None, "omitted"
            else:
                row = max(packet["exceptions"], key=lambda item: len(item["frames"]), default=None)
                if row is None or not row["frames"]:
                    return _unavailable("packet_byte_limit")
                row["frames"].pop(0)
                row["omitted_frame_count"] += 1
            _omit(packet, "packet_byte_limit")
        packet["status"] = _status(packet)
        return public(packet)


def public(details):
    """Return an independent bounded allowlisted packet, never arbitrary report data."""
    if details is None:
        return _unavailable("not_available")
    try:
        if (type(details) is not dict or set(details) != {
                "policy", "scope", "status", "exceptions", "omissions"}
                or details["policy"] != POLICY or details["scope"] != SCOPE
                or type(details["exceptions"]) is not list
                or len(details["exceptions"]) > MAX_EXCEPTIONS
                or type(details["omissions"]) is not dict
                or not set(details["omissions"]) <= _REASONS
                or any(type(n) is not int or not 1 <= n <= 2**31 - 1
                       for n in details["omissions"].values())):
            raise ValueError
        frames = 0
        for index, row in enumerate(details["exceptions"]):
            if (type(row) is not dict or set(row) != {
                    "relation", "type", "message", "message_source", "frames",
                    "excluded_frame_count", "omitted_frame_count"}
                    or row["relation"] not in ({"escaped"} if index == 0 else {"cause", "context"})
                    or type(row["type"]) is not str or not 1 <= len(row["type"]) <= MAX_TYPE_CHARS
                    or row["message_source"] not in {"safe_exception_args",
                        "truncated_safe_exception_args", "omitted"}
                    or (row["message_source"] == "omitted") != (row["message"] is None)
                    or row["message"] is not None and (
                        type(row["message"]) is not str or len(row["message"]) > MAX_MESSAGE_CHARS)
                    or any(type(row[k]) is not int or not 0 <= row[k] <= 2**31 - 1
                           for k in ("excluded_frame_count", "omitted_frame_count"))
                    or type(row["frames"]) is not list
                    or len(row["frames"]) > MAX_FRAMES_PER_EXCEPTION):
                raise ValueError
            frames += len(row["frames"])
            for frame in row["frames"]:
                if (type(frame) is not dict or set(frame) != {
                        "origin", "path", "function", "line", "file_hash"}
                        or frame["origin"] not in {"workspace", "dependency"}
                        or type(frame["path"]) is not str
                        or not 1 <= len(frame["path"]) <= MAX_PATH_CHARS
                        or "\\" in frame["path"] or "\x00" in frame["path"]
                        or PurePosixPath(frame["path"]).is_absolute()
                        or PureWindowsPath(frame["path"]).drive
                        or not PurePosixPath(frame["path"]).parts
                        or PurePosixPath(frame["path"]).as_posix() != frame["path"]
                        or ".." in PurePosixPath(frame["path"]).parts
                        or type(frame["function"]) is not str
                        or not 1 <= len(frame["function"]) <= MAX_FUNCTION_CHARS
                        or type(frame["line"]) is not int or not 1 <= frame["line"] <= 2**31 - 1
                        or type(frame["file_hash"]) is not str
                        or re.fullmatch(r"sha256:[0-9a-f]{64}", frame["file_hash"]) is None):
                    raise ValueError
        if (frames > MAX_FRAMES or details["status"] != _status(details)
                or _size(details) > MAX_PACKET_BYTES):
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError):
        return _unavailable("invalid_packet")
    return copy.deepcopy(details)
