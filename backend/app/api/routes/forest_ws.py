"""Backend -> Dashboard live-update WebSocket.

No authentication, consistent with the rest of this backend (see
``app/main.py``). See ``docs/WEBSOCKET.md`` for the event catalogue and the
reconnect/resync contract the dashboard must follow.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def forest_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # The dashboard does not send commands over this socket; we only
            # need to keep the connection alive and notice disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
