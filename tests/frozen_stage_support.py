"""Synthetic controls for closed experiments predating dedicated stage prompts.

This does not switch production defaults or rewrite a historical artifact. Tests
of the current runner and stage projections use the real stage policies.
"""

from patchloop.dev import completion_context, repair_context


def pin_pre_stage_prompt(monkeypatch):
    monkeypatch.setattr(repair_context, "pending", lambda _: False)
    monkeypatch.setattr(completion_context, "active", lambda _: False)
