from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import user_to_response
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.master_profile import MasterProfile
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.onboarding import (
    ExperienceRequest,
    IinRequest,
    OnboardingStatusResponse,
    PortfolioRequest,
    PricesRequest,
    ServiceAreaRequest,
    SpecializationsRequest,
)
from app.services.iin import IinError, validate_iin

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _profile(user: User):
    if user.role != "master" or user.master_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a master or profile not created",
        )
    return user.master_profile


@router.post("/specializations", response_model=UserResponse)
async def set_specializations(
    req: SpecializationsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.specializations = req.specializations
    await db.flush()
    return user_to_response(user)


@router.post("/experience", response_model=UserResponse)
async def set_experience(
    req: ExperienceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.experience = req.experience
    p.bio = req.bio
    await db.flush()
    return user_to_response(user)


@router.post("/portfolio", response_model=UserResponse)
async def set_portfolio(
    req: PortfolioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.portfolio = req.portfolio
    await db.flush()
    return user_to_response(user)


@router.post("/service-area", response_model=UserResponse)
async def set_service_area(
    req: ServiceAreaRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.service_lat = req.lat
    p.service_lng = req.lng
    p.service_radius_km = req.radius_km
    await db.flush()
    return user_to_response(user)


@router.post("/prices", response_model=UserResponse)
async def set_prices(
    req: PricesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.prices = {
        k: {"from": v.from_, "to": v.to} for k, v in req.prices.items()
    }
    await db.flush()
    return user_to_response(user)


@router.post("/iin", response_model=UserResponse)
async def verify_iin(
    req: IinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Offline IIN validation: format + ГОСТ РК checksum + birthdate + age ≥ 18 + uniqueness.

    Does NOT perform identity binding (eGov/KYC required for that).
    """
    p = _profile(user)

    try:
        validate_iin(req.iin)
    except IinError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ex.message,
        ) from ex

    existing = (await db.execute(
        select(MasterProfile).where(
            MasterProfile.iin == req.iin,
            MasterProfile.user_id != user.id,
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот ИИН уже зарегистрирован на другом аккаунте",
        )

    p.iin = req.iin
    p.iin_verified = True
    await db.flush()
    return user_to_response(user)


@router.post("/complete", response_model=UserResponse)
async def complete_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = _profile(user)
    p.onboarding_complete = True
    await db.flush()
    return user_to_response(user)


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(user: User = Depends(get_current_user)):
    p = _profile(user)

    if not p.specializations:
        step = "specializations"
    elif not p.experience:
        step = "experience"
    elif p.service_lat is None or p.service_lng is None or not p.service_radius_km:
        step = "districts"
    elif not p.iin_verified:
        step = "iin"
    elif p.onboarding_complete:
        step = "complete"
    else:
        step = "prices"

    return OnboardingStatusResponse(
        step=step,
        complete=p.onboarding_complete,
        specializations=p.specializations or [],
        experience=p.experience,
        portfolio=p.portfolio or [],
        service_lat=p.service_lat,
        service_lng=p.service_lng,
        service_radius_km=p.service_radius_km,
        prices=p.prices or {},
        bio=p.bio,
        iin_verified=p.iin_verified,
    )
