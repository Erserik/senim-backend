from app.core.database import async_session
from app.services.catalog_data import GROUPS
from app.services.seed import _seed_catalog


async def _seed():
    async with async_session() as db:
        await _seed_catalog(db)
        await db.commit()


async def test_groups_endpoint_shape(client):
    await _seed()
    res = await client.get("/api/category-groups")
    assert res.status_code == 200
    groups = res.json()["groups"]
    assert len(groups) == 6
    by_slug = {g["slug"]: g for g in groups}
    g = by_slug["g-cleaning"]
    assert g["label_ru"] == "Уборка"
    assert [c["slug"] for c in g["categories"]] == ["cleaning"]
    assert len(g["categories"][0]["subcategories"]) == 6
    # порядок групп как в GROUPS
    assert [x["slug"] for x in groups] == [x["slug"] for x in GROUPS]


async def test_groups_cover_all_categories(client):
    """Каждая категория из БД входит ровно в одну группу."""
    await _seed()
    cats_res = await client.get("/api/categories")
    db_slugs = {c["slug"] for c in cats_res.json()["categories"]}
    grouped = [c["slug"] for g in (await client.get("/api/category-groups")).json()["groups"]
               for c in g["categories"]]
    assert set(grouped) == db_slugs
    assert len(grouped) == len(set(grouped))  # без дублей
