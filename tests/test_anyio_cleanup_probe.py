import copy

import pytest

from diagnostics.anyio_cleanup_probe import PROGRAM, TARGET, first_mutation, omit_caller_cancel
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


def test_ablation_removes_only_caller_cancel_and_preserves_outer_request():
    source = ("        except CancelledError:\n"
              "            self._runner_task.cancel()\n"
              "            raise\n        finally:\n            pass\n"
              "    def run_test(self):\n        self._runner_task.cancel()\n")
    changed = omit_caller_cancel(source)
    assert source.splitlines()[2:] == changed.splitlines()[1:]
    assert changed.count("self._runner_task.cancel()") == 1
    with pytest.raises(ContractError, match="one caller-side"):
        omit_caller_cancel(changed)
    with pytest.raises(ContractError, match="one caller-side"):
        omit_caller_cancel(source + source)


@pytest.mark.parametrize("failure", [None, "changed_journal", "unaccepted"])
def test_saved_first_mutation_binding(tmp_path, failure):
    journal = DevJournal(tmp_path, "run_dev_fixture")
    # An inherited mutation must not be selected as the new first mutation.
    journal.append("action_started", {"tool": "replace_text", "action_id": "old"})
    journal.append("diagnostic_checkpoint_fork", {})
    payload = {"tool": "replace_text", "action_id": "first", "input_hash": "input",
               "mutation_target_path": TARGET, "baseline_changed_files": [],
               "mutation_expected_worktree_diff_hash": "diff"}
    journal.append("action_started", payload)
    result = {"input_hash": "input", "error_code": "rejected" if failure == "unaccepted" else None,
              "output": {"mutation": {"diff_hash": "diff"}}}
    journal.append("action_finished", {"action_id": "first", "result": result})
    digest = sha256_bytes(journal.path.read_bytes())
    if failure == "changed_journal":
        journal.append("another_event", {})
    if failure:
        with pytest.raises(ContractError):
            first_mutation(tmp_path, journal.run_id, digest)
    else:
        assert first_mutation(tmp_path, journal.run_id, digest) == copy.deepcopy(payload)


def test_probe_program_has_same_body_in_traced_and_untraced_modes():
    body = PROGRAM.read_text(encoding="utf-8")
    a, b = [f"TRACE = {flag!r}\n" + body for flag in (False, True)]
    assert a.splitlines()[1:] == b.splitlines()[1:]
    assert len(a) < 8000
    compile(a, "probe", "exec")
    compile(b, "probe", "exec")
