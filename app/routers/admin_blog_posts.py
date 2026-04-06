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


class AdminBlogPostToggleRequest(BaseModel):
    featured: bool


class AdminBlogPostResponse(BaseModel):
    id: str
    slug: str | None = None
    title: str | None = None
    excerpt: str | None = None
    content: str | None = None
    category: str | None = None
    author: str | None = None
    read_time: int | None = None
    published: bool | None = None
    featured: bool | None = None
    youtube_url: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    tags: list[str] | None = None
    images: list[str] | None = None
    cover_image: str | None = None
    author_avatar: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


admin_blog_posts_router = APIRouter(
    prefix="/admin",
    tags=["admin-blog-posts"]
)

BLOG_POSTS_COLLECTION = "blog_posts"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------------------------
# GET Blog Posts
# ----------------------------
@admin_blog_posts_router.get("/blog-posts", response_model=list[AdminBlogPostResponse])
async def admin_blog_posts_list(request: Request) -> list[AdminBlogPostResponse]:

    db = get_db(request)

    docs = await db[BLOG_POSTS_COLLECTION].find().sort("created_at", -1).to_list(100)

    posts = []
    for doc in docs:
        doc.pop("_id", None)
        posts.append(doc)

    return posts


# ----------------------------
# GET Single Blog Post
# ----------------------------
@admin_blog_posts_router.get("/blog-posts/{post_id}", response_model=AdminBlogPostResponse)
async def admin_blog_post_detail(
    request: Request,
    post_id: str = Path(...)
) -> AdminBlogPostResponse:

    db = get_db(request)

    post = await db[BLOG_POSTS_COLLECTION].find_one({"id": post_id})

    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    post.pop("_id", None)

    return post


# ----------------------------
# POST Blog Post (multipart)
# ----------------------------
@admin_blog_posts_router.post("/blog-posts", dependencies=[Depends(get_current_admin)])
async def admin_blog_posts_create(
    request: Request,

    slug: str = Form(...),
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    author: str = Form(...),

    read_time: int = Form(...),
    published: bool = Form(...),
    featured: bool = Form(...),

    youtube_url: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),

    tags: str = Form(""),

    cover_image: UploadFile | None = File(None),
    author_avatar: UploadFile | None = File(None),
) -> dict[str, str]:

    db = get_db(request)

    now = datetime.now(timezone.utc)

    payload = {
        "id": str(uuid.uuid4()),
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "content": content,
        "category": category,
        "author": author,
        "read_time": read_time,
        "published": published,
        "featured": featured,
        "youtube_url": youtube_url,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "tags": tags.split(",") if tags else [],
        "images": [],
        "created_at": now,
        "updated_at": now,
    }

    if cover_image:
        filename = f"{uuid.uuid4()}_{cover_image.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            buffer.write(await cover_image.read())

        payload["cover_image"] = f"/uploads/{filename}"

    if author_avatar:
        filename = f"{uuid.uuid4()}_{author_avatar.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            buffer.write(await author_avatar.read())

        payload["author_avatar"] = f"/uploads/{filename}"

    await db[BLOG_POSTS_COLLECTION].insert_one(payload)

    return {"id": payload["id"]}


# ----------------------------
# PUT Update Blog Post
# ----------------------------
@admin_blog_posts_router.put("/blog-posts/{post_id}", dependencies=[Depends(get_current_admin)])
async def admin_blog_posts_update(
    request: Request,
    post_id: str = Path(...),

    slug: str = Form(...),
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    author: str = Form(...),

    read_time: int = Form(...),
    published: bool = Form(...),
    featured: bool = Form(...),

    youtube_url: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),

    tags: str = Form(""),

    cover_image: UploadFile | None = File(None),
    author_avatar: UploadFile | None = File(None),
) -> dict[str, str]:

    db = get_db(request)

    update_data = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "content": content,
        "category": category,
        "author": author,
        "read_time": read_time,
        "published": published,
        "featured": featured,
        "youtube_url": youtube_url,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "tags": tags.split(",") if tags else [],
        "updated_at": datetime.now(timezone.utc),
    }

    if cover_image:
        filename = f"{uuid.uuid4()}_{cover_image.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            buffer.write(await cover_image.read())

        update_data["cover_image"] = f"/uploads/{filename}"

    if author_avatar:
        filename = f"{uuid.uuid4()}_{author_avatar.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as buffer:
            buffer.write(await author_avatar.read())

        update_data["author_avatar"] = f"/uploads/{filename}"

    res = await db[BLOG_POSTS_COLLECTION].update_one(
        {"id": post_id},
        {"$set": update_data},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog post not found")

    return {"id": post_id}


# ----------------------------
# PATCH Toggle Featured
# ----------------------------
@admin_blog_posts_router.patch(
    "/blog-posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_blog_posts_toggle(
    request: Request,
    body: AdminBlogPostToggleRequest = Body(...),
    post_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[BLOG_POSTS_COLLECTION].update_one(
        {"id": post_id},
        {
            "$set": {
                "featured": body.featured,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog post not found")


# ----------------------------
# DELETE Blog Post
# ----------------------------
@admin_blog_posts_router.delete(
    "/blog-posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)]
)
async def admin_blog_posts_delete(
    request: Request,
    post_id: str = Path(...)
) -> None:

    db = get_db(request)

    res = await db[BLOG_POSTS_COLLECTION].delete_one({"id": post_id})

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog post not found")