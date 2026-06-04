from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.category import Category, City, Subcategory
from app.schemas.category import (
    CategoryGroupOut,
    CategoryGroupsResponse,
    CategoryListResponse,
    CategoryOut,
    CityListResponse,
    CityOut,
    SearchHit,
    SearchResponse,
    SubcategoryOut,
)
from app.services.catalog_data import GROUPS

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .order_by(Category.sort_order)
    )
    cats = result.scalars().all()
    return CategoryListResponse(categories=[CategoryOut.model_validate(c) for c in cats])


@router.get("/category-groups", response_model=CategoryGroupsResponse)
async def list_category_groups(db: AsyncSession = Depends(get_db)):
    """Группы верхнего уровня (статичная таксономия) с категориями из БД."""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .order_by(Category.sort_order)
    )
    by_slug = {c.slug: c for c in result.scalars().all()}
    groups = []
    for g in GROUPS:
        cats = [CategoryOut.model_validate(by_slug[s]) for s in g["categories"] if s in by_slug]
        groups.append(CategoryGroupOut(
            slug=g["slug"], label_ru=g["label_ru"], label_kz=g["label_kz"],
            icon=g["icon"], color=g["color"], categories=cats,
        ))
    return CategoryGroupsResponse(groups=groups)


@router.get("/categories/{slug}", response_model=CategoryOut)
async def get_category(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .where(Category.slug == slug)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return CategoryOut.model_validate(c)


@router.get("/cities", response_model=CityListResponse)
async def list_cities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(City).options(selectinload(City.districts)).order_by(City.sort_order)
    )
    cities = result.scalars().all()
    return CityListResponse(cities=[CityOut.model_validate(c) for c in cities])


@router.get("/search/services", response_model=SearchResponse)
async def search_services(
    q: str = Query(..., min_length=1),
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Keyword-based search for subcategories.

    Matches:
      1. exact keyword hits in subcategory.keywords
      2. substring match in label_ru / label_kz
      3. substring match in category label_ru / label_kz (falls back to category)
    """
    needle = q.strip().lower()
    result = await db.execute(
        select(Subcategory).options(selectinload(Subcategory.category))
    )
    subs = result.scalars().all()

    hits: list[SearchHit] = []
    seen: set[tuple[str, str]] = set()

    def _add(sub: Subcategory, matched: str | None):
        key = (sub.category.slug, sub.slug)
        if key in seen:
            return
        seen.add(key)
        hits.append(SearchHit(
            category_slug=sub.category.slug,
            category_label_ru=sub.category.label_ru,
            category_label_kz=sub.category.label_kz,
            subcategory_slug=sub.slug,
            subcategory_label_ru=sub.label_ru,
            subcategory_label_kz=sub.label_kz,
            matched_keyword=matched,
        ))

    # Pass 1 — keyword hits (best)
    for sub in subs:
        for kw in (sub.keywords or []):
            if needle in kw.lower() or kw.lower() in needle:
                _add(sub, kw)
                break

    # Pass 2 — label substring
    for sub in subs:
        if needle in sub.label_ru.lower() or needle in sub.label_kz.lower():
            _add(sub, None)

    # Pass 3 — category label substring (add "other" subcategory as bucket)
    for sub in subs:
        if sub.is_other and (
            needle in sub.category.label_ru.lower()
            or needle in sub.category.label_kz.lower()
        ):
            _add(sub, None)

    return SearchResponse(query=q, hits=hits[:limit])
