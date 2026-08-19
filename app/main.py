import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from app.api import router
from app.background import alert_scheduler
from app.core.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import User, UserRole
from app.storage import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings(); ensure_bucket()
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        if len(settings.bootstrap_admin_password) < 10:
            raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must contain at least 10 characters")
        with SessionLocal() as db:
            exists=db.scalar(select(User).where(User.email==settings.bootstrap_admin_email))
            if not exists:
                db.add(User(full_name=settings.bootstrap_admin_name,email=settings.bootstrap_admin_email,role=UserRole.ADMIN,password_hash=hash_password(settings.bootstrap_admin_password))); db.commit()
    stop=asyncio.Event(); task=asyncio.create_task(alert_scheduler(stop))
    yield
    stop.set(); await task


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health", tags=["System"])
def health():
    try:
        with SessionLocal() as db: db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(503,"Database unavailable") from exc
    return {"status": "ok", "service": "supervisory-tracking-api", "database": "reachable"}
