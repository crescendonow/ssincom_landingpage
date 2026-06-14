from __future__ import annotations

import logging
from hmac import compare_digest
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .database import db
from .emailer import send_contact_email
from .schemas import ContactRequest, ContactResponse, PdGroup


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect(settings)
    try:
        yield
    finally:
        await db.disconnect()


app = FastAPI(title="S&S Incom Landing Page", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=60 * 60 * 2,
)


def _current_user(request: Request) -> dict[str, str] | None:
    user = request.session.get("user")
    return user if isinstance(user, dict) else None


def _is_safe_next(next_path: str | None) -> bool:
    return bool(next_path and next_path.startswith("/") and not next_path.startswith("//"))


def _safe_next(next_path: str | None, default: str = "/frontend/") -> str:
    return next_path if _is_safe_next(next_path) else default


def _login_redirect(next_path: str) -> RedirectResponse:
    return RedirectResponse(url=f"/login?next={quote(next_path)}", status_code=303)


def _require_dashboard_user(request: Request) -> JSONResponse | None:
    if _current_user(request):
        return None
    return JSONResponse(content={"detail": "Not authenticated"}, status_code=401)


@app.get("/api/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/", include_in_schema=False)
async def frontend_root() -> RedirectResponse:
    return RedirectResponse(url="/frontend/")


@app.get("/frontend", include_in_schema=False)
async def frontend_without_slash() -> RedirectResponse:
    return RedirectResponse(url="/frontend/")


@app.get("/frontend/", include_in_schema=False)
async def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/login", include_in_schema=False)
async def login_page(request: Request) -> Response:
    next_path = _safe_next(request.query_params.get("next"), "/frontend/")
    if _current_user(request):
        return RedirectResponse(url=next_path, status_code=303)
    return FileResponse(FRONTEND_DIR / "login.html")


@app.post("/login", include_in_schema=False)
async def do_login(request: Request) -> RedirectResponse:
    form = await request.form()
    username = str(form.get("username") or "")
    password = str(form.get("password") or "")
    next_path = _safe_next(str(form.get("next") or ""), "/frontend/")

    valid_user = compare_digest(username, settings.app_user)
    valid_pass = compare_digest(password, settings.app_pass)
    if valid_user and valid_pass:
        request.session["user"] = {"name": username}
        return RedirectResponse(url=next_path, status_code=303)

    return RedirectResponse(url=f"/login?error=1&next={quote(next_path)}", status_code=303)


@app.get("/logout", include_in_schema=False)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url=_safe_next(request.query_params.get("next"), "/frontend/"), status_code=303)


@app.get("/api/auth/me", include_in_schema=False)
async def auth_me(request: Request) -> dict[str, object]:
    user = _current_user(request)
    return {"authenticated": bool(user), "user": user}


@app.get("/frontend/dashboard_sand.html", include_in_schema=False)
async def dashboard_sand(request: Request) -> Response:
    if not _current_user(request):
        return _login_redirect("/frontend/dashboard_sand.html")
    return FileResponse(FRONTEND_DIR / "dashboard_sand.html")


@app.get("/api/pdgroups", response_model=list[PdGroup])
async def list_pdgroups() -> list[dict[str, object]]:
    async with db.connection() as conn:
        rows = await conn.fetch(
            """
            SELECT pdgroup_id, pdgroup_name
            FROM quotation.pdgroup
            ORDER BY pdgroup_id
            """
        )
    return [dict(row) for row in rows]


@app.post("/api/contact", response_model=ContactResponse)
async def create_contact(contact: ContactRequest) -> ContactResponse:
    pdgroup_name: str | None = None

    async with db.connection() as conn:
        async with conn.transaction():
            if contact.pdgroup_id is not None:
                pdgroup_name = await conn.fetchval(
                    """
                    SELECT pdgroup_name
                    FROM quotation.pdgroup
                    WHERE pdgroup_id = $1
                    """,
                    contact.pdgroup_id,
                )
                if pdgroup_name is None:
                    raise HTTPException(status_code=422, detail="Invalid pdgroup_id")

            idx = await conn.fetchval(
                """
                INSERT INTO quotation.contact_customer (
                    person_name,
                    org_name,
                    tel,
                    email,
                    pdgroup_id,
                    req_size,
                    address_send,
                    detail
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING idx
                """,
                contact.person_name.strip(),
                contact.org_name,
                contact.tel.strip(),
                str(contact.email) if contact.email else None,
                contact.pdgroup_id,
                contact.req_size,
                contact.address_send,
                contact.detail,
            )

    email_sent = await send_contact_email(settings, contact, idx, pdgroup_name)
    return ContactResponse(ok=True, idx=idx, email_sent=email_sent)


@app.get("/api/dashboard/saletax_summary", include_in_schema=False)
async def proxy_saletax_summary(request: Request) -> JSONResponse:
    auth_error = _require_dashboard_user(request)
    if auth_error:
        return auth_error

    url = f"{settings.bill_base_url}/api/saletax/summary"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=dict(request.query_params))
    return JSONResponse(content=r.json(), status_code=r.status_code)


@app.get("/api/dashboard/saletax_list", include_in_schema=False)
async def proxy_saletax_list(request: Request) -> JSONResponse:
    auth_error = _require_dashboard_user(request)
    if auth_error:
        return auth_error

    url = f"{settings.bill_base_url}/api/saletax/list"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=dict(request.query_params))
    return JSONResponse(content=r.json(), status_code=r.status_code)


app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
