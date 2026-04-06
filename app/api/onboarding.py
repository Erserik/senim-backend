from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.onboarding import (
    DistrictsRequest,
    ExperienceRequest,
    OnboardingStatusResponse,
    PortfolioRequest,
    PricesRequest,
    SpecializationsRequest,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _get_master_profile(user: User):
    if user.role != "master" or user.master_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a master or profile not created",
        )
    return user.master_profile


@router.post("/specializations")
async def set_specializations(
    req: SpecializationsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.specializations = req.specializations
    await db.flush()
    return {"status": "ok", "specializations": profile.specializations}


@router.post("/experience")
async def set_experience(
    req: ExperienceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.experience = req.experience
    profile.bio = req.bio
    await db.flush()
    return {"status": "ok", "experience": profile.experience, "bio": profile.bio}


@router.post("/portfolio")
async def set_portfolio(
    req: PortfolioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.portfolio = req.portfolio
    await db.flush()
    return {"status": "ok", "portfolio": profile.portfolio}


@router.post("/districts")
async def set_districts(
    req: DistrictsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.districts = req.districts
    await db.flush()
    return {"status": "ok", "districts": profile.districts}


@router.post("/prices")
async def set_prices(
    req: PricesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.prices = {k: v.model_dump(by_alias=True) for k, v in req.prices.items()}
    await db.flush()
    return {"status": "ok", "prices": profile.prices}


@router.post("/complete")
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = _get_master_profile(user)
    profile.onboarding_complete = True
    await db.flush()
    return {"status": "ok", "onboarding_complete": True}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: User = Depends(get_current_user)):
    profile = _get_master_profile(user)

    if not profile.specializations:
        return OnboardingStatusResponse(step="specializations", complete=False)
    if not profile.experience:
        return OnboardingStatusResponse(step="experience", complete=False)
    if not profile.districts:
        return OnboardingStatusResponse(step="districts", complete=False)
    if profile.onboarding_complete:
        return OnboardingStatusResponse(step="complete", complete=True)

    return OnboardingStatusResponse(step="prices", complete=False)
