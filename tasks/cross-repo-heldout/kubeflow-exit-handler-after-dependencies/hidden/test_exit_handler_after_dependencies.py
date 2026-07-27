import os
from pathlib import Path

import pytest

import kfp
from kfp import dsl
from kfp.compiler import compiler_utils
from kfp.dsl import PipelineTaskFinalStatus
from kfp.dsl import pipeline_task


@dsl.component
def _oracle_seed() -> str:
    return "seed"


@dsl.component
def _oracle_work(value: str = "work") -> str:
    return value


@dsl.component
def _oracle_cleanup() -> None:
    print("cleanup")


@dsl.component
def _oracle_sink() -> None:
    print("sink")


@dsl.component
def _oracle_status(status: PipelineTaskFinalStatus) -> None:
    print(status)


def _root_task(pipeline, task_name: str):
    return pipeline.pipeline_spec.root.dag.tasks[task_name]


def test_oracle_imports_submitted_kfp_copy() -> None:
    expected_root = Path(os.environ["PATCHLOOP_SUBMITTED_KFP"]).resolve()
    imported = (
        Path(kfp.__file__).resolve(),
        Path(compiler_utils.__file__).resolve(),
        Path(pipeline_task.__file__).resolve(),
    )

    assert all(path.is_relative_to(expected_root) for path in imported), imported


def test_after_records_exit_handler_group_name() -> None:
    observed: dict[str, object] = {}

    @dsl.pipeline(name="oracle-record-exit-group")
    def pipeline():
        cleanup = _oracle_cleanup()
        with dsl.ExitHandler(cleanup) as completed:
            _oracle_work()
        downstream = _oracle_sink()
        downstream.after(completed)
        observed["group"] = completed.name
        observed["recorded"] = list(downstream.dependent_tasks)

    assert observed["recorded"] == [observed["group"]]
    assert pipeline.pipeline_spec.root.dag.tasks


def test_compiler_depends_on_group_not_cleanup_task() -> None:
    observed: dict[str, str] = {}

    @dsl.pipeline(name="oracle-group-boundary")
    def pipeline():
        cleanup = _oracle_cleanup()
        observed["cleanup"] = cleanup.name
        with dsl.ExitHandler(cleanup) as completed:
            _oracle_work(value="inside")
        downstream = _oracle_sink().after(completed)
        observed["group"] = completed.name
        observed["downstream"] = downstream.name

    dependencies = list(
        _root_task(pipeline, observed["downstream"]).dependent_tasks
    )
    assert dependencies == [observed["group"]]
    assert observed["cleanup"] not in dependencies


def test_mixed_task_and_group_dependencies_are_preserved() -> None:
    observed: dict[str, str] = {}

    @dsl.pipeline(name="oracle-mixed-dependencies")
    def pipeline():
        ordinary = _oracle_seed()
        cleanup = _oracle_cleanup()
        with dsl.ExitHandler(cleanup) as completed:
            _oracle_work(value="inside")
        downstream = _oracle_sink().after(ordinary, completed)
        observed["ordinary"] = ordinary.name
        observed["group"] = completed.name
        observed["downstream"] = downstream.name

    dependencies = set(
        _root_task(pipeline, observed["downstream"]).dependent_tasks
    )
    assert dependencies == {observed["ordinary"], observed["group"]}


def test_two_completed_groups_keep_requested_order() -> None:
    observed: dict[str, str] = {}

    @dsl.pipeline(name="oracle-ordered-exit-groups")
    def pipeline():
        first_cleanup = _oracle_cleanup()
        with dsl.ExitHandler(first_cleanup) as first_completed:
            _oracle_work(value="phase-one")

        bridge = _oracle_work(value="bridge").after(first_completed)

        second_cleanup = _oracle_cleanup()
        with dsl.ExitHandler(second_cleanup) as second_completed:
            _oracle_work(value="phase-two").after(bridge)

        final = _oracle_sink().after(second_completed)
        observed["first_group"] = first_completed.name
        observed["bridge"] = bridge.name
        observed["second_group"] = second_completed.name
        observed["final"] = final.name

    assert list(_root_task(pipeline, observed["bridge"]).dependent_tasks) == [
        observed["first_group"]
    ]
    assert list(
        _root_task(pipeline, observed["second_group"]).dependent_tasks
    ) == [observed["bridge"]]
    assert list(_root_task(pipeline, observed["final"]).dependent_tasks) == [
        observed["second_group"]
    ]


def test_non_exit_group_rejected_before_dependency_mutation() -> None:
    observed: dict[str, pipeline_task.PipelineTask] = {}

    with pytest.raises(ValueError, match=r"dsl\.If is not supported"):

        @dsl.pipeline(name="oracle-reject-if-group")
        def pipeline(mode: str = "run"):
            with dsl.If(mode == "run") as conditional:
                _oracle_work(value="conditional")
            downstream = _oracle_sink()
            observed["downstream"] = downstream
            downstream.after(conditional)

    downstream = observed["downstream"]
    assert downstream._task_spec.dependent_tasks == []
    assert downstream._run_after == []


def test_arbitrary_dependency_rejected_before_dependency_mutation() -> None:
    observed: dict[str, pipeline_task.PipelineTask] = {}

    with pytest.raises(
        ValueError,
        match=r"only supports PipelineTask and dsl\.ExitHandler dependencies",
    ):

        @dsl.pipeline(name="oracle-reject-object")
        def pipeline():
            downstream = _oracle_sink()
            observed["downstream"] = downstream
            downstream.after("not-a-task")

    downstream = observed["downstream"]
    assert downstream._task_spec.dependent_tasks == []
    assert downstream._run_after == []


def test_unknown_recorded_dependency_has_clear_error() -> None:
    with pytest.raises(
        ValueError,
        match=r'Dependency "missing-from-pipeline" does not exist',
    ):

        @dsl.pipeline(name="oracle-reject-missing-name")
        def pipeline():
            downstream = _oracle_sink()
            downstream._task_spec.dependent_tasks.append(
                "missing-from-pipeline"
            )


def test_ambiguous_task_and_group_name_has_clear_error() -> None:
    @dsl.component
    def exit_handler_1() -> None:
        print("name collision")

    with pytest.raises(ValueError, match=r'Ambiguous dependency name "exit-handler-1"'):

        @dsl.pipeline(name="oracle-reject-name-collision")
        def pipeline():
            exit_handler_1()
            cleanup = _oracle_cleanup()
            with dsl.ExitHandler(cleanup) as completed:
                _oracle_work(value="inside")
            _oracle_sink().after(completed)


def test_inner_task_dependency_remains_illegal_after_group_exit() -> None:
    with pytest.raises(
        compiler_utils.InvalidTopologyException,
        match=r"uncommon dsl\.ExitHandler context",
    ):

        @dsl.pipeline(name="oracle-reject-inner-task")
        def pipeline():
            cleanup = _oracle_cleanup()
            with dsl.ExitHandler(cleanup):
                inner = _oracle_work(value="inside")
            _oracle_sink().after(inner)


def test_final_status_is_produced_by_depended_on_exit_group() -> None:
    observed: dict[str, str] = {}

    @dsl.pipeline(name="oracle-exit-group-final-status")
    def pipeline():
        cleanup = _oracle_cleanup()
        with dsl.ExitHandler(cleanup) as completed:
            _oracle_work(value="inside")
        reporter = _oracle_status().after(completed).ignore_upstream_failure()
        observed["group"] = completed.name
        observed["reporter"] = reporter.name

    reporter_spec = _root_task(pipeline, observed["reporter"])
    assert list(reporter_spec.dependent_tasks) == [observed["group"]]
    assert (
        reporter_spec.inputs.parameters["status"].task_final_status.producer_task
        == observed["group"]
    )
    assert reporter_spec.trigger_policy.strategy == 2
