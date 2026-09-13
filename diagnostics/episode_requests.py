"""Diagnostic compatibility exports for the shared bounded request transport."""
from __future__ import annotations

from types import SimpleNamespace

from patchloop.agent.model import ModelTurn, OpenAIResponsesAdapter
from patchloop.agent.request_transport import (
    PHASES as PHASES,
)
from patchloop.agent.request_transport import (
    WAITS as WAITS,
)
from patchloop.agent.request_transport import (
    BoundedResponsesClient,
)
from patchloop.agent.request_transport import (
    RequestWaitExpired as RequestWaitExpired,
)
from patchloop.agent.request_transport import (
    RequestWaits as RequestWaits,
)
from patchloop.agent.request_transport import (
    exception_evidence as exception_evidence,
)

DiagnosticClient = BoundedResponsesClient

def recovered_usage(adapter, requested_input_tokens):
    """Salvage only the existing parser's usage fields, never malformed output text.

    The normal dispatcher must still validate count/model/status and settle cost.
    No second request is made. If even usage cannot be parsed it remains unknown.
    """
    response = getattr(adapter.client, "received_response", None)
    if response is None:
        return None
    try:
        usage_response = SimpleNamespace(
            usage=response.usage, id=response.id, model=response.model,
            status=response.status, output=[],
        )
        parser = OpenAIResponsesAdapter(
            adapter.config, api_key="",
            client=SimpleNamespace(max_retries=0, responses=SimpleNamespace(
                create=lambda **_: usage_response)),
        )
        turn = parser.execute_request({}, requested_input_tokens=requested_input_tokens)
        return turn if isinstance(turn, ModelTurn) else None
    except Exception:
        return None
