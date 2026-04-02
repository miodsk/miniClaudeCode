from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.chat import api_router

app = FastAPI(title="Live2D Lead Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

public_dir = Path(__file__).resolve().parents[1] / "public"
app.mount("/assets", StaticFiles(directory=public_dir), name="assets")
app.include_router(api_router, prefix="/api")


__all__ = ["app"]
