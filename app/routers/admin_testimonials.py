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


class AdminTestimonialToggleRequest(BaseModel):
    active: bool


class AdminTestimonialResponse(BaseModel):
    id: str
    name: str | None = None
    location: str | None = None
    rating: int | None = None
    text: str | None = None
    avatar_url: str | None = None
    active: bool | None = None
    sort_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_testimonials_router = APIRouter(
    prefix="/admin",
    
    tags=["admin-testimonials"]
)

TESTIMONIALS_COLLECTION = "testimonials"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------------------------
# GET Testimonials
# ----------------------------
@admin_testimonials_router.get("/testimonials", response_model=list[AdminTestimonialResponse])
async def admin_testimonials_list(request: Request) -> list[AdminTestimonialResponse]:

    db = get_db(request)

    docs = await db[TESTIMONIALS_COLLECTION].find().sort("sort_order", 1).to_list(100)

    testimonials = []
    for doc in docs:
        doc.pop("_id", None)
        testimonials.append(doc)

    return testimonials


# ----------------------------
# POST Testimonial (multipart)
# ----------------------------
@admin_testimonials_router.post("/testimonials",dependencies=[Depends(get_current_admin)]
)
async def admin_testimonials_create(
    request: Request,
    avatar: UploadFile = File(...),
    name: str = Form(...),
    location: str = Form(...),
    rating: int = Form(...),
    text: str = Form(...),
    sort_order: int = Form(...),
    active: bool = Form(...),
) -> dict[str, str]:

    db = get_db(request)

    now = datetime.now(timezone.utc)

    filename = f"{uuid.uuid4()}_{avatar.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        buffer.write(await avatar.read())

    payload = {
        "id": str(uuid.uuid4()),
        "name": name,
        "location": location,
        "rating": rating,
        "text": text,
        "avatar_url": f"/uploads/{filename}",
        "active": active,
        "sort_order": sort_order,
        "created_at": now,
        "updated_at": now,
    }

    await db[TESTIMONIALS_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# PUT Update testimonial
# ----------------------------
@admin_testimonials_router.put("/testimonials/{testimonial_id}",dependencies=[Depends(get_current_admin)])
async def admin_testimonials_update(
    request: Request,
    testimonial_id: str = Path(...),
    avatar: UploadFile | None = File(None),
    name: str = Form(...),
    location: str = Form(...),
    rating: int = Form(...),
    text: str = Form(...),
    sort_order: int = Form(...),
    active: bool = Form(...),
) -> dict[str, str]:

    db = get_db(request)

    update_data = {
        "name": name,
        "location": location,
        "rating": rating,
        "text": text,
        "sort_order": sort_order,
        "active": active,
        "updated_at": datetime.now(timezone.utc),
    }

    if avatar:
        filename = f"{uuid.uuid4()}_{avatar.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as buffer:
            buffer.write(await avatar.read())

        update_data["avatar_url"] = f"/uploads/{filename}"

    res = await db[TESTIMONIALS_COLLECTION].update_one(
        {"id": testimonial_id},
        {"$set": update_data},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    return {"id": testimonial_id}


# ----------------------------
# PATCH Toggle active
# ----------------------------
@admin_testimonials_router.patch(
    "/testimonials/{testimonial_id}",
    status_code=status.HTTP_204_NO_CONTENT,dependencies=[Depends(get_current_admin)]
)
async def admin_testimonials_toggle(
    request: Request,
    body: AdminTestimonialToggleRequest = Body(...),
    testimonial_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[TESTIMONIALS_COLLECTION].update_one(
        {"id": testimonial_id},
        {
            "$set": {
                "active": body.active,
                "updated_at": datetime.now(timezone.utc),
            }
        }
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Testimonial not found")


# ----------------------------
# DELETE testimonial
# ----------------------------
@admin_testimonials_router.delete(
    "/testimonials/{testimonial_id}",
    status_code=status.HTTP_204_NO_CONTENT,dependencies=[Depends(get_current_admin)]
)
async def admin_testimonials_delete(
    request: Request,
    testimonial_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[TESTIMONIALS_COLLECTION].delete_one({"id": testimonial_id})

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Testimonial not found")