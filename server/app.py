"""Agent Golf website and upload API (plan 002).

Run from the repo root: .venv/bin/uvicorn server.app:app --port 8000
"""

import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from server import db, users
from server.config import Settings, load_settings

NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter()


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """A database connection for one request."""
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


@router.get("/api/v1/me")
def me(conn: Conn, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
    """docs/spec.md, "Contract: student key validation". Never echo or log the key."""
    user = users.user_for_authorization(conn, authorization)
    if user is None:
        return JSONResponse(
            {"error": "bad_key"},
            status_code=401,
            headers={**NO_STORE, "WWW-Authenticate": "Bearer"},
        )
    return JSONResponse({"username": user["username"]}, headers=NO_STORE)


def create_app(settings: Settings | None = None) -> FastAPI:
    """The app; tests pass their own settings (e.g. a temporary data directory)."""
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # At startup, not import, so importing this module never touches the disk.
        db.init_db(settings.db_path)
        yield

    app = FastAPI(title="Agent Golf", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)
    return app


app = create_app()
