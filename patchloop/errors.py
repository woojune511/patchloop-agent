"""Domain-specific errors with stable machine-readable codes."""


class PatchLoopError(Exception):
    code = "PATCHLOOP_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class ContractError(PatchLoopError):
    code = "CONTRACT_ERROR"


class EvaluatorControlContractCollision(ContractError):
    """Evaluator-private control bytes collided with a private marker."""

    code = "EVALUATOR_CONTROL_CONTRACT_COLLISION"


class UntrustedPrivateMarkerHit(ContractError):
    """Agent-visible evidence contained an evaluator-private marker."""

    code = "UNTRUSTED_PRIVATE_MARKER_HIT"


class CoverageCitationError(ContractError):
    """A public coverage target cited evidence outside its bound authority."""

    code = "COVERAGE_CITATION_REJECTED"


class SubmissionProtocolError(ContractError):
    code = "SUBMISSION_PROTOCOL_ERROR"


class ModelGenerationBudgetError(ContractError):
    code = "MODEL_GENERATION_BUDGET_EXCEEDED"


class PolicyViolation(PatchLoopError):
    code = "POLICY_VIOLATION"


class ControlledDiagnosticRejection(ContractError):
    code = "CONTROLLED_DIAGNOSTIC_REJECTION"


class ActionConflict(ContractError):
    code = "ACTION_CONFLICT"


class RecoveryError(PatchLoopError):
    code = "RECOVERY_ERROR"


class RunOwnershipConflict(RecoveryError):
    code = "RUN_OWNERSHIP_CONFLICT"


class InjectedFault(PatchLoopError):
    code = "INJECTED_FAULT"
