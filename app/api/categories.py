from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.category import Category, District
from app.schemas.category import (
    CategoryListResponse,
    CategoryOut,
    DistrictListResponse,
    DistrictOut,
)

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all service categories."""
    result = await db.execute(select(Category).order_by(Category.id))
    categories = result.scalars().all()
    return CategoryListResponse(
        categories=[CategoryOut.model_validate(c) for c in categories]
    )


@router.get("/districts", response_model=DistrictListResponse)
async def list_districts(db: AsyncSession = Depends(get_db)):
    """List all districts."""
    result = await db.execute(select(District).order_by(District.name))
    districts = result.scalars().all()
    return DistrictListResponse(
        districts=[DistrictOut.model_validate(d) for d in districts]
    )
