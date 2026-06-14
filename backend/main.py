from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

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
    url = f"{settings.bill_base_url}/api/saletax/summary"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=dict(request.query_params))
    return JSONResponse(content=r.json(), status_code=r.status_code)


@app.get("/api/dashboard/saletax_list", include_in_schema=False)
async def proxy_saletax_list(request: Request) -> JSONResponse:
    url = f"{settings.bill_base_url}/api/saletax/list"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=dict(request.query_params))
    return JSONResponse(content=r.json(), status_code=r.status_code)


app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
