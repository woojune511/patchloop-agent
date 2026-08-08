"""D-101 human review packet and externally anchored admission artifacts.

This module is intentionally isolated from the shared CLI/contracts files that
the D-100 source gate hashes.  It can render the exact five-group review packet
and implement a future candidate -> receipt -> seal flow, but it never invents
group decisions or writes a production journal on import/build/validation.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from patchloop.contracts import (
    D099ArtifactDescriptor,
    D099ProposedRule,
    D099ReviewProposal,
    D100DecisionJournalDescriptor,
    D100EntryPreview,
    D100EntryPreviewBody,
    D100GroupDecisionRecord,
    D100PreviewAuthority,
    D100ProjectedEntry,
    D100ProposalBinding,
    D100SourceGate,
    StrictModel,
)
from patchloop.errors import ContractError
from patchloop.memory.d099_review import DEFAULT_PROPOSAL_PATH
from patchloop.memory.d100_group_admission import (
    DEFAULT_SOURCE_GATE_PATH as DEFAULT_D100_SOURCE_GATE_PATH,
)
from patchloop.memory.d100_group_admission import (
    _journal_descriptor,
    _load_exact_proposal,
    _memory_template,
    _read_journal,
    _rule_hash,
    _validate_external_anchor,
    _validate_record_sequence,
    validate_d100_source_gate,
)
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes, sha256_text

PACKET_SCHEMA_VERSION = "memory-group-review-packet-d101-v1"
CANDIDATE_SCHEMA_VERSION = "memory-group-admission-candidate-d101-v1"
RECEIPT_SCHEMA_VERSION = "memory-group-human-approval-receipt-d101-v1"
SEAL_SCHEMA_VERSION = "memory-group-admission-seal-d101-v1"
SOURCE_GATE_SCHEMA_VERSION = "memory-group-admission-source-gate-d101-v1"
PACKET_RECORDED_AT = "2026-08-06T01:00:00Z"
SOURCE_GATE_RECORDED_AT = "2026-08-06T01:05:00Z"

DEFAULT_PACKET_JSON_PATH = Path(
    "reports/memory-development/d101-five-group-review-packet.json"
)
DEFAULT_PACKET_MARKDOWN_PATH = Path(
    "reports/memory-development/d101-five-group-review-packet.md"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d101-group-admission-source-gate.json"
)
SOURCE_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d101_group_admission.py"),
    Path("scripts/d101_group_admission.py"),
    Path("tests/test_d101_group_admission.py"),
)

# This copy is deliberately reviewer-facing rather than a literal translation
# of the machine contract. System identifiers and hashes are rendered only in
# an appendix; the main document uses ordinary Korean and preserves the same
# public-evidence meaning as the D-099 proposal.
KOREAN_REVIEW_COPY: dict[str, dict[str, Any]] = {
    "platform-emulation-matrix-gap": {
        "title": "운영체제와 경로 종류에 따른 동작을 충분히 확인하지 않음",
        "state": "기억 규칙 초안이 있어 채택 여부를 결정할 수 있음",
        "source_label": "pyfakefs 실행 2회",
        "observations": [
            (
                "첫 번째 실행은 마지막 폴더가 만들어지는 결과는 맞췄지만, 중간 폴더와 "
                "마지막 폴더, 경로 종류, 생성 방식, 운영체제 설정에 따른 차이를 모두 "
                "확인하지 못했습니다."
            ),
            (
                "두 번째 실행은 폴더를 따라가는 처리 범위를 좁혔지만, 문자열 경로와 "
                "바이트 경로가 운영체제별 처리와 함께 올바르게 동작하는지 충분히 "
                "확인하지 못했습니다."
            ),
        ],
        "why_grouped": (
            "두 실행 모두 폴더 생성 기능을 고치면서 최종 결과만 확인하고, 중간 단계와 "
            "경로·운영체제 조합 중 일부를 놓친 같은 종류의 문제입니다."
        ),
        "memory_problem": (
            "운영체제 동작을 흉내 내는 코드를 고칠 때 최종 결과만 확인하면, 중간 단계나 "
            "경로 종류별 차이를 놓칠 수 있습니다."
        ),
        "use_when": [
            "중간 폴더와 마지막 폴더의 동작이 밖에서 확인될 수 있는 작업",
            "문제 설명이 둘 이상의 경로 종류, 운영체제 설정 또는 오류 상황을 구분하는 작업",
        ],
        "check": [
            "중간 단계와 마지막 단계를 따로 적어 확인합니다.",
            (
                "운영체제 설정, 문자열·바이트 경로, 생성 방식, 기존 경로 상태와 오류 "
                "상황의 조합을 표로 만들어 빠진 경우가 없는지 봅니다."
            ),
        ],
        "actions": [
            "문제 설명이 구분한 모든 경우를 유지하는 가장 작은 수정을 합니다.",
            "기존 검사를 다시 실행하고, 표에서 빠진 경우를 별도로 확인합니다.",
        ],
        "do_not_use_when": [
            "중간 단계가 밖에서 전혀 보이지 않는 기능",
            "모든 운영체제와 경로 종류가 의도적으로 완전히 같은 동작을 하는 기능",
        ],
    },
    "request-context-propagation-gap": {
        "title": "요청마다 달라지는 설정값을 일부 호출 경로에만 전달함",
        "state": "기억 규칙 초안이 있어 채택 여부를 결정할 수 있음",
        "source_label": "Hugging Face Hub 실행 2회",
        "observations": [
            (
                "첫 번째 실행은 다운로드 주소 설정을 한 경로에만 추가했습니다. 다른 "
                "호출자와 상대 주소, 기본 주소, 외부에서 온 주소가 같은 설정을 유지하는지 "
                "확인하지 못했습니다."
            ),
            (
                "두 번째 실행은 더 많은 호출 경로에 설정을 전달했지만, 값을 만드는 모든 "
                "호출자와 주소의 소유권이 달라지는 경우까지 확인하지 못했습니다."
            ),
        ],
        "why_grouped": (
            "두 실행 모두 요청별 다운로드 주소를 처리했지만, 그 값이 처음부터 마지막까지 "
            "거치는 모든 경로를 완전히 따라가지 못했습니다."
        ),
        "memory_problem": (
            "요청마다 달라지는 설정값을 맨 아래 함수에만 추가하면, 그 함수를 부르는 다른 "
            "경로는 여전히 기본값을 사용할 수 있습니다."
        ),
        "use_when": [
            "동작이 프로그램 전체의 한 가지 기본값이 아니라 요청자가 고른 값에 따라 달라질 때",
            "같은 값을 만들거나 바꾸는 진입 경로가 여러 개일 때",
        ],
        "check": [
            "값을 처음 정하는 호출자부터 실제로 사용하는 함수까지 모든 연결을 적어 봅니다.",
            (
                "상대 주소, 기본 주소, 외부 소유 주소, 직접 지정한 주소와 값이 생략된 "
                "경우를 나누어 확인합니다."
            ),
        ],
        "actions": [
            "필요한 모든 연결을 통해 요청별 설정을 명시적으로 전달합니다.",
            "설정을 생략하는 호출자와 주소 종류별 경로를 각각 확인합니다.",
        ],
        "do_not_use_when": [
            "설정값이 의도적으로 프로그램 전체에서 하나만 쓰이도록 정해진 경우",
            "값을 만드는 경로가 하나뿐이고 호출자별로 달라질 수 없는 경우",
        ],
    },
    "interrupt-lifecycle-unresolved": {
        "title": "작업 중단과 정리가 정확히 한 번 이뤄지는지 판단할 근거가 부족함",
        "state": "근거가 부족해 아직 기억 규칙을 만들지 않음",
        "source_label": "AnyIO 실행 1회",
        "observations": [
            (
                "한 실행에서 작업 취소 처리와 실행 주체를 바꿨지만, 중단 신호가 제대로 "
                "전달되는지, 중단된 작업이 다시 시작되지 않는지, 정리가 정확히 한 번만 "
                "실행되는지까지 확인하기에는 자료가 부족했습니다."
            )
        ],
        "why_grouped": (
            "검토할 수 있는 완료 실행이 한 번뿐이어서, 다른 실행에서도 반복되는 일반적인 "
            "문제인지 비교할 수 없습니다."
        ),
        "why_not_ready": (
            "코드에서 취소 신호가 소비되거나 정리 책임이 어긋날 위험은 보이지만, 한 번의 "
            "실행만으로 모든 중단·재개·정리 상황에 적용할 규칙을 만들기에는 이릅니다."
        ),
        "more_to_review": [
            (
                "작업을 소유한 쪽, 실제 작업자, 결과를 기다리는 쪽과 테스트 "
                "준비·정리 단계를 나누어 봅니다."
            ),
            "중단 신호 전달, 중단 뒤 재시작 금지와 정리 횟수에 대한 다른 실행 근거를 더 모읍니다.",
        ],
    },
    "diagnostic-contract-unresolved": {
        "title": "오류를 설명하려다 또 다른 형식 오류를 만들 수 있음",
        "state": "문제는 보이지만 적용 범위가 불명확해 기억 규칙을 만들지 않음",
        "source_label": "Loguru 실행 2회",
        "observations": [
            (
                "첫 번째 실행은 잘못된 형식을 설명하는 메시지 자체가 다시 형식 문자열로 "
                "해석될 수 있었습니다. 일반 문자열, 실행 중 만들어지는 문자열, 색상 표시, "
                "오류 잡기 설정 등 다른 사용 방식까지는 확인하지 못했습니다."
            ),
            (
                "두 번째 실행도 같은 경계에서 설명용 기호가 또 다른 오류를 일으켜, "
                "도움이 되는 안내 대신 두 번째 실패를 만들 위험을 반복했습니다."
            ),
        ],
        "why_grouped": (
            "두 실행 모두 원래 형식 오류를 설명하려고 만든 메시지가 다시 형식 처리되어 "
            "두 번째 오류를 만들 수 있다는 같은 문제를 보였습니다."
        ),
        "why_not_ready": (
            "반복된 코드 문제는 분명하지만, 일반 문자열·동적 문자열·색상 표시·오류 잡기 "
            "설정·사용자 기록 변경 등 모든 사용 방식에 공통으로 적용할 규칙의 범위는 "
            "아직 확인되지 않았습니다."
        ),
        "more_to_review": [
            "원래 형식 오류와 그 오류를 설명하는 메시지를 만드는 과정을 따로 봅니다.",
            "공개된 모든 문자열 처리 방식과 오류 잡기 설정을 확인한 뒤 규칙을 다시 제안합니다.",
        ],
    },
    "exception-origin-state-conflation": {
        "title": "값이 없는 경우와 값 변환에 실패한 경우를 같은 것으로 처리함",
        "state": "기억 규칙 초안이 있어 채택 여부를 결정할 수 있음",
        "source_label": "tox 실행 2회",
        "observations": [
            (
                "두 실행은 같은 수정 내용을 제출했습니다. 값을 찾지 못한 경우와, 찾은 값을 "
                "바꾸는 과정에서 빈 값이 된 경우를 하나의 예외 처리 안에서 같은 상태로 "
                "취급했습니다."
            ),
            (
                "그 결과 원래 값이 없는 상황과 값은 있었지만 변환 결과가 빈 상황을 "
                "구분하지 못할 수 있었습니다."
            ),
        ],
        "why_grouped": (
            "두 실행의 수정 내용이 완전히 같고, 모두 값 찾기 실패와 변환 뒤 상태를 같은 "
            "예외 처리에 넣은 문제입니다."
        ),
        "memory_problem": (
            "값을 찾는 단계의 실패와 그 값을 바꾸는 단계의 실패를 한 예외 처리로 묶으면, "
            "서로 다른 의미의 상태를 같은 것으로 처리할 수 있습니다."
        ),
        "use_when": [
            "문제 설명이 '값 없음'과 '값은 있지만 비어 있음'을 다르게 취급할 때",
            "값 찾기와 값 변환이 서로 다른 이유로 같은 종류의 예외를 낼 수 있을 때",
        ],
        "check": [
            "값 찾기, 걸러내기, 치환, 기본값 적용과 호출자 대체 동작을 단계별로 따라갑니다.",
            "값 없음, 기존 빈 값, 일치, 기본값 사용, 호출자별 값과 대체 동작을 각각 확인합니다.",
        ],
        "actions": [
            "예외 처리를 실제로 '값 없음'을 뜻하는 연산에만 좁혀 적용합니다.",
            "뒤 단계에서도 빈 값과 기본값이 서로 다른 상태로 유지되게 합니다.",
        ],
        "do_not_use_when": [
            "공개된 동작이 값 찾기 실패와 변환 실패를 의도적으로 같게 정의한 경우",
            "두 연산이 구분되는 상태를 만들 수 없는 경우",
        ],
    },
}

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_ACTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_LEAK_PATTERNS = (
    re.compile(r"(?i)diff --git\s"),
    re.compile(r"@@(?:\s|$)"),
    re.compile(r"(?i)(?:\+\+\+|---)\s+[ab]/"),
    re.compile(r"```"),
    re.compile(r"(?i)\breference\.patch\b"),
    re.compile(r"(?i)\bprivate\.ya?ml\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)(?:^|[/\\])hidden(?:[/\\]|_tests?(?:[/\\]|\.))"),
    re.compile(r"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{12,}\b"),
    re.compile(r"(?i)\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bC:\\Users\\"),
)


class D101GroupAdmissionError(ContractError):
    """Stable fail-closed error for D-101 packet/admission handling."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D101GroupAdmissionError(message)


def _safe_text(value: str, *, field: str, maximum: int = 2_000) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    _require(0 < len(normalized) <= maximum, f"D-101 {field} is invalid")
    if any(pattern.search(normalized) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError(f"D-101 {field} leak scan failed")
    return normalized


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise D101GroupAdmissionError("D-101 timestamp is invalid") from exc
    _require(parsed.tzinfo is not None, "D-101 timestamp must be timezone-aware")
    return parsed


class D101D100GateBinding(StrictModel):
    path: str
    schema_version: Literal["memory-group-review-projector-source-gate-d100-v1"]
    gate_id: str = Field(pattern=r"^d100_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="d100_source_gate.path")


class D101DocumentBinding(StrictModel):
    path: str
    schema_version: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="document.path")


class D101ReviewSource(StrictModel):
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    failure_record_id: str = Field(min_length=1)
    repetition: int = Field(ge=1)
    causal_confidence: float = Field(ge=0, le=1)
    public_assessment: str = Field(min_length=1)


class D101ReviewGroup(StrictModel):
    order: int = Field(ge=1, le=5)
    semantic_group_id: str = Field(min_length=1)
    semantic_group_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    disposition: Literal["candidate", "hold"]
    relation: Literal["single", "semantic-cluster", "exact-duplicate"]
    merge_rationale: str = Field(min_length=1)
    dedup_confidence: float = Field(ge=0, le=1)
    sources: list[D101ReviewSource] = Field(min_length=1)
    evidence_ref_count: int = Field(ge=1)
    proposed_rule: D099ProposedRule | None = None
    proposed_rule_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    unresolved_reason: str | None = Field(default=None, min_length=1)
    next_review_actions: list[str]
    allowed_decisions: list[Literal["approve", "reject", "continue_hold"]]
    decision_status: Literal["not_made"]
    no_preselected_or_recommended_decision: Literal[True]
    exact_hidden_cause_established: Literal[False]
    memory_benefit_established: Literal[False]

    @model_validator(mode="after")
    def validate_review_shape(self) -> D101ReviewGroup:
        if self.disposition == "candidate":
            if (
                self.proposed_rule is None
                or self.proposed_rule_hash is None
                or self.unresolved_reason is not None
                or self.next_review_actions
                or self.allowed_decisions != ["approve", "reject", "continue_hold"]
            ):
                raise ValueError("D-101 candidate review group shape is invalid")
        elif (
            self.proposed_rule is not None
            or self.proposed_rule_hash is not None
            or self.unresolved_reason is None
            or not self.next_review_actions
            or self.allowed_decisions != ["reject", "continue_hold"]
        ):
            raise ValueError("D-101 hold review group shape is invalid")
        return self


class D101PacketAuthority(StrictModel):
    review_packet_only: Literal[True]
    production_human_decision_records: Literal[0]
    admission_candidate_created: Literal[False]
    approval_receipt_present: Literal[False]
    admission_seal_created: Literal[False]
    admitted_memory_rule_count: Literal[0]
    memory_admission_unlocked: Literal[False]
    memory_index_source_authoring_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]


class D101ReviewPacketBody(StrictModel):
    milestone: Literal["D-101"]
    evidence_kind: Literal["human-readable-five-group-review-packet"]
    recorded_at: str = Field(min_length=1)
    proposal: D100ProposalBinding
    d100_source_gate: D101D100GateBinding
    groups: list[D101ReviewGroup] = Field(min_length=5, max_length=5)
    warnings: list[str] = Field(min_length=4)
    leak_scan_passed: Literal[True]
    authority: D101PacketAuthority
    next_gate: Literal["explicit-five-group-decisions-in-d100-journal"]

    @model_validator(mode="after")
    def validate_group_algebra(self) -> D101ReviewPacketBody:
        if [group.order for group in self.groups] != [1, 2, 3, 4, 5]:
            raise ValueError("D-101 review group order must be exact")
        group_ids = [group.semantic_group_id for group in self.groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("D-101 review group IDs must be unique")
        if sum(group.disposition == "candidate" for group in self.groups) != 3:
            raise ValueError("D-101 candidate group count drifted")
        if sum(group.disposition == "hold" for group in self.groups) != 2:
            raise ValueError("D-101 hold group count drifted")
        return self


class D101ReviewPacket(StrictModel):
    schema_version: Literal["memory-group-review-packet-d101-v1"]
    packet_id: str = Field(pattern=r"^d101packet_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D101ReviewPacketBody


class D101EffectiveDecision(StrictModel):
    semantic_group_id: str = Field(min_length=1)
    semantic_group_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    group_disposition: Literal["candidate", "hold"]
    decision: Literal["approve", "reject", "continue_hold"]
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision_sequence: int = Field(ge=1)
    event_kind: Literal["DecisionRecorded", "DecisionCorrected"]
    reviewer_kind: Literal["human", "maintainer_assisted"]
    reviewer: str = Field(min_length=1)
    rationale_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposed_rule_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )


class D101CandidateAuthority(StrictModel):
    candidate_only: Literal[True]
    decision_coverage_complete: Literal[True]
    synthetic_decisions_present: Literal[False]
    journal_external_anchor_validated: Literal[True]
    explicit_candidate_approval_pending: Literal[True]
    approval_receipt_present: Literal[False]
    admission_seal_created: Literal[False]
    admitted_memory_rule_count: Literal[0]
    memory_admission_unlocked: Literal[False]
    memory_index_source_authoring_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]


class D101AdmissionCandidateBody(StrictModel):
    milestone: Literal["D-101"]
    evidence_kind: Literal["exact-five-group-admission-candidate"]
    prepared_at: str = Field(min_length=1)
    proposal: D100ProposalBinding
    d100_source_gate: D101D100GateBinding
    review_packet: D101DocumentBinding
    review_markdown: D099ArtifactDescriptor
    journal_logical_path: str
    journal: D100DecisionJournalDescriptor
    journal_records: list[D100GroupDecisionRecord] = Field(min_length=5)
    effective_decisions: list[D101EffectiveDecision] = Field(min_length=5, max_length=5)
    decision_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preview: D100EntryPreview
    approved_group_count: int = Field(ge=0, le=3)
    rejected_group_count: int = Field(ge=0, le=5)
    continued_hold_group_count: int = Field(ge=0, le=5)
    authority: D101CandidateAuthority

    @field_validator("journal_logical_path")
    @classmethod
    def validate_journal_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="journal_logical_path")

    @model_validator(mode="after")
    def validate_candidate_counts(self) -> D101AdmissionCandidateBody:
        if (
            self.approved_group_count
            + self.rejected_group_count
            + self.continued_hold_group_count
            != 5
        ):
            raise ValueError("D-101 candidate decision counts must cover five groups")
        if self.approved_group_count != len(self.preview.semantic_body.entries):
            raise ValueError("D-101 approved group and preview entry counts differ")
        return self


class D101AdmissionCandidate(StrictModel):
    schema_version: Literal["memory-group-admission-candidate-d101-v1"]
    candidate_id: str = Field(pattern=r"^d101candidate_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D101AdmissionCandidateBody


class D101ApprovalReceiptBody(StrictModel):
    milestone: Literal["D-101"]
    evidence_kind: Literal["self-attested-exact-candidate-approval"]
    recorded_at: str = Field(min_length=1)
    candidate: D101DocumentBinding
    approved_candidate_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    journal: D100DecisionJournalDescriptor
    decision_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    effective_decisions: list[D101EffectiveDecision] = Field(min_length=5, max_length=5)
    approval_action_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    approver_kind: Literal["human", "maintainer_assisted"]
    approver_label: str = Field(min_length=1, max_length=200)
    approval_reference: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1, max_length=2_000)
    approval_statement_code: Literal["EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE"]
    approval_statement: str = Field(min_length=1)
    explicit_approval_receipt_recorded: Literal[True]
    reviewer_identity_authenticated: Literal[False]
    cryptographic_signature_verified: Literal[False]


class D101ApprovalReceipt(StrictModel):
    schema_version: Literal["memory-group-human-approval-receipt-d101-v1"]
    receipt_id: str = Field(pattern=r"^d101receipt_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D101ApprovalReceiptBody


class D101SealAuthority(StrictModel):
    admission_snapshot_sealed: Literal[True]
    decision_coverage_complete: Literal[True]
    explicit_approval_receipt_validated: Literal[True]
    reviewer_identity_authenticated: Literal[False]
    cryptographic_signature_verified: Literal[False]
    open_hold_group_count: int = Field(ge=0, le=5)
    group_review_finalized: bool
    admitted_memory_rule_count: int = Field(ge=0, le=3)
    memory_admission_unlocked: bool
    memory_index_source_authoring_unlocked: bool
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]

    @model_validator(mode="after")
    def validate_authority(self) -> D101SealAuthority:
        unlocked = self.admitted_memory_rule_count > 0
        if self.memory_admission_unlocked != unlocked:
            raise ValueError("D-101 memory admission authority is inconsistent")
        if self.memory_index_source_authoring_unlocked != unlocked:
            raise ValueError("D-101 index source authoring authority is inconsistent")
        if self.group_review_finalized != (self.open_hold_group_count == 0):
            raise ValueError("D-101 group finalization state is inconsistent")
        return self


class D101AdmissionSealBody(StrictModel):
    milestone: Literal["D-101"]
    evidence_kind: Literal["portable-group-memory-admission-seal"]
    sealed_at: str = Field(min_length=1)
    candidate: D101DocumentBinding
    approval_receipt: D101DocumentBinding
    proposal: D100ProposalBinding
    d100_source_gate: D101D100GateBinding
    review_packet: D101DocumentBinding
    review_markdown: D099ArtifactDescriptor
    journal_logical_path: str
    journal: D100DecisionJournalDescriptor
    effective_decisions: list[D101EffectiveDecision] = Field(min_length=5, max_length=5)
    decision_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    admitted_entries: list[D100ProjectedEntry]
    leak_scan_passed: Literal[True]
    authority: D101SealAuthority
    next_gate: Literal["group-aware-memory-source-materialization-and-render-policy"]

    @field_validator("journal_logical_path")
    @classmethod
    def validate_journal_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="journal_logical_path")


class D101AdmissionSeal(StrictModel):
    schema_version: Literal["memory-group-admission-seal-d101-v1"]
    seal_id: str = Field(pattern=r"^d101seal_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D101AdmissionSealBody


class D101SourceAuthority(StrictModel):
    mechanism_source_gate_only: Literal[True]
    review_packet_generated: Literal[True]
    production_human_decision_records: Literal[0]
    admission_candidate_created: Literal[False]
    approval_receipt_present: Literal[False]
    admission_seal_created: Literal[False]
    admitted_memory_rule_count: Literal[0]
    memory_admission_unlocked: Literal[False]
    memory_index_source_authoring_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    historical_d099_or_d100_artifacts_modified: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]


class D101SourceGateBody(StrictModel):
    milestone: Literal["D-101"]
    evidence_kind: Literal["review-packet-and-admission-mechanism-source-gate"]
    recorded_at: str = Field(min_length=1)
    proposal: D100ProposalBinding
    d100_source_gate: D101D100GateBinding
    review_packet: D101DocumentBinding
    review_markdown: D099ArtifactDescriptor
    implementation_files: list[D099ArtifactDescriptor] = Field(min_length=3)
    packet_json_markdown_exact_binding: Literal[True]
    candidate_receipt_seal_flow_implemented: Literal[True]
    journal_head_count_file_sha_required: Literal[True]
    synthetic_journal_or_receipt_rejected: Literal[True]
    reviewer_identity_self_attested_not_authenticated: Literal[True]
    legacy_memory_builder_connected: Literal[False]
    authority: D101SourceAuthority
    next_gate: Literal["explicit-five-group-decisions-and-exact-candidate-approval"]


class D101SourceGate(StrictModel):
    schema_version: Literal["memory-group-admission-source-gate-d101-v1"]
    gate_id: str = Field(pattern=r"^d101_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D101SourceGateBody


def _repo_root(repository: str | Path | None) -> Path:
    return (Path(repository) if repository is not None else repository_root()).resolve()


def _resolved_path(path: str | Path, *, repository: Path) -> Path:
    selected = Path(path)
    if not selected.is_absolute():
        selected = repository / selected
    return selected.resolve()


def _logical_path(path: str | Path, *, repository: Path, field: str) -> str:
    selected = Path(path)
    if selected.is_absolute():
        try:
            value = selected.resolve().relative_to(repository).as_posix()
        except ValueError as exc:
            raise D101GroupAdmissionError(
                f"D-101 {field} must be within the repository or supplied as a logical path"
            ) from exc
    else:
        value = selected.as_posix()
    return safe_relative_path(value, field_name=field)


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        content = path.read_bytes()
        confirmed = path.read_bytes()
    except OSError as exc:
        raise D101GroupAdmissionError(f"D-101 {label} is unavailable") from exc
    _require(content == confirmed, f"D-101 {label} changed while being read")
    return content


def _body_identity(
    body: StrictModel,
    *,
    prefix: str,
) -> tuple[str, str]:
    body_hash = sha256_text(canonical_json(body.model_dump(mode="json")))
    return body_hash, f"{prefix}_{body_hash.removeprefix('sha256:')}"


def encode_d101_document(payload: StrictModel | dict[str, Any]) -> bytes:
    """Encode every D-101 JSON document in its one accepted representation."""

    data = payload.model_dump(mode="json") if isinstance(payload, StrictModel) else payload
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _artifact_descriptor(
    content: bytes,
    *,
    logical_path: str | Path,
    repository: Path,
) -> D099ArtifactDescriptor:
    return D099ArtifactDescriptor(
        path=_logical_path(logical_path, repository=repository, field="artifact.path"),
        bytes=len(content),
        sha256=sha256_bytes(content),
    )


def _document_binding(
    *,
    logical_path: str | Path,
    repository: Path,
    schema_version: str,
    document_id: str,
    semantic_body_hash: str,
    content: bytes,
) -> D101DocumentBinding:
    return D101DocumentBinding(
        path=_logical_path(logical_path, repository=repository, field="document.path"),
        schema_version=schema_version,
        document_id=document_id,
        semantic_body_hash=semantic_body_hash,
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )


def _source_descriptor(path: Path, *, repository: Path) -> D099ArtifactDescriptor:
    content = _read_stable(repository / path, label="implementation source")
    return _artifact_descriptor(content, logical_path=path, repository=repository)


def _load_exact_d100_gate(
    source_gate_path: str | Path,
    *,
    repository: Path,
) -> tuple[D100SourceGate, D101D100GateBinding, bytes]:
    selected = _resolved_path(source_gate_path, repository=repository)
    content = _read_stable(selected, label="D-100 source gate")
    try:
        gate = D100SourceGate.model_validate_json(content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 D-100 source gate is invalid") from exc
    try:
        validate_d100_source_gate(selected, repository=repository)
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 D-100 source gate validation failed") from exc
    _require(
        _read_stable(selected, label="D-100 source gate") == content,
        "D-101 D-100 source gate changed during validation",
    )
    binding = D101D100GateBinding(
        path=_logical_path(
            source_gate_path,
            repository=repository,
            field="d100_source_gate.path",
        ),
        schema_version=gate.schema_version,
        gate_id=gate.gate_id,
        semantic_body_hash=gate.semantic_body_hash,
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )
    return gate, binding, content


def _validate_d100_bindings(
    *,
    proposal: D099ReviewProposal,
    proposal_binding: dict[str, Any],
    gate: D100SourceGate,
) -> None:
    _require(
        gate.semantic_body.proposal.model_dump(mode="json") == proposal_binding,
        "D-101 D-100 proposal binding drifted",
    )
    expected_groups = [
        {
            "semantic_group_id": group.semantic_group_id,
            "semantic_group_fingerprint": group.semantic_fingerprint,
            "disposition": group.disposition,
            "proposed_rule_hash": _rule_hash(group),
        }
        for group in proposal.semantic_body.groups
    ]
    actual_groups = [
        group.model_dump(mode="json") for group in gate.semantic_body.group_bindings
    ]
    _require(actual_groups == expected_groups, "D-101 D-100 group bindings drifted")


def _packet_groups(proposal: D099ReviewProposal) -> list[D101ReviewGroup]:
    source_by_run = {source.run_id: source for source in proposal.semantic_body.sources}
    groups: list[D101ReviewGroup] = []
    for order, group in enumerate(proposal.semantic_body.groups, start=1):
        sources: list[D101ReviewSource] = []
        for member in group.members:
            source = source_by_run.get(member.run_id)
            _require(source is not None, "D-101 group member has no source record")
            assert source is not None
            _require(
                source.failure_record_id == member.failure_record_id
                and source.semantic_group_id == group.semantic_group_id,
                "D-101 group member source binding drifted",
            )
            sources.append(
                D101ReviewSource(
                    task_id=source.task_id,
                    run_id=source.run_id,
                    failure_record_id=source.failure_record_id,
                    repetition=source.repetition,
                    causal_confidence=source.causal_confidence,
                    public_assessment=source.assessment,
                )
            )
        groups.append(
            D101ReviewGroup(
                order=order,
                semantic_group_id=group.semantic_group_id,
                semantic_group_fingerprint=group.semantic_fingerprint,
                disposition=group.disposition,
                relation=group.relation,
                merge_rationale=group.merge_rationale,
                dedup_confidence=group.dedup_confidence,
                sources=sources,
                evidence_ref_count=len(group.evidence_ref_ids),
                proposed_rule=group.proposed_rule,
                proposed_rule_hash=_rule_hash(group),
                unresolved_reason=group.unresolved_reason,
                next_review_actions=group.next_review_actions,
                allowed_decisions=(
                    ["approve", "reject", "continue_hold"]
                    if group.disposition == "candidate"
                    else ["reject", "continue_hold"]
                ),
                decision_status="not_made",
                no_preselected_or_recommended_decision=True,
                exact_hidden_cause_established=False,
                memory_benefit_established=False,
            )
        )
    return groups


def build_d101_review_packet(
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
) -> dict[str, Any]:
    """Build the deterministic five-group review packet without decisions."""

    repo = _repo_root(repository)
    try:
        proposal, proposal_binding = _load_exact_proposal(
            proposal_path,
            repository=repo,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 exact proposal validation failed") from exc
    gate, gate_binding, _ = _load_exact_d100_gate(
        d100_source_gate_path,
        repository=repo,
    )
    _validate_d100_bindings(
        proposal=proposal,
        proposal_binding=proposal_binding,
        gate=gate,
    )
    body = D101ReviewPacketBody(
        milestone="D-101",
        evidence_kind="human-readable-five-group-review-packet",
        recorded_at=PACKET_RECORDED_AT,
        proposal=proposal_binding,
        d100_source_gate=gate_binding,
        groups=_packet_groups(proposal),
        warnings=[
            (
                "Public evidence supports a review hypothesis only; it does not "
                "establish the exact hidden acceptance cause."
            ),
            (
                "This packet does not establish an agent architecture defect or a "
                "harness defect."
            ),
            (
                "This packet does not establish that memory will improve performance "
                "or avoid negative transfer."
            ),
            (
                "No decision is preselected or recommended. Packet generation, "
                "validation, or a generic implementation request to proceed is not "
                "approval."
            ),
            (
                "Candidate approval admits only the exact normalized proposed rule "
                "bound by its rule hash; hold groups cannot be approved."
            ),
            (
                "Reviewer labels and approval receipts are self-attested; identity "
                "authentication and cryptographic signature verification are absent."
            ),
            (
                "Do not edit this checked-in packet to record choices; provide all "
                "decisions separately so its exact byte identity remains valid."
            ),
        ],
        leak_scan_passed=True,
        authority=D101PacketAuthority(
            review_packet_only=True,
            production_human_decision_records=0,
            admission_candidate_created=False,
            approval_receipt_present=False,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            memory_admission_unlocked=False,
            memory_index_source_authoring_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
        next_gate="explicit-five-group-decisions-in-d100-journal",
    )
    body_payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(body_payload)) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 review packet leak scan failed")
    body_hash, packet_id = _body_identity(body, prefix="d101packet")
    packet = D101ReviewPacket(
        schema_version=PACKET_SCHEMA_VERSION,
        packet_id=packet_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return packet.model_dump(mode="json")


def _korean_markdown_list(lines: list[str], heading: str, values: list[str]) -> None:
    lines.extend([f"### {heading}", ""])
    lines.extend(f"- {value}" for value in values)
    lines.append("")


def render_d101_review_markdown(
    packet: D101ReviewPacket | dict[str, Any],
) -> bytes:
    """Render a deterministic plain-Korean document for the human reviewer."""

    parsed = (
        packet
        if isinstance(packet, D101ReviewPacket)
        else D101ReviewPacket.model_validate(packet)
    )
    group_ids = [group.semantic_group_id for group in parsed.semantic_body.groups]
    _require(
        group_ids == list(KOREAN_REVIEW_COPY),
        "D-101 Korean review copy does not cover the exact group order",
    )
    for group in parsed.semantic_body.groups:
        copy = KOREAN_REVIEW_COPY[group.semantic_group_id]
        _require(
            len(copy["observations"]) == len(group.sources),
            "D-101 Korean review copy source coverage drifted",
        )
        has_draft = "memory_problem" in copy
        _require(
            has_draft == (group.proposed_rule is not None),
            "D-101 Korean review copy decision boundary drifted",
        )

    lines = [
        "# 실패 경험에서 만든 조언 5가지 검토",
        "",
        (
            "이 문서는 코딩 에이전트가 실패했던 실행 9개를 살펴보고, 다음에 비슷한 문제를 "
            "풀 때 참고할 조언을 기억에 추가할지 결정하기 위한 문서입니다."
        ),
        "",
        (
            "여기서 기억에 추가한다는 것은 과거 정답이나 숨은 테스트 내용을 저장한다는 "
            "뜻이 아닙니다. 여러 실패에서 얻은 일반적인 작업 원칙을 저장해, 이후 비슷한 "
            "문제에서 참고하게 한다는 뜻입니다."
        ),
        "",
        "## 먼저 알아둘 점",
        "",
        (
            "- 아래 설명은 에이전트가 작업할 때 볼 수 있었던 문제 설명, 코드, 공개된 검사, "
            "작업 기록과 제출한 변경만 바탕으로 정리했습니다."
        ),
        "- 숨은 테스트가 정확히 왜 실패했는지는 확정하지 않았습니다.",
        "- 에이전트 구조나 평가 시스템 자체에 문제가 있었다고 결론 내리지 않았습니다.",
        "- 이 조언을 기억하면 실제 성능이 좋아지는지도 아직 확인하지 않았습니다.",
        "- 다른 종류의 문제에서 이 조언이 오히려 방해가 될 가능성도 아직 확인하지 않았습니다.",
        "- 지금까지 어떤 항목도 선택하거나 기억에 추가하지 않았습니다.",
        (
            "- 이 파일을 직접 고치지 말고, 맨 아래 답변 양식에 맞춰 채팅으로 선택과 "
            "이유를 알려 주세요."
        ),
        "",
        "## 선택지 뜻",
        "",
        "- **기억에 추가**: 적혀 있는 조언을 그대로 다음 단계의 저장 대상으로 삼습니다.",
        "- **사용하지 않음**: 이번 제안을 끝내고 아무 조언도 저장하지 않습니다.",
        "- **나중에 결정**: 지금은 저장하지 않고, 자료를 더 모은 뒤 다시 검토합니다.",
        "",
        (
            "3번과 4번은 아직 일반적인 조언을 만들 근거가 부족하므로 **기억에 추가**를 "
            "고를 수 없습니다."
        ),
        (
            "조언을 채택하더라도 바로 비교 실험을 시작하지 않습니다. 저장 형식과 내용에 "
            "숨은 테스트 정보가 섞이지 않았는지 다음 단계에서 따로 확인합니다."
        ),
        "",
        "## 한눈에 보기",
        "",
        "| 번호 | 검토할 문제 | 관련 실행 | 현재 상태 | 가능한 선택 |",
        "|---:|---|---|---|---|",
    ]
    for group in parsed.semantic_body.groups:
        copy = KOREAN_REVIEW_COPY[group.semantic_group_id]
        choices = (
            "기억에 추가 / 사용하지 않음 / 나중에 결정"
            if group.proposed_rule is not None
            else "사용하지 않음 / 나중에 결정"
        )
        state = "지금 결정 가능" if group.proposed_rule is not None else "추가 자료 필요"
        lines.append(
            f"| {group.order} | {copy['title']} | {copy['source_label']} | "
            f"{state} | {choices} |"
        )
    lines.append("")

    for group in parsed.semantic_body.groups:
        copy = KOREAN_REVIEW_COPY[group.semantic_group_id]
        observations: list[str] = copy["observations"]
        lines.extend(
            [
                f"## {group.order}. {copy['title']}",
                "",
                f"관련 작업: {copy['source_label']}",
                "",
                "### 무슨 일이 있었나",
                "",
            ]
        )
        lines.extend(
            f"- {index}번째 관찰: {observation}"
            for index, observation in enumerate(observations, start=1)
        )
        lines.extend(
            [
                "",
                "### 왜 같은 문제로 보았나",
                "",
                str(copy["why_grouped"]),
                "",
            ]
        )
        if group.proposed_rule is not None:
            lines.extend(
                [
                    "### 앞으로 기억할 핵심",
                    "",
                    f"> {copy['memory_problem']}",
                    "",
                ]
            )
            _korean_markdown_list(
                lines,
                "이 조언을 참고할 때",
                copy["use_when"],
            )
            _korean_markdown_list(
                lines,
                "수정하기 전에 확인할 것",
                copy["check"],
            )
            _korean_markdown_list(
                lines,
                "같은 실수를 피하려면",
                copy["actions"],
            )
            _korean_markdown_list(
                lines,
                "이 조언을 사용하지 말아야 할 때",
                copy["do_not_use_when"],
            )
            choices = ["기억에 추가", "사용하지 않음", "나중에 결정"]
        else:
            lines.extend(
                [
                    "### 왜 아직 조언으로 만들지 않나",
                    "",
                    str(copy["why_not_ready"]),
                    "",
                ]
            )
            _korean_markdown_list(
                lines,
                "다음에 더 확인할 것",
                copy["more_to_review"],
            )
            choices = ["사용하지 않음", "나중에 결정"]
        lines.extend(["### 내가 고를 수 있는 선택", ""])
        lines.extend(f"- **{choice}**" for choice in choices)
        lines.extend(["", "선택 이유: ", ""])

    lines.extend(
        [
            "## 답변 양식",
            "",
            "내부 이름이나 긴 식별값을 복사할 필요가 없습니다. 아래 번호만 사용하면 됩니다.",
            "",
            "- **1번 선택:** 기억에 추가 / 사용하지 않음 / 나중에 결정",
            "  - 이유: ",
            "- **2번 선택:** 기억에 추가 / 사용하지 않음 / 나중에 결정",
            "  - 이유: ",
            "- **3번 선택:** 사용하지 않음 / 나중에 결정",
            "  - 이유: ",
            "- **4번 선택:** 사용하지 않음 / 나중에 결정",
            "  - 이유: ",
            "- **5번 선택:** 기억에 추가 / 사용하지 않음 / 나중에 결정",
            "  - 이유: ",
            "",
            (
                "'진행해줘'처럼 일반적인 요청만으로는 어떤 선택도 기록하지 않습니다. "
                "다섯 항목의 선택과 이유를 각각 알려 주어야 다음 단계로 넘어갑니다."
            ),
        ]
    )
    content = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    text = content.decode("utf-8")
    if any(pattern.search(text) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 review Markdown leak scan failed")
    return content


def render_d101_review_packet_markdown(
    packet: D101ReviewPacket | dict[str, Any],
) -> bytes:
    """Compatibility name that makes the rendered document's role explicit."""

    return render_d101_review_markdown(packet)


def _load_exact_review_packet(
    packet_json_path: str | Path,
    packet_markdown_path: str | Path,
    *,
    repository: Path,
    proposal_path: str | Path,
    d100_source_gate_path: str | Path,
) -> tuple[D101ReviewPacket, bytes, bytes]:
    json_path = _resolved_path(packet_json_path, repository=repository)
    markdown_path = _resolved_path(packet_markdown_path, repository=repository)
    json_content = _read_stable(json_path, label="review packet JSON")
    markdown_content = _read_stable(markdown_path, label="review packet Markdown")
    try:
        packet = D101ReviewPacket.model_validate_json(json_content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 review packet schema is invalid") from exc
    body_hash, packet_id = _body_identity(packet.semantic_body, prefix="d101packet")
    _require(
        packet.semantic_body_hash == body_hash,
        "D-101 review packet body hash drifted",
    )
    _require(packet.packet_id == packet_id, "D-101 review packet identity drifted")
    _parse_time(packet.semantic_body.recorded_at)
    expected = build_d101_review_packet(
        repository=repository,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    _require(
        json_content == encode_d101_document(expected),
        "D-101 review packet does not match the exact evidence",
    )
    _require(
        markdown_content == render_d101_review_markdown(packet),
        "D-101 review Markdown does not match the exact packet",
    )
    _require(
        _read_stable(json_path, label="review packet JSON") == json_content
        and _read_stable(markdown_path, label="review packet Markdown")
        == markdown_content,
        "D-101 review packet changed during validation",
    )
    return packet, json_content, markdown_content


def validate_d101_review_packet(
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
) -> dict[str, Any]:
    """Validate both deterministic packet representations against D-099/D-100."""

    repo = _repo_root(repository)
    packet, json_content, markdown_content = _load_exact_review_packet(
        packet_json_path,
        packet_markdown_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    return {
        "ok": True,
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_id": packet.packet_id,
        "semantic_body_hash": packet.semantic_body_hash,
        "packet_json_bytes": len(json_content),
        "packet_json_file_sha256": sha256_bytes(json_content),
        "packet_markdown_bytes": len(markdown_content),
        "packet_markdown_file_sha256": sha256_bytes(markdown_content),
        "semantic_group_count": len(packet.semantic_body.groups),
        "candidate_group_count": sum(
            group.disposition == "candidate" for group in packet.semantic_body.groups
        ),
        "hold_group_count": sum(
            group.disposition == "hold" for group in packet.semantic_body.groups
        ),
        "production_human_decision_records": 0,
        "memory_admission_unlocked": False,
        "memory_index_build_authorized": False,
        "core_campaign_unlocked": False,
        "packet_validation": "pass",
    }


def _canonical_journal(records: list[D100GroupDecisionRecord]) -> bytes:
    return (
        "".join(canonical_json(record.model_dump(mode="json")) + "\n" for record in records)
    ).encode("utf-8")


def _complete_nonsynthetic_effective_decisions(
    *,
    proposal: D099ReviewProposal,
    records: list[D100GroupDecisionRecord],
    effective: dict[str, D100GroupDecisionRecord],
) -> list[D101EffectiveDecision]:
    group_ids = [group.semantic_group_id for group in proposal.semantic_body.groups]
    _require(
        set(effective) == set(group_ids),
        "D-101 candidate requires an effective decision for every semantic group",
    )
    _require(
        all(record.reviewer_kind != "synthetic" for record in records),
        "D-101 production candidate rejects synthetic decision records",
    )
    decisions: list[D101EffectiveDecision] = []
    for group in proposal.semantic_body.groups:
        record = effective[group.semantic_group_id]
        reviewer_kind = record.reviewer_kind
        _require(
            reviewer_kind in {"human", "maintainer_assisted"},
            "D-101 production candidate reviewer kind is invalid",
        )
        decisions.append(
            D101EffectiveDecision(
                semantic_group_id=group.semantic_group_id,
                semantic_group_fingerprint=group.semantic_fingerprint,
                group_disposition=group.disposition,
                decision=record.decision,
                decision_hash=record.decision_hash,
                decision_sequence=record.sequence,
                event_kind=record.event_kind,
                reviewer_kind=reviewer_kind,
                reviewer=record.reviewer,
                rationale_sha256=sha256_text(record.rationale),
                proposed_rule_hash=record.proposed_rule_hash,
            )
        )
    return decisions


def _preview_from_snapshot(
    *,
    proposal: D099ReviewProposal,
    proposal_binding: dict[str, Any],
    content: bytes,
    records: list[D100GroupDecisionRecord],
    effective: dict[str, D100GroupDecisionRecord],
) -> D100EntryPreview:
    groups = proposal.semantic_body.groups
    group_ids = [group.semantic_group_id for group in groups]
    _require(
        set(effective) == set(group_ids),
        "D-101 preview requires complete group decisions",
    )
    approved = [
        group for group in groups if effective[group.semantic_group_id].decision == "approve"
    ]
    entries = [
        _memory_template(proposal, group, effective[group.semantic_group_id])
        for group in approved
    ]
    source_runs = [run_id for entry in entries for run_id in entry.template.source_run_ids]
    source_failures = [
        failure_id for entry in entries for failure_id in entry.provenance.source_failure_ids
    ]
    _require(
        len(source_runs) == len(set(source_runs))
        and len(source_failures) == len(set(source_failures)),
        "D-101 preview contains duplicate source provenance",
    )
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(content, records, effective)
    )
    body = D100EntryPreviewBody(
        milestone="D-100",
        evidence_kind="group-aware-memory-entry-preview",
        proposal=proposal_binding,
        journal=descriptor,
        final_decision_hashes={
            group_id: effective[group_id].decision_hash for group_id in group_ids
        },
        approved_group_ids=[group.semantic_group_id for group in approved],
        rejected_group_ids=[
            group.semantic_group_id
            for group in groups
            if effective[group.semantic_group_id].decision == "reject"
        ],
        continued_hold_group_ids=[
            group.semantic_group_id
            for group in groups
            if effective[group.semantic_group_id].decision == "continue_hold"
        ],
        entries=entries,
        leak_scan_passed=True,
        authority=D100PreviewAuthority(
            projection_only=True,
            complete_group_decisions_validated=True,
            external_head_anchor_validated=True,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            memory_admission_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
    )
    payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(payload)) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 preview leak scan failed")
    body_hash, preview_id = _body_identity(body, prefix="d100preview")
    return D100EntryPreview(
        schema_version="memory-entry-preview-d100-v1",
        preview_id=preview_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )


def _candidate_body_from_snapshot(
    *,
    prepared_at: str,
    proposal: D099ReviewProposal,
    proposal_binding: dict[str, Any],
    d100_binding: D101D100GateBinding,
    packet: D101ReviewPacket,
    packet_content: bytes,
    packet_logical_path: str | Path,
    markdown_content: bytes,
    markdown_logical_path: str | Path,
    journal_logical_path: str | Path,
    journal_content: bytes,
    records: list[D100GroupDecisionRecord],
    effective: dict[str, D100GroupDecisionRecord],
    repository: Path,
) -> D101AdmissionCandidateBody:
    _parse_time(prepared_at)
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(journal_content, records, effective)
    )
    decisions = _complete_nonsynthetic_effective_decisions(
        proposal=proposal,
        records=records,
        effective=effective,
    )
    decision_payload = [decision.model_dump(mode="json") for decision in decisions]
    preview = _preview_from_snapshot(
        proposal=proposal,
        proposal_binding=proposal_binding,
        content=journal_content,
        records=records,
        effective=effective,
    )
    return D101AdmissionCandidateBody(
        milestone="D-101",
        evidence_kind="exact-five-group-admission-candidate",
        prepared_at=prepared_at,
        proposal=proposal_binding,
        d100_source_gate=d100_binding,
        review_packet=_document_binding(
            logical_path=packet_logical_path,
            repository=repository,
            schema_version=packet.schema_version,
            document_id=packet.packet_id,
            semantic_body_hash=packet.semantic_body_hash,
            content=packet_content,
        ),
        review_markdown=_artifact_descriptor(
            markdown_content,
            logical_path=markdown_logical_path,
            repository=repository,
        ),
        journal_logical_path=_logical_path(
            journal_logical_path,
            repository=repository,
            field="journal_logical_path",
        ),
        journal=descriptor,
        journal_records=records,
        effective_decisions=decisions,
        decision_set_hash=sha256_text(canonical_json(decision_payload)),
        preview=preview,
        approved_group_count=sum(
            decision.decision == "approve" for decision in decisions
        ),
        rejected_group_count=sum(decision.decision == "reject" for decision in decisions),
        continued_hold_group_count=sum(
            decision.decision == "continue_hold" for decision in decisions
        ),
        authority=D101CandidateAuthority(
            candidate_only=True,
            decision_coverage_complete=True,
            synthetic_decisions_present=False,
            journal_external_anchor_validated=True,
            explicit_candidate_approval_pending=True,
            approval_receipt_present=False,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            memory_admission_unlocked=False,
            memory_index_source_authoring_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
        ),
    )


def prepare_d101_admission_candidate(
    packet_json_path: str | Path,
    packet_markdown_path: str | Path,
    journal_path: str | Path,
    *,
    journal_logical_path: str | Path,
    expected_journal_head: str,
    expected_journal_record_count: int,
    expected_journal_file_sha256: str,
    prepared_at: str,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_logical_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_logical_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
) -> dict[str, Any]:
    """Prepare a portable candidate from an externally pinned journal snapshot."""

    repo = _repo_root(repository)
    _require(
        _SHA256.fullmatch(expected_journal_file_sha256) is not None,
        "D-101 expected journal file hash is invalid",
    )
    packet, packet_content, markdown_content = _load_exact_review_packet(
        packet_json_path,
        packet_markdown_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    try:
        proposal, proposal_binding = _load_exact_proposal(
            proposal_path,
            repository=repo,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 exact proposal validation failed") from exc
    gate, d100_binding, _ = _load_exact_d100_gate(
        d100_source_gate_path,
        repository=repo,
    )
    _validate_d100_bindings(
        proposal=proposal,
        proposal_binding=proposal_binding,
        gate=gate,
    )
    journal = _resolved_path(journal_path, repository=repo)
    try:
        journal_content, records, effective = _read_journal(
            journal,
            proposal=proposal,
            binding=proposal_binding,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 decision journal validation failed") from exc
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(journal_content, records, effective)
    )
    try:
        anchored = _validate_external_anchor(
            descriptor,
            expected_head=expected_journal_head,
            expected_record_count=expected_journal_record_count,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 external journal anchor is invalid") from exc
    _require(anchored, "D-101 external journal anchor is required")
    _require(
        descriptor.file_sha256 == expected_journal_file_sha256,
        "D-101 expected journal file hash does not match",
    )
    body = _candidate_body_from_snapshot(
        prepared_at=prepared_at,
        proposal=proposal,
        proposal_binding=proposal_binding,
        d100_binding=d100_binding,
        packet=packet,
        packet_content=packet_content,
        packet_logical_path=packet_logical_path,
        markdown_content=markdown_content,
        markdown_logical_path=packet_markdown_logical_path,
        journal_logical_path=journal_logical_path,
        journal_content=journal_content,
        records=records,
        effective=effective,
        repository=repo,
    )
    payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(payload)) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 admission candidate leak scan failed")
    body_hash, candidate_id = _body_identity(body, prefix="d101candidate")
    candidate = D101AdmissionCandidate(
        schema_version=CANDIDATE_SCHEMA_VERSION,
        candidate_id=candidate_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    _require(
        _read_stable(journal, label="decision journal") == journal_content,
        "D-101 decision journal changed during candidate preparation",
    )
    return candidate.model_dump(mode="json")


def build_d101_admission_candidate(
    packet_json_path: str | Path,
    packet_markdown_path: str | Path,
    journal_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Public alias for candidate preparation."""

    return prepare_d101_admission_candidate(
        packet_json_path,
        packet_markdown_path,
        journal_path,
        **kwargs,
    )


def _load_valid_candidate(
    candidate_path: str | Path,
    *,
    repository: Path,
    proposal_path: str | Path,
    d100_source_gate_path: str | Path,
    packet_json_path: str | Path,
    packet_markdown_path: str | Path,
    live_journal_path: str | Path | None = None,
    expected_candidate_file_sha256: str | None = None,
) -> tuple[D101AdmissionCandidate, bytes, bytes]:
    selected = _resolved_path(candidate_path, repository=repository)
    content = _read_stable(selected, label="admission candidate")
    if expected_candidate_file_sha256 is not None:
        _require(
            _SHA256.fullmatch(expected_candidate_file_sha256) is not None,
            "D-101 expected candidate file hash is invalid",
        )
        _require(
            sha256_bytes(content) == expected_candidate_file_sha256,
            "D-101 candidate file hash does not match the external anchor",
        )
    try:
        candidate = D101AdmissionCandidate.model_validate_json(content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 admission candidate schema is invalid") from exc
    _require(
        content == encode_d101_document(candidate),
        "D-101 admission candidate is not canonical JSON",
    )
    body_hash, candidate_id = _body_identity(candidate.semantic_body, prefix="d101candidate")
    _require(
        candidate.semantic_body_hash == body_hash,
        "D-101 admission candidate body hash drifted",
    )
    _require(
        candidate.candidate_id == candidate_id,
        "D-101 admission candidate identity drifted",
    )
    _parse_time(candidate.semantic_body.prepared_at)
    packet, packet_content, markdown_content = _load_exact_review_packet(
        packet_json_path,
        packet_markdown_path,
        repository=repository,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    try:
        proposal, proposal_binding = _load_exact_proposal(
            proposal_path,
            repository=repository,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 exact proposal validation failed") from exc
    gate, d100_binding, _ = _load_exact_d100_gate(
        d100_source_gate_path,
        repository=repository,
    )
    _validate_d100_bindings(
        proposal=proposal,
        proposal_binding=proposal_binding,
        gate=gate,
    )
    records = candidate.semantic_body.journal_records
    journal_content = _canonical_journal(records)
    try:
        effective = _validate_record_sequence(
            records,
            proposal=proposal,
            binding=proposal_binding,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError(
            "D-101 embedded decision journal validation failed"
        ) from exc
    descriptor = D100DecisionJournalDescriptor.model_validate(
        _journal_descriptor(journal_content, records, effective)
    )
    _require(
        descriptor == candidate.semantic_body.journal,
        "D-101 embedded journal descriptor drifted",
    )
    expected_body = _candidate_body_from_snapshot(
        prepared_at=candidate.semantic_body.prepared_at,
        proposal=proposal,
        proposal_binding=proposal_binding,
        d100_binding=d100_binding,
        packet=packet,
        packet_content=packet_content,
        packet_logical_path=candidate.semantic_body.review_packet.path,
        markdown_content=markdown_content,
        markdown_logical_path=candidate.semantic_body.review_markdown.path,
        journal_logical_path=candidate.semantic_body.journal_logical_path,
        journal_content=journal_content,
        records=records,
        effective=effective,
        repository=repository,
    )
    _require(
        candidate.semantic_body == expected_body,
        "D-101 admission candidate semantic rebuild differs",
    )
    if live_journal_path is not None:
        live_path = _resolved_path(live_journal_path, repository=repository)
        live_content = _read_stable(live_path, label="live decision journal")
        _require(
            live_content == journal_content,
            "D-101 live decision journal differs from the candidate snapshot",
        )
    _require(
        _read_stable(selected, label="admission candidate") == content,
        "D-101 admission candidate changed during validation",
    )
    return candidate, content, journal_content


def validate_d101_admission_candidate(
    candidate_path: str | Path,
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
    live_journal_path: str | Path | None = None,
    expected_candidate_file_sha256: str | None = None,
) -> dict[str, Any]:
    """Portably rebuild a candidate, with optional external candidate/live anchors."""

    repo = _repo_root(repository)
    candidate, content, _ = _load_valid_candidate(
        candidate_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
        live_journal_path=live_journal_path,
        expected_candidate_file_sha256=expected_candidate_file_sha256,
    )
    body = candidate.semantic_body
    return {
        "ok": True,
        "schema_version": candidate.schema_version,
        "candidate_id": candidate.candidate_id,
        "semantic_body_hash": candidate.semantic_body_hash,
        "candidate_file_bytes": len(content),
        "candidate_file_sha256": sha256_bytes(content),
        "journal_record_count": body.journal.record_count,
        "journal_head_decision_hash": body.journal.head_decision_hash,
        "journal_file_sha256": body.journal.file_sha256,
        "decision_coverage_complete": True,
        "approved_group_count": body.approved_group_count,
        "rejected_group_count": body.rejected_group_count,
        "continued_hold_group_count": body.continued_hold_group_count,
        "live_journal_validated": live_journal_path is not None,
        "approval_receipt_present": False,
        "memory_admission_unlocked": False,
        "memory_index_build_authorized": False,
        "core_campaign_unlocked": False,
        "candidate_validation": "pass",
    }


def _approval_statement(candidate: D101AdmissionCandidate, content: bytes) -> str:
    return " ".join(
        [
            "EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE",
            candidate.candidate_id,
            candidate.semantic_body_hash,
            sha256_bytes(content),
        ]
    )


def _approval_receipt_body(
    *,
    candidate: D101AdmissionCandidate,
    candidate_content: bytes,
    candidate_logical_path: str | Path,
    approval_action_id: str,
    approver_kind: str,
    approver_label: str,
    approval_reference: str,
    rationale: str,
    recorded_at: str,
    repository: Path,
) -> D101ApprovalReceiptBody:
    _parse_time(recorded_at)
    _require(
        _ACTION_ID.fullmatch(approval_action_id) is not None,
        "D-101 approval action ID is invalid",
    )
    _require(
        approver_kind in {"human", "maintainer_assisted"},
        "D-101 approval receipt must be human or maintainer-assisted",
    )
    label = _safe_text(approver_label, field="approver label", maximum=200)
    reference = _safe_text(
        approval_reference,
        field="approval reference",
        maximum=256,
    )
    _require(
        _REFERENCE.fullmatch(reference) is not None,
        "D-101 approval reference is invalid",
    )
    safe_rationale = _safe_text(rationale, field="approval rationale", maximum=2_000)
    return D101ApprovalReceiptBody(
        milestone="D-101",
        evidence_kind="self-attested-exact-candidate-approval",
        recorded_at=recorded_at,
        candidate=_document_binding(
            logical_path=candidate_logical_path,
            repository=repository,
            schema_version=candidate.schema_version,
            document_id=candidate.candidate_id,
            semantic_body_hash=candidate.semantic_body_hash,
            content=candidate_content,
        ),
        approved_candidate_hash=candidate.semantic_body_hash,
        journal=candidate.semantic_body.journal,
        decision_set_hash=candidate.semantic_body.decision_set_hash,
        effective_decisions=candidate.semantic_body.effective_decisions,
        approval_action_id=approval_action_id,
        approver_kind=approver_kind,
        approver_label=label,
        approval_reference=reference,
        rationale=safe_rationale,
        approval_statement_code="EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE",
        approval_statement=_approval_statement(candidate, candidate_content),
        explicit_approval_receipt_recorded=True,
        reviewer_identity_authenticated=False,
        cryptographic_signature_verified=False,
    )


def build_d101_approval_receipt(
    candidate_path: str | Path,
    *,
    candidate_logical_path: str | Path,
    approved_candidate_id: str,
    approved_candidate_semantic_body_hash: str,
    approved_candidate_file_sha256: str,
    approval_action_id: str,
    approver_kind: str,
    approver_label: str,
    approval_reference: str,
    rationale: str,
    recorded_at: str,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
) -> dict[str, Any]:
    """Record self-attested approval of one exact candidate identity."""

    repo = _repo_root(repository)
    _require(
        _SHA256.fullmatch(approved_candidate_semantic_body_hash) is not None
        and _SHA256.fullmatch(approved_candidate_file_sha256) is not None,
        "D-101 approved candidate hashes are invalid",
    )
    candidate, content, _ = _load_valid_candidate(
        candidate_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
        expected_candidate_file_sha256=approved_candidate_file_sha256,
    )
    _require(
        candidate.candidate_id == approved_candidate_id,
        "D-101 approved candidate ID does not match",
    )
    _require(
        candidate.semantic_body_hash == approved_candidate_semantic_body_hash,
        "D-101 approved candidate semantic hash does not match",
    )
    body = _approval_receipt_body(
        candidate=candidate,
        candidate_content=content,
        candidate_logical_path=candidate_logical_path,
        approval_action_id=approval_action_id,
        approver_kind=approver_kind,
        approver_label=approver_label,
        approval_reference=approval_reference,
        rationale=rationale,
        recorded_at=recorded_at,
        repository=repo,
    )
    payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(payload)) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 approval receipt leak scan failed")
    body_hash, receipt_id = _body_identity(body, prefix="d101receipt")
    receipt = D101ApprovalReceipt(
        schema_version=RECEIPT_SCHEMA_VERSION,
        receipt_id=receipt_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return receipt.model_dump(mode="json")


def _load_valid_receipt(
    receipt_path: str | Path,
    candidate_path: str | Path,
    *,
    repository: Path,
    proposal_path: str | Path,
    d100_source_gate_path: str | Path,
    packet_json_path: str | Path,
    packet_markdown_path: str | Path,
    expected_receipt_file_sha256: str | None = None,
) -> tuple[D101ApprovalReceipt, bytes, D101AdmissionCandidate, bytes]:
    selected = _resolved_path(receipt_path, repository=repository)
    content = _read_stable(selected, label="approval receipt")
    if expected_receipt_file_sha256 is not None:
        _require(
            _SHA256.fullmatch(expected_receipt_file_sha256) is not None,
            "D-101 expected receipt file hash is invalid",
        )
        _require(
            sha256_bytes(content) == expected_receipt_file_sha256,
            "D-101 receipt file hash does not match the external anchor",
        )
    try:
        receipt = D101ApprovalReceipt.model_validate_json(content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 approval receipt schema is invalid") from exc
    _require(
        content == encode_d101_document(receipt),
        "D-101 approval receipt is not canonical JSON",
    )
    body_hash, receipt_id = _body_identity(receipt.semantic_body, prefix="d101receipt")
    _require(
        receipt.semantic_body_hash == body_hash,
        "D-101 approval receipt body hash drifted",
    )
    _require(receipt.receipt_id == receipt_id, "D-101 approval receipt identity drifted")
    candidate, candidate_content, _ = _load_valid_candidate(
        candidate_path,
        repository=repository,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
    )
    expected_body = _approval_receipt_body(
        candidate=candidate,
        candidate_content=candidate_content,
        candidate_logical_path=receipt.semantic_body.candidate.path,
        approval_action_id=receipt.semantic_body.approval_action_id,
        approver_kind=receipt.semantic_body.approver_kind,
        approver_label=receipt.semantic_body.approver_label,
        approval_reference=receipt.semantic_body.approval_reference,
        rationale=receipt.semantic_body.rationale,
        recorded_at=receipt.semantic_body.recorded_at,
        repository=repository,
    )
    _require(
        receipt.semantic_body == expected_body,
        "D-101 approval receipt semantic rebuild differs",
    )
    _require(
        _read_stable(selected, label="approval receipt") == content,
        "D-101 approval receipt changed during validation",
    )
    return receipt, content, candidate, candidate_content


def validate_d101_approval_receipt(
    receipt_path: str | Path,
    candidate_path: str | Path,
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
    expected_receipt_file_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate an exact self-attested receipt and its candidate."""

    repo = _repo_root(repository)
    receipt, content, candidate, _ = _load_valid_receipt(
        receipt_path,
        candidate_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
        expected_receipt_file_sha256=expected_receipt_file_sha256,
    )
    return {
        "ok": True,
        "schema_version": receipt.schema_version,
        "receipt_id": receipt.receipt_id,
        "semantic_body_hash": receipt.semantic_body_hash,
        "receipt_file_bytes": len(content),
        "receipt_file_sha256": sha256_bytes(content),
        "candidate_id": candidate.candidate_id,
        "candidate_file_sha256": receipt.semantic_body.candidate.file_sha256,
        "explicit_approval_receipt_recorded": True,
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "admission_seal_created": False,
        "memory_index_build_authorized": False,
        "core_campaign_unlocked": False,
        "receipt_validation": "pass",
    }


def _admission_seal_body(
    *,
    candidate: D101AdmissionCandidate,
    candidate_content: bytes,
    candidate_logical_path: str | Path,
    receipt: D101ApprovalReceipt,
    receipt_content: bytes,
    receipt_logical_path: str | Path,
    sealed_at: str,
    repository: Path,
) -> D101AdmissionSealBody:
    _parse_time(sealed_at)
    admitted_entries = candidate.semantic_body.preview.semantic_body.entries
    admitted_count = len(admitted_entries)
    open_holds = sum(
        decision.decision == "continue_hold"
        for decision in candidate.semantic_body.effective_decisions
    )
    return D101AdmissionSealBody(
        milestone="D-101",
        evidence_kind="portable-group-memory-admission-seal",
        sealed_at=sealed_at,
        candidate=_document_binding(
            logical_path=candidate_logical_path,
            repository=repository,
            schema_version=candidate.schema_version,
            document_id=candidate.candidate_id,
            semantic_body_hash=candidate.semantic_body_hash,
            content=candidate_content,
        ),
        approval_receipt=_document_binding(
            logical_path=receipt_logical_path,
            repository=repository,
            schema_version=receipt.schema_version,
            document_id=receipt.receipt_id,
            semantic_body_hash=receipt.semantic_body_hash,
            content=receipt_content,
        ),
        proposal=candidate.semantic_body.proposal,
        d100_source_gate=candidate.semantic_body.d100_source_gate,
        review_packet=candidate.semantic_body.review_packet,
        review_markdown=candidate.semantic_body.review_markdown,
        journal_logical_path=candidate.semantic_body.journal_logical_path,
        journal=candidate.semantic_body.journal,
        effective_decisions=candidate.semantic_body.effective_decisions,
        decision_set_hash=candidate.semantic_body.decision_set_hash,
        admitted_entries=admitted_entries,
        leak_scan_passed=True,
        authority=D101SealAuthority(
            admission_snapshot_sealed=True,
            decision_coverage_complete=True,
            explicit_approval_receipt_validated=True,
            reviewer_identity_authenticated=False,
            cryptographic_signature_verified=False,
            open_hold_group_count=open_holds,
            group_review_finalized=open_holds == 0,
            admitted_memory_rule_count=admitted_count,
            memory_admission_unlocked=admitted_count > 0,
            memory_index_source_authoring_unlocked=admitted_count > 0,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
        next_gate="group-aware-memory-source-materialization-and-render-policy",
    )


def build_d101_admission_seal(
    candidate_path: str | Path,
    receipt_path: str | Path,
    live_journal_path: str | Path,
    *,
    candidate_logical_path: str | Path,
    receipt_logical_path: str | Path,
    sealed_at: str,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
) -> dict[str, Any]:
    """Seal an explicitly approved candidate while the live journal still matches."""

    repo = _repo_root(repository)
    candidate, candidate_content, _ = _load_valid_candidate(
        candidate_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
        live_journal_path=live_journal_path,
    )
    receipt, receipt_content, receipt_candidate, receipt_candidate_content = (
        _load_valid_receipt(
            receipt_path,
            candidate_path,
            repository=repo,
            proposal_path=proposal_path,
            d100_source_gate_path=d100_source_gate_path,
            packet_json_path=packet_json_path,
            packet_markdown_path=packet_markdown_path,
        )
    )
    _require(
        receipt_candidate == candidate and receipt_candidate_content == candidate_content,
        "D-101 receipt is bound to a different candidate",
    )
    body = _admission_seal_body(
        candidate=candidate,
        candidate_content=candidate_content,
        candidate_logical_path=candidate_logical_path,
        receipt=receipt,
        receipt_content=receipt_content,
        receipt_logical_path=receipt_logical_path,
        sealed_at=sealed_at,
        repository=repo,
    )
    payload = body.model_dump(mode="json")
    if any(pattern.search(canonical_json(payload)) for pattern in _LEAK_PATTERNS):
        raise D101GroupAdmissionError("D-101 admission seal leak scan failed")
    body_hash, seal_id = _body_identity(body, prefix="d101seal")
    seal = D101AdmissionSeal(
        schema_version=SEAL_SCHEMA_VERSION,
        seal_id=seal_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return seal.model_dump(mode="json")


def validate_d101_admission_seal(
    seal_path: str | Path,
    candidate_path: str | Path,
    receipt_path: str | Path,
    live_journal_path: str | Path,
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
    expected_seal_file_sha256: str | None = None,
) -> dict[str, Any]:
    """Rebuild a seal from its exact candidate, receipt, and live journal."""

    repo = _repo_root(repository)
    selected = _resolved_path(seal_path, repository=repo)
    content = _read_stable(selected, label="admission seal")
    if expected_seal_file_sha256 is not None:
        _require(
            _SHA256.fullmatch(expected_seal_file_sha256) is not None,
            "D-101 expected seal file hash is invalid",
        )
        _require(
            sha256_bytes(content) == expected_seal_file_sha256,
            "D-101 seal file hash does not match the external anchor",
        )
    try:
        seal = D101AdmissionSeal.model_validate_json(content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 admission seal schema is invalid") from exc
    _require(content == encode_d101_document(seal), "D-101 seal is not canonical JSON")
    body_hash, seal_id = _body_identity(seal.semantic_body, prefix="d101seal")
    _require(seal.semantic_body_hash == body_hash, "D-101 seal body hash drifted")
    _require(seal.seal_id == seal_id, "D-101 seal identity drifted")
    expected = build_d101_admission_seal(
        candidate_path,
        receipt_path,
        live_journal_path,
        candidate_logical_path=seal.semantic_body.candidate.path,
        receipt_logical_path=seal.semantic_body.approval_receipt.path,
        sealed_at=seal.semantic_body.sealed_at,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
    )
    _require(
        content == encode_d101_document(expected),
        "D-101 admission seal semantic rebuild differs",
    )
    _require(
        _read_stable(selected, label="admission seal") == content,
        "D-101 admission seal changed during validation",
    )
    body = seal.semantic_body
    return {
        "ok": True,
        "schema_version": seal.schema_version,
        "seal_id": seal.seal_id,
        "semantic_body_hash": seal.semantic_body_hash,
        "seal_file_bytes": len(content),
        "seal_file_sha256": sha256_bytes(content),
        "candidate_id": body.candidate.document_id,
        "receipt_id": body.approval_receipt.document_id,
        "journal_head_decision_hash": body.journal.head_decision_hash,
        "admitted_memory_rule_count": body.authority.admitted_memory_rule_count,
        "open_hold_group_count": body.authority.open_hold_group_count,
        "group_review_finalized": body.authority.group_review_finalized,
        "memory_admission_unlocked": body.authority.memory_admission_unlocked,
        "memory_index_source_authoring_unlocked": (
            body.authority.memory_index_source_authoring_unlocked
        ),
        "memory_index_build_authorized": False,
        "memory_index_built": False,
        "core_campaign_unlocked": False,
        "seal_validation": "pass",
    }


def build_d101_source_gate(
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
) -> dict[str, Any]:
    """Build the deterministic source-only D-101 gate."""

    repo = _repo_root(repository)
    packet, packet_content, markdown_content = _load_exact_review_packet(
        packet_json_path,
        packet_markdown_path,
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    try:
        proposal, proposal_binding = _load_exact_proposal(
            proposal_path,
            repository=repo,
        )
    except ContractError as exc:
        raise D101GroupAdmissionError("D-101 exact proposal validation failed") from exc
    gate, d100_binding, _ = _load_exact_d100_gate(
        d100_source_gate_path,
        repository=repo,
    )
    _validate_d100_bindings(
        proposal=proposal,
        proposal_binding=proposal_binding,
        gate=gate,
    )
    body = D101SourceGateBody(
        milestone="D-101",
        evidence_kind="review-packet-and-admission-mechanism-source-gate",
        recorded_at=SOURCE_GATE_RECORDED_AT,
        proposal=proposal_binding,
        d100_source_gate=d100_binding,
        review_packet=_document_binding(
            logical_path=packet_json_path,
            repository=repo,
            schema_version=packet.schema_version,
            document_id=packet.packet_id,
            semantic_body_hash=packet.semantic_body_hash,
            content=packet_content,
        ),
        review_markdown=_artifact_descriptor(
            markdown_content,
            logical_path=packet_markdown_path,
            repository=repo,
        ),
        implementation_files=[
            _source_descriptor(path, repository=repo)
            for path in SOURCE_IMPLEMENTATION_PATHS
        ],
        packet_json_markdown_exact_binding=True,
        candidate_receipt_seal_flow_implemented=True,
        journal_head_count_file_sha_required=True,
        synthetic_journal_or_receipt_rejected=True,
        reviewer_identity_self_attested_not_authenticated=True,
        legacy_memory_builder_connected=False,
        authority=D101SourceAuthority(
            mechanism_source_gate_only=True,
            review_packet_generated=True,
            production_human_decision_records=0,
            admission_candidate_created=False,
            approval_receipt_present=False,
            admission_seal_created=False,
            admitted_memory_rule_count=0,
            memory_admission_unlocked=False,
            memory_index_source_authoring_unlocked=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            historical_d099_or_d100_artifacts_modified=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
            provider_calls_made=0,
            evaluator_calls_made=0,
            added_model_cost_usd=0,
        ),
        next_gate="explicit-five-group-decisions-and-exact-candidate-approval",
    )
    body_hash, gate_id = _body_identity(body, prefix="d101")
    source_gate = D101SourceGate(
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        gate_id=gate_id,
        semantic_body_hash=body_hash,
        semantic_body=body,
    )
    return source_gate.model_dump(mode="json")


def validate_d101_source_gate(
    source_gate_path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
    expected_source_gate_file_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the checked-in D-101 source gate by exact rebuild."""

    repo = _repo_root(repository)
    selected = _resolved_path(source_gate_path, repository=repo)
    content = _read_stable(selected, label="source gate")
    if expected_source_gate_file_sha256 is not None:
        _require(
            _SHA256.fullmatch(expected_source_gate_file_sha256) is not None,
            "D-101 expected source gate file hash is invalid",
        )
        _require(
            sha256_bytes(content) == expected_source_gate_file_sha256,
            "D-101 source gate file hash does not match the external anchor",
        )
    try:
        gate = D101SourceGate.model_validate_json(content)
    except ValidationError as exc:
        raise D101GroupAdmissionError("D-101 source gate schema is invalid") from exc
    _require(
        content == encode_d101_document(gate),
        "D-101 source gate is not canonical JSON",
    )
    body_hash, gate_id = _body_identity(gate.semantic_body, prefix="d101")
    _require(gate.semantic_body_hash == body_hash, "D-101 source gate body hash drifted")
    _require(gate.gate_id == gate_id, "D-101 source gate identity drifted")
    expected = build_d101_source_gate(
        repository=repo,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
        packet_json_path=packet_json_path,
        packet_markdown_path=packet_markdown_path,
    )
    _require(
        content == encode_d101_document(expected),
        "D-101 source gate does not match the implementation",
    )
    return {
        **d101_mechanism_status(
            repository=repo,
            proposal_path=proposal_path,
            d100_source_gate_path=d100_source_gate_path,
            packet_json_path=packet_json_path,
            packet_markdown_path=packet_markdown_path,
        ),
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": gate.gate_id,
        "semantic_body_hash": gate.semantic_body_hash,
        "source_gate_bytes": len(content),
        "source_gate_file_sha256": sha256_bytes(content),
        "source_gate_validation": "pass",
    }


def d101_mechanism_status(
    *,
    repository: str | Path | None = None,
    proposal_path: str | Path = DEFAULT_PROPOSAL_PATH,
    d100_source_gate_path: str | Path = DEFAULT_D100_SOURCE_GATE_PATH,
    packet_json_path: str | Path = DEFAULT_PACKET_JSON_PATH,
    packet_markdown_path: str | Path = DEFAULT_PACKET_MARKDOWN_PATH,
) -> dict[str, Any]:
    """Report source-only readiness without implying a human decision."""

    validation = validate_d101_review_packet(
        packet_json_path,
        packet_markdown_path,
        repository=repository,
        proposal_path=proposal_path,
        d100_source_gate_path=d100_source_gate_path,
    )
    return {
        "schema_version": "memory-group-admission-mechanism-status-d101-v1",
        "milestone": "D-101",
        "packet_id": validation["packet_id"],
        "review_packet_generated": True,
        "candidate_receipt_seal_flow_implemented": True,
        "semantic_group_count": 5,
        "candidate_group_count": 3,
        "hold_group_count": 2,
        "production_human_decision_records": 0,
        "admission_candidate_created": False,
        "approval_receipt_present": False,
        "admission_seal_created": False,
        "admitted_memory_rule_count": 0,
        "memory_admission_unlocked": False,
        "memory_index_source_authoring_unlocked": False,
        "memory_index_build_authorized": False,
        "memory_index_built": False,
        "memory_index_frozen": False,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
        "next_gate": "explicit-five-group-decisions-and-exact-candidate-approval",
    }


def write_d101_new_exact(path: str | Path, content: bytes) -> dict[str, Any]:
    """Exclusively create a D-101 artifact, allowing only an exact retry."""

    selected = Path(path)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return {
            "created": True,
            "idempotent_retry": False,
            "file_bytes": len(content),
            "file_sha256": sha256_bytes(content),
        }
    except FileExistsError:
        existing = _read_stable(selected, label="existing output")
        _require(
            existing == content,
            "D-101 output already exists with different bytes",
        )
        return {
            "created": False,
            "idempotent_retry": True,
            "file_bytes": len(existing),
            "file_sha256": sha256_bytes(existing),
        }
