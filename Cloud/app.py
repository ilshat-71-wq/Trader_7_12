"""HTTP/WebSocket API for the shared Trader_7_12 Cloud Market Data Engine."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PROJECT_ROOT / "Program"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROGRAM_ROOT) not in sys.path:
    sys.path.insert(0, str(PROGRAM_ROOT))


import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect

from Cloud.market_data_engine import CloudMarketDataEngine, ENGINE_VERSION


engine = CloudMarketDataEngine()
engine_task: asyncio.Task | None = None


def _authorized(token: str | None) -> bool:
    """Optional API-key gate for production deployment."""
    configured = os.getenv("CLOUD_CLIENT_API_KEY", "").strip()
    if not configured:
        return True
    return bool(token) and token == configured


def _require_api_key(authorization: str | None) -> None:
    token = None
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = value.strip()
    if not _authorized(token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global engine_task
    engine_task = asyncio.create_task(engine.run_forever())
    yield
    if engine_task:
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Trader_7_12 Cloud Market Data Engine",
    version=ENGINE_VERSION,
    description=(
        "Shared read-only market-information service. "
        "One market scan is distributed to many clients."
    ),
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "engine": ENGINE_VERSION}


@app.get("/v1/status")
async def status(authorization: str | None = Header(default=None)):
    _require_api_key(authorization)
    return engine.status


@app.get("/v1/snapshot")
async def snapshot(authorization: str | None = Header(default=None)):
    _require_api_key(authorization)
    current = engine.snapshot
    if current is None:
        raise HTTPException(status_code=503, detail="Market snapshot is not ready")
    return current.as_dict()



@app.get("/v1/morning-radar")
async def morning_radar(authorization: str | None = Header(default=None)):
    _require_api_key(authorization)
    return engine.morning_radar.summary()


@app.post("/v1/scan")
async def force_scan(authorization: str | None = Header(default=None)):
    _require_api_key(authorization)
    try:
        current = await asyncio.to_thread(engine.scan_once)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Market scan failed: {type(exc).__name__}: {exc}",
        ) from exc
    return current.as_dict()


@app.websocket("/v1/stream")
async def stream(websocket: WebSocket):
    configured = os.getenv("CLOUD_CLIENT_API_KEY", "").strip()
    if configured:
        auth = websocket.headers.get("authorization", "")
        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "bearer" or value.strip() != configured:
            await websocket.close(code=1008, reason="Unauthorized")
            return

    await websocket.accept()
    queue = engine.subscribe()
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe(queue)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "cloud.app:app",
        host=os.getenv("CLOUD_HOST", "0.0.0.0"),
        port=int(os.getenv("CLOUD_PORT", "8080")),
        reload=False,
    )
