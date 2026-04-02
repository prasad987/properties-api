from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import EmailStr
from pydantic import BaseModel

from ..db import get_db
from ..jwt import create_access_token, decode_access_token
from ..security import verify_password
from ..settings import settings


bearer_scheme = HTTPBearer(auto_error=False)


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminAccessTokenResponse(BaseModel):
    access_token: str


class AdminMeResponse(BaseModel):
    email: EmailStr


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    db = get_db(request)
    admin = await db[settings.mongodb_admin_collection].find_one(
        {"email": email, "active": {"$ne": False}},
        # MongoDB doesn't allow mixing inclusion and exclusion in a projection.
        # We only need email for admin context.
        projection={"email": 1, "active": 1, "_id": 0},
    )
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")

    return admin


# Unprotected routes for issuing tokens.
admin_auth_open_router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@admin_auth_open_router.post("/login", response_model=AdminAccessTokenResponse)
async def admin_login(body: AdminLoginRequest, request: Request) -> dict[str, str]:
    db = get_db(request)
    admin = await db[settings.mongodb_admin_collection].find_one({"email": body.email})
    if not admin or not admin.get("password_hash") or not verify_password(body.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if admin.get("active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin disabled")

    token = create_access_token(subject=body.email)
    return {"access_token": token}


# Protected routes under /admin/*.
admin_router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)], tags=["admin"])


@admin_router.get("/auth/me", response_model=AdminMeResponse)
async def admin_me(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict[str, str]:
    # The router dependency already validated the token + admin in Mongo.
    # Here we only extract the email from the JWT to match the contract.
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"email": email}


@admin_router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def admin_logout() -> None:
    # Stateless JWT logout: client clears token on the frontend.
    return None

