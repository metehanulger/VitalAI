import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.triage import router as triage_router
from app.core.config import settings
from app.db.database import SessionLocal, init_db
from app.db.tables import HastaneLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db_auto_create:
        try:
            init_db()
        except SQLAlchemyError:
            logger.exception("Could not create database tables; check DATABASE_URL")
    logger.info("watsonx.ai %s", "enabled" if settings.watsonx_enabled else "disabled")
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage_router)


@app.exception_handler(SQLAlchemyError)
async def veritabani_hatasi(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable. Please try again."})


@app.get("/api/health", tags=["health"])
def health():
    try:
        with SessionLocal() as db:
            db.scalar(select(func.count()).select_from(HastaneLog))
        veritabani = True
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        veritabani = False
    return JSONResponse(
        status_code=200 if veritabani else 503,
        content={"durum": "ok" if veritabani else "error", "veritabani": veritabani, "watsonx": settings.watsonx_enabled},
    )
