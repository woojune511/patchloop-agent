"""Historical metadata compatibility never changes ordinary resume admission."""

import json
from types import SimpleNamespace

import pytest
from test_correction_allowance import envelope_data

from diagnostics.checkpoint_envelope import read_checkpoint_envelope
from patchloop.dev.contracts import DevRunEnvelope
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes


def source(tmp_path, *, legacy=False, alter=None):
    data = envelope_data()
    if legacy:
        data["completion_cost_contract"].update(
            horizon="completion-and-available-bounded-repair-v2",
            reservation="role-successors-plus-correction-v3",
            role_calls="existing-runner-path-slots-no-extra-calls")
    if alter:
        alter(data)
    # Fields outside the intentional historical contract still use valid wire values.
    encoded = json.loads(DevRunEnvelope.model_validate(envelope_data()).model_dump_json())
    encoded["completion_cost_contract"] = data["completion_cost_contract"]
    encoded["split"] = data["split"]
    journal = DevJournal(tmp_path, data["run_id"])
    raw = (canonical_json(encoded) + "\n").encode()
    journal.envelope_path.write_bytes(raw)
    saved = SimpleNamespace(root=tmp_path, run_id=data["run_id"], envelope_hash=sha256_bytes(raw))
    return saved, raw


def test_current_metadata_matches_the_strict_reader(tmp_path):
    saved, _ = source(tmp_path)
    assert read_checkpoint_envelope(saved) == DevJournal(tmp_path, saved.run_id).load_envelope()


def test_known_history_is_read_only_and_still_cannot_resume(tmp_path):
    saved, before = source(tmp_path, legacy=True)
    metadata = read_checkpoint_envelope(saved)
    assert metadata.completion_cost_contract["reservation"] == "role-successors-plus-correction-v3"
    journal = DevJournal(tmp_path, saved.run_id)
    assert journal.envelope_path.read_bytes() == before
    with pytest.raises(RecoveryError, match="invalid"):
        journal.load_envelope()
    with pytest.raises(ValueError, match="exact contract"):
        DevRunEnvelope.model_validate(metadata.model_dump())


@pytest.mark.parametrize("alter", [
    lambda data: data["completion_cost_contract"].update(correction_credits_per_run=2),
    lambda data: data["completion_cost_contract"].update(unrecognized=True),
])
def test_unknown_contract_is_rejected_even_with_a_matching_file_hash(tmp_path, alter):
    saved, _ = source(tmp_path, legacy=True, alter=alter)
    with pytest.raises(ContractError, match="unsupported historical"):
        read_checkpoint_envelope(saved)


def test_hash_and_other_envelope_validation_are_preserved(tmp_path):
    saved, _ = source(tmp_path, legacy=True, alter=lambda data: data.update(split="wrong"))
    with pytest.raises(ValueError):
        read_checkpoint_envelope(saved)
    saved.envelope_hash = "sha256:" + "0" * 64
    with pytest.raises(ContractError, match="hash changed"):
        read_checkpoint_envelope(saved)
