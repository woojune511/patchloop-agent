"""Shared repair guidance; no new tool, verification gate or execution authority."""

INSTRUCTIONS = """For any mutation, ground intended and preserved behavior in public requirements
or callers.
Trace changed returns, conditions or state updates through related paths and boundaries.
Choose a small check that could refute the repair and a relevant normal control; observe
required results and preserved state, not only absence of errors. Reuse evidence and
group useful cases within budget. This adds no fixed probe count or completion gate.
"""
