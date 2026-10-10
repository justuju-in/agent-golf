"""Agent Golf website and upload API (plan 002).

Run from the repo root: .venv/bin/uvicorn server.app:app --port 8000
"""

import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import jinja2
from fastapi import APIRouter, Depends, FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server import db, users
from server.config import Settings, load_settings

HERE = Path(__file__).resolve().parent
NO_STORE = {"Cache-Control": "no-store"}

# Autoescape on for every template, whatever its file name.
templates = Jinja2Templates(
    env=jinja2.Environment(loader=jinja2.FileSystemLoader(HERE / "templates"), autoescape=True)
)

router = APIRouter()


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """A database connection for one request."""
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
FormText = Annotated[str, Form()]


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


def register_page(
    request: Request,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """The register form, with the entered values and an error per field, if any."""
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "values": values or {"username": "", "hackattic_username": ""},
            "errors": errors or {},
        },
        status_code=status_code,
        headers=NO_STORE,
    )


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request) -> HTMLResponse:
    return register_page(request)


@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request, conn: Conn, username: FormText = "", hackattic_username: FormText = ""
) -> HTMLResponse:
    """Create the student. On success the response is the key page itself, never a
    redirect, so the key is in no URL; the key is never logged.

    A missing field defaults to "", so it gets the same inline error as an empty one.
    """
    values = {"username": username, "hackattic_username": hackattic_username}
    # Check both fields first, so a form with two mistakes shows both.
    errors = {}
    try:
        users.clean_username(username)
    except users.InvalidUsername as exc:
        errors["username"] = str(exc)
    try:
        users.clean_hackattic_username(hackattic_username)
    except users.InvalidHackatticUsername as exc:
        errors["hackattic_username"] = str(exc)
    if errors:
        return register_page(request, values, errors, status_code=400)

    try:
        key = users.create_user(conn, username, hackattic_username)
    except users.UsernameTaken as exc:
        # Also what a browser gets if the key page is reloaded and the form re-sent.
        return register_page(request, values, {"username": str(exc)}, status_code=409)
    return templates.TemplateResponse(
        request,
        "key.html",
        {"key": key, "username": users.clean_username(username)},
        headers=NO_STORE,
    )


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
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    return app


app = create_app()
