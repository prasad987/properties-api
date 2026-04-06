from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, EmailStr

from ..db import get_db
from .admin import get_current_admin


class ContactEnquiryCreate(BaseModel):
    property_id: str | None = None
    name: str
    email: EmailStr
    phone: str
    message: str


class ContactEnquiryResponse(BaseModel):
    id: str
    property_id: str | None = None
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    message: str | None = None
    created_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_contact_enquiries_router = APIRouter(
    prefix="/admin",
    tags=["admin-contact-enquiries"]
)

CONTACT_ENQUIRIES_COLLECTION = "contact_enquiries"


# ----------------------------
# POST Contact Enquiry
# ----------------------------
@admin_contact_enquiries_router.post("/contact-enquiries")
async def create_contact_enquiry(
    body: ContactEnquiryCreate,
    request: Request,
) -> dict[str, str]:

    db = get_db(request)

    payload = body.model_dump()

    payload["id"] = str(uuid.uuid4())
    payload["created_at"] = datetime.now(timezone.utc)

    await db[CONTACT_ENQUIRIES_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# GET Contact Enquiries
# ----------------------------
@admin_contact_enquiries_router.get("/contact-enquiries", response_model=list[ContactEnquiryResponse])
async def admin_contact_enquiries_list(request: Request) -> list[ContactEnquiryResponse]:

    db = get_db(request)

    docs = await db[CONTACT_ENQUIRIES_COLLECTION].find().sort("created_at", -1).to_list(100)

    enquiries = []
    for doc in docs:
        doc.pop("_id", None)
        enquiries.append(doc)

    return enquiries





