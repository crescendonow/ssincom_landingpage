from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class PdGroup(BaseModel):
    pdgroup_id: int
    pdgroup_name: Optional[str] = None


class ContactRequest(BaseModel):
    person_name: str = Field(min_length=1, max_length=400)
    org_name: Optional[str] = Field(default=None, max_length=400)
    tel: str = Field(min_length=1, max_length=30)
    email: Optional[EmailStr] = Field(default=None, max_length=100)
    pdgroup_id: Optional[int] = None
    req_size: Optional[str] = Field(default=None, max_length=500)
    address_send: Optional[str] = Field(default=None, max_length=500)
    detail: Optional[str] = None


class ContactResponse(BaseModel):
    ok: bool
    idx: int
    email_sent: bool
