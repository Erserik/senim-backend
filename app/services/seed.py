"""Seed reference data and demo users/orders so the app looks alive from first run."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import async_session
from app.models import (
    Category,
    Chat,
    City,
    District,
    MasterProfile,
    Message,
    Order,
    Response,
    Review,
    Subcategory,
    User,
)
from app.services.catalog_data import (
    CATEGORIES,
    CITIES,
    default_districts_for_city,
)


async def _seed_catalog(db: AsyncSession) -> None:
    # Cities & districts
    existing_city = (await db.execute(select(City).limit(1))).scalar_one_or_none()
    if existing_city is None:
        for order, c in enumerate(CITIES):
            city = City(
                slug=c["slug"],
                name_ru=c["name_ru"],
                name_kz=c["name_kz"],
                latitude=c["lat"],
                longitude=c["lng"],
                sort_order=order,
            )
            db.add(city)
        await db.flush()

        for c in CITIES:
            city = (await db.execute(select(City).where(City.slug == c["slug"]))).scalar_one()
            for slug, name_ru, name_kz in default_districts_for_city(c["slug"]):
                db.add(District(
                    city_id=city.id,
                    slug=slug,
                    name_ru=name_ru,
                    name_kz=name_kz,
                ))
        await db.flush()

    # Categories & subcategories — идемпотентный upsert по slug:
    # добавляет недостающее, обновляет labels/icon/color/sort, ничего не удаляет
    # (безопасно для прод-ссылок мастеров и заказов).
    res = await db.execute(
        select(Category).options(selectinload(Category.subcategories))
    )
    existing_cats = {c.slug: c for c in res.scalars().all()}

    for order, cat in enumerate(CATEGORIES):
        category = existing_cats.get(cat["slug"])
        if category is None:
            category = Category(
                slug=cat["slug"],
                label_ru=cat["label_ru"],
                label_kz=cat["label_kz"],
                icon=cat["icon"],
                color=cat["color"],
                sort_order=order,
            )
            db.add(category)
            await db.flush()
            existing_subs: dict[str, Subcategory] = {}
        else:
            category.label_ru = cat["label_ru"]
            category.label_kz = cat["label_kz"]
            category.icon = cat["icon"]
            category.color = cat["color"]
            category.sort_order = order
            existing_subs = {s.slug: s for s in category.subcategories}

        for sub_order, (sslug, sru, skz, keywords) in enumerate(cat["subcategories"]):
            sub = existing_subs.get(sslug)
            if sub is None:
                db.add(Subcategory(
                    category_id=category.id,
                    slug=sslug,
                    label_ru=sru,
                    label_kz=skz,
                    keywords=keywords,
                    sort_order=sub_order,
                    is_other=sslug == "other",
                ))
            else:
                sub.label_ru = sru
                sub.label_kz = skz
                sub.keywords = keywords
                sub.sort_order = sub_order
    await db.flush()


DEMO_MASTERS = [
    {
        "phone": "+77011112233",
        "first_name": "Алмас",
        "last_name": "Серікбаев",
        "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&q=80",
        "specs": ["plumber", "ac", "electrician"],
        "bio": "Сантехник с 7-летним стажем. Аккуратно, со своим инструментом. Гарантия на работы.",
        "experience": "gt5",
        "portfolio": [
            "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=800&q=80",
            "https://images.unsplash.com/photo-1600508774764-4ce704363d66?w=800&q=80",
            "https://images.unsplash.com/photo-1572297780672-0662930d7ed9?w=800&q=80",
        ],
        "districts": ["bostandyksiy", "medeuskiy", "almaliniskiy"],
        "prices": {
            "plumber": {"from": 8000, "to": 25000},
            "ac": {"from": 15000, "to": 40000},
            "electrician": {"from": 5000, "to": 20000},
        },
        "rating": 4.8,
        "review_count": 12,
        "order_count": 15,
        "balance": 12000,
    },
    {
        "phone": "+77022223344",
        "first_name": "Марат",
        "last_name": "Кабиев",
        "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&q=80",
        "specs": ["electrician", "handyman"],
        "bio": "Электрик, 12 лет опыта. Работаю по всему городу. Квитанция и гарантия.",
        "experience": "gt5",
        "portfolio": [
            "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=800&q=80",
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
        ],
        "districts": ["almaliniskiy", "medeuskiy", "auezovskiy", "bostandyksiy"],
        "prices": {
            "electrician": {"from": 3000, "to": 25000},
            "handyman": {"from": 2500, "to": 15000},
        },
        "rating": 4.9,
        "review_count": 21,
        "order_count": 28,
        "balance": 5000,
    },
    {
        "phone": "+77033334455",
        "first_name": "Айгуль",
        "last_name": "Канатова",
        "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&q=80",
        "specs": ["renovation", "furniture"],
        "bio": "Отделочник. Клею обои, крашу стены, кладу плитку. Делаю аккуратно и в срок.",
        "experience": "1to5",
        "portfolio": [
            "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=800&q=80",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80",
        ],
        "districts": ["auezovskiy", "turksibskiy", "alatayskiy"],
        "prices": {
            "renovation": {"from": 4000, "to": 80000},
            "furniture": {"from": 3000, "to": 15000},
        },
        "rating": 4.7,
        "review_count": 8,
        "order_count": 10,
        "balance": 2000,
    },
    {
        "phone": "+77044445566",
        "first_name": "Ерлан",
        "last_name": "Бекенов",
        "photo_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&q=80",
        "specs": ["appliance_repair", "computer"],
        "bio": "Ремонтирую холодильники, стиралки, варочные панели. Диагностика бесплатно.",
        "experience": "gt5",
        "portfolio": [
            "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?w=800&q=80",
        ],
        "districts": ["bostandyksiy", "medeuskiy"],
        "prices": {
            "appliance_repair": {"from": 5000, "to": 30000},
            "computer": {"from": 3000, "to": 20000},
        },
        "rating": 4.6,
        "review_count": 5,
        "order_count": 6,
        "balance": 0,
    },
]


DEMO_CLIENTS = [
    {
        "phone": "+77055556677",
        "first_name": "Марина",
        "last_name": "Смирнова",
        "photo_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&q=80",
    },
    {
        "phone": "+77066667788",
        "first_name": "Данияр",
        "last_name": "Омаров",
        "photo_url": "https://images.unsplash.com/photo-1507591064344-4c6ce005b128?w=200&q=80",
    },
]


DEMO_ORDERS = [
    {
        "client_phone": "+77055556677",
        "category_slug": "plumber",
        "subcategory_slug": "leak",
        "title": "Течёт кран на кухне, нужна замена",
        "description": "Кран течёт уже неделю, вода капает постоянно. Нужен мастер со своим смесителем. Кухня стандартная, доступ свободный.",
        "district_slug": "bostandyksiy",
        "budget_from": 10000,
        "budget_to": 15000,
        "date_option": "tomorrow",
        "time_from": "14:00",
        "time_to": "18:00",
        "photos": ["https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=800&q=80"],
    },
    {
        "client_phone": "+77066667788",
        "category_slug": "electrician",
        "subcategory_slug": "socket",
        "title": "Установка розеток в новостройке, 8 точек",
        "description": "Нужно установить 8 розеток в новостройке. Провода уже подведены.",
        "district_slug": "medeuskiy",
        "budget_from": 25000,
        "budget_to": 25000,
        "date_option": "this_week",
        "photos": [],
    },
    {
        "client_phone": "+77055556677",
        "category_slug": "ac",
        "subcategory_slug": "ac_install",
        "title": "Установка кондиционера LG 12BTU",
        "description": "Купил кондиционер, нужно установить. Этаж 4, трасса ~4 метра.",
        "district_slug": "almaliniskiy",
        "budget_from": 25000,
        "budget_to": 35000,
        "date_option": "asap",
        "photos": [],
    },
    {
        "client_phone": "+77066667788",
        "category_slug": "renovation",
        "subcategory_slug": "wallpaper",
        "title": "Поклейка обоев в спальне, 18 м²",
        "description": "Обои готовы, нужен аккуратный мастер. Стены подготовлены.",
        "district_slug": "auezovskiy",
        "is_negotiable": True,
        "date_option": "this_week",
        "photos": [],
    },
    {
        "client_phone": "+77055556677",
        "category_slug": "appliance_repair",
        "subcategory_slug": "fridge",
        "title": "Холодильник не морозит",
        "description": "Samsung RB37, морозилка работает, а холодильник тёплый.",
        "district_slug": "turksibskiy",
        "budget_from": 8000,
        "budget_to": 20000,
        "date_option": "today",
        "photos": [],
    },
]


async def _seed_demo_users(db: AsyncSession) -> None:
    existing = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    if existing is not None:
        return

    # Clients
    for c in DEMO_CLIENTS:
        user = User(
            phone=c["phone"],
            first_name=c["first_name"],
            last_name=c["last_name"],
            photo_url=c["photo_url"],
            role="client",
            city_slug="almaty",
        )
        db.add(user)

    # Masters
    for m in DEMO_MASTERS:
        user = User(
            phone=m["phone"],
            first_name=m["first_name"],
            last_name=m["last_name"],
            photo_url=m["photo_url"],
            role="master",
            city_slug="almaty",
        )
        db.add(user)
        await db.flush()

        profile = MasterProfile(
            user_id=user.id,
            specializations=m["specs"],
            experience=m["experience"],
            bio=m["bio"],
            portfolio=m["portfolio"],
            districts=m["districts"],
            prices=m["prices"],
            onboarding_complete=True,
            iin="123456789012",
            iin_verified=True,
            rating=m["rating"],
            review_count=m["review_count"],
            order_count=m["order_count"],
            response_time_minutes=9,
            balance=m["balance"],
        )
        profile.recompute_tier()
        db.add(profile)

    await db.flush()


async def _seed_demo_orders(db: AsyncSession) -> None:
    existing = (await db.execute(select(Order).limit(1))).scalar_one_or_none()
    if existing is not None:
        return

    for i, o in enumerate(DEMO_ORDERS):
        client = (await db.execute(
            select(User).where(User.phone == o["client_phone"])
        )).scalar_one()
        category = (await db.execute(
            select(Category).where(Category.slug == o["category_slug"])
        )).scalar_one()
        sub = (await db.execute(
            select(Subcategory).where(
                (Subcategory.category_id == category.id)
                & (Subcategory.slug == o["subcategory_slug"])
            )
        )).scalar_one()
        district = (await db.execute(
            select(District).where(District.slug == o["district_slug"])
        )).scalar_one()

        order = Order(
            client_id=client.id,
            category_slug=category.slug,
            category_label_ru=category.label_ru,
            category_label_kz=category.label_kz,
            subcategory_slug=sub.slug,
            subcategory_label_ru=sub.label_ru,
            subcategory_label_kz=sub.label_kz,
            title=o["title"],
            description=o["description"],
            photos=o.get("photos", []),
            city_slug="almaty",
            district_slug=district.slug,
            district_label_ru=district.name_ru,
            district_label_kz=district.name_kz,
            date_option=o.get("date_option"),
            time_from=o.get("time_from"),
            time_to=o.get("time_to"),
            budget_from=o.get("budget_from"),
            budget_to=o.get("budget_to"),
            is_negotiable=o.get("is_negotiable", False),
            status="active",
            created_at=datetime.now(timezone.utc) - timedelta(hours=i * 3 + 1),
        )
        db.add(order)
    await db.flush()


async def _seed_demo_proposals(db: AsyncSession) -> None:
    orders = (await db.execute(select(Order))).scalars().all()
    for order in orders:
        # skip if already has proposals
        if order.responses:
            continue
        # Find masters whose specializations include this category
        masters = (await db.execute(
            select(User).where(User.role == "master")
        )).scalars().all()
        added = 0
        for m in masters:
            if added >= 2:
                break
            if not m.master_profile or order.category_slug not in (m.master_profile.specializations or []):
                continue
            price = order.budget_from or 10000
            price = int(price * (0.9 if added == 0 else 1.1))
            db.add(Response(
                order_id=order.id,
                master_id=m.id,
                price=price,
                message="Здравствуйте! Могу подъехать, всё нужное с собой." if added == 0
                        else "Добрый день! Возьмусь за работу. Цена обсуждаема.",
                availability="today" if added == 0 else "tomorrow",
                status="pending",
            ))
            added += 1
        order.response_count = added
    await db.flush()


async def _seed_admin(db: AsyncSession) -> None:
    existing = (await db.execute(select(User).where(User.phone == "+77000000001"))).scalar_one_or_none()
    if existing is not None:
        if not existing.is_admin:
            existing.is_admin = True
            await db.flush()
        return
    admin = User(
        phone="+77000000001",
        first_name="Admin",
        last_name="Senim",
        role="admin",
        is_admin=True,
        city_slug="almaty",
    )
    db.add(admin)
    await db.flush()


async def seed_initial_data() -> None:
    """Idempotent seed: catalog + demo users/orders/proposals."""
    async with async_session() as db:
        await _seed_catalog(db)
        await _seed_demo_users(db)
        await _seed_admin(db)
        await _seed_demo_orders(db)
        await _seed_demo_proposals(db)
        await db.commit()
