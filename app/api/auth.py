from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.phone import normalize_phone
from app.core.security import (
    create_access_token,
    get_current_user,
)
from app.models.master_profile import MasterProfile
from app.models.user import User
from app.schemas.auth import (
    AuthTokenResponse,
    ChangePhoneRequest,
    LoginRequest,
    MasterProfilePublic,
    ProfileSetupRequest,
    RoleSetupRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_to_response(user: User) -> UserResponse:
    mp_public = None
    if user.master_profile:
        mp = user.master_profile
        mp_public = MasterProfilePublic(
            specializations=mp.specializations or [],
            service_lat=mp.service_lat,
            service_lng=mp.service_lng,
            service_radius_km=mp.service_radius_km,
            tier=mp.tier,
            commission_percent=mp.commission_percent,
            rating=mp.rating or 0.0,
            review_count=mp.review_count or 0,
            order_count=mp.order_count or 0,
            onboarding_complete=mp.onboarding_complete,
            iin_verified=mp.iin_verified,
            balance=mp.balance or 0,
        )
    return UserResponse(
        id=user.id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        initials=user.initials,
        city_slug=user.city_slug,
        photo_url=user.photo_url,
        role=user.role,
        language=user.language or "ru",
        phone_visible_after_deal=user.phone_visible_after_deal,
        online_status_visible=user.online_status_visible,
        client_rating=user.client_rating or 0.0,
        client_review_count=user.client_review_count or 0,
        client_order_count=user.client_order_count or 0,
        master_profile=mp_public,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Вход/регистрация по номеру телефона. Подтверждение владения номером не выполняется."""
    phone = normalize_phone(req.phone)
    if phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера",
        )
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    is_new = user is None
    if is_new:
        user = User(phone=phone)
        db.add(user)
        await db.flush()
    token = create_access_token(user.id)
    return AuthTokenResponse(access_token=token, is_new_user=is_new)


@router.post("/profile", response_model=UserResponse)
async def setup_profile(
    req: ProfileSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.first_name = req.first_name
    user.last_name = req.last_name
    user.city_slug = req.city_slug
    if req.photo_url:
        user.photo_url = req.photo_url
    await db.flush()
    return user_to_response(user)


@router.post("/role", response_model=UserResponse)
async def set_role(
    req: RoleSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.role = req.role
    if req.role == "master" and user.master_profile is None:
        db.add(MasterProfile(user_id=user.id))
    await db.flush()
    await db.refresh(user)
    return user_to_response(user)


@router.post("/change-phone", response_model=UserResponse)
async def change_phone(
    req: ChangePhoneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    phone = normalize_phone(req.phone)
    if phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера",
        )
    existing = await db.execute(select(User).where(User.phone == phone))
    owner = existing.scalar_one_or_none()
    if owner is not None and owner.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот номер уже используется",
        )
    user.phone = phone
    await db.flush()
    return user_to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Touch last-seen
    user.last_seen_at = datetime.now(timezone.utc)
    await db.flush()
    return user_to_response(user)
