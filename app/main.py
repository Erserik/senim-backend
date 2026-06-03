from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base

# Import models so SQLAlchemy registers them
from app.models import (  # noqa: F401
    User, MasterProfile, Category, Subcategory, City, District,
    Order, Response, Chat, Message, Review, Transaction,
)

from app.api import (
    auth, onboarding, orders, responses, chats, profile,
    categories, settings as settings_router, reviews, balance, admin,
)
from app.services.seed import seed_initial_data


UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


async def _dev_migrations() -> None:
    """Idempotent ALTER TABLEs for SQLite (dev only). Skipped on PostgreSQL."""
    if engine.dialect.name != 'sqlite':
        return
    async with engine.begin() as conn:
        existing = await conn.execute(text("PRAGMA table_info(master_profiles)"))
        cols = {row[1] for row in existing.fetchall()}
        for col, coldef in [
            ("service_lat", "REAL"),
            ("service_lng", "REAL"),
            ("service_radius_km", "REAL"),
        ]:
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE master_profiles ADD COLUMN {col} {coldef}"))

        user_cols = await conn.execute(text("PRAGMA table_info(users)"))
        uc = {row[1] for row in user_cols.fetchall()}
        for col, coldef in [
            ("is_admin", "INTEGER DEFAULT 0"),
            ("is_banned", "INTEGER DEFAULT 0"),
        ]:
            if col not in uc:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {coldef}"))

        order_cols = await conn.execute(text("PRAGMA table_info(orders)"))
        oc = {row[1] for row in order_cols.fetchall()}
        for col, coldef in [
            ("is_boosted", "INTEGER DEFAULT 0"),
            ("boosted_until", "TIMESTAMP"),
        ]:
            if col not in oc:
                await conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col} {coldef}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _dev_migrations()
    await seed_initial_data()
    yield
    await engine.dispose()


app = FastAPI(
    title="Senim API",
    description="Backend API for Senim — service marketplace for Kazakhstan",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(responses.router, prefix="/api")
app.include_router(chats.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(balance.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "senim-backend", "version": "2.0.0"}
