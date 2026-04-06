from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, EmailStr, Field, ValidationError
from starlette.datastructures import UploadFile

from ..db import get_db
from ..mongo_ids import to_uuid
from .admin import get_current_admin


PropertyType = Literal["land_sale", "room_rent", "land_rent", "commercial_rent", "lease"]
PricePeriod = Literal["total", "monthly", "yearly", "per_sqft"]


class AdminPropertyCreateUpdate(BaseModel):
    title: str
    description: str | None = None
    type_: PropertyType = Field(alias="type")
    price: float
    price_period: PricePeriod
    area: float | None = None
    area_unit: str
    bedrooms: int | None = None
    bathrooms: int | None = None
    address: str
    city: str
    state: str
    country: str
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    featured: bool
    available: bool
    whatsapp_number: str | None = None
    cover_image: str
    amenities: list[str] | None = None
    near_by_places: list["AdminPropertyNearByPlaceItem"] | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    agent_email: EmailStr | None = None
    video_url: str | None = None
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class AdminPropertyCreateUpdateResponse(BaseModel):
    id: str


class AdminPropertyImageResponse(BaseModel):
    url: str
    sort_order: int


class AdminPropertyNearByPlaceItem(BaseModel):
    place: str
    distance: str


class AdminPropertyListItemResponse(BaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    type_: PropertyType | None = Field(default=None, alias="type")
    price: float | None = None
    price_period: PricePeriod | None = None
    area: float | None = None
    area_unit: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    featured: bool | None = None
    available: bool | None = None
    whatsapp_number: str | None = None
    cover_image: str | None = None
    amenities: list[str] | None = None
    near_by_places: list[AdminPropertyNearByPlaceItem] | None = None
    agent_name: str | None = None
    agent_phone: str | None = None
    agent_email: EmailStr | None = None
    video_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    property_images: list[AdminPropertyImageResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class AdminPropertyToggleRequest(BaseModel):
    available: bool | None = None
    featured: bool | None = None


class AdminPropertyImageItem(BaseModel):
    property_id: str
    url: str
    sort_order: int


class AdminPropertyImageBulkRequest(BaseModel):
    items: list[AdminPropertyImageItem]


admin_properties_router = APIRouter(prefix="/admin", tags=["admin"])

PROPERTIES_COLLECTION = "properties"
PROPERTY_IMAGES_COLLECTION = "property_images"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _parse_property_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").lower()
    raw_payload: dict[str, Any]

    if "application/json" in content_type:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Body must be an object")
        raw_payload = body
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        raw_payload = {}
        for key, value in form.multi_items():
            if isinstance(value, UploadFile):
                # Accept cover_image file upload and convert to stored URL string.
                if key == "cover_image" and value.filename:
                    filename = f"{uuid.uuid4()}_{value.filename}"
                    path = os.path.join(UPLOAD_DIR, filename)
                    with open(path, "wb") as buffer:
                        buffer.write(await value.read())
                    raw_payload["cover_image"] = f"/uploads/{filename}"
                continue
            if isinstance(value, bytes):
                continue
            if key in raw_payload:
                current = raw_payload[key]
                if isinstance(current, list):
                    current.append(value)
                else:
                    raw_payload[key] = [current, value]
            else:
                raw_payload[key] = value
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported Content-Type. Use application/json or multipart/form-data",
        )

    amenities = raw_payload.get("amenities")
    if isinstance(amenities, str):
        text = amenities.strip()
        if text:
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        raw_payload["amenities"] = parsed
                except json.JSONDecodeError:
                    raw_payload["amenities"] = [item.strip() for item in text.split(",") if item.strip()]
            else:
                raw_payload["amenities"] = [item.strip() for item in text.split(",") if item.strip()]
        else:
            raw_payload["amenities"] = []

    near_by_places = raw_payload.get("near_by_places")
    if isinstance(near_by_places, str):
        text = near_by_places.strip()
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    raw_payload["near_by_places"] = parsed
            except json.JSONDecodeError:
                # If client sends malformed value, let schema validation raise a clean 422.
                pass
        else:
            raw_payload["near_by_places"] = []

    # Form submissions often send empty strings for optional numeric fields.
    for optional_numeric in ("bedrooms", "bathrooms", "area", "latitude", "longitude"):
        if raw_payload.get(optional_numeric) == "":
            raw_payload[optional_numeric] = None

    try:
        validated = AdminPropertyCreateUpdate.model_validate(raw_payload)
    except ValidationError as exc:
        details = []
        for err in exc.errors():
            cleaned = dict(err)
            bad_input = cleaned.get("input")
            if isinstance(bad_input, UploadFile):
                cleaned["input"] = f"<upload:{bad_input.filename}>"
            details.append(cleaned)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=details)

    return validated.model_dump(by_alias=True)


@admin_properties_router.get("/properties", response_model=list[AdminPropertyListItemResponse])
async def admin_properties_list(request: Request) -> list[AdminPropertyListItemResponse]:
    db = get_db(request)

    # Fetch properties ordered by created_at desc and embed images sorted by sort_order.
    pipeline: list[dict[str, Any]] = [
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": PROPERTY_IMAGES_COLLECTION,
                "let": {"propertyId": "$id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$property_id", "$$propertyId"]}}},
                    {"$sort": {"sort_order": 1}},
                    {"$project": {"url": 1, "sort_order": 1, "_id": 0}},
                ],
                "as": "property_images",
            }
        },
    ]

    docs: list[dict[str, Any]] = await db[PROPERTIES_COLLECTION].aggregate(pipeline).to_list(length=1000)

    # Keep images' shape as {url, sort_order} and do not expose Mongo `_id`.
    out: list[dict[str, Any]] = []
    for doc in docs:
        # For compatibility: the frontend expects `id` (uuid string), not Mongo `_id`.
        doc.pop("_id", None)
        out.append(doc)
    return out


@admin_properties_router.get("/properties/{property_id}", response_model=AdminPropertyListItemResponse)
async def admin_property_detail(
    request: Request,
    property_id: str = Path(..., description="Property id (UUID string)"),
) -> AdminPropertyListItemResponse:
    db = get_db(request)
    pid = to_uuid(property_id, field_name="property_id")

    pipeline: list[dict[str, Any]] = [
        {"$match": {"id": pid}},
        {
            "$lookup": {
                "from": PROPERTY_IMAGES_COLLECTION,
                "let": {"propertyId": "$id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$property_id", "$$propertyId"]}}},
                    {"$sort": {"sort_order": 1}},
                    {"$project": {"url": 1, "sort_order": 1, "_id": 0}},
                ],
                "as": "property_images",
            }
        },
        {"$limit": 1},
    ]

    docs = await db[PROPERTIES_COLLECTION].aggregate(pipeline).to_list(length=1)
    if not docs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    doc = docs[0]
    doc.pop("_id", None)
    return doc


@admin_properties_router.post(
    "/properties",
    response_model=AdminPropertyCreateUpdateResponse,
    dependencies=[Depends(get_current_admin)],
)
async def admin_properties_create(
    request: Request,
) -> dict[str, str]:
    db = get_db(request)
    payload = await _parse_property_payload(request)

    now = datetime.now(timezone.utc)
    payload["id"] = str(uuid.uuid4())
    payload.setdefault("created_at", now)
    payload["created_at"] = payload.get("created_at", now)
    payload["updated_at"] = now

    # Mongo stores updated_at directly from the payload.
    res = await db[PROPERTIES_COLLECTION].insert_one(payload)
    return {"id": payload["id"]}


@admin_properties_router.put(
    "/properties/{property_id}",
    response_model=AdminPropertyCreateUpdateResponse,
    dependencies=[Depends(get_current_admin)],
)
async def admin_properties_update(
    request: Request,
    property_id: str = Path(..., description="Property id (UUID string)"),
) -> dict[str, str]:
    db = get_db(request)
    pid = to_uuid(property_id, field_name="property_id")

    payload = await _parse_property_payload(request)
    # Ensure Mongo update doesn't try to replace the stable id.
    payload.pop("id", None)
    # Always manage update timestamp on server side.
    payload["updated_at"] = datetime.now(timezone.utc)

    res = await db[PROPERTIES_COLLECTION].update_one(
        {"id": pid},
        {"$set": payload},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return {"id": pid}


@admin_properties_router.patch(
    "/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def admin_properties_toggle(
    request: Request,
    body: AdminPropertyToggleRequest = Body(...),
    property_id: str = Path(..., description="Property id (UUID string)"),
) -> None:
    db = get_db(request)
    pid = to_uuid(property_id, field_name="property_id")

    if body.available is None and body.featured is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")

    update_fields: dict[str, Any] = {}
    if body.available is not None:
        update_fields["available"] = body.available
    if body.featured is not None:
        update_fields["featured"] = body.featured

    update_fields["updated_at"] = datetime.now(timezone.utc)

    res = await db[PROPERTIES_COLLECTION].update_one({"id": pid}, {"$set": update_fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return None


@admin_properties_router.delete(
    "/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def admin_properties_delete(
    request: Request,
    property_id: str = Path(..., description="Property id (UUID string)"),
) -> None:
    db = get_db(request)
    pid = to_uuid(property_id, field_name="property_id")

    delete_prop = await db[PROPERTIES_COLLECTION].delete_one({"id": pid})
    if delete_prop.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    # Keep collection consistent with the Admin UI expectations.
    await db[PROPERTY_IMAGES_COLLECTION].delete_many({"property_id": pid})
    return None


@admin_properties_router.delete(
    "/property-images",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def admin_property_images_delete_by_property_id(
    request: Request,
    property_id: str = Query(..., description="Property id (UUID string)"),
) -> None:
    db = get_db(request)
    pid = to_uuid(property_id, field_name="property_id")

    await db[PROPERTY_IMAGES_COLLECTION].delete_many({"property_id": pid})
    return None


@admin_properties_router.post(
    "/property-images/bulk",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin)],
)
async def admin_property_images_bulk_insert(
    body: AdminPropertyImageBulkRequest,
    request: Request,
) -> dict[str, Any]:
    db = get_db(request)

    docs: list[dict[str, Any]] = []
    for item in body.items:
        pid = to_uuid(item.property_id, field_name="property_id")
        docs.append(
            {
                "property_id": pid,
                "url": item.url,
                "sort_order": item.sort_order,
            }
        )

    if docs:
        res = await db[PROPERTY_IMAGES_COLLECTION].insert_many(docs)
        inserted = len(res.inserted_ids)
    else:
        inserted = 0

    return {"inserted_count": inserted}

