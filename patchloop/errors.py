"""Stable machine-readable errors for the active development lane."""


class PatchLoopError(Exception):
    code = "PATCHLOOP_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class ContractError(PatchLoopError):
    code = "CONTRACT_ERROR"


class ActionConflict(ContractError):
    code = "ACTION_CONFLICT"


class RecoveryError(PatchLoopError):
    code = "RECOVERY_ERROR"


class ResumeContractMismatch(ContractError):
    code = "RESUME_CONTRACT_MISMATCH"
