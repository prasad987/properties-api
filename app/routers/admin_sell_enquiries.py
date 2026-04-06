from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel

from ..db import get_db
from .admin import get_current_admin


class SellEnquiryCreate(BaseModel):
    name: str
    phone: str
    location: str
    message: str


class SellEnquiryResponse(BaseModel):
    id: str
    name: str | None = None
    phone: str | None = None
    location: str | None = None
    message: str | None = None
    created_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_sell_enquiries_router = APIRouter(
    prefix="/admin",
    tags=["admin-sell-enquiries"]
)

SELL_ENQUIRIES_COLLECTION = "sell_enquiries"


# ----------------------------
# POST Sell Enquiry
# ----------------------------
@admin_sell_enquiries_router.post("/sell-enquiries")
async def create_sell_enquiry(
    body: SellEnquiryCreate,
    request: Request,
) -> dict[str, str]:

    db = get_db(request)

    payload = body.model_dump()

    payload["id"] = str(uuid.uuid4())
    payload["created_at"] = datetime.now(timezone.utc)

    await db[SELL_ENQUIRIES_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# GET Sell Enquiries
# ----------------------------
@admin_sell_enquiries_router.get("/sell-enquiries", response_model=list[SellEnquiryResponse])
async def admin_sell_enquiries_list(request: Request) -> list[SellEnquiryResponse]:

    db = get_db(request)

    docs = await db[SELL_ENQUIRIES_COLLECTION].find().sort("created_at", -1).to_list(100)

    enquiries = []
    for doc in docs:
        doc.pop("_id", None)
        enquiries.append(doc)

    return enquiries





