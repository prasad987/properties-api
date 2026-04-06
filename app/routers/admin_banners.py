from __future__ import annotations

import uuid
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Request,
    status,
    UploadFile,
    File,
    Form,
)

from pydantic import BaseModel

from ..db import get_db
from .admin import get_current_admin


class AdminBannerToggleRequest(BaseModel):
    active: bool


class AdminBannerResponse(BaseModel):
    id: str
    image_url: str | None = None
    label: str | None = None
    subtitle: str | None = None
    sort_order: int | None = None
    active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_banners_router = APIRouter(
    prefix="/admin",
    tags=["admin-banners"]
)

BANNERS_COLLECTION = "banners"


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------------------------
# GET - Fetch banners
# ----------------------------
@admin_banners_router.get("/banners", response_model=list[AdminBannerResponse])
async def admin_banners_list(request: Request) -> list[AdminBannerResponse]:

    db = get_db(request)

    docs = await db[BANNERS_COLLECTION].find().sort("sort_order", 1).to_list(100)

    banners = []
    for doc in docs:
        doc.pop("_id", None)
        banners.append(doc)

    return banners


# ----------------------------
# POST - Create banner (MULTIPART FORM)
# ----------------------------
@admin_banners_router.post("/banners", dependencies=[Depends(get_current_admin)])
async def admin_banners_create(
    request: Request,
    image: UploadFile = File(...),
    label: str = Form(...),
    subtitle: str = Form(...),
    sort_order: int = Form(...),
    active: bool = Form(...),
) -> dict[str, str]:

    db = get_db(request)

    now = datetime.now(timezone.utc)

    filename = f"{uuid.uuid4()}_{image.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        buffer.write(await image.read())

    payload = {
        "id": str(uuid.uuid4()),
        "image_url": f"/uploads/{filename}",
        "label": label,
        "subtitle": subtitle,
        "sort_order": sort_order,
        "active": active,
        "created_at": now,
        "updated_at": now,
    }

    await db[BANNERS_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# PUT - Update banner (MULTIPART FORM)
# ----------------------------
@admin_banners_router.put("/banners/{banner_id}", dependencies=[Depends(get_current_admin)])
async def admin_banners_update(
    request: Request,
    banner_id: str = Path(...),
    image: UploadFile | None = File(None),
    label: str = Form(...),
    subtitle: str = Form(...),
    sort_order: int = Form(...),
    active: bool = Form(...),
) -> dict[str, str]:

    db = get_db(request)

    update_data = {
        "label": label,
        "subtitle": subtitle,
        "sort_order": sort_order,
        "active": active,
        "updated_at": datetime.now(timezone.utc),
    }

    if image:
        filename = f"{uuid.uuid4()}_{image.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as buffer:
            buffer.write(await image.read())

        update_data["image_url"] = f"/uploads/{filename}"

    res = await db[BANNERS_COLLECTION].update_one(
        {"id": banner_id},
        {"$set": update_data},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Banner not found")

    return {"id": banner_id}


# ----------------------------
# PATCH - Toggle active
# ----------------------------
@admin_banners_router.patch(
    "/banners/{banner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_banners_toggle(
    request: Request,
    body: AdminBannerToggleRequest = Body(...),
    banner_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[BANNERS_COLLECTION].update_one(
        {"id": banner_id},
        {
            "$set": {
                "active": body.active,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Banner not found")


# ----------------------------
# DELETE - Remove banner
# ----------------------------
@admin_banners_router.delete(
    "/banners/{banner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_banners_delete(
    request: Request,
    banner_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[BANNERS_COLLECTION].delete_one({"id": banner_id})

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Banner not found")