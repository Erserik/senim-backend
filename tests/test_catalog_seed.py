from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session
from app.models import Category, Subcategory
from app.services.catalog_data import CATEGORIES
from app.services.seed import _seed_catalog


async def _run_seed():
    async with async_session() as db:
        await _seed_catalog(db)
        await db.commit()


async def _all_cats():
    async with async_session() as db:
        res = await db.execute(
            select(Category).options(selectinload(Category.subcategories))
        )
        return {c.slug: c for c in res.scalars().all()}


async def test_seed_on_empty_db_creates_all():
    await _run_seed()
    cats = await _all_cats()
    assert len(cats) == len(CATEGORIES) == 14
    assert "cleaning" in cats and "movers" in cats
    assert len(cats["cleaning"].subcategories) == 6


async def test_seed_adds_missing_categories_to_old_db():
    """Имитация прод-БД: есть только старая категория — upsert докатывает новые."""
    async with async_session() as db:
        db.add(Category(slug="plumber", label_ru="Старый лейбл", label_kz="x",
                        icon="wrench", color="#000000", sort_order=99))
        await db.commit()

    await _run_seed()
    cats = await _all_cats()
    assert len(cats) == 14
    # существующая категория обновлена, не задублирована
    assert cats["plumber"].label_ru == "Сантехник"
    assert cats["plumber"].color == "#1E88E5"
    # и получила подкатегории
    assert len(cats["plumber"].subcategories) > 0


async def test_seed_is_idempotent():
    await _run_seed()
    await _run_seed()
    cats = await _all_cats()
    assert len(cats) == 14
    async with async_session() as db:
        n_subs = len((await db.execute(select(Subcategory))).scalars().all())
    await _run_seed()
    async with async_session() as db:
        n_subs2 = len((await db.execute(select(Subcategory))).scalars().all())
    assert n_subs == n_subs2
