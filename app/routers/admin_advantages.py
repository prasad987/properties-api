from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel

from ..db import get_db
from .admin import get_current_admin


class AdminAdvantageCreateUpdate(BaseModel):
    icon_name: str
    title: str
    description: str
    color_class: str
    icon_color_class: str
    sort_order: int
    active: bool


class AdminAdvantageToggleRequest(BaseModel):
    active: bool


class AdminAdvantageResponse(BaseModel):
    id: str
    icon_name: str | None = None
    title: str | None = None
    description: str | None = None
    color_class: str | None = None
    icon_color_class: str | None = None
    sort_order: int | None = None
    active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_advantages_router = APIRouter(
    prefix="/admin",
    tags=["admin-advantages"]
)

ADVANTAGES_COLLECTION = "advantages"


# ----------------------------
# GET Advantages
# ----------------------------
@admin_advantages_router.get("/advantages", response_model=list[AdminAdvantageResponse])
async def admin_advantages_list(request: Request) -> list[AdminAdvantageResponse]:

    db = get_db(request)

    docs = await db[ADVANTAGES_COLLECTION].find().sort("sort_order", 1).to_list(100)

    advantages = []
    for doc in docs:
        doc.pop("_id", None)
        advantages.append(doc)

    return advantages


# ----------------------------
# POST Create advantage
# ----------------------------
@admin_advantages_router.post("/advantages", dependencies=[Depends(get_current_admin)])
async def admin_advantages_create(
    body: AdminAdvantageCreateUpdate,
    request: Request,
) -> dict[str, str]:

    db = get_db(request)

    now = datetime.now(timezone.utc)

    payload = body.model_dump()

    payload["id"] = str(uuid.uuid4())
    payload["created_at"] = now
    payload["updated_at"] = now

    await db[ADVANTAGES_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# PUT Update advantage
# ----------------------------
@admin_advantages_router.put("/advantages/{advantage_id}", dependencies=[Depends(get_current_admin)])
async def admin_advantages_update(
    body: AdminAdvantageCreateUpdate,
    request: Request,
    advantage_id: str = Path(...),
) -> dict[str, str]:

    db = get_db(request)

    payload = body.model_dump()

    payload["updated_at"] = datetime.now(timezone.utc)

    res = await db[ADVANTAGES_COLLECTION].update_one(
        {"id": advantage_id},
        {"$set": payload},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Advantage not found")

    return {"id": advantage_id}


# ----------------------------
# PATCH Toggle active
# ----------------------------
@admin_advantages_router.patch(
    "/advantages/{advantage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_advantages_toggle(
    request: Request,
    body: AdminAdvantageToggleRequest = Body(...),
    advantage_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[ADVANTAGES_COLLECTION].update_one(
        {"id": advantage_id},
        {
            "$set": {
                "active": body.active,
                "updated_at": datetime.now(timezone.utc),
            }
        }
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Advantage not found")


# ----------------------------
# DELETE advantage
# ----------------------------
@admin_advantages_router.delete(
    "/advantages/{advantage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_advantages_delete(
    request: Request,
    advantage_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[ADVANTAGES_COLLECTION].delete_one({"id": advantage_id})

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Advantage not found")