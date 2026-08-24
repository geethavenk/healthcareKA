"""
Application entry point.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config import settings
from database import init_db, SessionLocal
from security import limiter, rate_limit_exceeded_handler
import neo4j_client, models

from routers import health, departments, doctors, patients, appointments, documents, search, ask, symptoms

# Startup/shutdown lifecycle

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db() # enable pgvector extensions and create all tables
    yield
    # shutdown
    neo4j_client.close_driver()

# App instance
app = FastAPI(
    title=settings.app_name,
    description=(
        "A healthcare information assistant connecting doctors, departments, " \
        "appointments, symptoms and general medical documents via Graph RAG."
    ),
    version = "1.0.0",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS - allow the frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request logging

UNLOGGED_PATHS = {"/health", "/favicon.ico", "/docs", "/redoc", "/openapi.json"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)

    if request.url.path in UNLOGGED_PATHS:
        return response
    
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # write the log entry
    db=SessionLocal()
    try:
        db.add(models.RequestLog(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            client_ip=request.client.host if request.client else None,
            response_time_ms=duration_ms,
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    return response

# Routers
app.include_router(health.router)
app.include_router(departments.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(symptoms.router)

