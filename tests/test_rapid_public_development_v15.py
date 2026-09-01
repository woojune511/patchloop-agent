from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals import rapid_public_development_v15 as rapid
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def test_superseded_candidate_v19_is_preserved_byte_for_byte() -> None:
    candidate = rapid.load_consumed_rapid_public_development_v15_candidate(REPOSITORY)
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()

    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 33_703
    assert sha256_bytes(raw) == (
        "sha256:490701a56d7f00e204593df9fa74b9e36b64b2e3b8024f87ae163d3aff9f270e"
    )
    assert candidate["execution_hash"] == (
        "sha256:337649783ad6daa37afccefe7f4f0fcc873b4ba2d7f7bce354e036dee18ec46c"
    )
    assert candidate["content_hash"] == (
        "sha256:a116f47116235b59f404d307ec8083523e7c0c6cd29145a429d142845b6ff4b2"
    )
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0


def test_superseded_rehearsal_v16_is_preserved_byte_for_byte() -> None:
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()
    value = json.loads(raw)
    body = {key: item for key, item in value.items() if key != "content_hash"}

    assert len(raw) == 3_082
    assert sha256_bytes(raw) == (
        "sha256:289ca98395da198f0be5ef409e37b989efc0d0e0bf7a510fb867da78efd6aaa9"
    )
    assert (
        value["content_hash"]
        == sha256_json(body)
        == ("sha256:17053de206924ada7a4f612070560061809499c06b3c9b416cac4affb472b452")
    )
    assert value["verified_manifest_count"] == 6
    assert value["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert value["second_provider_boundary"]["provider_dispatch_blocked"] is True
    assert value["provider_calls_made"] == value["docker_calls_made"] == 0
