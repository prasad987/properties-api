from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import connect_mongo
from .routers.admin import admin_auth_open_router, admin_router
from .routers.admin_properties import admin_properties_router
from .routers.admin_banners import admin_banners_router
from .routers.admin_testimonials import admin_testimonials_router
from .routers.admin_advantages import admin_advantages_router
from .routers.admin_contact_enquiries import admin_contact_enquiries_router
from .routers.admin_sell_enquiries import admin_sell_enquiries_router
from .routers.admin_blog_posts import admin_blog_posts_router
from .routers.admin_settings import admin_settings_router

from .settings import settings


app = FastAPI(title="Properties API", version="0.1.0")


# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# MongoDB Startup
# -------------------------
@app.on_event("startup")
async def _startup() -> None:
    client, db = await connect_mongo()
    app.state.mongo_client = client
    app.state.mongo_db = db


# -------------------------
# MongoDB Shutdown
# -------------------------
@app.on_event("shutdown")
async def _shutdown() -> None:
    client = getattr(app.state, "mongo_client", None)
    if client is not None:
        client.close()


# -------------------------
# Static files
# -------------------------
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def _sanitize_validation_error(obj: object) -> object:
    if isinstance(obj, dict):
        return {str(k): _sanitize_validation_error(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_validation_error(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize_validation_error(v) for v in obj]
    if isinstance(obj, bytes):
        # Validation errors can contain raw multipart bytes; avoid UTF-8 decode crashes.
        return f"<{len(obj)} bytes>"
    return obj


async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": _sanitize_validation_error(exc.errors())},
    )


async def unicode_decode_exception_handler(_: Request, exc: UnicodeDecodeError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "type": "request_decode_error",
                    "msg": f"Invalid byte sequence in request payload: {exc}",
                }
            ]
        },
    )


app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(UnicodeDecodeError, unicode_decode_exception_handler)


# -------------------------
# Health Check
# -------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# -------------------------
# Routers
# -------------------------
app.include_router(admin_auth_open_router)
app.include_router(admin_router)
app.include_router(admin_properties_router)
app.include_router(admin_banners_router)
app.include_router(admin_testimonials_router)
app.include_router(admin_advantages_router)
app.include_router(admin_contact_enquiries_router)
app.include_router(admin_sell_enquiries_router)
app.include_router(admin_blog_posts_router)
app.include_router(admin_settings_router)