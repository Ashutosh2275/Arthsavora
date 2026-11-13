# ARTHSAVORA — CONFIGURATION REFERENCE

**Document Reference:** `docs/CONFIGURATION_REFERENCE.md`  
**Last Updated:** Prompt 02  

---

## 1. BACKEND CONFIGURATION (`backend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | `str` | `"ARTHSAVORA"` | Application identifier. |
| `ENVIRONMENT` | `str` | `"development"` | Environment mode: `development`, `testing`, `production`. |
| `DEBUG` | `bool` | `false` | Enables verbose SQL logging and reload flags. |
| `SECRET_KEY` | `str` | Dev Secret | Secret key for HS256 JWT encoding. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `1440` | JWT token lifetime (24 hours). |
| `CORS_ORIGINS` | `list[str]` | `["http://localhost:5173", ...]` | Allowed HTTP origins. Wildcard with credentials strictly prohibited. |
| `POSTGRES_SERVER` | `str` | `"localhost"` | PostgreSQL hostname. |
| `POSTGRES_PORT` | `int` | `5432` | PostgreSQL port. |
| `POSTGRES_USER` | `str` | `"postgres"` | Database user. |
| `POSTGRES_PASSWORD` | `str` | `"postgres"` | Database password. |
| `POSTGRES_DB` | `str` | `"arthsavora"` | Primary database name. |
| `DATABASE_URL` | `str` | Assembled | Async connection string: `postgresql+asyncpg://...`. |
| `MONGODB_URL` | `str` | `"mongodb://localhost:27017/arthsavora"` | Transitional MongoDB URL. |
| `REDIS_URL` | `str` | `"redis://localhost:6379/0"` | Redis broker for Celery tasks. |
| `SUPABASE_URL` | `str` | `"https://example.supabase.co"` | Supabase API URL. |
| `SUPABASE_KEY` | `str` | Placeholder | Supabase client access key. |
| `GEMINI_API_KEY` | `str` | Placeholder | Google AI API key for intelligence services. |

---

## 2. FRONTEND CONFIGURATION (`apps/web/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | `str` | `"/api"` | Base API path (proxied by Vite in dev to `http://127.0.0.1:8000`). |
| `VITE_APP_TITLE` | `str` | `"ARTHSAVORA"` | Brand display title. |
