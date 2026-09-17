"""SECURE OFFLINE FOREST PATROL — FastAPI backend.

Central verification and persistence layer for the forest patrol system:

    FIELD NODE -> LoRa -> GATEWAY -> Wi-Fi/GSM -> FASTAPI -> POSTGRESQL -> DASHBOARD

The backend is deliberately NOT assumed to be connected to LoRa: the Gateway
bridges the field radio network to IP and calls these HTTP routes. Every route
here therefore deals in HTTP requests, never raw RF.

Standard FastAPI OpenAPI support stays available at ``/docs``, ``/redoc`` and
``/openapi.json``. There is no custom in-application documentation portal and
no "about" product endpoint: this is an operational platform, and project
documentation lives in ``SECURE-FOREST-PATROL/docs/``.

There is NO authentication layer on this backend. See ``docs/BACKEND.md``
for the rationale and the deployment consequence.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    forest_acoustic_api,
    forest_checkpoints,
    forest_ingest,
    forest_ledger,
    forest_nodes,
    forest_patrol_api,
    forest_status,
    forest_ws,
)
from app.core.config import get_cors_origins
from app.services.errors import ResourceConflictError, ResourceNotFoundError
from app.services.mqtt_consumer import consumer as mqtt_consumer
from app.services.ws_manager import manager as ws_manager

DESCRIPTION = """
Centralised verification and persistence for offline forest patrols.

**Ingestion path (Gateway -> backend over Wi-Fi):**

* MQTT `forest/events/patrol`, `forest/events/acoustic`,
  `forest/events/node-status`, `forest/events/sync` — primary transport,
  see `docs/MQTT.md`
* `POST /api/ingest/gateway/forest-event` — HTTP fallback/management path
* `POST /api/ingest/gateway/acoustic-event` — HTTP fallback/management path
* `POST /api/ingest/gateway/status` — HTTP fallback/management path

Both transports call the same verification/persistence services — there is
no duplicated business logic between them.

**Verification performed on every event:**

* ECC secp256r1 signature verification against the node's registered public key
* hash-chain linkage check against the node's previous record hash
* duplicate detection on (node_id, sequence) for LoRa/gateway retries

**Query surface consumed by the dashboard:**

* `/api/forest/nodes`, `/api/forest/checkpoints`, `/api/forest/officers`
* `/api/forest/patrols`, `/api/forest/acoustic-events`
* `/api/forest/ledger`, `/api/forest/gateways`, `/api/forest/sync-history`
* `/api/forest/system-status`

**Live updates:** `WS /ws` — see `docs/WEBSOCKET.md`. PostgreSQL via the
REST routes above remains the source of truth; the socket only notifies.
"""

@asynccontextmanager
async def lifespan(_: FastAPI):
    loop = asyncio.get_running_loop()
    ws_manager.bind_loop(loop)
    mqtt_consumer.start(loop)
    try:
        yield
    finally:
        mqtt_consumer.stop()


app = FastAPI(
    title="Secure Offline Forest Patrol API",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

_origins = get_cors_origins()
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(ResourceNotFoundError)
async def _not_found_handler(_: Request, exc: ResourceNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ResourceConflictError)
async def _conflict_handler(_: Request, exc: ResourceConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe. Reports process health only -- it makes no DB claims."""
    return {"status": "healthy"}


# Ingestion (Gateway -> backend, HTTP fallback/management path)
app.include_router(forest_ingest.router)

# Forest operations / dashboard surface
app.include_router(forest_nodes.router)
app.include_router(forest_checkpoints.router)
app.include_router(forest_patrol_api.router)
app.include_router(forest_acoustic_api.router)
app.include_router(forest_ledger.router)
app.include_router(forest_status.router)

# Backend -> Dashboard live updates
app.include_router(forest_ws.router)
