"""Explicit public caller pins; the workspace project stays source supplied."""

from __future__ import annotations

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from patchloop.errors import ContractError


def requirements(values: list[str], *, project_name: str) -> list[str]:
    """Keep operator caller inputs separate from repository dependency declarations."""
    if not isinstance(values, list) or len(values) > 8:
        raise ContractError("public caller selection requires at most eight exact package pins")
    selected = {}
    for text in values:
        if not isinstance(text, str) or len(text) > 256 or any(c in text for c in "\r\n\x00"):
            raise ContractError("public caller requirements must be bounded single-line pins")
        try:
            requirement = Requirement(text)
            pins = list(requirement.specifier)
            if (requirement.url or requirement.marker or requirement.extras or len(pins) != 1
                    or pins[0].operator != "==" or "*" in pins[0].version):
                raise ValueError("exact unqualified version required")
            name = canonicalize_name(requirement.name)
            version = str(Version(pins[0].version))
            if name == canonicalize_name(project_name) or name in selected:
                raise ValueError("duplicate or workspace caller")
        except (InvalidRequirement, InvalidVersion, ValueError) as exc:
            raise ContractError(
                "caller must be a unique public package==version, not a URL/extra/marker/self dep",
            ) from exc
        selected[name] = version
    return [f"{name}=={version}" for name, version in sorted(selected.items())]


def verify_selection(callers: list[str], wheels: list) -> None:
    selected = {name: version for name, version, _, _ in
                (parse_wheel_filename(w.url.rsplit("/", 1)[-1]) for w in wheels)}
    for text in callers:
        name, version = text.split("==")
        if selected.get(name) != Version(version):
            raise ContractError("resolved wheels omit or change an explicitly pinned public caller")


def from_descriptor(descriptor: dict) -> tuple[str, ...]:
    lock = descriptor.get("wheel_lock", {})
    if "operator_caller_requirements" not in lock:
        return ()
    return tuple(requirements(lock["operator_caller_requirements"],
                              project_name=lock["source_metadata"]["project_name"]))


def description(callers: tuple[str, ...] | list[str]) -> str:
    if not callers:
        return ""
    return (
        "Prepared public callers: " + ", ".join(callers) + ". "
        "Use importlib.metadata to inspect installed versions/entry points and inspect.getsource "
        "or bounded reads of their files under /opt/patchloop-dependencies to obtain caller code. "
        "Reconstruct public input files/configuration in /tmp; inspect the caller's actual "
        "arguments, cwd, sys.path and environment before invoking its in-process entry point. "
        "Check observed setup values with check_setup and compare the reported failure with "
        "a normal control through that same caller. A reduced helper call covers only its own "
        "entry point and setup. Caller requirements on the workspace distribution are supplied "
        "by current source, not a resolved release; version compatibility remains unverified. "
    )
