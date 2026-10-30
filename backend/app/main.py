import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.triage import router as triage_router
from app.core.config import settings
from app.core.triage import ml_modellerini_yukle
from app.db.database import SessionLocal
from app.db.migrate import upgrade_to_head
from app.db.tables import HastaneLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db_auto_migrate:
        try:
            upgrade_to_head()
        except SQLAlchemyError:
            logger.exception("Could not run database migrations; check DATABASE_URL")
    # Load the ML artifacts now so the first triage request does not pay for it.
    ml_modellerini_yukle()
    logger.info("watsonx.ai %s", "enabled" if settings.watsonx_enabled else "disabled")
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(triage_router)


@app.exception_handler(IntegrityError)
async def butunluk_hatasi(request: Request, exc: IntegrityError):
    logger.warning("Integrity error: %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(status_code=422, content={"detail": "The record violates a database constraint."})


@app.exception_handler(SQLAlchemyError)
async def veritabani_hatasi(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable. Please try again."})


@app.get("/api/health", tags=["health"])
def health():
    try:
        with SessionLocal() as db:
            # Cheap probe: confirms the connection and that the schema exists.
            db.scalar(select(HastaneLog.id).limit(1))
        veritabani = True
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        veritabani = False
    return JSONResponse(
        status_code=200 if veritabani else 503,
        content={"durum": "ok" if veritabani else "error", "veritabani": veritabani, "watsonx": settings.watsonx_enabled},
    )
