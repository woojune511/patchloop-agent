import pytest

from diagnostics.anyio_caller_preservation import PROGRAM, TARGET, final_mutations
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.mark.parametrize("failure", [None, "rejected", "changed_journal", "not_accepted"])
def test_final_candidate_requires_two_bound_accepted_edits(tmp_path, failure):
    journal = DevJournal(tmp_path, "run_dev_fixture")
    for index in range(2):
        started = {
            "tool": "replace_text",
            "action_id": str(index),
            "input_hash": str(index),
            "mutation_target_path": TARGET,
            "mutation_expected_worktree_diff_hash": str(index),
        }
        journal.append("action_started", started)
        journal.append(
            "action_finished",
            {
                "action_id": str(index),
                "result": {
                    "error_code": "rejected" if failure == "rejected" else None,
                    "input_hash": str(index),
                    "output": {"mutation": {"diff_hash": str(index)}},
                },
            },
        )
    journal.append(
        "terminal", {"terminal": "AGENT_STOPPED" if failure == "not_accepted" else "EVALUATOR_PASS"}
    )
    digest = sha256_bytes(journal.path.read_bytes())
    if failure == "changed_journal":
        journal.append("another_event", {})
    if failure:
        with pytest.raises(ContractError):
            final_mutations(tmp_path, journal.run_id, digest)
    else:
        mutations = final_mutations(tmp_path, journal.run_id, digest)
        assert [m["action_id"] for m in mutations] == ["0", "1"]


def test_program_pair_only_changes_cancel_flag():
    body = PROGRAM.read_text(encoding="utf-8")
    for flag in (False, True):
        program = f"CANCEL = {flag!r}\n" + body
        assert len(program) < 8000
        compile(program, "probe", "exec")
