from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from poller import Poller
from ros import RouterOS
from store import SampleStore

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

ros = RouterOS(
    os.environ.get("ROS_URL", "http://10.1.1.1"),
    os.environ.get("ROS_USER", "dash"),
    os.environ.get("ROS_PASSWORD", ""),
)
store = SampleStore(ROOT / "data" / "samples.db")
poller = Poller(ros, store, wan_hint=os.environ.get("WAN_INTERFACE") or None)


@asynccontextmanager
async def lifespan(_: FastAPI):
    poller.start()
    try:
        yield
    finally:
        await poller.stop()
        await ros.close()


app = FastAPI(title="hAP 流量台", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/snapshot")
async def snapshot():
    return poller.snapshot


@app.get("/api/history")
async def history(
    iface: str | None = None,
    minutes: int = Query(default=30, ge=1, le=360),
):
    name = iface or (poller.snapshot.get("wan") or {}).get("name") or "pppoe-out1"
    since = time.time() - minutes * 60
    return {"iface": name, "points": store.history(name, since)}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        file = DIST / full_path
        if full_path and file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(DIST / "index.html")
