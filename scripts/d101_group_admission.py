"""Standalone D-101 packet, candidate, receipt, and seal commands.

The shared PatchLoop CLI is intentionally not changed because it is part of the
exact D-100 source-gate identity.  `build-source` creates only the immutable
review packet and mechanism source gate.  The mutating decision journal remains
a separate D-100 action and every later D-101 artifact requires explicit inputs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from patchloop.memory import d101_group_admission as d101


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--proposal", type=Path, default=d101.DEFAULT_PROPOSAL_PATH)
    parser.add_argument(
        "--d100-source-gate",
        type=Path,
        default=d101.DEFAULT_D100_SOURCE_GATE_PATH,
    )
    parser.add_argument(
        "--packet-json",
        type=Path,
        default=d101.DEFAULT_PACKET_JSON_PATH,
    )
    parser.add_argument(
        "--packet-markdown",
        type=Path,
        default=d101.DEFAULT_PACKET_MARKDOWN_PATH,
    )


def _base_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "repository": args.repository,
        "proposal_path": args.proposal,
        "d100_source_gate_path": args.d100_source_gate,
        "packet_json_path": args.packet_json,
        "packet_markdown_path": args.packet_markdown,
    }


def _write_generated(path: Path, content: bytes, *, repository: Path) -> None:
    selected = path if path.is_absolute() else repository / path
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(content)


def _build_source(args: argparse.Namespace) -> dict[str, Any]:
    repository = args.repository.resolve()
    packet = d101.build_d101_review_packet(
        repository=repository,
        proposal_path=args.proposal,
        d100_source_gate_path=args.d100_source_gate,
    )
    packet_content = d101.encode_d101_document(packet)
    markdown_content = d101.render_d101_review_packet_markdown(packet)
    _write_generated(args.packet_json, packet_content, repository=repository)
    _write_generated(args.packet_markdown, markdown_content, repository=repository)
    gate = d101.build_d101_source_gate(**_base_kwargs(args))
    gate_content = d101.encode_d101_document(gate)
    _write_generated(args.output, gate_content, repository=repository)
    return d101.validate_d101_source_gate(
        args.output,
        **_base_kwargs(args),
    )


def _validate_source(args: argparse.Namespace) -> dict[str, Any]:
    return d101.validate_d101_source_gate(
        args.source_gate,
        expected_source_gate_file_sha256=args.expected_file_sha256,
        **_base_kwargs(args),
    )


def _validate_packet(args: argparse.Namespace) -> dict[str, Any]:
    return d101.validate_d101_review_packet(
        args.packet_json,
        args.packet_markdown,
        repository=args.repository,
        proposal_path=args.proposal,
        d100_source_gate_path=args.d100_source_gate,
    )


def _prepare_candidate(args: argparse.Namespace) -> dict[str, Any]:
    payload = d101.build_d101_admission_candidate(
        args.packet_json,
        args.packet_markdown,
        args.journal,
        journal_logical_path=args.journal_logical_path,
        expected_journal_head=args.expected_head,
        expected_journal_record_count=args.expected_record_count,
        expected_journal_file_sha256=args.expected_file_sha256,
        prepared_at=args.prepared_at,
        repository=args.repository,
        proposal_path=args.proposal,
        d100_source_gate_path=args.d100_source_gate,
    )
    write = d101.write_d101_new_exact(args.output, d101.encode_d101_document(payload))
    return {**write, "candidate_id": payload["candidate_id"]}


def _record_approval(args: argparse.Namespace) -> dict[str, Any]:
    if args.confirm_statement != "EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE":
        raise d101.D101GroupAdmissionError(
            "D-101 exact approval confirmation statement is missing"
        )
    payload = d101.build_d101_approval_receipt(
        args.candidate,
        candidate_logical_path=args.candidate_logical_path,
        approved_candidate_id=args.approved_candidate_id,
        approved_candidate_semantic_body_hash=args.approved_candidate_semantic_body_hash,
        approved_candidate_file_sha256=args.approved_candidate_file_sha256,
        approval_action_id=args.action_id,
        approver_kind=args.approver_kind,
        approver_label=args.approver_label,
        approval_reference=args.approval_reference,
        rationale=args.rationale,
        recorded_at=args.recorded_at,
        **_base_kwargs(args),
    )
    write = d101.write_d101_new_exact(args.output, d101.encode_d101_document(payload))
    return {**write, "receipt_id": payload["receipt_id"]}


def _seal(args: argparse.Namespace) -> dict[str, Any]:
    payload = d101.build_d101_admission_seal(
        args.candidate,
        args.receipt,
        args.journal,
        candidate_logical_path=args.candidate_logical_path,
        receipt_logical_path=args.receipt_logical_path,
        sealed_at=args.sealed_at,
        **_base_kwargs(args),
    )
    write = d101.write_d101_new_exact(args.output, d101.encode_d101_document(payload))
    return {**write, "seal_id": payload["seal_id"]}


def _validate_seal(args: argparse.Namespace) -> dict[str, Any]:
    return d101.validate_d101_admission_seal(
        args.seal,
        args.candidate,
        args.receipt,
        args.journal,
        expected_seal_file_sha256=args.expected_file_sha256,
        **_base_kwargs(args),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-source")
    _common_paths(build)
    build.add_argument("--output", type=Path, default=d101.DEFAULT_SOURCE_GATE_PATH)
    build.set_defaults(handler=_build_source)

    validate_source = subparsers.add_parser("validate-source")
    _common_paths(validate_source)
    validate_source.add_argument(
        "--source-gate",
        type=Path,
        default=d101.DEFAULT_SOURCE_GATE_PATH,
    )
    validate_source.add_argument("--expected-file-sha256")
    validate_source.set_defaults(handler=_validate_source)

    validate_packet = subparsers.add_parser("validate-packet")
    _common_paths(validate_packet)
    validate_packet.set_defaults(handler=_validate_packet)

    candidate = subparsers.add_parser("prepare-candidate")
    _common_paths(candidate)
    candidate.add_argument("--journal", type=Path, required=True)
    candidate.add_argument("--journal-logical-path", type=Path, required=True)
    candidate.add_argument("--expected-head", required=True)
    candidate.add_argument("--expected-record-count", type=int, required=True)
    candidate.add_argument("--expected-file-sha256", required=True)
    candidate.add_argument("--prepared-at", required=True)
    candidate.add_argument("--output", type=Path, required=True)
    candidate.set_defaults(handler=_prepare_candidate)

    approval = subparsers.add_parser("record-exact-approval")
    _common_paths(approval)
    approval.add_argument("--candidate", type=Path, required=True)
    approval.add_argument("--candidate-logical-path", type=Path, required=True)
    approval.add_argument("--approved-candidate-id", required=True)
    approval.add_argument("--approved-candidate-semantic-body-hash", required=True)
    approval.add_argument("--approved-candidate-file-sha256", required=True)
    approval.add_argument("--action-id", required=True)
    approval.add_argument(
        "--approver-kind",
        choices=["human", "maintainer_assisted"],
        required=True,
    )
    approval.add_argument("--approver-label", required=True)
    approval.add_argument("--approval-reference", required=True)
    approval.add_argument("--rationale", required=True)
    approval.add_argument("--recorded-at", required=True)
    approval.add_argument("--confirm-statement", required=True)
    approval.add_argument("--output", type=Path, required=True)
    approval.set_defaults(handler=_record_approval)

    seal = subparsers.add_parser("seal")
    _common_paths(seal)
    seal.add_argument("--candidate", type=Path, required=True)
    seal.add_argument("--receipt", type=Path, required=True)
    seal.add_argument("--journal", type=Path, required=True)
    seal.add_argument("--candidate-logical-path", type=Path, required=True)
    seal.add_argument("--receipt-logical-path", type=Path, required=True)
    seal.add_argument("--sealed-at", required=True)
    seal.add_argument("--output", type=Path, required=True)
    seal.set_defaults(handler=_seal)

    validate_seal = subparsers.add_parser("validate-seal")
    _common_paths(validate_seal)
    validate_seal.add_argument("--seal", type=Path, required=True)
    validate_seal.add_argument("--candidate", type=Path, required=True)
    validate_seal.add_argument("--receipt", type=Path, required=True)
    validate_seal.add_argument("--journal", type=Path, required=True)
    validate_seal.add_argument("--expected-file-sha256")
    validate_seal.set_defaults(handler=_validate_seal)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = args.handler(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
