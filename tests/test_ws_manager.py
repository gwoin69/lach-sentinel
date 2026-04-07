import pytest
from unittest.mock import AsyncMock
from backend.ws.manager import WebSocketManager


@pytest.mark.asyncio
async def test_connect_and_broadcast():
    manager = WebSocketManager()
    ws = AsyncMock()
    await manager.connect(ws)
    assert ws in manager.active_connections
    await manager.broadcast({"type": "metrics_update", "data": {"cpu": 23}})
    ws.send_json.assert_called_once_with({"type": "metrics_update", "data": {"cpu": 23}})


@pytest.mark.asyncio
async def test_disconnect_removes_client():
    manager = WebSocketManager()
    ws = AsyncMock()
    await manager.connect(ws)
    manager.disconnect(ws)
    assert ws not in manager.active_connections


@pytest.mark.asyncio
async def test_broadcast_skips_failed_clients():
    manager = WebSocketManager()
    good_ws = AsyncMock()
    bad_ws = AsyncMock()
    bad_ws.send_json = AsyncMock(side_effect=Exception("disconnected"))
    await manager.connect(good_ws)
    await manager.connect(bad_ws)
    await manager.broadcast({"type": "ping"})  # ne doit pas lever d'exception
    good_ws.send_json.assert_called_once()
