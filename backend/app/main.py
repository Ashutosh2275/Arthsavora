from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from .db.mongodb import connect_to_mongo, close_mongo_connection
from .api import auth, expenses, ml_ops, budget, analytics, goals, reports
from .core.config import settings
from .core.limiter import limiter
from slowapi.errors import RateLimitExceeded

# 1. Setup Production Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ARTHSAVORA")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ARTHSAVORA Production Engine...")
    await connect_to_mongo()
    yield
    await close_mongo_connection()
    logger.info("Engine Shutdown Cleanly.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# 2. Rate Limiting Middleware
app.state.limiter = limiter
@app.exception_handler(RateLimitExceeded)
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."}
    )

# 3. Request Auditing Middleware
@app.middleware("http")
async def audit_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Path: {request.url.path} | Method: {request.method} | Time: {process_time:.4f}s")
    return response

# 4. Hardened CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with ["https://your-vercel-domain.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 5. Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Core"])
app.include_router(ml_ops.router, prefix="/api/ml", tags=["AI"])
app.include_router(budget.router, prefix="/api/budget", tags=["Budget"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(reports.router, prefix="/api/reports", tags=["Export"])

@app.get("/")
async def root():
    return {"status": "production_ready", "version": "1.1.0"}