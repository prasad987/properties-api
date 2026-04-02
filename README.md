# Properties API (FastAPI + MongoDB)

## Phase 1: Admin Auth Contract (JWT)

### Login
`POST /admin/auth/login`

Request body:
```json
{ "email": "admin@example.com", "password": "string" }
```

Response:
```json
{ "access_token": "jwt-token" }
```

### Me
`GET /admin/auth/me`

Headers:
`Authorization: Bearer <token>`

Response:
```json
{ "email": "admin@example.com" }
```

### Logout (stateless)
`POST /admin/auth/logout`

Headers:
`Authorization: Bearer <token>`

Response: `204 No Content`

All other routes under `/admin/*` are protected with the same Bearer token mechanism.

## Setup

1. Copy `.env.example` to `.env` and set `JWT_SECRET_KEY`.
2. Start MongoDB (or point `MONGODB_URL` to your Mongo instance).
3. Seed an admin user:

```powershell
./.venv/Scripts/python -m app.scripts.seed_admin --email "admin@example.com" --password "change-me"
```

4. Run the API:

```powershell
./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

## Health check
`GET /health` -> `{ "status": "ok" }`

