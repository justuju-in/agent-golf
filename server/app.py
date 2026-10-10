"""Agent Golf website and upload API (plan 002).

Run from the repo root: .venv/bin/uvicorn server.app:app --port 8000
"""

import logging
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import jinja2
from fastapi import APIRouter, Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from server import board, db, pages, problems, submissions, users
from server.config import Settings, load_settings

HERE = Path(__file__).resolve().parent
NO_STORE = {"Cache-Control": "no-store"}

# python-multipart warns with bytes quoted from a malformed upload; uploads stay out of logs.
logging.getLogger("python_multipart").setLevel(logging.ERROR)

# Autoescape on for every template, whatever its file name.
templates = Jinja2Templates(
    env=jinja2.Environment(loader=jinja2.FileSystemLoader(HERE / "templates"), autoescape=True)
)
templates.env.globals["pages"] = pages  # the pages' text helpers

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


@router.get("/api/v1/problems")
def list_problems() -> Response:
    """docs/spec.md, "Contract: problem list": public, no key. The bytes are the ones
    problems.check() measured when the app started."""
    return Response(problems.problem_list_json(), media_type="application/json")


def rejected(reason: str) -> JSONResponse:
    """A rejected upload's reply (docs/spec.md, "Contract: website → plugin")."""
    headers = {**NO_STORE, "WWW-Authenticate": "Bearer"} if reason == "bad_key" else NO_STORE
    return JSONResponse(
        submissions.rejection(reason),
        status_code=submissions.REJECTION_STATUS[reason],
        headers=headers,
    )


@router.post("/api/v1/submissions")
async def submit(request: Request, conn: Conn) -> JSONResponse:
    """docs/spec.md, "Contract: plugin → website". Checks in this order: key, problem,
    then the session (missing, too large, not UTF-8, not a Pi log), then the counter.

    No FastAPI form or header parameters: the form is parsed here, after the key check,
    so a bad request gets the spec's 400, never FastAPI's 422. Never log the key or the upload.
    """
    user = users.user_for_authorization(conn, request.headers.get("authorization"))
    if user is None:
        return rejected("bad_key")
    try:
        form = await request.form()
    except StarletteHTTPException:
        # Unreadable multipart (broken framing, or a plain field over Starlette's 1 MB cap).
        return rejected("not_pi_log")
    try:
        problem = problems.get(form.get("problem"))
        if problem is None:
            return rejected("unknown_problem")
        # `session` must be a file part. Count the bytes read, one past the limit, rather
        # than trust any size header.
        session = form.get("session")
        if not isinstance(session, UploadFile):
            return rejected("not_pi_log")
        data = await session.read(submissions.MAX_SESSION_BYTES + 1)
        if len(data) > submissions.MAX_SESSION_BYTES:
            return rejected("file_too_large")
        # Stored as sent; anything but "true" or "false" counts as not sent.
        flag = form.get("folder_was_empty")
        folder_was_empty = {"true": True, "false": False}.get(flag) if isinstance(flag, str) else None
        # Hashing, scoring and storing block, so off the event loop.
        body = await run_in_threadpool(
            submissions.submit, conn, request.app.state.settings, user["id"], problem, data, folder_was_empty
        )
    except submissions.Rejected as exc:
        return rejected(exc.reason)
    except submissions.CounterFailed:
        return JSONResponse({"error": "server_error"}, status_code=500, headers=NO_STORE)
    finally:
        await form.close()
    return JSONResponse(body, headers=NO_STORE)


def not_found(request: Request) -> HTMLResponse:
    """The 404 page, for a problem or submission that does not exist."""
    return templates.TemplateResponse(request, "not_found.html", status_code=404)


def board_page(request: Request, conn: sqlite3.Connection, problem: problems.Problem | None) -> HTMLResponse:
    """A problem's board, with links to the other listed problems' boards; without a
    problem, a page saying none is open yet."""
    context: dict = {"problem": problem}
    if problem is not None:
        context.update(
            board=board.board(conn, problem.slug),
            # docs/spec.md: the board of a model-"any" problem shows each row's model.
            show_model=problem.model == "any",
            others=[other for other in problems.listed() if other.slug != problem.slug],
            now=pages.now(),
        )
    return templates.TemplateResponse(request, "board.html", context)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, conn: Conn) -> HTMLResponse:
    """The first listed problem's board."""
    listed = problems.listed()
    return board_page(request, conn, listed[0] if listed else None)


@router.get("/problems/{slug}", response_class=HTMLResponse)
def problem_board(request: Request, slug: str, conn: Conn) -> HTMLResponse:
    problem = problems.get(slug)
    if problem is None:
        return not_found(request)
    return board_page(request, conn, problem)


@router.get("/submissions/{submission_id:int}")
def submission(submission_id: int, conn: Conn) -> JSONResponse:
    """The link in upload replies. Until step 3.2's page: the public fields as JSON."""
    found = submissions.public(conn, submission_id)
    if found is None:
        raise HTTPException(status_code=404)
    return JSONResponse(found)


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
    """The app; tests pass their own settings (e.g. a temporary data directory).

    Raises problems.InvalidConfig, so the server does not start, if the problem config
    breaks a limit of the problem list.
    """
    problems.check()
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
