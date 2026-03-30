# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""FastAPI application for SoccerHype web UI."""

from __future__ import annotations

import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from web.routes import athletes, clips, render

WEB_DIR = pathlib.Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

app = FastAPI(title="SoccerHype", docs_url="/api/docs")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routers
app.include_router(athletes.router, prefix="/api")
app.include_router(clips.router, prefix="/api")
app.include_router(render.router, prefix="/api")


@app.get("/")
async def serve_index():
    """Serve the SPA shell at root."""
    return FileResponse(str(TEMPLATES_DIR / "index.html"))


@app.get("/project/{rest:path}")
async def serve_spa_project(rest: str = ""):
    """Serve the SPA shell for project routes."""
    return FileResponse(str(TEMPLATES_DIR / "index.html"))
