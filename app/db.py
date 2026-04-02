from __future__ import annotations

from typing import Any

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .settings import settings


async def connect_mongo() -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]
    return client, db


def get_db(request: Request) -> AsyncIOMotorDatabase:
    db: Any = request.app.state.mongo_db
    return db

