import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .api.admin import router as admin_router
from .api.auth import router as auth_router
from .api.registration import router as registration_router
from .core.config import CORS_ORIGINS, async_engine, sync_engine
from .core.rate_limit import limiter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            client_ip=request.client.host if request.client else None,
        )

        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("application_startup")
    yield
    # Shutdown
    await async_engine.dispose()
    sync_engine.dispose()
    logger.info("application_shutdown")


app = FastAPI(
    title="MedVerify API",
    description="Production-grade medicine batch authenticity verification via QR codes",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health and metrics endpoints (must be before catch-all)
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/ready")
async def readiness():
    # Check database connectivity
    try:
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return JSONResponse(
            status_code=503, content={"status": "not ready", "database": "disconnected"}
        )


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")


# Routers
app.include_router(registration_router)
app.include_router(admin_router)
app.include_router(auth_router)

# Serve frontend static files (if built) - catch-all must be last
frontend_dist = Path(__file__).parent / "frontend" / "dist"
logger.info("frontend_dist_path", path=str(frontend_dist), exists=frontend_dist.exists())
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA for all non-API routes."""
        # Don't serve SPA for API routes
        if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("metrics") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("medverify.main:app", host="0.0.0.0", port=8000, reload=True)
