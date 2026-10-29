"""Shared repair guidance; no new tool, verification gate or execution authority."""

INSTRUCTIONS = """Ground repairs in public requirements or callers. Distinguish required outputs,
preserved state and success/failure conditions. Test a related failure path or option
boundary that could refute the patch, plus a normal control; group cases in one check.
Before another probe, name the still-untested condition in its question. Reuse adequate
same-diff results and observed APIs. One input does not cover other paths. No probe quota
or new completion gate.
"""
