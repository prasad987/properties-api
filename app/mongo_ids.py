from __future__ import annotations

from bson import ObjectId
from uuid import UUID
from fastapi import HTTPException, status


def to_object_id(value: str, *, field_name: str = "id") -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as e:  # noqa: BLE001 - map to 400 for invalid input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from e


def object_id_to_str(value: ObjectId) -> str:
    return str(value)


def to_uuid(value: str, *, field_name: str = "id") -> str:
    """
    Normalize/validate IDs that the frontend treats as UUID strings.
    Stored IDs remain plain strings in Mongo.
    """
    try:
        return str(UUID(value))
    except Exception as e:  # noqa: BLE001 - map to 400 for invalid input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from e

