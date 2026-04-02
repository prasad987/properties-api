from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import connect_mongo
from .routers.admin import admin_auth_open_router, admin_router
from .routers.admin_properties import admin_properties_router
from .settings import settings


app = FastAPI(title="Properties API", version="0.1.0")

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def _startup() -> None:
    client, db = await connect_mongo()
    app.state.mongo_client = client
    app.state.mongo_db = db


@app.on_event("shutdown")
async def _shutdown() -> None:
    client = getattr(app.state, "mongo_client", None)
    if client is not None:
        client.close()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Phase 1 admin auth contract (JWT).
app.include_router(admin_auth_open_router)
app.include_router(admin_router)
app.include_router(admin_properties_router)

