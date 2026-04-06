from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
)
from pydantic import BaseModel

from ..db import get_db
from .admin import get_current_admin


admin_settings_router = APIRouter(
    prefix="/admin",
    tags=["admin-settings"]
)

SETTINGS_COLLECTION = "settings"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class AdminSettingResponse(BaseModel):
    key: str
    value: str | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


# ----------------------------
# GET Settings
# ----------------------------
@admin_settings_router.get("/settings", response_model=list[AdminSettingResponse])
async def admin_settings_list(request: Request) -> list[AdminSettingResponse]:

    db = get_db(request)

    docs = await db[SETTINGS_COLLECTION].find().to_list(100)

    settings = []

    for doc in docs:
        doc.pop("_id", None)
        settings.append(doc)

    return settings


# ----------------------------
# POST Create / Update Setting
# ----------------------------
@admin_settings_router.post("/settings", dependencies=[Depends(get_current_admin)])
async def admin_settings_upsert(
    request: Request,
    key: str = Form(...),
    value: str = Form(""),
    logo: UploadFile | None = File(None),
) -> dict[str, str]:

    db = get_db(request)

    # handle logo upload
    if key == "logo_url" and logo:

        filename = f"{uuid.uuid4()}_{logo.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            buffer.write(await logo.read())

        value = f"/uploads/{filename}"

    payload = {
        "key": key,
        "value": value,
        "updated_at": datetime.now(timezone.utc),
    }

    # upsert setting
    await db[SETTINGS_COLLECTION].update_one(
        {"key": key},
        {"$set": payload},
        upsert=True,
    )

    return {"key": key}