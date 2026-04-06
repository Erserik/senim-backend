from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, onboarding, orders, responses, chats, profile, categories, settings as settings_router, reviews
from app.services.seed import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev mode; use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial data
    await seed_initial_data()

    yield

    await engine.dispose()


app = FastAPI(
    title="Senim API",
    description="Backend API for Senim — marketplace for home services in Almaty",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(responses.router, prefix="/api")
app.include_router(chats.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "senim-backend"}
