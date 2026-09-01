"""Domain-specific errors with stable machine-readable codes."""


class PatchLoopError(Exception):
    code = "PATCHLOOP_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class ContractError(PatchLoopError):
    code = "CONTRACT_ERROR"


class HarnessAdmissionError(ContractError):
    """The harness rejected a run before the coding agent was admitted."""

    code = "HARNESS_ADMISSION_FAILURE"


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


class CorrectionAttemptLimitError(ContractError):
    code = "CORRECTION_ATTEMPT_LIMIT"


class ReviewCorrectionLimitError(ContractError):
    code = "REVIEW_CORRECTION_LIMIT"


class ModelActionContractRepeatedError(ContractError):
    code = "MODEL_ACTION_CONTRACT_REPEATED"


class ModelGenerationIncompleteRepeatedError(ContractError):
    """The dedicated reasoning-only generation retry was already consumed."""

    code = "MODEL_GENERATION_INCOMPLETE_REPEATED"


class PreMutationEvidenceExhaustedError(ContractError):
    code = "PRE_MUTATION_EVIDENCE_EXHAUSTED"


class WorkPlanAdmissionRejectedError(ContractError):
    """One recoverable public work-plan request failed admission."""

    code = "WORK_PLAN_ADMISSION_REJECTED"


class WorkPlanAdmissionRepeatedError(ContractError):
    """A work-plan gate consumed its single bounded recovery slot."""

    code = "WORK_PLAN_ADMISSION_REPEATED"


class RequiredWorkflowEvidenceUnavailableError(ContractError):
    """A required public workflow trigger could not be reconstructed safely."""

    code = "REQUIRED_WORKFLOW_EVIDENCE_UNAVAILABLE"


class SemanticProgressEvidenceUnavailableError(ContractError):
    """The current public failure signature could not be reconstructed safely."""

    code = "SEMANTIC_PROGRESS_EVIDENCE_UNAVAILABLE"


class SemanticNoProgressEvidenceExhaustedError(ContractError):
    """The bounded reset lane exhausted its required search/read evidence."""

    code = "SEMANTIC_NO_PROGRESS_EVIDENCE_EXHAUSTED"


class SemanticNoProgressRevisionInvalidError(ContractError):
    """A repeated public failure was revised without rejecting the prior hypothesis."""

    code = "SEMANTIC_NO_PROGRESS_REVISION_INVALID"


class SelfDirectedExplorationExhaustedError(ContractError):
    """The bounded public exploration ended without a safe plan."""

    code = "SELF_DIRECTED_EXPLORATION_EXHAUSTED"


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
