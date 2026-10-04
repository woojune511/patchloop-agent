"""Executed as inline Python inside the existing check sandbox, not on the host.

Reports observations only. Repository pytest hooks remain untrusted test code;
this report is not a correctness oracle or a tamper-resistant attestation.
"""

import json
from pathlib import Path

import pytest


class Reporter:
    def __init__(self, selectors, working_directory):
        self.selectors = selectors
        self.working_directory = working_directory
        self.items = {}
        self.collection_errors = []
        self.collection_skips = []
        self.collected = 0
        self.summary = {key: 0 for key in ("passed", "failed", "skipped", "errors", "xfail_xpass")}

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.append(str(report.longrepr)[:2000])
        elif report.skipped:
            self.collection_skips.append(str(report.longrepr)[:2000])

    def pytest_collection_finish(self, session):
        self.collected = len(session.items)
        for item in session.items:
            relative = Path(item.path).resolve().relative_to(Path.cwd().resolve()).as_posix()
            path = (
                relative
                if self.working_directory == "."
                else self.working_directory + "/" + relative
            )
            for selector in self.selectors:
                if (
                    path != selector["path"]
                    or getattr(item, "originalname", None) != selector["function"]
                ):
                    continue
                indices = selector["indices"]
                if indices is not None and not all(
                    getattr(item, "callspec", None) is not None
                    and item.callspec.indices.get(name) in indices
                    for name in selector["parameter_names"]
                ):
                    continue
                self.items[item.nodeid] = {
                    "nodeid": item.nodeid,
                    "path": path,
                    "function": selector["function"],
                    "xfail_marked": item.get_closest_marker("xfail") is not None,
                    "phases": [],
                    "parameter_index": (
                        item.callspec.indices[selector["parameter_names"][0]]
                        if indices is not None
                        else None
                    ),
                }

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = (yield).get_result()
        if getattr(report, "wasxfail", None) is not None:
            self.summary["xfail_xpass"] += 1
        elif report.skipped:
            self.summary["skipped"] += 1
        elif report.failed:
            self.summary["failed" if report.when == "call" else "errors"] += 1
        elif report.when == "call" and report.passed:
            self.summary["passed"] += 1
        if item.nodeid in self.items:
            exception = None
            if call.excinfo is not None:
                cls = call.excinfo.type
                exception = cls.__module__ + "." + cls.__name__
            self.items[item.nodeid]["phases"].append(
                {
                    "when": report.when,
                    "outcome": report.outcome,
                    "exception_type": exception,
                    "wasxfail": getattr(report, "wasxfail", None),
                    "detail": str(report.longrepr)[:2000] if report.longrepr else None,
                }
            )


def main(args, selectors, working_directory, marker):
    reporter = Reporter(selectors, working_directory)
    code = pytest.main(args, plugins=[reporter])
    print(
        "\n"
        + marker
        + json.dumps(
            {
                "exit_code": int(code),
                "collected": reporter.collected,
                "collection_errors": reporter.collection_errors,
                "collection_skips": reporter.collection_skips,
                "summary": reporter.summary,
                "tests": list(reporter.items.values()),
            }
        )
    )
    raise SystemExit(code)
