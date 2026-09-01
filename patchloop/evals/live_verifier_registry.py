"""Central registry for paid-boundary experiment plan verifiers.

The runner owns one dispatch seam.  Experiment modules own their exact plan and
manifest matchers, while this registry makes supported schema combinations
machine-visible before a paid run can be admitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

from patchloop.contracts import ExperimentPurpose, RunManifest
from patchloop.util import sha256_json


@dataclass(frozen=True)
class LiveVerifierEntry:
    """One exact plan schema and its lazy manifest verifier."""

    verifier_id: str
    experiment_id: str
    plan_schema: str
    plan_kind: str | None
    purpose: str
    official: bool
    module: str
    function: str
    call_shape: Literal["rapid", "heldout"]
    requires_row_capability: bool = False
    plan_has_content_hash: bool = True
    plan_binds_experiment_id: bool = True

    def descriptor(self) -> dict[str, Any]:
        return {
            "verifier_id": self.verifier_id,
            "experiment_id": self.experiment_id,
            "plan_schema": self.plan_schema,
            "plan_kind": self.plan_kind,
            "purpose": self.purpose,
            "official": self.official,
            "requires_row_capability": self.requires_row_capability,
            "plan_binds_experiment_id": self.plan_binds_experiment_id,
        }


@dataclass(frozen=True)
class VerifierDecision:
    """Distinguish an unknown legacy plan from a known-but-invalid plan."""

    handled: bool
    accepted: bool
    verifier_id: str | None = None
    requires_row_capability: bool = False


class LiveVerifierRegistry:
    """Resolve exact experiment/schema tuples without runner-side ID branches."""

    def __init__(self, entries: tuple[LiveVerifierEntry, ...]) -> None:
        keys = [(item.experiment_id, item.plan_schema, item.plan_kind) for item in entries]
        if len(keys) != len(set(keys)):
            raise ValueError("live verifier registry contains a duplicate key")
        self._entries = entries
        self._by_key = {
            (item.experiment_id, item.plan_schema, item.plan_kind): item for item in entries
        }
        self._known_experiments = frozenset(item.experiment_id for item in entries)

    @property
    def content_hash(self) -> str:
        return sha256_json([item.descriptor() for item in self._entries])

    def descriptors(self) -> tuple[dict[str, Any], ...]:
        return tuple(item.descriptor() for item in self._entries)

    def descriptor_hash_for(
        self,
        *,
        experiment_id: str,
        plan_schema: str,
        plan_kind: str | None,
    ) -> str:
        """Hash one registered verifier without coupling it to later entries."""

        entry = self._by_key.get((experiment_id, plan_schema, plan_kind))
        if entry is None:
            raise KeyError("live verifier registry has no matching experiment/schema/kind entry")
        return sha256_json(entry.descriptor())

    def _entry_for_plan(self, plan: dict[str, Any]) -> LiveVerifierEntry | None:
        experiment_id = plan.get("experiment_id")
        if not isinstance(experiment_id, str):
            suite = plan.get("suite")
            if isinstance(suite, dict):
                experiment_id = suite.get("suite_id")
        return self._by_key.get(
            (
                experiment_id,
                plan.get("schema_version"),
                plan.get("plan_kind"),
            )
        )

    def _entry_for_manifest_plan(
        self,
        manifest: RunManifest,
        plan: dict[str, Any],
    ) -> LiveVerifierEntry | None:
        experiment = manifest.experiment
        if experiment is None:
            return None
        return self._by_key.get(
            (
                experiment.experiment_id,
                plan.get("schema_version"),
                plan.get("plan_kind"),
            )
        )

    @staticmethod
    def _entry_accepts_plan(entry: LiveVerifierEntry, plan: dict[str, Any]) -> bool:
        plan_experiment_id = plan.get("experiment_id")
        if not isinstance(plan_experiment_id, str):
            suite = plan.get("suite")
            plan_experiment_id = suite.get("suite_id") if isinstance(suite, dict) else None
        if entry.plan_binds_experiment_id and plan_experiment_id != entry.experiment_id:
            return False
        if (
            plan.get("purpose", entry.purpose) != entry.purpose
            or plan.get("official", entry.official) is not entry.official
        ):
            return False
        if entry.plan_has_content_hash:
            content_hash = plan.get("content_hash")
            body = {key: value for key, value in plan.items() if key != "content_hash"}
            if content_hash != sha256_json(body):
                return False
        return True

    def validate_authorization_plan(self, plan: dict[str, Any]) -> VerifierDecision:
        """Validate registry-level schema compatibility, not approval authority."""

        entry = self._entry_for_plan(plan)
        experiment_id = plan.get("experiment_id")
        if not isinstance(experiment_id, str):
            suite = plan.get("suite")
            experiment_id = suite.get("suite_id") if isinstance(suite, dict) else None
        if entry is None:
            return VerifierDecision(
                handled=experiment_id in self._known_experiments,
                accepted=False,
            )
        if not self._entry_accepts_plan(entry, plan):
            return VerifierDecision(True, False, entry.verifier_id)
        return VerifierDecision(
            handled=True,
            accepted=True,
            verifier_id=entry.verifier_id,
            requires_row_capability=entry.requires_row_capability,
        )

    def verify_manifest(
        self,
        *,
        plan: dict[str, Any],
        manifest: RunManifest,
        authorization_plan_path: str,
        authorization_plan_hash: str,
        repository: Path,
        runner_root: Path | None,
        batch_validation: bool = False,
    ) -> VerifierDecision:
        """Run the registered exact verifier through one common call surface."""

        experiment = manifest.experiment
        entry = self._entry_for_plan(plan)
        if entry is None:
            entry = self._entry_for_manifest_plan(manifest, plan)
        if entry is None:
            if experiment is not None and experiment.experiment_id in self._known_experiments:
                return VerifierDecision(True, False)
            return self.validate_authorization_plan(plan)
        if (
            experiment is None
            or experiment.experiment_id != entry.experiment_id
            or not self._entry_accepts_plan(entry, plan)
        ):
            return VerifierDecision(True, False, entry.verifier_id)
        if entry.requires_row_capability and not batch_validation:
            return VerifierDecision(
                True,
                False,
                entry.verifier_id,
                requires_row_capability=True,
            )
        verifier = getattr(import_module(entry.module), entry.function)
        if entry.call_shape == "rapid":
            accepted = verifier(
                plan=plan,
                manifest=manifest,
                repository=repository,
            )
        else:
            accepted = bool(
                runner_root is not None
                and verifier(
                    plan=plan,
                    manifest=manifest,
                    plan_path=authorization_plan_path,
                    plan_file_sha256=authorization_plan_hash,
                    expected_run_root=runner_root,
                )
            )
        return VerifierDecision(
            handled=True,
            accepted=bool(accepted),
            verifier_id=entry.verifier_id,
            requires_row_capability=entry.requires_row_capability,
        )


_RAPID_PURPOSE = ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value
_ENTRIES = (
    LiveVerifierEntry(
        verifier_id="rapid-r1-plan-v2",
        experiment_id="rapid-public-dev-lean-harness-20260818-r1",
        plan_schema="experiment-execution-plan-v2",
        plan_kind=None,
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development",
        function="rapid_live_plan_matches_manifest",
        call_shape="rapid",
        plan_binds_experiment_id=False,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r2-plan-v2",
        experiment_id="rapid-public-dev-lean-harness-20260821-r2",
        plan_schema="experiment-execution-plan-v2",
        plan_kind=None,
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v2",
        function="rapid_v2_live_plan_matches_manifest",
        call_shape="rapid",
        plan_binds_experiment_id=False,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r3-candidate-v3-plan-v3",
        experiment_id="rapid-public-dev-hard-panel-20260822-r3",
        plan_schema="experiment-execution-plan-v3",
        plan_kind="rapid-public-development-hard-panel-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v3",
        function="rapid_v3_live_plan_matches_manifest",
        call_shape="rapid",
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r3-candidate-v4-plan-v4",
        experiment_id="rapid-public-dev-hard-panel-20260822-r3",
        plan_schema="experiment-execution-plan-v4",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v4",
        function="rapid_v4_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r3-candidate-v5-plan-v5",
        experiment_id="rapid-public-dev-hard-panel-20260822-r3",
        plan_schema="experiment-execution-plan-v5",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v4",
        function="rapid_v4_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r3-candidate-v6-plan-v6",
        experiment_id="rapid-public-dev-hard-panel-20260822-r3",
        plan_schema="experiment-execution-plan-v6",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v4",
        function="rapid_v4_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r4-candidate-v7-plan-v7",
        experiment_id="rapid-public-dev-anyio-targeted-20260822-r4",
        plan_schema="experiment-execution-plan-v7",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v5",
        function="rapid_v5_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r5-candidate-v8-plan-v8",
        experiment_id="rapid-public-dev-anyio-finalization-20260822-r5",
        plan_schema="experiment-execution-plan-v8",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v6",
        function="rapid_v6_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r6-candidate-v9-plan-v9",
        experiment_id="rapid-public-dev-anyio-mechanical-20260823-r6",
        plan_schema="experiment-execution-plan-v9",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v7",
        function="rapid_v7_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r7-candidate-v10-plan-v10",
        experiment_id="rapid-public-dev-anyio-event-role-20260823-r7",
        plan_schema="experiment-execution-plan-v10",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v8",
        function="rapid_v8_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r8-candidate-v11-plan-v11",
        experiment_id="rapid-public-dev-anyio-completion-policy-20260823-r8",
        plan_schema="experiment-execution-plan-v11",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v9",
        function="rapid_v9_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r9-candidate-v12-plan-v12",
        experiment_id="rapid-public-dev-anyio-ordered-correction-20260824-r9",
        plan_schema="experiment-execution-plan-v12",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v10",
        function="rapid_v10_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r9-candidate-v13-plan-v13",
        experiment_id="rapid-public-dev-anyio-ordered-correction-20260824-r9",
        plan_schema="experiment-execution-plan-v13",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v11",
        function="rapid_v11_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r10-candidate-v14-plan-v14",
        experiment_id="rapid-public-dev-anyio-workflow-ab-20260824-r10",
        plan_schema="experiment-execution-plan-v14",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v12",
        function="rapid_v12_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r10-candidate-v15-plan-v15",
        experiment_id="rapid-public-dev-anyio-workflow-ab-20260824-r10",
        plan_schema="experiment-execution-plan-v15",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v12",
        function="rapid_v12_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r10-candidate-v16-plan-v16",
        experiment_id="rapid-public-dev-anyio-workflow-ab-20260824-r10",
        plan_schema="experiment-execution-plan-v16",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v12",
        function="rapid_v12_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r11-candidate-v17-plan-v17",
        experiment_id="rapid-public-dev-anyio-workflow-revision-ab-20260825-r11",
        plan_schema="experiment-execution-plan-v17",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v13",
        function="rapid_v13_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r12-candidate-v18-plan-v18",
        experiment_id="rapid-public-dev-anyio-semantic-progress-ab-20260825-r12",
        plan_schema="experiment-execution-plan-v18",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v14",
        function="rapid_v14_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r13-candidate-v19-plan-v19",
        experiment_id="rapid-public-dev-anyio-causal-activation-ab-20260826-r13",
        plan_schema="experiment-execution-plan-v19",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v15",
        function="rapid_v15_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r13-candidate-v20-plan-v20",
        experiment_id="rapid-public-dev-anyio-causal-activation-ab-20260826-r13",
        plan_schema="experiment-execution-plan-v20",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v16",
        function="rapid_v16_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r14-candidate-v21-plan-v21",
        experiment_id=("rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14"),
        plan_schema="experiment-execution-plan-v21",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v17",
        function="rapid_v17_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r15-candidate-v22-plan-v22",
        experiment_id="rapid-public-dev-anyio-v5-exploration-ab-20260827-r15",
        plan_schema="experiment-execution-plan-v22",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v18",
        function="rapid_v18_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r15-candidate-v23-plan-v23",
        experiment_id="rapid-public-dev-anyio-v5-exploration-ab-20260827-r15",
        plan_schema="experiment-execution-plan-v23",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v18",
        function="rapid_v18_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r16-candidate-v24-plan-v24",
        experiment_id="rapid-public-dev-anyio-v5-epoch-parity-ab-20260827-r16",
        plan_schema="experiment-execution-plan-v24",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v19",
        function="rapid_v19_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r17-candidate-v25-plan-v25",
        experiment_id="rapid-public-dev-anyio-v5-row-isolation-ab-20260827-r17",
        plan_schema="experiment-execution-plan-v25",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v20",
        function="rapid_v20_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r18-candidate-v26-plan-v26",
        experiment_id="rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18",
        plan_schema="experiment-execution-plan-v26",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v21",
        function="rapid_v21_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r19-candidate-v27-plan-v27",
        experiment_id="rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19",
        plan_schema="experiment-execution-plan-v27",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v22",
        function="rapid_v22_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r20-candidate-v28-plan-v28",
        experiment_id="rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20",
        plan_schema="experiment-execution-plan-v28",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v23",
        function="rapid_v23_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r21-candidate-v29-plan-v29",
        experiment_id="rapid-public-dev-anyio-v5-v25-mechanical-activation-20260830-r21",
        plan_schema="experiment-execution-plan-v29",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v24",
        function="rapid_v24_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r22-candidate-v30-plan-v30",
        experiment_id="rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22",
        plan_schema="experiment-execution-plan-v30",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v25",
        function="rapid_v25_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r23-candidate-v31-plan-v31",
        experiment_id="rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23",
        plan_schema="experiment-execution-plan-v31",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v26",
        function="rapid_v26_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    LiveVerifierEntry(
        verifier_id="rapid-r23-candidate-v32-plan-v32",
        experiment_id="rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23",
        plan_schema="experiment-execution-plan-v32",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v26",
        function="rapid_v26_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    # R24 integration begin: registry
    LiveVerifierEntry(
        verifier_id="rapid-r24-candidate-v33-plan-v33",
        experiment_id="rapid-public-dev-anyio-v5-provider-schema-ab-20260901-r24",
        plan_schema="experiment-execution-plan-v33",
        plan_kind="rapid-public-development-batch-v1",
        purpose=_RAPID_PURPOSE,
        official=False,
        module="patchloop.evals.rapid_public_development_v27",
        function="rapid_v27_registered_plan_matches_manifest",
        call_shape="rapid",
        requires_row_capability=True,
    ),
    # R24 integration end: registry
    LiveVerifierEntry(
        verifier_id="heldout-ac-plan-v1",
        experiment_id="core-ac-fixed-bundle-heldout-20260814-v1",
        plan_schema="experiment-execution-plan-v1",
        plan_kind="heldout-ac-approved-campaign-v1",
        purpose=ExperimentPurpose.CORE.value,
        official=True,
        module="patchloop.evals.heldout_ac_live_contract",
        function="heldout_ac_live_plan_matches_manifest",
        call_shape="heldout",
        plan_has_content_hash=False,
    ),
    LiveVerifierEntry(
        verifier_id="heldout-ac-plan-v2",
        experiment_id="core-ac-fixed-bundle-heldout-20260814-v1",
        plan_schema="experiment-execution-plan-v2",
        plan_kind="heldout-ac-approved-campaign-v2",
        purpose=ExperimentPurpose.CORE.value,
        official=True,
        module="patchloop.evals.heldout_ac_live_contract",
        function="heldout_ac_live_plan_matches_manifest",
        call_shape="heldout",
        plan_has_content_hash=False,
    ),
)

_REGISTRY = LiveVerifierRegistry(_ENTRIES)


def live_verifier_registry() -> LiveVerifierRegistry:
    return _REGISTRY


__all__ = [
    "LiveVerifierEntry",
    "LiveVerifierRegistry",
    "VerifierDecision",
    "live_verifier_registry",
]
