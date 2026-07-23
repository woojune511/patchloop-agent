from __future__ import annotations

import asyncio

import httpx

from patchloop.web import app


def test_health_route() -> None:
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/healthz")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json() == {"ok": True}
