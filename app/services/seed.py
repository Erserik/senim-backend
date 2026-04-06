from sqlalchemy import select

from app.core.database import async_session
from app.models.category import Category, District


CATEGORIES = [
    {"slug": "plumber", "label": "Сантехник", "icon": "\U0001f527", "color": "#34C759"},
    {"slug": "electrician", "label": "Электрик", "icon": "\u26a1", "color": "#FF9500"},
    {"slug": "cleaning", "label": "Уборка", "icon": "\U0001f9f9", "color": "#5856D6"},
    {"slug": "renovation", "label": "Ремонт квартир", "icon": "\U0001f3e0", "color": "#FF3B30"},
    {"slug": "movers", "label": "Грузчики", "icon": "\U0001f4e6", "color": "#007AFF"},
    {"slug": "furniture", "label": "Мебельщик", "icon": "\U0001fa91", "color": "#AF52DE"},
    {"slug": "ac", "label": "Кондиционеры", "icon": "\u2744\ufe0f", "color": "#5AC8FA"},
    {"slug": "painter", "label": "Маляр", "icon": "\U0001f3a8", "color": "#FFCC00"},
    {"slug": "welder", "label": "Сварщик", "icon": "\U0001f525", "color": "#FF6B35"},
    {"slug": "tiler", "label": "Плиточник", "icon": "\U0001f7eb", "color": "#8B4513"},
    {"slug": "carpenter", "label": "Плотник", "icon": "\U0001fa9a", "color": "#A0522D"},
    {"slug": "other", "label": "Другое", "icon": "\U0001f4ac", "color": "#8E8E93"},
]

DISTRICTS = [
    "Алмалинский",
    "Ауэзовский",
    "Бостандыкский",
    "Жетысуский",
    "Медеуский",
    "Наурызбайский",
    "Турксибский",
    "Алатауский",
]


async def seed_initial_data():
    """Seed categories and districts if they don't exist."""
    async with async_session() as session:
        # Seed categories
        result = await session.execute(select(Category).limit(1))
        if result.scalar_one_or_none() is None:
            for cat_data in CATEGORIES:
                session.add(Category(**cat_data))
            await session.flush()

        # Seed districts
        result = await session.execute(select(District).limit(1))
        if result.scalar_one_or_none() is None:
            for name in DISTRICTS:
                session.add(District(name=name))
            await session.flush()

        await session.commit()
