"""Domain-specific errors with stable machine-readable codes."""


class PatchLoopError(Exception):
    code = "PATCHLOOP_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class ContractError(PatchLoopError):
    code = "CONTRACT_ERROR"


class PolicyViolation(PatchLoopError):
    code = "POLICY_VIOLATION"


class ActionConflict(PatchLoopError):
    code = "ACTION_CONFLICT"


class RecoveryError(PatchLoopError):
    code = "RECOVERY_ERROR"


class InjectedFault(PatchLoopError):
    code = "INJECTED_FAULT"
