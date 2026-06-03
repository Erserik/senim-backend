import os

# ВАЖНО: до любых импортов app — движок создаётся на импорте.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_senim.db"
os.environ["SECRET_KEY"] = "test-secret"

import httpx
import pytest_asyncio
from httpx import ASGITransport

from app.main import app
from app.core.database import Base, engine


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    """Чистая схема на каждый тест; dispose — чтобы пул не пережил event loop."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
